# Rules — Coding Standards & Conventions

## Python
- Python 3.12. Type hints on every function signature, including returns.
- Docstrings (Google style) on every public function and class.
- No function longer than ~40 lines; no file longer than ~200 lines. If a
  file grows past that, propose a split.
- Prefer composition and dependency injection (pass clients/config in,
  don't reach for globals) so tests can mock cleanly.
- Use `dataclasses` or `pydantic` models for structured data (agent state,
  tool inputs/outputs, review findings) — not raw dicts passed around.

## Formatting & linting
- `black` for formatting, `ruff` for linting, `mypy` for type checking.
  All three must pass with zero errors before a phase is considered done.

## Logging
- Use `logging`, not `print`, anywhere outside the CLI's final output.
- Log tool calls (what was called, with what args, at debug level) so the
  agent's reasoning is inspectable with `--verbose`.

## Git-style hygiene (even though this isn't a team repo)
- Commit-sized units of work per phase.
- No commented-out dead code left in.
- No hardcoded secrets — everything sensitive comes from `.env` via
  `config/settings.py`.

## Naming
- Tools are verbs: `get_diff`, `post_comment`, not `diff` or `comment`.
- Agent state fields are nouns: `diff`, `findings`, `files_read`.

## FastAPI & Streamlit
- API routes are thin: parse/validate input, call `agent/review_agent.py`,
  map result/errors to response models. No business logic in `api/routes/`.
- Streamlit components (`ui/components/`) are also thin: call the API,
  render the response. No agent logic duplicated in the UI layer.
- The LLM provider is chosen via a config value / UI dropdown, resolved to
  a concrete `LLMClient` at request time — the agent code never imports
  `claude_client` or `ollama_client` directly, only the `LLMClient`
  protocol from `llm/base_client.py`.

## When in doubt
State the trade-off and the choice you're making, rather than picking
silently. This is a portfolio project — the reasoning is part of the
deliverable.
