import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Literal

# Load .env file from project root if it exists (for local development)
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

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
    Authenticates using credentials from ENV and URLs from env vars (primary) or config file (fallback).
    """
    global _token_cache
    
    # Check cache
    if _token_cache is not None:
        cached_token, expiry_time = _token_cache
        if time.time() < (expiry_time - 60):
            log("success", "Reusing cached Rightbrain token.")
            return cached_token

    # Load Configuration for fallback
    config = load_rb_config()
    
    # Credentials still come from secrets (Env vars)
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        log("error", "Missing RB_CLIENT_ID or RB_CLIENT_SECRET env vars.")
        sys.exit(1)

    # Get TOKEN_URI from env var first, then try RB_OAUTH2_URL + RB_OAUTH2_TOKEN_PATH, then fallback to config
    token_url = os.environ.get("TOKEN_URI")
    if token_url:
        log("debug", f"Using TOKEN_URI from environment variable: {token_url}")
    else:
        # Try constructing from RB_OAUTH2_URL and RB_OAUTH2_TOKEN_PATH
        oauth2_url = os.environ.get("RB_OAUTH2_URL")
        oauth2_token_path = os.environ.get("RB_OAUTH2_TOKEN_PATH") or os.environ.get("RB_OAUTH2_AUTH_PATH")
        
        if oauth2_url:
            if oauth2_token_path:
                base = oauth2_url.rstrip('/')
                path = oauth2_token_path.lstrip('/')
                token_url = f"{base}/{path}"
                log("debug", f"Constructed TOKEN_URI from RB_OAUTH2_URL and RB_OAUTH2_TOKEN_PATH: {token_url}")
            else:
                # If RB_OAUTH2_URL is set but no path, assume /oauth2/token
                base = oauth2_url.rstrip('/')
                token_url = f"{base}/oauth2/token"
                log("debug", f"Constructed TOKEN_URI from RB_OAUTH2_URL (default path): {token_url}")
        else:
            # Fallback: construct from config file
            log("warning", "TOKEN_URI and RB_OAUTH2_URL not found, falling back to config file")
            log("debug", f"Available env vars starting with 'TOKEN' or 'RB_OAUTH': {[k for k in os.environ.keys() if 'TOKEN' in k or 'OAUTH' in k]}")
            base = config.get("oauth_url") or "https://oauth.rightbrain.ai"
            path = config.get("auth_path") or "/oauth2/token"
            base = base.rstrip('/')
            path = path.lstrip('/')
            token_url = f"{base}/{path}"
            log("debug", f"Constructed TOKEN_URI from config file: {token_url}")

    log("debug", f"Requesting token from: {token_url}")

    try:
        # FIX: Reverted to Basic Auth (client_secret_basic) as required by the server config
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={
                "grant_type": "client_credentials",
                "scope": "offline_access"
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

def get_api_root() -> str:
    """Gets API root URL from env var (primary) or config (fallback)."""
    # Use API_ROOT from env var first (includes /api/v1)
    api_root = os.environ.get("API_ROOT")
    if api_root:
        log("debug", f"Using API_ROOT from environment variable: {api_root}")
        api_root = api_root.rstrip('/')
        if not api_root.endswith('/api/v1'):
            api_root = f"{api_root}/api/v1"
        return api_root
    
    # Fallback: construct from config file
    log("warning", "API_ROOT environment variable not found, falling back to config file")
    log("debug", f"Available env vars starting with 'API' or 'RB_API': {[k for k in os.environ.keys() if 'API' in k and ('ROOT' in k or 'RB_API' in k)]}")
    config = load_rb_config()
    api_url = config.get("api_url") or "https://app.rightbrain.ai"
    api_url = api_url.rstrip('/')
    # If config doesn't include /api/v1, add it
    if not api_url.endswith('/api/v1'):
        api_url = f"{api_url}/api/v1"
    log("debug", f"Constructed API_ROOT from config file: {api_url}")
    return api_url

def get_rb_config() -> Dict[str, str]:
    """
    Retrieves Rightbrain configuration (Org ID, Project ID, Client ID, Client Secret)
    from environment variables. Exits if any are missing.
    """
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([org_id, project_id, client_id, client_secret]):
        log("error", "Missing required secrets.", details="Requires: RB_ORG_ID, RB_PROJECT_ID, RB_CLIENT_ID, RB_CLIENT_SECRET")
        sys.exit(1)
        
    return {
        "org_id": org_id,
        "project_id": project_id,
        "client_id": client_id,
        "client_secret": client_secret
    }

def get_project_path() -> str:
    config = get_rb_config()
    return f"/org/{config['org_id']}/project/{config['project_id']}"

def detect_environment(api_url: Optional[str] = None) -> str:
    """
    Detects the environment (staging or production).
    Priority 1: Explicit 'RIGHTBRAIN_ENVIRONMENT' or 'RB_ENVIRONMENT' env var.
    Priority 2: Heuristic check of the API URL.
    """
    # 1. Explicit Overwrite (check both env var names)
    explicit_env = os.environ.get("RIGHTBRAIN_ENVIRONMENT") or os.environ.get("RB_ENVIRONMENT")
    if explicit_env:
        detected = explicit_env.lower().strip()
        env_var_name = "RIGHTBRAIN_ENVIRONMENT" if os.environ.get("RIGHTBRAIN_ENVIRONMENT") else "RB_ENVIRONMENT"
        log("debug", f"Environment detected from {env_var_name}: {detected}")
        return detected

    # 2. Heuristic Fallback
    if api_url is None:
        api_root = get_api_root()
    else:
        api_root = api_url.rstrip('/')
        if not api_root.endswith('/api/v1'):
            api_root = f"{api_root}/api/v1"
    
    # Check if it's staging (common patterns: staging, dev, test, stag)
    if any(keyword in api_root.lower() for keyword in ['staging', 'dev', 'test', 'sandbox', 'stag']):
        log("debug", f"Environment detected via heuristic (API URL contains staging keyword): staging")
        return 'staging'
    
    log("warning", f"Environment detection defaulting to 'production'. Set RIGHTBRAIN_ENVIRONMENT=staging to override.")
    log("debug", f"API URL used for detection: {api_root}")
    return 'production'

def get_task_id_by_name(task_name: str, environment: Optional[str] = None) -> Optional[str]:
    """
    Looks up a task ID by task name from the task manifest.
    If environment is not provided, detects it automatically.
    Returns None if not found.
    """
    if environment is None:
        environment = detect_environment()
    
    log("debug", f"Looking up task '{task_name}' in environment '{environment}'")
    
    project_root = Path(__file__).resolve().parent.parent
    manifest_path = project_root / "tasks" / "task_manifest.json"
    
    if not manifest_path.exists():
        log("error", f"Task manifest not found at {manifest_path}")
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check if manifest has new structure with environments
        if isinstance(manifest, dict) and (environment in manifest or 'staging' in manifest or 'production' in manifest):
            env_section = manifest.get(environment, {})
            # Try to find by task name
            for filename, task_data in env_section.items():
                if isinstance(task_data, dict):
                    # New structure: {filename: {name: "...", id: "..."}}
                    if task_data.get('name') == task_name:
                        task_id = task_data.get('id')
                        if task_id:
                            log("debug", f"Found task ID for '{task_name}': {task_id} (from {filename})")
                            return task_id
                elif isinstance(task_data, str):
                    # Direct ID mapping, need to check task file for name
                    task_file = project_root / "tasks" / filename
                    if task_file.exists() and filename.endswith('.json'):
                        try:
                            with open(task_file, 'r') as tf:
                                task_def = json.load(tf)
                                if task_def.get('name') == task_name:
                                    return task_data
                        except:
                            pass
        else:
            # Old flat structure - try to match by loading task files
            for filename, task_id in manifest.items():
                if isinstance(task_id, str) and filename.endswith('.json'):
                    task_file = project_root / "tasks" / filename
                    if task_file.exists():
                        try:
                            with open(task_file, 'r') as tf:
                                task_def = json.load(tf)
                                if task_def.get('name') == task_name:
                                    return task_id
                        except:
                            pass
        
        log("warning", f"Task '{task_name}' not found in manifest for environment '{environment}'")
        log("debug", f"Available environments in manifest: {list(manifest.keys()) if isinstance(manifest, dict) else 'N/A'}")
        if isinstance(manifest, dict) and environment in manifest:
            log("debug", f"Available tasks in '{environment}': {list(manifest[environment].keys())}")
        return None
    except Exception as e:
        log("error", f"Error reading task manifest: {e}")
        return None

def get_task_id_by_filename(task_filename: str, environment: Optional[str] = None) -> Optional[str]:
    """
    Looks up a task ID by task filename (e.g., 'discovery_task.json') from the task manifest.
    If environment is not provided, detects it automatically.
    Returns None if not found.
    """
    if environment is None:
        environment = detect_environment()
    
    project_root = Path(__file__).resolve().parent.parent
    manifest_path = project_root / "tasks" / "task_manifest.json"
    
    if not manifest_path.exists():
        log("error", f"Task manifest not found at {manifest_path}")
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check if manifest has new structure with environments
        if isinstance(manifest, dict) and (environment in manifest or 'staging' in manifest or 'production' in manifest):
            env_section = manifest.get(environment, {})
            task_data = env_section.get(task_filename)
            if isinstance(task_data, dict):
                return task_data.get('id')
            elif isinstance(task_data, str):
                return task_data
        else:
            # Old flat structure
            return manifest.get(task_filename)
        
        return None
    except Exception as e:
        log("error", f"Error reading task manifest: {e}")
        return None

def get_model_id_by_name(model_name: str, environment: Optional[str] = None) -> Optional[str]:
    """
    Looks up a model ID by model name from the model manifest.
    If environment is not provided, detects it automatically.
    Returns None if not found.
    """
    if environment is None:
        environment = detect_environment()
    
    project_root = Path(__file__).resolve().parent.parent
    manifest_path = project_root / "config" / "model_manifest.json"
    
    if not manifest_path.exists():
        log("error", f"Model manifest not found at {manifest_path}")
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check if manifest has new structure with environments
        if isinstance(manifest, dict) and (environment in manifest or 'staging' in manifest or 'production' in manifest):
            env_section = manifest.get(environment, {})
            return env_section.get(model_name)
        else:
            # Old flat structure
            models = manifest.get('models', {})
            if isinstance(models, dict):
                return models.get(model_name)
            return None
    except Exception as e:
        log("error", f"Error reading model manifest: {e}")
        return None

def get_task(rb_token: str, task_id: str) -> Dict[str, Any]:
    url = f"{get_api_root()}{get_project_path()}/task/{task_id}"
    try:
        response = requests.get(url, headers=_get_api_headers(rb_token))
        if response.status_code == 404:
            return {"error": "Task not found", "is_error": True}
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def update_task(rb_token: str, task_id: str, update_payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{get_api_root()}{get_project_path()}/task/{task_id}"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=update_payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": "API Error", "details": str(e), "is_error": True}

def create_task(rb_token: str, task_body: Dict[str, Any]) -> Optional[str]:
    url = f"{get_api_root()}{get_project_path()}/task"
    try:
        response = requests.post(url, headers=_get_api_headers(rb_token), json=task_body)
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        log("error", f"FAILED to create task '{task_body.get('name')}'", details=str(e))
        return None

def run_rb_task(rb_token: str, task_id: str, task_input_payload: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    # Ensure config is loaded/valid
    get_rb_config()
    
    if not task_id:
        log("error", f"Missing configuration for {task_name}")
        return {"error": "Missing configuration", "is_error": True}

    run_url = f"{get_api_root()}{get_project_path()}/task/{task_id}/run"
    
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