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
                # Build a comprehensive retrieval query that includes user context
                retrieval_query = _build_retrieval_query(
                    question=state['question'],
                    user_facts=user_facts,
                    conversation_history=state.get('conversation_history', []),
                    intent=state.get('intent')
                )
                
                print(f"🔍 Retrieval query: {retrieval_query[:200]}...")
                
                docs = nodes.retriever.get_relevant_documents(retrieval_query)

                # Enhanced re-ranking that considers user memory and question context
                def _enhanced_score(doc_obj) -> float:
                    doc_text = getattr(doc_obj, 'page_content', '') or ''
                    lowered = doc_text.lower()
                    score = 0.0
                    
                    # Base score from question overlap
                    for token in state['question'].lower().split():
                        if len(token) > 3 and token in lowered:
                            score += 1.0
                    
                    # Bonus score for user memory relevance
                    for fact_key, fact_value in user_facts.items():
                        if isinstance(fact_value, dict) and 'value' in fact_value:
                            fact_text = str(fact_value['value']).lower()
                        else:
                            fact_text = str(fact_value).lower()
                        
                        # Check if document content relates to user's known facts
                        if fact_text in lowered:
                            score += 2.0  # Higher weight for memory relevance
                    
                    # Bonus for document source relevance
                    source = getattr(doc_obj, 'metadata', {}).get('source', '').lower()
                    if any(keyword in source for keyword in ['wellness', 'cronograma', 'plan de trabajo']):
                        score += 1.5  # Bonus for relevant document types
                    elif any(keyword in source for keyword in ['fuxion', 'products', 'productos', 'catalog', 'catálogo']):
                        score += 2.0  # Higher bonus for Fuxion products
                    
                    # Special bonus for capabilities questions - prioritize diverse document types
                    if _is_capabilities_question(state['question']):
                        # For capabilities questions, ensure we get a good mix of document types
                        if 'wellness' in source or 'plan de trabajo' in source:
                            score += 3.0  # High bonus for wellness app plans
                        elif 'cronograma' in source or 'timeline' in source:
                            score += 3.0  # High bonus for project timelines
                        elif 'fuxion' in source or 'products' in source:
                            score += 3.0  # High bonus for Fuxion products
                        elif any(keyword in source for keyword in ['business', 'legal', 'formation']):
                            score += 2.5  # Bonus for business formation docs
                    
                    # Special bonus for workstream queries - prioritize the specific workstream content
                    if any(keyword in state['question'].lower() for keyword in ['workstream', 'ws']):
                        import re
                        ws_matches = re.findall(r'ws\s*(\d+)', state['question'].lower())
                        if ws_matches:
                            target_ws = ws_matches[0]
                            if f'ws{target_ws}' in lowered or f'workstream {target_ws}' in lowered:
                                score += 5.0  # Very high bonus for the specific workstream
                                print(f"🎯 Boosting score for WS{target_ws} content: +5.0")
                        # General bonus for wellness app plan documents in workstream queries
                        if 'wellness' in source or 'plan de trabajo' in source:
                            score += 2.0  # Bonus for wellness app plans in workstream queries
                    
                    return score

                ranked_docs = sorted(docs, key=_enhanced_score, reverse=True)

                # Apply budget: top N docs and total char cap
                MAX_DOCS = 8  # Increased from 6
                MAX_TOTAL_CHARS = 15000  # Increased from 12000
                MAX_PER_DOC_CHARS = 2500  # Increased from 2200
                
                # Increase limits for capabilities questions to provide comprehensive overview
                if _is_capabilities_question(state['question']):
                    MAX_DOCS = 12  # Get more documents for comprehensive capabilities overview
                    MAX_TOTAL_CHARS = 35000  # Much higher total character limit for capabilities
                    MAX_PER_DOC_CHARS = 4000  # Higher per-document limit to preserve context
                    print(f"🎯 Capabilities question detected - Using increased limits: {MAX_PER_DOC_CHARS} chars per doc, {MAX_TOTAL_CHARS} total")
                
                # Increase limits for product-related queries to preserve product names
                elif state.get('intent') == 'product_recommendation' or any(
                    keyword in state['question'].lower() for keyword in 
                    ['product', 'fuxion', 'supplement', 'sku', 'catalog', 'producto', 'suplemento', 'catálogo', 'fuxión']
                ):
                    MAX_TOTAL_CHARS = 25000  # Increased total character limit for product queries
                    MAX_PER_DOC_CHARS = 4000  # Increased per-document limit to preserve product details
                    print(f"🔍 Product query detected - Using increased limits: {MAX_PER_DOC_CHARS} chars per doc, {MAX_TOTAL_CHARS} total")
                
                # Increase limits for complex document queries (cronograma, wellness app plan)
                elif any(keyword in state['question'].lower() for keyword in 
                        ['cronograma', 'timeline', 'schedule', 'plan', 'workstream', 'ws', 'fase', 'gate', 'wellness', 'app']):
                    MAX_TOTAL_CHARS = 30000  # Much higher total character limit for complex docs
                    MAX_PER_DOC_CHARS = 6000  # Higher per-document limit to preserve context
                    print(f"🔍 Complex document query detected - Using increased limits: {MAX_PER_DOC_CHARS} chars per doc, {MAX_TOTAL_CHARS} total")
                
                # Special handling for workstream queries - ensure comprehensive coverage
                elif any(keyword in state['question'].lower() for keyword in ['workstream', 'ws']):
                    MAX_DOCS = 10  # Get more documents for comprehensive workstream coverage
                    MAX_TOTAL_CHARS = 35000  # Higher total character limit for workstream queries
                    MAX_PER_DOC_CHARS = 7000  # Higher per-document limit to preserve complete workstream sections
                    print(f"🎯 Workstream query detected - Using comprehensive limits: {MAX_PER_DOC_CHARS} chars per doc, {MAX_TOTAL_CHARS} total")
                
                # Increase limits for general project/planning queries
                elif any(keyword in state['question'].lower() for keyword in 
                        ['project', 'development', 'implementation', 'roadmap', 'milestone', 'deliverable']):
                    MAX_TOTAL_CHARS = 25000  # Higher total character limit for project docs
                    MAX_PER_DOC_CHARS = 5000  # Higher per-document limit
                    print(f"🔍 Project/planning query detected - Using increased limits: {MAX_PER_DOC_CHARS} chars per doc, {MAX_TOTAL_CHARS} total")
                
                total = 0
                for doc_item in ranked_docs[:MAX_DOCS]:
                    content = getattr(doc_item, 'page_content', '') or ''
                    if not content:
                        continue
                    
                    # Smart truncation: preserve product entries for Fuxion Products
                    truncated = content
                    source = getattr(doc_item, 'metadata', {}).get('source', '').lower()
                    
                    if 'fuxion products' in source and len(content) > MAX_PER_DOC_CHARS:
                        # For Fuxion Products, truncate at product boundaries
                        truncated = _smart_truncate_fuxion_products(content, MAX_PER_DOC_CHARS)
                        print(f"🎯 Smart truncation applied to Fuxion Products - preserved {len(truncated)} chars")
                    elif any(keyword in source for keyword in ['cronograma', 'wellness', 'plan de trabajo']) and len(content) > MAX_PER_DOC_CHARS:
                        # For complex documents, truncate at logical section boundaries
                        truncated = _smart_truncate_complex_documents(content, MAX_PER_DOC_CHARS, source)
                        print(f"🎯 Smart truncation applied to complex document - preserved {len(truncated)} chars")
                    else:
                        # Standard truncation for other documents
                        truncated = content[:MAX_PER_DOC_CHARS]
                    
                    if total + len(truncated) > MAX_TOTAL_CHARS:
                        remaining = max(0, MAX_TOTAL_CHARS - total)
                        if remaining == 0:
                            break
                        truncated = truncated[:remaining]
                    retrieved_docs.append(truncated)
                    total += len(truncated)

                print(f"✅ Retrieved {len(retrieved_docs)} relevant documents (budgeted {total} chars)")
                
                # Log document sources for debugging
                if retrieved_docs:
                    print("📚 Document sources retrieved:")
                    for i, doc_item in enumerate(ranked_docs[:len(retrieved_docs)]):
                        source = getattr(doc_item, 'metadata', {}).get('source', 'Unknown')
                        print(f"  {i+1}. {source}")
            else:
                print("⚠️ Warning: FAISS retriever not available")
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve documents: {e}")
            retrieved_docs = []
        
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
            state['user_facts'], state['retrieved_docs'], conversation_context, state
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

            # Use specialized capabilities prompt for capabilities questions
            if _is_capabilities_question(state['question']):
                print("🎯 Using specialized capabilities prompt")
                prompt = nodes.prompt_registry.get(
                    "capabilities",
                    user_facts=engineered_context["user_facts_str"],
                    context=context_for_prompt,
                    conversation=engineered_context["conversation_context"],
                    question=state['question']
                )
            # Use product recommendation prompt for product recommendation intents
            elif state.get('intent') == 'product_recommendation':
                prompt = nodes.prompt_registry.get(
                    "product_recommendation",
                    user_facts=engineered_context["user_facts_str"],
                    context=context_for_prompt,
                    question=state['question']
                )
            else:
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
            
            # 3. Validate response and ensure product names are preserved
            if not answer or len(answer.strip()) == 0:
                answer = "I apologize, but I couldn't generate a proper response to your question. Please try rephrasing it."
            else:
                # Post-processing validation for product recommendations
                if state.get('intent') == 'product_recommendation':
                    answer = _validate_product_names_in_response(answer, context_for_prompt)
            
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
        
        # Use specialized fact extraction for wellness app and cronograma related questions
        question_lower = state['question'].lower()
        if any(keyword in question_lower for keyword in ['wellness', 'app', 'workstream', 'ws', 'plan de trabajo']):
            print("🎯 Using wellness app specialized fact extraction")
            fact_extraction_prompt = nodes.prompt_registry.get(
                "fact_extraction",
                conversation_text=conversation_text,
                existing_facts=existing_facts_str,
                domain_hint="wellness_app_development"
            )
        elif any(keyword in question_lower for keyword in ['cronograma', 'timeline', 'schedule', 'gate', 'phase', 'project']):
            print("🎯 Using project timeline specialized fact extraction")
            fact_extraction_prompt = nodes.prompt_registry.get(
                "fact_extraction",
                conversation_text=conversation_text,
                existing_facts=existing_facts_str,
                domain_hint="project_timeline"
            )
        elif any(keyword in question_lower for keyword in ['fuxion', 'product', 'supplement', 'fuxión', 'producto', 'suplemento']):
            print("🎯 Using Fuxion products specialized fact extraction")
            fact_extraction_prompt = nodes.prompt_registry.get(
                "fact_extraction",
                conversation_text=conversation_text,
                existing_facts=existing_facts_str,
                domain_hint="fuxion_products"
            )
        else:
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
            
            # Post-process extracted facts for wellness app and cronograma domains
            extracted_facts = _post_process_domain_facts(extracted_facts, question_lower)
            
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
        
        # Check if this is actually a capabilities question that should go through full workflow
        if _is_capabilities_question(state['question']):
            print("🎯 Capabilities question detected in lightweight path - redirecting to full workflow")
            # This should not happen with proper routing, but provide a helpful response
            answer = "I'm your AI Co-founder assistant with access to comprehensive business documents and plans! I can help you with wellness app development plans, project timelines, Fuxion product recommendations, and business formation guidance. For detailed information about my capabilities and to explore your documents, please ask a more specific question about any of these areas."
        
        # Handle greetings with concise responses; tailor for first vs subsequent turn
        elif state['question_type'] == 'greeting':
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

def _engineer_context(user_facts: Dict[str, Any], retrieved_docs: List[str], conversation_context: Optional[str] = None, state: Dict = None) -> Dict[str, str]:
    """
    Combine user facts with document context for prompt engineering.
    
    This function intelligently combines user memory with retrieved documents to create
    comprehensive context that helps the LLM generate better responses.
    
    Args:
        user_facts: Dictionary of user facts from memory
        retrieved_docs: List of retrieved document contents
        conversation_context: Optional conversation history summary
        
    Returns:
        Dictionary with formatted user_facts_str, document_context, and conversation_context
    """
    # Format user facts for prompt with better structure
    if user_facts:
        facts_items = []
        priority_facts = []
        regular_facts = []
        
        # Separate priority facts (identity, preferences) from regular facts
        priority_keys = {'name', 'user_name', 'full_name', 'preferences', 'goals', 'target_market'}
        
        for key, value in user_facts.items():
            if isinstance(value, dict):
                # Handle nested dictionaries (like preferences)
                for sub_key, sub_value in value.items():
                    fact_line = f"- {key}.{sub_key}: {sub_value}"
                    if key in priority_keys:
                        priority_facts.append(fact_line)
                    else:
                        regular_facts.append(fact_line)
            else:
                fact_line = f"- {key}: {value}"
                if key in priority_keys:
                    priority_facts.append(fact_line)
                else:
                    regular_facts.append(fact_line)
        
        # Combine priority facts first, then regular facts
        facts_items = priority_facts + regular_facts
        user_facts_str = "\n".join(facts_items)
        
        print(f"🧠 Context engineering: {len(priority_facts)} priority facts, {len(regular_facts)} regular facts")
    else:
        user_facts_str = "No background information available for this user."
    
    # Format document context with better structure and intelligent categorization
    if retrieved_docs:
        # Group documents by type and provide intelligent summaries
        wellness_docs = []
        cronograma_docs = []
        product_docs = []
        other_docs = []
        
        # Check if this is a specific workstream query
        question_lower = state.get('question', '').lower()
        is_workstream_query = any(keyword in question_lower for keyword in ['workstream', 'ws'])
        
        # Extract workstream number if present
        workstream_number = None
        if is_workstream_query:
            import re
            ws_matches = re.findall(r'ws\s*(\d+)', question_lower)
            if ws_matches:
                workstream_number = ws_matches[0]
            else:
                # Also check for "workstream X" format
                ws_text_matches = re.findall(r'workstream\s*(\d+)', question_lower)
                if ws_text_matches:
                    workstream_number = ws_text_matches[0]
        
        for doc in retrieved_docs:
            # Simple heuristic to categorize documents
            doc_lower = doc.lower()
            if any(keyword in doc_lower for keyword in ['wellness', 'workstream', 'ws', 'plan de trabajo']):
                wellness_docs.append(doc)
            elif any(keyword in doc_lower for keyword in ['cronograma', 'timeline', 'gate', 'phase']):
                cronograma_docs.append(doc)
            elif any(keyword in doc_lower for keyword in ['fuxion', 'product', 'sku', 'supplement', 'fuxión', 'producto', 'suplemento']):
                product_docs.append(doc)
            else:
                other_docs.append(doc)
        
        # If this is a specific workstream query, prioritize the relevant workstream content
        if is_workstream_query and workstream_number:
            print(f"🎯 Workstream query detected for WS{workstream_number} - Prioritizing relevant content")
            
            # Re-sort wellness docs to prioritize the specific workstream
            def prioritize_workstream(doc):
                doc_lower = doc.lower()
                if f'ws{workstream_number}' in doc_lower or f'workstream {workstream_number}' in doc_lower:
                    return 0  # Highest priority
                elif any(f'ws{i}' in doc_lower for i in range(1, 10) if str(i) != workstream_number):
                    return 1  # Other workstreams
                else:
                    return 2  # Non-workstream content
            
            wellness_docs.sort(key=prioritize_workstream)
        
        # Build structured document context with intelligent summaries
        doc_sections = []
        
        if wellness_docs:
            # Check if this is a specific workstream query to customize the summary
            question_lower = state.get('question', '').lower()
            is_workstream_query = any(keyword in question_lower for keyword in ['workstream', 'ws'])
            workstream_number = None
            
            if is_workstream_query:
                import re
                ws_matches = re.findall(r'ws\s*(\d+)', question_lower)
                if ws_matches:
                    workstream_number = ws_matches[0]
                else:
                    ws_text_matches = re.findall(r'workstream\s*(\d+)', question_lower)
                    if ws_text_matches:
                        workstream_number = ws_text_matches[0]
            
            if workstream_number:
                wellness_summary = _create_workstream_specific_summary(wellness_docs, workstream_number)
                doc_sections.append(f"WORKSTREAM {workstream_number} DETAILS:\n{wellness_summary}")
            else:
                wellness_summary = _create_wellness_summary(wellness_docs)
                doc_sections.append(f"WELLNESS APP DEVELOPMENT PLAN:\n{wellness_summary}")
        
        if cronograma_docs:
            cronograma_summary = _create_cronograma_summary(cronograma_docs)
            doc_sections.append(f"PROJECT TIMELINE (CRONOGRAMA):\n{cronograma_summary}")
        
        if product_docs:
            product_summary = _create_product_summary(product_docs)
            doc_sections.append(f"FUXION PRODUCTS / PRODUCTOS FUXION:\n{product_summary}")
        
        if other_docs:
            other_summary = _create_other_docs_summary(other_docs)
            doc_sections.append(f"OTHER RELEVANT DOCUMENTS:\n{other_summary}")
        
        document_context = "\n\n" + "\n\n".join(doc_sections)
        
        print(f"📚 Context engineering: {len(wellness_docs)} wellness docs, {len(cronograma_docs)} cronograma docs, {len(product_docs)} product docs, {len(other_docs)} other docs")
    else:
        document_context = "No relevant documents found."
    
    # Format conversation context
    if conversation_context:
        conversation_context = f"Recent conversation context:\n{conversation_context}"
    else:
        conversation_context = "No recent conversation context available."
    
    return {
        "user_facts_str": user_facts_str,
        "document_context": document_context,
        "conversation_context": conversation_context
    }


def _build_retrieval_query(question: str, user_facts: Dict[str, Any], conversation_history: List[Dict[str, Any]], intent: str = None) -> str:
    """
    Build a richer retrieval query using the question, user facts, and conversation context.
    
    This function creates comprehensive queries that help retrieve the most relevant documents
    by incorporating user memory and conversation context.
    """
    # Take top few facts for query enrichment
    fact_items: List[str] = []
    for key, value in list(user_facts.items())[:8]:  # Increased from 5
        if isinstance(value, dict):
            # Include one nested item per nested dict to keep query short
            for sub_key, sub_value in value.items():
                if sub_key in ['value', 'name', 'type', 'category']:  # Prioritize key fields
                    fact_items.append(f"{key}.{sub_key}={sub_value}")
                    break
        else:
            fact_items.append(f"{key}={value}")

    recent_summary = _summarize_recent_conversation(conversation_history, max_chars=400)  # Increased from 280
    enriched = " ".join(fact_items)
    parts = [question]
    
    # Special handling for capabilities questions - retrieve comprehensive document overview
    if _is_capabilities_question(question):
        parts.extend([
            "wellness app development plan workstreams objectives implementation",
            "project timeline cronograma phases gates milestones schedule roadmap",
            "Fuxion products supplements catalog SKU weight loss nutrition health wellness",
            "business formation entrepreneurship legal compliance financial planning",
            "document types available access read analyze"
        ])
        print("🎯 Capabilities question detected - Using comprehensive retrieval query")
    
    # Enhance query for product recommendations to prioritize Fuxion products
    elif intent == 'product_recommendation':
        parts.append("Fuxion products weight loss nutrition supplements")
    
    # Enhance query for Fuxion product related questions (both languages)
    elif any(keyword in question.lower() for keyword in ['fuxion', 'product', 'supplement', 'fuxión', 'producto', 'suplemento']):
        parts.append("Fuxion products supplements catalog SKU weight loss nutrition health wellness")
        parts.append("productos Fuxion suplementos catálogo pérdida de peso nutrición salud")
    
    # Enhance query for wellness app and cronograma related questions
    elif any(keyword in question.lower() for keyword in ['wellness', 'app', 'plan', 'workstream', 'ws']):
        parts.append("wellness app development plan workstreams objectives implementation phases milestones")
    
    elif any(keyword in question.lower() for keyword in ['cronograma', 'timeline', 'schedule', 'gate', 'phase']):
        parts.append("project timeline cronograma phases gates milestones schedule roadmap")
    
    # Add user facts context if available
    if enriched:
        parts.append(f"[user context: {enriched}]")
    
    # Add recent conversation context if available
    if recent_summary:
        parts.append(f"[conversation context: {recent_summary}]")
    
    # Add document type hints for better retrieval
    if any(keyword in question.lower() for keyword in ['plan', 'document', 'report', 'file']):
        parts.append("document plan report file content")
    
    final_query = " ".join(parts)
    print(f"🔍 Built comprehensive retrieval query: {final_query[:300]}...")
    
    return final_query


def _is_capabilities_question(question: str) -> bool:
    """Check if the question is asking about the agent's capabilities or functionality."""
    try:
        question_lower = question.lower()
        
        # Capabilities and functionality question patterns
        capabilities_patterns = [
            # Direct capability questions
            r'\b(what are|what is|tell me about|explain) (your|the) (capabilities|abilities|features|functions|skills)\b',
            r'\b(what can|what do) you (do|help with|assist with|support)\b',
            r'\b(how do|how can) you (help|assist|support|work)\b',
            r'\b(what is|what does) this (agent|assistant|system|tool) (do|help with)\b',
            r'\b(can you|do you) (help|assist|support|work) (with|on)\b',
            
            # Document access questions
            r'\b(what|which) (documents|docs|files|plans|products) (can|do) you (see|access|read|know about)\b',
            r'\b(do you|can you) (see|access|read|know about) (my|the) (documents|docs|files)\b',
            r'\b(what|which) (files|documents|plans|products) (are|do) you (aware of|familiar with)\b',
            
            # General functionality questions
            r'\b(what|how) (does|can|will) this (work|function|operate)\b',
            r'\b(explain|describe) (how|what) (this|you) (works|does|functions)\b',
            r'\b(what|which) (features|capabilities|functions) (are|do) (available|you have)\b'
        ]
        
        # Check for capabilities question patterns
        import re
        for pattern in capabilities_patterns:
            if re.search(pattern, question_lower):
                return True
        
        # Also check for common capability question keywords
        capability_keywords = [
            'capabilities', 'abilities', 'features', 'functions', 'skills',
            'what can you do', 'how do you work', 'what do you help with',
            'what documents', 'what files', 'what plans', 'what products'
        ]
        
        for keyword in capability_keywords:
            if keyword in question_lower:
                return True
        
        return False
    except Exception as e:
        print(f"⚠️ Error checking capabilities keywords: {e}")
        return False


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


def _validate_product_names_in_response(answer: str, context: str) -> str:
    """
    Validate and correct product names in the response to ensure they match the Fuxion catalog.
    
    Args:
        answer: The generated answer from the LLM
        context: The context used to generate the answer (should contain Fuxion products)
        
    Returns:
        Corrected answer with proper product names
    """
    import re
    
    # Extract all product names from the context (Fuxion catalog)
    product_pattern = r'\*\*([^*]+)\*\*'
    catalog_products = set(re.findall(product_pattern, context))
    
    # Common product name variations that might need correction
    product_corrections = {
        'alpha balance': 'ALPHA BALANCE',
        'beauty-in': 'BEAUTY-IN',
        'berry balance': 'BERRY BALANCE',
        'biopro': 'BIOPRO+',
        'café': 'CAFÉ & CAFÉ FIT',
        'chocolate fit': 'CHOCOLATE FIT',
        'flora liv': 'FLORA LIV',
        'passion': 'PASSION',
        'prunex': 'PRUNEX1',
        'thermo': 'THERMO T3',
        'vita xtra': 'VITA XTRA T+',
        'gano': 'CAFÉ GANOMAX',
        'golden flx': 'GOLDEN FLX',
        'liquid fiber': 'LIQUID FIBER',
        'no stress': 'NO STRESS',
        'nutraday': 'NUTRA DAY',
        'protein': 'PROTEIN ACTIVE',
        'rexet': 'REXET',
        'vera': 'VERA+',
        'vitaenergia': 'VITAENERGIA',
        'xpeed': 'XPEED',
        'xtra mile': 'XTRA MILE',
        'youth elixir': 'YOUTH ELIXIR'
    }
    
    # Check if the answer contains any product names that need correction
    corrected_answer = answer
    
    for wrong_name, correct_name in product_corrections.items():
        # Look for variations of the wrong name in the answer
        wrong_pattern = re.compile(r'\b' + re.escape(wrong_name) + r'\b', re.IGNORECASE)
        if wrong_pattern.search(corrected_answer):
            # Replace with the correct name
            corrected_answer = wrong_pattern.sub(correct_name, corrected_answer)
            print(f"🔧 Corrected product name: '{wrong_name}' -> '{correct_name}'")
    
    # Also check for any product names that might be missing the ** formatting
    for product_name in catalog_products:
        # Look for product names without proper formatting
        unformatted_pattern = re.compile(r'\b' + re.escape(product_name) + r'\b', re.IGNORECASE)
        if unformatted_pattern.search(corrected_answer):
            # Ensure it's properly formatted with **
            formatted_pattern = re.compile(r'\*\*' + re.escape(product_name) + r'\*\*', re.IGNORECASE)
            if not formatted_pattern.search(corrected_answer):
                # Add proper formatting
                corrected_answer = unformatted_pattern.sub(f'**{product_name}**', corrected_answer)
                print(f"🔧 Added proper formatting to product name: '{product_name}'")
    
    return corrected_answer


def _smart_truncate_fuxion_products(self, content: str, max_chars: int) -> str:
    """
    Intelligently truncate Fuxion Products content to preserve complete product entries.
    
    Args:
        content: Full Fuxion Products document content
        max_chars: Maximum characters to preserve
        
    Returns:
        Truncated content that preserves complete product entries
    """
    if len(content) <= max_chars:
        return content
    
    # Look for product boundaries (numbered entries like "1. **PRODUCT NAME**")
    import re
    
    # Find all product entry boundaries
    product_pattern = r'\n(\d+\.\s+\*\*[^*]+\*\*)'
    matches = list(re.finditer(product_pattern, content))
    
    if not matches:
        # Fallback to standard truncation if no product boundaries found
        return content[:max_chars]
    
    # Find the last complete product entry that fits within the limit
    for i, match in enumerate(matches):
        if i == len(matches) - 1:
            # Last product, truncate at the end
            end_pos = len(content)
        else:
            # Truncate before the next product starts
            end_pos = matches[i + 1].start()
        
        truncated_content = content[:end_pos]
        
        if len(truncated_content) <= max_chars:
            # This truncation fits within limits
            return truncated_content
    
    # If we can't fit even one complete product, fall back to standard truncation
    # but try to preserve at least the first product name
    first_product_end = matches[0].end() + 500  # Include some description
    if first_product_end <= max_chars:
        return content[:first_product_end]
    
    # Final fallback: standard truncation
    return content[:max_chars]


def _smart_truncate_complex_documents(content: str, max_chars: int, source: str) -> str:
    """
    Intelligently truncate complex documents (cronograma, wellness app plan) to preserve logical sections.
    
    Args:
        content: Full document content
        max_chars: Maximum characters to preserve
        source: Document source filename
        
    Returns:
        Truncated content that preserves logical sections
    """
    if len(content) <= max_chars:
        return content
    
    import re
    
    # Different truncation strategies based on document type
    if 'cronograma' in source.lower():
        return _truncate_cronograma_at_boundaries(content, max_chars)
    elif 'wellness' in source.lower() or 'plan de trabajo' in source.lower():
        return _truncate_wellness_plan_at_boundaries(content, max_chars)
    else:
        # Generic truncation for other complex documents
        return _truncate_generic_at_boundaries(content, max_chars)

def _truncate_cronograma_at_boundaries(content: str, max_chars: int) -> str:
    """Truncate cronograma at phase/gate boundaries"""
    import re
    
    # Look for phase and gate boundaries
    boundary_pattern = r'(Fase\s+\d+\.\s*[^\n]+|Gate\s+\d+\.\s*[^\n]+|Semana\s+\d+\.\s*[^\n]+)'
    boundaries = list(re.finditer(boundary_pattern, content))
    
    if not boundaries:
        return content[:max_chars]
    
    # Find the last complete section that fits within the limit
    for i, boundary in enumerate(boundaries):
        if i == len(boundaries) - 1:
            # Last boundary, truncate at the end
            end_pos = len(content)
        else:
            # Truncate before the next boundary starts
            end_pos = boundaries[i + 1].start()
        
        truncated_content = content[:end_pos]
        
        if len(truncated_content) <= max_chars:
            # This truncation fits within limits
            return truncated_content
    
    # If we can't fit even one complete section, preserve at least the first phase
    first_boundary_end = boundaries[0].end() + 800  # Include some description
    if first_boundary_end <= max_chars:
        return content[:first_boundary_end]
    
    # Final fallback: standard truncation
    return content[:max_chars]

def _truncate_wellness_plan_at_boundaries(content: str, max_chars: int) -> str:
    """Truncate wellness app plan at workstream boundaries"""
    import re
    
    # Look for workstream and major section boundaries
    boundary_pattern = r'(WS\d+\.\s*[^\n]+|Objetivo\s*:|Alcance\s*y\s*supuestos|Efectos\s*WOW|Entregables\s*:|Tareas\s*:)'
    boundaries = list(re.finditer(boundary_pattern, content))
    
    if not boundaries:
        return content[:max_chars]
    
    # Find the last complete section that fits within the limit
    for i, boundary in enumerate(boundaries):
        if i == len(boundaries) - 1:
            # Last boundary, truncate at the end
            end_pos = len(content)
        else:
            # Truncate before the next boundary starts
            end_pos = boundaries[i + 1].start()
        
        truncated_content = content[:end_pos]
        
        if len(truncated_content) <= max_chars:
            # This truncation fits within limits
            return truncated_content
    
    # If we can't fit even one complete section, preserve at least the first workstream
    first_boundary_end = boundaries[0].end() + 1000  # Include more description for workstreams
    if first_boundary_end <= max_chars:
        return content[:first_boundary_end]
    
    # Final fallback: standard truncation
    return content[:max_chars]

def _truncate_generic_at_boundaries(content: str, max_chars: int) -> str:
    """Generic truncation for other complex documents"""
    import re
    
    # Look for common section boundaries
    boundary_pattern = r'(\n\n\d+\.\s*[^\n]+|\n\n[A-Z][^\n]*:|\n\n[A-Z][A-Z\s]+\n)'
    boundaries = list(re.finditer(boundary_pattern, content))
    
    if not boundaries:
        return content[:max_chars]
    
    # Find the last complete section that fits within the limit
    for i, boundary in enumerate(boundaries):
        if i == len(boundaries) - 1:
            # Last boundary, truncate at the end
            end_pos = len(content)
        else:
            # Truncate before the next boundary starts
            end_pos = boundaries[i + 1].start()
        
        truncated_content = content[:end_pos]
        
        if len(truncated_content) <= max_chars:
            # This truncation fits within limits
            return truncated_content
    
    # If we can't fit even one complete section, preserve at least the first section
    first_boundary_end = boundaries[0].end() + 600  # Include some description
    if first_boundary_end <= max_chars:
        return content[:first_boundary_end]
    
    # Final fallback: standard truncation
    return content[:max_chars]


def _post_process_domain_facts(extracted_facts: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Post-process extracted facts for specific domains to improve quality and consistency.
    
    Args:
        extracted_facts: Raw extracted facts
        question: Original question for context
        
    Returns:
        Dict: Post-processed facts
    """
    if not extracted_facts:
        return extracted_facts
    
    processed_facts = {}
    
    # Wellness app domain processing
    if any(keyword in question for keyword in ['wellness', 'app', 'workstream', 'ws']):
        for key, value in extracted_facts.items():
            # Normalize workstream keys
            if 'workstream' in key.lower() or 'ws' in key.lower():
                normalized_key = 'workstreams'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            # Normalize objective/goal keys
            elif any(goal_key in key.lower() for goal_key in ['objective', 'goal', 'objetivo']):
                normalized_key = 'objectives'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            else:
                processed_facts[key] = value
    
    # Fuxion products domain processing
    elif any(keyword in question for keyword in ['fuxion', 'product', 'supplement', 'fuxión', 'producto', 'suplemento']):
        for key, value in extracted_facts.items():
            # Normalize product keys
            if any(product_key in key.lower() for product_key in ['product', 'producto', 'supplement', 'suplemento']):
                normalized_key = 'products'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            # Normalize category keys
            elif any(cat_key in key.lower() for cat_key in ['category', 'categoría', 'type', 'tipo']):
                normalized_key = 'categories'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            else:
                processed_facts[key] = value
    
    # Project timeline domain processing
    elif any(keyword in question for keyword in ['cronograma', 'timeline', 'schedule', 'gate', 'phase']):
        for key, value in extracted_facts.items():
            # Normalize phase keys
            if 'phase' in key.lower() or 'fase' in key.lower():
                normalized_key = 'phases'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            # Normalize gate/milestone keys
            elif any(gate_key in key.lower() for gate_key in ['gate', 'milestone', 'hito']):
                normalized_key = 'milestones'
                if normalized_key not in processed_facts:
                    processed_facts[normalized_key] = []
                if isinstance(value, list):
                    processed_facts[normalized_key].extend(value)
                else:
                    processed_facts[normalized_key].append(value)
            else:
                processed_facts[key] = value
    
    else:
        # Default processing for other domains
        processed_facts = extracted_facts
    
    return processed_facts

def _create_wellness_summary(docs: List[str]) -> str:
    """Create an intelligent summary of wellness app development documents."""
    try:
        summary_parts = []
        
        # Extract key workstreams and objectives
        workstreams = []
        objectives = []
        
        for doc in docs:
            doc_lower = doc.lower()
            
            # Extract workstream information
            import re
            ws_matches = re.findall(r'ws\d+\.\s*([^\n]+)', doc, re.IGNORECASE)
            workstreams.extend(ws_matches)
            
            # Extract objectives
            obj_matches = re.findall(r'objetivo[s]?\s*:\s*([^\n]+)', doc, re.IGNORECASE)
            objectives.extend(obj_matches)
        
        if workstreams:
            summary_parts.append(f"Key Workstreams: {', '.join(workstreams[:5])}")
        
        if objectives:
            summary_parts.append(f"Main Objectives: {', '.join(objectives[:3])}")
        
        # Add document count and key topics
        summary_parts.append(f"Document Coverage: {len(docs)} wellness app development documents")
        summary_parts.append("Topics include: workstream planning, implementation phases, deliverables, and project milestones")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        print(f"⚠️ Error creating wellness summary: {e}")
        return f"Comprehensive wellness app development plan with {len(docs)} documents covering workstreams, objectives, and implementation phases."

def _create_workstream_specific_summary(docs: List[str], workstream_number: str) -> str:
    """Create a detailed summary focused on a specific workstream."""
    try:
        summary_parts = []
        
        # Find the specific workstream content
        target_workstream = None
        for doc in docs:
            doc_lower = doc.lower()
            if f'ws{workstream_number}' in doc_lower or f'workstream {workstream_number}' in doc_lower:
                target_workstream = doc
                break
        
        if target_workstream:
            # Extract the specific workstream section
            lines = target_workstream.split('\n')
            ws_lines = []
            in_ws_section = False
            
            for line in lines:
                if f'ws{workstream_number}' in line.lower() or f'workstream {workstream_number}' in line.lower():
                    in_ws_section = True
                    ws_lines.append(line)
                elif in_ws_section and line.strip():
                    # Continue collecting lines until we hit another workstream or empty line
                    if line.strip().startswith('WS') and any(str(i) in line for i in range(1, 10) if str(i) != workstream_number):
                        break
                    ws_lines.append(line)
                elif in_ws_section and not line.strip():
                    # Empty line, continue collecting
                    ws_lines.append(line)
            
            if ws_lines:
                # Format the workstream content nicely
                formatted_content = []
                for line in ws_lines:
                    line = line.strip()
                    if line:
                        # Clean up formatting issues
                        line = line.replace('**', '')  # Remove extra asterisks
                        line = line.replace('  ', ' ')  # Fix double spaces
                        formatted_content.append(line)
                
                summary_parts.append(f"WORKSTREAM {workstream_number} DETAILS:")
                summary_parts.append("=" * 50)
                summary_parts.extend(formatted_content)
                summary_parts.append("=" * 50)
                
                # Add context about other available workstreams
                other_ws = []
                for doc in docs:
                    doc_lower = doc.lower()
                    for i in range(1, 10):
                        if f'ws{i}' in doc_lower and str(i) != workstream_number:
                            other_ws.append(f"WS{i}")
                
                if other_ws:
                    summary_parts.append(f"\nOther available workstreams: {', '.join(set(other_ws))}")
                
                return "\n".join(summary_parts)
        
        # Fallback if specific workstream not found
        summary_parts.append(f"WORKSTREAM {workstream_number} INFORMATION:")
        summary_parts.append("=" * 50)
        summary_parts.append(f"Workstream {workstream_number} details were requested but not found in the retrieved documents.")
        summary_parts.append("Available workstreams in the wellness app plan:")
        
        # List available workstreams
        available_ws = []
        for doc in docs:
            doc_lower = doc.lower()
            import re
            ws_matches = re.findall(r'ws\s*(\d+)', doc_lower)
            available_ws.extend(ws_matches)
        
        if available_ws:
            summary_parts.append(f"- WS{', WS'.join(sorted(set(available_ws), key=int))}")
        else:
            summary_parts.append("- No specific workstreams identified")
        
        summary_parts.append("=" * 50)
        return "\n".join(summary_parts)
        
    except Exception as e:
        print(f"⚠️ Error creating workstream-specific summary: {e}")
        return f"Error retrieving workstream {workstream_number} details. Please try rephrasing your question."

def _create_cronograma_summary(docs: List[str]) -> str:
    """Create an intelligent summary of project timeline documents."""
    try:
        summary_parts = []
        
        # Extract key phases and milestones
        phases = []
        milestones = []
        
        for doc in docs:
            doc_lower = doc.lower()
            
            # Extract phase information
            import re
            phase_matches = re.findall(r'fase\s+\d+\.\s*([^\n]+)', doc, re.IGNORECASE)
            phases.extend(phase_matches)
            
            # Extract gate/milestone information
            gate_matches = re.findall(r'gate\s+\d+\.\s*([^\n]+)', doc, re.IGNORECASE)
            milestones.extend(gate_matches)
        
        if phases:
            summary_parts.append(f"Key Phases: {', '.join(phases[:5])}")
        
        if milestones:
            summary_parts.append(f"Major Milestones: {', '.join(milestones[:5])}")
        
        # Add document count and key topics
        summary_parts.append(f"Document Coverage: {len(docs)} project timeline documents")
        summary_parts.append("Topics include: project phases, gates, milestones, deadlines, and scheduling")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        print(f"⚠️ Error creating cronograma summary: {e}")
        return f"Comprehensive project timeline with {len(docs)} documents covering phases, gates, milestones, and scheduling."

def _create_product_summary(docs: List[str]) -> str:
    """Create an intelligent summary of Fuxion product documents."""
    try:
        summary_parts = []
        
        # Extract product categories and key products
        categories = set()
        products = []
        
        for doc in docs:
            doc_lower = doc.lower()
            
            # Extract product names (formatted with **)
            import re
            product_matches = re.findall(r'\*\*([^*]+)\*\*', doc)
            products.extend(product_matches)
            
            # Extract categories
            if 'weight loss' in doc_lower or 'pérdida de peso' in doc_lower:
                categories.add('Weight Loss')
            if 'nutrition' in doc_lower or 'nutrición' in doc_lower:
                categories.add('Nutrition')
            if 'energy' in doc_lower or 'energía' in doc_lower:
                categories.add('Energy')
            if 'wellness' in doc_lower or 'bienestar' in doc_lower:
                categories.add('Wellness')
            if 'detox' in doc_lower:
                categories.add('Detox')
        
        if products:
            summary_parts.append(f"Available Products: {', '.join(products[:8])}")
        
        if categories:
            summary_parts.append(f"Product Categories: {', '.join(sorted(categories))}")
        
        # Add document count and key topics
        summary_parts.append(f"Document Coverage: {len(docs)} Fuxion product documents")
        summary_parts.append("Topics include: product catalog, SKUs, benefits, usage instructions, and nutritional information")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        print(f"⚠️ Error creating product summary: {e}")
        return f"Comprehensive Fuxion product catalog with {len(docs)} documents covering products, categories, and nutritional information."

def _create_other_docs_summary(docs: List[str]) -> str:
    """Create an intelligent summary of other document types."""
    try:
        summary_parts = []
        
        # Analyze document content for common themes
        themes = set()
        
        for doc in docs:
            doc_lower = doc.lower()
            
            if any(keyword in doc_lower for keyword in ['business', 'company', 'llc', 'corporation']):
                themes.add('Business Formation')
            if any(keyword in doc_lower for keyword in ['legal', 'compliance', 'regulation']):
                themes.add('Legal & Compliance')
            if any(keyword in doc_lower for keyword in ['financial', 'tax', 'accounting']):
                themes.add('Financial & Tax')
            if any(keyword in doc_lower for keyword in ['marketing', 'sales', 'customer']):
                themes.add('Marketing & Sales')
            if any(keyword in doc_lower for keyword in ['technology', 'software', 'development']):
                themes.add('Technology & Development')
        
        if themes:
            summary_parts.append(f"Document Themes: {', '.join(sorted(themes))}")
        
        # Add document count
        summary_parts.append(f"Document Coverage: {len(docs)} additional relevant documents")
        summary_parts.append("Topics include: business guidance, legal information, and operational support")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        print(f"⚠️ Error creating other docs summary: {e}")
        return f"Additional relevant documents ({len(docs)}) covering business guidance and operational support."