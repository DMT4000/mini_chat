"""
LangGraph workflow definition for the AI Co-founder agent.

This module defines the complete agent workflow using LangGraph's StateGraph,
including all nodes, edges, state flow configuration, and comprehensive error handling.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .agent_state import AgentState, validate_agent_state, serialize_state_for_debug, update_state_field
from .workflow_nodes import retrieve_context, generate_answer, extract_facts, save_facts, lightweight_response
from .workflow_router import WorkflowRouter
from .workflow_analytics import WorkflowAnalytics

# Configure logging for workflow operations
logging.basicConfig(level=logging.INFO)
workflow_logger = logging.getLogger(__name__)


class AgentWorkflow:
    """
    LangGraph workflow definition for the AI Co-founder agent.
    
    This class encapsulates the complete agent workflow including:
    - Node definitions and sequencing
    - State flow configuration
    - Workflow compilation and validation
    - Comprehensive error handling and logging
    """
    
    def __init__(self, enable_debug_logging: bool = True):
        """
        Initialize the agent workflow.
        
        Args:
            enable_debug_logging: Whether to enable detailed debug logging
        """
        self.workflow = None
        self.compiled_workflow = None
        self.enable_debug_logging = enable_debug_logging
        self.execution_history = []
        self.router = WorkflowRouter()
        self.analytics = WorkflowAnalytics()
        self._build_workflow()
    
    def _build_workflow(self) -> None:
        """
        Build the LangGraph workflow with conditional routing and error handling.
        
        The workflow now includes intelligent routing:
        1. classify_input: Classify user input and determine routing path
        2a. memory_command: Process memory management commands
        2b. lightweight_response: Quick responses for greetings/simple questions
        2c. retrieve_context: Full context retrieval for complex questions
        3. generate_answer: Create response using context engineering
        4. extract_facts: Extract new facts from the conversation (conditional)
        5. save_facts: Save extracted facts to user memory (conditional)
        
        All nodes are wrapped with error handling for graceful failure recovery.
        """
        print("🔧 Building LangGraph workflow with conditional routing...")
        
        try:
            # Create the state graph
            workflow = StateGraph(AgentState)
            
            # Add routing and command processing nodes
            workflow.add_node("classify_input", self._wrap_node_with_error_handling(
                self._classify_input_node, "classify_input"
            ))
            # New: clarification node for ambiguous queries
            workflow.add_node("clarify_question", self._wrap_node_with_error_handling(
                self._clarify_question_node, "clarify_question"
            ))
            workflow.add_node("memory_command", self._wrap_node_with_error_handling(
                self._memory_command_node, "memory_command"
            ))
            workflow.add_node("lightweight_response", self._wrap_node_with_error_handling(
                lightweight_response, "lightweight_response"
            ))
            
            # Add existing workflow nodes with error handling wrappers
            workflow.add_node("retrieve_context", self._wrap_node_with_error_handling(
                retrieve_context, "retrieve_context"
            ))
            workflow.add_node("generate_answer", self._wrap_node_with_error_handling(
                generate_answer, "generate_answer"
            ))
            workflow.add_node("extract_facts", self._wrap_node_with_error_handling(
                extract_facts, "extract_facts"
            ))
            workflow.add_node("save_facts", self._wrap_node_with_error_handling(
                save_facts, "save_facts"
            ))
            
            # Add skip node for when fact extraction is not needed
            workflow.add_node("skip_save_facts", self._wrap_node_with_error_handling(
                self._skip_save_facts_node, "skip_save_facts"
            ))
            
            # Define the workflow entry point and conditional routing
            workflow.set_entry_point("classify_input")
            
            # Add conditional edges based on input classification
            workflow.add_conditional_edges(
                "classify_input",
                self._route_after_classification,
                {
                    "memory_command": "memory_command",
                    "lightweight": "lightweight_response",
                    "clarify": "clarify_question",
                    "full_workflow": "retrieve_context"
                }
            )
            
            # Memory command and lightweight paths go directly to end
            workflow.add_edge("memory_command", END)
            workflow.add_edge("lightweight_response", END)
            workflow.add_edge("clarify_question", END)
            
            # Full workflow path
            workflow.add_edge("retrieve_context", "generate_answer")
            
            # Conditional fact extraction based on whether facts should be extracted
            workflow.add_conditional_edges(
                "generate_answer",
                self._route_after_answer_generation,
                {
                    "extract_facts": "extract_facts",
                    "skip_facts": "skip_save_facts"
                }
            )
            
            # Conditional saving based on whether facts were extracted
            workflow.add_conditional_edges(
                "extract_facts",
                self._route_after_fact_extraction,
                {
                    "save_facts": "save_facts",
                    "skip_save": "skip_save_facts"
                }
            )
            
            # Both save and skip paths end the workflow
            workflow.add_edge("save_facts", END)
            workflow.add_edge("skip_save_facts", END)
            
            self.workflow = workflow
            print("✅ Conditional workflow graph built successfully")
            
        except Exception as e:
            error_msg = f"Failed to build workflow graph: {str(e)}"
            print(f"❌ {error_msg}")
            workflow_logger.error(f"Workflow build failed: {error_msg}")
            raise RuntimeError(error_msg)
    
    def _wrap_node_with_error_handling(self, node_func, node_name: str):
        """
        Wrap a workflow node function with comprehensive error handling.
        
        Args:
            node_func: The original node function to wrap
            node_name: Name of the node for logging purposes
            
        Returns:
            Wrapped function with error handling and logging
        """
        def wrapped_node(state: AgentState) -> AgentState:
            """Error-wrapped node function with logging and partial result handling."""
            start_time = datetime.now()
            
            try:
                # Log node execution start
                if self.enable_debug_logging:
                    workflow_logger.info(f"Starting node: {node_name}")
                    workflow_logger.debug(f"Node {node_name} input state: {serialize_state_for_debug(state)}")
                
                # Validate input state
                if not validate_agent_state(state):
                    raise ValueError(f"Invalid state provided to node {node_name}")
                
                # Execute the original node function
                result_state = node_func(state)
                
                # Validate output state
                if not validate_agent_state(result_state):
                    workflow_logger.warning(f"Node {node_name} returned invalid state, attempting recovery")
                    result_state = self._recover_invalid_state(state, result_state, node_name)
                
                # Log successful execution
                execution_time = (datetime.now() - start_time).total_seconds()
                if self.enable_debug_logging:
                    workflow_logger.info(f"Node {node_name} completed successfully in {execution_time:.2f}s")
                    workflow_logger.debug(f"Node {node_name} output state: {serialize_state_for_debug(result_state)}")
                
                # Record execution history
                self._record_node_execution(node_name, "success", execution_time, None)
                
                return result_state
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"Node {node_name} failed: {str(e)}"
                
                # Log the error
                workflow_logger.error(error_msg)
                workflow_logger.debug(f"Node {node_name} error details", exc_info=True)
                
                # Record execution history
                self._record_node_execution(node_name, "error", execution_time, str(e))
                
                # Attempt to provide partial results
                partial_result = self._handle_node_failure(state, node_name, e)
                
                if self.enable_debug_logging:
                    workflow_logger.info(f"Node {node_name} provided partial result after failure")
                    workflow_logger.debug(f"Partial result state: {serialize_state_for_debug(partial_result)}")
                
                return partial_result
        
        return wrapped_node
    
    def _recover_invalid_state(self, input_state: AgentState, invalid_state: Any, node_name: str) -> AgentState:
        """
        Attempt to recover from an invalid state returned by a node.
        
        Args:
            input_state: The original input state
            invalid_state: The invalid state returned by the node
            node_name: Name of the node that returned invalid state
            
        Returns:
            AgentState: Recovered state or input state with error annotation
        """
        workflow_logger.warning(f"Attempting to recover invalid state from node {node_name}")
        
        try:
            # If the invalid state is a dictionary, try to merge with input state
            if isinstance(invalid_state, dict):
                recovered_state = dict(input_state)
                
                # Safely merge valid fields from invalid state
                for key, value in invalid_state.items():
                    if key in input_state and value is not None:
                        recovered_state[key] = value
                
                # Validate the recovered state
                if validate_agent_state(recovered_state):
                    workflow_logger.info(f"Successfully recovered state for node {node_name}")
                    return AgentState(**recovered_state)
            
            # If recovery fails, return input state with error annotation
            workflow_logger.warning(f"Could not recover state for node {node_name}, using input state")
            return input_state
            
        except Exception as recovery_error:
            workflow_logger.error(f"State recovery failed for node {node_name}: {str(recovery_error)}")
            return input_state
    
    def _handle_node_failure(self, state: AgentState, node_name: str, error: Exception) -> AgentState:
        """
        Handle node failure by providing appropriate partial results.
        
        Args:
            state: Current state when the node failed
            node_name: Name of the failed node
            error: The exception that caused the failure
            
        Returns:
            AgentState: State with partial results or fallback values
        """
        workflow_logger.info(f"Handling failure for node {node_name}")
        
        # Provide node-specific fallback behavior
        if node_name == "retrieve_context":
            # If context retrieval fails, continue with empty context
            updated_state = update_state_field(state, 'user_facts', {})
            updated_state = update_state_field(updated_state, 'retrieved_docs', [])
            return updated_state
            
        elif node_name == "generate_answer":
            # If answer generation fails, provide error message
            error_answer = f"I apologize, but I encountered an error while processing your question: {str(error)}"
            return update_state_field(state, 'answer', error_answer)
            
        elif node_name == "extract_facts":
            # If fact extraction fails, continue with no new facts
            return update_state_field(state, 'newly_extracted_facts', {})
            
        elif node_name == "save_facts":
            # If saving fails, continue without saving (facts are already extracted)
            workflow_logger.warning(f"Facts could not be saved for user {state['user_id']}: {str(error)}")
            return state
            
        else:
            # Default fallback: return state unchanged
            workflow_logger.warning(f"No specific fallback for node {node_name}, returning unchanged state")
            return state
    
    def _record_node_execution(self, node_name: str, status: str, execution_time: float, error: Optional[str]):
        """
        Record node execution details for debugging and monitoring.
        
        Args:
            node_name: Name of the executed node
            status: Execution status ('success' or 'error')
            execution_time: Time taken to execute the node
            error: Error message if status is 'error'
        """
        execution_record = {
            'node_name': node_name,
            'status': status,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'error': error
        }
        
        self.execution_history.append(execution_record)
        
        # Keep only the last 100 execution records to prevent memory bloat
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def compile_workflow(self, checkpointer=None) -> None:
        """
        Compile the workflow for execution.
        
        Args:
            checkpointer: Optional checkpointer for state persistence
                         Defaults to MemorySaver for in-memory checkpointing
        """
        print("⚙️ Compiling LangGraph workflow...")
        
        try:
            if self.workflow is None:
                raise RuntimeError("Workflow not built. Call _build_workflow() first.")
            
            # Use MemorySaver as default checkpointer for state persistence
            if checkpointer is None:
                checkpointer = MemorySaver()
            
            # Compile the workflow
            self.compiled_workflow = self.workflow.compile(checkpointer=checkpointer)
            
            print("✅ Workflow compiled successfully")
            
        except Exception as e:
            error_msg = f"Failed to compile workflow: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
    
    def validate_workflow(self) -> bool:
        """
        Validate the workflow configuration.
        
        Returns:
            bool: True if workflow is valid, False otherwise
        """
        print("🔍 Validating workflow configuration...")
        
        try:
            # Check if workflow is built
            if self.workflow is None:
                print("❌ Workflow not built")
                return False
            
            # Check if workflow is compiled
            if self.compiled_workflow is None:
                print("❌ Workflow not compiled")
                return False
            
            # Validate that all required nodes are present
            expected_nodes = {
                "classify_input", "memory_command", "lightweight_response", "retrieve_context", 
                "generate_answer", "extract_facts", "save_facts", "skip_save_facts"
            }
            actual_nodes = set(self.workflow.nodes.keys())
            
            if not expected_nodes.issubset(actual_nodes):
                missing_nodes = expected_nodes - actual_nodes
                print(f"❌ Missing workflow nodes: {missing_nodes}")
                return False
            
            # Validate workflow structure
            if not hasattr(self.workflow, 'edges'):
                print("❌ Workflow missing edge configuration")
                return False
            
            print("✅ Workflow validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Workflow validation error: {str(e)}")
            return False
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the current workflow configuration.
        
        Returns:
            Dict containing workflow metadata and configuration
        """
        if self.workflow is None:
            return {"status": "not_built", "nodes": [], "edges": [], "node_count": 0}
        
        try:
            nodes = list(self.workflow.nodes.keys())
            
            # Extract edge information - LangGraph edges are stored differently
            edges = []
            try:
                # Try to get edge information from the workflow
                if hasattr(self.workflow, '_edges'):
                    for edge_info in self.workflow._edges:
                        edges.append(str(edge_info))
                elif hasattr(self.workflow, 'edges'):
                    edges.append(f"Edges: {len(self.workflow.edges)} configured")
                else:
                    edges.append("Edge information not accessible")
            except Exception as edge_error:
                edges.append(f"Edge extraction error: {str(edge_error)}")
            
            return {
                "status": "compiled" if self.compiled_workflow else "built",
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "is_valid": self.validate_workflow()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "nodes": [],
                "edges": [],
                "node_count": 0
            }
    
    def execute_workflow(self, initial_state: AgentState, config: Dict[str, Any] = None) -> AgentState:
        """
        Execute the compiled workflow with comprehensive error handling and analytics tracking.
        
        Args:
            initial_state: Initial AgentState to start the workflow
            config: Optional configuration for workflow execution
            
        Returns:
            AgentState: Final state after workflow execution
            
        Raises:
            RuntimeError: If workflow is not compiled or execution fails critically
        """
        if self.compiled_workflow is None:
            raise RuntimeError("Workflow not compiled. Call compile_workflow() first.")
        
        if not validate_agent_state(initial_state):
            raise ValueError("Invalid initial state provided to workflow")
        
        execution_start = datetime.now()
        user_id = initial_state['user_id']
        question_preview = initial_state['question'][:100] + "..." if len(initial_state['question']) > 100 else initial_state['question']
        
        print(f"🚀 Executing workflow for user: {user_id}")
        print(f"📝 Question: {question_preview}")
        
        if self.enable_debug_logging:
            workflow_logger.info(f"Starting workflow execution for user {user_id}")
            workflow_logger.debug(f"Initial state: {serialize_state_for_debug(initial_state)}")
        
        try:
            # Clear previous execution history for this run
            self.execution_history = []
            
            # Set default config if none provided
            if config is None:
                config = {"configurable": {"thread_id": user_id}}
            
            # Execute the workflow
            result = self.compiled_workflow.invoke(initial_state, config)
            
            # Calculate total execution time
            total_execution_time = (datetime.now() - execution_start).total_seconds()
            
            # Validate the result
            if not validate_agent_state(result):
                workflow_logger.warning("Workflow returned invalid final state")
                print("⚠️ Warning: Workflow returned invalid state")
                
                # Attempt to recover the final state
                result = self._recover_invalid_state(initial_state, result, "workflow_final")
            
            # Track analytics for successful execution
            workflow_path = self._determine_workflow_path(result)
            node_timings = self._extract_node_timings()
            
            self.analytics.track_execution_metrics(
                user_id=user_id,
                workflow_path=workflow_path,
                execution_time=total_execution_time,
                success=True,
                node_timings=node_timings,
                additional_metrics={
                    'question_length': len(initial_state['question']),
                    'facts_extracted': len(result.get('newly_extracted_facts', {})),
                    'question_type': result.get('question_type', 'unknown')
                }
            )
            
            # Track fact extraction decision if applicable
            if 'newly_extracted_facts' in result:
                conversation = f"User Question: {initial_state['question']}\n\nAssistant Answer: {result.get('answer', '')}"
                decision = 'performed' if result['newly_extracted_facts'] else 'skipped'
                self.analytics.track_fact_extraction_decision(
                    user_id=user_id,
                    decision=decision,
                    conversation_length=len(conversation),
                    facts_found=len(result['newly_extracted_facts'])
                )
            
            # Log successful completion
            print(f"✅ Workflow execution completed successfully in {total_execution_time:.2f}s")
            
            if self.enable_debug_logging:
                workflow_logger.info(f"Workflow completed for user {user_id} in {total_execution_time:.2f}s")
                workflow_logger.debug(f"Final state: {serialize_state_for_debug(result)}")
                
                # Log execution summary
                self._log_execution_summary()
            
            return result
            
        except Exception as e:
            total_execution_time = (datetime.now() - execution_start).total_seconds()
            error_msg = f"Workflow execution failed for user {user_id}: {str(e)}"
            
            # Track failed execution in analytics
            self.analytics.track_execution_metrics(
                user_id=user_id,
                workflow_path="failed",
                execution_time=total_execution_time,
                success=False,
                additional_metrics={'error': str(e)}
            )
            
            # Log the error with full context
            print(f"❌ {error_msg}")
            workflow_logger.error(error_msg)
            workflow_logger.debug("Workflow execution error details", exc_info=True)
            
            # Log state for debugging
            if self.enable_debug_logging:
                print("🐛 Debug - Initial state:")
                print(serialize_state_for_debug(initial_state))
                workflow_logger.debug(f"Failed execution initial state: {serialize_state_for_debug(initial_state)}")
                
                # Log partial execution history
                self._log_execution_summary()
            
            # Attempt to provide a partial result instead of complete failure
            try:
                partial_result = self._create_fallback_result(initial_state, str(e))
                workflow_logger.info(f"Providing fallback result for failed workflow execution")
                print("🔄 Providing fallback result due to workflow failure")
                return partial_result
                
            except Exception as fallback_error:
                workflow_logger.error(f"Fallback result creation failed: {str(fallback_error)}")
                raise RuntimeError(f"{error_msg}. Fallback also failed: {str(fallback_error)}")
    
    def _log_execution_summary(self):
        """Log a summary of node execution history for debugging."""
        if not self.execution_history:
            workflow_logger.debug("No execution history to summarize")
            return
        
        successful_nodes = [record for record in self.execution_history if record['status'] == 'success']
        failed_nodes = [record for record in self.execution_history if record['status'] == 'error']
        
        total_time = sum(record['execution_time'] for record in self.execution_history)
        
        summary = f"Execution Summary - Total: {len(self.execution_history)} nodes, "
        summary += f"Success: {len(successful_nodes)}, Failed: {len(failed_nodes)}, "
        summary += f"Total Time: {total_time:.2f}s"
        
        workflow_logger.info(summary)
        
        # Log details of failed nodes
        for failed_node in failed_nodes:
            workflow_logger.warning(f"Failed node: {failed_node['node_name']} - {failed_node['error']}")
    
    def _classify_input_node(self, state: AgentState) -> AgentState:
        """
        Classify user input and set routing information in state.
        
        Args:
            state: Current agent state with user question
            
        Returns:
            AgentState: Updated state with command_type and question_type
        """
        try:
            # Classify the command type
            command_type = self.router.classify_command(state['question'])

            # Try quick profile/identity detection first
            try:
                from .workflow_router import detect_profile_info
                quick_det = detect_profile_info(state['question'])
            except Exception:
                quick_det = None

            # Classify question complexity for routing
            question_type = self.router.classify_question_complexity(
                state['question'], 
                state.get('user_facts', {})
            )

            # Detect intent/entities and whether we should clarify
            conversation_summary = ""
            try:
                from .workflow_nodes import _summarize_recent_conversation
                conversation_summary = _summarize_recent_conversation(state.get('conversation_history', []), max_messages=6, max_chars=400)
            except Exception:
                pass

            # Use quick detection result if available; otherwise run LLM intent detection
            if quick_det:
                intent_info = {"intent": quick_det.get("intent", "unknown"), "entities": quick_det.get("entities", {}), "needs_clarification": False}
                # Treat as simple to avoid over-routing; downstream routing will handle exact path
                question_type = 'simple'
            else:
                intent_info = self.router.detect_intent(state['question'], state.get('user_facts', {}), conversation_summary)

            # Update state with classification results
            updated_state = update_state_field(state, 'command_type', command_type)
            updated_state = update_state_field(updated_state, 'question_type', question_type)
            updated_state = update_state_field(updated_state, 'intent', intent_info.get('intent', 'unknown'))
            updated_state = update_state_field(updated_state, 'entities', intent_info.get('entities', {}))
            updated_state = update_state_field(updated_state, 'needs_clarification', bool(intent_info.get('needs_clarification', False)))
            
            print(f"🎯 Input classified - Command: {command_type}, Question: {question_type}")
            
            return updated_state
            
        except Exception as e:
            print(f"❌ Error in input classification: {str(e)}")
            # Default to complex question on error
            updated_state = update_state_field(state, 'command_type', 'question')
            updated_state = update_state_field(updated_state, 'question_type', 'complex')
            return updated_state
    
    def _memory_command_node(self, state: AgentState) -> AgentState:
        """
        Placeholder for memory command processing (Task 14 not implemented).
        
        Args:
            state: Current agent state with memory command
            
        Returns:
            AgentState: Updated state with error message
        """
        error_msg = "❌ Memory management commands are not yet implemented. This feature is part of Task 14."
        updated_state = update_state_field(state, 'answer', error_msg)
        return updated_state
    
    def _route_after_classification(self, state: AgentState) -> str:
        """
        Determine routing path after input classification.
        
        Args:
            state: Current agent state with classification results
            
        Returns:
            str: Next node to execute ("memory_command", "lightweight", or "full_workflow")
        """
        try:
            command_type = state.get('command_type', 'question')
            question_type = state.get('question_type', 'complex')
            question = state.get('question', '').lower()
            
            # Route memory commands to memory command processor
            if command_type == 'memory_command':
                print(f"🚀 Routing to memory command processor")
                return "memory_command"
            
            # Ensure identity/profile go through context retrieval to load/save memory
            elif state.get('intent') in ('provide_profile_info', 'ask_identity'):
                print("Routing to full workflow for identity/profile handling")
                return "retrieve_context"
            
            # Route product recommendations through full workflow to access Fuxion products
            elif state.get('intent') == 'product_recommendation':
                print("🚀 Routing to full workflow for product recommendation")
                return "full_workflow"
            
            # Force capabilities and functionality questions through full workflow
            elif self._is_capabilities_question(state):
                print("🎯 Routing to full workflow for capabilities question")
                return "full_workflow"
            
            # Force document questions through full workflow to ground responses in retrieval
            elif self._is_document_question(state):
                print("📚 Routing to full workflow for document-related question")
                return "full_workflow"
            
            # Force wellness app and cronograma related questions through full workflow
            elif self._is_wellness_or_cronograma_question(state):
                print("📋 Routing to full workflow for wellness app/cronograma question")
                return "full_workflow"
            
            # Force Fuxion product related questions through full workflow
            elif self._is_fuxion_product_question(state):
                print("🛍️ Routing to full workflow for Fuxion product question")
                return "full_workflow"
            
            # Route simple questions and greetings to lightweight response
            elif state.get('needs_clarification'):
                print(f"🚦 Routing to clarification step due to ambiguity")
                return "clarify"
            
            # If user is providing profile info (e.g., name), prefer full workflow to enable fact extraction
            elif state.get('intent') == 'provide_profile_info':
                print("Routing to full workflow for profile info extraction")
                return "retrieve_context"
            
            elif question_type in ['simple', 'greeting']:
                print(f"🚀 Routing to lightweight path for {question_type} question")
                return "lightweight"
            else:
                print(f"🚀 Routing to full workflow for {question_type} question")
                return "full_workflow"
        except Exception as e:
            print(f"❌ Error in routing decision: {str(e)}")
            # Default to full workflow on error
            return "full_workflow"

    def _is_document_question(self, state: AgentState) -> bool:
        """Heuristic: decide if the user is asking about docs/ingest/vector index; if so, require retrieval path."""
        try:
            from .workflow_router import is_document_question
            return is_document_question(state.get('question', ''))
        except Exception:
            return False

    def _is_wellness_or_cronograma_question(self, state: AgentState) -> bool:
        """Check if the question is related to wellness app or cronograma documents."""
        try:
            question = state.get('question', '').lower()
            
            # Wellness app related keywords
            wellness_keywords = [
                'wellness', 'wellness app', 'wellness application', 'plan de trabajo',
                'workstream', 'work stream', 'ws', 'objetivo', 'objective', 'goal',
                'implementación', 'implementation', 'development', 'fase', 'phase',
                'milestone', 'hito', 'deliverable'
            ]
            
            # Cronograma/timeline related keywords
            cronograma_keywords = [
                'cronograma', 'timeline', 'schedule', 'calendar', 'project timeline',
                'project schedule', 'gate', 'gateway', 'checkpoint', 'deadline',
                'due date', 'target date', 'roadmap', 'project plan'
            ]
            
            # Check for wellness app keywords
            for keyword in wellness_keywords:
                if keyword in question:
                    print(f"🎯 Wellness app keyword detected: {keyword}")
                    return True
            
            # Check for cronograma keywords
            for keyword in cronograma_keywords:
                if keyword in question:
                    print(f"🎯 Cronograma keyword detected: {keyword}")
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️ Error checking wellness/cronograma keywords: {e}")
            return False

    def _is_fuxion_product_question(self, state: AgentState) -> bool:
        """Check if the question is related to Fuxion products."""
        try:
            question = state.get('question', '').lower()
            
            # Fuxion product related keywords in both English and Spanish
            fuxion_keywords = [
                # English keywords
                'fuxion', 'product', 'products', 'supplement', 'supplements', 'catalog',
                'sku', 'weight loss', 'nutrition', 'health', 'wellness',
                
                # Spanish keywords
                'producto', 'productos', 'suplemento', 'suplementos', 'catálogo',
                'pérdida de peso', 'nutrición', 'salud', 'bienestar',
                
                # Common product terms
                'café', 'chocolate', 'vitamin', 'vitamina', 'mineral', 'proteína'
            ]
            
            # Check for Fuxion product keywords
            for keyword in fuxion_keywords:
                if keyword in question:
                    print(f"🎯 Fuxion product keyword detected: {keyword}")
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️ Error checking Fuxion product keywords: {e}")
            return False

    def _is_capabilities_question(self, state: AgentState) -> bool:
        """Check if the question is asking about the agent's capabilities or functionality."""
        try:
            question = state.get('question', '').lower()
            
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
                if re.search(pattern, question):
                    print(f"🎯 Capabilities question detected: {pattern}")
                    return True
            
            # Also check for common capability question keywords
            capability_keywords = [
                'capabilities', 'abilities', 'features', 'functions', 'skills',
                'what can you do', 'how do you work', 'what do you help with',
                'what documents', 'what files', 'what plans', 'what products'
            ]
            
            for keyword in capability_keywords:
                if keyword in question:
                    print(f"🎯 Capabilities keyword detected: {keyword}")
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️ Error checking capabilities keywords: {e}")
            return False
    
    def _clarify_question_node(self, state: AgentState) -> AgentState:
        """
        Ask a short, targeted clarification question when the user's intent is ambiguous.
        """
        try:
            intent = state.get('intent', 'unknown')
            entities = state.get('entities', {})
            base = "I want to make sure I help precisely. "
            if intent == 'greeting':
                answer = "Hello! How can I assist you with your business today?"
            else:
                # Generate a concise clarification prompt heuristically
                missing = []
                if 'jurisdiction' not in entities and any(k in state.get('question','').lower() for k in ['llc','register','incorporate','license']):
                    missing.append('state or country')
                if 'business_type' not in entities and 'llc' not in entities:
                    missing.append('business type (e.g., LLC, corporation)')
                if 'timeline' not in entities and any(k in state.get('question','').lower() for k in ['deadline','when','timeline']):
                    missing.append('timeline')
                if missing:
                    answer = base + "Could you specify your " + ", ".join(missing) + "?"
                else:
                    answer = base + "Could you share a bit more detail on your goal so I can tailor the guidance?"
            return update_state_field(state, 'answer', answer)
        except Exception as e:
            return update_state_field(state, 'answer', "Could you share a bit more detail so I can tailor the guidance?")
    
    def _route_after_answer_generation(self, state: AgentState) -> str:
        """
        Determine whether to extract facts after answer generation.
        
        Args:
            state: Current agent state with generated answer
            
        Returns:
            str: Next node to execute ("extract_facts" or "skip_facts")
        """
        try:
            # Create conversation text for fact extraction decision
            conversation = f"User Question: {state['question']}\n\nAssistant Answer: {state['answer']}"
            
            # Use router to decide if fact extraction is worthwhile
            should_extract = self.router.should_extract_facts(
                conversation, 
                state.get('user_facts', {})
            )
            
            # Track the decision for analytics
            decision = 'performed' if should_extract else 'skipped'
            self.analytics.track_fact_extraction_decision(
                user_id=state['user_id'],
                decision=decision,
                conversation_length=len(conversation)
            )
            
            if should_extract:
                print("🔍 Routing to fact extraction")
                return "extract_facts"
            else:
                print("⏭️ Skipping fact extraction")
                return "skip_facts"
                
        except Exception as e:
            print(f"❌ Error in fact extraction routing: {str(e)}")
            # Default to extracting facts on error
            return "extract_facts"
    
    def _route_after_fact_extraction(self, state: AgentState) -> str:
        """
        Determine whether to save facts after extraction.
        
        Args:
            state: Current agent state with extracted facts
            
        Returns:
            str: Next node to execute ("save_facts" or "skip_save")
        """
        try:
            newly_extracted_facts = state.get('newly_extracted_facts', {})
            
            # Only save if we actually extracted facts
            if newly_extracted_facts:
                print(f"💾 Routing to save {len(newly_extracted_facts)} extracted facts")
                return "save_facts"
            else:
                print("⏭️ No facts to save, skipping save step")
                return "skip_save"
                
        except Exception as e:
            print(f"❌ Error in save routing decision: {str(e)}")
            # Default to saving on error (safe choice)
            return "save_facts"
    
    def _skip_save_facts_node(self, state: AgentState) -> AgentState:
        """
        Skip fact saving when no facts were extracted or extraction was skipped.
        
        Args:
            state: Current agent state
            
        Returns:
            AgentState: Unchanged state (no facts to save)
        """
        print("⏭️ Skipping fact save step - no new facts to save")
        return state

    def _create_fallback_result(self, initial_state: AgentState, error_message: str) -> AgentState:
        """
        Create a fallback result when the entire workflow fails.
        
        Args:
            initial_state: The initial state that was provided to the workflow
            error_message: The error message from the workflow failure
            
        Returns:
            AgentState: A fallback state with error information
        """
        fallback_answer = (
            f"I apologize, but I encountered a technical issue while processing your request. "
            f"Error: {error_message}. Please try again or rephrase your question."
        )
        
        # Create a minimal valid result state
        fallback_state = dict(initial_state)
        fallback_state.update({
            'answer': fallback_answer,
            'user_facts': {},  # Empty facts if retrieval failed
            'retrieved_docs': [],  # Empty docs if retrieval failed
            'newly_extracted_facts': {},  # No facts extracted due to failure
            'conversation_history': []  # Empty history for this failed attempt
        })
        
        return AgentState(**fallback_state)
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get the execution history for the last workflow run.
        
        Returns:
            List of execution records with node performance data
        """
        return self.execution_history.copy()
    
    def clear_execution_history(self):
        """Clear the execution history."""
        self.execution_history = []
    
    def _determine_workflow_path(self, result_state: AgentState) -> str:
        """
        Determine which workflow path was taken based on the result state.
        
        Args:
            result_state: Final state after workflow execution
            
        Returns:
            str: Workflow path identifier
        """
        try:
            question_type = result_state.get('question_type', 'unknown')
            
            # Check if lightweight path was used
            if question_type in ['simple', 'greeting']:
                return 'lightweight'
            else:
                return 'full'
                
        except Exception as e:
            workflow_logger.warning(f"Could not determine workflow path: {str(e)}")
            return 'unknown'
    
    def _extract_node_timings(self) -> Dict[str, float]:
        """
        Extract node timing information from execution history.
        
        Returns:
            Dict mapping node names to execution times
        """
        try:
            node_timings = {}
            
            for record in self.execution_history:
                if record.get('status') == 'success':
                    node_name = record.get('node_name')
                    execution_time = record.get('execution_time', 0.0)
                    if node_name:
                        node_timings[node_name] = execution_time
            
            return node_timings
            
        except Exception as e:
            workflow_logger.warning(f"Could not extract node timings: {str(e)}")
            return {}
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Get analytics summary for the workflow.
        
        Returns:
            Dict containing analytics data
        """
        try:
            return {
                'performance_summary': self.analytics.get_performance_summary(),
                'routing_metrics': self.router.get_routing_metrics(),
                'efficiency_score': self.analytics.calculate_efficiency_score()
            }
        except Exception as e:
            workflow_logger.error(f"Error getting analytics summary: {str(e)}")
            return {'error': str(e)}


def create_agent_workflow() -> AgentWorkflow:
    """
    Factory function to create and compile a new agent workflow.
    
    Returns:
        AgentWorkflow: Compiled and validated workflow ready for execution
        
    Raises:
        RuntimeError: If workflow creation or compilation fails
    """
    print("🏗️ Creating new agent workflow...")
    
    try:
        # Create workflow instance
        workflow = AgentWorkflow()
        
        # Compile the workflow
        workflow.compile_workflow()
        
        # Validate the workflow
        if not workflow.validate_workflow():
            raise RuntimeError("Workflow validation failed")
        
        print("✅ Agent workflow created and validated successfully")
        return workflow
        
    except Exception as e:
        error_msg = f"Failed to create agent workflow: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)


# Export the main workflow class and factory function
__all__ = ["AgentWorkflow", "create_agent_workflow"]