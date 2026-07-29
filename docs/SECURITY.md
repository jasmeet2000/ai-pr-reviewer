# Security — AI PR Reviewer & QA Assistant

This covers two things: security of the tool itself, and the security
checks the tool performs on reviewed code. Keep them distinct in the code
and in interview explanations.

## Security of the tool itself

- GitHub tokens and Anthropic API keys live only in `.env`, loaded via
  `config/settings.py`. Never logged, never printed, never committed.
  `.env.example` ships with placeholder values only.
- Scope the GitHub token to the minimum needed (repo read + PR comment
  write). Document this requirement in the README.
- `post_comment()` should require an explicit `--post-comment` flag — never
  post as a side effect of a dry run.
- Treat file contents fetched from the repo as untrusted text when
  constructing prompts — don't let fetched content be interpreted as
  instructions to the agent (basic prompt-injection awareness). Mention
  this explicitly in the README as a known risk class for agentic tools
  that read external content, and note it as a "future improvement" to add
  input sanitization / a system-prompt boundary that explicitly labels
  fetched content as data, not instructions.
- Rate-limit or cap tool-calling loops (e.g. max N tool calls per review) so
  a misbehaving agent loop can't spiral into runaway API spend.

## Security of the FastAPI layer

- No auth in v1 — call this out explicitly in the README as a known,
  deliberate gap for a local/demo prototype, not an oversight. Note API
  key or OAuth as the production next step.
- CORS restricted to the Streamlit UI's origin via `.env`, not `*`.
- Validate `repo` and `pr_number` inputs with pydantic before they reach
  the agent — reject malformed repo strings rather than passing them
  straight into the GitHub client.
- Don't expose internal exceptions/stack traces in API error responses;
  map them to clean error payloads (see `ERROR_HANDLING.md`).

## Security checks the tool performs on reviewed PRs

`review/security_checks.py` should flag, at minimum:
- Hardcoded secrets/credentials in the diff.
- Obvious injection risks (string-built SQL, shell commands built from
  unsanitized input).
- Missing input validation on new public-facing functions/endpoints.
- Newly introduced dependencies (flag for manual review, don't auto-judge).

These findings feed into the `## Security Concerns` section of the
generated review — see `PRD.md` for the output format.
