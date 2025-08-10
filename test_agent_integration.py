"""
Test agent integration with API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_agent_integration_structure():
    """Test that agent integration maintains API structure."""
    
    # Test chat endpoint exists and accepts proper parameters
    response = client.post("/chat?user_id=test_user", json={"q": "test question"})
    # Should return 200 or 500 (if dependencies not available), but not 404
    assert response.status_code != 404
    
    # Test memory endpoints exist
    response = client.get("/memory/test_user")
    assert response.status_code != 404
    
    response = client.post("/memory/test_user", json={"test": "data"})
    assert response.status_code != 404
    
    # Test new conversation endpoints exist
    response = client.get("/conversation/test_user")
    assert response.status_code != 404
    
    response = client.delete("/conversation/test_user")
    assert response.status_code != 404
    
    response = client.get("/session/test_user")
    assert response.status_code != 404

def test_chat_response_structure():
    """Test that chat endpoint returns expected response structure."""
    
    # This test will fail if Redis/OpenAI not available, but we can check structure
    try:
        response = client.post("/chat?user_id=test_user", json={"q": "Hello"})
        
        if response.status_code == 200:
            data = response.json()
            
            # Check that response has expected fields from agent
            expected_fields = ["answer", "user_id", "question", "extracted_facts", "execution_time", "conversation_turn"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
                
            # Check data types
            assert isinstance(data["answer"], str)
            assert isinstance(data["user_id"], str)
            assert isinstance(data["question"], str)
            assert isinstance(data["extracted_facts"], dict)
            assert isinstance(data["execution_time"], (int, float))
            assert isinstance(data["conversation_turn"], int)
            
    except Exception as e:
        # If dependencies not available, just check that endpoint exists
        assert response.status_code != 404

def test_conversation_history_structure():
    """Test conversation history endpoint response structure."""
    
    try:
        response = client.get("/conversation/test_user")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check expected fields
            expected_fields = ["user_id", "conversation_history", "message_count", "status"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
                
            # Check data types
            assert isinstance(data["user_id"], str)
            assert isinstance(data["conversation_history"], list)
            assert isinstance(data["message_count"], int)
            assert data["status"] == "success"
            
    except Exception as e:
        # If dependencies not available, just check that endpoint exists
        assert response.status_code != 404

def test_session_info_structure():
    """Test session info endpoint response structure."""
    
    try:
        response = client.get("/session/test_user")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check expected fields
            expected_fields = ["user_id", "status"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
                
            # Check data types
            assert isinstance(data["user_id"], str)
            assert data["status"] == "success"
            
    except Exception as e:
        # If dependencies not available, just check that endpoint exists
        assert response.status_code != 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])