"""Component: Structured Review Display."""

import streamlit as st
from typing import Dict, Any, List
from src.ui.styles.theme import get_severity_color

def render_review_display(result: Dict[str, Any]) -> None:
    """Render the main review report, findings, and metadata."""
    if not result:
        return
        
    st.header("AI Pull Request Review")
    
    # Final Recommendation Badge
    rec = result.get("final_recommendation", "Unknown")
    rec_color = "green" if "Approve" in rec else "red" if "Request Changes" in rec else "orange"
    st.markdown(f"**Recommendation**: :{rec_color}[**{rec}**]")
    
    # Grounding Check Warning (If passed in the trace or via backend extension)
    summary_text = result.get("summary", "")
    has_hallucinations = "GROUNDING FAILURE WARNING" in summary_text
    if has_hallucinations:
        st.warning("⚠️ **Warning: Grounding Check Failed.** The model referenced files or lines that were not fetched during its analysis. Some findings may be hallucinated.")

    st.markdown("---")
    
    # Summary
    st.subheader("Summary")
    st.write(result.get("summary", "No summary provided."))
    
    # Findings Table/List
    findings = result.get("findings", [])
    if findings:
        st.subheader(f"Findings ({len(findings)})")
        for idx, f in enumerate(findings, 1):
            severity = f.get("severity", "Low")
            color = get_severity_color(severity)
            
            # Using Streamlit markdown colored text: :color[text]
            st.markdown(f"**{idx}.** :{color}[**{severity}**] in `{f.get('file', 'Unknown')}` (Line {f.get('line') or 'N/A'})")
            st.markdown(f"*Explanation*: {f.get('explanation', '')}")
            st.markdown(f"*Recommendation*: **{f.get('recommendation', '')}**")
            st.markdown("---")
    else:
        st.info("No specific findings reported.")
        
    # Tabs for the rest of the metadata
    tab1, tab2, tab3 = st.tabs(["Code Quality & Security", "Testing", "Regression Risk"])
    
    with tab1:
        sec = result.get("security_concerns", [])
        if sec:
            st.error("**Security Concerns:**")
            for item in sec:
                st.markdown(f"- {item}")
        else:
            st.success("No security concerns identified.")
            
        qual = result.get("code_quality_notes", [])
        err = result.get("missing_error_handling", [])
        
        if qual or err:
            st.markdown("**Code Quality Notes:**")
            for item in qual:
                st.markdown(f"- {item}")
            for item in err:
                st.markdown(f"- [Error Handling] {item}")
                
    with tab2:
        tests = result.get("test_cases", {})
        if tests:
            for category, cases in tests.items():
                if cases:
                    st.markdown(f"**{category.title()} Cases:**")
                    for case in cases:
                        st.markdown(f"- {case}")
        else:
            st.write("No test cases suggested.")
            
    with tab3:
        risk = result.get("regression_risk", {})
        level = risk.get("level", "Unknown")
        level_color = "red" if "High" in level else "orange" if "Medium" in level else "green"
        st.markdown(f"**Risk Level**: :{level_color}[{level}]")
        st.write(risk.get("reasoning", ""))
