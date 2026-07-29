"""Tool executor dispatcher."""

from __future__ import annotations

import json
from typing import Any, Callable

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ToolExecutor:
    """Dispatches tool calls to actual Python functions.

    Catches errors inside tool functions and returns them as structured
    JSON strings back to the LLM (as required by ERROR_HANDLING.md),
    preventing the whole agent loop from crashing on bad LLM arguments.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[..., Any]] = {}
        self._cache: dict[str, str] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a Python function to a tool name."""
        self._registry[name] = func

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return its result as a JSON-encoded string.

        Args:
            tool_name: The name of the tool to run.
            arguments: The arguments passed by the LLM.

        Returns:
            A string (JSON encoded) representing the result or error.
        """
        logger.debug(f"Executing tool {tool_name} with args {arguments}")

        cache_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        if cache_key in self._cache:
            logger.info(f"Duplicate tool call prevented: returning cached result for {tool_name}")
            return self._cache[cache_key]

        if tool_name not in self._registry:
            error_msg = f"Unknown tool: {tool_name}"
            logger.warning(error_msg)
            return json.dumps({"error": error_msg})

        func = self._registry[tool_name]
        try:
            # We assume tools return dicts, lists, or primitive types.
            result = func(**arguments)
            json_result = json.dumps({"result": result})
            self._cache[cache_key] = json_result
            return json_result
        except TypeError as e:
            # Missing or unexpected arguments
            error_msg = f"Invalid arguments for {tool_name}: {e}"
            logger.warning(error_msg)
            return json.dumps({"error": error_msg})
        except Exception as e:
            # Domain-specific errors (e.g. GitHubRateLimitError) will be caught here
            # and returned gracefully to the model.
            error_msg = f"Tool execution failed: {type(e).__name__}: {e}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
