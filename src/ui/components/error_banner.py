"""Component: Dismissible Error Banner."""

import streamlit as st
from src.ui import state

def render_error_banner() -> None:
    """Render an error banner if there's an API error in the state."""
    err = state.get_api_error()
    if err:
        title = err.get("error", "Error")
        detail = err.get("detail", "An unexpected error occurred.")
        
        st.error(f"**{title}**\n\n{detail}")
        
        # Provide a way to dismiss the error
        if st.button("Dismiss"):
            state.set_api_error(None)
            st.rerun()
