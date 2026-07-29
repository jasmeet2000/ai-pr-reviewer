def process_security_concerns(raw_json: dict) -> list[str]:
    """Extract and validate security concerns."""
    concerns = raw_json.get("security_concerns", [])
    if not isinstance(concerns, list):
        return []
    return [str(c) for c in concerns if c]
