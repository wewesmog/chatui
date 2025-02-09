   # shared_types.py
from typing import TypedDict

class MainState(TypedDict):
    user_id: str
    session_id: str
    conversation_id: str
    user_input: str
    conversation_history: list
    node_history: list
    document_history: list
    strategy_history: list
    reflection_history: list
    requirements_history: list
    structure_history: list
    research_history: list
    
