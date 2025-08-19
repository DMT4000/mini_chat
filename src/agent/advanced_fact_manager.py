"""
Advanced Fact Management System for AI Co-founder Agent.

This module implements intelligent fact merging, conflict resolution, and memory optimization
using LLM-powered reasoning to maintain clean and accurate user memory.
"""

import json
import os
from typing import Dict, Any, List, Tuple
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from ..prompt_registry import PromptRegistry


class AdvancedFactManager:
    """
    Advanced fact management system with LLM-powered intelligent merging and conflict resolution.
    
    This class provides sophisticated memory management capabilities including:
    - Intelligent fact merging using LLM reasoning
    - Conflict detection and resolution
    - Memory summarization and compression
    - Fact relationship tracking
    """
    
    def __init__(self):
        """Initialize the advanced fact manager with LLM and prompt registry."""
        load_dotenv()
        self.llm = self._init_llm()
        self.prompt_registry = PromptRegistry()
        
    def _init_llm(self) -> ChatOpenAI:
        """Initialize the language model for fact management operations."""
        try:
            # Keep a low temperature for non-reasoning text model; fall back to env-configured if provided
            model_name = os.getenv("FACT_MANAGER_MODEL", "gpt-4o-mini")
            if model_name in {"o3", "o3-mini", "gpt-5-mini", "o4-mini-high"}:
                llm = ChatOpenAI(model=model_name)
            else:
                llm = ChatOpenAI(model=model_name, temperature=0.1)
            print("✅ Language Model initialized for Advanced Fact Manager.")
            return llm
        except Exception as e:
            print(f"❌ Error initializing LLM for Advanced Fact Manager: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {str(e)}")
    
    def merge_facts_intelligently(self, existing_facts: Dict[str, Any], 
                                new_facts: Dict[str, Any],
                                confidence_scores: Dict[str, float] | None = None) -> Dict[str, Any]:
        """
        Merge new facts with existing facts using LLM-powered intelligent reasoning.
        
        This method uses a dedicated LLM prompt to:
        - Consolidate similar facts
        - Resolve conflicts intelligently
        - Maintain fact relationships
        - Preserve important details
        
        Args:
            existing_facts: Current user facts from memory
            new_facts: Newly extracted facts to merge
            
        Returns:
            Dictionary of intelligently merged facts
            
        Raises:
            RuntimeError: If LLM-based merging fails critically
        """
        print(f"🧠 Intelligently merging {len(new_facts)} new facts with {len(existing_facts)} existing facts...")
        
        try:
            # If no existing facts, return new facts directly
            if not existing_facts:
                print("✅ No existing facts - returning new facts directly")
                return new_facts.copy()
            
            # If no new facts, return existing facts
            if not new_facts:
                print("✅ No new facts to merge - returning existing facts")
                return existing_facts.copy()
            
            # If we have confidence scores, prevent low-confidence overwrites for identity keys
            if confidence_scores:
                protected_keys = {"name", "full_name", "user_name"}
                adjusted_new_facts = {}
                for key, value in new_facts.items():
                    if key in protected_keys and key in existing_facts:
                        new_conf = confidence_scores.get(key, 0.0)
                        # Require high confidence to override identity
                        if new_conf < 0.85:
                            continue  # skip overwrite
                    adjusted_new_facts[key] = value
                new_facts = adjusted_new_facts

            # Detect potential conflicts before merging
            conflicts = self.detect_fact_conflicts(existing_facts, new_facts)
            
            if conflicts:
                print(f"⚠️ Detected {len(conflicts)} potential conflicts - using LLM resolution")
                return self._resolve_conflicts_with_llm(existing_facts, new_facts, conflicts)
            else:
                print("✅ No conflicts detected - performing simple intelligent merge")
                return self._simple_intelligent_merge(existing_facts, new_facts)
                
        except Exception as e:
            print(f"❌ Error in intelligent fact merging: {e}")
            # Fallback to simple merge if LLM fails
            print("⚠️ Falling back to simple merge due to error")
            return self._fallback_merge(existing_facts, new_facts)
    
    def detect_fact_conflicts(self, existing_facts: Dict[str, Any], 
                            new_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect potential conflicts between existing and new facts.
        
        Args:
            existing_facts: Current user facts
            new_facts: New facts to check for conflicts
            
        Returns:
            List of conflict dictionaries with details about each conflict
        """
        conflicts = []
        
        for key, new_value in new_facts.items():
            if key in existing_facts:
                existing_value = existing_facts[key]
                
                # Check for type conflicts first
                if type(existing_value) != type(new_value):
                    conflicts.append({
                        'key': key,
                        'existing_value': existing_value,
                        'new_value': new_value,
                        'conflict_type': 'type_mismatch'
                    })
                # Check for direct value conflicts
                elif existing_value != new_value:
                    # Skip conflicts for nested dictionaries (handle separately)
                    if not (isinstance(existing_value, dict) and isinstance(new_value, dict)):
                        conflicts.append({
                            'key': key,
                            'existing_value': existing_value,
                            'new_value': new_value,
                            'conflict_type': 'value_mismatch'
                        })
        
        return conflicts
    
    def _resolve_conflicts_with_llm(self, existing_facts: Dict[str, Any], 
                                  new_facts: Dict[str, Any], 
                                  conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM reasoning to resolve fact conflicts intelligently.
        
        Args:
            existing_facts: Current user facts
            new_facts: New facts with conflicts
            conflicts: List of detected conflicts
            
        Returns:
            Dictionary of facts with conflicts resolved
        """
        try:
            # Create conflict resolution prompt
            prompt = self.prompt_registry.get(
                "fact_merging",
                existing_facts=json.dumps(existing_facts, indent=2),
                new_facts=json.dumps(new_facts, indent=2),
                conflicts=json.dumps(conflicts, indent=2)
            )
            
            # Get LLM resolution
            response = self.llm.invoke(prompt)
            raw_merged = response.content
            
            # Parse the merged facts
            merged_facts = self._parse_merged_facts(raw_merged)
            
            if merged_facts:
                print(f"✅ LLM successfully resolved {len(conflicts)} conflicts")
                return merged_facts
            else:
                print("⚠️ LLM resolution failed - using fallback merge")
                return self._fallback_merge(existing_facts, new_facts)
                
        except Exception as e:
            print(f"❌ Error in LLM conflict resolution: {e}")
            return self._fallback_merge(existing_facts, new_facts)
    
    def _simple_intelligent_merge(self, existing_facts: Dict[str, Any], 
                                new_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform intelligent merge without conflicts using entity consolidation.
        
        Args:
            existing_facts: Current user facts
            new_facts: New facts to merge
            
        Returns:
            Dictionary of intelligently merged facts
        """
        merged = existing_facts.copy()
        
        for key, new_value in new_facts.items():
            if key in merged:
                existing_value = merged[key]
                
                # Handle nested dictionaries recursively
                if isinstance(existing_value, dict) and isinstance(new_value, dict):
                    merged[key] = self._simple_intelligent_merge(existing_value, new_value)
                else:
                    # For non-conflicting updates, prefer new value
                    merged[key] = new_value
            else:
                # New key, add it
                merged[key] = new_value
        
        return merged

    # (helper removed; logic handled inline in merge_facts_intelligently)
    
    def _fallback_merge(self, existing_facts: Dict[str, Any], 
                       new_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simple fallback merge when LLM processing fails.
        
        Args:
            existing_facts: Current user facts
            new_facts: New facts to merge
            
        Returns:
            Dictionary of merged facts using simple strategy
        """
        merged = existing_facts.copy()
        
        for key, value in new_facts.items():
            if key in merged and merged[key] != value:
                # Log conflict but prefer new value
                print(f"⚠️ Fallback merge conflict for '{key}': '{merged[key]}' -> '{value}'")
            merged[key] = value
        
        return merged
    
    def _parse_merged_facts(self, raw_merged: str) -> Dict[str, Any]:
        """
        Parse merged facts from LLM response.
        
        Args:
            raw_merged: Raw LLM response containing merged facts
            
        Returns:
            Dictionary of parsed merged facts, empty dict if parsing fails
        """
        try:
            import re
            
            # Look for JSON object in the response
            json_match = re.search(r'\{.*\}', raw_merged, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                merged_facts = json.loads(json_str)
                
                if isinstance(merged_facts, dict):
                    return merged_facts
            
            print("⚠️ Could not parse valid JSON from fact merging response")
            return {}
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error in fact merging: {e}")
            return {}
        except Exception as e:
            print(f"⚠️ Unexpected error parsing merged facts: {e}")
            return {}
    
    def summarize_memory(self, facts: Dict[str, Any], max_size: int = 1000) -> Dict[str, Any]:
        """
        Compress large fact collections using LLM summarization.
        
        This method uses LLM to intelligently summarize and compress user memory
        when it becomes too large, preserving the most important information.
        
        Args:
            facts: Dictionary of user facts to summarize
            max_size: Maximum desired size in characters for the summary
            
        Returns:
            Dictionary of summarized facts
        """
        print(f"📝 Summarizing memory with {len(facts)} facts (target size: {max_size} chars)...")
        
        try:
            # Check if summarization is needed
            current_size = len(json.dumps(facts))
            if current_size <= max_size:
                print("✅ Memory size within limits - no summarization needed")
                return facts
            
            # Use LLM to create intelligent summary
            prompt = self.prompt_registry.get(
                "memory_summarization",
                facts=json.dumps(facts, indent=2),
                max_size=max_size,
                current_size=current_size
            )
            
            response = self.llm.invoke(prompt)
            raw_summary = response.content
            
            # Parse summarized facts
            summarized_facts = self._parse_merged_facts(raw_summary)
            
            if summarized_facts:
                new_size = len(json.dumps(summarized_facts))
                print(f"✅ Memory summarized: {current_size} -> {new_size} characters")
                return summarized_facts
            else:
                print("⚠️ LLM summarization failed - using fallback compression")
                return self._fallback_summarize(facts, max_size)
                
        except Exception as e:
            print(f"❌ Error in memory summarization: {e}")
            return self._fallback_summarize(facts, max_size)
    
    def _fallback_summarize(self, facts: Dict[str, Any], max_size: int) -> Dict[str, Any]:
        """
        Fallback summarization using simple truncation strategy.
        
        Args:
            facts: Facts to summarize
            max_size: Target size limit
            
        Returns:
            Dictionary of summarized facts
        """
        # Priority order for preserving facts
        priority_keys = [
            'name', 'business_type', 'industry', 'state', 'stage',
            'preferences', 'goals', 'contact_info'
        ]
        
        summarized = {}
        current_size = 0
        
        # First, add priority facts
        for key in priority_keys:
            if key in facts:
                fact_size = len(json.dumps({key: facts[key]}))
                if current_size + fact_size <= max_size:
                    summarized[key] = facts[key]
                    current_size += fact_size
                else:
                    break
        
        # Add remaining facts if space allows
        for key, value in facts.items():
            if key not in summarized:
                fact_size = len(json.dumps({key: value}))
                if current_size + fact_size <= max_size:
                    summarized[key] = value
                    current_size += fact_size
                else:
                    break
        
        return summarized
    
    def filter_by_confidence(self, facts_with_confidence: Dict[str, Dict[str, Any]], 
                           threshold: float = 0.8) -> Dict[str, Any]:
        """
        Filter facts by confidence threshold.
        
        Args:
            facts_with_confidence: Dictionary mapping fact keys to {value, confidence} dicts
            threshold: Minimum confidence threshold (default 0.8)
            
        Returns:
            Dictionary of facts that meet the confidence threshold
        """
        filtered_facts = {}
        
        for key, fact_data in facts_with_confidence.items():
            confidence = fact_data.get('confidence', 0.0)
            value = fact_data.get('value')
            
            if confidence >= threshold:
                filtered_facts[key] = value
            else:
                print(f"⚠️ Filtered out fact '{key}' due to low confidence: {confidence}")
        
        return filtered_facts
    
    def confidence_decay(self, confidence_scores: Dict[str, float], 
                        days_elapsed: int, decay_rate: float = 0.02) -> Dict[str, float]:
        """
        Apply confidence decay over time to reduce confidence of older facts.
        
        Args:
            confidence_scores: Dictionary mapping fact keys to confidence scores
            days_elapsed: Number of days since facts were extracted
            decay_rate: Weekly decay rate (default 0.02 = 2% per week)
            
        Returns:
            Dictionary of confidence scores with decay applied
        """
        decayed_scores = {}
        
        # Convert daily decay rate to weekly (7 days)
        weeks_elapsed = days_elapsed / 7.0
        
        for fact_key, confidence in confidence_scores.items():
            # Apply exponential decay: new_confidence = old_confidence * (1 - decay_rate)^weeks
            decayed_confidence = confidence * ((1 - decay_rate) ** weeks_elapsed)
            
            # Ensure confidence doesn't go below 0.1
            decayed_confidence = max(0.1, decayed_confidence)
            
            decayed_scores[fact_key] = decayed_confidence
        
        return decayed_scores
    
    def auto_remove_low_confidence_facts(self, facts: Dict[str, Any], 
                                       confidence_scores: Dict[str, float],
                                       threshold: float = 0.3) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Automatically remove facts with confidence below threshold.
        
        Args:
            facts: Dictionary of user facts
            confidence_scores: Dictionary of confidence scores
            threshold: Minimum confidence to keep facts (default 0.3)
            
        Returns:
            Tuple of (cleaned_facts, cleaned_confidence_scores)
        """
        cleaned_facts = {}
        cleaned_scores = {}
        removed_count = 0
        
        for fact_key, fact_value in facts.items():
            confidence = confidence_scores.get(fact_key, 1.0)  # Default to high confidence if not found
            
            if confidence >= threshold:
                cleaned_facts[fact_key] = fact_value
                cleaned_scores[fact_key] = confidence
            else:
                removed_count += 1
                print(f"🗑️ Auto-removed fact '{fact_key}' due to low confidence: {confidence}")
        
        if removed_count > 0:
            print(f"✅ Auto-removed {removed_count} low-confidence facts")
        
        return cleaned_facts, cleaned_scores
    
    def track_fact_relationships(self, facts: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Track relationships between facts for better context understanding.
        
        Args:
            facts: Dictionary of user facts
            
        Returns:
            Dictionary mapping fact keys to related fact keys
        """
        relationships = {}
        
        # Define common fact relationships
        business_related = ['business_type', 'industry', 'stage', 'state', 'employees']
        contact_related = ['name', 'email', 'phone', 'address']
        preference_related = ['communication_style', 'detail_level', 'meeting_preference']
        
        relationship_groups = [business_related, contact_related, preference_related]
        
        for fact_key in facts.keys():
            relationships[fact_key] = []
            
            # Find related facts in the same group
            for group in relationship_groups:
                if fact_key in group:
                    relationships[fact_key] = [k for k in group if k in facts and k != fact_key]
                    break
        
        return relationships