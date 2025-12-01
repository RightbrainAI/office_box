import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Set, Any
from urllib.parse import unquote

# --- Fix Import Path for 'utils' ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.github_api import post_github_comment, load_company_profile, extract_vendor_usage_details, parse_form_field
    from utils.rightbrain_api import get_rb_token, run_rb_task, log, get_task_id_by_name
except ImportError as e:
    print(f"❌ Error importing 'utils' modules: {e}", file=sys.stderr)
    sys.exit(1)
# --- End Refactored Imports ---

# --- Constants ---
SOURCE_DIR = Path("_vendor_analysis_source")
CONFIG_DIR = Path("config")

# --- Core Logic: Text Compilation & Context ---

# parse_form_field is now imported from utils.rightbrain_api

# extract_vendor_usage_details is now imported from utils.rightbrain_api

def parse_data_processor_field(issue_body: str) -> str:
    """Parses the 'Data Processor' field from the issue body."""
    log("info", "Parsing data processor status from issue body...")
    return parse_form_field(issue_body, 'Data Processor')

# load_company_profile is now imported from utils.rightbrain_api

def parse_approved_documents(issue_body: str) -> Dict[str, Set[str]]:
    """
    Parses the issue body's checklist to find all checked files
    and their categories.
    """
    log("info", "Parsing approved documents from issue checklist...")
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
        log("warning", "No checked documents found in the issue body. Analysis may be empty.")

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
            log("warning", f"Checked file not found: '{file_path}'. Skipping.")
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Add the separator required by the AI tasks
            separator = f"\n\n--- DOCUMENT SEPARATOR ---\nSource URL: {file_path_str}\n\n"
            compiled_parts.append(separator + content)
            
        except Exception as e:
            log("warning", f"Error reading file '{file_path}': {e}. Skipping.")
            
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
        log("error", "Failed to format report", details=str(e))
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
    # Load .env file from project root if it exists (for local development)
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

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
    
    if not rb_api_url:
        sys.exit("❌ Error: Missing RB_API_URL environment variable.")

    if not all([gh_token, issue_body, issue_number, repo_name, rb_org_id, rb_project_id, 
                rb_client_id, rb_client_secret, rb_api_url]):
        sys.exit("❌ Error: Missing one or more required environment variables.")

    # Construct API root (ensure it includes /api/v1)
    rb_api_root = rb_api_url.rstrip('/')
    if not rb_api_root.endswith('/api/v1'):
        rb_api_root = f"{rb_api_root}/api/v1"
    
    # Temporarily set API_ROOT for detect_environment to work
    original_api_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root

    print(f"🚀 Starting analysis for issue #{issue_number} in repo {repo_name}...")

    # Look up task IDs by name (will use detected environment)
    security_task_id = get_task_id_by_name("Vendor Security Posture Analyzer")
    legal_task_id = get_task_id_by_name("Sub-Processor Terms Analyzer")
    reporter_task_id = get_task_id_by_name("Vendor Risk Reporter")
    
    # Restore original API_ROOT if it existed
    if original_api_root:
        os.environ["API_ROOT"] = original_api_root
    elif "API_ROOT" in os.environ:
        del os.environ["API_ROOT"]

    if not all([security_task_id, legal_task_id, reporter_task_id]):
        sys.exit("❌ Error: Could not find all required task IDs in manifest (security, legal, reporter).")

    # --- 2. Build Context Blocks (Refactored for Stage 2) ---
    company_profile = load_company_profile()
    vendor_usage_details = extract_vendor_usage_details(issue_body)
    # Phase 1.1 Update: Parse Relationship Owner separately for direct injection
    relationship_owner = parse_form_field(issue_body, 'Internal Contact')
    
    # --- 3. Determine Vendor Type Signal (Refactored for Stage 2) ---
    data_processor_status = parse_data_processor_field(issue_body)
    vendor_type_signal = "Processor" if data_processor_status.lower() == 'yes' else "General Supplier"
    log("info", f"Vendor type signal determined: {vendor_type_signal}")

    # --- 4. Parse Checklist and Compile Text ---
    approved_files = parse_approved_documents(issue_body)
    
    legal_docs_text = compile_text_from_files(approved_files["legal_files"])
    security_docs_text = compile_text_from_files(approved_files["security_files"])

    if not legal_docs_text and not security_docs_text:
        log("error", "No text compiled from any approved documents. Aborting analysis.")
        post_github_comment(repo_name, issue_number, 
                            "**Analysis Failed:** No approved documents were found or read. Please check the files in `_vendor_analysis_source` and ensure the correct items are checked in the issue checklist.")
        sys.exit()

    # --- 5. Run Analysis Tasks (Refactored for Stage 2) ---
    print("\n--- STAGE 5: Running Analysis Tasks ---")
    # Refactored to use new util function
    rb_token = get_rb_token()
    legal_analysis_json = {"status": "skipped", "reason": "No approved legal documents found."}
    security_analysis_json = {"status": "skipped", "reason": "No approved security documents found."}

    if legal_docs_text:
        legal_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": legal_docs_text
        }
        # Refactored to use new util function
        legal_analysis_run = run_rb_task(
            rb_token, legal_task_id, legal_input, "Sub-Processor Terms Analyzer"
        )
        legal_analysis_json = legal_analysis_run.get("response", {})
        if not legal_analysis_json or legal_analysis_run.get("is_error"):
             legal_analysis_json = {"error": "Task failed", "details": legal_analysis_run.get("response", "No response")}
    else:
        log("info", "No approved legal documents found. Skipping legal analysis.")

    if security_docs_text:
        security_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": security_docs_text
        }
        # Refactored to use new util function
        security_analysis_run = run_rb_task(
            rb_token, security_task_id, security_input, "Security Posture Analyzer"
        )
        security_analysis_json = security_analysis_run.get("response", {})
        if not security_analysis_json or security_analysis_run.get("is_error"):
            security_analysis_json = {"error": "Task failed", "details": security_analysis_run.get("response", "No response")}
    else:
        log("info", "No approved security documents found. Skipping security analysis.")

    # --- 6. Run Synthesis Task (Refactored for Stage 2) ---
    print("\n--- STAGE 6: Synthesizing Reports ---")
    security_json_string = json.dumps(security_analysis_json)
    legal_json_string = json.dumps(legal_analysis_json)
    
    reporter_input = {
        "company_profile": company_profile,
        "vendor_usage_details": vendor_usage_details,
        "vendor_type_signal": vendor_type_signal, # New signal
        # "relationship_owner": relationship_owner, # REMOVED PII: Handled locally
        "security_json_string": security_json_string,
        "legal_json_string": legal_json_string
    }

    # Refactored to use new util function
    report_run = run_rb_task(
        rb_token, reporter_task_id, reporter_input, "Vendor Risk Reporter"
    )
    report_json = report_run.get("response", {})

    # --- 7. Format and Post Results ---
    print("\n--- STAGE 7: Formatting and Posting Results ---")
    if not report_json or report_run.get("is_error"):
        log("error", "Synthesis task failed. Posting raw JSON as fallback.")
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
        log("success", "Synthesis complete. Injecting local data.")
        
        # --- DETERMINISTIC INJECTION BLOCK ---
        if "draft_approval_data" not in report_json:
            report_json["draft_approval_data"] = {}
        
        draft = report_json["draft_approval_data"]

        # 1. PII Injection
        draft["relationship_owner"] = relationship_owner
        
        # 2. Known Data Injection (Cheaper/Safer than AI)
        draft["processor_name"] = parse_form_field(issue_body, 'Supplier Name')
        draft["service_description"] = parse_form_field(issue_body, 'Service Description')
        draft["data_processing_status"] = vendor_type_signal
        
        # 3. Output Linking (AI Generated, but linked deterministically)
        draft["risk_rating"] = report_json.get("report", {}).get("overall_assessment", "Unknown")
        
        # 4. Safe Extraction from Legal JSON (Deterministically)
        # We try to grab the timeline from the legal analysis structure
        term_notice = "Check Legal Report"
        if legal_analysis_json:
            term_notice = legal_analysis_json.get("termination_rights", {}).get("for_convenience_timeline", "N/A")
        draft["termination_notice"] = term_notice

        print(f"Manually injected deterministic fields into draft_approval_data.")
        # -----------------------------------------------------------

        final_comment_body = format_report_as_markdown(
            report_json, security_analysis_json, legal_analysis_json
        )
    
    # Refactored to use new util function
    try:
        post_github_comment(repo_name, issue_number, final_comment_body)
    except Exception as e:
        log("error", "CRITICAL: Failed to post final comment to GitHub", details=str(e))
        
    log("success", "Analysis and reporting complete.")

if __name__ == "__main__":
    main()