import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import unquote
from datetime import datetime, timedelta

# --- Refactored Imports ---
sys.path.append(str(Path(__file__).parent.parent))
try:
    from utils.github_api import fetch_issue_comments, get_vendor_type, get_sanitized_vendor_name
    from utils.rightbrain_api import log
except ImportError:
    print("❌ Error: Could not import 'utils'.", file=sys.stderr)
    sys.exit(1)
# --- End Imports ---

# --- Constants ---
SUPPLIERS_ROOT = Path("suppliers")
PROCESSOR_DIR = SUPPLIERS_ROOT / "subprocessors"
GENERAL_DIR = SUPPLIERS_ROOT / "general_vendors"
SOURCE_DIR = Path("_vendor_analysis_source")

# ... [fetch_comments_and_approved_json function remains unchanged] ...
def fetch_comments_and_approved_json(repo_name, issue_number):
    """Fetches comments and the approved JSON block."""
    all_comments = fetch_issue_comments(repo_name, issue_number)
    json_pattern = re.compile(r"## 📝 Reviewer-Approved Data.*?```json\s*(\{.*?\})\s*```", re.DOTALL)

    approved_json = None
    for comment in reversed(all_comments):
        match = re.search(json_pattern, comment.get("body", ""))
        if match:
            try:
                approved_json = json.loads(match.group(1))
                break
            except json.JSONDecodeError: continue
    
    if not approved_json:
        sys.exit("❌ Error: No approved JSON found in comments.")
        
    return approved_json, all_comments

# get_vendor_type and get_sanitized_vendor_name are now imported from utils.github_api

# ... [update_central_json function remains unchanged] ...
# (This logic is already correct; it updates dates and overwrites the JSON record)

def update_central_json(summary_data, vendor_type):
    """Updates the central JSON registry."""
    # [Implementation from previous version is correct and retained]
    # ... (Calculates next review date and updates JSON file) ...
    # For brevity in this diff, assuming the logic from your upload
    
    processor_name = summary_data.get("processor_name")
    if not processor_name: return

    # Recalculate dates (Copied from previous provided code)
    closed_at_str = os.getenv("ISSUE_CLOSED_AT")
    closed_date = datetime.utcnow()
    if closed_at_str:
        closed_date = datetime.fromisoformat(closed_at_str.rstrip("Z"))
    
    summary_data["last_review_date"] = closed_date.strftime("%Y-%m-%d")
    
    # Calculate next review
    risk = summary_data.get("risk_rating", "Medium").lower()
    days = 180 if risk == "high" else (730 if risk == "low" else 365)
    summary_data["next_review_date"] = (closed_date + timedelta(days=days)).strftime("%Y-%m-%d")

    # Select File
    target_file = (PROCESSOR_DIR / "data-processors.json") if vendor_type == "processor" else (GENERAL_DIR / "all-general-vendors.json")
    target_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(target_file, 'r') as f: 
            all_records = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): 
        all_records = []

    # Update or Append
    found = False
    for i, rec in enumerate(all_records):
        if rec.get("processor_name") == processor_name:
            all_records[i] = summary_data
            found = True
            break
    if not found: all_records.append(summary_data)
    
    all_records.sort(key=lambda x: x.get("processor_name", "").lower())
    
    with open(target_file, 'w') as f: json.dump(all_records, f, indent=2)
    print(f"✅ Updated JSON registry at {target_file}")


def create_audit_markdown_file(full_issue_body, all_comments, issue_url, vendor_type, sanitized_vendor_name):
    """
    Creates OR Appends to the permanent Markdown audit file.
    """
    base_dir = PROCESSOR_DIR if vendor_type == "processor" else GENERAL_DIR
    file_path = base_dir / f"{sanitized_vendor_name}/{sanitized_vendor_name}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine Context (New vs Update)
    is_update = file_path.exists()
    mode = 'a' if is_update else 'w'
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        with open(file_path, mode, encoding='utf-8') as f:
            
            if is_update:
                # Append Header
                f.write(f"\n\n---\n\n")
                f.write(f"# 🔄 Review: {timestamp}\n\n")
                f.write(f"**Review Issue:** [{issue_url}]({issue_url})\n\n")
            else:
                # New File Header
                f.write(f"# Vendor Audit: {sanitized_vendor_name.capitalize()}\n\n")
                f.write(f"**Original Issue:** [{issue_url}]({issue_url})\n\n")
                f.write("---\n\n")

            # Write Content (Same format for both)
            f.write("## 📄 Context & Request\n\n")
            f.write(full_issue_body)
            f.write("\n\n---\n\n")
            
            f.write("## 💬 Discussion & Analysis Log\n\n")
            if not all_comments:
                f.write("*No comments found on the issue.*\n")
            
            for comment in all_comments:
                author = comment.get("user", {}).get("login", "unknown")
                body = comment.get("body", "*No comment body*")
                created_at = comment.get("created_at", "unknown")
                
                f.write(f"### @{author} ({created_at})\n")
                f.write(body)
                f.write("\n\n")
                
        print(f"✅ Audit file updated at: {file_path}")
        
    except IOError as e:
        log("error", f"Failed to write audit file {file_path}", details=str(e))
        sys.exit(1)

# ... [parse_files_from_checklist, archive_approved_files, cleanup_source_directory remain unchanged] ...
# (Copy these verbatim from your uploaded file)
def parse_files_from_checklist(issue_body, issue_number, check_status="[x]"):
    pattern = re.compile(
        r"-\s*" + re.escape(check_status) + r".*?\[.*?\]\((?:.*?)(" + 
        r"_vendor_analysis_source/issue-" + re.escape(issue_number) + r".*?)\)" +
        r".*?\((https?://.*?)\)", re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(issue_body)
    return [(Path(unquote(p)), u) for p, u in matches]

def archive_approved_files(approved_files, vendor_type, sanitized_vendor_name, date_str):
    if not approved_files: return
    base_dir = PROCESSOR_DIR if vendor_type == "processor" else GENERAL_DIR
    dest_dir = base_dir / f"{sanitized_vendor_name}/approved-terms/{date_str}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    for local_path, url in approved_files:
        if not local_path.exists(): continue
        try:
            new_path = dest_dir / local_path.name.split('-', 2)[-1]
            content = f"Original Source: {url}\nApproved: {date_str}\n{'-'*20}\n\n{local_path.read_text(encoding='utf-8')}"
            new_path.write_text(content, encoding='utf-8')
        except Exception as e: print(f"Error archiving {local_path}: {e}")

def cleanup_source_directory(issue_body, issue_number):
    checked = parse_files_from_checklist(issue_body, issue_number, "[x]")
    unchecked = parse_files_from_checklist(issue_body, issue_number, "[ ]")
    for p, _ in (checked + unchecked):
        if p.exists(): p.unlink()

def main():
    load_dotenv()
    
    # 1. Inputs
    issue_body = os.getenv("ISSUE_BODY")
    repo_name = os.getenv("REPO_NAME")
    issue_number = os.getenv("ISSUE_NUMBER")
    issue_closed_at = os.getenv("ISSUE_CLOSED_AT") 
    issue_url = os.getenv("ISSUE_URL")

    if not all([issue_body, repo_name, issue_number, issue_closed_at, issue_url]):
        sys.exit("❌ Error: Missing required env vars (ISSUE_BODY, REPO_NAME, NUMBER, CLOSED_AT, URL)")

    # 2. Logic
    vendor_type = get_vendor_type(issue_body)
    approved_json, all_comments = fetch_comments_and_approved_json(repo_name, issue_number)
    vendor_name = get_sanitized_vendor_name(approved_json)
    date_str = datetime.fromisoformat(issue_closed_at.rstrip("Z")).strftime("%Y-%m-%d")

    # 3. Execution
    update_central_json(approved_json, vendor_type)
    
    # THIS is the key change: calling the logic that handles both New and Existing
    create_audit_markdown_file(issue_body, all_comments, issue_url, vendor_type, vendor_name)
    
    approved_files = parse_files_from_checklist(issue_body, issue_number, "[x]")
    archive_approved_files(approved_files, vendor_type, vendor_name, date_str)
    
    cleanup_source_directory(issue_body, issue_number)
    
    log("success", "Vendor commit and archive process complete.")

if __name__ == "__main__":
    main()