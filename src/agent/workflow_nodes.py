"""
LangGraph workflow nodes for the AI Co-founder agent.

This module implements the individual nodes that make up the agent workflow:
- RetrieveContextNode: Retrieves user memory and relevant documents
- GenerateAnswerNode: Generates responses using context engineering
- ExtractFactsNode: Extracts new facts from conversations
- SaveFactsNode: Saves extracted facts to user memory
"""

import os
import json
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from .config import MODEL_NAME, llm_kwargs_for
from dotenv import load_dotenv

from .agent_state import AgentState, update_state_field
from ..memory.redis_memory_manager import RedisMemoryManager
from ..prompt_registry import PromptRegistry
from .advanced_fact_manager import AdvancedFactManager


class WorkflowNodes:
    """Container class for all workflow node implementations."""
    
    def __init__(self):
        """Initialize shared resources for workflow nodes."""
        load_dotenv()
        self.memory_manager = RedisMemoryManager()
        self.prompt_registry = PromptRegistry()
        self.advanced_fact_manager = AdvancedFactManager()
        self.llm = self._init_llm()
        self.retriever = self._init_retriever()
    
    def _init_llm(self) -> ChatOpenAI:
        """Initialize the language model."""
        try:
            # Use conditional kwargs to avoid temperature errors on reasoning models
            llm = ChatOpenAI(**llm_kwargs_for(MODEL_NAME))
            print("✅ Language Model initialized for workflow nodes.")
            return llm
        except Exception as e:
            print(f"❌ Error initializing LLM for workflow: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {str(e)}")
    
    def _init_retriever(self):
        """Initialize the FAISS retriever."""
        print("🔍 Initializing FAISS index for workflow...")
        if os.path.exists("faiss_index"):
            try:
                embeddings = OpenAIEmbeddings()
                retriever = FAISS.load_local(
                    "faiss_index", 
                    embeddings, 
                    allow_dangerous_deserialization=True
                ).as_retriever()
                print("✅ FAISS index loaded successfully for workflow.")
                return retriever
            except Exception as e:
                print(f"❌ Error loading FAISS index for workflow: {e}")
                return None
        else:
            print("❌ FAISS index directory not found for workflow.")
            return None


def retrieve_context(state: AgentState) -> AgentState:
    """
    Retrieve user memory and relevant documents for the current question.
    
    This node:
    1. Retrieves user memory from Redis
    2. Retrieves relevant documents from FAISS vector store
    3. Updates the state with retrieved context
    
    Args:
        state: Current agent state containing user_id and question
        
    Returns:
        AgentState: Updated state with user_facts and retrieved_docs
        
    Raises:
        RuntimeError: If critical retrieval operations fail
    """
    print(f"🔍 Retrieving context for user: {state['user_id']}")
    
    try:
        # Initialize workflow nodes if not already done
        if not hasattr(retrieve_context, '_nodes'):
            retrieve_context._nodes = WorkflowNodes()
        
        nodes = retrieve_context._nodes
        
        # 1. Retrieve user memory from Redis
        try:
            user_facts = nodes.memory_manager.get_user_memory(state['user_id'])
            
            # Apply confidence-based prioritization if confidence scores are available
            confidence_scores = state.get('confidence_scores', {})
            if confidence_scores:
                # Sort facts by confidence for better context prioritization
                sorted_facts = sorted(user_facts.items(), 
                                    key=lambda x: confidence_scores.get(x[0], 0.8), 
                                    reverse=True)
                user_facts = dict(sorted_facts)
                print(f"✅ Retrieved {len(user_facts)} user facts from memory (prioritized by confidence)")
            else:
                print(f"✅ Retrieved {len(user_facts)} user facts from memory")
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve user memory: {e}")
            user_facts = {}
        
        # 2. Retrieve relevant documents from FAISS using a richer query and apply a context budget
        retrieved_docs: List[str] = []
        try:
            if nodes.retriever:
                retrieval_query = _build_retrieval_query(
                    question=state['question'],
                    user_facts=user_facts,
                    conversation_history=state.get('conversation_history', [])
                )
                docs = nodes.retriever.get_relevant_documents(retrieval_query)

                # Optional lightweight re-ranking by simple overlap score with the original question
                def _score(doc_text: str) -> int:
                    lowered = doc_text.lower()
                    score = 0
                    for token in state['question'].lower().split():
                        if len(token) > 3 and token in lowered:
                            score += 1
                    return score

                ranked_docs = sorted(docs, key=lambda d: _score(getattr(d, 'page_content', '')), reverse=True)

                # Apply budget: top N docs and total char cap
                MAX_DOCS = 6
                MAX_TOTAL_CHARS = 12000
                MAX_PER_DOC_CHARS = 2200
                total = 0
                for doc in ranked_docs[:MAX_DOCS]:
                    content = getattr(doc, 'page_content', '') or ''
                    if not content:
                        continue
                    truncated = content[:MAX_PER_DOC_CHARS]
                    if total + len(truncated) > MAX_TOTAL_CHARS:
                        remaining = max(0, MAX_TOTAL_CHARS - total)
                        if remaining == 0:
                            break
                        truncated = truncated[:remaining]
                    retrieved_docs.append(truncated)
                    total += len(truncated)

                print(f"✅ Retrieved {len(retrieved_docs)} relevant documents (budgeted {total} chars)")
            else:
                print("⚠️ Warning: FAISS retriever not available")
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve documents: {e}")
        
        # 3. Update state with retrieved context
        updated_state = update_state_field(state, 'user_facts', user_facts)
        updated_state = update_state_field(updated_state, 'retrieved_docs', retrieved_docs)
        
        print(f"✅ Context retrieval completed for user: {state['user_id']}")
        return updated_state
        
    except Exception as e:
        error_msg = f"Critical error in retrieve_context node: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Return state with empty context rather than failing completely
        updated_state = update_state_field(state, 'user_facts', {})
        updated_state = update_state_field(updated_state, 'retrieved_docs', [])
        
        # Log the error but don't raise to allow workflow to continue
        print("⚠️ Continuing with empty context due to retrieval failure")
        return updated_state


def generate_answer(state: AgentState) -> AgentState:
    """
    Generate an answer using context engineering with user facts and documents.
    
    This node:
    1. Engineers context by combining user facts with retrieved documents
    2. Uses enhanced prompt templates to generate responses
    3. Validates and formats the response
    4. Updates the state with the generated answer
    
    Args:
        state: Current agent state with user_facts, retrieved_docs, and question
        
    Returns:
        AgentState: Updated state with generated answer
        
    Raises:
        RuntimeError: If answer generation fails critically
    """
    print(f"🤖 Generating answer for question: {state['question'][:50]}...")
    
    try:
        # Initialize workflow nodes if not already done
        if not hasattr(generate_answer, '_nodes'):
            generate_answer._nodes = WorkflowNodes()
        
        nodes = generate_answer._nodes
        
        # 0. Deterministic short-circuits for common intents/questions to avoid verbose/unwanted output
        try:
            intent = state.get('intent', '')
            entities = state.get('entities', {}) or {}
            question_lower = state['question'].strip().lower()

            # If the user provided profile info (e.g., name), acknowledge briefly
            if intent == 'provide_profile_info':
                name_val = entities.get('name')
                if name_val:
                    answer = f"Nice to meet you, {name_val}. I'll remember that."
                else:
                    answer = "Thanks, I will remember that information."
                return update_state_field(state, 'answer', answer)

            # If user asks for their name and we have it, answer directly; else ask to provide
            if ("what is my name" in question_lower or question_lower == "my name?"):
                stored_name = None
                user_facts = state.get('user_facts', {}) or {}
                for key in ['name', 'user_name', 'full_name']:
                    if key in user_facts and str(user_facts[key]).strip():
                        stored_name = str(user_facts[key]).strip()
                        break
                if stored_name:
                    return update_state_field(state, 'answer', f"Your name is {stored_name}.")
                else:
                    return update_state_field(state, 'answer', "I don't have your name yet. You can tell me by saying, 'my name is ...'.")
        except Exception:
            pass

        # Short-circuit: identity questions answered directly from memory
        try:
            if state.get('intent') == 'ask_identity':
                name = (state.get('user_facts') or {}).get('name')
                answer = f"Your name is {name}." if name else "I don’t have your name yet — tell me and I’ll remember."
                return update_state_field(state, 'answer', answer)
        except Exception:
            pass

        # 1. Engineer context by combining user facts with documents and recent conversation summary
        conversation_context = _summarize_recent_conversation(state.get('conversation_history', []))
        engineered_context = _engineer_context(
            state['user_facts'], state['retrieved_docs'], conversation_context
        )
        
        # 2. Generate response using enhanced prompt template
        try:
            # Strengthen grounding: If no retrieved docs, steer model away from claiming it "saw" documents
            context_for_prompt = engineered_context["document_context"]
            if not state.get('retrieved_docs'):
                context_for_prompt = (
                    "No relevant documents were retrieved for this question. "
                    "Answer based on user background and ask for more details if needed."
                )

            prompt = nodes.prompt_registry.get(
                "qa_with_memory",
                user_facts=engineered_context["user_facts_str"],
                context=context_for_prompt,
                conversation=engineered_context["conversation_context"],
                question=state['question']
            )
            
            # Generate the answer using LLM
            response = nodes.llm.invoke(prompt)
            answer = response.content
            
            # 3. Validate response
            if not answer or len(answer.strip()) == 0:
                answer = "I apologize, but I couldn't generate a proper response to your question. Please try rephrasing it."
            
            print(f"✅ Generated answer ({len(answer)} characters)")
            
        except Exception as e:
            print(f"❌ Error generating answer with LLM: {e}")
            answer = f"I apologize, but I encountered an error while processing your question: {str(e)}"
        
        # 4. Update state with generated answer
        updated_state = update_state_field(state, 'answer', answer)
        
        print("✅ Answer generation completed")
        return updated_state
        
    except Exception as e:
        error_msg = f"Critical error in generate_answer node: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Provide fallback answer
        fallback_answer = "I apologize, but I encountered a technical issue while processing your question. Please try again."
        updated_state = update_state_field(state, 'answer', fallback_answer)
        
        return updated_state


def extract_facts(state: AgentState) -> AgentState:
    """
    Extract new facts from the conversation using specialized LLM prompt.
    
    This node:
    1. Analyzes the conversation (question + answer) for extractable facts
    2. Uses a specialized fact extraction prompt
    3. Parses and validates extracted facts
    4. Updates the state with newly extracted facts
    
    Args:
        state: Current agent state with question and answer
        
    Returns:
        AgentState: Updated state with newly_extracted_facts
    """
    print("🔍 Extracting facts from conversation...")
    
    try:
        # Initialize workflow nodes if not already done
        if not hasattr(extract_facts, '_nodes'):
            extract_facts._nodes = WorkflowNodes()
        
        nodes = extract_facts._nodes

        # If user explicitly provided profile info (e.g., name), save directly without LLM
        try:
            if state.get('intent') == 'provide_profile_info':
                name = (state.get('entities') or {}).get('name')
                if name:
                    return update_state_field(state, 'newly_extracted_facts', {"name": name})
        except Exception:
            pass
        
        # 1. Prepare conversation context for fact extraction
        conversation_text = f"User Question: {state['question']}\n\nAssistant Answer: {state['answer']}"
        
        # 2. Create fact extraction prompt using template
        existing_facts_str = json.dumps(state['user_facts'], indent=2) if state['user_facts'] else "None"
        
        fact_extraction_prompt = nodes.prompt_registry.get(
            "fact_extraction",
            conversation_text=conversation_text,
            existing_facts=existing_facts_str
        )
        
        # 3. Extract facts using LLM
        try:
            response = nodes.llm.invoke(fact_extraction_prompt)
            raw_facts = response.content
            
            # 4. Parse and validate extracted facts with confidence scores
            extracted_facts_with_confidence = _parse_extracted_facts_with_confidence(raw_facts)
            
            # Filter facts by confidence threshold (default 0.8)
            confidence_threshold = 0.8
            extracted_facts = _filter_by_confidence(extracted_facts_with_confidence, confidence_threshold)
            
            print(f"✅ Extracted {len(extracted_facts)} new facts (filtered by confidence >= {confidence_threshold})")
            
        except Exception as e:
            print(f"❌ Error extracting facts with LLM: {e}")
            extracted_facts = {}
        
        # 5. Update state with extracted facts and confidence scores
        updated_state = update_state_field(state, 'newly_extracted_facts', extracted_facts)
        
        # Store confidence scores in state
        global _last_confidence_scores
        if '_last_confidence_scores' in globals():
            updated_state = update_state_field(updated_state, 'confidence_scores', _last_confidence_scores)
        
        print("✅ Fact extraction completed")
        return updated_state
        
    except Exception as e:
        error_msg = f"Critical error in extract_facts node: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Return state with empty extracted facts
        updated_state = update_state_field(state, 'newly_extracted_facts', {})
        return updated_state


def lightweight_response(state: AgentState) -> AgentState:
    """
    Generate lightweight responses for simple interactions and greetings.
    
    This node provides quick responses without full context retrieval or fact extraction,
    optimizing performance for simple interactions like greetings and basic questions.
    
    Args:
        state: Current agent state with question and question_type
        
    Returns:
        AgentState: Updated state with lightweight answer
    """
    print(f"⚡ Generating lightweight response for: {state['question'][:50]}...")
    
    try:
        # Initialize workflow nodes if not already done
        if not hasattr(lightweight_response, '_nodes'):
            lightweight_response._nodes = WorkflowNodes()
        
        nodes = lightweight_response._nodes
        
        question = state['question'].strip().lower()
        
        # Handle greetings with concise responses; tailor for first vs subsequent turn
        if state['question_type'] == 'greeting':
            is_first_turn = len(state.get('conversation_history', [])) == 0
            answer = "Hey! How can I help?" if is_first_turn else "Hey again — what do you need?"
        
        # Handle simple questions with basic responses
        elif state['question_type'] == 'simple':
            # For simple questions, provide a brief response encouraging more detail
            if any(word in question for word in ['what', 'who', 'when', 'where', 'how']):
                answer = f"That's a great question! To give you the most helpful answer, could you provide a bit more context about your specific situation? I'm here to help with detailed business advice tailored to your needs."
            else:
                answer = "I'd be happy to help! Could you tell me more about what you're looking for? The more details you can share, the better I can assist you with your business needs."

            # If this simple question is actually about documents, nudge into specificity rather than generic marketing
            try:
                from .workflow_router import is_document_question
                if is_document_question(state.get('question', '')):
                    answer = "I can check the documents by running a full retrieval step. Ask your question specifically about the docs, or say 'check my documents' to proceed."
            except Exception:
                pass
        
        else:
            # Fallback for other lightweight cases
            answer = "I'm here to help! What specific business question can I assist you with today?"
        
        print(f"✅ Generated lightweight response ({len(answer)} characters)")
        
        # Update state with lightweight answer
        updated_state = update_state_field(state, 'answer', answer)
        
        # Do not blank user_facts; simply avoid using them in lightweight path
        updated_state = update_state_field(updated_state, 'retrieved_docs', [])
        updated_state = update_state_field(updated_state, 'newly_extracted_facts', {})
        
        print("✅ Lightweight response completed")
        return updated_state
        
    except Exception as e:
        error_msg = f"Critical error in lightweight_response node: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Provide fallback response
        fallback_answer = "Hello! I'm here to help you with your business questions. What would you like to know?"
        updated_state = update_state_field(state, 'answer', fallback_answer)
        
        return updated_state


def save_facts(state: AgentState) -> AgentState:
    """
    Save extracted facts to user memory with conflict resolution.
    
    This node:
    1. Merges newly extracted facts with existing user memory
    2. Implements conflict resolution for contradictory facts
    3. Saves updated memory to Redis
    4. Updates conversation history with fact extraction info
    
    Args:
        state: Current agent state with newly_extracted_facts
        
    Returns:
        AgentState: Updated state with saved facts and updated conversation history
    """
    print(f"💾 Saving facts for user: {state['user_id']}")
    
    try:
        # Initialize workflow nodes if not already done
        if not hasattr(save_facts, '_nodes'):
            save_facts._nodes = WorkflowNodes()
        
        nodes = save_facts._nodes
        
        # 1. Check if there are facts to save
        if not state['newly_extracted_facts']:
            print("ℹ️ No new facts to save")
            return state
        
        # 2. Merge facts with intelligent conflict resolution using LLM
        try:
            # Pass confidence scores when available to protect identity facts from low-confidence overrides
            merged_facts = nodes.advanced_fact_manager.merge_facts_intelligently(
                state['user_facts'], 
                state['newly_extracted_facts'],
                confidence_scores=state.get('confidence_scores', {})
            )

            # Optional summarization to keep memory compact well below Redis hard limits
            try:
                serialized_len = len(json.dumps(merged_facts))
                if serialized_len > 10000:  # ~10KB
                    target_size = 8000
                    merged_facts = nodes.advanced_fact_manager.summarize_memory(
                        merged_facts, max_size=target_size
                    )
                    print(f"📝 Memory summarized before save (target {target_size} chars)")
            except Exception as summarize_err:
                print(f"⚠️ Memory summarization skipped due to error: {summarize_err}")

            # 3. Save updated memory to Redis
            nodes.memory_manager.save_user_memory(state['user_id'], merged_facts)

            print(f"✅ Saved {len(state['newly_extracted_facts'])} new facts to memory using intelligent merging")

        except Exception as e:
            print(f"❌ Error saving facts to memory: {e}")
            # Continue without saving rather than failing
        
        # 4. Update conversation history with fact extraction info
        from .agent_state import add_conversation_entry
        
        updated_state = add_conversation_entry(
            state,
            role='assistant',
            content=state['answer'],
            facts_extracted=state['newly_extracted_facts']
        )
        
        print("✅ Fact saving completed")
        return updated_state
        
    except Exception as e:
        error_msg = f"Critical error in save_facts node: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Return original state if saving fails
        return state


# Helper functions

def _engineer_context(user_facts: Dict[str, Any], retrieved_docs: List[str], conversation_context: Optional[str] = None) -> Dict[str, str]:
    """
    Combine user facts with document context for prompt engineering.
    
    Args:
        user_facts: Dictionary of user facts from memory
        retrieved_docs: List of retrieved document contents
        
    Returns:
        Dictionary with formatted user_facts_str and document_context
    """
    # Format user facts for prompt
    if user_facts:
        facts_items = []
        for key, value in user_facts.items():
            if isinstance(value, dict):
                # Handle nested dictionaries (like preferences)
                for sub_key, sub_value in value.items():
                    facts_items.append(f"- {key}.{sub_key}: {sub_value}")
            else:
                facts_items.append(f"- {key}: {value}")
        user_facts_str = "\n".join(facts_items)
    else:
        user_facts_str = "No background information available for this user."
    
    # Format document context
    if retrieved_docs:
        document_context = "\n\n".join(retrieved_docs)
    else:
        document_context = "No relevant documents found."
    
    return {
        "user_facts_str": user_facts_str,
        "document_context": document_context,
        "conversation_context": conversation_context or ""
    }


def _build_retrieval_query(question: str, user_facts: Dict[str, Any], conversation_history: List[Dict[str, Any]]) -> str:
    """
    Build a richer retrieval query using the question, a small selection of high-signal facts,
    and a brief summary of recent conversation turns.
    """
    # Take top few facts for query enrichment
    fact_items: List[str] = []
    for key, value in list(user_facts.items())[:5]:
        if isinstance(value, dict):
            # include one nested item per nested dict to keep query short
            for sub_key, sub_value in value.items():
                fact_items.append(f"{key}.{sub_key}={sub_value}")
                break
        else:
            fact_items.append(f"{key}={value}")

    recent_summary = _summarize_recent_conversation(conversation_history, max_chars=280)
    enriched = " ".join(fact_items)
    parts = [question]
    if enriched:
        parts.append(f"[facts: {enriched}]")
    if recent_summary:
        parts.append(f"[recent: {recent_summary}]")
    return " ".join(parts)


def _summarize_recent_conversation(conversation_history: List[Dict[str, Any]], max_messages: int = 6, max_chars: int = 1000) -> str:
    """
    Produce a compact plaintext summary of the last few conversation messages for prompt/retrieval use.
    """
    if not conversation_history:
        return ""
    recent = conversation_history[-max_messages:]
    lines: List[str] = []
    for msg in recent:
        role = msg.get('role', 'user')
        content = str(msg.get('content', '')).strip()
        if not content:
            continue
        prefix = 'User' if role == 'user' else 'Assistant'
        lines.append(f"{prefix}: {content}")
    joined = " \n".join(lines)
    return joined[:max_chars]





def _parse_extracted_facts_with_confidence(raw_facts: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse extracted facts with confidence scores from LLM response.
    
    Args:
        raw_facts: Raw response from fact extraction LLM
        
    Returns:
        Dictionary mapping fact keys to {value, confidence} dictionaries
    """
    try:
        import re
        
        # Look for JSON object in the response
        json_match = re.search(r'\{.*\}', raw_facts, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            response_data = json.loads(json_str)
            
            # Handle new format with confidence scores
            if isinstance(response_data, dict) and 'facts' in response_data:
                facts_with_confidence = response_data['facts']
                
                if isinstance(facts_with_confidence, dict):
                    # Validate structure and clean up
                    cleaned_facts = {}
                    for key, fact_data in facts_with_confidence.items():
                        if isinstance(key, str) and isinstance(fact_data, dict):
                            if 'value' in fact_data and 'confidence' in fact_data:
                                value = fact_data['value']
                                confidence = fact_data['confidence']
                                
                                # Validate confidence score
                                if isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0:
                                    if value is not None and str(value).strip():
                                        cleaned_facts[key] = {
                                            'value': value,
                                            'confidence': float(confidence)
                                        }
                    
                    return cleaned_facts
            
            # Fallback: handle old format without confidence scores
            elif isinstance(response_data, dict):
                # Convert old format to new format with default confidence
                cleaned_facts = {}
                for key, value in response_data.items():
                    if isinstance(key, str) and value is not None and str(value).strip():
                        cleaned_facts[key] = {
                            'value': value,
                            'confidence': 0.8  # Default confidence for old format
                        }
                return cleaned_facts
        
        print("⚠️ Could not parse valid JSON from fact extraction response")
        return {}
        
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parsing error in fact extraction: {e}")
        return {}
    except Exception as e:
        print(f"⚠️ Unexpected error parsing extracted facts: {e}")
        return {}


def _filter_by_confidence(facts_with_confidence: Dict[str, Dict[str, Any]], 
                         threshold: float = 0.8) -> Dict[str, Any]:
    """
    Filter facts by confidence threshold and return simple fact dictionary.
    
    Args:
        facts_with_confidence: Dictionary with confidence scores
        threshold: Minimum confidence threshold (default 0.8)
        
    Returns:
        Dictionary of facts that meet the confidence threshold
    """
    filtered_facts = {}
    confidence_scores = {}
    
    for key, fact_data in facts_with_confidence.items():
        confidence = fact_data.get('confidence', 0.0)
        value = fact_data.get('value')
        
        if confidence >= threshold:
            filtered_facts[key] = value
            confidence_scores[key] = confidence
        else:
            print(f"⚠️ Filtered out fact '{key}' due to low confidence: {confidence}")
    
    # Store confidence scores in a way that can be accessed later
    # This is a bit of a hack, but we'll store it as a module-level variable
    # In a real implementation, this should be handled more elegantly
    global _last_confidence_scores
    _last_confidence_scores = confidence_scores
    
    return filtered_facts


def _parse_extracted_facts(raw_facts: str) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Parse and validate extracted facts from LLM response.
    
    Args:
        raw_facts: Raw response from fact extraction LLM
        
    Returns:
        Dictionary of parsed and validated facts
    """
    # Use the new confidence-aware parsing but return only the values
    facts_with_confidence = _parse_extracted_facts_with_confidence(raw_facts)
    
    # Extract just the values
    simple_facts = {}
    for key, fact_data in facts_with_confidence.items():
        simple_facts[key] = fact_data['value']
    
    return simple_facts


def _merge_facts_with_conflict_resolution(existing_facts: Dict[str, Any], 
                                        new_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new facts with existing facts, handling conflicts intelligently.
    
    Args:
        existing_facts: Current user facts
        new_facts: Newly extracted facts
        
    Returns:
        Merged facts dictionary with conflicts resolved
    """
    merged = existing_facts.copy()
    
    for key, new_value in new_facts.items():
        if key in merged:
            existing_value = merged[key]
            
            # Handle different conflict resolution strategies
            if isinstance(existing_value, dict) and isinstance(new_value, dict):
                # Recursively merge nested dictionaries
                merged[key] = _merge_facts_with_conflict_resolution(existing_value, new_value)
            elif existing_value != new_value:
                # For conflicting values, prefer the new value but log the conflict
                print(f"⚠️ Fact conflict for '{key}': '{existing_value}' -> '{new_value}'")
                merged[key] = new_value
        else:
            # New key, just add it
            merged[key] = new_value
    
    return merged