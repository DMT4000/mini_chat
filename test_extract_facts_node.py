#!/usr/bin/env python3
"""
Test script for the ExtractFactsNode implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent_state import create_initial_state
from src.agent.workflow_nodes import retrieve_context, generate_answer, extract_facts

def test_extract_facts_node():
    """Test the extract_facts node functionality."""
    print("🧪 Testing ExtractFactsNode...")
    
    # Create initial state with a question that should generate extractable facts
    test_user_id = "test_user_extract_facts"
    test_question = "I'm planning to start a tech consulting LLC in California and I prefer detailed explanations."
    
    initial_state = create_initial_state(test_user_id, test_question)
    print(f"✅ Created initial state for user: {test_user_id}")
    
    try:
        # First retrieve context
        context_state = retrieve_context(initial_state)
        print("✅ Context retrieved successfully")
        
        # Then generate answer
        answer_state = generate_answer(context_state)
        print("✅ Answer generated successfully")
        
        # Test extract_facts node
        final_state = extract_facts(answer_state)
        
        # Verify state was updated correctly
        assert 'newly_extracted_facts' in final_state
        assert isinstance(final_state['newly_extracted_facts'], dict)
        
        print(f"✅ ExtractFactsNode completed successfully")
        print(f"   - Facts extracted: {len(final_state['newly_extracted_facts'])} items")
        
        # Print extracted facts if any
        if final_state['newly_extracted_facts']:
            print("   - Extracted facts:")
            for key, value in final_state['newly_extracted_facts'].items():
                print(f"     * {key}: {value}")
        else:
            print("   - No facts were extracted from this conversation")
        
        # Verify other state fields are preserved
        assert final_state['user_id'] == test_user_id
        assert final_state['question'] == test_question
        assert 'answer' in final_state
        assert len(final_state['answer']) > 0
        
        return True
        
    except Exception as e:
        print(f"❌ ExtractFactsNode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extract_facts_with_existing_memory():
    """Test extract_facts with existing user memory."""
    print("\n🧪 Testing ExtractFactsNode with existing memory...")
    
    # Create state with existing user facts
    test_user_id = "test_user_extract_facts_existing"
    test_question = "I'm also interested in forming a corporation instead, and I'm located in Texas."
    
    initial_state = create_initial_state(test_user_id, test_question)
    
    # Add some existing facts to simulate existing memory
    initial_state['user_facts'] = {
        "business_type": "LLC",
        "state": "California",
        "industry": "tech consulting"
    }
    
    print(f"✅ Created state with existing facts for user: {test_user_id}")
    
    try:
        # Generate a simple answer for testing
        initial_state['answer'] = "A corporation offers different benefits than an LLC, including potential tax advantages and easier access to investment. In Texas, you'll need to file Articles of Incorporation with the Texas Secretary of State."
        
        # Test extract_facts node
        final_state = extract_facts(initial_state)
        
        print(f"✅ ExtractFactsNode with existing memory completed")
        print(f"   - New facts extracted: {len(final_state['newly_extracted_facts'])} items")
        
        if final_state['newly_extracted_facts']:
            print("   - New extracted facts:")
            for key, value in final_state['newly_extracted_facts'].items():
                print(f"     * {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ ExtractFactsNode with existing memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_extract_facts_node()
    success2 = test_extract_facts_with_existing_memory()
    
    if success1 and success2:
        print("\n🎉 All ExtractFactsNode tests passed!")
    else:
        print("\n💥 Some ExtractFactsNode tests failed!")
        sys.exit(1)