import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# --- 1. Fix Import Path for 'utils' ---
# Get the project root directory (two levels up from this script)
# file -> scripts/ -> root
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # Import shared utilities
    from utils.rightbrain_api import get_rb_token, log, load_rb_config
except ImportError as e:
    print(f"❌ Error importing 'utils.rightbrain_api': {e}", file=sys.stderr)
    sys.exit(1)

def get_available_models(token, api_url, org_id, project_id):
    """
    Fetches the list of all available LLM models for the project.
    """
    # Remove /api/v1 suffix if present to avoid duplication, then reconstruct path
    base = api_url.rstrip('/')
    if base.endswith("/api/v1"):
        models_url = f"{base}/org/{org_id}/project/{project_id}/model"
    else:
        models_url = f"{base}/api/v1/org/{org_id}/project/{project_id}/model"

    headers = {"Authorization": f"Bearer {token}"}
    
    log("info", f"Fetching models from {models_url}...")
    try:
        response = requests.get(models_url, headers=headers)
        response.raise_for_status()
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
    if manifest_path.exists():
        log("info", f"Loading existing manifest from {manifest_path}...")
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
    else:
        log("warning", f"No manifest found at {manifest_path}. Creating a new one.")
        manifest_data = {}

    # Create the alias -> id mapping
    # We filter for active models (not retired) if possible, or just map all
    model_mapping = {}
    for model in models_list:
        # Prefer 'alias' (e.g. "gpt-4"), fallback to 'name', then 'id'
        alias = model.get('alias') or model.get('name')
        model_id = model.get('id')
        
        if alias and model_id:
            model_mapping[alias] = model_id
        else:
            log("warning", f"Skipping model with missing info: {model.get('name', 'Unknown')}")
            continue
            
    # Update the manifest data
    manifest_data["models"] = model_mapping
    
    try:
        # Ensure directory exists
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, 'w') as manifest_file:
            json.dump(manifest_data, manifest_file, indent=2)
        
        log("success", f"Successfully updated {manifest_path} with {len(model_mapping)} models.")
        return True
        
    except IOError as e:
        log("error", f"Failed to write to manifest file {manifest_path}", details=str(e))
        return False

def main():
    log("info", "Starting Model Fetch Script...")
    log("debug", f"Project Root detected as: {project_root}")

    # --- 2. Load Environment & Config ---
    # Load .env file if it exists (useful for local development)
    env_path = project_root / ".env"
    if env_path.exists():
        log("info", f"Loading environment from {env_path}")
        load_dotenv(env_path)

    # Load config for URLs
    try:
        config = load_rb_config()
        # Fallback logic consistent with other scripts
        rb_api_url = config.get("api_url") or os.environ.get("RB_API_URL") or "https://app.rightbrain.ai"
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

    # Define the manifest path
    manifest_path = project_root / "config" / "model_manifest.json"

    # --- 3. Execute ---
    try:
        # No arguments needed; it pulls from env/config automatically
        token = get_rb_token()
    except Exception as e:
        log("error", f"Failed to get token: {e}")
        sys.exit(1)

    models = get_available_models(token, rb_api_url, rb_org_id, rb_project_id)
    
    if models:
        update_manifest(manifest_path, models)
    else:
        log("warning", "No models returned from API. Manifest not updated.")

if __name__ == "__main__":
    main()