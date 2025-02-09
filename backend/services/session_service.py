from datetime import datetime, timezone
from typing import Dict, Any, List
from backend.shared_services.db import get_postgres_connection
from backend.shared_services.logger_setup import setup_logger
from psycopg2.extras import RealDictCursor

logger = setup_logger()

def get_chat_sessions(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get chat sessions grouped by session_id from existing state data"""
    conn = get_postgres_connection("conversations")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT DISTINCT ON (state->>'session_id')
                    state->>'session_id' as session_id,
                    state->'conversation_history' as messages,
                    MIN(log_timestamp) OVER (PARTITION BY state->>'session_id') as created_at,
                    MAX(log_timestamp) OVER (PARTITION BY state->>'session_id') as last_updated,
                    (
                        SELECT content 
                        FROM jsonb_array_elements(state->'conversation_history') msgs
                        WHERE msgs->>'role' = 'user'
                        LIMIT 1
                    ) as first_message
                FROM andika.andika_conversations 
                WHERE user_id = %s
                    AND state->>'session_id' IS NOT NULL
                    AND state->'conversation_history' IS NOT NULL
                    AND jsonb_array_length(state->'conversation_history') > 0
                ORDER BY state->>'session_id', log_timestamp DESC
                LIMIT %s;
            """
            cur.execute(query, (user_id, limit))
            results = cur.fetchall()
            
            return [{
                'id': str(row['session_id']),
                'first_message': row['first_message'],
                'messages': row['messages'],
                'timestamp': row['created_at'].isoformat(),
                'last_updated': row['last_updated'].isoformat()
            } for row in results]
            
    except Exception as e:
        logger.error(f"Error retrieving chat sessions: {str(e)}")
        return []
    finally:
        conn.close()

def get_session_by_id(session_id: str) -> Dict[str, Any]:
    """Get a specific chat session by session_id"""
    conn = get_postgres_connection("conversations")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    state->>'session_id' as session_id,
                    state->'conversation_history' as messages,
                    MIN(log_timestamp) as created_at,
                    MAX(log_timestamp) as last_updated
                FROM andika.andika_conversations 
                WHERE state->>'session_id' = %s
                GROUP BY state->>'session_id', state->'conversation_history';
            """
            cur.execute(query, (session_id,))
            row = cur.fetchone()
            
            if row and row['messages']:
                first_message = next((msg['content'] for msg in row['messages'] if msg['role'] == 'user'), None)
                return {
                    'id': row['session_id'],
                    'first_message': first_message,
                    'messages': row['messages'],
                    'timestamp': row['created_at'].isoformat(),
                    'last_updated': row['last_updated'].isoformat()
                }
            return None
    except Exception as e:
        logger.error(f"Error retrieving chat session: {str(e)}")
        return None
    finally:
        conn.close() 