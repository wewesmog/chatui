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
    Final agent that crafts and streams beautiful, well-structured responses to users.
    """
    try:
        response_id = str(uuid.uuid4())

        # Get ALL unanalyzed handoffs for respond_to_human
        handoff_parameters = get_unanalyzed_handoffs(state, "respond_to_human")
        
        if not handoff_parameters:
            logger.error("No handoff parameters found for respond_to_human")
            return state

        # Prepare the prompt for crafting the final response
        prompt = f"""
You are Simba, KCB Bank's expert communicator. Here are all the handoffs you need to combine into one cohesive response:

{json.dumps(handoff_parameters, indent=2)}

Create a beautiful, engaging response that:
1. Uses clear, professional Markdown formatting
2. Maintains a warm, helpful tone
3. Organizes information logically
4. Highlights key points effectively
5. Makes complex information accessible

Formatting Guidelines:
- Use headers (##) for main sections
- Use bullet points for lists
- Use bold (**) for emphasis
- Use tables for comparisons
- Use blockquotes (>) for important notes/disclaimers
- Use code blocks (```) for steps or procedures
- Include a "Sources" section at the end if sources are provided

Remember to:
- Maintain natural flow between combined messages
- Ensure consistent tone throughout
- Make information easily scannable
- Use appropriate emphasis for key points
- Keep paragraphs concise
"""

        messages = [
            {
                "role": "system",
                "content": "You are Simba, KCB Bank's expert communicator. Create beautiful, engaging responses using Markdown."
            },
            {"role": "user", "content": prompt}
        ]

        # Stream the beautifully formatted response
        response_text = await stream_response_to_user(messages, state["session_id"])
        logger.info(f"Response to user: {response_text}")
        # Mark all handoffs as analyzed
        state = mark_handoffs_as_analyzed(state, "respond_to_human")
        
        # Add response to conversation history
        state["conversation_history"].append({
            "role": "assistant",
            "content": response_text,
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
                "message": response_text
            }
        })

        return state

    except Exception as e:
        logger.error(f"Error in respond_to_human: {str(e)}", exc_info=True)
        return state 