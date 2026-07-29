"""GitHub API client — typed, testable wrapper around PyGithub.

Testability strategy: the ``Github`` instance is **injected** via the
constructor.  Production code passes the authenticated client from
``auth.create_github_client()``; unit tests pass a mock ``Github``
object — no network calls required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from github import Github
from github import (
    BadCredentialsException,
    RateLimitExceededException,
    UnknownObjectException,
)
from github.PullRequest import PullRequest as GHPullRequest
from github.Repository import Repository as GHRepo

from src.github.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from src.github.models import ChangedFile, CommitMetadata, PullRequestDiff
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Typed GitHub client that converts PyGithub objects to domain models.

    Args:
        github: An authenticated (or anonymous) PyGithub ``Github``
            instance.  Injected so tests can substitute a mock.
    """

    def __init__(self, github: Github) -> None:
        self._github = github

    # ── Public API ────────────────────────────────────────────────────

    def get_pull_request_diff(self, repo: str, pr_number: int) -> PullRequestDiff:
        """Fetch the full diff for a pull request, including file patches.

        Args:
            repo: Repository in ``"owner/name"`` format.
            pr_number: Pull request number.

        Returns:
            A ``PullRequestDiff`` with all changed files and patches.
        """
        gh_repo = self._get_repo(repo)
        pr = self._get_pull_request(gh_repo, pr_number, repo)

        logger.debug("Fetching files for %s PR #%d", repo, pr_number)
        gh_files = self._paginated_list(
            pr.get_files,
            context=f"fetching files for {repo} PR #{pr_number}",
        )

        changed = [self._to_changed_file(f, include_patch=True) for f in gh_files]

        return PullRequestDiff(
            repo=repo,
            pr_number=pr_number,
            title=pr.title,
            description=pr.body or "",
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            changed_files=changed,
            total_additions=pr.additions,
            total_deletions=pr.deletions,
        )

    def list_changed_files(self, repo: str, pr_number: int) -> list[ChangedFile]:
        """List files changed in a PR (without patches, for a quick overview).

        Args:
            repo: Repository in ``"owner/name"`` format.
            pr_number: Pull request number.

        Returns:
            Changed files with ``patch`` set to ``None``.
        """
        gh_repo = self._get_repo(repo)
        pr = self._get_pull_request(gh_repo, pr_number, repo)

        logger.debug("Listing changed files for %s PR #%d", repo, pr_number)
        gh_files = self._paginated_list(
            pr.get_files,
            context=f"listing files for {repo} PR #{pr_number}",
        )
        return [self._to_changed_file(f, include_patch=False) for f in gh_files]

    def get_commit_metadata(self, repo: str, pr_number: int) -> list[CommitMetadata]:
        """Fetch metadata for all commits in a pull request.

        Args:
            repo: Repository in ``"owner/name"`` format.
            pr_number: Pull request number.

        Returns:
            One ``CommitMetadata`` per commit in the PR.
        """
        gh_repo = self._get_repo(repo)
        pr = self._get_pull_request(gh_repo, pr_number, repo)

        logger.debug("Fetching commits for %s PR #%d", repo, pr_number)
        gh_commits = self._paginated_list(
            pr.get_commits,
            context=f"fetching commits for {repo} PR #{pr_number}",
        )

        results: list[CommitMetadata] = []
        for c in gh_commits:
            git_commit = c.commit
            author = git_commit.author
            results.append(
                CommitMetadata(
                    sha=c.sha,
                    message=git_commit.message,
                    author=author.name if author else "Unknown",
                    date=(
                        author.date
                        if author and author.date
                        else datetime.now(tz=timezone.utc)
                    ),
                )
            )
        return results

    def get_file_contents(self, repo: str, path: str, ref: str | None = None) -> str:
        """Fetch the decoded contents of a single file.

        Args:
            repo: Repository in ``"owner/name"`` format.
            path: File path within the repository.
            ref: Git ref (branch, tag, or SHA).  Defaults to the repo's
                default branch.

        Returns:
            The file contents decoded as UTF-8.
        """
        gh_repo = self._get_repo(repo)
        logger.debug("Fetching %s from %s (ref=%s)", path, repo, ref)

        try:
            kwargs: dict[str, str] = {}
            if ref:
                kwargs["ref"] = ref
            content = gh_repo.get_contents(path, **kwargs)
        except UnknownObjectException as exc:
            detail = f"File '{path}' not found in {repo}"
            if ref:
                detail += f" at ref '{ref}'"
            raise GitHubNotFoundError(f"{detail}.") from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError.from_headers(
                exc.headers or {},
                context=f"fetching {path} from {repo}",
            ) from exc

        if isinstance(content, list):
            raise GitHubNotFoundError(
                f"'{path}' is a directory, not a file, in {repo}."
            )
        text_content = content.decoded_content.decode("utf-8", errors="replace")
        max_len = 8000
        if len(text_content) > max_len:
            logger.warning("Truncating file content for %s to %d chars", path, max_len)
            text_content = text_content[:max_len] + f"\n\n...[Content truncated: exceeded {max_len} chars]..."
        
        return text_content

    def post_comment(self, repo: str, pr_number: int, body: str) -> str:
        """Post a comment on a pull request.

        Args:
            repo: Repository in ``"owner/name"`` format.
            pr_number: Pull request number.
            body: Markdown body of the comment.

        Returns:
            The URL of the created comment.
        """
        gh_repo = self._get_repo(repo)
        pr = self._get_pull_request(gh_repo, pr_number, repo)

        logger.info("Posting comment on %s PR #%d", repo, pr_number)
        try:
            comment = pr.create_issue_comment(body)
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError.from_headers(
                exc.headers or {},
                context=f"posting comment on {repo} PR #{pr_number}",
            ) from exc

        logger.info("Comment posted: %s", comment.html_url)
        return comment.html_url

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_repo(self, repo: str) -> GHRepo:
        """Look up a repository, translating PyGithub exceptions."""
        try:
            return self._github.get_repo(repo)
        except BadCredentialsException as exc:
            raise GitHubAuthError(
                "GitHub authentication failed. Check that GITHUB_TOKEN "
                "is valid and not expired."
            ) from exc
        except UnknownObjectException as exc:
            raise GitHubNotFoundError(
                f"Repository '{repo}' not found. Check the owner/name "
                f"format and that you have access."
            ) from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError.from_headers(
                exc.headers or {}, context=f"accessing repo {repo}"
            ) from exc

    def _get_pull_request(
        self, gh_repo: GHRepo, pr_number: int, repo: str
    ) -> GHPullRequest:
        """Look up a pull request, translating PyGithub exceptions."""
        try:
            return gh_repo.get_pull(pr_number)
        except UnknownObjectException as exc:
            raise GitHubNotFoundError(
                f"Pull request #{pr_number} not found in {repo}."
            ) from exc
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError.from_headers(
                exc.headers or {},
                context=f"accessing {repo} PR #{pr_number}",
            ) from exc

    @staticmethod
    def _paginated_list(fetch_fn, context: str) -> list:  # type: ignore[type-arg]
        """Consume a PyGithub paginated list, wrapping rate-limit errors."""
        try:
            return list(fetch_fn())
        except RateLimitExceededException as exc:
            raise GitHubRateLimitError.from_headers(
                exc.headers or {}, context=context
            ) from exc

    @staticmethod
    def _to_changed_file(f, *, include_patch: bool) -> ChangedFile:  # type: ignore[no-untyped-def]
        """Convert a PyGithub File to our domain model."""
        prev = f.previous_filename
        return ChangedFile(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
            patch=f.patch if include_patch else None,
            previous_filename=prev if isinstance(prev, str) else None,
        )
