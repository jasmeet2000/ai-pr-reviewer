import sys
import os
import json
from pprint import pprint

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from src.config.settings import Settings
from src.github.client import GitHubClient
from src.llm.ollama_client import OllamaClient
from src.llm.tool_executor import ToolExecutor
from src.agent.graph import build_graph
import github
from github import Github

def main():
    print("Initializing Settings and Clients...")
    os.environ["LLM_PROVIDER"] = "ollama"
    # Testing with qwen2.5-coder:7b
    os.environ["OLLAMA_MODEL"] = "qwen2.5-coder:7b"
    
    settings = Settings()
    
    # Let Settings load GITHUB_TOKEN from .env. If missing, it will crash.
    # We must construct PyGithub client with auth
    gh = Github(auth=github.Auth.Token(settings.github_token))
    gh_client = GitHubClient(gh)
    
    # Using Ollama
    llm_client = OllamaClient(settings)
    
    # Bind real GitHub methods to the ToolExecutor
    tool_executor = ToolExecutor()
    
    # We must wrap the domain models returned by GitHubClient so they are JSON-serializable dicts
    from dataclasses import asdict
    
    def wrapped_get_diff(repo: str, pr_number: int) -> dict:
        return asdict(gh_client.get_pull_request_diff(repo, pr_number))
        
    def wrapped_get_file_contents(repo: str, path: str, ref: str = None) -> str:
        return gh_client.get_file_contents(repo, path, ref)
        
    def wrapped_list_changed_files(repo: str, pr_number: int) -> list:
        return [asdict(f) for f in gh_client.list_changed_files(repo, pr_number)]
        
    def wrapped_get_commit_metadata(repo: str, pr_number: int) -> list:
        res = []
        for c in gh_client.get_commit_metadata(repo, pr_number):
            d = asdict(c)
            d["date"] = d["date"].isoformat()
            res.append(d)
        return res
    
    tool_executor.register("get_diff", wrapped_get_diff)
    tool_executor.register("get_file_contents", wrapped_get_file_contents)
    tool_executor.register("list_changed_files", wrapped_list_changed_files)
    tool_executor.register("get_commit_metadata", wrapped_get_commit_metadata)
    
    def mock_planner(state):
        print("Mock planner: returning files to guarantee review.")
        files = ["tests/test_path.py"]
        return {"files_to_review": files}
        
    print("Building LangGraph...")
    from langgraph.graph import StateGraph, END
    from src.agent.state import PRReviewState
    from src.agent.review_agent import review_node
    
    workflow = StateGraph(PRReviewState)
    workflow.add_node("planner_node", mock_planner)
    workflow.add_node(
        "review_node",
        lambda state: review_node(state, llm_client, tool_executor, settings),
    )
    workflow.set_entry_point("planner_node")
    workflow.add_edge("planner_node", "review_node")
    workflow.add_edge("review_node", END)
    app = workflow.compile()
    
    repo = "fastapi/fastapi"
    pr_number = 1
    
    print(f"Fetching PR #{pr_number} metadata to populate state...")
    pr = gh_client._get_pull_request(gh_client._get_repo(repo), pr_number, repo)
    pr_diff = gh_client.get_pull_request_diff(repo, pr_number)
    
    initial_state = {
        "repo": repo,
        "pr_number": pr_number,
        "head_branch": pr.head.sha,  # Use SHA so it doesn't 404 if branch was deleted
        "diff_context": f"PR title: {pr_diff.title}\nFiles changed: {', '.join([f.filename for f in pr_diff.changed_files])}",
        "commit_metadata": [],
        "files_to_review": [],
        "file_reviews": [],
        "final_review": "",
        "errors": [],
        "trace": []
    }
    
    print(f"\n--- Running E2E Graph on {repo} PR #{pr_number} ---")
    try:
        final_state = app.invoke(initial_state)
    except Exception as e:
        print(f"\nGraph execution failed: {e}")
        return
        
    print("\n--- FINAL TRACE ---")
    for t in final_state.get("trace", []):
        source_val = t.get('source', 'native')
        print(f"[{t['timestamp']}] Tool: {t['tool']} (source: {source_val}) | Args: {t['args_summary']} | Duration: {t['duration_ms']}ms")
        print(f"Result Preview: {t['result_summary']}")
        
    print("\n--- FINAL ERRORS ---")
    pprint(final_state.get("errors", []))
    
    print("\n--- FILES SELECTED BY PLANNER ---")
    pprint(final_state.get("files_to_review", []))
    
    print("\n--- FINAL REVIEW (Structured JSON) ---")
    from src.review.review_generator import synthesize_review
    from src.review.report_renderer import render_markdown
    
    import time
    synth_start = time.time()
    structured_review = synthesize_review(final_state, llm_client)
    synth_duration = time.time() - synth_start
    
    print(json.dumps(structured_review, indent=2, ensure_ascii=False))
    print(f"\n--- SYNTHESIS TIMING ---")
    print(f"Full synthesis step took {synth_duration:.2f} seconds.")
    
    with open("scratch_review_report.json", "w", encoding="utf-8") as f:
        json.dump(structured_review, f, indent=2, ensure_ascii=False)

    print("\n--- RENDERING REPORT ---")
    md_output = render_markdown(structured_review)
    print(md_output)
    with open("scratch_review_report.md", "w", encoding="utf-8") as f:
        f.write(md_output)
    print("Wrote scratch_review_report.md and scratch_review_report.json")

if __name__ == "__main__":
    main()
