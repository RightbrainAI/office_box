import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

def get_vendor_type_from_path(file_path_str):
    """Determines vendor type based on the file path."""
    if "general_vendors/" in file_path_str:
        print("Vendor Type: General Vendor (inferred from path)")
        return "general"
    else:
        print("Vendor Type: Data Processor (inferred from path)")
        return "processor"

def get_rb_token(client_id, client_secret, token_url):
    """Authenticates with the Rightbrain API to get an access token."""
    try:
        response = requests.post(token_url, auth=(client_id, client_secret), data={"grant_type": "client_credentials"})
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Error getting Rightbrain token: {e}")

def get_or_create_task_id(rb_token, api_url, org_id, project_id, task_name, task_definition_path):
    """Finds a task by name. If it doesn't exist, it creates it."""
    # API URL should already include /api/v1
    list_tasks_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/task"
    headers = {"Authorization": f"Bearer {rb_token}"}
    params = {"name": task_name}
    try:
        response = requests.get(list_tasks_url, headers=headers, params=params)
        response.raise_for_status()
        tasks = response.json().get("results", [])
        if tasks:
            task_id = tasks[0]['id']
            print(f"Task '{task_name}' found with ID: {task_id}")
            return task_id
        else:
            print(f"Task '{task_name}' not found. Creating it...")
            with open(task_definition_path, 'r') as f:
                task_definition = json.load(f)
            # API URL should already include /api/v1
            create_task_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/task"
            create_response = requests.post(create_task_url, headers=headers, json=task_definition)
            create_response.raise_for_status()
            new_task_id = create_response.json()['id']
            print(f"Task created successfully with ID: {new_task_id}")
            return new_task_id
    except requests.exceptions.RequestException as e:
        sys.exit(f"Error getting or creating task: {e.response.text}")

def run_rb_task(rb_token, api_url, org_id, project_id, task_id, vendor_url):
    """Runs the specified Rightbrain task with the vendor URL."""
    # API URL should already include /api/v1
    run_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/task/{task_id}/run"
    headers = {"Authorization": f"Bearer {rb_token}"}
    payload = {"task_input": {"document_url": vendor_url}}
    print(f"Running task with URL: {vendor_url}")
    response = requests.post(run_url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json().get("response")

def parse_url_from_issue(body):
    """Finds the specific URL associated with the 'T&Cs' heading in a markdown file."""
    match = re.search(r'### T&Cs\s*\n\s*(https?://[^\s<>"]+)', str(body), re.IGNORECASE)
    return match.group(1) if match else None

def format_results_as_markdown(results):
    """Formats the detailed analysis from the task response into Markdown."""
    exclude_keys = ["ready_for_final_review", "incorporated_documents"]
    markdown_sections = []
    for key, value in results.items():
        if key in exclude_keys or not isinstance(value, dict):
            continue
        title = key.replace('_', ' ').title()
        answer = value.get('answer', 'N/A')
        if isinstance(answer, bool):
            answer = "Yes" if answer else "No"
        section = f"### {title}\n"
        section += f"**Answer:** {answer}\n"
        if value.get("quote"): section += f"> {value['quote']}\n"
        if value.get("comment"): section += f"**Comment:** {value['comment']}\n"
        markdown_sections.append(section)
    return "\n---\n\n".join(markdown_sections)

def extract_summary_data(results, issue_body, vendor_type):
    """Extracts key fields for the summary JSON file based on vendor type."""
    analysis_data = results
    def get_value(key, sub_key): return analysis_data.get(key, {}).get(sub_key)
    def parse_from_body(heading):
        match = re.search(f"### {heading}\\s*\\n\\s*(.*)", issue_body, re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"
    
    summary = {
        "processor_name": parse_from_body("Supplier Name"),
        "relationship_manager": parse_from_body("Rightbrain contact"),
        "summary_of_proposed_usage": parse_from_body("Summary of proposed usage")
    }
    if vendor_type == "processor":
        summary.update({
            "use_of_customer_content_for_training": get_value("data_usage_for_training", "answer"),
            "ip_indemnity_for_outputs": get_value("ip_indemnity", "answer"),
            "data_deletion_timeline_days": get_value("data_deletion", "timeline_days"),
            "liability_cap": get_value("limitation_of_liability", "cap_amount"),
            "governing_law": get_value("governing_law", "answer")
        })
    else: # General Vendor
        summary.update({
            "contract_term": get_value("contract_term", "initial_term"),
            "auto_renews": get_value("contract_term", "auto_renews"),
            "payment_terms": get_value("payment_terms", "answer"),
            "liability_cap": get_value("limitation_of_liability", "cap_amount"),
            "governing_law": get_value("governing_law", "answer")
        })
    return summary

def update_local_markdown_file(file_path, original_content, new_report_content):
    """Replaces the analysis section in a local Markdown file using consistent markers."""
    # Use the same invisible HTML markers as the other script for consistency
    START_MARKER = "<! -- -->"
    END_MARKER = "<! -- -->"

    # The new block of content to insert
    content_block = f"{START_MARKER}\n{new_report_content}\n{END_MARKER}"

    if START_MARKER in original_content:
        # If the markers exist, replace the content between them
        print("Analysis section found. Replacing it with updated results...")
        before_marker = original_content.split(START_MARKER)[0]
        after_marker_parts = original_content.split(END_MARKER)
        after_marker = after_marker_parts[1] if len(after_marker_parts) > 1 else ""
        
        updated_body = before_marker.strip() + "\n\n" + content_block + after_marker.strip()
    else:
        # Fallback: if markers aren't found, append the new block to the end
        print("No existing analysis section found. Appending new results...")
        updated_body = original_content.strip() + "\n\n" + content_block

    with open(file_path, 'w') as f:
        f.write(updated_body)
    print(f"Successfully updated file: {file_path}")

def update_central_json(summary_data, vendor_type):
    """Reads, updates, and writes to the correct central JSON file."""
    processor_name = summary_data.get("processor_name")
    if not processor_name or processor_name == "N/A":
        print("Skipping JSON update because processor name is missing.")
        return

    if vendor_type == "processor":
        json_path = Path("eng/data-processors.json")
    else: # General Vendor
        json_path = Path("general_vendors/all-general-vendors.json")
    
    json_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(json_path, 'r') as f: all_records = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): all_records = []

    record_found = False
    for i, record in enumerate(all_records):
        if record.get("processor_name") == processor_name:
            all_records[i] = summary_data
            record_found = True
            break
    if not record_found: all_records.append(summary_data)

    with open(json_path, 'w') as f:
        json.dump(all_records, f, indent=2)
    print(f"Updated record for '{processor_name}' in {json_path}.")

def main():
    """Main execution block."""
    load_dotenv()
    vendor_file_path_str = os.getenv("VENDOR_FILE_PATH")
    if not vendor_file_path_str:
        sys.exit("Error: VENDOR_FILE_PATH environment variable not set.")
    
    vendor_file_path = Path(vendor_file_path_str)
    if not vendor_file_path.is_file():
        sys.exit(f"Error: File not found at '{vendor_file_path}'")

    vendor_type = get_vendor_type_from_path(vendor_file_path_str)
    task_def_path = "tasks/sub_processor_terms_analyzer.json" if vendor_type == "processor" else "tasks/general_vendor_terms_analyzer.json"
    
    try:
        with open(task_def_path, 'r') as f: task_name = json.load(f)['name']
    except (FileNotFoundError, KeyError): sys.exit(f"Error reading task name from {task_def_path}")
        
    rb_org_id = os.getenv("RB_ORG_ID")
    rb_project_id = os.getenv("RB_PROJECT_ID")
    rb_client_id = os.getenv("RB_CLIENT_ID")
    rb_client_secret = os.getenv("RB_CLIENT_SECRET")
    rb_api_url = os.getenv("RB_API_URL")
    rb_oauth2_url = os.getenv("RB_OAUTH2_URL")
    
    if not rb_api_url or not rb_oauth2_url:
        sys.exit("❌ Error: Missing RB_API_URL or RB_OAUTH2_URL environment variable.")
    
    # Use the OAuth2 URL directly (should be the full endpoint URL)
    rb_token_url = rb_oauth2_url

    print(f"--- Processing: {vendor_file_path.name} ---")
    with open(vendor_file_path, 'r') as f: content = f.read()

    vendor_url = parse_url_from_issue(content)
    if not vendor_url:
        sys.exit(f"Skipping: No T&Cs URL found in {vendor_file_path.name}")
        
    rb_token = get_rb_token(rb_client_id, rb_client_secret, rb_token_url)
    rb_task_id = get_or_create_task_id(rb_token, rb_api_url, rb_org_id, rb_project_id, task_name, task_def_path)
    rb_results = run_rb_task(rb_token, rb_api_url, rb_org_id, rb_project_id, rb_task_id, vendor_url)

    markdown_report = format_results_as_markdown(rb_results)
    summary_json = extract_summary_data(rb_results, content, vendor_type)
    final_report = (
        f"{markdown_report}\n\n---\n\n"
        "### 📋 Summary Data for Automation\n\n"
        "This data is for the central JSON file. Please review for accuracy before the PR is merged.\n"
        "```json\n"
        f"{json.dumps(summary_json, indent=2)}\n"
        "```"
    )
    
    update_local_markdown_file(vendor_file_path, content, final_report)
    update_central_json(summary_json, vendor_type)

if __name__ == "__main__":
    main()
