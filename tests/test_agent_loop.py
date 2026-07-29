import pytest
from src.agent.review_agent import review_node
from src.agent.exceptions import AgentLoopLimitExceeded
from src.config.settings import Settings
from src.llm.tool_executor import ToolExecutor
from src.llm.base_client import LLMClient

class EndlessToolCallLLM(LLMClient):
    def send_message(self, messages, tools=None, system_prompt=None):
        # Always return a tool call
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "name": "get_file_contents",
                    "arguments": {"path": "file1.txt", "repo": "test"}
                }
            ]
        }

def test_agent_loop_limit_exceeded():
    """
    Test that if the LLM endlessly asks for tool calls without providing a final answer,
    the agent loop halts at Settings.max_tool_calls and raises AgentLoopLimitExceeded, 
    rather than looping infinitely.
    """
    settings = Settings(max_tool_calls=3)
    llm = EndlessToolCallLLM()
    
    executor = ToolExecutor()
    executor.register("get_file_contents", lambda repo, path: "dummy content")
    
    state = {
        "repo": "test/test",
        "pr_number": 1,
        "files_to_review": ["file1.txt"],
    }
    
    # It should raise the limit exceeded exception
    with pytest.raises(AgentLoopLimitExceeded) as exc_info:
        review_node(state, llm, executor, settings)
        
    assert "exceeded MAX_TOOL_CALLS (3)" in str(exc_info.value)
