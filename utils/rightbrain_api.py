import os
import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional

# --- Configuration Loader ---
def load_rb_config() -> Dict[str, str]:
    """Loads public configuration from rightbrain.config.json in the project root."""
    # Find root relative to this file (utils/rightbrain_api.py -> project_root)
    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / "rightbrain.config.json"
    
    if not config_path.exists():
        print(f"❌ Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(config_path, "r") as f:
        return json.load(f)

# Token cache: stores (token, expiry_timestamp)
_token_cache: Optional[tuple[str, float]] = None

def get_rb_token() -> str:
    """
    Authenticates using credentials from ENV and URLs from config file.
    """
    global _token_cache
    
    # Check cache
    if _token_cache is not None:
        cached_token, expiry_time = _token_cache
        if time.time() < (expiry_time - 60):
            print("✅ Reusing cached Rightbrain token.")
            return cached_token

    # Load Configuration
    config = load_rb_config()
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        print("❌ Error: Missing RB_CLIENT_ID or RB_CLIENT_SECRET env vars.", file=sys.stderr)
        sys.exit(1)

    # Construct URL from Config
    base = config.get("oauth_url", "").rstrip('/')
    path = config.get("auth_path", "/oauth2/token").lstrip('/')
    token_url = f"{base}/{path}"

    print(f"🔐 Requesting token from: {token_url}")

    try:
        # Client Credentials Flow
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "scope": "offline_access",
                "client_id": client_id,
                "client_secret": client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if not response.ok:
            print(f"❌ HTTP Error {response.status_code}", file=sys.stderr)
            print(f"   Target: {token_url}", file=sys.stderr)
            print(f"   Response: {response.text[:500]}", file=sys.stderr)
            sys.exit(1)

        response_data = response.json()
        token = response_data.get("access_token")
        
        if not token:
            print(f"❌ Error: No access_token in response.", file=sys.stderr)
            sys.exit(1)
        
        expires_in = response_data.get("expires_in", 3600)
        _token_cache = (token, time.time() + expires_in)
        
        print(f"✅ Rightbrain token acquired.")
        return token

    except Exception as e:
        print(f"❌ Connection Error: {e}", file=sys.stderr)
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def _get_base_url() -> str:
    """Gets API base URL from config."""
    config = load_rb_config()
    return config.get("api_url", "").rstrip('/')

def _get_project_path() -> str:
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    if not all([org_id, project_id]):
        print("❌ Error: Missing RB_ORG_ID or RB_PROJECT_ID.", file=sys.stderr)
        sys.exit(1)
    return f"/api/v1/org/{org_id}/project/{project_id}"

def get_task(rb_token: str, task_id: str) -> Dict[str, Any]:
    url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}"
    try:
        response = requests.get(url, headers=_get_api_headers(rb_token))
        if response.status_code == 404:
            return {"error": "Task not found", "is_error": True}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def update_task(rb_token: str, task_id: str, update_payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=update_payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def create_task(rb_token: str, task_body: Dict[str, Any]) -> Optional[str]:
    url = f"{_get_base_url()}{_get_project_path()}/task"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=task_body)
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        print(f"  ❌ FAILED to create task: {e}", file=sys.stderr)
        return None

def run_rb_task(rb_token: str, task_id: str, task_input_payload: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    # Implementation remains the same, relies on _get_base_url()
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    
    if not all([org_id, project_id, task_id]):
        return {"error": "Missing configuration", "is_error": True}

    run_url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}/run"
    print(f"🚀 Running {task_name} at {run_url}")
    
    try:
        response = requests.post(run_url, headers=_get_api_headers(rb_token), json={"task_input": task_input_payload}, timeout=600)
        response.raise_for_status()
        print(f"✅ {task_name} complete.")
        return response.json()
    except Exception as e:
        print(f"❌ {task_name} failed: {e}", file=sys.stderr)
        return {"error": str(e), "is_error": True}