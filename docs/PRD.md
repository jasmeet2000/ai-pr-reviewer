# PRD — AI PR Reviewer & QA Assistant

## Problem

Reviewing PRs and writing QA test cases is manual, slow, and inconsistent.
Engineering orgs increasingly want AI agents embedded in the SDLC to reduce
that toil — this is the exact class of tool the target role builds.

## Goal

A working agentic prototype that, given a GitHub PR, produces a structured
review: bugs, security issues, style problems, missing error handling, a
plain-English summary, a QA test checklist, a regression risk estimate, and
a final recommendation — optionally posted back to GitHub as a comment.

Accessible through three interfaces sharing one agent core: a Streamlit UI
(with live tool-call visualization, for interview demos), a CLI (for
scripted/local runs), and a GitHub Action (for real CI/CD use).

## Non-goals

- Not a production SaaS product. No multi-tenant auth, billing, or
  hosting-at-scale. The API has no auth in v1 — stated explicitly as a
  known gap, not hidden.
- Not trying to replace human review — augment it.
- No fine-tuning or custom model training.
- No persistent database — review results are ephemeral per-request
  (returned to the caller, optionally downloaded); no history/dashboard of
  past reviews in v1.

## Users

- Software engineers opening PRs (get faster, more consistent feedback).
- QA engineers (get a generated test checklist instead of starting cold).
- The interviewer, evaluating this as a portfolio project.

## Success criteria

- Runs end-to-end against a real public GitHub PR.
- Demonstrably uses tool calling — the LLM chooses when to fetch a diff,
  fetch file contents, or produce the final review, rather than a
  hardcoded sequence.
- Code and README are good enough to walk through in an interview and
  explain every architectural decision confidently.

## Out of scope for v1 (mention as "future improvements" in README)

- Multi-PR batch review.
- Learning from human review feedback (RLHF-style loop).
- Repo-wide RAG over the full codebase (mentioned as a natural extension).
- Slack/Teams notifications.
