"""
Test module for agent state functionality.

This module provides basic tests to verify the AgentState schema,
validation, and utility functions work correctly.
"""

import pytest
from typing import Dict, Any
from .agent_state import (
    AgentState, 
    validate_agent_state, 
    create_initial_state,
    serialize_state_for_debug,
    deserialize_state_from_debug,
    update_state_field,
    merge_user_facts,
    add_conversation_entry
)


def test_create_initial_state():
    """Test creating an initial AgentState with default values."""
    user_id = "test_user_123"
    question = "What are the requirements for forming an LLC?"
    
    state = create_initial_state(user_id, question)
    
    assert state['user_id'] == user_id
    assert state['question'] == question
    assert state['user_facts'] == {}
    assert state['retrieved_docs'] == []
    assert state['answer'] == ""
    assert state['newly_extracted_facts'] == {}
    assert state['conversation_history'] == []


def test_validate_agent_state_valid():
    """Test validation with a valid AgentState."""
    valid_state = {
        'user_id': 'test_user',
        'question': 'test question',
        'user_facts': {'business_type': 'LLC'},
        'retrieved_docs': ['doc1', 'doc2'],
        'answer': 'test answer',
        'newly_extracted_facts': {'state': 'CA'},
        'conversation_history': [{'role': 'user', 'content': 'hello'}]
    }
    
    assert validate_agent_state(valid_state) == True


def test_validate_agent_state_missing_field():
    """Test validation with missing required field."""
    invalid_state = {
        'user_id': 'test_user',
        'question': 'test question',
        # Missing other required fields
    }
    
    assert validate_agent_state(invalid_state) == False


def test_validate_agent_state_wrong_type():
    """Test validation with wrong field type."""
    invalid_state = {
        'user_id': 'test_user',
        'question': 'test question',
        'user_facts': 'should_be_dict',  # Wrong type
        'retrieved_docs': [],
        'answer': '',
        'newly_extracted_facts': {},
        'conversation_history': []
    }
    
    assert validate_agent_state(invalid_state) == False


def test_serialize_deserialize_state():
    """Test state serialization and deserialization for debugging."""
    original_state = create_initial_state("test_user", "test question")
    
    # Serialize
    json_str = serialize_state_for_debug(original_state)
    assert isinstance(json_str, str)
    assert "test_user" in json_str
    assert "test question" in json_str
    
    # Deserialize
    deserialized_state = deserialize_state_from_debug(json_str)
    assert deserialized_state is not None
    assert deserialized_state['user_id'] == original_state['user_id']
    assert deserialized_state['question'] == original_state['question']


def test_update_state_field():
    """Test updating a specific field in the state."""
    state = create_initial_state("test_user", "test question")
    
    updated_state = update_state_field(state, 'answer', 'This is the answer')
    
    assert updated_state['answer'] == 'This is the answer'
    assert updated_state['user_id'] == state['user_id']  # Other fields unchanged


def test_merge_user_facts():
    """Test merging new facts into existing user facts."""
    state = create_initial_state("test_user", "test question")
    state = update_state_field(state, 'user_facts', {'business_type': 'LLC'})
    
    new_facts = {'state': 'CA', 'industry': 'tech'}
    updated_state = merge_user_facts(state, new_facts)
    
    expected_facts = {'business_type': 'LLC', 'state': 'CA', 'industry': 'tech'}
    assert updated_state['user_facts'] == expected_facts


def test_add_conversation_entry():
    """Test adding entries to conversation history."""
    state = create_initial_state("test_user", "test question")
    
    # Add user message
    state = add_conversation_entry(state, 'user', 'Hello, I need help with LLC formation')
    
    # Add assistant message with extracted facts
    facts = {'business_type': 'LLC', 'state': 'unknown'}
    state = add_conversation_entry(state, 'assistant', 'I can help you with that', facts)
    
    assert len(state['conversation_history']) == 2
    assert state['conversation_history'][0]['role'] == 'user'
    assert state['conversation_history'][1]['role'] == 'assistant'
    assert state['conversation_history'][1]['facts_extracted'] == facts


if __name__ == "__main__":
    # Run basic tests
    test_create_initial_state()
    test_validate_agent_state_valid()
    test_validate_agent_state_missing_field()
    test_validate_agent_state_wrong_type()
    test_serialize_deserialize_state()
    test_update_state_field()
    test_merge_user_facts()
    test_add_conversation_entry()
    
    print("All agent state tests passed!")