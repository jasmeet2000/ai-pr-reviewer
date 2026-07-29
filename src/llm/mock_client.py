from typing import List, Dict, Any, Optional
import json

from src.llm.base_client import LLMClient

class MockLLMClient(LLMClient):
    """
    MockLLMClient: WIRING VERIFICATION ONLY
    
    Used only to prove FastAPI route -> agent graph -> UI rendering works when the LLM layer 
    responds correctly, given the sandbox environment lacks Ollama access.
    
    It does NOT re-verify agent/model behavior.
    """
    def __init__(self):
        self.call_count = 0
        
    def send_message(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        
        self.call_count += 1
        
        # Planner Node: Return list_files
        if any("You are a senior engineer planning" in msg.get("content", "") for msg in messages) or (system_prompt and "planning" in system_prompt):
            return {
                "role": "assistant",
                "content": "docs/en/docs/tutorial/security/first-steps.md"
            }

        # Review Node: Return review JSON
        if any("expert code reviewer" in msg.get("content", "") for msg in messages) or (system_prompt and "expert code reviewer" in system_prompt):
            # We use messages length or something to detect if it's the first call vs second call.
            # If it's the first call, the only assistant message is missing or it's just the user prompt.
            if len(messages) == 1:
                # Simulate a grounding failure tool call to trigger the warning
                return {
                    "role": "assistant",
                    "content": "Checking a hallucinated file.",
                    "tool_calls": [
                        {
                            "id": "call_mock_3",
                            "type": "function",
                            "function": {
                                "name": "get_file_contents",
                                "arguments": {"path": "does_not_exist.py"}
                            }
                        }
                    ]
                }
            
            return {
                "role": "assistant",
                "content": "This is a mock raw review note for the file. I am also reviewing hallucinated_file.py which I didn't fetch."
            }
            
        # Synthesizer Node: Return final review JSON
        if any("PR review orchestrator" in msg.get("content", "") for msg in messages) or (system_prompt and "orchestrator" in system_prompt):
            review_json = {
                "findings": [
                    {
                        "file": "hallucinated_file.py",
                        "line": 42,
                        "severity": "Low",
                        "explanation": "Typo in the documentation.",
                        "recommendation": "Fix the typo."
                    }
                ],
                "summary": "This is a mock wiring verification. The code looks fine."
            }
            return {
                "role": "assistant",
                "content": json.dumps(review_json)
            }
            
        # Fallback
        return {
            "role": "assistant",
            "content": "{}"
        }
