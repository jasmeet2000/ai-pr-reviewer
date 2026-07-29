# Architecture — AI PR Reviewer & QA Assistant

## System overview

```
                     Streamlit UI
                          |
                          v
                   FastAPI Backend
                          |
                          v
                  LangGraph Agent
                          |
        +-----------------+------------------+
        v                 v                  v
   GitHub API        LLM Provider        Local Tools
   (PyGithub)      (Claude / Ollama)   (diff parse, risk)
        |                 |                  |
        +-----------------+------------------+
                          v
                  Structured Review
                          |
             +------------+-------------+
             v                          v
      Download Report            Post to GitHub
      (markdown / HTML)          (PR comment)
```

There are three ways to trigger a review, all going through the same
agent core:

1. **Streamlit UI** -> calls the FastAPI backend -> agent runs -> UI shows
   live tool-call trace + rendered review + download/post buttons.
2. **CLI** (`review_pr.py`) -> calls the agent core directly (no HTTP hop
   needed for a local run) -> prints markdown, optional `--post-comment`.
3. **GitHub Action** -> runs the CLI in CI on PR open -> posts the review
   as a comment automatically.

All three are thin entry points over one shared `agent/` + `review/` core.
This is the key architectural point for the interview: the agent logic is
not duplicated per interface — UI, API, and CLI are just different callers.

## Folder structure

```
project/
  README.md
  requirements.txt
  .env.example
  .gitignore
  src/
    agent/
      graph.py            # LangGraph graph definition (or ReAct loop fallback)
      planner.py           # decides next action given current state
      review_agent.py      # top-level agent entry point (shared by API/CLI)
      state.py             # typed agent state, includes tool-call trace
      prompts.py           # system/tool prompts (see PROMPTS.md)
    tools/
      github_tools.py
      diff_tools.py
      file_reader.py
      comment_tools.py
      risk_analysis.py
    github/
      client.py
      auth.py
      models.py
    llm/
      base_client.py       # LLMClient protocol/interface
      claude_client.py      # Anthropic implementation
      ollama_client.py       # local model implementation
      tool_executor.py
      schemas.py
    review/
      diff_parser.py
      review_generator.py
      summary_generator.py
      test_generator.py
      security_checks.py
      style_checks.py
      report_renderer.py    # markdown -> HTML for download/report.html
    api/
      main.py                # FastAPI app
      routes/
        review.py             # POST /review, GET /review/{id}/status
      schemas.py               # request/response pydantic models
      dependencies.py           # DI: settings, agent factory
    ui/
      app.py                    # Streamlit entry point
      components/
        review_form.py           # repo/PR input, provider select
        trace_view.py             # live tool-call visualization
        review_display.py         # rendered findings, severity badges
    cli/
      review_pr.py
    config/
      settings.py
    utils/
      logger.py
      helpers.py
  tests/
    test_agent.py
    test_tools.py
    test_review.py
    test_api.py
  .github/workflows/
    review.yml
```

**Why this structure:** `agent/` and `review/` are the shared core;
`api/`, `ui/`, and `cli/` are three independent, thin interfaces over that
core. `llm/base_client.py` defines a small `LLMClient` protocol so
`claude_client.py` and `ollama_client.py` are interchangeable — the agent
never hardcodes a provider.

## Agent reasoning loop

```
Request arrives (from UI, CLI, or Action) with {repo, pr_number, provider}
        |
        v
   Planner (LLM decides next action)
        |
   ---------------------------
   | Need the diff?           | -> call get_diff()
   | Need a specific file?    | -> call get_file_contents()
   | Need commit context?     | -> call get_commit_metadata()
   | Enough info gathered?    | -> proceed to synthesis
   ---------------------------
        |  (each step appended to state.trace for UI visualization)
        v
   Generate findings -> QA checklist -> regression risk -> summary
        |
        v
   review_generator.py assembles structured review
        |
        v
   report_renderer.py -> markdown + HTML
        |
        v
   If post_to_github requested: call post_comment()
```

The `state.trace` list (each entry: tool name, args, result summary,
timestamp) is what the Streamlit UI renders as the "agent reasoning"
visualization — it's not a separate mechanism, it's the same state the
agent already needs internally.

## API layer (FastAPI)

- `POST /review` — body: `{repo, pr_number, provider, post_to_github}`.
  Runs the agent synchronously for the prototype (simplest to demo and
  reason about); note in README that a production version would make this
  async with a job ID + polling or websockets, given LLM calls can take
  10-30s.
- `GET /health` — trivial liveness check.
- CORS restricted to the Streamlit UI's origin in `.env`.
- No auth for the prototype (single-user, local/demo use) — call this out
  explicitly as a known gap in `SECURITY.md` and README, not silently
  omitted.

## Data flow

1. UI or CLI collects `{repo, pr_number, provider}`.
2. Request reaches `review_agent.py` (via FastAPI route or directly from
   CLI — same function either way).
3. Agent loop runs, appending to `state.trace` as it goes.
4. `review_generator.py` produces the structured review (see
   `PROMPTS.md` for the schema).
5. `report_renderer.py` produces markdown + HTML.
6. Caller (UI/CLI) displays it, offers download, and/or triggers
   `post_comment()`.

## Key design decisions (talking points)

- **Shared core, three thin interfaces**: demonstrates you understand
  separation between business logic and delivery mechanism — a core
  software engineering principle, not just an AI demo trick.
- **LLM provider abstraction (Claude/Ollama)**: shows awareness of
  cost/latency/privacy trade-offs between hosted and local models — a real
  consideration for any org building internal AI tooling.
- **Synchronous API for v1**: a deliberate, stated trade-off for prototype
  simplicity, with an explicit note on what you'd change for production
  (async job queue) — better than accidentally building something naive
  and not knowing it.
- **Trace-as-state**: the same data structure that drives the tool-calling
  loop also drives the UI visualization — no duplicate bookkeeping.
