"""State definition for the LangGraph agent loop."""

from __future__ import annotations

from typing import TypedDict, Annotated, Any
import operator


class PRReviewState(TypedDict):
    """The state dictionary passed between nodes in the LangGraph."""

    # Inputs
    repo: str
    pr_number: int
    head_branch: str

    # Context built during execution
    diff_context: str
    commit_metadata: list[dict[str, Any]]

    # Planner outputs
    files_to_review: list[str]

    # Review results (we use Annotated to append new reviews instead of overwriting)
    file_reviews: Annotated[list[dict[str, Any]], operator.add]

    # Final generated summary
    final_review: str

    # Errors encountered along the way
    errors: Annotated[list[str], operator.add]

    # Trace of tool executions for UI rendering
    trace: Annotated[list[dict[str, Any]], operator.add]
