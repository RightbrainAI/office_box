import os
import sys
import json
import requests
import time
from typing import Dict, Any, Optional

# This module centralizes all Rightbrain API interactions.

# Token cache: stores (token, expiry_timestamp)
_token_cache: Optional[tuple[str, float]] = None

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
            print("✅ Reusing cached Rightbrain token.")
            return cached_token
        else:
            print("ℹ️ Cached token expired, requesting new token.")

    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")
    
    # --- DEBUGGING START ---
    raw_base_url = os.environ.get("RB_OAUTH2_URL")
    print(f"🔍 DEBUG: Raw RB_OAUTH2_URL env var: '{raw_base_url}'")
    
    # Default to the correct OAuth host if not provided
    token_url_base = raw_base_url if raw_base_url else "https://oauth.rightbrain.ai"
    
    # Default to /oauth2/token if not provided
    token_path = os.environ.get("RB_OAUTH2_TOKEN_PATH", "/oauth2/token")
    
    print(f"🔍 DEBUG: Using Base URL: '{token_url_base}'")
    print(f"🔍 DEBUG: Using Token Path: '{token_path}'")
    # --- DEBUGGING END ---

    if not token_url_base:
        print("❌ Error: Missing RB_OAUTH2_URL environment variable.", file=sys.stderr)
        sys.exit(1)

    # Construct the full URL
    token_url = f"{token_url_base.rstrip('/')}/{token_path.lstrip('/')}"
    print(f"🔐 Requesting token from FULL URL: {token_url}")

    if not all([client_id, client_secret]):
        print("❌ Error: Missing RB_CLIENT_ID or RB_CLIENT_SECRET.", file=sys.stderr)
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
            print(f"❌ HTTP Error {response.status_code}", file=sys.stderr)
            print(f"   Target URL: {token_url}", file=sys.stderr)
            # Print first 500 chars to verify if it's HTML (Dashboard) or JSON error
            print(f"   Response Preview: {response.text[:500]}", file=sys.stderr)
            sys.exit(1)

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            print(f"❌ JSON Decode Error. Server returned non-JSON content.", file=sys.stderr)
            print(f"   Target URL: {token_url}", file=sys.stderr)
            print(f"   Response Start: {response.text[:500]}", file=sys.stderr)
            sys.exit(1)

        token = response_data.get("access_token")
        if not token:
            print(f"❌ Error: Response did not contain 'access_token'. Raw data:", file=sys.stderr)
            print(json.dumps(response_data, indent=2), file=sys.stderr)
            sys.exit(1)
        
        # Cache the token with expiry (default to 3600 seconds if not provided)
        expires_in = response_data.get("expires_in", 3600)
        expiry_time = time.time() + expires_in
        _token_cache = (token, expiry_time)
        
        print(f"✅ Rightbrain token acquired (expires in {expires_in}s).")
        return token

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error getting Rightbrain token: {e}", file=sys.stderr)
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
        print("❌ Error: Missing RB_ORG_ID or RB_PROJECT_ID.", file=sys.stderr)
        sys.exit(1)
    return f"/api/v1/org/{org_id}/project/{project_id}"

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
        print(f"  ❌ FAILED to create task '{task_body.get('name')}': {e}", file=sys.stderr)
        if e.response is not None:
             print(f"  Response Body: {e.response.text}", file=sys.stderr)
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
        print(f"❌ Error: Missing RB_ORG_ID, RB_PROJECT_ID, or task_id for {task_name}.", file=sys.stderr)
        return {"error": "Missing configuration", "details": "Org/Project/Task ID missing.", "is_error": True}

    run_url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}/run"
    headers = _get_api_headers(rb_token)
    payload = {"task_input": task_input_payload}
    
    # Redact sensitive data for logging
    logged_input = task_input_payload.copy()
    if 'document_text' in logged_input:
        logged_input['document_text'] = f"<Redacted text (length: {len(str(logged_input.get('document_text', '')))})>"
    
    print(f"🚀 Running {task_name} with input: {json.dumps(logged_input)}")
    
    try:
        response = requests.post(run_url, headers=headers, json=payload, timeout=600)
        response.raise_for_status()
        print(f"✅ {task_name} complete.")
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