#!/usr/bin/env python3
"""
Test script for the RetrieveContextNode implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent_state import create_initial_state
from src.agent.workflow_nodes import retrieve_context

def test_retrieve_context_node():
    """Test the retrieve_context node functionality."""
    print("🧪 Testing RetrieveContextNode...")
    
    # Create initial state
    test_user_id = "test_user_retrieve_context"
    test_question = "What are the requirements for forming an LLC in California?"
    
    initial_state = create_initial_state(test_user_id, test_question)
    print(f"✅ Created initial state for user: {test_user_id}")
    
    # Test retrieve_context node
    try:
        updated_state = retrieve_context(initial_state)
        
        # Verify state was updated correctly
        assert 'user_facts' in updated_state
        assert 'retrieved_docs' in updated_state
        assert isinstance(updated_state['user_facts'], dict)
        assert isinstance(updated_state['retrieved_docs'], list)
        
        print(f"✅ RetrieveContextNode completed successfully")
        print(f"   - User facts retrieved: {len(updated_state['user_facts'])} items")
        print(f"   - Documents retrieved: {len(updated_state['retrieved_docs'])} items")
        
        # Print some details if available
        if updated_state['user_facts']:
            print(f"   - Sample user facts: {list(updated_state['user_facts'].keys())[:3]}")
        
        if updated_state['retrieved_docs']:
            print(f"   - First document preview: {updated_state['retrieved_docs'][0][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ RetrieveContextNode test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_retrieve_context_node()
    if success:
        print("\n🎉 RetrieveContextNode test passed!")
    else:
        print("\n💥 RetrieveContextNode test failed!")
        sys.exit(1)