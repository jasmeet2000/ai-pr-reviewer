"""Diagnostic script: Verify API happy-path and CORS."""

import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from src.api.main import app
from src.config.settings import Settings

client = TestClient(app)

# The mock JSON that `synthesize_review` would return
MOCK_REVIEW_JSON = {
    "summary": "A mock summary",
    "findings": [
        {
            "severity": "Low",
            "file": "test.py",
            "line": 42,
            "explanation": "Mock finding",
            "recommendation": "Fix it"
        }
    ],
    "security_concerns": [],
    "code_quality_notes": [],
    "missing_error_handling": [],
    "test_cases": {
        "functional": [],
        "boundary": [],
        "negative": [],
        "regression": []
    },
    "regression_risk": {"level": "Low", "reasoning": "Mock reasoning"},
    "final_recommendation": "Approve"
}

MOCK_STATE = {
    "file_reviews": [{"file": "test.py", "review": "mock"}],
    "trace": [{"tool": "mock_tool", "duration_ms": 100}]
}


@patch("src.api.routes.review.create_github_client")
@patch("src.api.routes.review.GitHubClient")
@patch("src.api.routes.review.build_graph")
@patch("src.api.routes.review.synthesize_review")
def run_happy_path_test(mock_synth, mock_build, mock_gh_client_class, mock_gh_auth):
    print("=" * 70)
    print("TEST 1: POST /review Happy Path (Mocked core)")
    
    # Setup mocks
    mock_gh_instance = MagicMock()
    mock_gh_instance.get_pull_request_diff.return_value = MagicMock(title="Mock PR", changed_files=[MagicMock(filename="test.py")])
    mock_gh_client_class.return_value = mock_gh_instance
    
    mock_auth_instance = MagicMock()
    mock_auth_instance.get_repo.return_value.get_pull.return_value.head.sha = "mock_sha"
    mock_gh_auth.return_value = mock_auth_instance
    
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = MOCK_STATE
    mock_build.return_value = mock_graph
    
    mock_synth.return_value = MOCK_REVIEW_JSON
    
    # Run the request
    response = client.post(
        "/review", 
        json={"repo": "owner/repo", "pr_number": 1}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response matches schema successfully.")
        print(f"Summary: {data['summary']}")
        print(f"Markdown report generated: {len(data['markdown_report'])} bytes")
        print(f"Trace included: {len(data['trace'])} items")
    else:
        print(f"Body: {response.json()}")
    assert response.status_code == 200


def run_cors_test():
    print("\n" + "=" * 70)
    print("TEST 2: CORS Middleware Verification")
    
    # In .env / Settings, cors_origin is "http://localhost:8501"
    
    # Allowed origin
    res_allowed = client.options(
        "/review",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST"
        }
    )
    print(f"Allowed Origin (http://localhost:8501) OPTIONS Status: {res_allowed.status_code}")
    print(f"  Access-Control-Allow-Origin: {res_allowed.headers.get('access-control-allow-origin')}")
    assert res_allowed.status_code == 200
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:8501"
    
    # Denied origin
    res_denied = client.options(
        "/review",
        headers={
            "Origin": "http://evil-hacker.com",
            "Access-Control-Request-Method": "POST"
        }
    )
    print(f"Denied Origin (http://evil-hacker.com) OPTIONS Status: {res_denied.status_code}")
    print(f"  Access-Control-Allow-Origin: {res_denied.headers.get('access-control-allow-origin')}")
    assert res_denied.status_code == 400
    assert "Disallowed CORS origin" in res_denied.text


if __name__ == "__main__":
    run_happy_path_test()
    run_cors_test()
    print("\nAll tests completed.")
