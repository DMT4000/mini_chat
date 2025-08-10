#!/usr/bin/env python3
"""
Test script to verify the complete agent workflow implementation.

This script tests:
- Agent workflow creation and compilation
- Agent execution interface
- Error handling and recovery
- Conversation history tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import create_agent, AgentState, create_initial_state


def test_agent_creation():
    """Test agent creation and initialization."""
    print("🧪 Testing agent creation...")
    
    try:
        agent = create_agent(enable_debug_logging=False)
        print("✅ Agent created successfully")
        
        # Test health check
        health = agent.health_check()
        print(f"🏥 Health check: {health['status']}")
        
        # Test workflow info
        workflow_info = agent.get_workflow_info()
        print(f"⚙️ Workflow status: {workflow_info.get('status', 'unknown')}")
        print(f"📊 Workflow nodes: {workflow_info.get('node_count', 0)}")
        
        return agent
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return None


def test_agent_execution(agent):
    """Test agent conversation execution."""
    print("\n🧪 Testing agent execution...")
    
    test_cases = [
        {
            "user_id": "test_user_1",
            "question": "I'm starting an LLC in California. What do I need to know?",
            "expected_keywords": ["LLC", "California"]
        },
        {
            "user_id": "test_user_1", 
            "question": "What about taxes for my business?",
            "expected_keywords": ["tax"]
        },
        {
            "user_id": "test_user_2",
            "question": "How do I get an EIN number?",
            "expected_keywords": ["EIN"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test case {i}: {test_case['question'][:50]}...")
        
        try:
            response = agent.run(
                user_id=test_case['user_id'],
                question=test_case['question']
            )
            
            # Check response structure
            required_fields = ['answer', 'user_id', 'question', 'extracted_facts', 'execution_time']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing response fields: {missing_fields}")
                results.append(False)
                continue
            
            # Check if answer is not empty
            if not response['answer'] or len(response['answer'].strip()) == 0:
                print("❌ Empty answer received")
                results.append(False)
                continue
            
            # Check execution time is reasonable
            if response['execution_time'] > 30:  # 30 seconds max
                print(f"⚠️ Slow execution time: {response['execution_time']:.2f}s")
            
            print(f"✅ Test case {i} passed")
            print(f"   Answer length: {len(response['answer'])} characters")
            print(f"   Execution time: {response['execution_time']:.2f}s")
            print(f"   Extracted facts: {len(response['extracted_facts'])} items")
            
            results.append(True)
            
        except Exception as e:
            print(f"❌ Test case {i} failed: {e}")
            results.append(False)
    
    return results


def test_conversation_history(agent):
    """Test conversation history tracking."""
    print("\n🧪 Testing conversation history...")
    
    user_id = "history_test_user"
    
    try:
        # Have a few conversations
        questions = [
            "I want to start a business in Texas",
            "What type of business structure should I choose?",
            "How much does it cost to file?"
        ]
        
        for question in questions:
            agent.run(user_id=user_id, question=question)
        
        # Check conversation history
        history = agent.get_conversation_history(user_id)
        
        if len(history) != 6:  # 3 questions * 2 messages each (user + assistant)
            print(f"❌ Expected 6 history items, got {len(history)}")
            return False
        
        # Check session info
        session_info = agent.get_session_info(user_id)
        
        if session_info['total_conversation_turns'] != 3:
            print(f"❌ Expected 3 conversation turns, got {session_info['total_conversation_turns']}")
            return False
        
        print("✅ Conversation history test passed")
        print(f"   History items: {len(history)}")
        print(f"   Conversation turns: {session_info['total_conversation_turns']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversation history test failed: {e}")
        return False


def test_error_handling(agent):
    """Test error handling and recovery."""
    print("\n🧪 Testing error handling...")
    
    try:
        # Test with empty question
        try:
            agent.run(user_id="test_user", question="")
            print("❌ Should have failed with empty question")
            return False
        except ValueError:
            print("✅ Correctly handled empty question")
        
        # Test with empty user_id
        try:
            agent.run(user_id="", question="Test question")
            print("❌ Should have failed with empty user_id")
            return False
        except ValueError:
            print("✅ Correctly handled empty user_id")
        
        # Test with very long question (should still work)
        long_question = "What should I know about business formation? " * 100
        response = agent.run(user_id="test_user", question=long_question)
        
        if not response['answer']:
            print("❌ Failed to handle long question")
            return False
        
        print("✅ Successfully handled long question")
        print("✅ Error handling test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Agent Workflow Complete Test")
    print("=" * 50)
    
    # Test 1: Agent creation
    agent = test_agent_creation()
    if not agent:
        print("\n❌ Agent creation failed - stopping tests")
        return False
    
    # Test 2: Agent execution
    execution_results = test_agent_execution(agent)
    execution_success = all(execution_results)
    
    # Test 3: Conversation history
    history_success = test_conversation_history(agent)
    
    # Test 4: Error handling
    error_handling_success = test_error_handling(agent)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Agent Creation: {'✅ PASS' if agent else '❌ FAIL'}")
    print(f"   Agent Execution: {'✅ PASS' if execution_success else '❌ FAIL'} ({sum(execution_results)}/{len(execution_results)})")
    print(f"   Conversation History: {'✅ PASS' if history_success else '❌ FAIL'}")
    print(f"   Error Handling: {'✅ PASS' if error_handling_success else '❌ FAIL'}")
    
    overall_success = agent and execution_success and history_success and error_handling_success
    
    if overall_success:
        print("\n🎉 All tests passed! Agent workflow is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)