from typing import Dict, Any
from datetime import datetime, timezone
import json
import uuid
from backend.shared_services.llm import call_llm_api, call_llm_api_openrouter
from backend.shared_services.shared_types import MainState
from backend.shared_services.extract_and_parse_json import extract_and_parse_json
from backend.shared_services.logger_setup import setup_logger

from backend.shared_services.handoff_parameters import get_unanalyzed_handoffs, mark_handoffs_as_analyzed
from backend.shared_services.handoffs import handoff_to_answer_user, handoff_to_welcome_user

import logging

logger = logging.getLogger(__name__)

async def welcome_user(state: MainState) -> MainState:
    """
    Welcome user agent that autonomously decides how to handle user queries.
    Can be triggered directly by user input or through handoffs from other agents/tools.
    """
    try:
        response_id = str(uuid.uuid4())
        user_input = state.get('user_input', '')
        conversation_history = state.get('conversation_history', [])
        available_docs = state.get('available_docs', [])

        # Check for handoffs from other agents/tools
        handoff_parameters = get_unanalyzed_handoffs(state, "welcome_user")
        
        # If there are handoff parameters, use them to enhance context
        handoff_context = ""
        if handoff_parameters:
            latest_params = handoff_parameters[-1]
            error_context = latest_params.get("context", "")
            previous_attempt = latest_params.get("previous_attempt", "")
            handoff_context = f"""
Previous Attempt: {previous_attempt}
Error Context: {error_context}
"""
            state = mark_handoffs_as_analyzed(state, "welcome_user")
        
        if not user_input:
            return handoff_to_welcome_user(
                state, 
                "No user input provided", 
                response_id,
                "welcome_user"
            )

        # Keep the original prompt as is
        prompt = f"""
You are Simba, KCB Bank's dedicated product information assistant for Staff. You are fully autonomous in deciding how to handle queries.

REMEMBER:
- You are communicating with staff at KCB Bank, not customers.
- Do not refer the user to check on website or visit the website.
- Instead of telling users to visit the website, guide them on follow up questions that will help them get the information they need.
- Talk to staff from the point of view of a staff member at KCB Bank.

Current User Query: {user_input}

Current Conversation History: {conversation_history}

Relevant Past Interactions: {state.get('past_history', [])}

Available Documentation: {len(available_docs) > 0}  # Changed to boolean check

{handoff_context if handoff_parameters else ""}

DECISION MAKING PROCESS:

1. First, analyze the context:
   a) Check if internal documentation is available
   b) If no internal docs available, use web search
   c) Consider query type and requirements
   d) Review any error contexts from handoffs

2. For queries about KCB Bank products/services:
   - If internal docs are available, use extract_docs_tool
   - If no internal docs, use tavily_tool for web search
   - Consider previous attempts and errors
   - Break down complex queries if needed

3. Direct answers on information that is already available in the conversation history
   - If the user asks about a topic that has already been discussed, provide a direct answer.
   - Use the information in the conversation history to answer the user's question.
   - Ensure you state the sources that were used to answer the question.

3. For general banking inquiries:
   - Use tavily_tool to get accurate, up-to-date information
   - Ensure search queries are well-formed
   - Consider regulatory and compliance aspects

4. For chitchat or unrelated topics, or unundestandable queries, or jargon:
   - Hand off directly to respond_to_human
   - No need for research or documentation

5. For error recovery (when handed off from other agents):
   - Understand what went wrong in previous attempt
   - Try alternative approaches
   - Consider simplifying complex queries
   - May need to request clarification from user
   - Do not retry many times, you can tell the customer that the response in unavailable

AVAILABLE ACTIONS:

1. Search Internal Documents:
{{
    "response_type": "tool_call",
    "tools": [
        {{
            "tool": "extract_docs_tool",
            "parameters": {{
                "query": "specific search query",
                "relevant_docs": ["doc1.txt", "doc2.txt"],  // Optional
                "comprehensive_question": "expanded version of query"
            }}
        }}
    ]
}}

2. Search Web:
{{
    "response_type": "tool_call",
    "tools": [
        {{
            "tool": "tavily_tool",
            "parameters": {{
                "query": "refined search query for web search, should be a question that can be answered by the web search/content",
              
            }}
        }}
    ]
}}

3. Hand off to Agents:
{{
    "response_type": "handoff",
    "agents": [
        {{
            "agent": "answer_user",  # Changed from agent_name to agent
            "parameters": {{
                "query": "original or refined query",
                "context": "why you're making this handoff",
                "comprehensive_question": "expanded version of query if needed",
                "query_type": "product|general_banking|chitchat",
                "requires_research": "true|false"
            }}
        }}
    ]
}}

Example for direct user response:
{{
    "response_type": "handoff",
    "agents": [
        {{
            "agent": "respond_to_human",  # Changed from agent_name to agent
            "parameters": {{
                "message_to_user": "Your message here",
                "follow_up_questions": ["question 1", "question 2"],
                "sources": ["source 1", "source 2"]
            }}
        }}
    ]
}}

GUIDELINES:

1. For Product Queries:
   - Account types, loans, credit cards, etc.
   - Always check internal docs first
   - Use web search only if internal docs insufficient
   - Consider previous failed attempts

2. For General Banking:
   - Industry practices, regulations, terminology
   - Use web search for current information
   - Ensure sources are reliable

3. For Chitchat:
   - Greetings, personal questions, unrelated topics
   - Hand off directly to respond_to_human
   - No need for research

4. For Error Recovery:
   - Analyze previous error context
   - Try different approach than previous attempt
   - May need to simplify or break down query
   - Consider asking for clarification

5. Query Refinement:
   - Expand unclear queries
   - Break down complex questions
   - Add relevant context
   - Consider previous failed attempts

6. Guidelines for Tavily query:
   - Craft a query whose results can answer the user's intent i.e user_input & comprehensive_query.
   - Tavily will do a web search based on the query
    Example:
    User Input: "What are the benefits of a savings account?"
    Comprehensive Query: "What are the benefits of a savings account?"
    Tavily Query: "benefits of savings account"

Choose the most efficient path to provide accurate, helpful information while prioritizing internal documentation for product-specific queries. If handling an error case, ensure you try a different approach than what previously failed.

IMPORTANT NOTE:
- Only use extract_docs_tool if available_docs is True
- Default to tavily_tool if no internal docs are available
- For product queries without docs, use tavily_tool with specific KCB focus
"""

        messages = [
            {
                "role": "system",
                "content": "You are Simba, KCB Bank's autonomous AI assistant. Make independent decisions about query handling."
            },
            {"role": "user", "content": prompt},
            {
                "role": "system",
                "content": "Always respond in the specified JSON format. Prioritize internal documentation for product queries. Include source in message_to_user"
            }
        ]

        llm_response = await call_llm_api(messages)
        parsed_response = extract_and_parse_json(llm_response)

        print(f"Welcome User Parsed Response: {json.dumps(parsed_response, indent=2)}")
        
        if not parsed_response:
            logger.error("Failed to parse LLM response")
            raise ValueError("Failed to parse LLM response")

        # Add response to node_history
        state["node_history"].append({
            "role": "AI_AGENT",
            "node": "welcome_user",
            "conversation_id": state["conversation_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_id": response_id,
            "content": parsed_response
        })

        

        return state

    except Exception as e:
        logger.error(f"Error in welcome_user: {str(e)}", exc_info=True)
        raise



