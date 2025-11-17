import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

# --- Helper Functions ---

def sanitize_filename(name: str) -> str:
    """Converts a task name into a safe, valid filename."""
    s = name.lower()
    s = s.replace(" ", "_").replace("-", "_")
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s

def format_task_for_creation(full_task_def: dict) -> dict:
    """
    Reformats a full task definition (from a GET request) into a payload
    suitable for creating a new task (for a POST request). It extracts the
    latest active revision and merges it with the parent task's metadata.
    """
    print("... Reformatting task into a creation-ready payload.")
    
    # 1. Find the active revision ID
    active_revisions = full_task_def.get("active_revisions")
    if not active_revisions:
        sys.exit("❌ Error: Task has no active revisions to extract.")
        
    # Assuming the first active revision is the one we want
    active_revision_id = active_revisions[0].get("task_revision_id")
    print(f"✅ Found active revision ID: {active_revision_id}")

    # 2. Find the full revision object from the list of all revisions
    latest_active_revision = None
    for revision in full_task_def.get("revisions", []):
        if revision.get("id") == active_revision_id:
            latest_active_revision = revision
            break
            
    if not latest_active_revision:
        sys.exit(f"❌ Error: Could not find revision details for ID {active_revision_id} in the task's revision list.")

    # 3. Build the new creation-ready payload
    # The 'Create Task' API endpoint expects a flat structure combining
    # task properties and the properties of a single revision.
    creation_payload = {
        # Parent Task Properties
        "name": full_task_def.get("name"),
        "description": full_task_def.get("description"),
        "enabled": full_task_def.get("enabled", True),
        "public": full_task_def.get("public", False),

        # Active Revision Properties
        "system_prompt": latest_active_revision.get("system_prompt"),
        "user_prompt": latest_active_revision.get("user_prompt"),
        "llm_model_id": latest_active_revision.get("llm_model_id"),
        "llm_config": latest_active_revision.get("llm_config", {}),
        "output_format": latest_active_revision.get("output_format"),
        "input_processors": latest_active_revision.get("input_processors", []),
        "rag": latest_active_revision.get("rag"),
        "task_forwarder_id": latest_active_revision.get("task_forwarder_id"),
        "image_required": latest_active_revision.get("image_required", False),
        "optimise_images": latest_active_revision.get("optimise_images", True),
        "test": latest_active_revision.get("test", False),
        "annotation": latest_active_revision.get("annotation")
    }

    # Clean out any keys that are None, as they are not needed for creation
    return {k: v for k, v in creation_payload.items() if v is not None}


# --- Rightbrain API Helper Functions ---

def get_rb_token(client_id, client_secret, token_url):
    """Authenticates with the Rightbrain API to get an access token."""
    try:
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"}
        )
        response.raise_for_status()
        print("✅ Successfully authenticated with Rightbrain.")
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Error getting Rightbrain token: {e}")

def fetch_task_definition(rb_token, api_url, org_id, project_id, task_id):
    """Fetches a specific task definition by its ID."""
    # API URL should already include /api/v1
    fetch_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/task/{task_id}"
    headers = {"Authorization": f"Bearer {rb_token}"}
    
    print(f"📡 Fetching task definition for ID: {task_id}...")
    try:
        response = requests.get(fetch_url, headers=headers)
        response.raise_for_status()
        print("✅ Full task definition fetched successfully.")
        return response.json()
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Error fetching task definition: {e.response.text}")

# --- Main Execution ---

def main():
    """
    Main script to prompt for a Task ID, fetch its definition, reformat it
    for creation, and save it to a dynamically named JSON file.
    """
    try:
        import requests
        from dotenv import load_dotenv
    except ImportError:
        print("⚠️ Required packages not found.")
        print("Please run: pip install requests python-dotenv")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=project_root / ".env")

    # --- Configuration ---
    required_vars = [
        "RB_ORG_ID", "RB_PROJECT_ID", "RB_CLIENT_ID",
        "RB_CLIENT_SECRET", "RB_API_URL", "RB_OAUTH2_URL"
    ]
    config = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            sys.exit(f"❌ Error: Environment variable '{var}' is not set. Please add it to your .env file in the project root.")
        config[var] = value
    
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    config["rb_token_url"] = config["RB_OAUTH2_URL"]
    
    # --- Script Logic ---
    task_id = input("➡️ Please enter the Rightbrain Task ID to fetch: ")
    if not task_id:
        sys.exit("❌ No Task ID provided. Exiting.")

    rb_token = get_rb_token(
        config["RB_CLIENT_ID"],
        config["RB_CLIENT_SECRET"],
        config["rb_token_url"]
    )

    full_task_definition = fetch_task_definition(
        rb_token,
        config["RB_API_URL"],
        config["RB_ORG_ID"],
        config["RB_PROJECT_ID"],
        task_id.strip()
    )

    # --- NEW STEP: Reformat the fetched data ---
    creation_ready_definition = format_task_for_creation(full_task_definition)
    
    # --- Dynamic Filename Generation ---
    task_name = creation_ready_definition.get("name")
    if not task_name:
        sys.exit("❌ Error: Task definition is missing the 'name' field.")
    
    filename = f"{sanitize_filename(task_name)}.json"
    output_file_path = project_root / "tasks" / filename
    print(f"📄 Task name found: '{task_name}'. Saving to '{output_file_path}'.")

    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, 'w') as f:
            json.dump(creation_ready_definition, f, indent=2)
        print(f"\n🎉 Success! The file '{output_file_path}' has been updated with a creation-ready definition.")
        print("You can now commit the changes to your repository.")
    except IOError as e:
        sys.exit(f"❌ Error writing to file '{output_file_path}': {e}")


if __name__ == "__main__":
    main()