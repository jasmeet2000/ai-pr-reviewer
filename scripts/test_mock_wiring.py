import httpx
import json

def test_mock_wiring():
    print("Testing MockLLMClient wiring via FastAPI...")
    url = "http://localhost:8000/review"
    payload = {
        "repo": "tiangolo/fastapi",
        "pr_number": 16060,
        "provider": "mock"
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        print("\n=== SUCCESS ===")
        print(f"Grounding Check Failed? {not data.get('grounding_check', True)}")
        print(f"Findings Count: {len(data.get('findings', []))}")
        print("\nTrace:")
        for t in data.get("trace", []):
            print(f"  - [{t['source']}] {t['tool']} : {t.get('args_summary')}")
        print("\nFirst Finding:")
        if data.get("findings"):
            print(json.dumps(data["findings"][0], indent=2))
    except Exception as e:
        print(f"\n=== ERROR ===\n{e}")

if __name__ == "__main__":
    test_mock_wiring()
