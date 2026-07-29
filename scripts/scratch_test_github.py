import sys
from pprint import pprint
from github import Github

# Add src to path if needed (run from project root)
import os
sys.path.insert(0, os.path.abspath("."))

from src.github.client import GitHubClient
from src.github.exceptions import GitHubRateLimitError

def main():
    print("Initializing unauthenticated GitHub client...")
    # Unauthenticated client (60 requests/hr limit)
    gh = Github()
    client = GitHubClient(gh)

    repo = "fastapi/fastapi"
    pr_number = 1

    print(f"\n--- Testing get_commit_metadata for {repo} PR #{pr_number} ---")
    try:
        commits = client.get_commit_metadata(repo, pr_number)
        for c in commits:
            print(f"Commit: {c.sha[:8]} | {c.author} | {c.date} | {c.message.splitlines()[0]}")
    except GitHubRateLimitError as e:
        print(f"Rate limited: {e}")
        return

    print(f"\n--- Testing list_changed_files for {repo} PR #{pr_number} ---")
    try:
        files = client.list_changed_files(repo, pr_number)
        for f in files:
            print(f"File: {f.filename} ({f.status}) +{f.additions} -{f.deletions}")
    except GitHubRateLimitError as e:
        print(f"Rate limited: {e}")
        return

    print(f"\n--- Testing get_pull_request_diff for {repo} PR #{pr_number} ---")
    try:
        diff = client.get_pull_request_diff(repo, pr_number)
        print(f"PR: {diff.title} (Base: {diff.base_branch} <- Head: {diff.head_branch})")
        print(f"Total additions: {diff.total_additions}, Total deletions: {diff.total_deletions}")
        if diff.changed_files:
            first_file = diff.changed_files[0]
            print(f"\nFirst file patch preview ({first_file.filename}):")
            print("\n".join(str(first_file.patch).splitlines()[:10]))
            print("...")
    except GitHubRateLimitError as e:
        print(f"Rate limited: {e}")
        return

if __name__ == "__main__":
    main()
