"""Application configuration — single typed settings object.

Uses pydantic-settings to load values from .env / environment variables.
Imported wherever config is needed; passed into components via dependency
injection (never accessed as a module-level global inside business logic).
"""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded once at startup.

    Fails loudly if required secrets are missing, so mis-configuration
    surfaces immediately — not three tool calls deep inside the agent loop.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Extra env vars (e.g. PATH) won't cause a validation error.
        extra="ignore",
    )

    # ── LLM provider ──────────────────────────────────────────────────
    anthropic_api_key: str = ""
    llm_provider: Literal["claude", "ollama", "mock"] = "claude"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout_seconds: int = 600

    # ── GitHub ────────────────────────────────────────────────────────
    github_token: str = ""

    # ── FastAPI / CORS ────────────────────────────────────────────────
    cors_origin: str = "http://localhost:8501"

    # ── Agent guardrails ──────────────────────────────────────────────
    max_tool_calls: int = 10

    # ── Logging ───────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Validators ────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _require_secrets(self) -> "Settings":
        """Fail fast if required credentials are missing.

        GITHUB_TOKEN is always required (every run talks to GitHub).
        ANTHROPIC_API_KEY is required when the Claude provider is selected;
        omitting it when using Ollama is fine — forcing users to set a
        dummy key they'll never use would be bad DX.
        """
        if not self.github_token:
            raise ValueError(
                "GITHUB_TOKEN is required. Set it in .env or as an "
                "environment variable (needs repo:read + pull-request "
                "comment:write scopes)."
            )
        if self.llm_provider == "claude" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=claude. "
                "Set it in .env or as an environment variable, or switch "
                "to LLM_PROVIDER=ollama."
            )
        return self

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        """Accept lowercase log levels from .env without surprising users."""
        return v.upper() if isinstance(v, str) else v


def get_settings() -> Settings:
    """Factory for the settings singleton.

    Call this (and pass the result via DI) rather than constructing
    Settings() everywhere — makes it easy to override in tests.
    """
    return Settings()
