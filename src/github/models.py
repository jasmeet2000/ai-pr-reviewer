"""Typed domain models for GitHub data.

These decouple the rest of the application from PyGithub's object shapes.
The agent and tools layers receive these models — never raw PyGithub objects
or untyped dicts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ChangedFile:
    """A single file changed in a pull request.

    Attributes:
        filename: Path of the file relative to the repo root.
        status: One of ``"added"``, ``"modified"``, ``"removed"``,
            ``"renamed"``.
        additions: Number of lines added.
        deletions: Number of lines removed.
        patch: Unified-diff text for this file, or ``None`` if the patch
            was omitted (e.g. binary file, or lightweight listing mode).
        previous_filename: Set only for renames; the file's old path.
    """

    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None
    previous_filename: str | None = None


@dataclass(slots=True)
class PullRequestDiff:
    """Full diff context for a pull request.

    Attributes:
        repo: Repository in ``"owner/name"`` format.
        pr_number: Pull request number.
        title: PR title.
        description: PR body / description (empty string if unset).
        base_branch: The branch being merged *into*.
        head_branch: The branch being merged *from*.
        changed_files: All files changed, with patches included.
        total_additions: Sum of additions across all files.
        total_deletions: Sum of deletions across all files.
    """

    repo: str
    pr_number: int
    title: str
    description: str
    base_branch: str
    head_branch: str
    changed_files: list[ChangedFile]
    total_additions: int
    total_deletions: int


@dataclass(slots=True)
class CommitMetadata:
    """Metadata for a single commit in a pull request.

    Attributes:
        sha: Full 40-character commit SHA.
        message: Commit message (first line + body).
        author: Author display name.
        date: Author-date as a timezone-aware datetime.
    """

    sha: str
    message: str
    author: str
    date: datetime
