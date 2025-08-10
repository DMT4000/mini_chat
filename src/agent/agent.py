"""
Agent execution interface for the AI Co-founder agent.

This module provides the main Agent class that wraps the LangGraph workflow
and provides a clean interface for executing conversations with conversation
history tracking and session management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .agent_state import AgentState, create_initial_state, add_conversation_entry
from .workflow import AgentWorkflow, create_agent_workflow

# Configure logging for agent operations
logging.basicConfig(level=logging.INFO)
agent_logger = logging.getLogger(__name__)


class Agent:
    """
    Main agent execution interface that wraps the LangGraph workflow.
    
    This class provides:
    - Simple conversation execution interface
    - Conversation history tracking
    - Session management
    - Error handling and recovery
    """
    
    def __init__(self, enable_debug_logging: bool = True):
        """
        Initialize the Agent with a compiled workflow.
        
        Args:
            enable_debug_logging: Whether to enable detailed debug logging
        """
        self.enable_debug_logging = enable_debug_logging
        self.workflow: Optional[AgentWorkflow] = None
        self.conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Initialize the workflow
        self._initialize_workflow()
    
    def _initialize_workflow(self):
        """Initialize and compile the agent workflow."""
        try:
            print("🤖 Initializing Agent workflow...")
            agent_logger.info("Initializing Agent workflow")
            
            self.workflow = create_agent_workflow()
            
            print("✅ Agent initialized successfully")
            agent_logger.info("Agent workflow initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Agent workflow: {str(e)}"
            print(f"❌ {error_msg}")
            agent_logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def run(self, user_id: str, question: str, session_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a conversation turn with the agent.
        
        Args:
            user_id: Unique identifier for the user
            question: User's question or message
            session_config: Optional configuration for this session
            
        Returns:
            Dict containing the response and metadata:
            {
                'answer': str,
                'user_id': str,
                'question': str,
                'extracted_facts': dict,
                'execution_time': float,
                'session_id': str,
                'conversation_turn': int
            }
            
        Raises:
            RuntimeError: If the agent is not properly initialized
            ValueError: If invalid parameters are provided
        """
        if self.workflow is None:
            raise RuntimeError("Agent workflow not initialized")
        
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        
        if not question or not question.strip():
            raise ValueError("question cannot be empty")
        
        execution_start = datetime.now()
        session_id = self._get_or_create_session_id(user_id, session_config)
        
        print(f"🗣️ Processing conversation for user: {user_id}")
        print(f"❓ Question: {question[:100]}{'...' if len(question) > 100 else ''}")
        
        if self.enable_debug_logging:
            agent_logger.info(f"Starting conversation turn for user {user_id}, session {session_id}")
        
        try:
            # Create initial state for the workflow
            initial_state = create_initial_state(user_id, question)
            
            # Add conversation history to the state
            initial_state = self._add_conversation_history_to_state(initial_state, user_id)
            
            # Execute the workflow
            workflow_config = {"configurable": {"thread_id": session_id}}
            final_state = self.workflow.execute_workflow(initial_state, workflow_config)
            
            # Calculate execution time
            execution_time = (datetime.now() - execution_start).total_seconds()
            
            # Update conversation history
            conversation_turn = self._update_conversation_history(
                user_id, question, final_state['answer'], final_state['newly_extracted_facts']
            )
            
            # Prepare response
            response = {
                'answer': final_state['answer'],
                'user_id': user_id,
                'question': question,
                'extracted_facts': final_state['newly_extracted_facts'],
                'execution_time': execution_time,
                'session_id': session_id,
                'conversation_turn': conversation_turn,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ Conversation completed in {execution_time:.2f}s")
            
            if self.enable_debug_logging:
                agent_logger.info(f"Conversation turn completed for user {user_id} in {execution_time:.2f}s")
                agent_logger.debug(f"Response: {response}")
            
            return response
            
        except Exception as e:
            execution_time = (datetime.now() - execution_start).total_seconds()
            error_msg = f"Conversation execution failed for user {user_id}: {str(e)}"
            
            print(f"❌ {error_msg}")
            agent_logger.error(error_msg)
            
            # Create error response
            error_response = {
                'answer': f"I apologize, but I encountered an error while processing your question: {str(e)}",
                'user_id': user_id,
                'question': question,
                'extracted_facts': {},
                'execution_time': execution_time,
                'session_id': session_id,
                'conversation_turn': self._get_conversation_turn_count(user_id) + 1,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
            
            # Still update conversation history with the error
            self._update_conversation_history(
                user_id, question, error_response['answer'], {}
            )
            
            return error_response
    
    def _get_or_create_session_id(self, user_id: str, session_config: Optional[Dict[str, Any]]) -> str:
        """
        Get or create a session ID for the user.
        
        Args:
            user_id: User identifier
            session_config: Optional session configuration
            
        Returns:
            Session ID string
        """
        # Use provided session_id if available, otherwise create one
        if session_config and 'session_id' in session_config:
            session_id = session_config['session_id']
        else:
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize session metadata if new
        if session_id not in self.session_metadata:
            self.session_metadata[session_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'conversation_count': 0
            }
        
        return session_id
    
    def _add_conversation_history_to_state(self, state: AgentState, user_id: str) -> AgentState:
        """
        Add conversation history to the agent state.
        
        Args:
            state: Current agent state
            user_id: User identifier
            
        Returns:
            Updated state with conversation history
        """
        if user_id in self.conversation_sessions:
            # Get the last few conversation turns (limit to prevent context overflow)
            recent_history = self.conversation_sessions[user_id][-10:]  # Last 10 turns
            state['conversation_history'] = recent_history
        
        return state
    
    def _update_conversation_history(self, user_id: str, question: str, answer: str, 
                                   extracted_facts: Dict[str, Any]) -> int:
        """
        Update the conversation history for a user.
        
        Args:
            user_id: User identifier
            question: User's question
            answer: Agent's answer
            extracted_facts: Facts extracted from this conversation
            
        Returns:
            Current conversation turn number
        """
        if user_id not in self.conversation_sessions:
            self.conversation_sessions[user_id] = []
        
        # Add user message
        user_message = {
            'role': 'user',
            'content': question,
            'timestamp': datetime.now().isoformat(),
            'facts_extracted': {}
        }
        
        # Add assistant message
        assistant_message = {
            'role': 'assistant',
            'content': answer,
            'timestamp': datetime.now().isoformat(),
            'facts_extracted': extracted_facts
        }
        
        self.conversation_sessions[user_id].extend([user_message, assistant_message])
        
        # Limit conversation history to prevent memory bloat (keep last 50 messages)
        if len(self.conversation_sessions[user_id]) > 50:
            self.conversation_sessions[user_id] = self.conversation_sessions[user_id][-50:]
        
        # Update session metadata
        for session_id, metadata in self.session_metadata.items():
            if metadata['user_id'] == user_id:
                metadata['conversation_count'] += 1
                metadata['last_activity'] = datetime.now().isoformat()
                break
        
        return len(self.conversation_sessions[user_id]) // 2  # Divide by 2 since each turn has 2 messages
    
    def _get_conversation_turn_count(self, user_id: str) -> int:
        """Get the current conversation turn count for a user."""
        if user_id not in self.conversation_sessions:
            return 0
        return len(self.conversation_sessions[user_id]) // 2
    
    def get_conversation_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: User identifier
            limit: Optional limit on number of messages to return
            
        Returns:
            List of conversation messages
        """
        if user_id not in self.conversation_sessions:
            return []
        
        history = self.conversation_sessions[user_id]
        
        if limit:
            return history[-limit:]
        
        return history.copy()
    
    def clear_conversation_history(self, user_id: str):
        """
        Clear conversation history for a user.
        
        Args:
            user_id: User identifier
        """
        if user_id in self.conversation_sessions:
            del self.conversation_sessions[user_id]
        
        # Also clear related session metadata
        sessions_to_remove = []
        for session_id, metadata in self.session_metadata.items():
            if metadata['user_id'] == user_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.session_metadata[session_id]
        
        if self.enable_debug_logging:
            agent_logger.info(f"Cleared conversation history for user {user_id}")
    
    def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get session information for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with session information
        """
        user_sessions = []
        for session_id, metadata in self.session_metadata.items():
            if metadata['user_id'] == user_id:
                user_sessions.append({
                    'session_id': session_id,
                    'created_at': metadata['created_at'],
                    'conversation_count': metadata['conversation_count'],
                    'last_activity': metadata.get('last_activity', metadata['created_at'])
                })
        
        return {
            'user_id': user_id,
            'total_sessions': len(user_sessions),
            'sessions': user_sessions,
            'total_conversation_turns': self._get_conversation_turn_count(user_id),
            'has_active_history': user_id in self.conversation_sessions
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the underlying workflow.
        
        Returns:
            Dictionary with workflow information
        """
        if self.workflow is None:
            return {'status': 'not_initialized'}
        
        workflow_info = self.workflow.get_workflow_info()
        workflow_info['agent_status'] = 'ready'
        workflow_info['total_users'] = len(self.conversation_sessions)
        workflow_info['total_sessions'] = len(self.session_metadata)
        
        return workflow_info
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get the execution history from the last workflow run.
        
        Returns:
            List of execution records
        """
        if self.workflow is None:
            return []
        
        return self.workflow.get_execution_history()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the agent.
        
        Returns:
            Dictionary with health status information
        """
        try:
            health_status = {
                'status': 'healthy',
                'workflow_initialized': self.workflow is not None,
                'workflow_valid': False,
                'active_users': len(self.conversation_sessions),
                'active_sessions': len(self.session_metadata),
                'timestamp': datetime.now().isoformat()
            }
            
            if self.workflow:
                health_status['workflow_valid'] = self.workflow.validate_workflow()
                health_status['workflow_info'] = self.workflow.get_workflow_info()
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Factory function for creating agent instances
def create_agent(enable_debug_logging: bool = True) -> Agent:
    """
    Factory function to create a new Agent instance.
    
    Args:
        enable_debug_logging: Whether to enable detailed debug logging
        
    Returns:
        Agent: Initialized agent ready for conversation execution
        
    Raises:
        RuntimeError: If agent creation fails
    """
    try:
        print("🏗️ Creating new Agent instance...")
        agent = Agent(enable_debug_logging=enable_debug_logging)
        print("✅ Agent created successfully")
        return agent
        
    except Exception as e:
        error_msg = f"Failed to create Agent: {str(e)}"
        print(f"❌ {error_msg}")
        agent_logger.error(error_msg)
        raise RuntimeError(error_msg)


# Export the main Agent class and factory function
__all__ = ["Agent", "create_agent"]