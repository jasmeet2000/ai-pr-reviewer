"""Tool JSON schemas shared by all LLM providers."""

from __future__ import annotations

from typing import Any

# The agent uses these shared schemas for Claude, Ollama, etc.
# Tool definitions follow the standard JSON Schema format for functions.

GET_DIFF_SCHEMA: dict[str, Any] = {
    "name": "get_diff",
    "description": "Fetch the full diff of the pull request, including all changes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in owner/name format, e.g., 'encode/httpx'",
            },
            "pr_number": {"type": "integer", "description": "Pull request number"},
        },
        "required": ["repo", "pr_number"],
    },
}

GET_FILE_CONTENTS_SCHEMA: dict[str, Any] = {
    "name": "get_file_contents",
    "description": "Fetch the entire contents of a single file at a specific reference.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in owner/name format",
            },
            "path": {
                "type": "string",
                "description": "Path to the file in the repository",
            },
            "ref": {
                "type": "string",
                "description": "Git reference (branch, tag, or SHA). You MUST use the head branch of the PR.",
            },
        },
        "required": ["repo", "path"],
    },
}

LIST_CHANGED_FILES_SCHEMA: dict[str, Any] = {
    "name": "list_changed_files",
    "description": "List all files changed in a pull request with additions/deletions counts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in owner/name format",
            },
            "pr_number": {"type": "integer", "description": "Pull request number"},
        },
        "required": ["repo", "pr_number"],
    },
}

GET_COMMIT_METADATA_SCHEMA: dict[str, Any] = {
    "name": "get_commit_metadata",
    "description": "Fetch metadata for all commits in a pull request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in owner/name format",
            },
            "pr_number": {"type": "integer", "description": "Pull request number"},
        },
        "required": ["repo", "pr_number"],
    },
}

# The complete list of standard tools available to the LLMs.
# Note: post_comment is intentionally omitted per requirements unless explicitly enabled.
DEFAULT_TOOLS: list[dict[str, Any]] = [
    GET_DIFF_SCHEMA,
    GET_FILE_CONTENTS_SCHEMA,
    LIST_CHANGED_FILES_SCHEMA,
    GET_COMMIT_METADATA_SCHEMA,
]
