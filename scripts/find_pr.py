import requests

def find_small_pr(repo):
    url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=50"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    # We don't have a token here, but public endpoints allow 60 req/hr
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Error: {resp.status_code}")
        return
        
    prs = resp.json()
    for pr in prs:
        pr_number = pr["number"]
        files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        files_resp = requests.get(files_url, headers=headers)
        if files_resp.status_code == 200:
            files = files_resp.json()
            if len(files) == 1 and files[0]["changes"] < 10:
                print(f"Found small PR: {repo} #{pr_number}")
                print(f"File: {files[0]['filename']} ({files[0]['changes']} changes)")
                return

find_small_pr("tiangolo/fastapi")
