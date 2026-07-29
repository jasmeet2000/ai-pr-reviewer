import pytest
import json
from unittest.mock import patch, MagicMock
from src.llm.ollama_client import OllamaClient
from src.config.settings import Settings

@pytest.fixture
def ollama_client():
    settings = Settings(ollama_host="http://localhost:11434", ollama_model="test-model")
    return OllamaClient(settings)

def test_ollama_schema_mapping(ollama_client):
    """
    Tests that Anthropic-style 'input_schema' is mapped correctly to 'parameters'
    in the payload sent to Ollama, fixing the mapping bug.
    """
    tools = [
        {
            "name": "my_tool",
            "description": "Does something",
            "input_schema": {
                "type": "object",
                "properties": {"arg1": {"type": "string"}}
            }
        }
    ]
    
    with patch.object(ollama_client.client, "post") as mock_post:
        # Provide a valid fake response
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "done"}}
        mock_post.return_value = mock_response
        
        ollama_client.send_message(messages=[{"role": "user", "content": "hi"}], tools=tools)
        
        # Verify payload structure
        call_kwargs = mock_post.call_args.kwargs
        payload = call_kwargs["json"]
        
        assert "tools" in payload
        assert len(payload["tools"]) == 1
        
        tool_payload = payload["tools"][0]
        assert tool_payload["type"] == "function"
        
        # This is the crucial fix: the key MUST be 'parameters', not 'input_schema'
        assert "parameters" in tool_payload["function"]
        assert tool_payload["function"]["parameters"] == tools[0]["input_schema"]
        assert "input_schema" not in tool_payload["function"]

def test_ollama_fallback_parser_success(ollama_client):
    """
    Tests the fallback parser logic when the model outputs a tool call as a JSON string
    in the content block, rather than using the native tool_calls array.
    """
    tools = [
        {
            "name": "get_file",
            "input_schema": {
                "type": "object",
                "required": ["path"]
            }
        }
    ]
    
    fake_json_content = json.dumps({
        "name": "get_file",
        "arguments": {"path": "src/main.py"}
    })
    
    # Wrap in markdown just to test that stripping works too
    fake_content = f"```json\n{fake_json_content}\n```"
    
    with patch.object(ollama_client.client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": fake_content,
                "tool_calls": []  # Native tool calls empty
            }
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.send_message(messages=[{"role": "user", "content": "fetch"}], tools=tools)
        
        assert len(result["tool_calls"]) == 1
        tc = result["tool_calls"][0]
        assert tc["function"]["name"] == "get_file"
        assert tc["function"]["arguments"]["path"] == "src/main.py"
        assert result["source"] == "fallback_parsed"

def test_ollama_fallback_parser_missing_required_keys(ollama_client):
    """
    Tests that the fallback parser rejects the tool call and falls back to plain text
    if the parsed JSON is missing required arguments.
    """
    tools = [
        {
            "name": "get_file",
            "input_schema": {
                "type": "object",
                "required": ["path", "repo"]
            }
        }
    ]
    
    # Missing 'repo'
    fake_json_content = json.dumps({
        "name": "get_file",
        "arguments": {"path": "src/main.py"}
    })
    
    with patch.object(ollama_client.client, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": fake_json_content,
                "tool_calls": []
            }
        }
        mock_post.return_value = mock_response
        
        result = ollama_client.send_message(messages=[{"role": "user", "content": "fetch"}], tools=tools)
        
        # Should reject because 'repo' is missing
        assert len(result["tool_calls"]) == 0
        assert result["source"] == "native"
        assert "get_file" in result["content"]
