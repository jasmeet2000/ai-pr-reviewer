"""github — GitHub API client package.

Re-exports the key public interfaces so callers can write::

    from src.github import GitHubClient, create_github_client
"""

from src.github.auth import create_github_client
from src.github.client import GitHubClient
from src.github.exceptions import (
    GitHubAuthError,
    GitHubClientError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from src.github.models import ChangedFile, CommitMetadata, PullRequestDiff

__all__ = [
    "ChangedFile",
    "CommitMetadata",
    "GitHubAuthError",
    "GitHubClient",
    "GitHubClientError",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "PullRequestDiff",
    "create_github_client",
]
