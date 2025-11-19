import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any

# --- 1. Fix Import Path for 'utils' ---
# Get the project root directory (two levels up from this script)
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.rightbrain_api import get_rb_token
except ImportError as e:
    print(f"❌ Error importing 'utils.rightbrain_api': {e}", file=sys.stderr)
    print(f"   Current sys.path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
TASK_TEMPLATE_DIR = project_root / "task_templates"
TASK_MANIFEST_PATH = project_root / "tasks/task_manifest.json"

def create_rb_task(rb_token: str, api_url_base: str, org_id: str, project_id: str, task_body: Dict[str, Any]) -> str:
    """Creates a single Rightbrain task and returns its new ID."""
    task_name = task_body.get("name", "Unnamed Task")
    
    # Intelligent URL construction: check if api_url_base already contains /api/v1
    base = api_url_base.rstrip('/')
    if base.endswith("/api/v1"):
        # If base has /api/v1, strip it so we can build the full path correctly if needed, 
        # OR just append the rest. The safest way with the provided vars is usually:
        create_url = f"{base}/org/{org_id}/project/{project_id}/task"
    else:
        create_url = f"{base}/api/v1/org/{org_id}/project/{project_id}/task"

    headers = {
        "Authorization": f"Bearer {rb_token}", 
        "Content-Type": "application/json"
    }
    
    print(f"  Attempting to create task: '{task_name}'...")
    
    try:
        response = requests.post(create_url, headers=headers, json=task_body)
        
        if not response.ok:
            print(f"  ❌ Error creating task '{task_name}' (Status: {response.status_code})", file=sys.stderr)
            try:
                print(f"  Response: {response.json()}", file=sys.stderr)
            except:
                print(f"  Response: {response.text}", file=sys.stderr)
            return None
            
        task_id = response.json().get("id")
        if not task_id:
            raise ValueError(f"Task creation for '{task_name}' did not return an ID.")
            
        print(f"  ✅ Successfully created task '{task_name}' with ID: {task_id}")
        return task_id

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Connection error creating task '{task_name}': {e}", file=sys.stderr)
        return None

# --- Main Setup Function ---

def main():
    print("🚀 Starting Rightbrain Task Setup Script...")
    print(f"📂 Project Root detected as: {project_root}")

    # 1. Load configuration from GitHub Actions environment variables
    print("Loading configuration from environment variables...")
    rb_org_id = os.environ.get("RB_ORG_ID")
    rb_project_id = os.environ.get("RB_PROJECT_ID")
    rb_client_id = os.environ.get("RB_CLIENT_ID")
    rb_client_secret = os.environ.get("RB_CLIENT_SECRET")
    
    rb_oauth2_url = os.environ.get("RB_OAUTH2_URL", "https://oauth.rightbrain.ai")
    rb_api_url = os.environ.get("RB_API_URL", "https://app.rightbrain.ai")

    if not all([rb_org_id, rb_project_id, rb_client_id, rb_client_secret]):
        print("❌ Error: Missing one or more required environment variables.", file=sys.stderr)
        print("  Requires: RB_ORG_ID, RB_PROJECT_ID, RB_CLIENT_ID, RB_CLIENT_SECRET", file=sys.stderr)
        sys.exit(1)
        
    print(f"  Org ID: {rb_org_id}")
    print(f"  Project ID: {rb_project_id}")
    print(f"  Auth Base URL: {rb_oauth2_url}")
    print(f"  API Base URL: {rb_api_url}")

    # 2. Authenticate with Rightbrain (using shared utility)
    try:
        rb_token = get_rb_token()
    except Exception as e:
        print(f"❌ Authentication failed in main script: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 3. Find and load all task templates
    print(f"Looking for task templates in '{TASK_TEMPLATE_DIR}'...")
    if not TASK_TEMPLATE_DIR.is_dir():
        print(f"❌ Error: Task template directory not found at '{TASK_TEMPLATE_DIR}'", file=sys.stderr)
        # Try printing contents of root to help debug
        print(f"Contents of root ({project_root}):", file=sys.stderr)
        for item in project_root.iterdir():
            print(f" - {item}", file=sys.stderr)
        sys.exit(1)
        
    task_files = list(TASK_TEMPLATE_DIR.glob("*.json"))
    if not task_files:
        print(f"❌ Error: No .json task templates found in '{TASK_TEMPLATE_DIR}'", file=sys.stderr)
        sys.exit(1)
        
    print(f"Found {len(task_files)} task templates.")
    
    # 4. Create tasks and build the manifest
    task_manifest = {}
    print("Creating tasks in Rightbrain project...")
    
    for task_file_path in task_files:
        try:
            with open(task_file_path, 'r') as f:
                task_body = json.load(f)
        except json.JSONDecodeError:
            print(f"  ⚠️ Warning: Could not parse '{task_file_path}'. Skipping.", file=sys.stderr)
            continue
            
        task_id = create_rb_task(rb_token, rb_api_url, rb_org_id, rb_project_id, task_body)
        
        if task_id:
            # The key is the *filename* (e.g., "discovery_task.json")
            # The value is the *newly created ID*
            task_manifest[task_file_path.name] = task_id

    if not task_manifest:
        print("❌ Error: No tasks were successfully created. Aborting.", file=sys.stderr)
        sys.exit(1)

    # 5. Write the task manifest file
    print(f"Writing new task manifest to '{TASK_MANIFEST_PATH}'...")
    try:
        TASK_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASK_MANIFEST_PATH, 'w') as f:
            json.dump(task_manifest, f, indent=2)
        print("✅ Task manifest created successfully.")
    except IOError as e:
        print(f"❌ Error writing manifest file: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n🎉 Rightbrain setup complete!")
    print(f"The '{TASK_MANIFEST_PATH}' file has been created (or updated) and must be committed to your repository.")

if __name__ == "__main__":
    main()