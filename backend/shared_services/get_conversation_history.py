import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from .db import get_postgres_connection
from .logger_setup import setup_logger
from psycopg2.extras import RealDictCursor
import asyncpg


logger = setup_logger()

def get_conversation_history(
    user_id: str, 
    limit: int,  # Removed session_id and conversation_id parameters
) -> Dict[str, Any]:
    """
    Extract recent conversation_history and node_history for a user
    """
    conn = get_postgres_connection("conversations")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    state->'conversation_history' as conversation_history,
                    state->'node_history' as node_history
                FROM andika.andika_conversations 
                WHERE user_id = %s 
                ORDER BY log_timestamp DESC
                LIMIT %s;
            """, (user_id, limit))
            
            results = cur.fetchall()
            
            if not results:
                logger.info(f"No conversations found for user_id: {user_id}")
                return {
                    "status": "no_data",
                    "conversation_history": [],
                    "node_history": [],
                }
            
            # Extract histories
            conversations = []
            node_conversations = []
       
            for result in results:
                if result['conversation_history']:
                    conversations.extend(result['conversation_history'])
                if result['node_history']:
                    node_conversations.extend(result['node_history'])

            # Sort with error handling
            def safe_sort(items):
                try:
                    return sorted(
                        items,
                        key=lambda x: datetime.fromisoformat(x.get('timestamp', datetime.now().isoformat())),
                        reverse=True  # Newest first
                    )[:limit]  # Limit after sorting to get most recent
                except Exception as e:
                    logger.warning(f"Error sorting items: {str(e)}")
                    return items[:limit]

            return {
                "status": "success",
                "conversation_history": safe_sort(conversations),
                "node_history": safe_sort(node_conversations),
            }
            
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        return {
            "status": "error",
            "conversation_history": [],
            "node_history": []
        }
    finally:
        conn.close()

async def get_db_connection():
    """Get async database connection"""
    try:
        conn = await asyncpg.connect(
            user='your_user',
            password='your_password',
            database='ai_agents',
            host='localhost'
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

async def get_user_past_history(
    user_id: str,
    current_conversation_id: Optional[str] = None,
    max_past_turns: int = 5
) -> list:
    """
    Retrieve relevant exchanges from user's past conversations using async DB connection
    """
    try:
        conn = await get_db_connection()
        
        query = """
            SELECT 
                conversation_history,
                conversation_id,
                created_at as timestamp
            FROM conversations
            WHERE user_id = $1
            AND ($2::uuid IS NULL OR conversation_id != $2)
            ORDER BY created_at DESC
            LIMIT $3
        """
        
        rows = await conn.fetch(query, user_id, current_conversation_id, max_past_turns)
        await conn.close()
        
        relevant_history = []
        for row in rows:
            conversation = json.loads(row['conversation_history'])
            if conversation:
                relevant_history.append({
                    "conversation_id": row['conversation_id'],
                    "timestamp": row['timestamp'].isoformat(),
                    "exchange": conversation[-1]  # Last message pair
                })
        
        return relevant_history
            
    except Exception as e:
        logger.error(f"Error retrieving past history: {str(e)}")
        return []