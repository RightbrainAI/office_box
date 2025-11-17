import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Set, Any
from urllib.parse import unquote

# --- Constants ---
SOURCE_DIR = Path("_vendor_analysis_source")
CONFIG_DIR = Path("config")
TASK_MANIFEST_PATH = Path("tasks/task_manifest.json")

# --- Helper: GitHub & Manifest ---

def load_task_manifest() -> Dict[str, str]:
    """Loads the task_manifest.json file."""
    if not TASK_MANIFEST_PATH.exists():
        sys.exit(f"❌ Error: Task manifest not found at '{TASK_MANIFEST_PATH}'.")
    try:
        with open(TASK_MANIFEST_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        sys.exit(f"❌ Error: Could not parse '{TASK_MANIFEST_PATH}'.")

def post_github_comment(gh_token: str, repo: str, issue_number: str, body: str):
    """Posts a new comment to the GitHub issue."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"body": body}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully posted results to issue #{issue_number}.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to post comment to GitHub issue: {e}")
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        # We don't sys.exit, as the analysis *ran*, but we need to log failure.
        print("--- ANALYSIS RESULTS (stdout) ---")
        print(body)
        print("--- END ANALYSIS RESULTS ---")


# --- Helper: Rightbrain API ---

def get_rb_token(client_id: str, client_secret: str, token_url: str) -> str:
    """Authenticates with the Rightbrain API."""
    try:
        response = requests.post(token_url, auth=(client_id, client_secret), data={"grant_type": "client_credentials"})
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Error getting Rightbrain token: {e}")

def run_rb_task(rb_token: str, api_url: str, org_id: str, project_id: str, 
                task_id: str, task_input_payload: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    """Runs a Rightbrain task with a dynamic input payload."""
    if not task_id:
        sys.exit(f"❌ Error: Missing task ID for {task_name}.")
        
    run_url = f"{api_url.rstrip('/')}/org/{org_id}/project/{project_id}/task/{task_id}/run"
    headers = {"Authorization": f"Bearer {rb_token}"}
    
    # Use the generic payload structure
    payload = {"task_input": task_input_payload}
    
    print(f"🚀 Running {task_name}...")
    try:
        response = requests.post(run_url, headers=headers, json=payload, timeout=600)
        response.raise_for_status()
        print(f"✅ {task_name} complete.")
        # Return only the 'response' field which contains the structured JSON
        return response.json().get("response", {})
    except requests.exceptions.RequestException as e:
        print(f"❌ {task_name} API call failed: {e}")
        if e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            try:
                print(f"Response Body: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response Body (non-JSON): {e.response.text}")
        return {"error": f"{task_name} failed", "details": str(e)}

# --- Core Logic: Text Compilation & Context ---

def parse_form_field(body: str, label: str) -> str:
    """Extracts a single field's value from the issue form body."""
    # Matches "### Label" followed by text until the next "###" or end of string
    pattern = re.compile(f"### {re.escape(label)}\\s*\\n\\s*([\\s\\S]*?)(?=\\n### |\\Z)", re.IGNORECASE)
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    return "N/A"

def extract_vendor_usage_details(issue_body: str) -> str:
    """Builds the vendor-specific {vendor_usage_details} context block (the 'Subject')."""
    print("ℹ️ Parsing vendor usage details from issue body...")
    # Per Stage 2 spec, {vendor_usage_details} includes Usage Context, Data Types,
    # and Service Name/Description (for the reporter task).
    #
    # Phase 1.1 Update: Also include Relationship Owner and Term Length for full context.
    context_parts = [
        f"**Service Name:** {parse_form_field(issue_body, 'Service Name')}",
        f"**Service Description:** {parse_form_field(issue_body, 'Service Description')}",
        f"**Vendor/Service Usage Context:** {parse_form_field(issue_body, 'Vendor/Service Usage Context')}", # Updated label
        f"**Data Types Involved:** {parse_form_field(issue_body, 'Data Types Involved')}",
        f"**Relationship Owner:** {parse_form_field(issue_body, 'Relationship Owner')}",
        f"**Term Length:** {parse_form_field(issue_body, 'Term Length')}",
    ]
    return "\n".join(context_parts)

def parse_data_processor_field(issue_body: str) -> str:
    """Parses the 'Data Processor' field from the issue body."""
    print("ℹ️ Parsing data processor status from issue body...")
    return parse_form_field(issue_body, 'Data Processor')

def load_company_profile() -> str:
    """Loads the company profile and formats it as a string for the {company_profile} block (the 'Lens')."""
    print("ℹ️ Loading company profile...")
    profile_path = CONFIG_DIR / "company_profile.json"
    if not profile_path.exists():
        sys.exit(f"❌ Error: Company profile not found at '{profile_path}'")
    
    try:
        with open(profile_path, 'r') as f:
            data = json.load(f)
        
        # Format as markdown string, as expected by the tasks
        profile_parts = [
            f"**Company Name:** {data.get('name')}",
            f"**Industry:** {data.get('industry')}",
            f"**Services:** {data.get('services')}",
            f"**Applicable Regulations:** {', '.join(data.get('regulations', []))}"
        ]
        return "\n".join(profile_parts)
    except Exception as e:
        sys.exit(f"❌ Error reading company profile: {e}")

def parse_approved_documents(issue_body: str) -> Dict[str, Set[str]]:
    """
    Parses the issue body's checklist to find all checked files
    and their categories.
    """
    print("ℹ️ Parsing approved documents from issue checklist...")
    legal_files: Set[str] = set()
    security_files: Set[str] = set()
    
    # Regex to find:
    # - [x] **(Categories)**: ... (path) ...
    # Group 1: The categories (e.g., "Legal", "Security", "Legal, Security")
    # Group 2: The file path (e.g., "_vendor_analysis_source/issue-123-doc.txt")
    pattern = re.compile(
        r"-\s*\[x\]\s*\*\*(.*?)\*\*:.*?\((?:https://.*?/blob/main/)?(_vendor_analysis_source/.*?)\)",
        re.IGNORECASE
    )
    
    matches = pattern.findall(issue_body)
    
    if not matches:
        print("⚠️ Warning: No checked documents found in the issue body. Analysis may be empty.")

    for categories_str, file_path_raw in matches:
        # File path might be URL-encoded in the markdown link
        file_path = unquote(file_path_raw.strip(')'))
        
        categories = [cat.strip().lower() for cat in categories_str.split(',')]
        
        if "legal" in categories:
            legal_files.add(file_path)
        if "security" in categories:
            security_files.add(file_path)
            
    print(f"Found {len(legal_files)} approved legal document(s).")
    print(f"Found {len(security_files)} approved security document(s).")
    
    return {"legal_files": legal_files, "security_files": security_files}

def compile_text_from_files(file_list: Set[str]) -> str:
    """Reads a list of files and compiles them into a single string."""
    if not file_list:
        return ""
        
    compiled_parts = []
    
    for file_path_str in sorted(list(file_list)):
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            print(f"⚠️ Warning: Checked file not found: '{file_path}'. Skipping.")
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Add the separator required by the AI tasks
            separator = f"\n\n--- DOCUMENT SEPARATOR ---\nSource URL: {file_path_str}\n\n"
            compiled_parts.append(separator + content)
            
        except Exception as e:
            print(f"⚠️ Error reading file '{file_path}': {e}. Skipping.")
            
    return "".join(compiled_parts)

# --- Helper: Report Formatting ---

def format_report_as_markdown(report_data: Dict[str, Any], 
                            raw_security_json: Dict[str, Any], 
                            raw_legal_json: Dict[str, Any]) -> str:
    """Formats the synthesis task's JSON into a human-readable Markdown comment."""
    
    try:
        report = report_data.get("report", {})
        draft_data = report_data.get("draft_approval_data", {})

        # Build positive findings
        pos_findings_md_list = []
        for f in report.get("positive_findings", []):
            pos_findings_md_list.append(f"* **{f.get('finding', 'N/A')}:** {f.get('summary', 'N/A')}")
        pos_findings_md = "\n".join(pos_findings_md_list)
        if not pos_findings_md: pos_findings_md = "None identified."

        # Build legal risks
        legal_risks_md_list = []
        for r in report.get("key_legal_risks", []):
            legal_risks_md_list.append(f"* **Risk:** {r.get('risk', 'N/A')}\n  * **Summary:** {r.get('summary', 'N/A')}\n  * **Recommendation:** {r.get('recommendation', 'N/A')}")
        legal_risks_md = "\n".join(legal_risks_md_list)
        if not legal_risks_md: legal_risks_md = "No critical legal risks identified."

        # Build security gaps
        sec_gaps_md_list = []
        for g in report.get("key_security_gaps", []):
            sec_gaps_md_list.append(f"* **Gap:** {g.get('gap', 'N/A')}\n  * **Summary:** {g.get('summary', 'N/A')}\n  * **Recommendation:** {g.get('recommendation', 'N/A')}")
        sec_gaps_md = "\n".join(sec_gaps_md_list)
        if not sec_gaps_md: sec_gaps_md = "No critical security gaps identified."

        # Build the final comment
        comment_parts = [
            "## 🚀 AI-Generated Risk Summary",
            f"### **Overall Assessment: {report.get('overall_assessment', 'N/A')}**",
            f"**Executive Summary:** {report.get('executive_summary', 'N/A')}",
            "\n### ✅ Positive Findings",
            pos_findings_md,
            "\n### ⚖️ Key Legal Risks",
            legal_risks_md,
            "\n### 🛡️ Key Security Gaps",
            sec_gaps_md,
            "\n---",
            "\n## 📝 Reviewer-Approved Data (Draft)",
            "Please review, edit, and confirm the details below. This JSON block will be committed to the central vendor registry upon issue closure.",
            "\n**ACTION REQUIRED:** Before closing this issue, please **edit the `mitigations` field** (and any others) in the JSON block below to reflect the final, agreed-upon controls.",
            f"```json\n{json.dumps(draft_data, indent=2)}\n```",
            "\n---",
            "\n## 🤖 Raw Analysis Data (for review)",
            "\n### 🛡️ Security Posture Analysis (Raw)",
            f"```json\n{json.dumps(raw_security_json, indent=2)}\n```",
            "\n### ⚖️ Legal & DPA Analysis (Raw)",
            f"```json\n{json.dumps(raw_legal_json, indent=2)}\n```"
        ]
        return "\n".join(comment_parts)
        
    except Exception as e:
        print(f"❌ Error formatting report: {e}")
        # Fallback to just dumping all the data
        return (
            "## 🤖 Vendor Analysis Results (Fallback)\n\n"
            "Error formatting the AI-generated report. Please review the raw JSON outputs.\n\n"
            "### 📊 Synthesis Report\n"
            f"```json\n{json.dumps(report_data, indent=2)}\n```\n\n"
            "### 🛡️ Security Posture Analysis\n"
            f"```json\n{json.dumps(raw_security_json, indent=2)}\n```\n\n"
            "### ⚖️ Legal & DPA Analysis\n"
            f"```json\n{json.dumps(raw_legal_json, indent=2)}\n```"
        )

# --- Main Execution ---

def main():
    load_dotenv()

    # --- 1. Load Config & Environment Variables ---
    gh_token = os.environ.get("GITHUB_TOKEN")
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    repo_name = os.environ.get("REPO_NAME")
    rb_org_id = os.environ.get("RB_ORG_ID")
    rb_project_id = os.environ.get("RB_PROJECT_ID")
    rb_client_id = os.environ.get("RB_CLIENT_ID")
    rb_client_secret = os.environ.get("RB_CLIENT_SECRET")
    rb_api_url = os.environ.get("RB_API_URL")
    rb_token_url = f"{os.environ.get('RB_OAUTH2_URL', '')}{os.environ.get('RB_OAUTH2_TOKEN_PATH', '')}"

    if not all([gh_token, issue_body, issue_number, repo_name, rb_org_id, rb_project_id, 
                rb_client_id, rb_client_secret, rb_api_url, rb_token_url]):
        sys.exit("❌ Error: Missing one or more required environment variables.")

    print(f"🚀 Starting analysis for issue #{issue_number} in repo {repo_name}...")

    manifest = load_task_manifest()
    security_task_id = manifest.get("security_posture_analyzer.json")
    legal_task_id = manifest.get("sub_processor_terms_analyzer.json")
    reporter_task_id = manifest.get("vendor_risk_reporter.json")

    if not all([security_task_id, legal_task_id, reporter_task_id]):
        sys.exit("❌ Error: Could not find all required task IDs in manifest (security, legal, reporter).")

    # --- 2. Build Context Blocks (Refactored for Stage 2) ---
    company_profile = load_company_profile()
    vendor_usage_details = extract_vendor_usage_details(issue_body)
    # Phase 1.1 Update: Parse Relationship Owner separately for direct injection
    relationship_owner = parse_form_field(issue_body, 'Relationship Owner')
    
    # --- 3. Determine Vendor Type Signal (Refactored for Stage 2) ---
    data_processor_status = parse_data_processor_field(issue_body)
    vendor_type_signal = "Processor" if data_processor_status.lower() == 'yes' else "General Supplier"
    print(f"ℹ️ Vendor type signal determined: {vendor_type_signal}")

    # --- 4. Parse Checklist and Compile Text ---
    approved_files = parse_approved_documents(issue_body)
    
    legal_docs_text = compile_text_from_files(approved_files["legal_files"])
    security_docs_text = compile_text_from_files(approved_files["security_files"])

    if not legal_docs_text and not security_docs_text:
        print("❌ No text compiled from any approved documents. Aborting analysis.")
        post_github_comment(gh_token, repo_name, issue_number, 
                            "**Analysis Failed:** No approved documents were found or read. Please check the files in `_vendor_analysis_source` and ensure the correct items are checked in the issue checklist.")
        sys.exit()

    # --- 5. Run Analysis Tasks (Refactored for Stage 2) ---
    print("\n--- STAGE 5: Running Analysis Tasks ---")
    rb_token = get_rb_token(rb_client_id, rb_client_secret, rb_token_url)
    legal_analysis_json = {"status": "skipped", "reason": "No approved legal documents found."}
    security_analysis_json = {"status": "skipped", "reason": "No approved security documents found."}

    if legal_docs_text:
        legal_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": legal_docs_text
        }
        legal_analysis_json = run_rb_task(
            rb_token, rb_api_url, rb_org_id, rb_project_id,
            legal_task_id, legal_input, "Sub-Processor Terms Analyzer"
        )
    else:
        print("ℹ️ No approved legal documents found. Skipping legal analysis.")

    if security_docs_text:
        security_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": security_docs_text
        }
        security_analysis_json = run_rb_task(
            rb_token, rb_api_url, rb_org_id, rb_project_id,
            security_task_id, security_input, "Security Posture Analyzer"
        )
    else:
        print("ℹ️ No approved security documents found. Skipping security analysis.")

    # --- 6. Run Synthesis Task (Refactored for Stage 2) ---
    print("\n--- STAGE 6: Synthesizing Reports ---")
    security_json_string = json.dumps(security_analysis_json)
    legal_json_string = json.dumps(legal_analysis_json)
    
    reporter_input = {
        "company_profile": company_profile,
        "vendor_usage_details": vendor_usage_details,
        "vendor_type_signal": vendor_type_signal, # New signal
        "relationship_owner": relationship_owner, # Phase 1.1 Update
        "security_json_string": security_json_string,
        "legal_json_string": legal_json_string
    }

    report_json = run_rb_task(
        rb_token, rb_api_url, rb_org_id, rb_project_id,
        reporter_task_id, reporter_input, "Vendor Risk Reporter"
    )

    # --- 7. Format and Post Results ---
    print("\n--- STAGE 7: Formatting and Posting Results ---")
    if not report_json or "error" in report_json:
        print("❌ Synthesis task failed. Posting raw JSON as fallback.")
        # Fallback to old behavior
        final_comment_body = (
            "## 🤖 Vendor Analysis Results (Synthesis Failed)\n\n"
            "The final risk synthesis report failed to generate. Please review the raw JSON outputs.\n\n"
            "### 🛡️ Security Posture Analysis\n"
            f"```json\n{json.dumps(security_analysis_json, indent=2)}\n```\n\n"
            "### ⚖️ Legal & DPA Analysis\n"
            f"```json\n{json.dumps(legal_analysis_json, indent=2)}\n```"
        )
    else:
        print("✅ Synthesis complete. Formatting report.")
        final_comment_body = format_report_as_markdown(
            report_json, security_analysis_json, legal_analysis_json
        )
    
    post_github_comment(gh_token, repo_name, issue_number, final_comment_body)
    print("✅ Analysis and reporting complete.")

if __name__ == "__main__":
    main()