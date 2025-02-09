from typing import List, Dict
import logging
from backend.shared_services.llm import call_llm_api_stream
from backend.shared_services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

async def stream_response_to_user(messages: List[Dict[str, str]], session_id: str) -> str:
    """Stream the response to the user via WebSocket"""
    try:
        full_response = []
        
        # Use the existing streaming function
        async for content in call_llm_api_stream(messages):
            if content:
                # Send the chunk to the frontend via WebSocket
                await websocket_manager.send_message(content, session_id)
                full_response.append(content)
        
        # Return the complete response
        return "".join(full_response)
        
    except Exception as e:
        logger.error(f"Error in stream_response_to_user: {str(e)}", exc_info=True)
        raise 