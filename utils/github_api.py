import os
import sys
import json
import re
import requests
from typing import Dict, Optional, List
from pathlib import Path

# Add parent directory to path to allow importing utils
sys.path.append(str(Path(__file__).parent.parent))
from utils.rightbrain_api import log

# This module centralizes all GitHub API interactions.

def get_github_headers() -> Dict[str, str]:
    """Helper to get standard GitHub API headers."""
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        log("error", "GITHUB_TOKEN environment variable not set.")
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
        log("info", f"Found existing marker. Replacing content with {marker_to_use} content.")
        updated_body = body_content[:marker_pos] + new_content
    else:
        marker_to_use = FAILURE_MARKER if is_failure else CHECKLIST_MARKER
        log("info", f"No marker found. Appending {marker_to_use} content.")
        separator = "\n\n---\n\n" if body_content.strip() else ""
        updated_body = body_content.strip() + separator + new_content

    payload = {"body": updated_body.strip()}
    payload_size = len(payload['body'])
    
    if payload_size > 65000:
         log("warning", f"Payload size ({payload_size}) is close to GitHub API limit (65,535)!",
             details="Truncated body to 65,000 characters.")
         # Truncate if we are over
         payload['body'] = payload['body'][:65000]


    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        log("success", f"Issue #{issue_number} body updated successfully.")
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
        log("success", f"Successfully posted comment to issue #{issue_number}.")
    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if e.response is not None:
            error_details += f"\nResponse Status: {e.response.status_code}\nResponse Body: {e.response.text}"
        log("error", "Failed to post comment to GitHub issue", details=error_details)
        # Raise an exception, but don't exit.
        raise RuntimeError(f"Failed to post GitHub comment: {e}")

def fetch_issue_comments(repo: str, issue_number: str) -> List[Dict]:
    """Fetches all comments on a specific issue."""
    log("info", f"Fetching comments for issue {repo}#{issue_number}...")
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = get_github_headers()
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log("error", "Failed to fetch comments", details=str(e))
        # This is a critical failure for the commit script.
        sys.exit(1)

def post_failure_and_exit(repo: str, issue_number: str, original_body: str, failure_message: str):
    """Posts a failure message to the issue body and exits the script."""
    log("error", failure_message)
    
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
        log("error", "CRITICAL: Failed to post failure comment to GitHub", details=str(e))
        
    sys.exit(1) # Exit with a non-zero status code

# --- GitHub Issue / Markdown Parsing Helpers ---

def parse_form_field(body: str, field_name: str) -> str:
    """Parses a form field value from markdown content (e.g., GitHub issue body)."""
    pattern = re.compile(rf'### {re.escape(field_name)}\s*\n\s*(.*?)(?=\n### |\Z)', re.IGNORECASE | re.DOTALL)
    match = pattern.search(body)
    if match:
        value = match.group(1).strip()
        # Remove HTML tags if present
        value = re.sub(r'<[^>]+>', '', value)
        return value
    return "N/A"

def extract_vendor_usage_details(markdown_content: str) -> str:
    """Builds the vendor-specific {vendor_usage_details} context block from markdown content."""
    log("info", "Parsing vendor usage details from markdown content...")
    context_parts = [
        f"**Service Name:** {parse_form_field(markdown_content, 'Supplier Name')}",
        f"**Service Description:** {parse_form_field(markdown_content, 'Summary of Proposed Usage')}",
        f"**Vendor/Service Usage Context:** {parse_form_field(markdown_content, 'Summary of Proposed Usage')}", 
        f"**Data Types Involved:** {parse_form_field(markdown_content, 'Data Types Involved')}",
        f"**Term Length:** {parse_form_field(markdown_content, 'Minimum Term Length')}",
    ]
    return "\n".join(context_parts)

def create_github_issue(repo: str, title: str, body: str, labels: Optional[List[str]] = None) -> Dict:
    """Creates a new GitHub issue."""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = get_github_headers()
    payload = {
        "title": title,
        "body": body
    }
    if labels:
        payload["labels"] = labels
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        log("success", f"Successfully created issue: {title}")
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if e.response is not None:
            error_details += f"\nResponse Status: {e.response.status_code}\nResponse Body: {e.response.text}"
        log("error", "Failed to create GitHub issue", details=error_details)
        raise RuntimeError(f"Failed to create GitHub issue: {e}")

def get_vendor_type(issue_body: str) -> str:
    """Determines vendor type from issue body (processor or general)."""
    data_processor_value = parse_form_field(issue_body, "Data Processor")
    return "processor" if data_processor_value.lower() == "yes" else "general"

def get_vendor_type_from_path(file_path_str: str) -> str:
    """Determines vendor type based on file path."""
    return "processor" if "subprocessors" in file_path_str else "general"

def get_sanitized_vendor_name(summary_data: Dict) -> str:
    """Creates a filesystem-safe vendor name from summary data."""
    processor_name = summary_data.get("processor_name", "vendor")
    sanitized = re.sub(r"[^a-z0-9-]+", "-", processor_name.lower()).strip("-")
    return sanitized

def load_company_profile() -> str:
    """Loads the company profile and formats it as a string for the {company_profile} block."""
    log("info", "Loading company profile...")
    project_root = Path(__file__).resolve().parent.parent
    profile_path = project_root / "config" / "company_profile.json"
    if not profile_path.exists():
        log("error", f"Company profile not found at '{profile_path}'")
        sys.exit(1)
    
    try:
        with open(profile_path, 'r') as f:
            data = json.load(f)
        
        # Format as markdown string, as expected by the tasks
        profile_parts = [
            f"**Company Name:** {data.get('name')}",
            f"**Industry:** {data.get('industry')}",
            f"**Services:** {data.get('services')}",
            f"**Applicable Regulations:** {', '.join(data.get('regulations', []))}"
        ]
        return "\n".join(profile_parts)
    except Exception as e:
        log("error", f"Error reading company profile: {e}")
        sys.exit(1)