"""
Simple test script for agent state functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agent.agent_state import (
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
    print("✓ test_create_initial_state passed")


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
    print("✓ test_validate_agent_state_valid passed")


def test_validate_agent_state_missing_field():
    """Test validation with missing required field."""
    invalid_state = {
        'user_id': 'test_user',
        'question': 'test question',
        # Missing other required fields
    }
    
    assert validate_agent_state(invalid_state) == False
    print("✓ test_validate_agent_state_missing_field passed")


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
    print("✓ test_serialize_deserialize_state passed")


def test_merge_user_facts():
    """Test merging new facts into existing user facts."""
    state = create_initial_state("test_user", "test question")
    state = update_state_field(state, 'user_facts', {'business_type': 'LLC'})
    
    new_facts = {'state': 'CA', 'industry': 'tech'}
    updated_state = merge_user_facts(state, new_facts)
    
    expected_facts = {'business_type': 'LLC', 'state': 'CA', 'industry': 'tech'}
    assert updated_state['user_facts'] == expected_facts
    print("✓ test_merge_user_facts passed")


if __name__ == "__main__":
    # Run basic tests
    test_create_initial_state()
    test_validate_agent_state_valid()
    test_validate_agent_state_missing_field()
    test_serialize_deserialize_state()
    test_merge_user_facts()
    
    print("\n🎉 All agent state tests passed!")