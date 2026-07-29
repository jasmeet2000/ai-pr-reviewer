"""Planner Node for LangGraph."""

from __future__ import annotations

from typing import Any

from src.agent.state import PRReviewState
from src.llm.base_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


def planner_node(state: PRReviewState, llm: LLMClient) -> dict[str, Any]:
    """Analyzes the initial PR context and selects files to review.

    This node expects the `diff_context` to be populated in the state.
    It returns an update dictionary for LangGraph.
    """
    logger.info(
        "Executing planner_node for %s PR #%d", state["repo"], state["pr_number"]
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"You are a Senior Engineer reviewing a PR for {state['repo']} #{state['pr_number']}.\n"
                f"Here is the diff context:\n\n{state.get('diff_context', 'No diff provided.')}\n\n"
                "Identify up to 5 of the most critical files that require a deep dive review. "
                "Return ONLY a comma-separated list of file paths. If no files need deep review, return 'NONE'."
            ),
        }
    ]

    try:
        response = llm.send_message(
            messages=messages,
            system_prompt="You are a senior engineer planning a code review.",
        )
        content = response.get("content", "").strip()

        if not content or content.upper() == "NONE":
            logger.info("Planner decided no files need review.")
            return {"files_to_review": []}

        files = [f.strip() for f in content.split(",") if f.strip()]
        logger.info(f"Planner selected files: {files}")
        return {"files_to_review": files}

    except Exception as e:
        error_msg = f"Planner node failed: {e}"
        logger.error(error_msg)
        return {"errors": [error_msg], "files_to_review": []}
