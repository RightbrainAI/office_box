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
from utils.rightbrain_api import get_rb_token

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
        print(f"ℹ️ No manifest file found at {manifest_path}. Will create one.")
        return {}
    
    with open(manifest_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            sys.exit(f"❌ Error: Manifest file at {manifest_path} is corrupted.")

def update_task_manifest(manifest_path: Path, manifest_data: Dict, task_filename: str, task_id: str):
    """Saves the new task_id to the manifest file."""
    # Update the manifest data
    manifest_data[task_filename] = task_id
    
    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        print(f"✅ Successfully updated manifest: '{task_filename}' -> '{task_id}'")
    except IOError as e:
        print(f"❌ Error writing to manifest file {manifest_path}: {e}")

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
    
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    rb_token_url = rb_oauth2_url

    # --- 2. Load Task Def and Manifest ---
    manifest_path = get_manifest_path()
    manifest_data = load_task_manifest(manifest_path)
    
    with open(task_def_path, 'r') as f:
        try:
            task_payload = json.load(f)
        except json.JSONDecodeError:
            sys.exit(f"❌ Error: Task definition file {task_filename} is not valid JSON.")
            
    # Check manifest for existing ID for this filename
    existing_task_id = manifest_data.get(task_filename)
    
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
            print(f"✅ Step 1: Task '{task_filename}' updated successfully.")

            # --- STEP 2: Find the new revision and set it as active ---
            revisions = response_data.get("revisions", [])
            if not revisions:
                print("⚠️ Warning: Task was updated, but no revisions were found in the response.")
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
                print("✅ Step 2: New revision set to active.")

        else:
            # --- CREATE (POST) ---
            print(f"No existing ID found for '{task_filename}'. Attempting to CREATE task...")
            # Per API docs, Create Task uses a POST request
            # API URL should already include /api/v1
            url = f"{rb_api_url.rstrip('/')}/org/{rb_org_id}/project/{rb_project_id}/task"
            response = requests.post(url, headers=headers, json=task_payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            print(f"✅ Task '{task_filename}' created successfully (new tasks are active by default).")

    except requests.exceptions.RequestException as e:
        print(f"❌ Rightbrain API call failed: {e}")
        if e.response is not None:
            print(f"Response Body: {e.response.text}")
        sys.exit(1)

    # --- 4. Write New ID back to Manifest ---
    new_task_id = response_data.get("id")
    
    if not new_task_id:
        print(f"❌ Error: API response did not contain a task 'id'.\n{response_data}")
        sys.exit(1)
        
    if new_task_id != existing_task_id:
        print(f"Task ID retrieved: {new_task_id}")
        update_task_manifest(manifest_path, manifest_data, task_filename, new_task_id)
    else:
        print("Task ID is unchanged. Manifest is already up-to-date.")

if __name__ == "__main__":
    main()