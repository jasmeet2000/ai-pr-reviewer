import pytest
from src.review.summary_generator import process_summary
from src.review.diff_parser import process_findings

def test_process_summary_valid():
    raw_json = {
        "summary": "Looks good.",
        "regression_risk": {"level": "Low", "reasoning": "Minimal changes."},
        "final_recommendation": "Approve"
    }
    file_reviews = []
    
    result = process_summary(raw_json, file_reviews)
    assert result["summary"] == "Looks good."
    assert result["regression_risk"]["level"] == "Low"
    assert result["final_recommendation"] == "Approve"

def test_process_summary_invalid_recommendation():
    raw_json = {
        "summary": "Looks good.",
        "final_recommendation": "Merge Immediately!"  # Invalid
    }
    file_reviews = []
    
    result = process_summary(raw_json, file_reviews)
    assert result["final_recommendation"] == "Needs Discussion"

def test_process_summary_grounding_failure_override():
    raw_json = {
        "summary": "Looks good.",
        "final_recommendation": "Approve"
    }
    file_reviews = [
        {"file": "file1.py", "grounding_check": "passed"},
        {"file": "hallucinated.py", "grounding_check": "failed"}
    ]
    
    result = process_summary(raw_json, file_reviews)
    assert "GROUNDING FAILURE WARNING" in result["summary"]
    assert "hallucinated.py" in result["summary"]
    assert result["final_recommendation"] == "Needs Discussion"

def test_process_findings_valid():
    raw_json = {
        "findings": [
            {
                "file": "test.py",
                "line": 10,
                "severity": "High",
                "explanation": "Bug here.",
                "recommendation": "Fix it."
            }
        ]
    }
    
    findings = process_findings(raw_json)
    assert len(findings) == 1
    assert findings[0]["file"] == "test.py"
    assert findings[0]["severity"] == "High"

def test_process_findings_invalid_severity():
    raw_json = {
        "findings": [
            {
                "file": "test.py",
                "severity": "Extreme", # Invalid
                "explanation": "Bad.",
                "recommendation": "Fix."
            }
        ]
    }
    
    findings = process_findings(raw_json)
    assert len(findings) == 1
    assert findings[0]["severity"] == "Low"
