"""Typed wrappers for Streamlit's session_state.

Prevents raw `st.session_state["key"]` access scattered across files,
providing a single source of truth for the shape of the app's state.
"""

import streamlit as st
from typing import Any, Dict


def init_state() -> None:
    """Initialize default state values if they don't exist."""
    if "review_result" not in st.session_state:
        st.session_state.review_result = None
    if "api_error" not in st.session_state:
        st.session_state.api_error = None
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False


def set_review_result(result: Dict[str, Any] | None) -> None:
    st.session_state.review_result = result


def get_review_result() -> Dict[str, Any] | None:
    return st.session_state.get("review_result")


def set_api_error(error: Dict[str, str] | None) -> None:
    """Expects dict with 'error' and 'detail' keys per ERROR_HANDLING.md."""
    st.session_state.api_error = error


def get_api_error() -> Dict[str, str] | None:
    return st.session_state.get("api_error")


def set_loading(loading: bool) -> None:
    st.session_state.is_loading = loading


def is_loading() -> bool:
    return st.session_state.get("is_loading", False)
