"""Diagnostic script: Verify UI rendering with Mock Data."""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

import streamlit as st
from src.ui import state
from src.ui import app

# The mock JSON that API would return
MOCK_REVIEW_JSON = {
    "summary": "This is a mock summary demonstrating the UI components.",
    "findings": [
        {
            "severity": "Critical",
            "file": "auth.py",
            "line": 15,
            "explanation": "Hardcoded secret found.",
            "recommendation": "Use environment variables."
        },
        {
            "severity": "High",
            "file": "database.py",
            "line": None,
            "explanation": "Missing index on frequently queried column.",
            "recommendation": "Add an index to improve performance."
        },
        {
            "severity": "Low",
            "file": "utils.py",
            "line": 42,
            "explanation": "Typo in variable name.",
            "recommendation": "Rename `usr` to `user`."
        }
    ],
    "security_concerns": ["Hardcoded secrets in auth.py"],
    "code_quality_notes": ["Inconsistent naming conventions"],
    "missing_error_handling": ["Database connection not wrapped in try/except"],
    "test_cases": {
        "functional": ["Test successful login", "Test failed login"],
        "boundary": [],
        "negative": ["Test SQL injection in username field"],
        "regression": []
    },
    "regression_risk": {"level": "Medium", "reasoning": "Auth changes always carry risk."},
    "final_recommendation": "Request Changes",
    "markdown_report": "# Mock Report\nThis is a mock report.",
    "trace": [
        {"source": "native", "tool": "get_diff", "args_summary": "{'repo': 'test/test', 'pr_number': 1}", "duration_ms": 150},
        {"source": "fallback_parsed", "tool": "get_file_contents", "args_summary": "hallucinated_file.py", "duration_ms": 1050}
    ],
    "comment_url": "https://github.com/owner/repo/pull/1#issuecomment-123456"
}

MOCK_REVIEW_JSON_CLEAN = MOCK_REVIEW_JSON.copy()
MOCK_REVIEW_JSON_CLEAN["trace"] = [
    {"source": "native", "tool": "get_diff", "args_summary": "{'repo': 'test/test', 'pr_number': 1}", "duration_ms": 150}
]

st.set_page_config(page_title="Mock UI Test", layout="wide")

st.sidebar.warning("MOCK UI MODE: Data is hardcoded.")
if st.sidebar.button("Load Mock Success State (Grounding Failure)"):
    state.init_state()
    state.set_review_result(MOCK_REVIEW_JSON)
    state.set_api_error(None)
    st.rerun()

if st.sidebar.button("Load Mock Success State (Clean Grounding)"):
    state.init_state()
    state.set_review_result(MOCK_REVIEW_JSON_CLEAN)
    state.set_api_error(None)
    st.rerun()

if st.sidebar.button("Load Mock Error State (404)"):
    state.init_state()
    state.set_review_result(None)
    state.set_api_error({"error": "Not Found", "detail": "Repository 'owner/repo' not found. Check the owner/name format and that you have access."})
    st.rerun()

# Run the normal app layout (skipping its page config)
state.init_state()

st.title("🤖 AI Pull Request Reviewer (Mocked)")
from src.ui.components.review_form import render_review_form
from src.ui.components.error_banner import render_error_banner
from src.ui.components.trace_view import render_trace_view
from src.ui.components.review_display import render_review_display
from src.ui.components.download_actions import render_download_actions

render_review_form()
render_error_banner()
result = state.get_review_result()
if result:
    render_download_actions(result)
    render_trace_view(result.get("trace", []))
    st.divider()
    render_review_display(result)
else:
    if not state.get_api_error():
        st.info("👈 Configure and submit a PR review from the sidebar.")
