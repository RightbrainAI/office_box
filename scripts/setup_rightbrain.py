import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any

# --- Configuration ---
TASK_TEMPLATE_DIR = Path("task_templates")
TASK_MANIFEST_PATH = Path("tasks/task_manifest.json")

# --- Rightbrain API Client ---

def get_rb_token(client_id: str, client_secret: str, token_url_base: str) -> str:
    """Authenticates with the Rightbrain API."""
    
    # Allow overriding the token path via environment variable, default to /oauth/token if not set
    token_path = os.environ.get("RB_OAUTH2_TOKEN_PATH", "/oauth/token")
    
    # Construct URL carefully handling slashes
    token_url = f"{token_url_base.rstrip('/')}/{token_path.lstrip('/')}"
    
    print(f"Authenticating with {token_url}...")
    
    try:
        # Support both Basic Auth (header) and Client Credentials (body)
        # The docs suggest body params for client_credentials flow
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "offline_access" # Added scope based on common RB docs
            }
        )
        
        # Debugging: If not JSON, print raw response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"❌ Error: Response from {token_url} was not valid JSON.", file=sys.stderr)
            print(f"Status Code: {response.status_code}", file=sys.stderr)
            print(f"Raw Response: {response.text[:500]}...", file=sys.stderr) # Print first 500 chars
            sys.exit(1)

        if not response.ok:
             print(f"❌ Authentication failed with status {response.status_code}.", file=sys.stderr)
             print(f"Response: {json.dumps(data, indent=2)}", file=sys.stderr)
             sys.exit(1)

        token = data.get("access_token")
        if not token:
            raise ValueError(f"No access_token in response: {data}")
            
        print("✅ Authentication successful.")
        return token

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error getting Rightbrain token: {e}", file=sys.stderr)
        sys.exit(1)

def create_rb_task(rb_token: str, api_url_base: str, org_id: str, project_id: str, task_body: Dict[str, Any]) -> str:
    """Creates a single Rightbrain task and returns its new ID."""
    task_name = task_body.get("name", "Unnamed Task")
    
    # Intelligent URL construction: check if api_url_base already contains /api/v1
    base = api_url_base.rstrip('/')
    if base.endswith("/api/v1"):
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

    # 2. Authenticate with Rightbrain
    rb_token = get_rb_token(rb_client_id, rb_client_secret, rb_oauth2_url)
    
    # 3. Find and load all task templates
    print(f"Looking for task templates in '{TASK_TEMPLATE_DIR}'...")
    if not TASK_TEMPLATE_DIR.is_dir():
        print(f"❌ Error: Task template directory not found at '{TASK_TEMPLATE_DIR}'", file=sys.stderr)
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