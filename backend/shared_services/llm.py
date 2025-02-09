import logging

# Set OpenAI logger to WARNING level at the start of the file
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

from openai import OpenAI
from typing import List, Dict, Any, Optional, AsyncGenerator
import os
from dotenv import load_dotenv
import traceback, requests
import google.generativeai as genai
from openai import AsyncOpenAI
import json

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

logger = logging.getLogger(__name__)

# Initialize the client properly
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://your-site.com",  # Required by OpenRouter
        "X-Title": "KCB-Simba"        # Required by OpenRouter
    }
)





def call_llm_api_gemini(messages):
    try:
        # Configure the API
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        
        # Create model instance
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        # Extract just the text content from the message
        if isinstance(messages, dict):
            content = messages.get('content', '')
        elif isinstance(messages, list):
            # If it's a list of messages, get the last one's content
            content = messages[-1].get('content', '') if messages else ''
        else:
            content = str(messages)
        
        # Generate response
        response = model.generate_content(content)
        
        return response.text
        
    except Exception as e:
        print(f"Error in Gemini API call: {str(e)}")
        return None


# Alternative implementation using OpenRouter
async def call_llm_api_openrouter(messages):
    try:
        response = await openrouter_client.chat.completions.create(
            model="mistral-7b-instruct",  # or your preferred model
            messages=messages,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Extract the actual message content from the response
        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            message_content = response.choices[0].message.content
            logger.info(f"OpenRouter response received: {message_content[:100]}...")  # Log first 100 chars
            return message_content
        else:
            logger.error("OpenRouter response missing expected structure")
            return None
            
    except Exception as e:
        logger.error(f"Error in OpenRouter API call: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return None

def call_llm_api_ollama(messages: List[Dict[str, str]], model="deepseek-r1:7b") -> str:
    """
    Make a call to the Ollama API with properly formatted system and user messages.
    """
    try:
        # Ollama runs on port 11434 by default
        OLLAMA_ENDPOINT = "http://212.56.44.75:11434/api/generate"
        
        # Format messages into a single prompt with clear role separation
        formatted_prompt = ""
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                formatted_prompt += f"[SYSTEM]: {content}\n\n"
            elif role == 'user':
                formatted_prompt += f"[USER]: {content}\n\n"
            elif role == 'assistant':
                formatted_prompt += f"[ASSISTANT]: {content}\n\n"
        
        # Add final instruction to ensure JSON response
        formatted_prompt += "[ASSISTANT]: I will now provide my response in the specified JSON format:\n"

        # Call Ollama API
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": model,
                "prompt": formatted_prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            print(f"Ollama API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error in Ollama API call: {str(e)}")
        return None

async def call_llm_api_stream(messages: list) -> AsyncGenerator[str, None]:
    """
    Stream responses from OpenAI API
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",  # or your preferred model
            messages=messages,
            temperature=0.7,
            stream=True  # Enable streaming
        )

        
        async for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"Error in streaming LLM response: {str(e)}")
        yield f"Error: {str(e)}"

async def call_llm_api(messages: list) -> str:
    """
    Regular non-streaming API call
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",  # or your preferred model
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content or ""
    
    except Exception as e:
        print(f"Error in LLM API call: {str(e)}")
        return f"Error: {str(e)}"