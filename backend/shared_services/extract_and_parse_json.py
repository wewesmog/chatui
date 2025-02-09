import json
import re
from backend.shared_services.logger_setup import setup_logger

logger = setup_logger()

def extract_and_parse_json(text):
    try:
        # Clean the text of any invalid control characters
        cleaned_text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # First try to parse the entire text as JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass

        # Look for JSON-like content
        matches = re.findall(r'({[\s\S]*})', cleaned_text)
        
        for match in matches:
            try:
                # Further clean the JSON string
                cleaned_json = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', match)
                cleaned_json = cleaned_json.replace('\n', '\\n').replace('\r', '\\r')
                
                # Try to parse the cleaned JSON
                parsed_json = json.loads(cleaned_json)
                
                # Validate the expected structure
                if isinstance(parsed_json, dict):
                    if "response_type" in parsed_json or "agent_name" in parsed_json:
                        return parsed_json
                        
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON match: {e}")
                continue
                
        logger.error("No valid JSON found in response")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting JSON: {str(e)}")
        return None
    


# TODO: Add handoff to the agent if JSON fails and tell the agent to try again.  You can set a counter to limit the number of times the agent can try.

