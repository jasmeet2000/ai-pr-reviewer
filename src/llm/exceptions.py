"""Exceptions for the LLM layer."""

from __future__ import annotations


class LLMClientError(Exception):
    """Base exception for all LLM client errors."""


class ClaudeAPIError(LLMClientError):
    """Raised when the Claude API returns an error or times out."""


class OllamaAPIError(LLMClientError):
    """Raised when the Ollama API returns an error or times out."""


class ToolExecutionError(LLMClientError):
    """Raised when a tool execution fails due to invalid arguments or internal errors.

    The string representation of this error should be safe to return to the LLM
    as a tool result so it can correct its behavior.
    """
