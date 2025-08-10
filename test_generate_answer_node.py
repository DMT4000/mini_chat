#!/usr/bin/env python3
"""
Test script for the GenerateAnswerNode implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent_state import create_initial_state
from src.agent.workflow_nodes import retrieve_context, generate_answer

def test_generate_answer_node():
    """Test the generate_answer node functionality."""
    print("🧪 Testing GenerateAnswerNode...")
    
    # Create initial state
    test_user_id = "test_user_generate_answer"
    test_question = "What are the requirements for forming an LLC in California?"
    
    initial_state = create_initial_state(test_user_id, test_question)
    print(f"✅ Created initial state for user: {test_user_id}")
    
    # First retrieve context (prerequisite for generate_answer)
    try:
        context_state = retrieve_context(initial_state)
        print("✅ Context retrieved successfully")
        
        # Test generate_answer node
        final_state = generate_answer(context_state)
        
        # Verify state was updated correctly
        assert 'answer' in final_state
        assert isinstance(final_state['answer'], str)
        assert len(final_state['answer'].strip()) > 0
        
        print(f"✅ GenerateAnswerNode completed successfully")
        print(f"   - Answer length: {len(final_state['answer'])} characters")
        print(f"   - Answer preview: {final_state['answer'][:150]}...")
        
        # Verify other state fields are preserved
        assert final_state['user_id'] == test_user_id
        assert final_state['question'] == test_question
        assert 'user_facts' in final_state
        assert 'retrieved_docs' in final_state
        
        return True
        
    except Exception as e:
        print(f"❌ GenerateAnswerNode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generate_answer_node()
    if success:
        print("\n🎉 GenerateAnswerNode test passed!")
    else:
        print("\n💥 GenerateAnswerNode test failed!")
        sys.exit(1)