"""GitHub authentication — creates an authenticated PyGithub client.

Reads the token from the ``Settings`` object (not directly from
``os.environ``) to maintain the DI pattern established in Phase 2.
"""

from __future__ import annotations

from github import Auth, Github

from src.config.settings import Settings
from src.github.exceptions import GitHubAuthError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_github_client(settings: Settings) -> Github:
    """Create an authenticated PyGithub ``Github`` instance.

    Args:
        settings: Application settings containing the GitHub token.

    Returns:
        An authenticated PyGithub ``Github`` instance ready for use.

    Raises:
        GitHubAuthError: If the token is empty (should not happen if
            ``Settings`` validation passed, but guards against misuse).
    """
    token = settings.github_token
    if not token:
        raise GitHubAuthError(
            "GitHub token is not configured. Set GITHUB_TOKEN in .env "
            "or as an environment variable."
        )

    logger.debug("Creating GitHub client (authenticated)")
    auth = Auth.Token(token)
    return Github(auth=auth)
