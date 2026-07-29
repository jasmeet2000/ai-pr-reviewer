"""CLI entry point for the AI PR Reviewer.

Usage:
    python review_pr.py --repo owner/repo --pr 42
    python review_pr.py --repo owner/repo --pr 42 --provider ollama --verbose
    python review_pr.py --repo owner/repo --pr 42 --output report.md --post-comment
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agent.exceptions import AgentLoopLimitExceeded
from src.config.settings import Settings
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
from src.utils.logger import get_logger, enable_debug

logger = get_logger(__name__)


# ── Errors the CLI catches and presents cleanly ──────────────────────
# These produce a human-readable message + exit code 1.
# Any other exception is unexpected and gets a generic message
# (full traceback only with --verbose).
_HANDLED_EXCEPTIONS = (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    AgentLoopLimitExceeded,
    ClaudeAPIError,
    OllamaAPIError,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review_pr",
        description="AI-powered Pull Request reviewer. Analyzes a GitHub PR and produces a structured review report.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/name format (e.g. 'fastapi/fastapi')",
    )
    parser.add_argument(
        "--pr",
        required=True,
        type=int,
        help="Pull request number",
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "ollama"],
        default=None,
        help="LLM provider (default: from .env / LLM_PROVIDER)",
    )
    parser.add_argument(
        "--post-comment",
        action="store_true",
        help="Post the review as a comment on the PR",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write the markdown report to a file",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        dest="json_output",
        help="Write the raw structured review JSON to a file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging and show stack traces on errors",
    )
    return parser


def _create_settings(provider_override: str | None) -> Settings:
    """Create Settings, optionally overriding the LLM provider.

    Uses pydantic-settings' constructor override — no os.environ mutation.
    """
    kwargs: dict[str, Any] = {}
    if provider_override is not None:
        kwargs["llm_provider"] = provider_override
    return Settings(**kwargs)


def _create_llm_client(settings: Settings):
    """Factory: create the right LLM client based on settings."""
    if settings.llm_provider == "claude":
        from src.llm.claude_client import ClaudeClient
        return ClaudeClient(settings)
    else:
        from src.llm.ollama_client import OllamaClient
        return OllamaClient(settings)


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


def _run_review(args: argparse.Namespace) -> int:
    """Core review pipeline. Returns exit code (0=success, 1=failure)."""

    # 1. Settings
    settings = _create_settings(args.provider)
    if args.verbose:
        enable_debug()

    logger.info("Starting review: %s PR #%d (provider=%s)", args.repo, args.pr, settings.llm_provider)

    # 2. GitHub client
    pygithub = create_github_client(settings)
    gh_client = GitHubClient(pygithub)

    # 3. LLM client
    llm_client = _create_llm_client(settings)

    # 4. Tool executor
    tool_executor = ToolExecutor()
    _register_tools(tool_executor, gh_client)

    # 5. Fetch PR metadata to build initial state
    pr_diff = gh_client.get_pull_request_diff(args.repo, args.pr)
    # Use head SHA (not branch name) — branch may be deleted post-merge
    pygithub_repo = pygithub.get_repo(args.repo)
    pr_obj = pygithub_repo.get_pull(args.pr)
    head_ref = pr_obj.head.sha

    diff_summary = (
        f"PR title: {pr_diff.title}\n"
        f"Files changed: {', '.join(f.filename for f in pr_diff.changed_files)}"
    )

    initial_state = {
        "repo": args.repo,
        "pr_number": args.pr,
        "head_branch": head_ref,
        "diff_context": diff_summary,
        "commit_metadata": [],
        "files_to_review": [],
        "file_reviews": [],
        "final_review": "",
        "errors": [],
        "trace": [],
    }

    # 6. Build and run the agent graph
    from src.agent.graph import build_graph

    graph = build_graph(llm_client, tool_executor, settings)
    final_state = graph.invoke(initial_state)

    # 7. Check for agent-level errors that didn't raise
    #    (defensive: if somehow errors accumulated without raising)
    agent_errors = final_state.get("errors", [])
    if agent_errors:
        logger.warning("Agent completed with %d error(s):", len(agent_errors))
        for err in agent_errors:
            logger.warning("  - %s", err)

    # 8. Synthesize structured review
    file_reviews = final_state.get("file_reviews", [])
    if not file_reviews:
        print("Error: Review could not be completed — no files were successfully reviewed.", file=sys.stderr)
        print("The agent pipeline ran but produced no file reviews.", file=sys.stderr)
        if agent_errors:
            print(f"Agent errors: {'; '.join(agent_errors)}", file=sys.stderr)
        return 1

    structured_review = synthesize_review(final_state, llm_client)

    # 9. Render
    md_report = render_markdown(structured_review)

    # 10. Output
    print(md_report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md_report)
        print(f"\nReport written to: {args.output}", file=sys.stderr)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(structured_review, f, indent=2, ensure_ascii=False)
        print(f"JSON written to: {args.json_output}", file=sys.stderr)

    # 11. Post comment
    if args.post_comment:
        comment_url = gh_client.post_comment(args.repo, args.pr, md_report)
        print(f"\nComment posted: {comment_url}", file=sys.stderr)

    # 12. Print trace summary
    trace = final_state.get("trace", [])
    if trace:
        print(f"\n--- Tool trace ({len(trace)} calls) ---", file=sys.stderr)
        for t in trace:
            src = t.get("source", "native")
            print(f"  [{src}] {t['tool']}  {t['duration_ms']}ms", file=sys.stderr)

    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        exit_code = _run_review(args)
    except _HANDLED_EXCEPTIONS as exc:
        # Known, expected errors: clean message, no traceback unless --verbose
        print(f"\nError: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        # Unexpected errors
        print(f"\nUnexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        else:
            print("Run with --verbose for full traceback.", file=sys.stderr)
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
