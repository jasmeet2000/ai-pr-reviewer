def process_findings(raw_json: dict) -> list[dict]:
    """Extract and validate findings from the synthesized JSON."""
    findings = raw_json.get("findings", [])
    if not isinstance(findings, list):
        return []
    
    valid_findings = []
    for f in findings:
        if isinstance(f, dict) and "explanation" in f:
            severity = f.get("severity", "Low")
            if severity not in ["Critical", "High", "Medium", "Low"]:
                severity = "Low"
            valid_findings.append({
                "severity": severity,
                "file": str(f.get("file", "unknown")),
                "line": f.get("line"),
                "explanation": str(f.get("explanation", "")),
                "recommendation": str(f.get("recommendation", ""))
            })
    return valid_findings
