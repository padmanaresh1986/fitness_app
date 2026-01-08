import base64
import json
import requests
from pathlib import Path


def push_excel_to_github(
    local_file_path: str,
    github_token: str,
    owner: str,
    repo: str,
    repo_file_path: str,
    branch: str = "main",
    commit_message: str = "Auto update leaderboard"
) -> str:
    """
    Push an Excel file to GitHub (create or update).

    Returns: GitHub API content URL
    """

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json"
    }

    # Step 1: Check if file already exists (to get SHA)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{repo_file_path}"
    response = requests.get(url, headers=headers)

    sha = response.json().get("sha") if response.status_code == 200 else None

    # Step 2: Read & encode file
    content = base64.b64encode(Path(local_file_path).read_bytes()).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": content,
        "branch": branch
    }

    if sha:
        payload["sha"] = sha

    # Step 3: Push file
    push_response = requests.put(url, headers=headers, data=json.dumps(payload))
    push_response.raise_for_status()

    return push_response.json()["content"]["html_url"]
