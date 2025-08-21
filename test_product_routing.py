#!/usr/bin/env python3
"""
Test script to verify product recommendation routing is working correctly.
"""

def test_workflow_router_import():
    """Test that WorkflowRouter can be imported without syntax errors."""
    try:
        from src.agent.workflow_router import WorkflowRouter
        print("✅ WorkflowRouter imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import WorkflowRouter: {e}")
        return False

def test_product_intent_detection():
    """Test that product recommendation intents are detected correctly."""
    try:
        from src.agent.workflow_router import WorkflowRouter
        
        router = WorkflowRouter()
        
        # Test weight loss query
        weight_loss_query = "i want to lose weight"
        intent_info = router.detect_intent(weight_loss_query, {}, "")
        
        print(f"Query: '{weight_loss_query}'")
        print(f"Detected intent: {intent_info['intent']}")
        print(f"Entities: {intent_info['entities']}")
        
        if intent_info['intent'] == 'product_recommendation':
            print("✅ Product recommendation intent detected correctly")
            return True
        else:
            print(f"❌ Expected 'product_recommendation' intent, got '{intent_info['intent']}'")
            return False
            
    except Exception as e:
        print(f"❌ Error testing product intent detection: {e}")
        return False

def test_workflow_import():
    """Test that the workflow can be imported."""
    try:
        from src.agent.workflow import AgentWorkflow
        print("✅ AgentWorkflow imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import AgentWorkflow: {e}")
        return False

def test_workflow_nodes_import():
    """Test that workflow nodes can be imported."""
    try:
        from src.agent.workflow_nodes import retrieve_context, generate_answer
        print("✅ Workflow nodes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import workflow nodes: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Product Recommendation Routing...\n")
    
    tests = [
        ("WorkflowRouter Import", test_workflow_router_import),
        ("Product Intent Detection", test_product_intent_detection),
        ("Workflow Import", test_workflow_import),
        ("Workflow Nodes Import", test_workflow_nodes_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Product recommendation routing should work correctly.")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
