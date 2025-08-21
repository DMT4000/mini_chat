#!/usr/bin/env python3
"""
Test script for the local memory system.

This script demonstrates how the memory system works and tests
various memory operations including remembering user names and preferences.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.memory.local_memory_manager import LocalMemoryManager
from src.chat import ChatPipeline

def test_memory_operations():
    """Test basic memory operations."""
    print("🧠 Testing Local Memory System")
    print("=" * 50)
    
    # Initialize memory manager
    memory_manager = LocalMemoryManager()
    
    # Test user 1: John
    user1_id = "john_doe"
    print(f"\n👤 Testing user: {user1_id}")
    
    # Save initial facts about John
    john_facts = {
        "name": "John Doe",
        "age": 35,
        "occupation": "Software Engineer",
        "interests": ["coding", "fitness", "reading"],
        "preferences": {
            "communication_style": "direct",
            "detail_level": "technical"
        }
    }
    
    print("💾 Saving John's information...")
    memory_manager.save_user_memory(user1_id, john_facts)
    
    # Retrieve and display John's memory
    print("📖 Retrieving John's memory...")
    retrieved_memory = memory_manager.get_user_memory(user1_id)
    print(f"Retrieved facts: {retrieved_memory}")
    
    # Test user 2: Sarah
    user2_id = "sarah_smith"
    print(f"\n👤 Testing user: {user2_id}")
    
    # Save initial facts about Sarah
    sarah_facts = {
        "name": "Sarah Smith",
        "age": 28,
        "occupation": "Marketing Manager",
        "interests": ["yoga", "cooking", "travel"],
        "preferences": {
            "communication_style": "friendly",
            "detail_level": "simple"
        }
    }
    
    print("💾 Saving Sarah's information...")
    memory_manager.save_user_memory(user2_id, sarah_facts)
    
    # Test updating Sarah's memory with new facts
    print("🔄 Updating Sarah's memory with new information...")
    new_sarah_facts = {
        "location": "New York",
        "favorite_color": "blue",
        "preferences": {
            "communication_style": "friendly",
            "detail_level": "simple",
            "response_format": "bullet_points"
        }
    }
    
    memory_manager.update_user_memory(user2_id, new_sarah_facts)
    
    # Retrieve updated memory
    updated_sarah_memory = memory_manager.get_user_memory(user2_id)
    print(f"Updated Sarah's facts: {updated_sarah_memory}")
    
    # Test memory statistics
    print("\n📊 Memory Statistics:")
    stats = memory_manager.get_memory_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test listing users
    print(f"\n👥 All users in memory:")
    users = memory_manager.list_users()
    for user in users:
        print(f"  - {user}")
    
    return True

def test_chat_with_memory():
    """Test the chat pipeline with memory integration."""
    print("\n💬 Testing Chat Pipeline with Memory")
    print("=" * 50)
    
    try:
        # Initialize chat pipeline
        chat_pipeline = ChatPipeline()
        
        # Test user
        test_user_id = "test_user_123"
        
        # Save some test facts
        test_facts = {
            "name": "Alex",
            "business_type": "e-commerce",
            "goals": ["increase sales", "improve customer retention"],
            "preferences": {
                "communication_style": "casual",
                "detail_level": "moderate"
            }
        }
        
        print(f"💾 Saving test facts for user: {test_user_id}")
        chat_pipeline.memory_manager.save_user_memory(test_user_id, test_facts)
        
        # Test a question that should use the stored memory
        test_question = "Hi! Can you remember my name and what I'm trying to achieve?"
        
        print(f"\n❓ Question: {test_question}")
        print("🤖 Getting response...")
        
        response = chat_pipeline.ask(test_question, test_user_id)
        
        print(f"✅ Response received:")
        print(f"Answer: {response['answer']}")
        print(f"User facts used: {response['user_facts_used']}")
        print(f"Documents retrieved: {response['documents_retrieved']}")
        print(f"Query type: {response['query_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing chat pipeline: {e}")
        return False

def test_memory_persistence():
    """Test that memory persists across different instances."""
    print("\n💾 Testing Memory Persistence")
    print("=" * 50)
    
    # Create first memory manager instance
    memory_manager1 = LocalMemoryManager()
    
    # Save some test data
    test_user = "persistence_test_user"
    test_data = {
        "name": "Test User",
        "test_value": "This should persist",
        "timestamp": "2024-01-15"
    }
    
    print(f"💾 Saving data with first instance...")
    memory_manager1.save_user_memory(test_user, test_data)
    
    # Create second memory manager instance
    memory_manager2 = LocalMemoryManager()
    
    # Try to retrieve the data
    print(f"📖 Retrieving data with second instance...")
    retrieved_data = memory_manager2.get_user_memory(test_user)
    
    if retrieved_data and "facts" in retrieved_data:
        facts = retrieved_data["facts"]
        if facts.get("name") == "Test User" and facts.get("test_value") == "This should persist":
            print("✅ Memory persistence test PASSED!")
            return True
        else:
            print("❌ Memory persistence test FAILED - data mismatch")
            return False
    else:
        print("❌ Memory persistence test FAILED - no data retrieved")
        return False

def main():
    """Run all memory tests."""
    print("🚀 Starting Memory System Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Memory Operations", test_memory_operations),
        ("Chat Pipeline Integration", test_chat_with_memory),
        ("Memory Persistence", test_memory_persistence)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Memory system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
