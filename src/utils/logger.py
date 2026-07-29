"""Centralized logging factory.

Every module should call ``get_logger(__name__)`` once at module level.
The root verbosity is controlled by the ``LOG_LEVEL`` setting in ``.env``
(default INFO).  The CLI's ``--verbose`` flag flips the root logger to
DEBUG at runtime via :func:`enable_debug`.

Usage::

    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Review started for %s PR #%d", repo, pr_number)
"""

from __future__ import annotations

import logging
import sys

# ── Module state ──────────────────────────────────────────────────────
_CONFIGURED = False


def _configure_root(level: str = "INFO") -> None:
    """Set up the root logger exactly once.

    Args:
        level: A standard Python log-level name (DEBUG, INFO, …).
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level.upper())

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring the root logger on first call.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` scoped to *name*.
    """
    # Lazy-import settings so the logger module itself has no hard
    # dependency on pydantic at import time — this matters during early
    # startup and in tests that don't need a full Settings object.
    try:
        from src.config.settings import Settings

        settings = Settings()
        level = settings.log_level
    except Exception:
        # If settings can't load yet (e.g. missing env in a test), fall
        # back to INFO — never crash just because someone imported the
        # logger before .env was available.
        level = "INFO"

    _configure_root(level)
    return logging.getLogger(name)


def enable_debug() -> None:
    """Switch the root logger to DEBUG at runtime.

    Called by the CLI when ``--verbose`` is passed.  Safe to call
    multiple times; only the first call has an effect on handler setup,
    and subsequent calls just lower the threshold.
    """
    _configure_root("DEBUG")  # no-op if already configured
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in root.handlers:
        handler.setLevel(logging.DEBUG)
