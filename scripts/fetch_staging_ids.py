import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

# --- Fix Import Path for 'utils' ---
# Use absolute path resolution to ensure we get the correct project root
# regardless of where the script is run from
_script_file = Path(__file__).resolve()
project_root = _script_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.rightbrain_api import get_rb_token, log, load_rb_config, _get_base_url
except ImportError as e:
    print(f"❌ Error importing 'utils.rightbrain_api': {e}", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
# Use absolute paths to ensure consistency regardless of working directory
TASK_TEMPLATE_DIR = (project_root / "tasks").resolve()
TASK_MANIFEST_PATH = (project_root / "tasks" / "task_manifest.json").resolve()

def get_all_tasks(rb_token: str, api_root: str, org_id: str, project_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all tasks from the Rightbrain API.
    Returns a list of task objects with 'id' and 'name' fields.
    """
    base = api_root.rstrip('/')
    tasks_url = f"{base}/org/{org_id}/project/{project_id}/task"
    
    headers = {"Authorization": f"Bearer {rb_token}"}
    
    log("info", f"Fetching tasks from {tasks_url}...")
    try:
        response = requests.get(tasks_url, headers=headers)
        response.raise_for_status()
        tasks_response = response.json()
        
        # Handle different response structures
        # The API might return:
        # 1. A list of task objects directly
        # 2. A paginated response with 'data' or 'tasks' key
        # 3. A list of task IDs (strings)
        
        if isinstance(tasks_response, list):
            # Check if it's a list of strings (IDs) or objects
            if tasks_response and isinstance(tasks_response[0], str):
                # It's a list of IDs, we need to fetch each task individually
                log("info", f"API returned list of IDs. Fetching details for {len(tasks_response)} tasks...")
                tasks_list = []
                for task_id in tasks_response:
                    task_url = f"{base}/org/{org_id}/project/{project_id}/task/{task_id}"
                    task_response = requests.get(task_url, headers=headers)
                    task_response.raise_for_status()
                    task_data = task_response.json()
                    tasks_list.append(task_data)
                log("success", f"Fetched details for {len(tasks_list)} tasks.")
                return tasks_list
            else:
                # It's a list of task objects
                log("success", f"Found {len(tasks_response)} tasks.")
                return tasks_response
        elif isinstance(tasks_response, dict):
            # Check for paginated response
            if 'data' in tasks_response:
                tasks_list = tasks_response['data']
                log("success", f"Found {len(tasks_list)} tasks in paginated response.")
                return tasks_list
            elif 'tasks' in tasks_response:
                tasks_list = tasks_response['tasks']
                log("success", f"Found {len(tasks_list)} tasks in response.")
                return tasks_list
            else:
                log("warning", f"Unexpected response structure: {list(tasks_response.keys())}")
                # Try to return the whole dict as a single-item list
                return [tasks_response]
        else:
            log("error", f"Unexpected response type: {type(tasks_response)}")
            return []
            
    except requests.exceptions.RequestException as e:
        log("error", "Failed to fetch tasks", 
            details=f"{e}\nResponse: {e.response.text if hasattr(e, 'response') and e.response else 'N/A'}")
        sys.exit(1)

def get_all_models(rb_token: str, api_root: str, org_id: str, project_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all models from the Rightbrain API.
    """
    base = api_root.rstrip('/')
    models_url = f"{base}/org/{org_id}/project/{project_id}/model"
    
    headers = {"Authorization": f"Bearer {rb_token}"}
    
    log("info", f"Fetching models from {models_url}...")
    try:
        response = requests.get(models_url, headers=headers)
        response.raise_for_status()
        models_list = response.json()
        log("success", f"Found {len(models_list)} models.")
        return models_list
    except requests.exceptions.RequestException as e:
        log("error", "Failed to fetch models", 
            details=f"{e}\nResponse: {e.response.text if hasattr(e, 'response') and e.response else 'N/A'}")
        sys.exit(1)

def update_task_manifest_staging(tasks_list: List[Dict[str, Any]]):
    """
    Updates the staging section of the task manifest by matching task names from API
    to task definition files.
    """
    log("debug", f"Updating task manifest at: {TASK_MANIFEST_PATH}")
    log("debug", f"Task template directory: {TASK_TEMPLATE_DIR}")
    log("debug", f"Task template directory exists: {TASK_TEMPLATE_DIR.exists()}")
    
    # Load existing manifest
    if TASK_MANIFEST_PATH.exists():
        try:
            with open(TASK_MANIFEST_PATH, 'r') as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError:
            log("warning", "Existing manifest is invalid JSON. Creating new one.")
            manifest_data = {}
    else:
        manifest_data = {}
    
    # Initialize manifest structure
    if not isinstance(manifest_data, dict) or 'production' not in manifest_data:
        manifest_data = {
            "production": manifest_data if manifest_data and not any(k in manifest_data for k in ['production', 'staging']) else {},
            "staging": {}
        }
    if 'staging' not in manifest_data:
        manifest_data['staging'] = {}
    
    # Load all task definition files to get their names
    task_files = list(TASK_TEMPLATE_DIR.glob("*.json"))
    log("debug", f"Found {len(task_files)} task definition files in {TASK_TEMPLATE_DIR}")
    task_defs = {}
    for task_file in task_files:
        try:
            with open(task_file, 'r') as f:
                task_def = json.load(f)
                task_name = task_def.get("name")
                if task_name:
                    task_defs[task_name] = task_file.name
        except (json.JSONDecodeError, IOError):
            log("warning", f"Could not read task file {task_file.name}")
            continue
    
    # Match API tasks to task files by name
    staging_tasks = {}
    matched_count = 0
    for task in tasks_list:
        # Handle both dict and string responses
        if isinstance(task, str):
            # If task is just an ID string, skip it (shouldn't happen after our fix, but be safe)
            log("warning", f"Skipping task that is just an ID string: {task}")
            continue
        
        if not isinstance(task, dict):
            log("warning", f"Skipping task with unexpected type: {type(task)}")
            continue
            
        task_name = task.get("name")
        task_id = task.get("id")
        
        if not task_name or not task_id:
            log("warning", f"Skipping task with missing name or id: {task}")
            continue
        
        # Find matching task file
        task_filename = task_defs.get(task_name)
        if task_filename:
            staging_tasks[task_filename] = {
                "name": task_name,
                "id": task_id
            }
            matched_count += 1
            log("info", f"Matched: {task_name} -> {task_filename} (ID: {task_id})")
        else:
            log("warning", f"Task '{task_name}' from API has no matching task definition file")
    
    # Update staging section
    manifest_data['staging'] = staging_tasks
    
    # Write updated manifest
    try:
        TASK_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASK_MANIFEST_PATH, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        log("success", f"Updated staging section with {matched_count} tasks.")
        return True
    except IOError as e:
        log("error", f"Failed to write manifest file: {e}")
        return False

def update_model_manifest_staging(models_list: List[Dict[str, Any]]):
    """
    Updates the staging section of the model manifest.
    """
    manifest_path = (project_root / "config" / "model_manifest.json").resolve()
    log("debug", f"Updating model manifest at: {manifest_path}")
    
    # Load existing manifest
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError:
            log("warning", "Existing manifest is invalid JSON. Creating new one.")
            manifest_data = {}
    else:
        manifest_data = {}
    
    # Initialize manifest structure
    if not isinstance(manifest_data, dict) or 'production' not in manifest_data:
        if 'models' in manifest_data:
            # Migrate old format
            old_models = manifest_data.get('models', {})
            manifest_data = {
                "production": old_models if old_models else {},
                "staging": {}
            }
        else:
            manifest_data = {
                "production": {},
                "staging": {}
            }
    if 'staging' not in manifest_data:
        manifest_data['staging'] = {}
    
    # Create model mapping
    model_mapping = {}
    for model in models_list:
        alias = model.get('alias') or model.get('name')
        model_id = model.get('id')
        
        if alias and model_id:
            model_mapping[alias] = model_id
        else:
            log("warning", f"Skipping model with missing info: {model.get('name', 'Unknown')}")
            continue
    
    # Update staging section
    manifest_data['staging'] = model_mapping
    
    # Write updated manifest
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        log("success", f"Updated staging section with {len(model_mapping)} models.")
        return True
    except IOError as e:
        log("error", f"Failed to write manifest file: {e}")
        return False

def main():
    log("info", "Starting Staging ID Fetch Script...")
    log("info", "This script fetches task and model IDs from the staging environment")
    log("info", "Make sure your environment variables point to the STAGING environment")
    
    # Debug: Log project root and paths
    log("debug", f"Project root: {project_root}")
    log("debug", f"Task template dir: {TASK_TEMPLATE_DIR}")
    log("debug", f"Task manifest path: {TASK_MANIFEST_PATH}")
    log("debug", f"Current working directory: {Path.cwd()}")
    
    # Load .env file if it exists
    env_path = project_root / ".env"
    log("debug", f"Looking for .env file at: {env_path}")
    if env_path.exists():
        log("info", f"Loading .env file from {env_path}")
        load_dotenv(env_path)
    else:
        log("info", f"No .env file found at {env_path}, using environment variables only")
    
    # Load configuration
    try:
        config = load_rb_config()
        # Priority: API_ROOT > RB_API_URL > config.api_url > default
        rb_api_root = os.environ.get("API_ROOT")
        if not rb_api_root:
            rb_api_url = os.environ.get("RB_API_URL")
            if rb_api_url:
                # RB_API_URL might already include /api/v1
                rb_api_url = rb_api_url.rstrip('/')
                if not rb_api_url.endswith('/api/v1'):
                    rb_api_root = f"{rb_api_url}/api/v1"
                else:
                    rb_api_root = rb_api_url
            else:
                # Fallback to config or default
                api_url = config.get("api_url") or "https://app.rightbrain.ai"
                api_url = api_url.rstrip('/')
                if not api_url.endswith('/api/v1'):
                    rb_api_root = f"{api_url}/api/v1"
                else:
                    rb_api_root = api_url
        
        log("info", f"Using API_ROOT: {rb_api_root}")
        log("warning", "⚠️  Make sure this points to STAGING, not production!")
    except Exception as e:
        log("error", f"Configuration Error: {e}")
        sys.exit(1)
    
    # Load IDs from Environment
    rb_org_id = os.environ.get("RB_ORG_ID")
    rb_project_id = os.environ.get("RB_PROJECT_ID")
    
    if not all([rb_org_id, rb_project_id]):
        log("error", "Missing required environment variables.", 
            details="Ensure RB_ORG_ID and RB_PROJECT_ID are set.")
        sys.exit(1)
    
    # Get authentication token
    try:
        token = get_rb_token()
    except Exception as e:
        log("error", f"Failed to get token: {e}")
        sys.exit(1)
    
    # Fetch and update tasks
    log("info", "\n--- Fetching Tasks ---")
    tasks = get_all_tasks(token, rb_api_root, rb_org_id, rb_project_id)
    if tasks:
        update_task_manifest_staging(tasks)
    else:
        log("warning", "No tasks returned from API.")
    
    # Fetch and update models
    log("info", "\n--- Fetching Models ---")
    models = get_all_models(token, rb_api_root, rb_org_id, rb_project_id)
    if models:
        update_model_manifest_staging(models)
    else:
        log("warning", "No models returned from API.")
    
    log("success", "\n✅ Staging ID fetch complete!")

if __name__ == "__main__":
    main()

