"""
Unit tests for the Advanced Fact Manager.

Tests intelligent fact merging, conflict resolution, and memory optimization functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.agent.advanced_fact_manager import AdvancedFactManager


class TestAdvancedFactManager:
    """Test suite for AdvancedFactManager class."""
    
    @pytest.fixture
    def fact_manager(self):
        """Create a fact manager instance for testing."""
        with patch('src.agent.advanced_fact_manager.ChatOpenAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            with patch('src.agent.advanced_fact_manager.PromptRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.return_value = mock_registry
                
                manager = AdvancedFactManager()
                manager.llm = mock_llm
                manager.prompt_registry = mock_registry
                
                return manager
    
    def test_merge_facts_no_conflicts(self, fact_manager):
        """Test merging facts when there are no conflicts."""
        existing_facts = {
            "business_type": "LLC",
            "state": "California"
        }
        new_facts = {
            "industry": "Technology",
            "employees": "5"
        }
        
        result = fact_manager.merge_facts_intelligently(existing_facts, new_facts)
        
        expected = {
            "business_type": "LLC",
            "state": "California",
            "industry": "Technology",
            "employees": "5"
        }
        
        assert result == expected
    
    def test_merge_facts_empty_existing(self, fact_manager):
        """Test merging when existing facts are empty."""
        existing_facts = {}
        new_facts = {
            "business_type": "Corporation",
            "industry": "Healthcare"
        }
        
        result = fact_manager.merge_facts_intelligently(existing_facts, new_facts)
        
        assert result == new_facts
    
    def test_merge_facts_empty_new(self, fact_manager):
        """Test merging when new facts are empty."""
        existing_facts = {
            "business_type": "LLC",
            "state": "Texas"
        }
        new_facts = {}
        
        result = fact_manager.merge_facts_intelligently(existing_facts, new_facts)
        
        assert result == existing_facts
    
    def test_detect_fact_conflicts_value_mismatch(self, fact_manager):
        """Test conflict detection for value mismatches."""
        existing_facts = {
            "business_type": "LLC",
            "state": "California"
        }
        new_facts = {
            "business_type": "Corporation",
            "industry": "Technology"
        }
        
        conflicts = fact_manager.detect_fact_conflicts(existing_facts, new_facts)
        
        assert len(conflicts) == 1
        assert conflicts[0]['key'] == 'business_type'
        assert conflicts[0]['existing_value'] == 'LLC'
        assert conflicts[0]['new_value'] == 'Corporation'
        assert conflicts[0]['conflict_type'] == 'value_mismatch'
    
    def test_detect_fact_conflicts_type_mismatch(self, fact_manager):
        """Test conflict detection for type mismatches."""
        existing_facts = {
            "employees": "5"
        }
        new_facts = {
            "employees": 5
        }
        
        conflicts = fact_manager.detect_fact_conflicts(existing_facts, new_facts)
        
        assert len(conflicts) == 1
        assert conflicts[0]['key'] == 'employees'
        assert conflicts[0]['conflict_type'] == 'type_mismatch'
    
    def test_detect_fact_conflicts_no_conflicts(self, fact_manager):
        """Test conflict detection when there are no conflicts."""
        existing_facts = {
            "business_type": "LLC",
            "state": "California"
        }
        new_facts = {
            "industry": "Technology",
            "employees": "5"
        }
        
        conflicts = fact_manager.detect_fact_conflicts(existing_facts, new_facts)
        
        assert len(conflicts) == 0
    
    def test_simple_intelligent_merge_nested_dicts(self, fact_manager):
        """Test simple intelligent merge with nested dictionaries."""
        existing_facts = {
            "preferences": {
                "communication_style": "formal",
                "detail_level": "high"
            }
        }
        new_facts = {
            "preferences": {
                "meeting_preference": "video",
                "detail_level": "medium"
            }
        }
        
        result = fact_manager._simple_intelligent_merge(existing_facts, new_facts)
        
        expected = {
            "preferences": {
                "communication_style": "formal",
                "detail_level": "medium",
                "meeting_preference": "video"
            }
        }
        
        assert result == expected
    
    def test_fallback_merge_with_conflicts(self, fact_manager):
        """Test fallback merge handles conflicts by preferring new values."""
        existing_facts = {
            "business_type": "LLC",
            "state": "California"
        }
        new_facts = {
            "business_type": "Corporation",
            "industry": "Technology"
        }
        
        result = fact_manager._fallback_merge(existing_facts, new_facts)
        
        expected = {
            "business_type": "Corporation",
            "state": "California",
            "industry": "Technology"
        }
        
        assert result == expected
    
    def test_parse_merged_facts_valid_json(self, fact_manager):
        """Test parsing valid JSON from LLM response."""
        raw_response = '''
        Here are the merged facts:
        {
            "business_type": "LLC",
            "industry": "Technology",
            "state": "California"
        }
        '''
        
        result = fact_manager._parse_merged_facts(raw_response)
        
        expected = {
            "business_type": "LLC",
            "industry": "Technology",
            "state": "California"
        }
        
        assert result == expected
    
    def test_parse_merged_facts_invalid_json(self, fact_manager):
        """Test parsing invalid JSON returns empty dict."""
        raw_response = "This is not valid JSON at all"
        
        result = fact_manager._parse_merged_facts(raw_response)
        
        assert result == {}
    
    def test_summarize_memory_within_limits(self, fact_manager):
        """Test memory summarization when size is within limits."""
        facts = {
            "business_type": "LLC",
            "industry": "Tech"
        }
        
        result = fact_manager.summarize_memory(facts, max_size=1000)
        
        assert result == facts
    
    def test_fallback_summarize_priority_preservation(self, fact_manager):
        """Test fallback summarization preserves priority facts."""
        facts = {
            "name": "John Doe",
            "business_type": "LLC",
            "industry": "Technology",
            "random_fact": "Likes coffee",
            "another_fact": "Has a dog",
            "preferences": {"style": "formal"}
        }
        
        result = fact_manager._fallback_summarize(facts, max_size=100)
        
        # Should preserve high-priority facts
        assert "name" in result
        assert "business_type" in result
        # May or may not include lower priority facts depending on size
    
    def test_track_fact_relationships_business_group(self, fact_manager):
        """Test fact relationship tracking for business-related facts."""
        facts = {
            "business_type": "LLC",
            "industry": "Technology",
            "stage": "startup",
            "employees": "5",
            "name": "John Doe"
        }
        
        relationships = fact_manager.track_fact_relationships(facts)
        
        # Business-related facts should be related to each other
        business_facts = relationships["business_type"]
        assert "industry" in business_facts
        assert "stage" in business_facts
        assert "employees" in business_facts
        assert "name" not in business_facts  # Name is in different group
    
    def test_track_fact_relationships_contact_group(self, fact_manager):
        """Test fact relationship tracking for contact-related facts."""
        facts = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "business_type": "LLC"
        }
        
        relationships = fact_manager.track_fact_relationships(facts)
        
        # Contact-related facts should be related to each other
        name_relationships = relationships["name"]
        assert "email" in name_relationships
        assert "phone" in name_relationships
        assert "business_type" not in name_relationships  # Different group
    
    def test_filter_by_confidence_above_threshold(self, fact_manager):
        """Test filtering facts by confidence threshold."""
        facts_with_confidence = {
            "business_type": {"value": "LLC", "confidence": 0.9},
            "industry": {"value": "Technology", "confidence": 0.7},
            "uncertain_fact": {"value": "Maybe", "confidence": 0.5}
        }
        
        result = fact_manager.filter_by_confidence(facts_with_confidence, threshold=0.8)
        
        expected = {"business_type": "LLC"}
        assert result == expected
    
    def test_filter_by_confidence_all_pass(self, fact_manager):
        """Test filtering when all facts meet threshold."""
        facts_with_confidence = {
            "business_type": {"value": "LLC", "confidence": 0.9},
            "industry": {"value": "Technology", "confidence": 0.85}
        }
        
        result = fact_manager.filter_by_confidence(facts_with_confidence, threshold=0.8)
        
        expected = {"business_type": "LLC", "industry": "Technology"}
        assert result == expected
    
    def test_confidence_decay_over_time(self, fact_manager):
        """Test confidence decay calculation over time."""
        confidence_scores = {
            "business_type": 0.9,
            "industry": 0.8
        }
        
        # Test decay after 7 days (1 week) with 2% weekly decay rate
        decayed_scores = fact_manager.confidence_decay(confidence_scores, days_elapsed=7, decay_rate=0.02)
        
        # After 1 week with 2% decay: 0.9 * 0.98 = 0.882, 0.8 * 0.98 = 0.784
        assert abs(decayed_scores["business_type"] - 0.882) < 0.001
        assert abs(decayed_scores["industry"] - 0.784) < 0.001
    
    def test_confidence_decay_minimum_threshold(self, fact_manager):
        """Test confidence decay doesn't go below minimum threshold."""
        confidence_scores = {"old_fact": 0.2}
        
        # Test extreme decay (100 days)
        decayed_scores = fact_manager.confidence_decay(confidence_scores, days_elapsed=100, decay_rate=0.1)
        
        # Should not go below 0.1
        assert decayed_scores["old_fact"] >= 0.1
    
    def test_auto_remove_low_confidence_facts(self, fact_manager):
        """Test automatic removal of low confidence facts."""
        facts = {
            "high_confidence": "Value1",
            "medium_confidence": "Value2",
            "low_confidence": "Value3"
        }
        confidence_scores = {
            "high_confidence": 0.9,
            "medium_confidence": 0.5,
            "low_confidence": 0.2
        }
        
        cleaned_facts, cleaned_scores = fact_manager.auto_remove_low_confidence_facts(
            facts, confidence_scores, threshold=0.3
        )
        
        # Only high and medium confidence facts should remain
        expected_facts = {
            "high_confidence": "Value1",
            "medium_confidence": "Value2"
        }
        expected_scores = {
            "high_confidence": 0.9,
            "medium_confidence": 0.5
        }
        
        assert cleaned_facts == expected_facts
        assert cleaned_scores == expected_scores


class TestAdvancedFactManagerIntegration:
    """Integration tests for AdvancedFactManager with real LLM calls."""
    
    @pytest.fixture
    def real_fact_manager(self):
        """Create a real fact manager for integration testing."""
        # Only run if OpenAI API key is available
        import os
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key not available for integration tests")
        
        return AdvancedFactManager()
    
    def test_llm_conflict_resolution_integration(self, real_fact_manager):
        """Test LLM-based conflict resolution with real API call."""
        existing_facts = {
            "business_type": "LLC",
            "state": "California",
            "industry": "Technology"
        }
        new_facts = {
            "business_type": "Corporation",
            "employees": "10"
        }
        
        # This will make a real LLM call
        result = real_fact_manager.merge_facts_intelligently(existing_facts, new_facts)
        
        # Verify the result is a valid dictionary
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Should contain facts from both sets
        assert "state" in result
        assert "industry" in result
        assert "employees" in result
        
        # Should have resolved the business_type conflict
        assert "business_type" in result
        assert result["business_type"] in ["LLC", "Corporation"]


if __name__ == "__main__":
    pytest.main([__file__])