"""
Test confidence-based fact extraction functionality.
"""

import pytest
from src.agent.workflow_nodes import _parse_extracted_facts_with_confidence, _filter_by_confidence


class TestConfidenceExtraction:
    """Test confidence-based fact extraction parsing."""
    
    def test_parse_facts_with_confidence_new_format(self):
        """Test parsing facts with confidence scores in new format."""
        raw_response = '''
        {
          "facts": {
            "business_type": {
              "value": "LLC",
              "confidence": 0.9
            },
            "industry": {
              "value": "Technology",
              "confidence": 0.8
            }
          }
        }
        '''
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        expected = {
            "business_type": {"value": "LLC", "confidence": 0.9},
            "industry": {"value": "Technology", "confidence": 0.8}
        }
        
        assert result == expected
    
    def test_parse_facts_with_confidence_old_format_fallback(self):
        """Test parsing facts in old format with default confidence."""
        raw_response = '''
        {
          "business_type": "LLC",
          "industry": "Technology"
        }
        '''
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        expected = {
            "business_type": {"value": "LLC", "confidence": 0.8},
            "industry": {"value": "Technology", "confidence": 0.8}
        }
        
        assert result == expected
    
    def test_parse_facts_with_confidence_invalid_confidence(self):
        """Test parsing facts with invalid confidence scores."""
        raw_response = '''
        {
          "facts": {
            "business_type": {
              "value": "LLC",
              "confidence": 1.5
            },
            "industry": {
              "value": "Technology",
              "confidence": -0.1
            },
            "valid_fact": {
              "value": "Valid",
              "confidence": 0.8
            }
          }
        }
        '''
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        # Only valid fact should be included
        expected = {
            "valid_fact": {"value": "Valid", "confidence": 0.8}
        }
        
        assert result == expected
    
    def test_parse_facts_with_confidence_empty_values(self):
        """Test parsing facts with empty or None values."""
        raw_response = '''
        {
          "facts": {
            "empty_value": {
              "value": "",
              "confidence": 0.9
            },
            "none_value": {
              "value": null,
              "confidence": 0.8
            },
            "valid_fact": {
              "value": "Valid",
              "confidence": 0.8
            }
          }
        }
        '''
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        # Only valid fact should be included
        expected = {
            "valid_fact": {"value": "Valid", "confidence": 0.8}
        }
        
        assert result == expected
    
    def test_filter_by_confidence_threshold(self):
        """Test filtering facts by confidence threshold."""
        facts_with_confidence = {
            "high_confidence": {"value": "High", "confidence": 0.9},
            "medium_confidence": {"value": "Medium", "confidence": 0.7},
            "low_confidence": {"value": "Low", "confidence": 0.5}
        }
        
        result = _filter_by_confidence(facts_with_confidence, threshold=0.8)
        
        expected = {"high_confidence": "High"}
        assert result == expected
    
    def test_filter_by_confidence_default_threshold(self):
        """Test filtering with default threshold (0.8)."""
        facts_with_confidence = {
            "above_threshold": {"value": "Above", "confidence": 0.85},
            "below_threshold": {"value": "Below", "confidence": 0.75}
        }
        
        result = _filter_by_confidence(facts_with_confidence)
        
        expected = {"above_threshold": "Above"}
        assert result == expected
    
    def test_parse_facts_invalid_json(self):
        """Test parsing invalid JSON returns empty dict."""
        raw_response = "This is not valid JSON"
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        assert result == {}
    
    def test_parse_facts_no_json_found(self):
        """Test parsing when no JSON is found in response."""
        raw_response = "Here are some facts but no JSON structure"
        
        result = _parse_extracted_facts_with_confidence(raw_response)
        
        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__])