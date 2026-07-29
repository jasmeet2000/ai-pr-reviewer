# Error Handling — AI PR Reviewer & QA Assistant

## Principles
- Fail loudly and specifically. No bare `except:` blocks.
- Define custom exceptions per layer so callers can catch meaningfully:
  - `github/`: `GitHubAuthError`, `GitHubNotFoundError`, `GitHubRateLimitError`
  - `llm/`: `ClaudeAPIError`, `ToolExecutionError`
  - `agent/`: `AgentLoopLimitExceeded` (when the tool-calling loop exceeds
    the max iteration cap from `SECURITY.md`)
- CLI layer catches these and prints a clean, actionable message —
  stack traces only appear with `--verbose`.

## Specific cases to handle
- PR not found / repo not found -> clear CLI error, exit code non-zero.
- GitHub rate limit hit -> surface remaining-quota info if available,
  don't retry silently in a loop.
- Anthropic API error/timeout -> one retry with backoff, then fail with a
  clear message; don't silently return a partial/empty review.
- Diff too large for context -> truncate deliberately (e.g. per-file, with
  a note in the output that truncation occurred), never fail silently.
- Malformed tool-call arguments from the LLM -> catch, log, and return a
  structured error back to the agent loop so the LLM can retry/adjust,
  rather than crashing the whole process.

## API layer
- FastAPI exception handlers map internal exceptions to clean HTTP
  responses: `{error: str, detail: str}` with an appropriate status code
  (404 for not found, 429 for rate limit, 502 for upstream LLM/GitHub
  failure, 400 for bad input). Never leak a raw stack trace in the body.
- The Streamlit UI should surface these `error`/`detail` fields directly to
  the user rather than a generic "something went wrong."

## Testing requirement
Every custom exception above needs at least one test in `tests/` that
triggers it via a mocked failure and asserts the CLI's error output.
