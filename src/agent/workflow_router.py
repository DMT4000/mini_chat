"""
Intelligent workflow routing for conditional agent execution.

This module implements the WorkflowRouter class that classifies user inputs
and determines the appropriate workflow path for optimal performance.
"""

import re
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from .config import MODEL_NAME, llm_kwargs_for
from dotenv import load_dotenv

from ..prompt_registry import PromptRegistry
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
router_logger = logging.getLogger(__name__)


class WorkflowRouter:
    """
    Intelligent router for determining optimal workflow paths based on user input.
    
    This class analyzes user inputs to:
    - Detect memory management commands (!memory, !forget, !update)
    - Classify question complexity (simple, complex, greeting)
    - Make routing decisions for workflow optimization
    - Track routing metrics for performance analysis
    """
    
    def __init__(self):
        """Initialize the workflow router with LLM and prompt registry."""
        load_dotenv()
        self.llm = self._init_llm()
        self.prompt_registry = PromptRegistry()
        self.routing_metrics = {
            'total_classifications': 0,
            'command_detections': 0,
            'simple_questions': 0,
            'complex_questions': 0,
            'greetings': 0,
            'routing_errors': 0
        }
    
    def _init_llm(self) -> ChatOpenAI:
        """Initialize the language model for classification tasks."""
        try:
            # Use conditional kwargs to avoid passing temperature to reasoning models
            llm = ChatOpenAI(**llm_kwargs_for(MODEL_NAME))
            print("✅ Language Model initialized for workflow routing.")
            return llm
        except Exception as e:
            print(f"❌ Error initializing LLM for routing: {e}")
            raise RuntimeError(f"Failed to initialize routing LLM: {str(e)}")

# --- Quick-profile/identity detection helpers ---
PROFILE_PATTERNS = [
    r"\bmy name is\s+(?P<name>[A-Za-zÀ-ÿ'.-]{2,40})\b",
    r"\bcall me\s+(?P<name>[A-Za-zÀ-ÿ'.-]{2,40})\b",
    r"\bi am\s+(?P<name>[A-Za-zÀ-ÿ'.-]{2,40})\b",
    r"\bme llamo\s+(?P<name>[A-Za-zÀ-ÿ'.-]{2,40})\b",
]

ASK_IDENTITY_PATTERNS = [
    r"\bwhat(?:'s| is) my name\b",
    r"\bdo you remember my name\b",
    r"\bcual es mi nombre\b",
]


def detect_profile_info(user_input: str):
    text = user_input.strip().lower()
    for p in PROFILE_PATTERNS:
        m = re.search(p, text)
        if m:
            return {"intent": "provide_profile_info", "entities": {"name": m.group("name").strip().title()}}
    for p in ASK_IDENTITY_PATTERNS:
        if re.search(p, text):
            return {"intent": "ask_identity", "entities": {}}
    return None

# Document-related question patterns (doc visibility / ingestion / retrieval status)
DOC_QUESTION_PATTERNS = [
    r"\b(can you|do you) (see|access|read) (my|the) (docs|documents|files|pdfs)\b",
    r"\b(do you have|did you load|did you ingest) (my|the) (docs|documents|files|pdfs)\b",
    r"\bhow many (docs|documents|files|pdfs) (do you|did you) (see|load|ingest)\b",
    r"\bcan you see (\d+) (docs|documents|files|pdfs)\b",
    r"\bvector|faiss|ingest|index\b",
]

def is_document_question(user_input: str) -> bool:
    text = user_input.strip().lower()
    for p in DOC_QUESTION_PATTERNS:
        if re.search(p, text):
            return True
    return False
    
    def classify_command(self, user_input: str) -> str:
        """
        Classify user input to detect memory management commands.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            str: Command type - "memory_command", "question", or "system"
        """
        try:
            self.routing_metrics['total_classifications'] += 1
            
            # Normalize input for pattern matching
            normalized_input = user_input.strip().lower()
            
            # Define memory command patterns
            memory_patterns = [
                r'^!memory\s*$',           # !memory
                r'^!forget\s+.+',          # !forget [topic]
                r'^!update\s+.+',          # !update [key] [value]
                r'^!help\s*$',             # !help
                r'^!export\s*$',           # !export
                r'^!import\s+.+',          # !import [data]
                r'^!search\s+.+',          # !search [keyword]
            ]
            
            # Check for memory commands
            for pattern in memory_patterns:
                if re.match(pattern, normalized_input):
                    self.routing_metrics['command_detections'] += 1
                    router_logger.info(f"Detected memory command: {user_input[:50]}...")
                    return "memory_command"
            
            # Check for system commands (future extensibility)
            system_patterns = [
                r'^!status\s*$',
                r'^!debug\s*$',
                r'^!config\s+.+',
            ]
            
            for pattern in system_patterns:
                if re.match(pattern, normalized_input):
                    router_logger.info(f"Detected system command: {user_input[:50]}...")
                    return "system"
            
            # Default to question if no commands detected
            return "question"
            
        except Exception as e:
            self.routing_metrics['routing_errors'] += 1
            router_logger.error(f"Error in command classification: {str(e)}")
            # Default to question on error
            return "question"
    
    def classify_question_complexity(self, question: str, user_facts: Dict[str, Any]) -> str:
        """
        Determine question complexity using LLM to optimize workflow routing.
        
        Args:
            question: User's question
            user_facts: Current user facts for context
            
        Returns:
            str: Question type - "simple", "complex", or "greeting"
        """
        try:
            self.routing_metrics['total_classifications'] += 1
            
            # Quick pattern-based classification for obvious cases
            quick_classification = self._quick_classify_question(question)
            if quick_classification:
                return quick_classification
            
            # Use LLM for more nuanced classification
            user_context = self._format_user_context(user_facts)
            
            classification_prompt = self._create_classification_prompt(question, user_context)
            
            response = self.llm.invoke(classification_prompt)
            classification = response.content.strip().lower()
            
            # Validate and normalize LLM response
            if "greeting" in classification or "simple" in classification:
                if "greeting" in classification:
                    self.routing_metrics['greetings'] += 1
                    return "greeting"
                else:
                    self.routing_metrics['simple_questions'] += 1
                    return "simple"
            elif "complex" in classification:
                self.routing_metrics['complex_questions'] += 1
                return "complex"
            else:
                # Default to complex for safety
                self.routing_metrics['complex_questions'] += 1
                router_logger.warning(f"Unclear LLM classification: {classification}, defaulting to complex")
                return "complex"
                
        except Exception as e:
            self.routing_metrics['routing_errors'] += 1
            router_logger.error(f"Error in question complexity classification: {str(e)}")
            # Default to complex on error for safety
            return "complex"

    def detect_intent(self, question: str, user_facts: Dict[str, Any], conversation_context: str = "") -> Dict[str, Any]:
        """
        Extract intent, entities, and whether clarification is needed.
        Returns a dict: {"intent": str, "entities": dict, "needs_clarification": bool}
        """
        try:
            # Quick heuristics first
            lowered = question.strip().lower()
            if len(lowered) < 6 or lowered in {"hi", "hello", "hey"}:
                return {"intent": "greeting", "entities": {}, "needs_clarification": False}

            # Heuristic: fact statements about identity/preferences
            # e.g., "my name is X", "call me X", "i am X"
            name_match = re.search(r"\b(my name is|call me)\s+([A-Za-z][A-Za-z\-\s]{1,40})", lowered)
            if name_match:
                name_val = name_match.group(2).strip().title()
                return {"intent": "provide_profile_info", "entities": {"name": name_val}, "needs_clarification": False}

            # LLM-based structured extraction with robust JSON parsing
            facts_snippet = self._format_user_context(user_facts)
            prompt = (
                "You are an intent extraction system. Read the user's question and return STRICT JSON with keys: "
                "intent (string), entities (object), needs_clarification (boolean). If unsure, set needs_clarification true.\n\n"
                f"User facts: {facts_snippet}\n"
                f"Recent: {conversation_context[:400]}\n"
                f"Question: {question}\n\n"
                "Return ONLY JSON."
            )
            response = self.llm.invoke(prompt)
            raw = response.content
            data = self._safe_json_extract(raw)
            if not isinstance(data, dict):
                raise ValueError("Intent JSON not a dict")
            intent = str(data.get("intent", "unknown")).strip().lower()
            entities = data.get("entities", {}) or {}
            needs = bool(data.get("needs_clarification", False))
            return {"intent": intent, "entities": entities, "needs_clarification": needs}
        except Exception as e:
            self.routing_metrics['routing_errors'] += 1
            router_logger.error(f"Error in intent detection: {str(e)}")
            # Safe fallback
            return {"intent": "unknown", "entities": {}, "needs_clarification": False}

    def _safe_json_extract(self, text: str) -> Any:
        """Extract first JSON object from text robustly."""
        try:
            # Fast path: direct parse
            return json.loads(text)
        except Exception:
            pass
        try:
            import re
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group(0))
        except Exception:
            return {}
    
    def _quick_classify_question(self, question: str) -> Optional[str]:
        """
        Quick pattern-based classification for obvious cases.
        
        Args:
            question: User's question
            
        Returns:
            Optional[str]: Classification if obvious, None otherwise
        """
        normalized = question.strip().lower()
        
        # Greeting patterns
        greeting_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)\s*[!.]*$',
            r'^(thanks|thank you|thx)\s*[!.]*$',
            r'^(bye|goodbye|see you|farewell)\s*[!.]*$',
            r'^(how are you|what\'s up|how\'s it going)\s*[?!.]*$',
        ]
        
        for pattern in greeting_patterns:
            if re.match(pattern, normalized):
                self.routing_metrics['greetings'] += 1
                return "greeting"
        
        # Simple question patterns (short, basic queries)
        if len(normalized) < 20 and any(word in normalized for word in ['what', 'who', 'when', 'where', 'how']):
            simple_patterns = [
                r'^what is .{1,20}\?*$',
                r'^who is .{1,20}\?*$',
                r'^when .{1,20}\?*$',
                r'^where .{1,20}\?*$',
                r'^how .{1,20}\?*$',
            ]
            
            for pattern in simple_patterns:
                if re.match(pattern, normalized):
                    self.routing_metrics['simple_questions'] += 1
                    return "simple"
        
        return None
    
    def _format_user_context(self, user_facts: Dict[str, Any]) -> str:
        """
        Format user facts for context in classification.
        
        Args:
            user_facts: User facts dictionary
            
        Returns:
            str: Formatted context string
        """
        if not user_facts:
            return "No user context available"
        
        context_items = []
        for key, value in user_facts.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    context_items.append(f"{key}.{sub_key}: {sub_value}")
            else:
                context_items.append(f"{key}: {value}")
        
        return "; ".join(context_items[:5])  # Limit context for efficiency
    
    def _create_classification_prompt(self, question: str, user_context: str) -> str:
        """
        Create a prompt for LLM-based question classification.
        
        Args:
            question: User's question
            user_context: Formatted user context
            
        Returns:
            str: Classification prompt
        """
        return f"""Classify this user question based on complexity and type.

User Context: {user_context}
Question: "{question}"

Classification Rules:
- GREETING: Simple social interactions (hi, thanks, bye, how are you)
- SIMPLE: Basic factual questions that can be answered quickly without deep analysis
- COMPLEX: Questions requiring research, analysis, or detailed business advice

Respond with exactly one word: GREETING, SIMPLE, or COMPLEX"""
    
    def should_extract_facts(self, conversation: str, existing_facts: Dict[str, Any]) -> bool:
        """
        Determine if fact extraction is worth the computational cost.
        
        Args:
            conversation: Full conversation text (question + answer)
            existing_facts: Current user facts
            
        Returns:
            bool: True if fact extraction should be performed
        """
        try:
            # Skip fact extraction for very short conversations
            if len(conversation.strip()) < 50:
                router_logger.info("Skipping fact extraction: conversation too short")
                return False
            
            # Skip if conversation is purely greeting/social
            if self._is_purely_social_conversation(conversation):
                router_logger.info("Skipping fact extraction: purely social conversation")
                return False
            
            # Always extract if user has no facts yet
            if not existing_facts:
                router_logger.info("Performing fact extraction: no existing user facts")
                return True
            
            # Check if conversation contains potential factual information
            if self._contains_factual_information(conversation):
                router_logger.info("Performing fact extraction: factual information detected")
                return True
            
            router_logger.info("Skipping fact extraction: no new factual information detected")
            return False
            
        except Exception as e:
            router_logger.error(f"Error in fact extraction decision: {str(e)}")
            # Default to extracting facts on error for safety
            return True
    
    def _is_purely_social_conversation(self, conversation: str) -> bool:
        """
        Check if conversation is purely social/greeting without business content.
        
        Args:
            conversation: Conversation text
            
        Returns:
            bool: True if purely social
        """
        social_keywords = [
            'hello', 'hi', 'hey', 'thanks', 'thank you', 'goodbye', 'bye',
            'how are you', 'nice to meet', 'pleasure', 'welcome'
        ]
        
        business_keywords = [
            'business', 'company', 'llc', 'corporation', 'tax', 'legal',
            'formation', 'register', 'license', 'permit', 'compliance'
        ]
        
        conversation_lower = conversation.lower()
        
        # Count social vs business keywords
        social_count = sum(1 for keyword in social_keywords if keyword in conversation_lower)
        business_count = sum(1 for keyword in business_keywords if keyword in conversation_lower)
        
        # Consider purely social if social keywords dominate and no business keywords
        return social_count > 0 and business_count == 0 and len(conversation) < 200
    
    def _contains_factual_information(self, conversation: str) -> bool:
        """
        Check if conversation contains potential factual information worth extracting.
        
        Args:
            conversation: Conversation text
            
        Returns:
            bool: True if factual information is present
        """
        factual_indicators = [
            # Business information
            r'\b(llc|corporation|partnership|sole proprietorship)\b',
            r'\b(delaware|california|texas|new york|florida)\b',
            r'\b(technology|healthcare|retail|manufacturing|consulting)\b',
            
            # Personal/business details
            r'\b(my business|my company|we are|i am)\b',
            r'\b(planning to|want to|need to|looking to)\b',
            r'\b(revenue|employees|customers|clients)\b',
            
            # Specific facts
            r'\$\d+',  # Dollar amounts
            r'\b\d+\s+(employees|years|months)\b',  # Numbers with units
            r'\b(founded|established|started)\b',
        ]
        
        conversation_lower = conversation.lower()
        
        for pattern in factual_indicators:
            if re.search(pattern, conversation_lower):
                return True
        
        return False
    
    def get_routing_metrics(self) -> Dict[str, Any]:
        """
        Get current routing performance metrics.
        
        Returns:
            Dict containing routing statistics
        """
        metrics = self.routing_metrics.copy()
        
        # Calculate percentages if we have classifications
        if metrics['total_classifications'] > 0:
            total = metrics['total_classifications']
            metrics['command_percentage'] = (metrics['command_detections'] / total) * 100
            metrics['simple_percentage'] = (metrics['simple_questions'] / total) * 100
            metrics['complex_percentage'] = (metrics['complex_questions'] / total) * 100
            metrics['greeting_percentage'] = (metrics['greetings'] / total) * 100
            metrics['error_rate'] = (metrics['routing_errors'] / total) * 100
        
        return metrics
    
    def reset_metrics(self):
        """Reset routing metrics for fresh tracking."""
        self.routing_metrics = {
            'total_classifications': 0,
            'command_detections': 0,
            'simple_questions': 0,
            'complex_questions': 0,
            'greetings': 0,
            'routing_errors': 0
        }
        router_logger.info("Routing metrics reset")


# Export the main class
__all__ = ["WorkflowRouter"]