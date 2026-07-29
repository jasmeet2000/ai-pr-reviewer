"""Review API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from src.api.dependencies import SettingsDep
from src.api.schemas import ReviewRequest, ReviewResponse
from src.agent.exceptions import AgentLoopLimitExceeded
from src.agent.graph import build_graph
from src.github.auth import create_github_client
from src.github.client import GitHubClient
from src.github.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from src.llm.exceptions import ClaudeAPIError, OllamaAPIError
from src.llm.tool_executor import ToolExecutor
from src.review.review_generator import synthesize_review
from src.review.report_renderer import render_markdown
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["review"])


def _create_llm_client(settings):
    """Factory: create the right LLM client based on settings."""
    provider = settings.llm_provider
    if provider == "claude":
        from src.llm.claude_client import ClaudeClient
        return ClaudeClient(settings)
    elif provider == "ollama":
        from src.llm.ollama_client import OllamaClient
        return OllamaClient(settings)
    elif provider == "mock":
        from src.llm.mock_client import MockLLMClient
        return MockLLMClient()
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _register_tools(tool_executor: ToolExecutor, gh_client: GitHubClient) -> None:
    """Register GitHub tool wrappers on the executor."""
    def wrapped_get_diff(repo: str, pr_number: int) -> dict:
        return asdict(gh_client.get_pull_request_diff(repo, pr_number))

    def wrapped_get_file_contents(repo: str, path: str, ref: str = None) -> str:
        return gh_client.get_file_contents(repo, path, ref)

    def wrapped_list_changed_files(repo: str, pr_number: int) -> list:
        return [asdict(f) for f in gh_client.list_changed_files(repo, pr_number)]

    def wrapped_get_commit_metadata(repo: str, pr_number: int) -> list:
        res = []
        for c in gh_client.get_commit_metadata(repo, pr_number):
            d = asdict(c)
            d["date"] = d["date"].isoformat()
            res.append(d)
        return res

    tool_executor.register("get_diff", wrapped_get_diff)
    tool_executor.register("get_file_contents", wrapped_get_file_contents)
    tool_executor.register("list_changed_files", wrapped_list_changed_files)
    tool_executor.register("get_commit_metadata", wrapped_get_commit_metadata)


@router.post("/review", response_model=ReviewResponse)
def create_review(request: ReviewRequest, base_settings: SettingsDep) -> ReviewResponse:
    """Run the AI PR reviewer synchronously."""
    # 1. Apply provider override if requested
    settings = base_settings
    if request.provider and request.provider != base_settings.llm_provider:
        # Create a new Settings object with the overridden provider
        kwargs = {"llm_provider": request.provider}
        settings = type(base_settings)(**kwargs)

    logger.info("API Starting review: %s PR #%d (provider=%s)", request.repo, request.pr_number, settings.llm_provider)

    try:
        # 2. Setup clients
        pygithub = create_github_client(settings)
        gh_client = GitHubClient(pygithub)
        llm_client = _create_llm_client(settings)
        tool_executor = ToolExecutor()
        _register_tools(tool_executor, gh_client)

        # 3. Fetch PR metadata to build initial state
        pr_diff = gh_client.get_pull_request_diff(request.repo, request.pr_number)
        pygithub_repo = pygithub.get_repo(request.repo)
        pr_obj = pygithub_repo.get_pull(request.pr_number)
        head_ref = pr_obj.head.sha

        diff_summary = (
            f"PR title: {pr_diff.title}\n"
            f"Files changed: {', '.join(f.filename for f in pr_diff.changed_files)}"
        )

        initial_state = {
            "repo": request.repo,
            "pr_number": request.pr_number,
            "head_branch": head_ref,
            "diff_context": diff_summary,
            "commit_metadata": [],
            "files_to_review": [],
            "file_reviews": [],
            "final_review": "",
            "errors": [],
            "trace": [],
        }

        # 4. Run the agent graph
        graph = build_graph(llm_client, tool_executor, settings)
        final_state = graph.invoke(initial_state)

        # 5. Check results
        file_reviews = final_state.get("file_reviews", [])
        if not file_reviews:
            agent_errors = final_state.get("errors", [])
            err_msg = "Review could not be completed — no files were successfully reviewed."
            if agent_errors:
                err_msg += f" Agent errors: {'; '.join(agent_errors)}"
            raise AgentLoopLimitExceeded(err_msg)

        # 6. Synthesize structured review
        structured_review = synthesize_review(final_state, llm_client)

        # 7. Render Markdown
        md_report = render_markdown(structured_review)

        # 8. Post to GitHub (if requested)
        comment_url = None
        if request.post_to_github:
            comment_url = gh_client.post_comment(request.repo, request.pr_number, md_report)

        # 9. Return Response
        return ReviewResponse(
            summary=structured_review.get("summary", ""),
            findings=structured_review.get("findings", []),
            security_concerns=structured_review.get("security_concerns", []),
            code_quality_notes=structured_review.get("code_quality_notes", []),
            missing_error_handling=structured_review.get("missing_error_handling", []),
            test_cases=structured_review.get("test_cases", {}),
            regression_risk=structured_review.get("regression_risk", {}),
            final_recommendation=structured_review.get("final_recommendation", "Needs Discussion"),
            grounding_check=structured_review.get("grounding_check", True),
            markdown_report=md_report,
            trace=final_state.get("trace", []),
            comment_url=comment_url,
        )

    # Note: Exceptions are caught and mapped to HTTP status codes by global handlers in main.py
    except Exception as e:
        logger.error("API error during review: %s: %s", type(e).__name__, str(e))
        raise
