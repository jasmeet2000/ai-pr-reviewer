"""Shared styles and color constants for the Streamlit UI."""

from typing import Dict

# Severity color mapping (per DESIGN.md)
SEVERITY_COLORS: Dict[str, str] = {
    "Critical": "red",
    "High": "orange",
    "Medium": "yellow",
    "Low": "gray"
}

def get_severity_color(severity: str) -> str:
    """Return the color for a given severity, defaulting to gray."""
    # Normalize to title case just in case
    sev = severity.strip().title()
    return SEVERITY_COLORS.get(sev, "gray")
