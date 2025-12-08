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
    pass

# --- Centralized Logging ---

def log(
    level: Literal["success", "error", "info", "warning", "debug"],
    message: str,
    details: Optional[str] = None,
    to_stderr: bool = False
) -> None:
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
    try:
        root_dir = Path(__file__).resolve().parent.parent
        config_path = root_dir / "config/rightbrain.config.json"
        if not config_path.exists():
            return {}
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log("error", f"Failed to load config file: {e}")
        sys.exit(1)

# --- API Functions ---

_token_cache: Optional[tuple[str, float]] = None

def get_rb_token() -> str:
    global _token_cache
    if _token_cache is not None:
        cached_token, expiry_time = _token_cache
        if time.time() < (expiry_time - 60):
            log("debug", f"Using cached token (expires in {int(expiry_time - time.time())}s)")
            log("debug", f"Token preview: {cached_token[:20]}...{cached_token[-10:] if len(cached_token) > 30 else ''}")
            return cached_token

    log("debug", "Fetching new authentication token...")
    config = load_rb_config()
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        log("error", "Missing RB_CLIENT_ID or RB_CLIENT_SECRET env vars.")
        sys.exit(1)

    log("debug", f"Client ID: {client_id[:8]}...{client_id[-4:] if len(client_id) > 12 else ''} (length: {len(client_id)})")
    log("debug", f"Client Secret: {'*' * min(20, len(client_secret))} (length: {len(client_secret)})")

    # Priority 1: Explicit TOKEN_URI (full URL to token endpoint)
    token_url = os.environ.get("TOKEN_URI")
    
    # Priority 2: AUTH_URI (convert /oauth2/auth to /oauth2/token if needed)
    if not token_url:
        auth_uri = os.environ.get("AUTH_URI")
        if auth_uri:
            # Convert /oauth2/auth to /oauth2/token if present
            auth_uri = auth_uri.rstrip('/')
            if auth_uri.endswith('/oauth2/auth'):
                token_url = auth_uri.replace('/oauth2/auth', '/oauth2/token')
            elif '/oauth2/token' in auth_uri:
                token_url = auth_uri
            else:
                # If path not specified, append /oauth2/token
                token_url = f"{auth_uri}/oauth2/token"
            log("debug", f"Using AUTH_URI from environment: {token_url}")
    
    # Priority 3: RB_OAUTH2_URL (base URL, construct full path)
    if not token_url:
        oauth2_url = os.environ.get("RB_OAUTH2_URL")
        oauth2_token_path = os.environ.get("RB_OAUTH2_TOKEN_PATH") or os.environ.get("RB_OAUTH2_AUTH_PATH")
        
        if oauth2_url:
            base = oauth2_url.rstrip('/')
            path = (oauth2_token_path or "/oauth2/token").lstrip('/')
            token_url = f"{base}/{path}"
            log("debug", f"Using RB_OAUTH2_URL from environment: {token_url}")
    
    # Priority 4: Auto-detect from environment (only if no explicit env vars set)
    if not token_url:
        # Use known OAuth URLs based on detected environment
        environment = detect_environment()
        
        if environment == 'staging':
            # Known staging OAuth URL
            base = "https://oauth.leftbrain.me"
        else:
            # Production - use config or default
            base = config.get("oauth_url") or "https://oauth.rightbrain.ai"
        
        path = config.get("auth_path") or "/oauth2/token"
        token_url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        log("debug", f"Environment detected: {environment}, using OAuth URL: {base}")

    log("debug", f"Token URL: {token_url}")

    try:
        log("debug", "Sending token request...")
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials", "scope": "offline_access"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        log("debug", f"Token response status: {response.status_code}")
        
        if not response.ok:
            log("error", f"Auth failed ({response.status_code})", details=response.text[:200])
            sys.exit(1)

        response_data = response.json()
        token = response_data.get("access_token")
        if not token:
            log("error", "No access_token in response", details=str(response_data)[:200])
            sys.exit(1)
        
        expires_in = response_data.get("expires_in", 3600)
        _token_cache = (token, time.time() + expires_in)
        log("success", f"Token obtained successfully (expires in {expires_in}s)")
        log("debug", f"Token preview: {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
        log("debug", f"Token length: {len(token)} characters")
        return token
    except Exception as e:
        log("error", f"Auth connection error: {e}")
        sys.exit(1)

def _get_api_headers(rb_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

def get_api_root() -> str:
    # Priority 1: API_ROOT env var
    api_root = os.environ.get("API_ROOT")
    if api_root:
        api_root = api_root.rstrip('/')
        return api_root if api_root.endswith('/api/v1') else f"{api_root}/api/v1"
    
    # Priority 2: RB_API_URL env var
    rb_api_url = os.environ.get("RB_API_URL")
    if rb_api_url:
        rb_api_url = rb_api_url.rstrip('/')
        return rb_api_url if rb_api_url.endswith('/api/v1') else f"{rb_api_url}/api/v1"
    
    # Priority 3: Config file or default
    config = load_rb_config()
    api_url = config.get("api_url") or "https://app.rightbrain.ai"
    api_url = api_url.rstrip('/')
    return api_url if api_url.endswith('/api/v1') else f"{api_url}/api/v1"

def get_rb_config() -> Dict[str, str]:
    org_id = os.environ.get("RB_ORG_ID")
    project_id = os.environ.get("RB_PROJECT_ID")
    client_id = os.environ.get("RB_CLIENT_ID")
    client_secret = os.environ.get("RB_CLIENT_SECRET")
    
    log("debug", f"Config check - Org ID: {org_id[:8] if org_id and len(org_id) > 8 else org_id}...")
    log("debug", f"Config check - Project ID: {project_id[:8] if project_id and len(project_id) > 8 else project_id}...")
    log("debug", f"Config check - Client ID: {'present' if client_id else 'missing'}")
    log("debug", f"Config check - Client Secret: {'present' if client_secret else 'missing'}")
    
    if not all([org_id, project_id, client_id, client_secret]):
        log("error", "Missing required secrets (RB_ORG_ID, RB_PROJECT_ID, RB_CLIENT_ID, RB_CLIENT_SECRET).")
        sys.exit(1)
    return {"org_id": org_id, "project_id": project_id, "client_id": client_id, "client_secret": client_secret}

def get_project_path() -> str:
    config = get_rb_config()
    return f"/org/{config['org_id']}/project/{config['project_id']}"

def detect_environment() -> str:
    # Priority 1: Explicit Env Var
    explicit = os.environ.get("RIGHTBRAIN_ENVIRONMENT") or os.environ.get("RB_ENVIRONMENT")
    if explicit:
        env = explicit.lower().strip()
        log("debug", f"Environment detected from env var: {env}")
        return env
    
    # Priority 2: API URL Inspection
    api_root = get_api_root().lower()
    log("debug", f"Detecting environment from API root: {api_root}")
    if any(k in api_root for k in ['staging', 'dev', 'test', 'sandbox', 'stag']):
        log("debug", "Environment detected as: staging (from API URL)")
        return 'staging'
    log("debug", "Environment detected as: production (default)")
    return 'production'

# --- DYNAMIC TASK RESOLUTION ---

def fetch_remote_tasks_map(rb_token: str) -> Dict[str, str]:
    """
    Fetches ALL tasks from the API and builds a {task_name: task_id} map.
    This acts as the source of truth if local manifest fails.
    """
    url = f"{get_api_root()}{get_project_path()}/task"
    try:
        log("debug", "Fetching remote task list for dynamic resolution...")
        response = requests.get(url, headers=_get_api_headers(rb_token))
        response.raise_for_status()
        tasks = response.json()
        
        # Build map: {"Document Discovery Task": "uuid-...", ...}
        task_map = {t.get("name"): t.get("id") for t in tasks if t.get("name") and t.get("id")}
        log("debug", f"Fetched {len(task_map)} tasks from remote API.")
        return task_map
    except Exception as e:
        log("warning", f"Could not fetch remote task list: {e}")
        return {}

def get_task_id_by_name(task_name: str, environment: Optional[str] = None) -> Optional[str]:
    """
    1. Tries local manifest based on environment.
    2. If not found or if environment seems wrong, fetches from API (Dynamic Resolution).
    """
    if environment is None:
        environment = detect_environment()

    # --- ATTEMPT 1: Local Manifest ---
    log("debug", f"Resolving '{task_name}' for environment '{environment}' via Manifest...")
    project_root = Path(__file__).resolve().parent.parent
    manifest_path = project_root / "tasks" / "task_manifest.json"
    local_id = None
    
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Handle Nested Manifest (staging/production keys)
            if isinstance(manifest, dict) and environment in manifest:
                env_section = manifest[environment]
                for key, val in env_section.items():
                    # Handle val as dict {name:..., id:...} or string ID
                    if isinstance(val, dict) and val.get('name') == task_name:
                        local_id = val.get('id')
                        break
            
            if local_id:
                log("debug", f"Found ID in manifest: {local_id}")
                return local_id
        except Exception as e:
            log("warning", f"Manifest read failed: {e}")

    # --- ATTEMPT 2: Dynamic Resolution (Self-Healing) ---
    # If we are here, either the manifest is missing, the task is missing in manifest,
    # or the manifest ID is wrong/outdated. Let's ask the API directly.
    log("info", f"Task '{task_name}' not found in local manifest for {environment}. Attempting remote fetch...")
    
    try:
        # We need a token to fetch tasks
        token = get_rb_token()
        remote_map = fetch_remote_tasks_map(token)
        remote_id = remote_map.get(task_name)
        
        if remote_id:
            log("success", f"Resolved '{task_name}' via API to ID: {remote_id}")
            return remote_id
        else:
            log("error", f"Task '{task_name}' does not exist in the remote project.")
            return None
    except Exception as e:
        log("error", f"Remote resolution failed: {e}")
        return None

# --- Existing wrappers (mostly unchanged) ---

def run_rb_task(rb_token: str, task_id: str, task_input_payload: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    get_rb_config() # Validate config exists
    
    if not task_id:
        log("error", f"Cannot run {task_name}: No Task ID provided.")
        return {"error": "Missing Task ID", "is_error": True}

    if not rb_token:
        log("error", f"Cannot run {task_name}: No token provided.")
        return {"error": "Missing token", "is_error": True}

    run_url = f"{get_api_root()}{get_project_path()}/task/{task_id}/run"
    
    # Debug logging
    log("debug", f"API Root: {get_api_root()}")
    log("debug", f"Project Path: {get_project_path()}")
    log("debug", f"Full Run URL: {run_url}")
    log("debug", f"Token preview: {rb_token[:20]}...{rb_token[-10:] if len(rb_token) > 30 else ''}")
    log("debug", f"Token length: {len(rb_token)} characters")
    
    # Redact sensitive data for logging
    logged_input = task_input_payload.copy()
    if 'document_text' in logged_input:
        logged_input['document_text'] = f"<Redacted text len={len(logged_input['document_text'])}>"
        
    log("info", f"Running {task_name} (ID: {task_id})", details=f"Input keys: {list(logged_input.keys())}")
    
    try:
        headers = _get_api_headers(rb_token)
        log("debug", f"Request headers: Authorization=Bearer ***, Content-Type={headers.get('Content-Type')}")
        
        response = requests.post(
            run_url, 
            headers=headers, 
            json={"task_input": task_input_payload}, 
            timeout=600
        )
        
        log("debug", f"Response status: {response.status_code}")
        log("debug", f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 404:
             # This catches the exact error you are seeing
             log("error", f"404 Not Found: The Task ID {task_id} does not exist in this environment.")
             log("debug", f"Response body: {response.text[:500]}")
             return {"error": "Task ID not found in environment", "is_error": True}
        
        if response.status_code == 403:
            log("error", f"403 Forbidden: Access denied for Task ID {task_id}")
            log("error", f"This usually means:")
            log("error", f"  1. Token is invalid or expired")
            log("error", f"  2. Token doesn't have permissions for this project/task")
            log("error", f"  3. Token is for a different environment than the API endpoint")
            log("error", f"  4. Task ID belongs to a different project/org")
            log("debug", f"Response body: {response.text[:500]}")
            log("debug", f"API Root: {get_api_root()}")
            log("debug", f"Environment detected: {detect_environment()}")
            return {"error": "403 Forbidden - Access denied", "is_error": True, "response": response.text[:200]}
             
        response.raise_for_status()
        log("success", f"{task_name} complete.")
        return response.json()
    except requests.exceptions.HTTPError as e:
        log("error", f"{task_name} failed with HTTP error", details=str(e))
        if hasattr(e.response, 'text'):
            log("error", f"Response body: {e.response.text[:500]}")
        return {"error": str(e), "is_error": True}
    except Exception as e:
        log("error", f"{task_name} failed", details=str(e))
        return {"error": str(e), "is_error": True}

# Stub function for compatibility
def update_issue_body(repo, issue, body, new_content):
    pass