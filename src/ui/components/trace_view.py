"""Component: Tool Call Trace Viewer."""

import streamlit as st
from typing import List, Dict, Any

def render_trace_view(trace: List[Dict[str, Any]]) -> None:
    """Render the tool call trace inside a collapsed expander."""
    if not trace:
        return
        
    with st.expander(f"View Pipeline Trace ({len(trace)} steps)", expanded=False):
        for idx, step in enumerate(trace, 1):
            source = step.get("source", "native")
            tool_name = step.get("tool", "unknown_tool")
            duration = step.get("duration_ms", 0)
            
            # Format arguments safely
            args_summary = step.get("args_summary", str(step.get("args", {})))
            if len(args_summary) > 100:
                args_summary = args_summary[:97] + "..."
                
            # Distinguish fallback parsed calls
            prefix = "⚠️ [Fallback]" if source == "fallback_parsed" else "✅"
            
            st.markdown(f"**Step {idx}**: {prefix} `{tool_name}` ({duration}ms)")
            st.caption(f"**Args**: `{args_summary}`")
            st.divider()
