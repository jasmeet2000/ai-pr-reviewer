"""Agent-specific exceptions."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for agent-level errors."""


class AgentLoopLimitExceeded(AgentError):
    """Raised when the tool-calling loop exceeds the max iteration cap.
    
    Prevents infinite hallucination loops when interacting with LLMs.
    """
