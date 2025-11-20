import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))
from utils.rightbrain_api import get_rb_token, log

def get_available_models(token, api_url, org_id, project_id):
    """
    Fetches the list of all available LLM models for the project.
    [cite_start][cite: 609, 610]
    """
    # [cite_start]Endpoint definition from API docs [cite: 609]
    # API URL should already include /api/v1
    models_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/model"
    # [cite_start]Auth header requirement from API docs [cite: 616]
    headers = {"Authorization": f"Bearer {token}"}
    
    log("info", f"Fetching models from {models_url}...")
    try:
        response = requests.get(models_url, headers=headers)
        response.raise_for_status()
        # [cite_start]The API returns a list of model objects [cite: 617]
        models_list = response.json()
        log("success", f"Found {len(models_list)} available models.")
        return models_list
    except requests.exceptions.RequestException as e:
        log("error", "Failed to fetch models", 
            details=f"{e}\nResponse: {e.response.text if e.response else 'N/A'}")
        sys.exit(1)

def update_manifest(manifest_path, models_list):
    """
    Reads the existing manifest, adds the model map, and writes it back.
    """
    # Load existing data, or create a new dict
    if manifest_path.exists():
        print(f"Loading existing manifest from {manifest_path}...")
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
    else:
        print(f"No manifest found at {manifest_path}. Creating a new one.")
        manifest_data = {}

    # Create the alias -> id mapping
    # [cite_start]Model object schema contains 'alias' and 'id' [cite: 620]
    model_mapping = {}
    for model in models_list:
        alias = model.get('alias')
        model_id = model.get('id')
        if alias and model_id:
            model_mapping[alias] = model_id
        else:
            log("warning", f"Skipping model with missing alias or id: {model.get('name')}")
            continue
            
    # Update the manifest data with the new model map
    manifest_data["models"] = model_mapping
    
    # Write the updated data back to the file
    try:
        with open(manifest_path, 'w') as manifest_file:
            json.dump(manifest_data, manifest_file, indent=2)
        
        log("success", f"Successfully updated {manifest_path} with model ID mappings.")
        return True
        
    except IOError as e:
        log("error", f"Failed to write to manifest file {manifest_path}", details=str(e))
        return False

def main():
    # --- 1. Setup Paths ---
    # This script is in /scripts, so we go up one level to the root
    try:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    except NameError:
        # Handle cases where __file__ is not defined (e.g., interactive REPL)
        project_root = Path.cwd()
        print(f"Running in interactive mode. Using CWD as project root: {project_root}")

    # Load .env file from the project root
    load_dotenv(project_root / ".env")
    
    # Define the manifest path
    manifest_path = project_root / "tasks" / "task_manifest.json"

    # --- 2. Load Configuration ---
    rb_client_id = os.environ.get("RB_CLIENT_ID")
    rb_client_secret = os.environ.get("RB_CLIENT_SECRET")
    rb_org_id = os.environ.get("RB_ORG_ID")
    rb_project_id = os.environ.get("RB_PROJECT_ID")
    rb_api_url = os.environ.get("RB_API_URL")
    rb_oauth_url = os.environ.get("RB_OAUTH2_URL")
    
    if not rb_api_url or not rb_oauth_url:
        log("error", "Missing RB_API_URL or RB_OAUTH2_URL environment variable.")
        sys.exit(1)
    
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    rb_token_url = rb_oauth_url

    # Check for required env vars
    required_vars = [rb_client_id, rb_client_secret, rb_org_id, rb_project_id]
    if not all(required_vars):
        print("❌ Error: Missing one or more required environment variables.")
        print("Ensure RB_CLIENT_ID, RB_CLIENT_SECRET, RB_ORG_ID, and RB_PROJECT_ID are set.")
        sys.exit(1)

    # --- 3. Run the script ---
    token = get_rb_token(rb_client_id, rb_client_secret, rb_token_url)
    models = get_available_models(token, rb_api_url, rb_org_id, rb_project_id)
    
    if models:
        update_manifest(manifest_path, models)
    else:
        print("No models returned from API. Manifest not updated.")

if __name__ == "__main__":
    main()