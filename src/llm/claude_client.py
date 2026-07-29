"""Claude-specific implementation of the LLMClient Protocol."""

from __future__ import annotations

import time
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError

from src.config.settings import Settings
from src.llm.base_client import LLMClient
from src.llm.exceptions import ClaudeAPIError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeClient(LLMClient):
    """Client for Anthropic's Claude models.

    Implements a single retry with backoff for transient errors, per ERROR_HANDLING.md.
    """

    def __init__(
        self, settings: Settings, model: str = "claude-3-5-sonnet-20240620"
    ) -> None:
        if not settings.anthropic_api_key:
            raise ClaudeAPIError("Anthropic API key is required but not configured.")
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model

    def send_message(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Send a message to Claude, handling retries and standardizing the response."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if system_prompt:
            kwargs["system"] = system_prompt

        retries = 1
        delay = 2.0  # initial backoff delay

        for attempt in range(retries + 1):
            try:
                logger.debug(f"Calling Claude (attempt {attempt + 1}/{retries + 1})")
                response = self.client.messages.create(**kwargs)
                return self._parse_response(response)
            except (APIError, APITimeoutError) as e:
                if attempt < retries:
                    logger.warning(f"Claude API error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error("Claude API error. Max retries exceeded.")
                    raise ClaudeAPIError(
                        f"Claude API failed after {retries} retries: {e}"
                    ) from e

        # This should never be reached due to the raise in the loop above.
        raise ClaudeAPIError("Unexpected exit from retry loop.")

    def _parse_response(self, response: Any) -> dict[str, Any]:
        """Convert Anthropic's proprietary response format into our standard dict."""
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        }
