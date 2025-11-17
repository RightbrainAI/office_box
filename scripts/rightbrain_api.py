import os
import sys
import json
import requests
from typing import Dict, Any, Optional

# This module centralizes all Rightbrain API interactions.

def get_rb_token() -> str:
    """
    Authenticates with the Rightbrain API using environment variables.
    """
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")
    token_url_base = os.environ.get("RB_OAUTH2_URL")
    if not token_url_base:
        print("❌ Error: Missing RB_OAUTH2_URL environment variable.", file=sys.stderr)
        sys.exit(1)
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    token_url = token_url_base

    if not all([client_id, client_secret]):
        print("❌ Error: Missing RB_CLIENT_ID or RB_CLIENT_SECRET.", file=sys.stderr)
        sys.exit(1)

    try:
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"}
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("No access_token in response.")
        print("✅ Rightbrain token acquired.")
        return token
    except Exception as e:
        print(f"❌ Error getting Rightbrain token: {e}", file=sys.stderr)
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    """Internal helper to create standard API headers."""
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def _get_base_url() -> str:
    """Internal helper to get the base API URL."""
    api_url = os.environ.get("RB_API_URL")
    if not api_url:
        print("❌ Error: Missing RB_API_URL environment variable.", file=sys.stderr)
        sys.exit(1)
    return api_url.rstrip('/')

def _get_project_path() -> str:
    """Internal helper to get the common org/project API path."""
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    if not all([org_id, project_id]):
        print("❌ Error: Missing RB_ORG_ID or RB_PROJECT_ID.", file=sys.stderr)
        sys.exit(1)
    # API URL should already include /api/v1, so just use the path
    return f"/org/{org_id}/project/{project_id}"

def get_task(rb_token: str, task_id: str) -> Dict[str, Any]:
    """Fetches the full task object, including all revisions."""
    url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}"
    print(f"  GET Task: {task_id}")
    try:
        response = requests.get(url, headers=_get_api_headers(rb_token))
        if response.status_code == 404:
            return {"error": "Task not found", "details": "404 Not Found", "is_error": True}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def update_task(rb_token: str, task_id: str, update_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates a task. Can be used to create a new revision (by sending prompts)
    or to update settings (by sending `active_revisions`).
    """
    url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=update_payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def create_task(rb_token: str, task_body: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new task in the project from a local template.
    Returns the new Task ID if successful, else None.
    """
    url = f"{_get_base_url()}{_get_project_path()}/task"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=task_body)
        response.raise_for_status()
        return response.json().get("id")
    except requests.exceptions.RequestException as e:
        print(f"  ❌ FAILED to create task '{task_body.get('name')}': {e}", file=sys.stderr)
        if e.response is not None:
             print(f"  Response Body: {e.response.json()}", file=sys.stderr)
        return None

def run_rb_task(
    rb_token: str,
    task_id: str,
    task_input_payload: Dict[str, Any],
    task_name: str
) -> Dict[str, Any]:
    """
    Runs a specific Rightbrain task with the given payload.
    
    Args:
        rb_token: The authenticated bearer token.
        task_id: The unique ID of the task to run.
        task_input_payload: A dictionary of inputs for the task.
        task_name: A human-readable name for logging.

    Returns:
        The full task run object as a dictionary, or an error dict.
    """
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    # RB_API_URL is already validated by _get_base_url() which is called via run_url construction
    
    if not all([org_id, project_id, task_id]):
        print(f"❌ Error: Missing RB_ORG_ID, RB_PROJECT_ID, or task_id for {task_name}.", file=sys.stderr)
        return {"error": "Missing configuration", "details": "Org/Project/Task ID missing.", "is_error": True}

    run_url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}/run"
    headers = _get_api_headers(rb_token)
    payload = {"task_input": task_input_payload}
    
    # Redact sensitive data for logging
    logged_input = task_input_payload.copy()
    if 'document_text' in logged_input:
        logged_input['document_text'] = f"<Redacted text (length: {len(str(logged_input.get('document_text', '')))})>"
    if 'consolidated_text' in logged_input:
        logged_input['consolidated_text'] = f"<Redacted text (length: {len(str(logged_input.get('consolidated_text', '')))})>"
        
    print(f"🚀 Running {task_name} with input: {json.dumps(logged_input)}")
    
    try:
        response = requests.post(run_url, headers=headers, json=payload, timeout=600) # 10 min timeout
        response.raise_for_status()
        print(f"✅ {task_name} complete.")
        # Return the *entire* task run object
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ {task_name} API call failed: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}", file=sys.stderr)
            try:
                print(f"Response Body: {e.response.json()}", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Response Body (non-JSON): {e.response.text}", file=sys.stderr)
        return {"error": f"{task_name} failed", "details": str(e), "is_error": True}