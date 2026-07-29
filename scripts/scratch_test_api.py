"""Diagnostic script: Verify FastAPI backend (Phase 9) using TestClient."""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("TEST 1: GET /health")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
    assert response.status_code == 200

    print("=" * 70)
    print("TEST 2: POST /review with invalid repo (404)")
    response = client.post(
        "/review", 
        json={"repo": "nonexistent/fake-repo-xyz", "pr_number": 1, "provider": "ollama"}
    )
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
    assert response.status_code == 404
    assert response.json()["error"] == "Not Found"

    print("=" * 70)
    print("TEST 3: POST /review with missing field (422 Pydantic Validation)")
    response = client.post(
        "/review", 
        json={"pr_number": 1} # Missing repo
    )
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
    assert response.status_code == 422

    print("=" * 70)
    print("TEST 4: POST /review with invalid repo format (422 Pydantic Validation)")
    response = client.post(
        "/review", 
        json={"repo": "invalid_format", "pr_number": 1}
    )
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
    assert response.status_code == 422

    print("\nAll targeted API tests passed!")

if __name__ == "__main__":
    run_tests()
