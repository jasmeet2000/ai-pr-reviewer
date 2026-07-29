# Phases — AI PR Reviewer & QA Assistant

Work strictly one phase at a time. Do not start a phase until the previous
one is approved. After each phase, update `MEMORY.md`.

## Phase 1 — Architecture & design walkthrough
Explain `ARCHITECTURE.md` in your own words: why each folder exists, the
shared core vs. three thin interfaces (UI/API/CLI), the agent reasoning
loop, and the LLM provider abstraction. Then walk through the key
decisions in `DESIGN.md` (ADR-1 through ADR-5) and the UX notes for the
Streamlit UI. No code yet.

## Phase 2 — Project setup & configuration
`requirements.txt`, `.env.example`, `.gitignore`, `config/settings.py`,
`utils/logger.py`. Confirm the project scaffolding runs (even as stubs)
before moving on.

## Phase 3 — GitHub client
`github/client.py`, `github/auth.py`, `github/models.py`. Diff fetching,
file content fetching, commit metadata, comment posting. Testable in
isolation against a real public repo, no LLM yet.

## Phase 4 — LLM clients (Claude + Ollama)
`llm/base_client.py` (protocol), `llm/claude_client.py`,
`llm/ollama_client.py`, `llm/schemas.py`, `llm/tool_executor.py`. Get a
basic tool-calling round trip working against a trivial tool with the
Claude client before wiring in Ollama or the real tools.

## Phase 5 — Tools
`tools/github_tools.py`, `tools/diff_tools.py`, `tools/file_reader.py`,
`tools/comment_tools.py`, `tools/risk_analysis.py`.

## Phase 6 — Agent (LangGraph or ReAct loop)
`agent/graph.py`, `agent/planner.py`, `agent/state.py` (including the
`trace` list), `agent/review_agent.py`. Core of the demo — LLM decides
which tools to call and when, per `PROMPTS.md`.

## Phase 7 — Review generation
`review/review_generator.py`, `summary_generator.py`, `test_generator.py`,
`security_checks.py`, `style_checks.py`, `diff_parser.py`,
`report_renderer.py` (markdown -> HTML).

## Phase 8 — CLI
`cli/review_pr.py`: `python review_pr.py --repo owner/repo --pr N
[--provider claude|ollama] [--post-comment] [--verbose]`.

## Phase 9 — FastAPI backend
`api/main.py`, `api/routes/review.py`, `api/schemas.py`,
`api/dependencies.py`. `POST /review`, `GET /health`. Reuses
`review_agent.py` directly — no logic duplicated from the CLI.

## Phase 10 — Streamlit UI
`ui/app.py`, `ui/components/review_form.py`, `trace_view.py`,
`review_display.py`. Form to submit repo/PR/provider, live-ish display of
the tool-call trace, rendered findings with severity badges, download
report button, "post to GitHub" button (calls the API, which calls
`post_comment()`).

## Phase 11 — Tests
`tests/test_agent.py`, `test_tools.py`, `test_review.py`, `test_api.py`.
Mock Anthropic/Ollama and GitHub responses. Cover planner decisions, tool
execution, review formatting, API request/response contracts, and error
paths from `ERROR_HANDLING.md`.

## Phase 12 — CI/CD
`.github/workflows/review.yml` — trigger on PR open, checkout, install, run
`review_pr.py` (CLI path, not the UI), post the review. Final README pass
covering all three entry points (UI, CLI, Action) and how to run each.

## Phase 13 (stretch) — MCP framing
Note in README (no need to implement) how `tools/` could be re-exposed as
an MCP server consumed by the agent instead of hardcoded schemas.
