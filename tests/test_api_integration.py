import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider" in data

def test_review_endpoint_success_and_hallucination_regression():
    """
    Tests the main review endpoint using the mock LLM client.
    Because MockLLMClient intentionally injects a hallucinated finding 
    ('hallucinated_file.py') that it never fetched, this test also serves 
    as the regression test for the hallucination bypass bug.
    """
    payload = {
        "repo": "tiangolo/fastapi",
        "pr_number": 16060,
        "provider": "mock"
    }
    
    response = client.post("/review", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    
    # 1. Basic Structure
    assert "summary" in data
    assert "findings" in data
    
    # 2. Hallucination Regression Assertions
    # Top-level flag should correctly reflect failure
    assert data["grounding_check"] is False
    
    # Findings should have been filtered and replaced with an Info placeholder
    findings = data["findings"]
    assert len(findings) == 1
    info_finding = findings[0]
    
    assert info_finding["severity"] == "Info"
    assert info_finding["file"] == "hallucinated_file.py"
    assert "Manual review required" in info_finding["recommendation"]

def test_cors_allowed_origin():
    """
    Tests that a request with an allowed Origin header succeeds.
    Since CORS is enabled in the test env for '*', everything should pass,
    but let's verify the CORS headers are returned.
    """
    headers = {
        "Origin": "http://localhost:8501",
        "Access-Control-Request-Method": "POST"
    }
    response = client.options("/review", headers=headers)
    assert response.status_code == 200
    # Depending on settings, it might be '*' or the specific origin
    assert "access-control-allow-origin" in response.headers
