#!/usr/bin/env python3
"""Test script to verify improved memory management and workflow routing"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.agent import create_agent
from src.agent.workflow_router import WorkflowRouter, is_document_question

def test_workflow_routing():
    """Test the improved workflow routing for different types of questions."""
    print("🔍 Testing improved workflow routing...")
    
    # Test questions that should route to full workflow
    test_questions = [
        # Wellness app related
        "Tell me about the wellness app plan",
        "What are the workstreams?",
        "Show me the wellness app development plan",
        "What are the objectives of the wellness app?",
        "Tell me about the wellness app workstreams",
        "¿Cuáles son los objetivos de la app wellness?",
        
        # Cronograma/timeline related
        "Tell me about the project timeline",
        "What are the phases of the project?",
        "Show me the cronograma",
        "What gates are in the project?",
        "Tell me about the project schedule",
        "¿Cuáles son las fases del proyecto?",
        
        # General document questions
        "What documents do you have access to?",
        "Can you see my files?",
        "Show me the project documents",
        
        # Product questions (should also go to full workflow)
        "What Fuxion products do you recommend?",
        "Tell me about the supplements"
    ]
    
    router = WorkflowRouter()
    
    print(f"\n{'='*80}")
    print("📋 TESTING WORKFLOW ROUTING")
    print(f"{'='*80}")
    
    for question in test_questions:
        print(f"\n🔍 Question: '{question}'")
        
        # Test document question detection
        is_doc = is_document_question(question)
        print(f"   📚 Document question detected: {is_doc}")
        
        # Test question complexity classification
        try:
            complexity = router.classify_question_complexity(question, {})
            print(f"   🎯 Question complexity: {complexity}")
        except Exception as e:
            print(f"   ⚠️ Complexity classification error: {e}")
        
        # Test intent detection
        try:
            intent_info = router.detect_intent(question, {}, "")
            print(f"   🎭 Intent: {intent_info.get('intent', 'unknown')}")
            print(f"   🏷️ Entities: {intent_info.get('entities', {})}")
        except Exception as e:
            print(f"   ⚠️ Intent detection error: {e}")

def test_agent_workflow():
    """Test the full agent workflow with a wellness app question."""
    print(f"\n{'='*80}")
    print("🤖 TESTING FULL AGENT WORKFLOW")
    print(f"{'='*80}")
    
    try:
        print("🔧 Creating agent...")
        agent = create_agent(enable_debug_logging=True)
        
        test_user = "test_memory_workflow_user"
        test_question = "Tell me about the wellness app plan and what workstreams are involved"
        
        print(f"👤 User: {test_user}")
        print(f"❓ Question: {test_question}")
        
        print("\n🚀 Running agent workflow...")
        result = agent.run(test_user, test_question)
        
        print(f"\n✅ Agent workflow completed!")
        print(f"📝 Answer: {result.get('answer', 'No answer')[:500]}...")
        print(f"🧠 Extracted facts: {result.get('extracted_facts', {})}")
        print(f"⏱️ Execution time: {result.get('execution_time', 0):.2f}s")
        
        # Check if the answer contains wellness app related content
        answer = result.get('answer', '').lower()
        wellness_keywords = ['wellness', 'workstream', 'ws', 'plan', 'development', 'objective']
        found_keywords = [kw for kw in wellness_keywords if kw in answer]
        
        if found_keywords:
            print(f"🎯 Found wellness-related keywords: {found_keywords}")
        else:
            print("⚠️ No wellness-related keywords found in answer")
            
    except Exception as e:
        print(f"❌ Agent workflow test failed: {e}")
        import traceback
        traceback.print_exc()

def test_memory_integration():
    """Test that user memory is properly integrated with document retrieval."""
    print(f"\n{'='*80}")
    print("🧠 TESTING MEMORY INTEGRATION")
    print(f"{'='*80}")
    
    try:
        from src.agent.workflow_nodes import _build_retrieval_query, _engineer_context
        
        # Simulate user facts
        user_facts = {
            'name': 'Test User',
            'preferences': {'goal': 'weight loss', 'interest': 'supplements'},
            'project_context': 'wellness app development'
        }
        
        # Simulate conversation history
        conversation_history = [
            {'role': 'user', 'content': 'My name is Test User'},
            {'role': 'assistant', 'content': 'Nice to meet you, Test User!'},
            {'role': 'user', 'content': 'I am working on a wellness app project'}
        ]
        
        question = "What are the workstreams in the wellness app plan?"
        
        print(f"🔍 Question: {question}")
        print(f"👤 User facts: {user_facts}")
        
        # Test retrieval query building
        retrieval_query = _build_retrieval_query(question, user_facts, conversation_history)
        print(f"\n🔍 Built retrieval query: {retrieval_query}")
        
        # Test context engineering
        simulated_docs = [
            "WELLNESS APP DEVELOPMENT PLAN: This document outlines the workstreams and phases...",
            "PROJECT TIMELINE: The project is divided into 4 main phases..."
        ]
        
        engineered_context = _engineer_context(user_facts, simulated_docs, "Recent conversation about wellness app")
        print(f"\n🧠 Engineered context:")
        print(f"   User facts: {engineered_context['user_facts_str'][:200]}...")
        print(f"   Document context: {engineered_context['document_context'][:200]}...")
        print(f"   Conversation context: {engineered_context['conversation_context'][:200]}...")
        
    except Exception as e:
        print(f"❌ Memory integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Improved Memory Management and Workflow")
    print("=" * 80)
    
    try:
        test_workflow_routing()
        test_memory_integration()
        test_agent_workflow()
        
        print(f"\n{'='*80}")
        print("✅ All tests completed!")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
