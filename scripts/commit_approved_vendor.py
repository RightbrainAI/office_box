import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import unquote
from datetime import datetime

# --- Constants ---
PROCESSOR_DIR = Path("eng")
GENERAL_DIR = Path("general_vendors")
SOURCE_DIR = Path("_vendor_analysis_source")


def fetch_comments_and_approved_json(token, repo_name, issue_number):
    """
    Fetches all comments on an issue.
    Returns a tuple:
    1. The *last* "Reviewer-Approved Data" JSON block found.
    2. The full list of all comments for archival.
    """
    print(f"Fetching comments for issue {repo_name}#{issue_number}...")
    url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_comments = response.json() # This is our list for archival
    except requests.exceptions.RequestException as e:
        print(f"::error::Failed to fetch comments: {e}")
        sys.exit(1)

    json_pattern = re.compile(
        r"## 📝 Reviewer-Approved Data.*?```json\s*(\{.*?\})\s*```", 
        re.DOTALL
    )

    approved_json = None
    # Iterate comments in reverse (newest first) to find the most recent approval
    for comment in reversed(all_comments):
        comment_body = comment.get("body", "")
        match = re.search(json_pattern, comment_body)
        
        if match:
            print("Found 'Reviewer-Approved Data' JSON block in a comment.")
            try:
                approved_json = json.loads(match.group(1))
                break # Found the most recent one
            except json.JSONDecodeError:
                print(f"::error::Could not parse the JSON in the comment.")
                sys.exit(1)
    
    if not approved_json:
        print("::error::Could not find 'Reviewer-Approved Data' JSON block in any comment.")
        sys.exit(1)
        
    return approved_json, all_comments


def get_vendor_type(issue_body):
    """Determines the vendor type from the *original issue body*."""
    pattern = r"### Data Processor\s*(Yes|No)"
    match = re.search(pattern, issue_body, re.IGNORECASE)

    if match:
        if match.group(1).lower() == "yes":
            print("Vendor Type: Data Processor")
            return "processor"
        else: 
            print("Vendor Type: General Supplier")
            return "general"
    else:
        print("::warning::'Data Processor' section not found. Defaulting to General Supplier.")
        return "general"

def get_sanitized_vendor_name(summary_data):
    """Gets and sanitizes the vendor name for use in paths."""
    vendor_name = summary_data.get("processor_name", "unknown-vendor").lower()
    # Replace spaces and invalid characters with a hyphen
    vendor_name = re.sub(r"[^a-z0-9-]+", "-", vendor_name).strip("-")
    if not vendor_name:
        vendor_name = "unknown-vendor"
    return vendor_name

def update_central_json(summary_data, vendor_type):
    """Reads, updates, and writes to the correct central JSON file."""
    processor_name = summary_data.get("processor_name")
    if not processor_name or processor_name == "N/A":
        print("::warning::Skipping JSON update because processor name is missing or N/A.")
        return

    try:
        closed_at_str = os.getenv("ISSUE_CLOSED_AT")
        if not closed_at_str:
            print("::warning:: ISSUE_CLOSED_AT env var not found. Using today's date.")
            closed_date = datetime.utcnow()
        else:
            closed_date = datetime.fromisoformat(closed_at_str.rstrip("Z"))
        
        summary_data["last_review_date"] = closed_date.strftime("%Y-%m-%d")

        # Calculate next review date based on risk
        risk = summary_data.get("risk_rating", "Medium").lower()
        review_days = 365 # Default to 1 year
        if risk == "high":
            review_days = 180 # 6 months
        elif risk == "low":
            review_days = 730 # 2 years
        
        next_review_date = closed_date + timedelta(days=review_days)
        summary_data["next_review_date"] = next_review_date.strftime("%Y-%m-%d")
        print(f"Set last_review_date: {summary_data['last_review_date']}")
        print(f"Set next_review_date: {summary_data['next_review_date']} (Risk: {risk}, Days: {review_days})")

    except Exception as e:
        print(f"::error::Failed to calculate review dates: {e}")
        # Assign placeholder dates so the schema remains consistent
        summary_data["last_review_date"] = "N/A"
        summary_data["next_review_date"] = "N/A"

    if vendor_type == "processor":
        json_path = PROCESSOR_DIR / "data-processors.json"
    else:
        json_path = GENERAL_DIR / "all-general-vendors.json"

    json_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(json_path, 'r', encoding='utf-8') as f: 
            all_records = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): 
        all_records = []

    record_found = False
    for i, record in enumerate(all_records):
        if record.get("processor_name") == processor_name:
            all_records[i] = summary_data
            record_found = True
            print(f"Updated existing record for '{processor_name}'.")
            break
            
    if not record_found: 
        all_records.append(summary_data)
        print(f"Added new record for '{processor_name}'.")

    # Sort by processor_name for consistency in git diffs
    all_records.sort(key=lambda x: x.get("processor_name", "").lower())

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)
    print(f"Successfully updated {json_path}.")

def create_audit_markdown_file(full_issue_body, all_comments, issue_url, vendor_type, sanitized_vendor_name):
    """
    Creates the permanent Markdown audit file, including the
    original issue body and all comments.
    """
    if vendor_type == "processor":
        file_path = PROCESSOR_DIR / f"{sanitized_vendor_name}/{sanitized_vendor_name}.md"
    else:
        file_path = GENERAL_DIR / f"{sanitized_vendor_name}/{sanitized_vendor_name}.md"

    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            # Add a link back to the original issue at the top
            f.write(f"# Vendor Audit: {sanitized_vendor_name.capitalize()}\n\n")
            f.write(f"**Original Issue:** [{issue_url}]({issue_url})\n\n")
            f.write("---\n\n")
            
            # Write the original issue body
            f.write("## Original Request\n\n")
            f.write(full_issue_body)
            f.write("\n\n---\n\n")
            
            # Write all comments
            f.write("## Issue Discussion & Analysis\n\n")
            if not all_comments:
                f.write("*No comments found on the issue.*\n")
            
            for comment in all_comments:
                author = comment.get("user", {}).get("login", "unknown")
                body = comment.get("body", "*No comment body*")
                created_at = comment.get("created_at", "unknown date")
                
                f.write(f"### Comment from @{author} (at {created_at})\n\n")
                f.write(body)
                f.write("\n\n---\n\n")
                
        print(f"Created full audit file at: {file_path}")
    except IOError as e:
        print(f"::error::Failed to create audit file {file_path}: {e}")
        sys.exit(1)


def parse_files_from_checklist(issue_body, issue_number, check_status="[x]"):
    """
    Parses the issue body checklist for files (checked or unchecked) 
    associated with this issue.
    Returns a list of tuples: (Path(local_path), original_url)
    """
    # Regex to find:
    # - [x] or [ ]
    # A link to a local file from this issue, e.g., (_vendor_analysis_source/issue-46-....txt)
    # The original source URL, e.g., (https://...)
    pattern = re.compile(
        r"-\s*" + re.escape(check_status) +
        r".*?\[.*?\]\((?:.*?)" + 
        r"(_vendor_analysis_source/issue-" + re.escape(issue_number) + r".*?)\)" +
        r".*?\((https?://.*?)\)",
        re.IGNORECASE | re.DOTALL
    )
    
    matches = pattern.findall(issue_body)
    
    files = []
    for local_path_encoded, url in matches:
        try:
            local_path = Path(unquote(local_path_encoded))
            files.append((local_path, url))
        except Exception as e:
            print(f"::warning::Could not parse file path: {local_path_encoded}. Error: {e}")
            
    return files

def archive_approved_files(approved_files, vendor_type, sanitized_vendor_name, date_str):
    """
    Moves approved files to the vendor's permanent directory, prepending metadata.
    """
    if not approved_files:
        print("No approved files found in checklist to archive.")
        return

    if vendor_type == "processor":
        dest_dir = PROCESSOR_DIR / f"{sanitized_vendor_name}/approved-terms/{date_str}"
    else:
        dest_dir = GENERAL_DIR / f"{sanitized_vendor_name}/approved-terms/{date_str}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Archiving approved terms to: {dest_dir}")

    for local_path, original_url in approved_files:
        if not local_path.exists():
            print(f"::warning::File {local_path} was checked but not found. Skipping.")
            continue
        
        # Sanitize the original filename part
        # e.g., "issue-46-Main_T&Cs.txt" -> "Main_T&Cs.txt"
        original_name = local_path.name.split('-', 2)[-1]
        new_path = dest_dir / original_name

        try:
            content = local_path.read_text(encoding="utf-8")
            
            # Prepend the metadata header
            with new_path.open("w", encoding="utf-8") as f:
                f.write(f"Original Source URL: {original_url}\n")
                f.write(f"Approved on: {date_str}\n")
                f.write("-" * 20 + "\n\n")
                f.write(content)
                
            print(f"Archived: {new_path}")
            
        except Exception as e:
            print(f"::error::Failed to archive {local_path}: {e}")

def cleanup_source_directory(issue_body, issue_number):
    """
    Deletes *all* files (checked or unchecked) for this issue 
    from the _vendor_analysis_source directory.
    """
    print(f"Cleaning up source files for issue {issue_number}...")
    
    # Find all files, checked "[x]" or unchecked "[ ]"
    checked_files, _ = zip(*parse_files_from_checklist(issue_body, issue_number, "[x]")) if parse_files_from_checklist(issue_body, issue_number, "[x]") else ([], [])
    unchecked_files, _ = zip(*parse_files_from_checklist(issue_body, issue_number, "[ ]")) if parse_files_from_checklist(issue_body, issue_number, "[ ]") else ([], [])
    
    all_files_for_issue = set(checked_files) | set(unchecked_files)

    if not all_files_for_issue:
        print("No source files found in checklist to clean up.")
        return

    for local_path in all_files_for_issue:
        if local_path.exists():
            try:
                local_path.unlink()
                print(f"Cleaned up {local_path}")
            except OSError as e:
                print(f"::warning::Could not delete {local_path}: {e}")
        else:
            # This is not an error, it might have been an offline file that was never added
            print(f"Source file {local_path} not found; skipping cleanup for it.")

def main():
    load_dotenv()
    
    # 1. Get all required environment variables
    issue_body = os.getenv("ISSUE_BODY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("REPO_NAME")
    issue_number = os.getenv("ISSUE_NUMBER")
    issue_closed_at = os.getenv("ISSUE_CLOSED_AT") 
    issue_url = os.getenv("ISSUE_URL")

    if not all([issue_body, github_token, repo_name, issue_number, issue_closed_at, issue_url]):
        print("::error::Missing one or more required environment variables.")
        print("::error::Requires: ISSUE_BODY, GITHUB_TOKEN, REPO_NAME, ISSUE_NUMBER, ISSUE_CLOSED_AT, ISSUE_URL")
        sys.exit(1)

    # 2. Parse common data
    vendor_type = get_vendor_type(issue_body)
    
    summary_data, all_comments = fetch_comments_and_approved_json(
        github_token, repo_name, issue_number
    )
    
    vendor_name = get_sanitized_vendor_name(summary_data)
    date_str = datetime.fromisoformat(issue_closed_at.rstrip("Z")).strftime("%Y-%m-%d")

    # 3. Update the central JSON database
    update_central_json(summary_data, vendor_type)
    
    # 4. Create the permanent audit file (body + all comments)
    create_audit_markdown_file(issue_body, all_comments, issue_url, vendor_type, vendor_name)
    
    # 5. Archive the approved source text files
    approved_files = parse_files_from_checklist(issue_body, issue_number, "[x]")
    archive_approved_files(approved_files, vendor_type, vendor_name, date_str)
    
    # 6. Clean up all source files for this issue
    cleanup_source_directory(issue_body, issue_number)
    
    print("\n✅ Vendor commit and archive process complete.")

if __name__ == "__main__":
    main()