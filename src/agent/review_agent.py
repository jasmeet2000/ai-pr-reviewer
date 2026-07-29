"""Review Agent node for LangGraph."""

from __future__ import annotations

import json
from typing import Any

from src.agent.state import PRReviewState
from src.config.settings import Settings
from src.llm.base_client import LLMClient
from src.llm.tool_executor import ToolExecutor
from src.llm.schemas import DEFAULT_TOOLS
from src.utils.logger import get_logger

logger = get_logger(__name__)


def review_node(
    state: PRReviewState, llm: LLMClient, tool_executor: ToolExecutor, settings: Settings
) -> dict[str, Any]:
    """Reviews individual files using tool calling to fetch contents if needed.

    This acts as a ReAct loop. In this simplified Phase 5 version, we loop
    through the `files_to_review` selected by the planner, asking the LLM to
    review them. We allow it to use tools to fetch file contents.
    """
    logger.info(
        "Executing review_node for %d files", len(state.get("files_to_review", []))
    )

    if not state.get("files_to_review"):
        return {"final_review": "No files required deep review."}

    reviews = []
    errors = []
    traces = []
    
    import time
    from datetime import datetime, timezone
    from src.agent.exceptions import AgentLoopLimitExceeded

    for file_path in state["files_to_review"]:
        logger.debug(f"Reviewing file: {file_path}")

        messages = [
            {
                "role": "user",
                "content": (
                    f"Please review the file `{file_path}` in the repository `{state['repo']}` "
                    f"(PR #{state['pr_number']}). You can use your tools to fetch its full contents "
                    "or the commit metadata to understand the changes better. Provide a concise critique.\n"
                    f"IMPORTANT: When fetching file contents, use the exact ref: `{state.get('head_branch', '')}`."
                ),
            }
        ]

        iteration = 0
        final_file_review = ""
        fetched_paths = {file_path}

        while iteration < settings.max_tool_calls:
            iteration += 1
            try:
                response = llm.send_message(
                    messages=messages,
                    tools=DEFAULT_TOOLS,
                    system_prompt=(
                        "You are an expert code reviewer. Be concise and focus on security, performance, and architecture.\n\n"
                        "CRITICAL INSTRUCTION - AVOID HALLUCINATION:\n"
                        "1. ONLY review the exact code provided to you in the tool results.\n"
                        "2. DO NOT rely on prior knowledge of this repository, and DO NOT write patches for files you did not explicitly fetch."
                    ),
                )

                tool_calls = response.get("tool_calls", [])
                content = response.get("content", "")
                source = response.get("source", "native")

                # Append the assistant's message to the history
                messages.append(
                    {"role": "assistant", "content": content, "tool_calls": tool_calls}
                )

                if not tool_calls:
                    # If it didn't call tools, we consider the text content as its final review
                    final_file_review = content
                    break

                # Execute tools and feed results back
                for call in tool_calls:
                    tool_name = call.get("name", "")
                    # handle different LLM formats (e.g. OpenAI/Ollama vs Anthropic)
                    args = call.get("arguments", call.get("input", {}))
                    if not args and "function" in call:
                        tool_name = call["function"]["name"]
                        args = call["function"]["arguments"]

                    if tool_name in ["get_file_contents", "get_pr_diff"] and isinstance(args, dict):
                        path_arg = args.get("file_path") or args.get("path")
                        if path_arg and isinstance(path_arg, str):
                            fetched_paths.add(path_arg)

                    # Execute
                    start_time = time.time()
                    tool_result_str = tool_executor.execute(tool_name, args)
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Capture trace
                    traces.append({
                        "tool": tool_name,
                        "args_summary": str(args)[:100] + ("..." if len(str(args)) > 100 else ""),
                        "result_summary": tool_result_str[:100] + ("..." if len(tool_result_str) > 100 else ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": duration_ms,
                        "source": source
                    })

                    # Feed the result back as a user message (tool response)
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Tool '{tool_name}' result:\n{tool_result_str}",
                        }
                    )

            except Exception as e:
                error_msg = f"Review failed for {file_path} on iteration {iteration}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                raise e
        else:
            # Reached max_tool_calls without breaking
            error_msg = f"Tool calling loop for {file_path} exceeded MAX_TOOL_CALLS ({settings.max_tool_calls})."
            logger.error(error_msg)
            errors.append(error_msg)
            raise AgentLoopLimitExceeded(error_msg)

        if final_file_review:
            import re
            # Extract potential paths/files referenced to check grounding
            # Matches words with slashes or ending in common extensions
            mentioned = set(re.findall(r'\b[\w\.-]+(?:/[\w\.-]+)+\b|\b[\w-]+\.(?:py|js|ts|jsx|tsx|cpp|c|h|cs|java|go|rb|php)\b', final_file_review))
            
            grounding_failed = False
            for candidate in mentioned:
                if candidate.startswith("http:") or candidate.startswith("https:"):
                    continue
                if not any(candidate in p or p in candidate for p in fetched_paths):
                    grounding_failed = True
                    logger.warning(f"Grounding check failed: Hallucinated reference to '{candidate}' not in fetched paths {fetched_paths}")
                    break

            reviews.append({
                "file": file_path, 
                "review": final_file_review,
                "grounding_check": "failed" if grounding_failed else "passed",
                "fetched_paths": list(fetched_paths)
            })

    # Combine the individual file reviews into a final summary string
    final_review = "\n\n".join(
        [f"### Review for `{r['file']}` (Grounding: {r.get('grounding_check', 'unknown')})\n{r['review']}" for r in reviews]
    )
    if not final_review:
        final_review = "Review could not be completed due to errors."

    return {"file_reviews": reviews, "final_review": final_review, "errors": errors, "trace": traces}
