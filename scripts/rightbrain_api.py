import os
import sys
import json
import requests
<<<<<<< Updated upstream
from typing import Dict, Any, Optional

# This module centralizes all Rightbrain API interactions.

=======
import time
from datetime import datetime
from typing import Dict, Any, Optional, Literal

# This module centralizes all Rightbrain API interactions.

# Token cache: stores (token, expiry_timestamp)
_token_cache: Optional[tuple[str, float]] = None

# --- Centralized Logging ---

def log(
    level: Literal["success", "error", "info", "warning", "debug"],
    message: str,
    details: Optional[str] = None,
    to_stderr: bool = False
) -> None:
    """
    Centralized logging function with consistent emoji prefixes and timestamps.
    
    Args:
        level: The log level (success, error, info, warning, debug)
        message: The main log message
        details: Optional additional details to print on a new line
        to_stderr: If True, writes to stderr instead of stdout (default for errors)
    """
    icons = {
        "success": "✅",
        "error": "❌",
        "info": "ℹ️",
        "warning": "⚠️",
        "debug": "🔍"
    }
    
    icon = icons.get(level, "ℹ️")
    output = sys.stderr if (to_stderr or level == "error") else sys.stdout
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
    
    print(f"[{timestamp}] {icon} {message}", file=output)
    if details:
        print(f"               {details}", file=output)

>>>>>>> Stashed changes
def get_rb_token() -> str:
    """
    Authenticates with the Rightbrain API using environment variables.
    """
<<<<<<< Updated upstream
=======
    global _token_cache
    
    # Check if we have a valid cached token
    if _token_cache is not None:
        cached_token, expiry_time = _token_cache
        # Add 60 second buffer before expiry to be safe
        if time.time() < (expiry_time - 60):
            log("success", "Reusing cached Rightbrain token.")
            return cached_token
        else:
            log("info", "Cached token expired, requesting new token.")

>>>>>>> Stashed changes
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")
    token_url_base = os.environ.get("RB_OAUTH2_URL")
    if not token_url_base:
        log("error", "Missing RB_OAUTH2_URL environment variable.")
        sys.exit(1)
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    token_url = token_url_base

    if not all([client_id, client_secret]):
        log("error", "Missing RB_CLIENT_ID or RB_CLIENT_SECRET.")
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
<<<<<<< Updated upstream
        print("✅ Rightbrain token acquired.")
=======
        
        # Cache the token with expiry (default to 3600 seconds if not provided)
        expires_in = response_data.get("expires_in", 3600)
        expiry_time = time.time() + expires_in
        _token_cache = (token, expiry_time)
        
        log("success", f"Rightbrain token acquired (expires in {expires_in}s).")
>>>>>>> Stashed changes
        return token
    except Exception as e:
        log("error", "Failed to get Rightbrain token", details=str(e))
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    """Internal helper to create standard API headers."""
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def _get_base_url() -> str:
    """Internal helper to get the base API URL."""
    api_url = os.environ.get("RB_API_URL")
    if not api_url:
        log("error", "Missing RB_API_URL environment variable.")
        sys.exit(1)
    return api_url.rstrip('/')

def _get_project_path() -> str:
    """Internal helper to get the common org/project API path."""
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    if not all([org_id, project_id]):
        log("error", "Missing RB_ORG_ID or RB_PROJECT_ID.")
        sys.exit(1)
    # API URL should already include /api/v1, so just use the path
    return f"/org/{org_id}/project/{project_id}"

def get_task(rb_token: str, task_id: str) -> Dict[str, Any]:
    """Fetches the full task object, including all revisions."""
    url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}"
    log("debug", f"GET Task: {task_id}")
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
        details = f"Response: {e.response.json()}" if e.response else str(e)
        log("error", f"Failed to create task '{task_body.get('name')}'", details=details)
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
        log("error", f"Missing RB_ORG_ID, RB_PROJECT_ID, or task_id for {task_name}.")
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
        
    log("info", f"🚀 Running {task_name}", details=f"Input: {json.dumps(logged_input)}")
    
    try:
        response = requests.post(run_url, headers=headers, json=payload, timeout=600) # 10 min timeout
        response.raise_for_status()
        log("success", f"{task_name} complete.")
        # Return the *entire* task run object
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = f"Status: {e.response.status_code}" if e.response else str(e)
        if e.response is not None:
            try:
                error_details += f" | Body: {e.response.json()}"
            except json.JSONDecodeError:
                error_details += f" | Body: {e.response.text}"
        log("error", f"{task_name} API call failed", details=error_details)
        return {"error": f"{task_name} failed", "details": str(e), "is_error": True}