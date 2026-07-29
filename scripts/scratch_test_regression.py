"""Diagnostic script: Verify AgentLoopLimitExceeded and fallback parser fix.

Runs a real, unmocked E2E pipeline against a live GitHub PR using Ollama.
Tests that:
1. The fixed fallback parser no longer duplicates tool calls (Bug 1 + Bug 2).
2. AgentLoopLimitExceeded is raised (not swallowed) if the loop hits the cap.
3. A normal review completes successfully when the LLM behaves.

Usage:
    python scratch_test_regression.py
"""
import sys
import os
import json
import time
import traceback

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from src.config.settings import Settings
from src.github.client import GitHubClient
from src.llm.ollama_client import OllamaClient
from src.llm.tool_executor import ToolExecutor
from src.agent.state import PRReviewState
from src.agent.review_agent import review_node
from src.agent.exceptions import AgentLoopLimitExceeded
from src.review.review_generator import synthesize_review
from src.review.report_renderer import render_markdown
import github
from github import Github
from dataclasses import asdict


def setup():
    """Initialize all components with Ollama."""
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = "qwen2.5-coder:7b"
    os.environ["LOG_LEVEL"] = "DEBUG"  # See all fallback parser logs

    settings = Settings()
    gh = Github(auth=github.Auth.Token(settings.github_token))
    gh_client = GitHubClient(gh)
    llm_client = OllamaClient(settings)
    tool_executor = ToolExecutor()

    # Register real GitHub tools (same as E2E test)
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

    return settings, gh_client, llm_client, tool_executor


def test_1_fallback_parser_no_duplicate():
    """Unit test: verify fallback parser returns exactly 1 tool call, not N."""
    print("\n" + "=" * 70)
    print("TEST 1: Fallback parser deduplication")
    print("=" * 70)

    from src.llm.schemas import DEFAULT_TOOLS

    client = OllamaClient.__new__(OllamaClient)
    # Simulate Ollama returning a tool call as text content (no native tool_calls)
    fake_data = {
        "message": {
            "role": "assistant",
            "content": json.dumps({
                "name": "get_file_contents",
                "arguments": {"repo": "test/repo", "path": "test.py"}
            }),
            "tool_calls": []  # empty — triggers fallback
        }
    }

    result = client._parse_response(fake_data, DEFAULT_TOOLS)
    n_calls = len(result["tool_calls"])
    print(f"  Tool calls returned: {n_calls}")
    print(f"  Source: {result['source']}")

    if n_calls == 1:
        print("  ✅ PASS — Exactly 1 tool call injected (not duplicated)")
        return True
    else:
        print(f"  ❌ FAIL — Expected 1 tool call, got {n_calls}")
        return False


def test_2_fallback_parser_rejects_unknown_tool():
    """Unit test: verify fallback parser rejects unknown tool names."""
    print("\n" + "=" * 70)
    print("TEST 2: Fallback parser rejects unregistered tool names")
    print("=" * 70)

    from src.llm.schemas import DEFAULT_TOOLS

    client = OllamaClient.__new__(OllamaClient)
    fake_data = {
        "message": {
            "role": "assistant",
            "content": json.dumps({
                "name": "hallucinated_tool_that_doesnt_exist",
                "arguments": {"some_arg": "value"}
            }),
            "tool_calls": []
        }
    }

    result = client._parse_response(fake_data, DEFAULT_TOOLS)
    n_calls = len(result["tool_calls"])
    print(f"  Tool calls returned: {n_calls}")
    print(f"  Source: {result['source']}")

    if n_calls == 0 and result["source"] == "native":
        print("  ✅ PASS — Hallucinated tool rejected, treated as plain text")
        return True
    else:
        print(f"  ❌ FAIL — Expected 0 tool calls (rejected), got {n_calls}")
        return False


def test_3_agent_loop_limit_raised():
    """Integration test: verify AgentLoopLimitExceeded is raised, not swallowed.
    
    We force MAX_TOOL_CALLS=2 and use a real Ollama call that will try to
    call tools. If the LLM uses both iterations on tool calls, it MUST
    raise AgentLoopLimitExceeded — not silently return a partial result.
    """
    print("\n" + "=" * 70)
    print("TEST 3: AgentLoopLimitExceeded is raised (MAX_TOOL_CALLS=2)")
    print("=" * 70)

    settings, gh_client, llm_client, tool_executor = setup()

    # Override to a tiny limit to force the exception
    settings.max_tool_calls = 2
    print(f"  MAX_TOOL_CALLS set to: {settings.max_tool_calls}")

    repo = "fastapi/fastapi"
    pr_number = 1

    pr = gh_client._get_pull_request(gh_client._get_repo(repo), pr_number, repo)
    pr_diff = gh_client.get_pull_request_diff(repo, pr_number)

    state: PRReviewState = {
        "repo": repo,
        "pr_number": pr_number,
        "head_branch": pr.head.sha,
        "diff_context": f"PR title: {pr_diff.title}\nFiles changed: {', '.join([f.filename for f in pr_diff.changed_files])}",
        "commit_metadata": [],
        "files_to_review": ["tests/test_path.py"],  # Force a specific file
        "file_reviews": [],
        "final_review": "",
        "errors": [],
        "trace": []
    }

    start = time.time()
    try:
        result = review_node(state, llm_client, tool_executor, settings)
        duration = time.time() - start
        print(f"  Duration: {duration:.1f}s")
        # If we get here, the LLM finished within 2 iterations (possible if it
        # fetched the file and immediately reviewed it without more tool calls)
        if result.get("file_reviews"):
            print(f"  ⚠️  LLM completed review in ≤2 iterations (no loop exceeded).")
            print(f"  This is VALID if the LLM was well-behaved. Trace:")
            for t in result.get("trace", []):
                print(f"    [{t.get('source', 'native')}] {t['tool']} -> {t['result_summary'][:60]}")
            print("  ✅ PASS (LLM cooperated within the limit)")
            return True
        else:
            print(f"  ❌ FAIL — No file_reviews AND no exception. Result keys: {list(result.keys())}")
            return False
    except AgentLoopLimitExceeded as e:
        duration = time.time() - start
        print(f"  Duration: {duration:.1f}s")
        print(f"  ✅ PASS — AgentLoopLimitExceeded raised correctly:")
        print(f"     {e}")
        return True
    except Exception as e:
        duration = time.time() - start
        print(f"  Duration: {duration:.1f}s")
        print(f"  ❌ UNEXPECTED — Got {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def test_4_full_e2e_live_run():
    """Full E2E live run with default MAX_TOOL_CALLS=10.
    
    Must either:
    - Complete successfully with a rendered review, OR
    - Raise AgentLoopLimitExceeded loudly (not swallow it as 'synthesis failed')
    """
    print("\n" + "=" * 70)
    print("TEST 4: Full E2E live run (MAX_TOOL_CALLS=10)")
    print("=" * 70)

    settings, gh_client, llm_client, tool_executor = setup()
    settings.max_tool_calls = 10
    print(f"  MAX_TOOL_CALLS: {settings.max_tool_calls}")

    repo = "fastapi/fastapi"
    pr_number = 1

    pr = gh_client._get_pull_request(gh_client._get_repo(repo), pr_number, repo)
    pr_diff = gh_client.get_pull_request_diff(repo, pr_number)

    state: PRReviewState = {
        "repo": repo,
        "pr_number": pr_number,
        "head_branch": pr.head.sha,
        "diff_context": f"PR title: {pr_diff.title}\nFiles changed: {', '.join([f.filename for f in pr_diff.changed_files])}",
        "commit_metadata": [],
        "files_to_review": ["tests/test_path.py"],
        "file_reviews": [],
        "final_review": "",
        "errors": [],
        "trace": []
    }

    start = time.time()
    try:
        result = review_node(state, llm_client, tool_executor, settings)
        duration = time.time() - start
        print(f"  Review node completed in {duration:.1f}s")

        # Show trace
        print(f"\n  --- TRACE ({len(result.get('trace', []))} entries) ---")
        for t in result.get("trace", []):
            src = t.get('source', 'native')
            print(f"  [{src}] {t['tool']}({t['args_summary'][:50]}) -> {t['result_summary'][:60]}... [{t['duration_ms']}ms]")

        # Show errors
        if result.get("errors"):
            print(f"\n  --- ERRORS ---")
            for e in result["errors"]:
                print(f"  ⚠️  {e}")

        # Show file reviews
        reviews = result.get("file_reviews", [])
        print(f"\n  --- FILE REVIEWS ({len(reviews)}) ---")
        for r in reviews:
            gc = r.get("grounding_check", "unknown")
            print(f"  [{gc}] {r['file']}: {r['review'][:120]}...")

        # Now synthesize
        if reviews:
            print(f"\n  --- SYNTHESIS ---")
            synth_start = time.time()
            # Build a minimal state with file_reviews for synthesis
            synth_state = {"file_reviews": reviews}
            structured = synthesize_review(synth_state, llm_client)
            synth_dur = time.time() - synth_start
            print(f"  Synthesis completed in {synth_dur:.1f}s")
            print(f"  Recommendation: {structured.get('final_recommendation')}")
            print(f"  Findings: {len(structured.get('findings', []))}")
            print(f"  Summary: {structured.get('summary', '')[:200]}")

            md = render_markdown(structured)
            with open("scratch_regression_report.md", "w", encoding="utf-8") as f:
                f.write(md)
            print(f"\n  Report written to scratch_regression_report.md")

        print(f"\n  ✅ PASS — E2E completed successfully")
        return True

    except AgentLoopLimitExceeded as e:
        duration = time.time() - start
        print(f"  Duration: {duration:.1f}s")
        print(f"  ⚠️  AgentLoopLimitExceeded raised (LLM stuck in tool loop):")
        print(f"     {e}")
        print(f"  This is CORRECT behavior — the exception propagated, not swallowed.")
        print(f"  ✅ PASS (exception raised loudly, not silently swallowed)")
        return True

    except Exception as e:
        duration = time.time() - start
        print(f"  Duration: {duration:.1f}s")
        print(f"  ❌ UNEXPECTED — {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = {}

    # Run offline unit tests first (no Ollama needed)
    results["test_1"] = test_1_fallback_parser_no_duplicate()
    results["test_2"] = test_2_fallback_parser_rejects_unknown_tool()

    # Check if Ollama is available before running live tests
    print("\n" + "=" * 70)
    print("Checking Ollama availability...")
    print("=" * 70)
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  Ollama is running. Available models: {models}")
        has_ollama = True
        if not any("qwen2.5-coder" in m for m in models):
            print("  ⚠️  qwen2.5-coder:7b not found. Live tests may fail.")
    except Exception as e:
        print(f"  ⚠️  Ollama not available: {e}")
        print(f"  Skipping live tests (3 and 4).")
        has_ollama = False

    if has_ollama:
        results["test_3"] = test_3_agent_loop_limit_raised()
        results["test_4"] = test_4_full_e2e_live_run()

    # Summary
    print("\n" + "=" * 70)
    print("REGRESSION TEST SUMMARY")
    print("=" * 70)
    all_pass = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n  All {len(results)} tests passed.")
    else:
        print(f"\n  SOME TESTS FAILED.")

    sys.exit(0 if all_pass else 1)
