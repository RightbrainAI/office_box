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
    from utils.rightbrain_api import get_rb_token, run_rb_task, log, get_task_id_by_name, get_api_root, get_rb_config
except ImportError as e:
    print(f"❌ Error importing 'utils' modules: {e}", file=sys.stderr)
    sys.exit(1)
# --- End Refactored Imports ---

# --- Constants ---
SOURCE_DIR = Path("_vendor_analysis_source")
CONFIG_DIR = Path("config")

# --- Core Logic: Text Compilation & Context ---

def parse_data_processor_field(issue_body: str) -> str:
    """Parses the 'Data Processor' field from the issue body."""
    log("info", "Parsing data processor status from issue body...")
    return parse_form_field(issue_body, 'Data Processor')

def parse_approved_documents(issue_body: str) -> Dict[str, Set[str]]:
    """
    Parses the issue body's checklist to find all checked files
    and their categories.
    """
    log("info", "Parsing approved documents from issue checklist...")
    legal_files: Set[str] = set()
    security_files: Set[str] = set()
    
    pattern = re.compile(
        r"-\s*\[x\]\s*\*\*(.*?)\*\*:.*?\((?:https://.*?/blob/main/)?(_vendor_analysis_source/.*?)\)",
        re.IGNORECASE
    )
    
    matches = pattern.findall(issue_body)
    
    if not matches:
        log("warning", "No checked documents found in the issue body. Analysis may be empty.")

    for categories_str, file_path_raw in matches:
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
            separator = f"\n\n--- DOCUMENT SEPARATOR ---\nSource URL: {file_path_str}\n\n"
            compiled_parts.append(separator + content)
            
        except Exception as e:
            log("warning", f"Error reading file '{file_path}': {e}. Skipping.")
            
    return "".join(compiled_parts)

# --- Helper: Report Formatting ---

def format_report_as_markdown(report_data: Dict[str, Any], 
                            raw_security_json: Dict[str, Any], 
                            raw_legal_json: Dict[str, Any],
                            raw_media_json: Dict[str, Any]) -> str:
    """Formats the synthesis task's JSON into a human-readable Markdown comment."""
    
    try:
        report = report_data.get("report", {})
        draft_data = report_data.get("draft_approval_data", {})
        
        # Determine Status Icon based on overall assessment
        assessment = report.get('overall_assessment', 'Unknown')
        status_icon = "🟢" if "Low" in assessment else "aaa" if "Medium" in assessment else "🔴"

        # Build positive findings
        pos_findings_md_list = []
        for f in report.get("positive_findings", []):
            pos_findings_md_list.append(f"* **{f.get('finding', 'N/A')}:** {f.get('summary', 'N/A')}")
        pos_findings_md = "\n".join(pos_findings_md_list) or "None identified."

        # Build legal risks
        legal_risks_md_list = []
        for r in report.get("key_legal_risks", []):
            legal_risks_md_list.append(f"* **Risk:** {r.get('risk', 'N/A')}\n  * **Summary:** {r.get('summary', 'N/A')}\n  * **Recommendation:** {r.get('recommendation', 'N/A')}")
        legal_risks_md = "\n".join(legal_risks_md_list) or "No critical legal risks identified."

        # Build security gaps
        sec_gaps_md_list = []
        for g in report.get("key_security_gaps", []):
            sec_gaps_md_list.append(f"* **Gap:** {g.get('gap', 'N/A')}\n  * **Summary:** {g.get('summary', 'N/A')}\n  * **Recommendation:** {g.get('recommendation', 'N/A')}")
        sec_gaps_md = "\n".join(sec_gaps_md_list) or "No critical security gaps identified."

        # Build Adverse Media Summary
        media_summary = report.get("adverse_media_summary", {})
        media_risk = media_summary.get("risk_level", "Unknown")
        media_text = media_summary.get("key_findings_summary", "No adverse media analysis available.")
        
        media_icon = "🟢" if media_risk == "LOW" else "aaa" if media_risk == "MEDIUM" else "🔴"
        media_section = f"### {media_icon} Reputation & Adverse Media: {media_risk}\n{media_text}"

        # Build the final comment
        comment_parts = [
            f"## {status_icon} AI-Generated Risk Summary",
            f"### **Overall Assessment: {assessment}**",
            f"**Executive Summary:** {report.get('executive_summary', 'N/A')}",
            "\n### ✅ Positive Findings",
            pos_findings_md,
            "\n### ⚖️ Key Legal Risks",
            legal_risks_md,
            "\n### 🛡️ Key Security Gaps",
            sec_gaps_md,
            f"\n{media_section}",
            "\n---",
            "\n## 📝 Reviewer-Approved Data (Draft)",
            "Please review, edit, and confirm the details below. This JSON block will be committed to the central vendor registry upon issue closure.",
            "\n**ACTION REQUIRED:** Before closing this issue, please **edit the `mitigations` field** (and any others) in the JSON block below to reflect the final, agreed-upon controls.",
            f"```json\n{json.dumps(draft_data, indent=2)}\n```",
            "\n---",
            "\n## 🤖 Raw Analysis Data (for review)",
            "<details><summary>🛡️ Security Posture Analysis (Raw)</summary>",
            f"```json\n{json.dumps(raw_security_json, indent=2)}\n```",
            "</details>",
            "<details><summary>⚖️ Legal & DPA Analysis (Raw)</summary>",
            f"```json\n{json.dumps(raw_legal_json, indent=2)}\n```",
            "</details>",
            "<details><summary>📰 Adverse Media Analysis (Raw)</summary>",
            f"```json\n{json.dumps(raw_media_json, indent=2)}\n```",
            "</details>"
        ]
        return "\n".join(comment_parts)
        
    except Exception as e:
        log("error", "Failed to format report", details=str(e))
        return (
            "## 🤖 Vendor Analysis Results (Fallback)\n\n"
            "Error formatting the AI-generated report. Please review the raw JSON outputs.\n\n"
            "### 📊 Synthesis Report\n"
            f"```json\n{json.dumps(report_data, indent=2)}\n```"
        )

# --- Main Execution ---

def main():
    # Load .env file from project root if it exists
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # --- 1. Load Config & Environment Variables ---
    gh_token = os.environ.get("GITHUB_TOKEN")
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    repo_name = os.environ.get("REPO_NAME")
    
    get_rb_config()
    rb_api_root = get_api_root()

    if not all([gh_token, issue_body, issue_number, repo_name]):
        sys.exit("❌ Error: Missing one or more required environment variables.")
    
    # Temporarily set API_ROOT
    original_api_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root

    print(f"🚀 Starting analysis for issue #{issue_number} in repo {repo_name}...")

    # Look up task IDs by name
    security_task_id = get_task_id_by_name("Vendor Security Posture Analyzer")
    legal_task_id = get_task_id_by_name("Sub-Processor Terms Analyzer")
    reporter_task_id = get_task_id_by_name("Vendor Risk Reporter")
    media_task_id = get_task_id_by_name("Adverse Media Screener") # New Task
    
    if original_api_root:
        os.environ["API_ROOT"] = original_api_root
    elif "API_ROOT" in os.environ:
        del os.environ["API_ROOT"]

    if not all([security_task_id, legal_task_id, reporter_task_id, media_task_id]):
        sys.exit("❌ Error: Could not find all required task IDs in manifest.")

    # --- 2. Build Context Blocks ---
    company_profile = load_company_profile()
    vendor_usage_details = extract_vendor_usage_details(issue_body)
    relationship_owner = parse_form_field(issue_body, 'Internal Contact')
    
    # NEW: Extract Vendor Name early for Adverse Media check
    vendor_name = parse_form_field(issue_body, 'Supplier Name')
    if not vendor_name:
        vendor_name = "Unknown Vendor"

    # --- 3. Determine Vendor Type Signal ---
    data_processor_status = parse_data_processor_field(issue_body)
    vendor_type_signal = "Processor" if data_processor_status.lower() == 'yes' else "General Supplier"

    # --- 4. Parse Checklist and Compile Text ---
    approved_files = parse_approved_documents(issue_body)
    legal_docs_text = compile_text_from_files(approved_files["legal_files"])
    security_docs_text = compile_text_from_files(approved_files["security_files"])

    if not legal_docs_text and not security_docs_text:
        log("warning", "No documents compiled. Analysis will rely primarily on Adverse Media checks.")

    # --- 5. Run Analysis Tasks ---
    print("\n--- STAGE 5: Running Analysis Tasks ---")
    rb_token = get_rb_token()
    
    # Initialize defaults
    legal_analysis_json = {"status": "skipped", "reason": "No approved legal documents found."}
    security_analysis_json = {"status": "skipped", "reason": "No approved security documents found."}
    media_analysis_json = {"status": "skipped", "reason": "Task execution failed"}

    # A. Legal Analysis
    if legal_docs_text:
        legal_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": legal_docs_text
        }
        legal_run = run_rb_task(rb_token, legal_task_id, legal_input, "Sub-Processor Terms Analyzer")
        legal_analysis_json = legal_run.get("response", {}) or legal_analysis_json

    # B. Security Analysis
    if security_docs_text:
        security_input = {
            "company_profile": company_profile,
            "vendor_usage_details": vendor_usage_details,
            "consolidated_text": security_docs_text
        }
        sec_run = run_rb_task(rb_token, security_task_id, security_input, "Security Posture Analyzer")
        security_analysis_json = sec_run.get("response", {}) or security_analysis_json

    # C. Adverse Media Analysis (New)
    print(f"🕵️‍♂️ Running Adverse Media Check for: {vendor_name}")
    media_input = {"vendor": vendor_name}
    media_run = run_rb_task(rb_token, media_task_id, media_input, "Adverse Media Screener")
    media_analysis_json = media_run.get("response", {}) or media_analysis_json

    # --- 6. Run Synthesis Task ---
    print("\n--- STAGE 6: Synthesizing Reports ---")
    
    reporter_input = {
        "company_profile": company_profile,
        "vendor_usage_details": vendor_usage_details,
        "vendor_type_signal": vendor_type_signal,
        "security_json_string": json.dumps(security_analysis_json),
        "legal_json_string": json.dumps(legal_analysis_json),
        "adverse_media_json_string": json.dumps(media_analysis_json) # Passed to reporter
    }

    report_run = run_rb_task(rb_token, reporter_task_id, reporter_input, "Vendor Risk Reporter")
    report_json = report_run.get("response", {})

    # --- 7. Format and Post Results ---
    print("\n--- STAGE 7: Formatting and Posting Results ---")
    if not report_json or report_run.get("is_error"):
        log("error", "Synthesis task failed. Posting raw JSON as fallback.")
        final_comment_body = format_report_as_markdown({}, security_analysis_json, legal_analysis_json, media_analysis_json)
    else:
        log("success", "Synthesis complete. Injecting local data.")
        
        if "draft_approval_data" not in report_json:
            report_json["draft_approval_data"] = {}
        
        draft = report_json["draft_approval_data"]
        draft["relationship_owner"] = relationship_owner
        draft["processor_name"] = vendor_name
        draft["service_description"] = parse_form_field(issue_body, 'Service Description')
        draft["data_processing_status"] = vendor_type_signal
        draft["risk_rating"] = report_json.get("report", {}).get("overall_assessment", "Unknown")
        
        # Attempt to grab termination notice from legal findings if available
        term_notice = "Check Legal Report"
        if isinstance(legal_analysis_json, dict):
             term_notice = legal_analysis_json.get("termination_rights", {}).get("for_convenience_timeline", "N/A")
        draft["termination_notice"] = term_notice

        final_comment_body = format_report_as_markdown(
            report_json, security_analysis_json, legal_analysis_json, media_analysis_json
        )
    
    try:
        post_github_comment(repo_name, issue_number, final_comment_body)
    except Exception as e:
        log("error", "CRITICAL: Failed to post final comment to GitHub", details=str(e))
        
    log("success", "Analysis and reporting complete.")

if __name__ == "__main__":
    main()