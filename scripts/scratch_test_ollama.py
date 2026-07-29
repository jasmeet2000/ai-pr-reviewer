import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath("."))

from src.config.settings import Settings
from src.llm.ollama_client import OllamaClient
from src.llm.tool_executor import ToolExecutor
from src.llm.schemas import DEFAULT_TOOLS

def mock_get_diff(repo: str, pr_number: int) -> dict:
    """A trivial dummy tool to test round-tripping."""
    print(f"\n[Tool Execution] mock_get_diff called with repo={repo}, pr_number={pr_number}")
    return {"diff": "--- a/file.txt\n+++ b/file.txt\n+ Hello world"}

def main():
    print("Initializing Ollama Client...")
    
    # Bypass settings requirements for this test
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["GITHUB_TOKEN"] = "dummy_for_test"
    # The local machine doesn't have llama3.1, but has qwen2.5-coder:7b which supports tools
    os.environ["OLLAMA_MODEL"] = "qwen2.5-coder:7b" 
    
    settings = Settings()
    
    client = OllamaClient(settings)
    executor = ToolExecutor()
    executor.register("get_diff", mock_get_diff)

    messages = [
        {"role": "user", "content": "Can you get the diff for encode/httpx PR #1? Use the get_diff tool."}
    ]

    print(f"\n--- Sending request to Ollama ({client.model}) ---")
    
    try:
        response = client.send_message(
            messages=messages,
            tools=DEFAULT_TOOLS,
            system_prompt="You are an automated PR reviewer. You must use tools to fetch information."
        )
    except Exception as e:
        print(f"\nAPI Error: {e}")
        return

    print("\n--- Ollama Response ---")
    pprint(response)

    if response.get("tool_calls"):
        for tool_call in response["tool_calls"]:
            name = ""
            args = {}
            if "function" in tool_call:
                name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
            elif "name" in tool_call:
                name = tool_call["name"]
                args = tool_call.get("arguments", tool_call.get("input", {}))
            
            tool_result = executor.execute(name, args)
            
            print(f"\n--- Tool Result for {name} ---")
            print(tool_result)
    else:
        print("\nOllama did not invoke any tools. Content returned:")
        print(response.get("content"))

if __name__ == "__main__":
    main()
