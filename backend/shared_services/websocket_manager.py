import logging
from typing import Dict
from fastapi import WebSocket
import json
from backend.shared_services.logger_setup import setup_logger

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to session {session_id}: {str(e)}")
                self.disconnect(session_id)

# Create a singleton instance
websocket_manager = WebSocketManager()

def register_connection(session_id: str, websocket: WebSocket):
    """Register a new websocket connection"""
    websocket_manager.active_connections[session_id] = websocket
    logger.info(f"WebSocket connection registered for session: {session_id}")

def remove_connection(session_id: str):
    """Remove a websocket connection"""
    websocket_manager.disconnect(session_id)

async def send_stream_to_websocket(session_id: str, chunk: str):
    """Send a chunk of text to the websocket"""
    if session_id in websocket_manager.active_connections:
        try:
            await websocket_manager.active_connections[session_id].send_text(json.dumps({
                "type": "stream",
                "content": chunk
            }))
        except Exception as e:
            logger.error(f"Error sending to websocket: {str(e)}")
            websocket_manager.disconnect(session_id) 