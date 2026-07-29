import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.github.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubClientError
)
from src.agent.exceptions import AgentLoopLimitExceeded
from src.llm.exceptions import ClaudeAPIError, OllamaAPIError, ToolExecutionError

client = TestClient(app)

@pytest.fixture
def base_payload():
    return {
        "repo": "test/test",
        "pr_number": 1,
        "provider": "mock"
    }

def test_github_auth_error(base_payload):
    with patch("src.api.routes.review.create_github_client") as mock_gh:
        mock_gh.side_effect = GitHubAuthError("Bad token")
        response = client.post("/review", json=base_payload)
        
        assert response.status_code == 401
        assert response.json()["error"] == "GitHub Authentication Failed"

def test_github_not_found_error(base_payload):
    with patch("src.api.routes.review.create_github_client") as mock_gh:
        mock_gh.side_effect = GitHubNotFoundError("Repo not found")
        response = client.post("/review", json=base_payload)
        
        assert response.status_code == 404
        assert response.json()["error"] == "Not Found"

def test_github_rate_limit_error(base_payload):
    with patch("src.api.routes.review.create_github_client") as mock_gh:
        mock_gh.side_effect = GitHubRateLimitError("Rate limited")
        response = client.post("/review", json=base_payload)
        
        assert response.status_code == 429
        assert response.json()["error"] == "Rate Limit Exceeded"

def test_agent_loop_limit_exceeded(base_payload):
    with patch("src.api.routes.review.build_graph") as mock_build:
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = AgentLoopLimitExceeded("Too many loops")
        mock_build.return_value = mock_graph
        
        # We also need to mock create_github_client so it doesn't try to connect
        with patch("src.api.routes.review.create_github_client"):
            with patch("src.api.routes.review.GitHubClient"):
                response = client.post("/review", json=base_payload)
                
        assert response.status_code == 500
        assert response.json()["error"] == "Review Generation Failed"

def test_claude_api_error(base_payload):
    with patch("src.api.routes.review._create_llm_client") as mock_llm:
        mock_llm.side_effect = ClaudeAPIError("Anthropic down")
        
        with patch("src.api.routes.review.create_github_client"):
            with patch("src.api.routes.review.GitHubClient"):
                response = client.post("/review", json=base_payload)
                
        assert response.status_code == 502
        assert response.json()["error"] == "LLM Provider Error"

def test_ollama_api_error(base_payload):
    with patch("src.api.routes.review._create_llm_client") as mock_llm:
        mock_llm.side_effect = OllamaAPIError("Ollama down")
        
        with patch("src.api.routes.review.create_github_client"):
            with patch("src.api.routes.review.GitHubClient"):
                response = client.post("/review", json=base_payload)
                
        assert response.status_code == 502
        assert response.json()["error"] == "LLM Provider Error"

def test_tool_execution_error(base_payload):
    # For ToolExecutionError, it's typically caught by the agent loop or bubble up.
    # We can mock tool execution to throw it and let it bubble up, or just throw it directly.
    # It inherits from Exception and is not explicitly mapped in exception handlers, 
    # so it should return a 500 Internal Server Error.
    with patch("src.api.routes.review.build_graph") as mock_build:
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = ToolExecutionError("Tool crashed")
        mock_build.return_value = mock_graph
        
        with patch("src.api.routes.review.create_github_client"):
            with patch("src.api.routes.review.GitHubClient"):
                response = client.post("/review", json=base_payload)
                
        assert response.status_code == 502
        assert response.json()["error"] == "LLM Provider Error"
