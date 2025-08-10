#!/usr/bin/env python3
"""
Test script for the SaveFactsNode implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent_state import create_initial_state, update_state_field
from src.agent.workflow_nodes import save_facts
from src.memory.redis_memory_manager import RedisMemoryManager

def test_save_facts_node():
    """Test the save_facts node functionality."""
    print("🧪 Testing SaveFactsNode...")
    
    # Create initial state
    test_user_id = "test_user_save_facts"
    test_question = "I'm planning to start a tech consulting LLC in California."
    test_answer = "Great! I can help you with forming an LLC in California. Here are the key steps..."
    
    initial_state = create_initial_state(test_user_id, test_question)
    
    # Add some extracted facts to save
    extracted_facts = {
        "business_type": "tech consulting",
        "business_structure": "LLC",
        "state": "California",
        "communication_preference": "detailed explanations"
    }
    
    # Update state with answer and extracted facts
    state_with_answer = update_state_field(initial_state, 'answer', test_answer)
    state_with_facts = update_state_field(state_with_answer, 'newly_extracted_facts', extracted_facts)
    
    print(f"✅ Created state with {len(extracted_facts)} facts to save")
    
    try:
        # Test save_facts node
        final_state = save_facts(state_with_facts)
        
        # Verify state was updated correctly
        assert 'conversation_history' in final_state
        assert isinstance(final_state['conversation_history'], list)
        assert len(final_state['conversation_history']) > 0
        
        # Check that conversation history was updated
        last_entry = final_state['conversation_history'][-1]
        assert last_entry['role'] == 'assistant'
        assert last_entry['content'] == test_answer
        assert 'facts_extracted' in last_entry
        assert last_entry['facts_extracted'] == extracted_facts
        
        print(f"✅ SaveFactsNode completed successfully")
        print(f"   - Conversation history entries: {len(final_state['conversation_history'])}")
        print(f"   - Facts in last entry: {len(last_entry['facts_extracted'])} items")
        
        # Verify facts were saved to Redis
        memory_manager = RedisMemoryManager()
        saved_memory = memory_manager.get_user_memory(test_user_id)
        
        print(f"   - Facts saved to Redis: {len(saved_memory)} items")
        if saved_memory:
            print("   - Saved facts:")
            for key, value in saved_memory.items():
                print(f"     * {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ SaveFactsNode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_save_facts_with_existing_memory():
    """Test save_facts with existing user memory and conflict resolution."""
    print("\n🧪 Testing SaveFactsNode with existing memory and conflicts...")
    
    test_user_id = "test_user_save_facts_conflict"
    test_question = "Actually, I want to form a corporation in Texas instead."
    test_answer = "I understand you want to switch to forming a corporation in Texas. Here's what you need to know..."
    
    # Set up existing memory
    memory_manager = RedisMemoryManager()
    existing_memory = {
        "business_type": "tech consulting",
        "business_structure": "LLC",
        "state": "California"
    }
    memory_manager.save_user_memory(test_user_id, existing_memory)
    print("✅ Set up existing memory with potential conflicts")
    
    # Create state with conflicting facts
    initial_state = create_initial_state(test_user_id, test_question)
    initial_state['user_facts'] = existing_memory
    
    conflicting_facts = {
        "business_structure": "corporation",  # Conflicts with existing "LLC"
        "state": "Texas",  # Conflicts with existing "California"
        "industry": "technology"  # New fact, no conflict
    }
    
    state_with_answer = update_state_field(initial_state, 'answer', test_answer)
    state_with_facts = update_state_field(state_with_answer, 'newly_extracted_facts', conflicting_facts)
    
    try:
        # Test save_facts node with conflicts
        final_state = save_facts(state_with_facts)
        
        print("✅ SaveFactsNode with conflicts completed")
        
        # Verify facts were merged with conflict resolution
        updated_memory = memory_manager.get_user_memory(test_user_id)
        
        print(f"   - Updated memory has {len(updated_memory)} items")
        print("   - Final memory state:")
        for key, value in updated_memory.items():
            print(f"     * {key}: {value}")
        
        # Verify conflicts were resolved (new values should win)
        assert updated_memory["business_structure"] == "corporation"
        assert updated_memory["state"] == "Texas"
        assert updated_memory["industry"] == "technology"
        assert updated_memory["business_type"] == "tech consulting"  # Should be preserved
        
        print("✅ Conflict resolution worked correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ SaveFactsNode conflict test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_save_facts_no_new_facts():
    """Test save_facts when there are no new facts to save."""
    print("\n🧪 Testing SaveFactsNode with no new facts...")
    
    test_user_id = "test_user_save_no_facts"
    test_question = "What's the weather like?"
    test_answer = "I don't have access to current weather information."
    
    initial_state = create_initial_state(test_user_id, test_question)
    state_with_answer = update_state_field(initial_state, 'answer', test_answer)
    # newly_extracted_facts remains empty {}
    
    try:
        # Test save_facts node with no facts
        final_state = save_facts(state_with_answer)
        
        print("✅ SaveFactsNode with no facts completed")
        print("   - No facts were saved (as expected)")
        
        # State should be unchanged since no facts to save
        assert final_state['newly_extracted_facts'] == {}
        
        return True
        
    except Exception as e:
        print(f"❌ SaveFactsNode no facts test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_save_facts_node()
    success2 = test_save_facts_with_existing_memory()
    success3 = test_save_facts_no_new_facts()
    
    if success1 and success2 and success3:
        print("\n🎉 All SaveFactsNode tests passed!")
    else:
        print("\n💥 Some SaveFactsNode tests failed!")
        sys.exit(1)