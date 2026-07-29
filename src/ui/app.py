"""Streamlit App Entry Point.

Run with: `streamlit run src/ui/app.py`
"""

import os
import sys

# Ensure the src module is importable when running via streamlit
sys.path.insert(0, os.path.abspath("."))

import streamlit as st

from src.ui import state
from src.ui.components.review_form import render_review_form
from src.ui.components.error_banner import render_error_banner
from src.ui.components.trace_view import render_trace_view
from src.ui.components.review_display import render_review_display
from src.ui.components.download_actions import render_download_actions

st.set_page_config(
    page_title="AI PR Reviewer",
    page_icon="🤖",
    layout="wide"
)

def main():
    # 1. Initialize State
    state.init_state()
    
    # 2. Main Title
    st.title("🤖 AI Pull Request Reviewer")
    st.caption("Automated code review, security checks, and test generation using LLMs.")
    
    # 3. Sidebar Form
    render_review_form()
    
    # 4. Error Banner (if any)
    render_error_banner()
    
    # 5. Main Content Area
    result = state.get_review_result()
    
    if result:
        # Render Actions (Download, GitHub Link)
        render_download_actions(result)
        
        # Render the Trace Expander
        render_trace_view(result.get("trace", []))
        
        st.divider()
        
        # Render the Core Review
        render_review_display(result)
    else:
        # Empty state
        if not state.get_api_error():
            st.info("👈 Configure and submit a PR review from the sidebar.")

if __name__ == "__main__":
    main()
