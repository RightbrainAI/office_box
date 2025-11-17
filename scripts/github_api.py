import os
import sys
import json
import requests
from typing import Dict, Optional, List

# This module centralizes all GitHub API interactions.

def get_github_headers() -> Dict[str, str]:
    """Helper to get standard GitHub API headers."""
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        print("❌ Error: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)
        
    return {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def update_issue_body(repo: str, issue_number: str, original_body: str, new_content: str, is_failure: bool = False):
    """
    Updates the GitHub issue body. Replaces content below the checklist or failure marker
    if it exists, otherwise appends.
    """
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = get_github_headers()
    
    CHECKLIST_MARKER = "<!--CHECKLIST_MARKER-->"
    FAILURE_MARKER = "<!--FAILURE_MARKER-->"
    
    body_content = original_body if original_body else ""
    
    # Find either marker
    checklist_pos = body_content.find(CHECKLIST_MARKER)
    failure_pos = body_content.find(FAILURE_MARKER)
    
    marker_pos = -1
    if checklist_pos != -1:
        marker_pos = checklist_pos
    elif failure_pos != -1:
        marker_pos = failure_pos

    if marker_pos != -1:
        marker_to_use = FAILURE_MARKER if is_failure else CHECKLIST_MARKER
        print(f"ℹ️ Found existing marker. Replacing content with {marker_to_use} content.")
        updated_body = body_content[:marker_pos] + new_content
    else:
        marker_to_use = FAILURE_MARKER if is_failure else CHECKLIST_MARKER
        print(f"ℹ️ No marker found. Appending {marker_to_use} content.")
        separator = "\n\n---\n\n" if body_content.strip() else ""
        updated_body = body_content.strip() + separator + new_content

    payload = {"body": updated_body.strip()}
    payload_size = len(payload['body'])
    
    if payload_size > 65000:
         print(f"⚠️ WARNING: Payload size ({payload_size}) is close to GitHub API limit (65,535)!")
         # Truncate if we are over
         payload['body'] = payload['body'][:65000]
         print("  Truncated body to 65,000 characters.")


    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Issue #{issue_number} body updated successfully.")
    except requests.exceptions.RequestException as e:
        error_message = f"❌ Failed to update GitHub issue via PATCH to {url}: {e}"
        if e.response is not None:
            error_message += f"\nStatus Code: {e.response.status_code}"
            try:
                error_details = e.response.json()
                error_message += f"\nResponse Body: {json.dumps(error_details, indent=2)}"
            except json.JSONDecodeError:
                error_message += f"\nResponse Body (non-JSON): {e.response.text}"
        # Raise an exception so the calling script can handle it.
        raise RuntimeError(error_message)

def post_github_comment(repo: str, issue_number: str, body: str):
    """Posts a new comment to the GitHub issue."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = get_github_headers()
    payload = {"body": body}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully posted comment to issue #{issue_number}.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to post comment to GitHub issue: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        # Raise an exception, but don't exit.
        raise RuntimeError(f"Failed to post GitHub comment: {e}")

def fetch_issue_comments(repo: str, issue_number: str) -> List[Dict]:
    """Fetches all comments on a specific issue."""
    print(f"Fetching comments for issue {repo}#{issue_number}...")
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = get_github_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"::error::Failed to fetch comments: {e}")
        # This is a critical failure for the commit script.
        sys.exit(1)

def post_failure_and_exit(repo: str, issue_number: str, original_body: str, failure_message: str):
    """Posts a failure message to the issue body and exits the script."""
    print(f"❌ {failure_message}", file=sys.stderr) # Log to stderr
    
    FAILURE_MARKER = "<!--FAILURE_MARKER-->"
    error_body = (
        f"{FAILURE_MARKER}\n"
        "## 🤖 AI Workflow Failed\n\n"
        "The vendor discovery/analysis workflow failed to run.\n\n"
        f"**Error Details:**\n`{failure_message}`\n\n"
        "**Next Steps:**\n"
        "1.  Check the error details and the GitHub Actions log.\n"
        "2.  If this was a temporary API issue, you can re-run the workflow by adding the trigger label again.\n"
        "3.  If the problem persists, please contact the administrator."
    ).strip()
    
    try:
        # Pass is_failure=True to update_issue_body
        update_issue_body(repo, issue_number, original_body, error_body, is_failure=True)
    except Exception as e:
        # If we can't even post the comment, just log it.
        print(f"❌ CRITICAL: Failed to post failure comment to GitHub: {e}", file=sys.stderr)
        
    sys.exit(1) # Exit with a non-zero status code