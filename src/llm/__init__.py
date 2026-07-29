"""llm — LLM client package.

Exposes the base Protocol and concrete clients, plus schemas and executors.
"""

from src.llm.base_client import LLMClient
from src.llm.claude_client import ClaudeClient
from src.llm.exceptions import (
    ClaudeAPIError,
    LLMClientError,
    OllamaAPIError,
    ToolExecutionError,
)
from src.llm.ollama_client import OllamaClient
from src.llm.schemas import DEFAULT_TOOLS
from src.llm.tool_executor import ToolExecutor

__all__ = [
    "ClaudeAPIError",
    "ClaudeClient",
    "DEFAULT_TOOLS",
    "LLMClient",
    "LLMClientError",
    "OllamaAPIError",
    "OllamaClient",
    "ToolExecutionError",
    "ToolExecutor",
]
