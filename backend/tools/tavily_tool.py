from typing import Dict, Any
from datetime import datetime, timezone
import json
import uuid
import os
from backend.shared_services.shared_types import MainState
from backend.shared_services.logger_setup import setup_logger
from backend.shared_services.handoff_parameters import get_unanalyzed_handoffs, mark_handoffs_as_analyzed
from backend.shared_services.handoffs import handoff_to_answer_user, handoff_to_welcome_user
from backend.shared_services.tavily import search_tavily

logger = setup_logger()

async def tavily_tool(state: MainState) -> MainState:
    """
    Tool to fetch web results using Tavily API
    """
    try:
        # Create a serializable version of state for logging
        log_state = {
            "user_id": state["user_id"],
            "session_id": state["session_id"],
            "conversation_id": state["conversation_id"],
            "user_input": state["user_input"]
        }
        
        logger.info("tavily_tool started with state: %s", json.dumps(log_state, indent=2))

        response_id = str(uuid.uuid4())
        handoff_parameters = get_unanalyzed_handoffs(state, "tavily_tool")
        
        if not handoff_parameters:
            logger.info("No unanalyzed handoffs found for tavily_tool")
            return handoff_to_welcome_user(
                state, 
                "No parameters provided for web search", 
                response_id,
                "tavily_tool"
            )

        latest_params = handoff_parameters[-1]
        query = latest_params.get("query", "")
        
        if not query:
            logger.error("No search query provided")
            return handoff_to_welcome_user(
                state, 
                "No search query provided", 
                response_id,
                "tavily_tool"
            )

        search_results = search_tavily(query)
        
        if not search_results:
            logger.error("No search results found")
            return handoff_to_welcome_user(
                state, 
                "No web results found", 
                response_id,
                "tavily_tool"
            )

        # Mark handoffs as analyzed
        state = mark_handoffs_as_analyzed(state, "tavily_tool")
        return handoff_to_answer_user(
            state, 
            search_results, 
            response_id,
            "tavily_tool"
        )

    except Exception as e:
        logger.error(f"Error in tavily_tool: {str(e)}", exc_info=True)
        raise

    finally:
        # At the end, log only the response ID
        logger.info("Completed tavily_tool")
        return state