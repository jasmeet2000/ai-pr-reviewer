"""review — Review generation and rendering package.

Exposes the high-level orchestration functions used by the CLI and API.
"""

from src.review.review_generator import synthesize_review
from src.review.report_renderer import render_markdown, render_html

__all__ = [
    "synthesize_review",
    "render_markdown",
    "render_html",
]
