"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.routes import review
from src.api.schemas import HealthResponse, ErrorResponse
from src.agent.exceptions import AgentLoopLimitExceeded
from src.config.settings import Settings
from src.github.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubClientError,
)
from src.llm.exceptions import ClaudeAPIError, OllamaAPIError, LLMClientError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Application Setup ────────────────────────────────────────────────

app = FastAPI(
    title="AI PR Reviewer API",
    description="API for automated Pull Request reviews using LLMs.",
    version="1.0.0",
)

settings = Settings()

# CORS configuration
if settings.cors_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(review.router)

# ── Routes ───────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Trivial liveness check."""
    return HealthResponse(provider=settings.llm_provider)

# ── Exception Handlers ───────────────────────────────────────────────

def _error_response(status_code: int, error_msg: str, detail_msg: str) -> JSONResponse:
    """Helper to return consistent JSON error shapes."""
    content = ErrorResponse(error=error_msg, detail=detail_msg).model_dump()
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(GitHubNotFoundError)
async def github_not_found_handler(request: Request, exc: GitHubNotFoundError):
    return _error_response(404, "Not Found", str(exc))


@app.exception_handler(GitHubRateLimitError)
async def github_rate_limit_handler(request: Request, exc: GitHubRateLimitError):
    return _error_response(429, "Rate Limit Exceeded", str(exc))


@app.exception_handler(GitHubAuthError)
async def github_auth_handler(request: Request, exc: GitHubAuthError):
    # 401 Unauthorized because the GitHub token is bad
    return _error_response(401, "GitHub Authentication Failed", str(exc))


@app.exception_handler(GitHubClientError)
async def github_client_error_handler(request: Request, exc: GitHubClientError):
    # 502 Bad Gateway for upstream GitHub failures
    return _error_response(502, "GitHub API Error", str(exc))


@app.exception_handler(ClaudeAPIError)
@app.exception_handler(OllamaAPIError)
@app.exception_handler(LLMClientError)
async def llm_error_handler(request: Request, exc: LLMClientError):
    # 502 Bad Gateway for upstream LLM provider failures
    return _error_response(502, "LLM Provider Error", str(exc))


@app.exception_handler(AgentLoopLimitExceeded)
async def agent_loop_limit_handler(request: Request, exc: AgentLoopLimitExceeded):
    # 500 Internal Server Error - The agent failed to converge or synthesize a review within the allowed loops
    return _error_response(500, "Review Generation Failed", str(exc))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception in API: %s: %s", type(exc).__name__, str(exc), exc_info=True)
    return _error_response(500, "Internal Server Error", "An unexpected error occurred.")
