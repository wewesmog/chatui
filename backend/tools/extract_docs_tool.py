from typing import Dict, Any
from datetime import datetime, timezone
import json
import uuid
import os
from backend.shared_services.shared_types import MainState
from backend.shared_services.logger_setup import setup_logger
from backend.shared_services.handoff_parameters import get_unanalyzed_handoffs, mark_handoffs_as_analyzed
from backend.shared_services.handoffs import handoff_to_answer_user, handoff_to_welcome_user

logger = setup_logger()

def load_documents(relevant_docs: list) -> dict:
    """ 
    Load specified documents from the parsed directory
    """
    docs = {}
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parsed")  # Go up one level to backend
    
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
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parsed")  # Go up one level to backend
    
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

def extract_docs_tool(state: MainState) -> MainState:
    """
    Tool that verifies document paths and returns relevant directory or file paths
    """
    try:
        last_node = state["node_history"][-1]
        params = last_node.get("content", {}).get("parameters", {})
        query = params.get("query", "")
        
        # Base path for documents
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parsed")
        
        # You might have different folders for different document types
        relevant_paths = {
            "docs_path": "parsed",  # Relative path from backend
            "specific_files": []    # If you want to point to specific files
        }
        
        return handoff_to_answer_user(
            state,
            query=query,
            doc_paths=relevant_paths
        )

    except Exception as e:
        logger.error(f"Error in extract_docs_tool: {str(e)}")
        return handoff_to_welcome_user(
            state,
            f"Error accessing documents: {str(e)}",
            str(uuid.uuid4()),
            "extract_docs_tool"
        )

