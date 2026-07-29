# AI PR Reviewer & QA Assistant

An agentic PR reviewer built with LangGraph, supporting both Claude and local Ollama models.

## Setup & Installation

1. **Clone the repository and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables:**
   Copy the example environment file and fill in your credentials.
   ```bash
   cp .env.example .env
   ```
   At a minimum, you must provide a `GITHUB_TOKEN` to read PRs. For the free, local implementation, you do not need an Anthropic key.

3. **Install and Run Ollama (for free local inference):**
   - Download and install [Ollama](https://ollama.com/).
   - Start the Ollama server locally (runs on `http://localhost:11434` by default).
   - Pull the recommended model:
     ```bash
     ollama pull qwen2.5-coder:7b
     ```

## Known Limitations

- **Knowledge Collapse on Famous Repositories:** Small local models (like `qwen2.5-coder:7b`) may suffer from "knowledge collapse" on widely known codebases, hallucinating files or patches that were never fetched despite system prompt instructions. We use a deterministic post-generation check that flags reviews referencing un-fetched filenames as a safety net against this.
- **Hardware-bound Timeouts:** Processing large files (e.g., >8000 characters) + diffs + chat history can cause local inference to exceed generation timeouts (e.g., 180s on `httpx`) during the final synthesis step. This is a documented hardware limitation for local models; our primary mitigations are file content truncation, duplicate-call prevention (caching), and a lighter grounding prompt.
- **Review Depth / Specificity:** Grounding checks verify that the review doesn't reference files or repos that were never fetched — but they do NOT verify that findings cite specific functions, lines, or logic from the actual file content. `qwen2.5-coder:7b` tends to produce structurally correct but generic findings (e.g., "add docstrings", "add error handling") rather than engaging with the code it read. This is a model-capability limitation, not a pipeline bug; Claude produces more specific reviews on the same inputs.

## Future Improvements

- **Async API / Job Queue:** Upgrade the synchronous execution model to an async job queue (e.g., Celery or Redis) to support concurrent users and long-running reviews without HTTP timeouts.

## Usage

The AI PR Reviewer provides two fully tested, free, Ollama-based entry points, alongside a reference implementation for GitHub Actions:

### 1. Command Line Interface (CLI)
Ideal for local scripting and manual triggers. (Fully Tested & Free)
```bash
python review_pr.py --repo "owner/repo" --pr 123 --provider ollama --post-comment
```

### 2. Streamlit UI
Ideal for interactive use, visual trace debugging, and manual review generation.
```bash
streamlit run src/ui/app.py
```

### 3. GitHub Action (Reference Implementation)
> **Note**: This workflow structurally requires a paid `ANTHROPIC_API_KEY` to run Claude inside GitHub Actions, as Ollama cannot run natively on standard hosted runners. Due to the strict free-only constraints of this project, this action serves as an **architectural extension point** and has not been live-tested.

You can theoretically deploy the reviewer as an automated bot in your own repositories by providing a paid API key. 

**Setup Instructions (Unverified):**
1. Navigate to your repository's **Settings > Secrets and variables > Actions**.
2. Add a new repository secret named `ANTHROPIC_API_KEY` with your Claude API key.
3. Ensure your repository's Action permissions allow `GITHUB_TOKEN` to read/write Pull Request comments.
4. Copy the `review-action.yml` file into your repository under `.github/workflows/review-action.yml`.

Every time a PR is opened or updated, the action will run the `review_pr.py` script with Claude and post the results automatically.
