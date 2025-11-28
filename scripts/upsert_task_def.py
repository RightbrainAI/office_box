import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
from datetime import datetime, timezone

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))
from utils.rightbrain_api import get_rb_token, log, detect_environment, _get_base_url, get_model_id_by_name

# --- Manifest Helper Functions ---

def get_manifest_path() -> Path:
    """Gets the absolute path to the task_manifest.json file."""
    try:
        # Assumes this script is in /scripts
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    except NameError:
        # Fallback for interactive use
        project_root = Path.cwd()
        
    return project_root / "tasks" / "task_manifest.json"

def load_task_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Loads the task manifest file from its path."""
    if not manifest_path.exists():
        log("info", f"No manifest file found at {manifest_path}. Will create one.")
        return {}
    
    with open(manifest_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            sys.exit(f"❌ Error: Manifest file at {manifest_path} is corrupted.")

def update_task_manifest(manifest_path: Path, manifest_data: Dict, task_filename: str, task_id: str, task_name: str, environment: str):
    """Saves the new task_id to the manifest file for the specified environment."""
    # Initialize manifest structure if needed
    if not isinstance(manifest_data, dict) or 'production' not in manifest_data:
        manifest_data = {
            "production": manifest_data if manifest_data and not any(k in manifest_data for k in ['production', 'staging']) else {},
            "staging": {}
        }
    if 'staging' not in manifest_data:
        manifest_data['staging'] = {}
    
    # Update the manifest data for this environment
    if environment not in manifest_data:
        manifest_data[environment] = {}
    
    manifest_data[environment][task_filename] = {
        "name": task_name,
        "id": task_id
    }
    
    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        log("success", f"Successfully updated manifest: '{task_filename}' -> '{task_id}' for {environment} environment")
    except IOError as e:
        log("error", f"Failed to write to manifest file {manifest_path}", details=str(e))

# --- Main Upsert Logic ---

def main():
    # --- 1. Load Config & Arguments ---
    load_dotenv()
    
    try:
        task_filename = sys.argv[1]
    except IndexError:
        sys.exit(f"❌ Error: Please provide the task filename to upsert.\nUsage: python {sys.argv[0]} my_task_def.json")

    # Construct the full path to the task definition
    try:
        task_def_path = (Path(__file__).parent.parent / "tasks" / task_filename).resolve()
    except NameError:
        task_def_path = (Path.cwd() / "tasks" / task_filename).resolve()
        
    if not task_def_path.exists():
        sys.exit(f"❌ Error: Task definition file not found at {task_def_path}")

    # Load RB environment variables
    rb_org_id = os.environ["RB_ORG_ID"]
    rb_project_id = os.environ["RB_PROJECT_ID"]
    rb_client_id = os.environ["RB_CLIENT_ID"]
    rb_client_secret = os.environ["RB_CLIENT_SECRET"] 
    rb_api_url = os.environ.get("RB_API_URL") # This should already include /api/v1
    rb_oauth2_url = os.environ.get("RB_OAUTH2_URL")
    
    if not rb_api_url or not rb_oauth2_url:
        sys.exit("❌ Error: Missing RB_API_URL or RB_OAUTH2_URL environment variable.")
    
    # Determine environment
    rb_api_root = rb_api_url.rstrip('/')
    if not rb_api_root.endswith('/api/v1'):
        rb_api_root = f"{rb_api_root}/api/v1"
    
    original_api_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root
    environment = detect_environment()
    if original_api_root:
        os.environ["API_ROOT"] = original_api_root
    elif "API_ROOT" in os.environ:
        del os.environ["API_ROOT"]
    
    log("info", f"Detected environment: {environment}")

    # --- 2. Load Task Def and Manifest ---
    manifest_path = get_manifest_path()
    manifest_data = load_task_manifest(manifest_path)
    
    # Initialize manifest structure if needed
    if not isinstance(manifest_data, dict) or 'production' not in manifest_data:
        manifest_data = {
            "production": manifest_data if manifest_data and not any(k in manifest_data for k in ['production', 'staging']) else {},
            "staging": {}
        }
    if 'staging' not in manifest_data:
        manifest_data['staging'] = {}
    
    with open(task_def_path, 'r') as f:
        try:
            task_payload = json.load(f)
        except json.JSONDecodeError:
            sys.exit(f"❌ Error: Task definition file {task_filename} is not valid JSON.")
    
    # Resolve model name to model ID if needed
    if "llm_model_name" in task_payload:
        model_name = task_payload.get("llm_model_name")
        model_id = get_model_id_by_name(model_name, environment)
        if model_id:
            # Replace llm_model_name with llm_model_id for API
            task_payload["llm_model_id"] = model_id
            del task_payload["llm_model_name"]
            log("info", f"Resolved model '{model_name}' to ID '{model_id}' for environment '{environment}'")
        else:
            log("error", f"Could not find model ID for '{model_name}' in {environment} environment. Task will be updated without model.")
            # Remove llm_model_name so API doesn't get confused
            del task_payload["llm_model_name"]
    elif "llm_model_id" in task_payload:
        # Already has ID, keep it as is
        log("debug", f"Task already has llm_model_id, using as-is")
    
    task_name = task_payload.get("name", "Unnamed Task")
            
    # Check manifest for existing ID for this filename in this environment
    env_section = manifest_data.get(environment, {})
    existing_task_data = env_section.get(task_filename)
    existing_task_id = existing_task_data.get("id") if isinstance(existing_task_data, dict) else (existing_task_data if isinstance(existing_task_data, str) else None)
    
    # --- 3. Get Auth Token ---
    rb_token = get_rb_token()
    headers = {"Authorization": f"Bearer {rb_token}", "Content-Type": "application/json"}

    response_data = {}
    
    try:
        if existing_task_id:
            # --- UPDATE (POST) ---
            print(f"Found existing ID: {existing_task_id}. Attempting to UPDATE task...")
            
            # --- STEP 1: Create the new revision ---
            # Per API docs, Update Task uses a POST request
            # API URL should already include /api/v1
            url = f"{rb_api_url.rstrip('/')}/org/{rb_org_id}/project/{rb_project_id}/task/{existing_task_id}"
            response = requests.post(url, headers=headers, json=task_payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            log("success", f"Step 1: Task '{task_filename}' updated successfully.")

            # --- STEP 2: Find the new revision and set it as active ---
            revisions = response_data.get("revisions", [])
            if not revisions:
                log("warning", "Task was updated, but no revisions were found in the response.")
            else:
                # Sort revisions by 'created' timestamp to find the newest one
                revisions.sort(key=lambda r: datetime.fromisoformat(r['created']), reverse=True)
                newest_revision_id = revisions[0]['id']
                print(f"Found new revision ID: {newest_revision_id}")
                
                # Now, make the second call to set it active
                active_payload = {
                    "active_revisions": [
                        {"task_revision_id": newest_revision_id, "weight": 1.0}
                    ]
                }
                print("Running Step 2: Setting new revision as active...")
                response = requests.post(url, headers=headers, json=active_payload, timeout=30)
                response.raise_for_status()
                response_data = response.json() # Store the final response from this call
                log("success", "Step 2: New revision set to active.")

        else:
            # --- CREATE (POST) ---
            print(f"No existing ID found for '{task_filename}'. Attempting to CREATE task...")
            # Per API docs, Create Task uses a POST request
            # API URL should already include /api/v1
            url = f"{rb_api_url.rstrip('/')}/org/{rb_org_id}/project/{rb_project_id}/task"
            response = requests.post(url, headers=headers, json=task_payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            log("success", f"Task '{task_filename}' created successfully (new tasks are active by default).")

    except requests.exceptions.RequestException as e:
        log("error", "Rightbrain API call failed", details=str(e))
        if e.response is not None:
            print(f"Response Body: {e.response.text}")
        sys.exit(1)

    # --- 4. Write New ID back to Manifest ---
    new_task_id = response_data.get("id")
    
    if not new_task_id:
        log("error", "API response did not contain a task 'id'", details=str(response_data))
        sys.exit(1)
        
    if new_task_id != existing_task_id:
        print(f"Task ID retrieved: {new_task_id}")
        update_task_manifest(manifest_path, manifest_data, task_filename, new_task_id, task_name, environment)
    else:
        print("Task ID is unchanged. Manifest is already up-to-date.")

if __name__ == "__main__":
    main()