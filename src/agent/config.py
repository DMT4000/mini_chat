"""
LangGraph configuration and imports for the AI Co-founder agent.

This module centralizes LangGraph imports and provides basic configuration
for the agent workflow.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage

# LangGraph workflow configuration
WORKFLOW_CONFIG = {
    "max_iterations": 10,
    "recursion_limit": 50,
    "debug": True
}

# Node names for the agent workflow
class NodeNames:
    RETRIEVE_CONTEXT = "retrieve_context"
    GENERATE_ANSWER = "generate_answer"
    EXTRACT_FACTS = "extract_facts"
    SAVE_FACTS = "save_facts"

# Edge names for workflow transitions
class EdgeNames:
    START = "start"
    END = "end"
    CONTINUE = "continue"

def create_workflow_graph() -> StateGraph:
    """
    Create and return a basic StateGraph instance for the agent workflow.
    
    Returns:
        StateGraph: Configured StateGraph instance
    """
    from .agent_state import AgentState
    
    workflow = StateGraph(AgentState)
    return workflow