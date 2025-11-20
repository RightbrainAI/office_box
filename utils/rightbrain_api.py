import os
import sys
import json
import requests
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
def get_rb_token() -> str:
    """
    Authenticates with the Rightbrain API using environment variables.
    Caches the token and reuses it until expiry to minimize OAuth requests.
    """
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

    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")
    
    # --- DEBUGGING START ---
    raw_base_url = os.environ.get("RB_OAUTH2_URL")
    log("debug", f"Raw RB_OAUTH2_URL env var: '{raw_base_url}'")
    
    # Default to the correct OAuth host if not provided
    token_url_base = raw_base_url if raw_base_url else "https://oauth.rightbrain.ai"
    
    # Default to /oauth2/token if not provided
    token_path = os.environ.get("RB_OAUTH2_TOKEN_PATH", "/oauth2/token")
    
    log("debug", f"Using Base URL: '{token_url_base}'")
    log("debug", f"Using Token Path: '{token_path}'")
    # --- DEBUGGING END ---

    if not token_url_base:
        log("error", "Missing RB_OAUTH2_URL environment variable.")
        sys.exit(1)

    # Construct the full URL
    token_url = f"{token_url_base.rstrip('/')}/{token_path.lstrip('/')}"
    log("info", f"Requesting token from: {token_url}")

    if not all([client_id, client_secret]):
        log("error", "Missing RB_CLIENT_ID or RB_CLIENT_SECRET.")
        sys.exit(1)

    try:
        # Using Client Credentials flow via POST body (standard for Rightbrain)
        payload = {
            "grant_type": "client_credentials",
            "scope": "offline_access",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        response = requests.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Debugging: Check for common non-JSON responses (like 404 HTML pages)
        if not response.ok:
            error_details = f"Target URL: {token_url}\nResponse Preview: {response.text[:500]}"
            log("error", f"HTTP Error {response.status_code}", details=error_details)
            sys.exit(1)

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            error_details = f"Target URL: {token_url}\nResponse Start: {response.text[:500]}"
            log("error", "JSON Decode Error. Server returned non-JSON content.", details=error_details)
            sys.exit(1)

        token = response_data.get("access_token")
        if not token:
            error_details = f"Raw data:\n{json.dumps(response_data, indent=2)}"
            log("error", "Response did not contain 'access_token'", details=error_details)
            sys.exit(1)
        
        # Cache the token with expiry (default to 3600 seconds if not provided)
        expires_in = response_data.get("expires_in", 3600)
        expiry_time = time.time() + expires_in
        _token_cache = (token, expiry_time)
        
        log("success", f"Rightbrain token acquired (expires in {expires_in}s).")
        return token
    except Exception as e:
        log("error", "Failed to get Rightbrain token", details=str(e))
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    """Internal helper to create standard API headers."""
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def _get_base_url() -> str:
    """Internal helper to get the base API URL."""
    # Default to the standard app URL if not provided
    api_url = os.environ.get("RB_API_URL", "https://app.rightbrain.ai")
    return api_url.rstrip('/')

def _get_project_path() -> str:
    """Internal helper to get the common org/project API path."""
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    if not all([org_id, project_id]):
        log("error", "Missing RB_ORG_ID or RB_PROJECT_ID.")
        sys.exit(1)
    return f"/api/v1/org/{org_id}/project/{project_id}"

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
    Updates a task. Can be used to create a new revision or update settings.
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
    """
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    
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
        response = requests.post(run_url, headers=headers, json=payload, timeout=600)
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