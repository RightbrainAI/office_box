import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any

# --- 0. Determine project root and load .env file if it exists (for local development) ---
project_root = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# --- 1. Fix Import Path for 'utils' ---
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.rightbrain_api import get_rb_token, load_rb_config, log
except ImportError as e:
    print(f"❌ Error importing 'utils.rightbrain_api': {e}", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
TASK_TEMPLATE_DIR = project_root / "tasks"
TASK_MANIFEST_PATH = project_root / "tasks/task_manifest.json"

def create_rb_task(rb_token: str, api_root: str, org_id: str, project_id: str, task_body: Dict[str, Any]) -> str:
    """Creates a single Rightbrain task and returns its new ID."""
    task_name = task_body.get("name", "Unnamed Task")
    
    # API_ROOT already includes /api/v1, so just append the path
    base = api_root.rstrip('/')
    create_url = f"{base}/org/{org_id}/project/{project_id}/task"

    headers = {
        "Authorization": f"Bearer {rb_token}", 
        "Content-Type": "application/json"
    }
    
    log("info", f"Attempting to create task: '{task_name}'...")
    
    try:
        response = requests.post(create_url, headers=headers, json=task_body)
        
        if not response.ok:
            log("error", f"Error creating task '{task_name}' (Status: {response.status_code})", details=response.text[:200])
            return None
            
        task_id = response.json().get("id")
        log("success", f"Successfully created task '{task_name}'", details=f"ID: {task_id}")
        return task_id

    except requests.exceptions.RequestException as e:
        log("error", f"Connection error creating task '{task_name}'", details=str(e))
        return None

def main():
    log("info", "Starting Rightbrain Task Setup Script...")
    log("debug", f"Project Root detected as: {project_root}")

    # 1. Load configuration
    log("info", "Loading configuration...")
    try:
        config = load_rb_config()
        # Use API_ROOT from env var first, then fallback to constructing from config
        rb_api_root = os.environ.get("API_ROOT")
        if not rb_api_root:
            # Fallback: construct from config file
            api_url = config.get("api_url") or "https://app.rightbrain.ai"
            api_url = api_url.rstrip('/')
            # If config doesn't include /api/v1, add it
            if not api_url.endswith('/api/v1'):
                rb_api_root = f"{api_url}/api/v1"
            else:
                rb_api_root = api_url
        
        log("debug", f"Using API_ROOT: {rb_api_root}")
    except Exception as e:
        log("error", f"Configuration Error: {e}")
        sys.exit(1)

    # 2. Load Secrets
    rb_org_id = os.environ.get("RB_ORG_ID")
    rb_project_id = os.environ.get("RB_PROJECT_ID")
    rb_client_id = os.environ.get("RB_CLIENT_ID")
    rb_client_secret = os.environ.get("RB_CLIENT_SECRET")

    if not all([rb_org_id, rb_project_id, rb_client_id, rb_client_secret]):
        log("error", "Missing required secrets.", details="Requires: RB_ORG_ID, RB_PROJECT_ID, RB_CLIENT_ID, RB_CLIENT_SECRET")
        sys.exit(1)

    # 3. Authenticate
    try:
        rb_token = get_rb_token()
    except Exception as e:
        log("error", f"Authentication failed: {e}")
        sys.exit(1)
    
    # 4. Find templates
    log("info", f"Looking for task templates in '{TASK_TEMPLATE_DIR}'...")
    if not TASK_TEMPLATE_DIR.is_dir():
        log("error", f"Task template directory not found at '{TASK_TEMPLATE_DIR}'")
        sys.exit(1)
        
    task_files = list(TASK_TEMPLATE_DIR.glob("*.json"))
    if not task_files:
        log("error", f"No .json task templates found in '{TASK_TEMPLATE_DIR}'")
        sys.exit(1)
        
    log("info", f"Found {len(task_files)} task templates.")
    
    # 5. Create tasks
    task_manifest = {}
    log("info", "Creating tasks in Rightbrain project...")
    
    for task_file_path in task_files:
        try:
            with open(task_file_path, 'r') as f:
                task_body = json.load(f)
        except json.JSONDecodeError:
            log("warning", f"Could not parse '{task_file_path}'. Skipping.")
            continue
            
        task_id = create_rb_task(rb_token, rb_api_root, rb_org_id, rb_project_id, task_body)
        
        if task_id:
            task_manifest[task_file_path.name] = task_id

    if not task_manifest:
        log("error", "No tasks were successfully created. Aborting.")
        sys.exit(1)

    # 6. Write manifest
    log("info", f"Writing new task manifest to '{TASK_MANIFEST_PATH}'...")
    try:
        TASK_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASK_MANIFEST_PATH, 'w') as f:
            json.dump(task_manifest, f, indent=2)
        log("success", "Task manifest created successfully.")
    except IOError as e:
        log("error", f"Error writing manifest file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()