import pytest
from src.llm.tool_executor import ToolExecutor

def test_tool_executor_cache():
    """
    Tests that ToolExecutor caches duplicate calls and returns the exact same 
    string without calling the underlying function twice.
    """
    executor = ToolExecutor()
    
    call_count = 0
    
    def mock_fetch(repo: str, path: str):
        nonlocal call_count
        call_count += 1
        return f"content of {path} at call {call_count}"
        
    executor.register("get_file_contents", mock_fetch)
    
    args = {"repo": "test/test", "path": "file1.txt"}
    
    # First call
    res1 = executor.execute("get_file_contents", args)
    assert call_count == 1
    assert "call 1" in res1
    
    # Second call with same exact arguments
    res2 = executor.execute("get_file_contents", args)
    assert call_count == 1  # Should NOT increment
    assert res1 == res2
    
    # Third call with different arguments
    args_diff = {"repo": "test/test", "path": "file2.txt"}
    res3 = executor.execute("get_file_contents", args_diff)
    assert call_count == 2
    assert "call 2" in res3
    
    # Fourth call with slightly different kwargs ordering or structure
    args_diff2 = {"path": "file1.txt", "repo": "test/test"}
    res4 = executor.execute("get_file_contents", args_diff2)
    assert call_count == 2  # Should still hit cache of the first call
    assert res4 == res1
