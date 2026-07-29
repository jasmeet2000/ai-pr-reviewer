"""Thin HTTP client for communicating with the FastAPI backend."""

import httpx
from typing import Any, Dict, Tuple

# Hardcoded for the prototype; in production this would be an env var
API_BASE_URL = "http://localhost:8000"


def get_health() -> bool:
    """Check if the backend is alive."""
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False


def submit_review(
    repo: str, pr_number: int, provider: str, post_to_github: bool = False
) -> Tuple[Dict[str, Any] | None, Dict[str, str] | None]:
    """Submit a PR for review.
    
    Returns:
        Tuple of (review_response_dict, error_dict)
        Where error_dict has 'error' and 'detail' keys per ERROR_HANDLING.md.
    """
    payload = {
        "repo": repo,
        "pr_number": pr_number,
        "provider": provider,
        "post_to_github": post_to_github,
    }
    
    # We use a long timeout because the API is fully synchronous and local LLMs can take 3-6+ minutes.
    try:
        response = httpx.post(f"{API_BASE_URL}/review", json=payload, timeout=600.0)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            # Safely parse the {error, detail} shape per ERROR_HANDLING.md
            try:
                err_data = response.json()
                if "error" in err_data and "detail" in err_data:
                    return None, err_data
                return None, {"error": f"HTTP {response.status_code}", "detail": response.text}
            except Exception:
                return None, {"error": f"HTTP {response.status_code}", "detail": response.text}
                
    except httpx.TimeoutException:
        return None, {
            "error": "Timeout",
            "detail": "The review took too long to complete. The backend might still be processing it."
        }
    except httpx.RequestError as e:
        return None, {
            "error": "Connection Error",
            "detail": f"Could not connect to the backend API: {str(e)}"
        }
