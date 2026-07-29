"""LangGraph state graph definition."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END

from src.agent.state import PRReviewState
from src.agent.planner import planner_node
from src.agent.review_agent import review_node
from src.llm.base_client import LLMClient
from src.config.settings import Settings
from src.llm.tool_executor import ToolExecutor
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_graph(llm: LLMClient, tool_executor: ToolExecutor, settings: Settings) -> Any:
    """Builds and compiles the StateGraph for the PR Review Agent.

    Args:
        llm: The configured LLM client (Claude or Ollama).
        tool_executor: The tool executor pre-registered with GitHub tools.
        settings: Application configuration settings.

    Returns:
        A compiled LangGraph application.
    """
    logger.info("Building PR Review LangGraph")

    # We use partials or closures to inject the LLM and Executor into the nodes
    def planner_wrapper(state: PRReviewState) -> dict[str, Any]:
        return planner_node(state, llm)

    def review_wrapper(state: PRReviewState) -> dict[str, Any]:
        return review_node(state, llm, tool_executor, settings)

    # Build the graph
    workflow = StateGraph(PRReviewState)

    workflow.add_node("planner", planner_wrapper)
    workflow.add_node("reviewer", review_wrapper)

    # Define edges: START -> planner -> reviewer -> END
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "reviewer")
    workflow.add_edge("reviewer", END)

    app = workflow.compile()
    logger.info("LangGraph compiled successfully")
    return app
