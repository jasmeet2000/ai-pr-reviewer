import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath("."))

from src.config.settings import Settings
from src.llm.claude_client import ClaudeClient
from src.llm.tool_executor import ToolExecutor
from src.llm.schemas import DEFAULT_TOOLS

def mock_get_diff(repo: str, pr_number: int) -> dict:
    """A trivial dummy tool to test round-tripping."""
    print(f"\n[Tool Execution] get_diff called with repo={repo}, pr_number={pr_number}")
    return {"diff": "--- a/file.txt\n+++ b/file.txt\n+ Hello world"}

def main():
    print("Initializing Claude Client...")
    
    # We load settings, which requires ANTHROPIC_API_KEY for Claude
    try:
        settings = Settings()
    except Exception as e:
        print(f"Failed to load settings (Missing API key?): {e}")
        print("\nPlease run this script with GITHUB_TOKEN and ANTHROPIC_API_KEY set.")
        return

    client = ClaudeClient(settings)
    executor = ToolExecutor()
    executor.register("get_diff", mock_get_diff)

    messages = [
        {"role": "user", "content": "Can you get the diff for encode/httpx PR #1?"}
    ]

    print("\n--- Sending request to Claude ---")
    print(f"Messages: {json.dumps(messages, indent=2)}")
    
    # 1. Send the message and the tool schemas to Claude
    response = client.send_message(
        messages=messages,
        tools=DEFAULT_TOOLS,
        system_prompt="You are a PR reviewer. Use tools to fetch information."
    )

    print("\n--- Claude Response ---")
    pprint(response)

    # 2. Extract tool calls and execute them
    if response["tool_calls"]:
        for tool_call in response["tool_calls"]:
            name = tool_call["name"]
            args = tool_call["input"]
            
            # Execute the tool via our ToolExecutor
            tool_result = executor.execute(name, args)
            
            print(f"\n--- Tool Result for {name} ---")
            print(tool_result)
            
            # 3. Normally we would append this result to the messages and send back to Claude
            # messages.append({"role": "assistant", "content": response["content"], "tool_calls": response["tool_calls"]}) # (Simplified)
            # messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_call["id"], "content": tool_result}]})
    else:
        print("\nClaude did not invoke any tools.")

if __name__ == "__main__":
    main()
