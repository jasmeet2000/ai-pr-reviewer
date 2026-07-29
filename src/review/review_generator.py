import json
import time
from typing import Any
from src.agent.state import PRReviewState
from src.llm.base_client import LLMClient
from src.utils.logger import get_logger

from src.review.diff_parser import process_findings
from src.review.summary_generator import process_summary
from src.review.test_generator import process_test_cases
from src.review.security_checks import process_security_concerns
from src.review.style_checks import process_style_notes

logger = get_logger(__name__)

def synthesize_review(state: PRReviewState, llm: LLMClient) -> dict[str, Any]:
    """
    Takes the raw per-file reviews from the state, plus the trace, and uses
    a single LLM call to synthesize the final structured output JSON.
    Delegates parsing and validation of the JSON to single-purpose modules.
    """
    file_reviews = state.get("file_reviews", [])
    if not file_reviews:
        logger.warning("No file reviews to synthesize.")
        return _fallback_review()

    # Build the combined text context
    context = ""
    for r in file_reviews:
        context += f"--- Review for {r['file']} ---\n{r['review']}\n\n"

    messages = [
        {
            "role": "user",
            "content": (
                "Here are the per-file reviews for a Pull Request. "
                "Synthesize them into a single, comprehensive structured JSON report.\n\n"
                f"{context}\n\n"
                "Return ONLY valid JSON matching the exact schema requested in the system prompt."
            )
        }
    ]

    system_prompt = (
        "You are an expert PR review orchestrator. Your job is to take raw per-file review notes "
        "and synthesize them into a single JSON object. DO NOT wrap the JSON in markdown code blocks. "
        "Return raw, valid JSON only.\n\n"
        "IMPORTANT: Each finding's 'recommendation' field must be a concrete, actionable fix "
        "suggestion (e.g. 'add a null check before accessing user.name', 'wrap this call in a "
        "try/except block'). It is NOT an Approve/Reject verdict — the overall verdict belongs "
        "ONLY in the top-level 'final_recommendation' field.\n\n"
        "Schema:\n"
        "{\n"
        '  "summary": "High level summary",\n'
        '  "findings": [{"severity": "Critical|High|Medium|Low", "file": "string", "line": "int or null", "explanation": "string", "recommendation": "actionable fix suggestion"}],\n'
        '  "security_concerns": ["string array"],\n'
        '  "code_quality_notes": ["string array"],\n'
        '  "missing_error_handling": ["string array"],\n'
        '  "test_cases": {"functional": ["string array"], "boundary": ["string array"], "negative": ["string array"], "regression": ["string array"]},\n'
        '  "regression_risk": {"level": "Low|Medium|High", "reasoning": "string"},\n'
        '  "final_recommendation": "Approve|Request Changes|Needs Discussion"\n'
        "}"
    )

    logger.info("Starting LLM synthesis of full structured review (Single Call).")
    start_time = time.time()
    try:
        response = llm.send_message(messages=messages, system_prompt=system_prompt)
        content = response.get("content", "").strip()
        
        # Clean potential markdown wrapping
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        raw_json = json.loads(content.strip())
        logger.info(f"LLM synthesis completed in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Failed to synthesize review with LLM: {e}")
        logger.info(f"LLM synthesis failed after {time.time() - start_time:.2f} seconds.")
        return _fallback_review()

    # Delegate to small single-purpose modules to process their slice
    structured_review = {}
    structured_review.update(process_summary(raw_json, file_reviews))
    structured_review["findings"] = process_findings(raw_json)
    structured_review["test_cases"] = process_test_cases(raw_json)
    structured_review["security_concerns"] = process_security_concerns(raw_json)
    structured_review.update(process_style_notes(raw_json))

    # Fix 1: Validate every finding against the set of all fetched paths.
    # Replace findings for hallucinated files with an Info placeholder.
    all_fetched_paths = set()
    for r in file_reviews:
        all_fetched_paths.update(r.get("fetched_paths", []))
        
    # Also include files that the planner initially selected, as they are implicitly "in the PR"
    all_fetched_paths.update(state.get("files_to_review", []))

    kept_findings = []
    hallucinated_files = set()
    
    for finding in structured_review["findings"]:
        f_path = finding.get("file")
        if not f_path:
            continue
            
        # Check if the file path is in the known fetched/requested paths
        is_grounded = any(f_path in p or p in f_path for p in all_fetched_paths)
        
        if is_grounded:
            kept_findings.append(finding)
        else:
            hallucinated_files.add(f_path)

    # Add the Info placeholder for any hallucinated files that were stripped
    for h_file in sorted(hallucinated_files):
        kept_findings.append({
            "severity": "Info",
            "file": h_file,
            "line": None,
            "explanation": (
                "Review could not be reliably grounded in fetched "
                "content — the LLM hallucinated references to files "
                "or repositories not present in this PR. "
                "See summary warning for details."
            ),
            "recommendation": "Manual review required for this file."
        })
        
    structured_review["findings"] = kept_findings

    # Set overall grounding_check flag: False (failed) if either check caught something
    has_regex_failures = any(r.get("grounding_check") == "failed" for r in file_reviews)
    structured_review["grounding_check"] = not (has_regex_failures or bool(hallucinated_files))

    return structured_review

def _fallback_review() -> dict[str, Any]:
    return {
        "summary": "Review synthesis failed or no files were reviewed.",
        "findings": [],
        "security_concerns": [],
        "code_quality_notes": [],
        "missing_error_handling": [],
        "test_cases": {"functional": [], "boundary": [], "negative": [], "regression": []},
        "regression_risk": {"level": "Unknown", "reasoning": "Synthesis failed."},
        "final_recommendation": "Needs Discussion"
    }
