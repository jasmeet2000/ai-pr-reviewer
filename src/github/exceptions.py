"""Custom exceptions for the GitHub client layer.

Each exception wraps the underlying PyGithub/HTTP error with a clearer,
actionable message.  See ERROR_HANDLING.md for the full exception taxonomy.
"""

from __future__ import annotations

from datetime import datetime, timezone


class GitHubClientError(Exception):
    """Base exception for all GitHub client errors."""


class GitHubAuthError(GitHubClientError):
    """Raised when GitHub authentication fails (bad or expired token).

    Wraps PyGithub's ``BadCredentialsException`` with a user-actionable
    message that tells the caller *what to do*, not just what went wrong.
    """


class GitHubNotFoundError(GitHubClientError):
    """Raised when a repository, pull request, or file path is not found.

    Wraps PyGithub's ``UnknownObjectException``.
    """


class GitHubRateLimitError(GitHubClientError):
    """Raised when the GitHub API rate limit is exceeded.

    Includes the reset time so callers can inform the user when to retry.

    Attributes:
        reset_at: UTC datetime when the rate limit resets, or ``None``
            if the reset time could not be determined.
    """

    def __init__(self, message: str, reset_at: datetime | None = None) -> None:
        super().__init__(message)
        self.reset_at = reset_at

    @classmethod
    def from_headers(
        cls, headers: dict[str, str], context: str = ""
    ) -> GitHubRateLimitError:
        """Construct from GitHub response headers, extracting reset time.

        Args:
            headers: HTTP response headers from the rate-limited response.
            context: Human-readable description of the operation that
                was rate-limited (e.g. "fetching files for owner/repo PR #1").
        """
        reset_at: datetime | None = None
        reset_str = "unknown"

        raw = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
        if raw:
            try:
                reset_at = datetime.fromtimestamp(int(raw), tz=timezone.utc)
                reset_str = reset_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, OSError):
                pass

        msg = "GitHub API rate limit exceeded"
        if context:
            msg += f" while {context}"
        msg += f". Resets at {reset_str}."

        return cls(msg, reset_at=reset_at)
