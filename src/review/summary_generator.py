from typing import Any

def process_summary(raw_json: dict, file_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract and validate summary, regression risk, and final recommendation."""
    summary = str(raw_json.get("summary", "No summary provided."))
    
    regression_risk = raw_json.get("regression_risk", {})
    if not isinstance(regression_risk, dict):
        regression_risk = {"level": "Unknown", "reasoning": "Could not parse regression risk."}
    else:
        level = regression_risk.get("level", "Unknown")
        if level not in ["Low", "Medium", "High"]:
            level = "Unknown"
        regression_risk["level"] = level
        regression_risk["reasoning"] = str(regression_risk.get("reasoning", "No reasoning provided."))
        
    final_recommendation = str(raw_json.get("final_recommendation", "Needs Discussion"))
    if final_recommendation not in ["Approve", "Request Changes", "Needs Discussion"]:
        final_recommendation = "Needs Discussion"

    # Check for grounding failures
    grounding_failures = [r["file"] for r in file_reviews if r.get("grounding_check") == "failed"]
    if grounding_failures:
        summary = (
            f"**⚠️ GROUNDING FAILURE WARNING ⚠️**\n"
            f"Review could not be reliably grounded in fetched content. "
            f"The LLM hallucinated external paths or context while reviewing the following files: "
            f"{', '.join(grounding_failures)}. Manual review is required for these files."
        )
        final_recommendation = "Needs Discussion"

    return {
        "summary": summary,
        "regression_risk": regression_risk,
        "final_recommendation": final_recommendation
    }
