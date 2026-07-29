"""
Quick test: exercises both fixes in review_generator without waiting for Ollama.

1. Grounding-failed file findings get replaced with a placeholder entry.
2. The "recommendation" field semantics are correct in the placeholder.

We mock the LLM synthesis response to simulate a successful single-call.
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from src.review.review_generator import synthesize_review
from src.review.report_renderer import render_markdown

# ── Simulate final_state with a grounding-failed file review ──
# This is exactly what review_agent.py puts in state["file_reviews"]
mock_state = {
    "file_reviews": [
        {
            "file": "tests/test_path.py",
            "review": "Some hallucinated review text about http3 and encode/httpx.",
            "grounding_check": "failed",
        }
    ],
    "trace": [],
    "errors": [],
}

# ── Mock LLM client that returns a realistic-looking synthesis response ──
class MockLLM:
    """Returns a pre-baked synthesis JSON as if the model responded."""

    def send_message(self, messages, system_prompt=None):
        # This simulates what the model WOULD return — including the
        # hallucinated findings that should be stripped by fix #1.
        raw = {
            "summary": "The PR adds RequestDataStream and AsyncRequestDataStream classes.",
            "findings": [
                {
                    "severity": "Low",
                    "file": "tests/test_path.py",
                    "line": None,
                    "explanation": "New classes for stream handling are well-documented.",
                    "recommendation": "Approve"   # <-- fix #2: this would be wrong
                },
                {
                    "severity": "Medium",
                    "file": "tests/test_path.py",
                    "line": 42,
                    "explanation": "Potential issue with async iterator cleanup.",
                    "recommendation": "Add __aexit__ to ensure streams are closed."
                }
            ],
            "security_concerns": [],
            "code_quality_notes": ["Consider adding type annotations."],
            "missing_error_handling": [],
            "test_cases": {"functional": [], "boundary": [], "negative": [], "regression": []},
            "regression_risk": {"level": "Low", "reasoning": "Focused feature addition."},
            "final_recommendation": "Approve"
        }
        return {"content": json.dumps(raw)}


print("=" * 60)
print("Running Phase 7 fix verification (mock LLM)")
print("=" * 60)

result = synthesize_review(mock_state, MockLLM())

print("\n--- Structured JSON ---")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Assertions
print("\n--- Verification ---")

# Fix 1: No hallucinated findings for the grounding-failed file
real_findings = [f for f in result["findings"] if f["file"] == "tests/test_path.py"]
assert len(real_findings) == 1, f"Expected 1 placeholder finding, got {len(real_findings)}"
assert real_findings[0]["severity"] == "Info", f"Expected 'Info' severity, got {real_findings[0]['severity']}"
assert "grounded" in real_findings[0]["explanation"].lower(), "Placeholder should mention grounding"
assert "Manual review" in real_findings[0]["recommendation"], "Placeholder should say manual review"
print("✓ Fix 1: Grounding-failed findings replaced with single placeholder")

# Fix 1 continued: final_recommendation forced to Needs Discussion
assert result["final_recommendation"] == "Needs Discussion", \
    f"Expected 'Needs Discussion', got {result['final_recommendation']}"
print("✓ Fix 1: final_recommendation forced to 'Needs Discussion'")

# Summary has grounding warning
assert "GROUNDING FAILURE WARNING" in result["summary"], "Summary should contain warning"
print("✓ Fix 1: Summary contains grounding failure warning")

# Now render markdown
md = render_markdown(result)
print("\n--- Rendered Markdown ---")
print(md)

with open("scratch_review_report.md", "w", encoding="utf-8") as f:
    f.write(md)
with open("scratch_review_report.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("\n✓ All checks passed. Files written to scratch_review_report.md and .json")
