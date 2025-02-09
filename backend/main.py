from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import json
import uuid
import asyncio
import logging
import sys
import uvicorn
import requests
import gradio as gr

from backend.shared_services.get_conversation_history import get_conversation_history, get_user_past_history
from backend.shared_services.save_conversation import save_conversation
from backend.shared_services.logger_setup import setup_logger
from backend.shared_services.shared_types import MainState
from backend.shared_services.websocket_manager import register_connection, remove_connection
from backend.shared_services.handoffs import handoff_to_welcome_user

from backend.agents.welcome_user import welcome_user
from backend.agents.answer_user import answer_user
from backend.agents.respond_to_human import respond_to_human


from backend.tools.extract_docs_tool import extract_docs_tool
from backend.tools.tavily_tool import tavily_tool


# Configure logging to show more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)  # Enable debug mode

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active websocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_locks: Dict[str, asyncio.Lock] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        try:
            logger.debug(f"Attempting to connect WebSocket for session {session_id}")
            await websocket.accept()
            self.active_connections[session_id] = websocket
            self.connection_locks[session_id] = asyncio.Lock()
            logger.info(f"WebSocket connected successfully for session {session_id}")
            
            # Send initial connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_status",
                "content": "Connected to chat server"
            }))
            
        except Exception as e:
            logger.error(f"Error in WebSocket connection for session {session_id}: {str(e)}", exc_info=True)
            raise

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            logger.info(f"Disconnecting WebSocket for session {session_id}")
            del self.active_connections[session_id]
        if session_id in self.connection_locks:
            del self.connection_locks[session_id]

    async def send_message(self, message: str, session_id: str):
        if session_id in self.active_connections and session_id in self.connection_locks:
            async with self.connection_locks[session_id]:
                try:
                    ws = self.active_connections[session_id]
                    await ws.send_text(message)  # Send raw message
                    logger.debug(f"Message sent to session {session_id}")
                except Exception as e:
                    logger.error(f"Error sending message to {session_id}: {str(e)}", exc_info=True)
                    self.disconnect(session_id)

manager = ConnectionManager()

class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_id: str
    conversation_id: Optional[str] = None

class ChatInput(BaseModel):
    user_id: str
    conversation_id: Optional[str] = None
    user_input: str
    session_id: Optional[str] = None  # Made optional since we'll generate if not provided

class ChatResponse(BaseModel):
    message_to_human: Optional[str]
    session_id: str  # Will always return the session_id (new or existing)
    conversation_id: str
    error: Optional[str] = None
    is_new_session: bool  # Indicate if this was a new session

# Session management constants
SESSION_EXPIRY = timedelta(hours=24)  # Sessions expire after 24 hours
SESSION_CLEANUP_FREQUENCY = 100  # Clean up expired sessions every N requests

# In-memory session store (consider Redis for production)
active_sessions: Dict[str, Dict[str, Any]] = {}
request_counter = 0

# Add these constants at the top
MAX_MEMORY_RECORDS = 10  # Maximum records to keep in memory per user
MEMORY_THRESHOLD = 7     # When to fetch more from DB

def generate_session_id() -> str:
    """Generate a new session ID"""
    return str(uuid.uuid4())

async def cleanup_expired_sessions():
    """Remove expired sessions from memory"""
    current_time = datetime.now(timezone.utc)
    expired = [
        session_id for session_id, session in active_sessions.items()
        if current_time - session["last_active"] > SESSION_EXPIRY
    ]
    for session_id in expired:
        # Save state to DB before removing session
        if session_id in active_sessions:
            await save_conversation(active_sessions[session_id]["state"])
            del active_sessions[session_id]
            logger.info(f"Session {session_id} expired and saved to database")

async def get_or_create_session(chat_input: ChatInput) -> tuple[str, bool]:
    """Get existing session or create new one"""
    global request_counter
    
    # Periodic cleanup of expired sessions
    request_counter += 1
    if request_counter % SESSION_CLEANUP_FREQUENCY == 0:
        await cleanup_expired_sessions()
    
    # If session_id provided and valid, use it
    if chat_input.session_id and chat_input.session_id in active_sessions:
        session = active_sessions[chat_input.session_id]
        # Check if session is expired
        if datetime.now(timezone.utc) - session["last_active"] > SESSION_EXPIRY:
            # Session expired, create new one
            new_session_id = generate_session_id()
            return new_session_id, True
        else:
            # Update last active time
            session["last_active"] = datetime.now(timezone.utc)
            return chat_input.session_id, False
            
    # Create new session
    new_session_id = generate_session_id()
    return new_session_id, True

async def initialize_state(request: ChatRequest) -> MainState:
    """Initialize the state object for the chat flow"""
    # Generate conversation_id for this turn
    conversation_id = f"{request.user_id}_{request.session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    conversation_history = []
    node_history = []
    
    # Check memory records first
    memory_records = active_sessions.get(request.session_id, {}).get("conversation_history", [])
    
    # If memory records below threshold, fetch from DB
    if len(memory_records) < MEMORY_THRESHOLD:
        records_needed = MAX_MEMORY_RECORDS - len(memory_records)
        history = get_conversation_history(
            user_id=request.user_id,
            limit=records_needed
        )
        conversation_history = memory_records + history.get("conversation_history", [])
        conversation_history = conversation_history[-MAX_MEMORY_RECORDS:]
    else:
        conversation_history = memory_records[-MAX_MEMORY_RECORDS:]
    
    logger.info(f"Starting conversation {conversation_id} for user {request.user_id}")

    state = {
        "user_id": request.user_id,
        "session_id": request.session_id,
        "conversation_id": conversation_id,
        "user_input": request.user_input,
        "conversation_history": conversation_history,
        "node_history": node_history,
        "handoff_parameters": [],
        "extracted_parameters": {},
    }
    
    # Add websocket manager separately
    state["websocket_manager"] = manager
    
    return state

async def run_chat_flow(state: MainState) -> MainState:
    """Run the chat flow through agents and tools"""
    try:
        # Generate conversation_id if not present
        if not state.get("conversation_id"):
            state["conversation_id"] = f"{state['user_id']}_{state['session_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.info(f"Starting new conversation: {state['conversation_id']}")
        
        logger.info(f"Starting chat flow for session {state['session_id']}")
        max_steps = 20  # Prevent infinite loops
        steps_taken = 0
        
        state = await welcome_user(state)
        
        while steps_taken < max_steps:
            steps_taken += 1
            
            try:
                latest_record = state.get("node_history", [])[-1]
                print(f"Latest record: {latest_record}")
            except IndexError:
                logger.error("No node history found")
                break
                
            handoff_parameters = latest_record.get("content")
            if not handoff_parameters:
                logger.error("No handoff parameters found")
                break
                
            logger.info(f"Step {steps_taken}: Processing {handoff_parameters.get('response_type')}")
                
            if handoff_parameters.get('response_type') == "tool_call":
                for tool in handoff_parameters.get('tools', []):
                    tool_name = tool.get('tool')
                    logger.info(f"Calling tool: {tool_name}")
                    
                    if tool_name == "tavily_tool":
                        state = await tavily_tool(state)
                    elif tool_name == "extract_docs_tool":
                        state = await extract_docs_tool(state)
                    else:
                        logger.error(f"Unsupported tool: {tool_name}")
                        state = await handoff_to_welcome_user(state, f"Unsupported tool: {tool_name}")
                        
            elif handoff_parameters.get('response_type') == "handoff":
                for agent in handoff_parameters.get('agents', []):
                    # Check both agent and agent_name fields
                    agent_name = agent.get('agent') or agent.get('agent_name')
                    logger.info(f"Calling agent: {agent_name}")
                    
                    if agent_name == "welcome_user":
                        state = await welcome_user(state)
                    elif agent_name == "answer_user":
                        state = await answer_user(state)
                    elif agent_name == "respond_to_human":
                        logger.info(f"Final step: Responding to human for conversation {state['conversation_id']}")
                        state = await respond_to_human(state)
                        await save_conversation(state)
                        logger.info(f"Conversation {state['conversation_id']} completed")
                        return state
                    else:
                        logger.error(f"Unsupported agent: {agent_name}")
                        response_id = str(uuid.uuid4())
                        state = await handoff_to_welcome_user(
                            state=state,
                            error_message=f"Unsupported agent: {agent_name}",
                            response_id=response_id,
                            source="run_chat_flow"
                        )
            
            else:
                logger.error(f"Unsupported response type: {handoff_parameters.get('response_type')}")
                break
                
        if steps_taken >= max_steps:
            logger.warning(f"Max steps reached, ending conversation {state['conversation_id']}")
            # Add error message to state
            state["final_answer"] = "I apologize, but I've taken too many steps to process your request. Please try rephrasing your question in a simpler way."
            await save_conversation(state)
            
        return state

    except Exception as e:
        logger.error(f"Error in chat flow for conversation {state.get('conversation_id')}: {str(e)}", exc_info=True)
        raise

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    logger.info(f"New WebSocket connection request for session {session_id}")
    try:
        await manager.connect(websocket, session_id)
        logger.info(f"WebSocket connection accepted for session {session_id}")
        
        while True:
            try:
                data = await websocket.receive_text()
                if data != "ping" and data.strip():
                    logger.debug(f"Received WebSocket message from {session_id}: {data}")
                    
                    # Parse the incoming message
                    message_data = json.loads(data)
                    
                    # Create ChatRequest from WebSocket message
                    chat_request = ChatRequest(
                        user_id=message_data['user_id'],
                        user_input=message_data['user_input'],
                        session_id=message_data['session_id']
                    )
                    
                    # Initialize state and run chat flow
                    state = await initialize_state(chat_request)
                    state = await run_chat_flow(state)
                    
                    # Send response with sources and follow-up questions
                    await manager.send_message(json.dumps({
                        "type": "message",
                        "message": state.get("final_answer", "I apologize, but I couldn't generate a response."),
                        "sources": [
                            f"• {source}" for source in state.get("sources", [])
                        ],
                        "follow_up_questions": [
                            question for question in state.get("follow_up_questions", [])
                        ]
                    }), session_id)
                    
            except WebSocketDisconnect:
                manager.disconnect(session_id)
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"Error in websocket loop for {session_id}: {str(e)}")
                await manager.send_message(
                    "I apologize, but I encountered an error processing your message.",
                    session_id
                )
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {str(e)}")
    finally:
        manager.disconnect(session_id)
        logger.info(f"Cleaning up WebSocket connection for {session_id}")

@app.options("/chat")
async def chat_options():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        logger.info(f"Received chat request for session {request.session_id}")
        
        # Initialize state
        state = await initialize_state(request)
        
        # Run chat flow and wait for result
        state = await run_chat_flow(state)
        
        # Return the final answer to frontend
        return JSONResponse(content={
            "status": "success",
            "session_id": request.session_id,
            "message": state.get("final_answer", "I apologize, but I couldn't generate a response. Please try again."),
            "conversation_id": state.get("conversation_id", "")
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "I apologize, but I encountered an error while processing your request. Please try again.",
                "error_type": type(e).__name__,
                "technical_error": str(e)  # For debugging
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "connections": len(manager.active_connections)}

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/end-session")
async def end_session(session_id: str):
    """Endpoint for when user explicitly ends session (new chat button)"""
    try:
        if session_id in active_sessions:
            # Save final state to DB
            await save_conversation(active_sessions[session_id]["state"])
            # Clean up session
            del active_sessions[session_id]
            logger.info(f"Session {session_id} ended by user and saved to database")
            return {"status": "success", "message": "Session ended"}
        return {"status": "not_found", "message": "Session not found"}
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=True  # Enable auto-reload for development
    )