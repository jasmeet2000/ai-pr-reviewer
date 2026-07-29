"""Base Protocol/ABC for all LLM clients."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol that all concrete LLM providers must implement.

    Ensures the agent can swap between Claude, Ollama, etc. without code changes.
    """

    def send_message(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Send a message to the LLM and return its response.

        Args:
            messages: Conversation history in standard format (role, content).
            tools: List of tool schemas (from schemas.py).
            system_prompt: Optional system prompt to guide behavior.

        Returns:
            The raw provider response mapped into a standardized dict, usually
            containing:
                - "content": the text output
                - "tool_calls": list of requested tool executions (if any)
                - "role": "assistant"
        """
        ...
