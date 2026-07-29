"""Pydantic models for API request/response contracts.

These are the public-facing shapes — internal domain models (PRReviewState,
PullRequestDiff, etc.) stay internal and are never leaked in the API.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ── Request ──────────────────────────────────────────────────────────


class ReviewRequest(BaseModel):
    """POST /review request body."""

    repo: str = Field(
        ...,
        description="Repository in owner/name format",
        examples=["fastapi/fastapi"],
    )
    pr_number: int = Field(..., gt=0, description="Pull request number")
    provider: Literal["claude", "ollama", "mock"] | None = Field(
        default=None,
        description="LLM provider override (default: from server config)",
    )
    post_to_github: bool = Field(
        default=False,
        description="If true, post the review as a PR comment",
    )

    @field_validator("repo")
    @classmethod
    def _validate_repo_format(cls, v: str) -> str:
        """Reject malformed repo strings before they reach the GitHub client."""
        parts = v.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                f"repo must be in 'owner/name' format, got: '{v}'"
            )
        return v.strip()


# ── Response ─────────────────────────────────────────────────────────


class ReviewFinding(BaseModel):
    severity: str
    file: str
    line: int | None = None
    explanation: str
    recommendation: str


class TestCases(BaseModel):
    functional: list[str] = []
    boundary: list[str] = []
    negative: list[str] = []
    regression: list[str] = []


class RegressionRisk(BaseModel):
    level: str = "Unknown"
    reasoning: str = ""


class ReviewResponse(BaseModel):
    """POST /review response body — the structured review."""

    summary: str
    findings: list[ReviewFinding] = []
    security_concerns: list[str] = []
    code_quality_notes: list[str] = []
    missing_error_handling: list[str] = []
    test_cases: TestCases = TestCases()
    regression_risk: RegressionRisk = RegressionRisk()
    final_recommendation: str = "Needs Discussion"
    grounding_check: bool = True
    markdown_report: str = Field(
        default="",
        description="Pre-rendered markdown report",
    )
    trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tool-call trace for UI visualization",
    )
    comment_url: str | None = Field(
        default=None,
        description="URL of the posted GitHub comment, if requested",
    )


class ErrorResponse(BaseModel):
    """Standard error response shape per ERROR_HANDLING.md."""

    error: str
    detail: str


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str = ""
