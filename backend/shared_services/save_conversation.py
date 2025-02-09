import json
from typing import Dict, Any
from backend.shared_services.db import get_postgres_connection
from backend.shared_services.logger_setup import setup_logger

logger = setup_logger()

async def save_conversation(state: Dict[str, Any]) -> None:
    """Save conversation state to database"""
    conn = get_postgres_connection("conversations")
    try:
        # Create a copy of state without the websocket manager
        save_state = state.copy()
        save_state.pop('websocket_manager', None)  # Remove websocket manager before saving
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO andika.andika_conversations 
                (user_id, session_id, conversation_id, state, log_timestamp)
                VALUES (%s, %s, %s, %s, NOW())
            """, (
                state['user_id'],
                state['session_id'],
                state['conversation_id'],
                json.dumps(save_state)
            ))
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error saving conversation: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
