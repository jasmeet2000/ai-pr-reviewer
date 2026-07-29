"""Component: Download Actions."""

import streamlit as st
from typing import Dict, Any

def render_download_actions(result: Dict[str, Any]) -> None:
    """Render the download button for the markdown report."""
    if not result:
        return
        
    md_report = result.get("markdown_report", "")
    comment_url = result.get("comment_url")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if md_report:
            st.download_button(
                label="📥 Download Markdown",
                data=md_report,
                file_name="pr_review_report.md",
                mime="text/markdown"
            )
            
    with col2:
        if comment_url:
            st.success(f"✅ Posted to GitHub: [View Comment]({comment_url})")
