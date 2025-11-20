import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Literal

# --- Centralized Logging ---

def log(
    level: Literal["success", "error", "info", "warning", "debug"],
    message: str,
    details: Optional[str] = None,
    to_stderr: bool = False
) -> None:
    """
    Centralized logging function with consistent emoji prefixes and timestamps.
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
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print(f"[{timestamp}] {icon} {message}", file=output)
    if details:
        print(f"               {details}", file=output)

# --- Configuration Loader ---

def load_rb_config() -> Dict[str, str]:
    """Loads public configuration from rightbrain.config.json in the config folder."""
    try:
        # Find root relative to this file (utils/rightbrain_api.py -> project_root)
        root_dir = Path(__file__).resolve().parent.parent
        config_path = root_dir / "config/rightbrain.config.json"
        
        if not config_path.exists():
            # Fallback if file is missing, though file is preferred
            log("warning", f"Config file not found at {config_path}. Using defaults.")
            return {}
            
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log("error", f"Failed to load config file: {e}")
        sys.exit(1)

# --- API Functions ---

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
            log("success", "Reusing cached Rightbrain token.")
            return cached_token

    # Load Configuration
    config = load_rb_config()
    
    # Credentials still come from secrets (Env vars)
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        log("error", "Missing RB_CLIENT_ID or RB_CLIENT_SECRET env vars.")
        sys.exit(1)

    # Construct URL from Config (with fallbacks)
    base = config.get("oauth_url") or os.environ.get("RB_OAUTH2_URL") or "https://oauth.rightbrain.ai"
    path = config.get("auth_path") or os.environ.get("RB_OAUTH2_TOKEN_PATH") or "/oauth2/token"
    
    base = base.rstrip('/')
    path = path.lstrip('/')
    token_url = f"{base}/{path}"

    log("debug", f"Requesting token from: {token_url}")

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
            log("error", f"HTTP Error {response.status_code}", details=f"Response: {response.text[:500]}")
            sys.exit(1)

        response_data = response.json()
        token = response_data.get("access_token")
        
        if not token:
            log("error", "No access_token in response.", details=json.dumps(response_data, indent=2))
            sys.exit(1)
        
        expires_in = response_data.get("expires_in", 3600)
        _token_cache = (token, time.time() + expires_in)
        
        log("success", "Rightbrain token acquired.")
        return token

    except Exception as e:
        log("error", f"Connection Error during auth: {e}")
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def _get_base_url() -> str:
    """Gets API base URL from config."""
    config = load_rb_config()
    # Fallback to env var or default
    url = config.get("api_url") or os.environ.get("RB_API_URL") or "https://app.rightbrain.ai"
    return url.rstrip('/')

def _get_project_path() -> str:
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    if not all([org_id, project_id]):
        log("error", "Missing RB_ORG_ID or RB_PROJECT_ID.")
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
        log("error", f"FAILED to create task '{task_body.get('name')}'", details=str(e))
        return None

def run_rb_task(rb_token: str, task_id: str, task_input_payload: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    
    if not all([org_id, project_id, task_id]):
        log("error", f"Missing configuration for {task_name}")
        return {"error": "Missing configuration", "is_error": True}

    run_url = f"{_get_base_url()}{_get_project_path()}/task/{task_id}/run"
    
    # Redact sensitive data for logging
    logged_input = task_input_payload.copy()
    if 'document_text' in logged_input:
        logged_input['document_text'] = f"<Redacted text>"
        
    log("info", f"Running {task_name}", details=f"Input keys: {list(logged_input.keys())}")
    
    try:
        response = requests.post(
            run_url, 
            headers=_get_api_headers(rb_token), 
            json={"task_input": task_input_payload}, 
            timeout=600
        )
        response.raise_for_status()
        log("success", f"{task_name} complete.")
        return response.json()
    except Exception as e:
        log("error", f"{task_name} failed", details=str(e))
        return {"error": str(e), "is_error": True}