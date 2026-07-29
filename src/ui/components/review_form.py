"""Component: PR Review Submission Form."""

import streamlit as st
from src.ui import api_client
from src.ui import state

def render_review_form() -> None:
    """Render the sidebar form to submit a PR for review."""
    with st.sidebar:
        st.header("Configure Review")
        
        with st.form("review_form"):
            repo = st.text_input(
                "Repository", 
                placeholder="e.g. fastapi/fastapi", 
                help="Must be in owner/name format."
            )
            pr_number = st.number_input(
                "PR Number", 
                min_value=1, 
                step=1, 
                value=1
            )
            provider = st.selectbox(
                "LLM Provider", 
                options=["claude", "ollama", "mock"],
                index=2
            )
            post_to_github = st.checkbox(
                "Post to GitHub", 
                value=False,
                help="Automatically post the completed review as a comment on the PR."
            )
            
            submitted = st.form_submit_button("Start Review")
            
            if submitted:
                if not repo or "/" not in repo:
                    state.set_api_error({"error": "Validation Error", "detail": "Repository must be in 'owner/name' format."})
                    return
                
                # Clear previous state
                state.set_review_result(None)
                state.set_api_error(None)
                
                # We can't use set_loading() effectively across a synchronous blocking call in Streamlit
                # without rerunning. Instead, we use an honest st.spinner right here.
                
                spinner_msg = (
                    "Analyzing PR... (This can take 3-6+ minutes with local Ollama models. "
                    "Pipeline: Fetching PR → Reviewing files → Synthesizing)"
                )
                
                with st.spinner(spinner_msg):
                    result, error = api_client.submit_review(
                        repo=repo.strip(),
                        pr_number=pr_number,
                        provider=provider,
                        post_to_github=post_to_github
                    )
                    
                    if error:
                        state.set_api_error(error)
                    else:
                        state.set_review_result(result)
                        
                    # Rerun to update the main UI area with the new state
                    st.rerun()
