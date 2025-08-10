"""
Test conversation history endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_conversation_endpoints_structure():
    """Test that conversation endpoints exist and have proper structure."""
    
    # Test get conversation history endpoint exists
    response = client.get("/conversation/test_user")
    # Should return 200 or 500 (if Redis not available), but not 404
    assert response.status_code != 404
    
    # Test clear conversation history endpoint exists
    response = client.delete("/conversation/test_user")
    # Should return 200 or 500 (if Redis not available), but not 404
    assert response.status_code != 404
    
    # Test session info endpoint exists
    response = client.get("/session/test_user")
    # Should return 200 or 500 (if Redis not available), but not 404
    assert response.status_code != 404

def test_conversation_history_validation():
    """Test conversation history endpoint validation."""
    
    # Test invalid user_id
    response = client.get("/conversation/")
    assert response.status_code == 404  # Missing user_id
    
    # Test invalid limit parameter
    response = client.get("/conversation/test_user?limit=0")
    assert response.status_code == 400
    
    response = client.get("/conversation/test_user?limit=-1")
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main([__file__, "-v"])