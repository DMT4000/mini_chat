"""
Agent state schema for LangGraph workflow.

This module defines the AgentState TypedDict that maintains state throughout
the agent workflow, including user context, conversation data, and extracted facts.
"""

from typing import TypedDict, List, Dict, Any, Optional
import json
from datetime import datetime


class AgentState(TypedDict):
    """
    State schema for the LangGraph agent workflow.
    
    This TypedDict defines all the fields that are passed between workflow nodes
    and maintained throughout the agent execution.
    """
    user_id: str
    question: str
    user_facts: dict
    retrieved_docs: List[str]
    answer: str
    newly_extracted_facts: dict
    conversation_history: List[dict]
    # Phase 4 additions for conditional workflow
    command_type: str  # "question", "memory_command", "system"
    question_type: str  # "simple", "complex", "greeting"
    confidence_scores: dict  # fact_id -> confidence_score mapping
    # Intent understanding
    intent: str
    entities: Dict[str, Any]
    needs_clarification: bool


def validate_agent_state(state: Dict[str, Any]) -> bool:
    """
    Validate that a state dictionary conforms to the AgentState schema.
    
    Args:
        state: Dictionary to validate
        
    Returns:
        bool: True if state is valid, False otherwise
    """
    required_fields = {
        'user_id': str,
        'question': str,
        'user_facts': dict,
        'retrieved_docs': list,
        'answer': str,
        'newly_extracted_facts': dict,
        'conversation_history': list,
        'command_type': str,
        'question_type': str,
        'confidence_scores': dict
    }
    
    # Check all required fields are present
    for field, expected_type in required_fields.items():
        if field not in state:
            return False
        if not isinstance(state[field], expected_type):
            return False
    
    # Validate conversation_history structure
    if state['conversation_history']:
        for entry in state['conversation_history']:
            if not isinstance(entry, dict):
                return False
    
    return True


def create_initial_state(user_id: str, question: str) -> AgentState:
    """
    Create an initial AgentState with default values.
    
    Args:
        user_id: Unique identifier for the user
        question: User's question to process
        
    Returns:
        AgentState: Initial state with default values
    """
    return AgentState(
        user_id=user_id,
        question=question,
        user_facts={},
        retrieved_docs=[],
        answer="",
        newly_extracted_facts={},
        conversation_history=[],
        command_type="question",
        question_type="complex",
        confidence_scores={},
        intent="",
        entities={},
        needs_clarification=False
    )


def serialize_state_for_debug(state: AgentState) -> str:
    """
    Serialize AgentState to JSON string for debugging purposes.
    
    Args:
        state: AgentState to serialize
        
    Returns:
        str: JSON representation of the state
    """
    # Create a copy for serialization to avoid modifying original
    serializable_state = dict(state)
    
    # Add timestamp for debugging
    serializable_state['_debug_timestamp'] = datetime.now().isoformat()
    
    try:
        return json.dumps(serializable_state, indent=2, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        return f"Error serializing state: {str(e)}"


def deserialize_state_from_debug(json_str: str) -> Optional[AgentState]:
    """
    Deserialize AgentState from JSON string (for debugging).
    
    Args:
        json_str: JSON string representation of state
        
    Returns:
        Optional[AgentState]: Deserialized state or None if invalid
    """
    try:
        data = json.loads(json_str)
        
        # Remove debug timestamp if present
        data.pop('_debug_timestamp', None)
        
        # Validate the structure
        if validate_agent_state(data):
            return AgentState(**data)
        else:
            return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def update_state_field(state: AgentState, field: str, value: Any) -> AgentState:
    """
    Update a specific field in the AgentState.
    
    Args:
        state: Current AgentState
        field: Field name to update
        value: New value for the field
        
    Returns:
        AgentState: Updated state
    """
    updated_state = dict(state)
    updated_state[field] = value
    return AgentState(**updated_state)


def merge_user_facts(state: AgentState, new_facts: Dict[str, Any]) -> AgentState:
    """
    Merge new facts into the existing user_facts in the state.
    
    Args:
        state: Current AgentState
        new_facts: New facts to merge
        
    Returns:
        AgentState: State with merged facts
    """
    updated_facts = dict(state['user_facts'])
    updated_facts.update(new_facts)
    
    return update_state_field(state, 'user_facts', updated_facts)


def add_conversation_entry(state: AgentState, role: str, content: str, 
                          facts_extracted: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    Add a new entry to the conversation history.
    
    Args:
        state: Current AgentState
        role: Role of the message sender ('user' or 'assistant')
        content: Message content
        facts_extracted: Optional facts extracted from this message
        
    Returns:
        AgentState: State with updated conversation history
    """
    new_entry = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'facts_extracted': facts_extracted or {}
    }
    
    updated_history = list(state['conversation_history'])
    updated_history.append(new_entry)
    
    return update_state_field(state, 'conversation_history', updated_history)