#!/usr/bin/env python3
"""
Test script to verify that the capabilities workflow is working correctly.
This script tests the agent's ability to answer capabilities questions with proper document access.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from agent.agent import Agent
from agent.workflow_nodes import _is_capabilities_question

def test_capabilities_detection():
    """Test that capabilities questions are properly detected."""
    print("🧪 Testing capabilities question detection...")
    
    # Test cases for capabilities questions
    test_questions = [
        "What are your capabilities?",
        "What can you do?",
        "How do you help?",
        "What documents can you see?",
        "What files do you have access to?",
        "Tell me about your features",
        "What are your skills?",
        "How does this work?",
        "What can you help me with?",
        "Do you have access to my documents?",
        "What plans can you read?",
        "Which products do you know about?",
        "Can you see my wellness app plan?",
        "Do you know about my cronograma?",
        "What Fuxion products can you recommend?",
        "How can you assist with business formation?",
        "What is your expertise?",
        "What are you good at?",
        "What do you specialize in?",
        "How do you function?"
    ]
    
    print("\nCapabilities questions detected:")
    for question in test_questions:
        is_cap = _is_capabilities_question(question)
        status = "✅ YES" if is_cap else "❌ NO"
        print(f"  {status}: {question}")
    
    # Test cases for non-capabilities questions
    non_cap_questions = [
        "Hello",
        "How are you?",
        "What is the weather like?",
        "Tell me a joke",
        "What time is it?",
        "My name is John",
        "I need help with weight loss",
        "What supplements should I take?",
        "How do I form an LLC?",
        "What is the deadline for phase 2?"
    ]
    
    print("\nNon-capabilities questions detected:")
    for question in non_cap_questions:
        is_cap = _is_capabilities_question(question)
        status = "❌ YES" if is_cap else "✅ NO"
        print(f"  {status}: {question}")

def test_capabilities_workflow():
    """Test the full capabilities workflow with the agent."""
    print("\n🧪 Testing capabilities workflow...")
    
    try:
        # Initialize the agent
        print("Initializing agent...")
        agent = Agent(enable_debug_logging=True)
        print("✅ Agent initialized successfully")
        
        # Test capabilities question
        test_user_id = "test_capabilities_user"
        capabilities_question = "What are your capabilities? What documents can you access?"
        
        print(f"\nAsking capabilities question: {capabilities_question}")
        print("=" * 80)
        
        # Run the agent
        response = agent.run(test_user_id, capabilities_question)
        
        print("\nAgent Response:")
        print("=" * 80)
        print(response['answer'])
        print("=" * 80)
        
        # Analyze the response
        print(f"\nResponse Analysis:")
        print(f"  - Answer length: {len(response['answer'])} characters")
        print(f"  - Execution time: {response['execution_time']:.2f} seconds")
        print(f"  - Facts extracted: {len(response.get('extracted_facts', {}))}")
        print(f"  - Conversation turn: {response.get('conversation_turn', 'N/A')}")
        
        # Check if the response mentions key capabilities
        answer_lower = response['answer'].lower()
        key_capabilities = [
            'wellness', 'app', 'development', 'plan',
            'cronograma', 'timeline', 'project', 'phase',
            'fuxion', 'product', 'supplement', 'catalog',
            'business', 'formation', 'entrepreneurship',
            'workstream', 'milestone', 'objective'
        ]
        
        print(f"\nCapabilities mentioned in response:")
        for capability in key_capabilities:
            if capability in answer_lower:
                print(f"  ✅ {capability}")
            else:
                print(f"  ❌ {capability}")
        
        # Test a follow-up question
        print(f"\nTesting follow-up question...")
        follow_up = "Tell me more about the wellness app development plan"
        
        print(f"Follow-up question: {follow_up}")
        print("=" * 80)
        
        follow_up_response = agent.run(test_user_id, follow_up)
        
        print("\nFollow-up Response:")
        print("=" * 80)
        print(follow_up_response['answer'])
        print("=" * 80)
        
        print(f"\nFollow-up Analysis:")
        print(f"  - Answer length: {len(follow_up_response['answer'])} characters")
        print(f"  - Execution time: {follow_up_response['execution_time']:.2f} seconds")
        print(f"  - Facts extracted: {len(follow_up_response.get('extracted_facts', {}))}")
        
        print("\n✅ Capabilities workflow test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing capabilities workflow: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function."""
    print("🚀 Starting Capabilities Workflow Test")
    print("=" * 80)
    
    # Test capabilities detection
    test_capabilities_detection()
    
    # Test full workflow
    test_capabilities_workflow()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main()
