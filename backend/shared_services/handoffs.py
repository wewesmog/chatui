from typing import Dict, Any
from datetime import datetime, timezone
from backend.shared_services.shared_types import MainState


def handoff_to_answer_user(state: MainState, content: Dict[str, Any], response_id: str, source: str) -> MainState:
    """
    Helper function to create an answer_user handoff with content
    """
    state["node_history"].append({
        "role": "AI_AGENT",
        "node": source,
        "conversation_id": state["conversation_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_id": response_id,
        "content": {
            "response_type": "handoff",
            "agents": [{
                "agent_name": "answer_user",
                "parameters": {
                    "content": content,
                    "context": f"Content successfully retrieved from {source}",
                    "previous_attempt": f"Content retrieval completed in {source}"
                }
            }]
        }
    })

    
    
    return state

def handoff_to_welcome_user(state: MainState, error_context: str, response_id: str, source: str) -> MainState:
    """
    Helper function to create a welcome_user handoff when errors occur
    """
    state["node_history"].append({
        "role": "AI_AGENT",
        "node": source,
        "conversation_id": state["conversation_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_id": response_id,
        "content": {
            "response_type": "handoff",
            "agents": [{
                "agent_name": "welcome_user",
                "parameters": {
                    "original_query": state.get('user_input', ''),
                    "context": error_context,
                    "previous_attempt": f"Operation failed in {source}"
                }
            }]
        }
    })
    
    return state 