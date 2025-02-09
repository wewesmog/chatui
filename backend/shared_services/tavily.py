import os
from typing import List, Dict, Any
import requests
from backend.shared_services.logger_setup import setup_logger

logger = setup_logger()

def search_tavily(query: str) -> List[Dict[str, Any]]:
    """
    Perform web search using Tavily API
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY not found in environment variables")
        return []

    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "query": query,
        "search_depth": "advanced",
        "include_raw_content": True,
        "include_domains": ["ke.kcbgroup.com"],
        "include_images": False,
        "include_answer": True,
        "max_results": 2
    }

    try:
        response = requests.post(url, headers=headers, json=params)
        response.raise_for_status()
        
        results = response.json()
        if "results" in results:
            logger.info(f"Successfully retrieved {len(results['results'])} results from Tavily")
            return results["results"]
        else:
            logger.warning("No results found in Tavily response")
            return []
            

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Tavily API: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in Tavily search: {str(e)}")
        return [] 