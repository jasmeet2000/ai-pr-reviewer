"""FastAPI dependencies for dependency injection."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.config.settings import Settings


@lru_cache()
def get_base_settings() -> Settings:
    """Return the global, cached settings instance.
    
    Reads from .env on startup and caches the result.
    """
    return Settings()


# Type alias for injecting settings into route handlers
SettingsDep = Annotated[Settings, Depends(get_base_settings)]
