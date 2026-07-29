def process_test_cases(raw_json: dict) -> dict[str, list[str]]:
    """Extract and validate test cases."""
    test_cases = raw_json.get("test_cases", {})
    if not isinstance(test_cases, dict):
        test_cases = {}

    def get_list(key: str) -> list[str]:
        val = test_cases.get(key, [])
        if not isinstance(val, list):
            return []
        return [str(v) for v in val if v]

    return {
        "functional": get_list("functional"),
        "boundary": get_list("boundary"),
        "negative": get_list("negative"),
        "regression": get_list("regression")
    }
