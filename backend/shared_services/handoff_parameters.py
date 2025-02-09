from typing import List, Dict, Any
from datetime import datetime, timezone
import logging
from backend.shared_services.shared_types import MainState
from backend.shared_services.handoffs import handoff_to_welcome_user

logger = logging.getLogger(__name__)

def get_unanalyzed_handoffs(state: MainState, agent_name: str) -> List[Dict[str, Any]]:
    """
    Get all unanalyzed handoff parameters for a specific agent/tool from node_history
    Returns a list of parameter dictionaries from unanalyzed handoffs
    """
    handoff_parameters = []
    
    try:
        if "node_history" not in state or not state["node_history"]:
            logger.info(f"No node_history found for {agent_name}")
            return []

        for entry in state["node_history"]:
            if not isinstance(entry.get("content"), dict):
                continue

            content = entry["content"]
            
            # Handle agent handoffs
            if "agents" in content:
                for agent in content["agents"]:
                    if (
                        #get "agent_name" or "agent"    
                        (agent.get("agent_name") == agent_name or agent.get("agent") == agent_name) and
                        (not agent.get("analyzed", False))  # Either no analyzed field or analyzed is False
                    ):
                        handoff_parameters.append(agent.get("parameters", {}))

            # Handle tool calls
            elif (
                content.get("response_type") == "tool_call" and
                content.get("tool") == agent_name and
                (not content.get("analyzed", False))  # Either no analyzed field or analyzed is False
            ):
                handoff_parameters.append(content.get("parameters", {}))
                        
        logger.info(f"Found {len(handoff_parameters)} unanalyzed handoffs for {agent_name}")
        return handoff_parameters
        
    except Exception as e:
        logger.error(f"Error getting unanalyzed handoffs for {agent_name}: {str(e)}")
        return []

def mark_handoffs_as_analyzed(state: MainState, agent_name: str) -> MainState:
    """
    Mark all handoffs for a specific agent as analyzed in node_history
    """
    try:
        if "node_history" not in state or not state["node_history"]:
            logger.info(f"No node_history found for {agent_name}")
            return state

        for entry in state["node_history"]:
            if (
                isinstance(entry.get("content"), dict) and
                "agents" in entry["content"]
            ):
                for agent in entry["content"]["agents"]:
                    if (
                        #get "agent_name" or "agent"    
                        (agent.get("agent_name") == agent_name or agent.get("agent") == agent_name) and
                        not agent.get("analyzed")
                    ):
                        agent["analyzed"] = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "analyzed_by": agent_name
                        }
                        logger.info(f"Marked handoff as analyzed for {agent_name}")
                        
        return state
        
    except Exception as e:
        logger.error(f"Error marking handoffs as analyzed for {agent_name}: {str(e)}")
        return state