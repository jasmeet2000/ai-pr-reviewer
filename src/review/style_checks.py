def process_style_notes(raw_json: dict) -> dict[str, list[str]]:
    """Extract and validate style notes and missing error handling."""
    code_quality_notes = raw_json.get("code_quality_notes", [])
    if not isinstance(code_quality_notes, list):
        code_quality_notes = []
        
    missing_error_handling = raw_json.get("missing_error_handling", [])
    if not isinstance(missing_error_handling, list):
        missing_error_handling = []

    return {
        "code_quality_notes": [str(c) for c in code_quality_notes if c],
        "missing_error_handling": [str(c) for c in missing_error_handling if c]
    }
