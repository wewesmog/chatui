from typing import Dict, Any
from datetime import datetime, timezone
import json
import uuid
import os
from backend.shared_services.llm import call_llm_api, call_llm_api_openrouter, call_llm_api_ollama
from backend.shared_services.shared_types import MainState
from backend.shared_services.extract_and_parse_json import extract_and_parse_json
from backend.shared_services.logger_setup import setup_logger
from backend.shared_services.handoff_parameters import get_unanalyzed_handoffs, mark_handoffs_as_analyzed


logger = setup_logger()

def load_documents(relevant_docs: list) -> dict:
    """ 
    Load specified documents from the parsed directory
    """
    docs = {}
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "document_processing", "parsed")  # Go up one level to backend, then into document_processing
    
    try:
        logger.info(f"Looking for documents in: {docs_path}")
        if not os.path.exists(docs_path):
            logger.error(f"Parsed directory not found at: {docs_path}")
            return {}
            
        for doc_name in relevant_docs:
            file_path = os.path.join(docs_path, doc_name)
            logger.info(f"Attempting to load document from: {file_path}")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    docs[doc_name] = file.read()
                    logger.info(f"Successfully loaded document: {doc_name}")
            else:
                logger.warning(f"Document not found: {file_path}")
        return docs
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        return {}

def load_all_documents() -> dict:
    """
    Load all documents from the parsed directory
    """
    docs = {}
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "document_processing", "parsed")  # Go up one level to backend, then into document_processing
    
    try:
        logger.info(f"Looking for all documents in: {docs_path}")
        if not os.path.exists(docs_path):
            logger.error(f"Parsed directory not found at: {docs_path}")
            return {}
            
        files_found = os.listdir(docs_path)
        logger.info(f"Files found in directory: {files_found}")
        
        for filename in files_found:
            if filename.endswith(('.txt', '.md', '.json')):
                file_path = os.path.join(docs_path, filename)
                logger.info(f"Attempting to load document from: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        docs[filename] = file.read()
                        logger.info(f"Successfully loaded document: {filename}")
                except Exception as e:
                    logger.error(f"Error loading file {filename}: {str(e)}")
                    
        if not docs:
            logger.warning(f"No documents loaded from {docs_path}")
        return docs
    except Exception as e:
        logger.error(f"Error loading all documents: {str(e)}")
        return {}

async def answer_user(state: MainState) -> MainState:
    """
    Agent that crafts detailed responses using document paths and/or web results
    """
    try:
        response_id = str(uuid.uuid4())
        user_input = state.get('user_input', '')
        comprehensive_query = state.get('comprehensive_query', '')
        conversation_history = state.get('conversation_history', [])

        handoff_parameters = get_unanalyzed_handoffs(state, "answer_user")
        
        if not handoff_parameters:
            return handoff_to_welcome_user(state, "No content provided", response_id, "answer_user")

        # Get the latest handoff parameters
        latest_handoff = handoff_parameters[-1]
        tavily_content = latest_handoff.get("content", [])
        doc_paths = latest_handoff.get("doc_paths", {})
        
        # Check if we have any content to work with
        if not tavily_content and not doc_paths:
            return handoff_to_welcome_user(
                state,
                "No relevant information found",
                response_id,
                "answer_user"
            )

        prompt = f"""
You are an AI assistant tasked with providing detailed responses using available information.

REMEMBER:
- You are communicating with staff at KCB Bank, not customers.
- Do not refer the user to check on website or visit the website.
- Instead of telling users to visit the website, guide them on follow up questions that will help them get the information they need.
- Talk to staff from the point of view of a staff member at KCB Bank.


Available Information Sources:

{f'''Document Locations:
1. Document Directory: {doc_paths.get('docs_path', 'parsed')}
2. Specific Files: {doc_paths.get('specific_files', [])}
Please read and analyze the content from these locations.''' if doc_paths else ''}

{f'''Web Search Results:
{json.dumps(tavily_content, indent=2)}''' if tavily_content else ''}

Context:
User Query: {user_input}
Conversation History: {conversation_history}
Comprehensive Query: {comprehensive_query}

Your task is to:
1. Read and analyze all available information sources:
   {' - Read documents from the provided paths' if doc_paths else ''}
   {' - Consider web search results' if tavily_content else ''}
2. Craft a comprehensive response that:
   - Directly answers the user's question
   - Provides relevant context and details
   - Maintains accuracy and clarity
   - Uses natural, conversational language
3. Include citations for all sources (both documents and web results)
4. Request clarification if the query is unclear

If you cannot provide a good answer (due to insufficient information, unclear query, or need for clarification), use this format:
{{
    "response_type": "handoff",
    "agents": [
        {{
            "agent_name": "welcome_user",
            "parameters": {{
                "context": "Explain why you couldn't answer",
                "previous_attempt": "Describe what you tried",
                "original_query": "{user_input}"
            }}
        }}
    ]
}}

For successful responses, use this format:
{{
    "response_type": "handoff",
    "agents": [
        {{
            "agent_name": "respond_to_human",
            "parameters": {{
                "message_to_user": "Your detailed response here, ensure to use markdown formatting. Nudge the user to continue with the conversation by suggesting follow-up questions."
                "sources": ["List of sources used (both documents and web results) use exact url or document name/details"],
                "requires_clarification": false,
                "follow_up_questions": "suggested questions for more information  i.e ["Question 1", "Question 2"]"
            }}
        }}
    ]
}}

Example of a successful response:
{{
    "response_type": "handoff",
    "agents": [
        {{
            "agent_name": "respond_to_human",
            "parameters": {{
                "message_to_user": "KCB Bank offers many products like savings accounts, current accounts, fixed deposits, loans, etc. /n/n Do you want to know the benefits of a savings account?",
                "sources": document source or url e.g ["Vooma document.pdf page 3", "Vooma document.pdf page 4", "www.kcb.co.ke/savings-account/"],
                "requires_clarification": false,
                "follow_up_questions": ["What are the benefits of a savings account?", "Can you tell me more about fixed deposits?"]
            }}
        }}
    ]
}}



Guidelines:
1. For Product Information:
   - Prioritize information from internal documents if available
   - Use web results for supplementary details
   - Include specific features, terms, and conditions
   - Mention eligibility criteria if applicable

2. For General Banking Queries:
   - Combine document and web information when available
   - Ensure accuracy of regulatory information
   - Provide context for banking terms
   - Include relevant disclaimers

3. For Process Questions:
   - Detail step-by-step procedures
   - Mention required documentation
   - Include relevant timelines
   - Note any prerequisites

4. For Comparisons:
   - Present information in structured format
   - Highlight key differences
   - Include advantages and limitations
   - Make balanced recommendations

5. For Citations and Grounding:
   - Always include sources as part of "message_to_user"
   - Always cite your sources for every piece of information
   - Use inline citations when mentioning specific details
   - Specify whether information comes from documents or web results
   - If combining information from multiple sources, cite all relevant sources
   - When information conflicts between sources, note the discrepancy
   - If information seems outdated, mention the date/source
   - Don't make claims without supporting evidence

6. For User Engagement and Follow-up:
   - Suggest 2-3 relevant follow-up questions based on the response
   - Highlight areas where user might want more details
   - If mentioning related products/services, suggest questions about them
   - For complex topics, suggest breaking down into smaller questions
   - If user might need clarification, provide example questions
   - For time-sensitive information, suggest updates/verification
   - Guide user towards more detailed information when available

Instructions for Response Format:
1. Start with a warm, direct answer to the user's question
2. Use clear Markdown formatting:
   - **Bold** for important terms and key points
   - *Italics* for emphasis
   - Numbered lists (1., 2., 3.) for steps or sequences
   - Bullet points (•) for features or related items
   - ### Headers for different sections
   - > Blockquotes for important notes or disclaimers
   - Add spacing between sections for readability

3. Structure your response with:
   - A clear introduction
   - Well-organized main points
   - A concise conclusion
   - Sources section at the end (if relevant)

4. Keep the tone professional yet friendly, and ensure information is accurate based on the search results.

"""

        messages = [
            {
                "role": "system", 
                "content": "You are Simba, KCB Bank's dedicated product information assistant. Read from all available sources to provide accurate information."
            },
            {"role": "user", "content": prompt},
            {
                "role": "system", 
                "content": "Please provide your response in the specified JSON format."
            }
        ]

        # Try OpenRouter first, fallback to regular LLM API if it fails
        #llm_response = await call_llm_api_openrouter(messages)
        llm_response = await call_llm_api(messages)
        

        parsed_response = extract_and_parse_json(llm_response)

        print(json.dumps(parsed_response, indent=2))
        if not parsed_response:
            return handoff_to_welcome_user(
                state,
                "Failed to parse response format",
                response_id,
                "answer_user"
            )
        
        # Mark handoffs as analyzed
        state = mark_handoffs_as_analyzed(state, "answer_user")
        
        # Add response to node_history
        state["node_history"].append({
            "role": "AI_AGENT",
            "node": "answer_user",
            "conversation_id": state["conversation_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_id": response_id,
            "content": parsed_response
        })

        return state

    except Exception as e:
        logger.error(f"Error in answer_user: {str(e)}", exc_info=True)
        return handoff_to_welcome_user(
            state,
            f"Error crafting response: {str(e)}",
            response_id,
            "answer_user"
        )

def handoff_to_welcome_user(state: MainState, error_context: str, response_id: str, node: str) -> MainState:
    """
    Helper function to create a welcome_user handoff when errors occur
    """
    state["node_history"].append({
        "role": "AI_AGENT",
        "node": node,
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
                    "previous_attempt": "Document loading failed in answer_user"
                }
            }]
        }
    })
    
    logger.info(f"Handing off to welcome_user due to error: {error_context}")
    return state 