from typing import Dict, Any, List
from datetime import datetime, timezone
import json
import uuid
from backend.shared_services.shared_types import MainState
from backend.shared_services.logger_setup import setup_logger
from backend.shared_services.handoff_parameters import get_unanalyzed_handoffs, mark_handoffs_as_analyzed
from backend.shared_services.streaming import stream_response_to_user

logger = setup_logger()


async def respond_to_human(state: MainState) -> MainState:
    """
    Final agent that delivers responses to users.
    Currently just picks up message_to_user from handoffs.
    """
    try:
        response_id = str(uuid.uuid4())

        # Get ALL unanalyzed handoffs for respond_to_human
        handoff_parameters = get_unanalyzed_handoffs(state, "respond_to_human")
        
        if not handoff_parameters:
            logger.error("No handoff parameters found for respond_to_human")
            return state

        # Get the message from the latest handoff
        latest_handoff = handoff_parameters[-1]
        
        # Get message directly from top level
        message = latest_handoff.get("message_to_user")

        #Get sources and follow up questions, if available 
        if "sources" in latest_handoff:
            sources = latest_handoff.get("sources")
        else:
            sources = []
        if "follow_up_questions" in latest_handoff:
            follow_up_questions = latest_handoff.get("follow_up_questions")
        else:
            follow_up_questions = []
        
        if not message:
            logger.error("No message_to_user found in handoff parameters")
            return state
            
        # Mark all handoffs as analyzed
        state = mark_handoffs_as_analyzed(state, "respond_to_human")
        
        # Update final_answer and related info in state for frontend
        state["final_answer"] = message
        state["sources"] = sources
        state["follow_up_questions"] = follow_up_questions
        
        # Add response to conversation history
        state["conversation_history"].append({
            "role": "assistant",
            "content": message,
            "sources": sources,
            "follow_up_questions": follow_up_questions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Add to node history
        state["node_history"].append({
            "role": "AI_AGENT",
            "node": "respond_to_human",
            "conversation_id": state["conversation_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_id": response_id,
            "content": {
                "response_type": "final_response",
                "message": message,
                "sources": sources,
                "follow_up_questions": follow_up_questions
            }
        })

        return state

    except Exception as e:
        logger.error(f"Error in respond_to_human: {str(e)}", exc_info=True)
        return state 