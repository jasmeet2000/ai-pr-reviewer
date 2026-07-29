"""Ollama-specific implementation of the LLMClient Protocol."""

from __future__ import annotations

import httpx
import json
from typing import Any

from src.config.settings import Settings
from src.llm.base_client import LLMClient
from src.llm.exceptions import OllamaAPIError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient(LLMClient):
    """Client for local Ollama models.

    Note: This requires Ollama to be running locally (or wherever `ollama_host` points).
    If Ollama isn't running, it will fail loudly.
    """

    def __init__(self, settings: Settings) -> None:
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        # Use httpx for robust synchronous HTTP requests
        self.client = httpx.Client(timeout=float(settings.ollama_timeout_seconds))

    def send_message(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Send a message to Ollama's chat API."""
        url = f"{self.host.rstrip('/')}/api/chat"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        # Ollama supports system prompts natively in the message list or via system parameter
        # depending on the version, but standard Ollama expects system as a separate param or
        # first message. We'll add it as the first message if present.
        if system_prompt:
            payload["messages"] = [
                {"role": "system", "content": system_prompt}
            ] + messages

        if tools:
            # Note: Ollama tool support requires fairly recent versions (0.1.23+).
            # The schema format aligns closely with OpenAI's.
            # We must map Anthropic's `input_schema` to OpenAI's `parameters`.
            mapped_tools = []
            for t in tools:
                func_def = {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}})
                }
                mapped_tools.append({"type": "function", "function": func_def})
            payload["tools"] = mapped_tools

        try:
            logger.debug(f"Calling Ollama API at {url} with model {self.model}")
            # Dump the exact messages to a file for debugging
            with open("last_ollama_messages.json", "w") as f:
                json.dump(payload["messages"], f, indent=2)

            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data, tools)
        except httpx.RequestError as e:
            logger.error(f"Ollama network error: {e}")
            raise OllamaAPIError(
                f"Failed to connect to Ollama at {self.host}. Is it running? Error: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise OllamaAPIError(
                f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}"
            ) from e

    def _parse_response(self, data: dict[str, Any], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        """Convert Ollama's response format into our standard dict."""
        message = data.get("message", {})
        
        tool_calls = message.get("tool_calls", [])
        content = message.get("content", "")
        source = "native"

        # ── Fallback Parser ─────────────────────────────────────────────
        # If native tool_calls is empty, but we provided tools and there's 
        # content, check if the content is just a JSON string describing a tool call.
        if not tool_calls and tools and content:
            content_stripped = content.strip()
            # Often models wrap json in markdown blocks
            if content_stripped.startswith("```json"):
                content_stripped = content_stripped[7:]
            if content_stripped.endswith("```"):
                content_stripped = content_stripped[:-3]
            content_stripped = content_stripped.strip()
            
            if content_stripped.startswith("{") and content_stripped.endswith("}"):
                import json
                try:
                    parsed = json.loads(content_stripped)
                    # Rough validation: must have a name that matches a registered tool
                    if "name" in parsed and "arguments" in parsed and isinstance(parsed["arguments"], dict):
                        matched_tool = None
                        for t in tools:
                            if t["name"] == parsed["name"]:
                                matched_tool = t
                                break

                        if matched_tool is not None:
                            # Check arguments against schema (basic key presence)
                            required_keys = matched_tool.get("input_schema", {}).get("required", [])
                            if all(k in parsed["arguments"] for k in required_keys):
                                logger.warning(
                                    f"Fallback parser triggered: Ollama emitted tool call "
                                    f"'{parsed['name']}' as text content. Injecting as tool_call."
                                )
                                tool_calls.append({
                                    "function": {
                                        "name": parsed["name"],
                                        "arguments": parsed["arguments"]
                                    }
                                })
                                source = "fallback_parsed"
                            else:
                                logger.warning(
                                    f"Fallback parser: '{parsed['name']}' matched but missing "
                                    f"required keys {required_keys}. Treating as plain text."
                                )
                        else:
                            logger.warning(
                                f"Fallback parser: '{parsed.get('name')}' does not match any "
                                f"registered tool. Treating as plain text (not injecting)."
                            )
                except json.JSONDecodeError:
                    pass

        # Standardize output
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
            "source": source,
        }
