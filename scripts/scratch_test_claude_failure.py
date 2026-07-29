import sys
import os

sys.path.insert(0, os.path.abspath("."))

from src.config.settings import Settings
from src.llm.claude_client import ClaudeClient
from src.llm.exceptions import ClaudeAPIError

def main():
    print("Testing ClaudeClient initialization without an API key...")
    
    # Force Claude provider, but strip the API key
    os.environ["LLM_PROVIDER"] = "claude"
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
    os.environ["GITHUB_TOKEN"] = "dummy"
    
    try:
        settings = Settings()
    except Exception as e:
        print(f"Settings successfully caught it early! Error: {e}")
        return
        
    try:
        client = ClaudeClient(settings)
        print("FAIL: ClaudeClient initialized successfully without an API key (it shouldn't have).")
    except ClaudeAPIError as e:
        print(f"SUCCESS: ClaudeClient caught the missing API key! Error: {e}")

if __name__ == "__main__":
    main()
