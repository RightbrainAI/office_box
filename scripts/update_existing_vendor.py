import os
import sys
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# --- Import Utils ---
sys.path.append(str(Path(__file__).parent.parent))
try:
    from utils.github_api import create_github_issue, post_github_comment, parse_form_field, get_vendor_type_from_path
    from utils.rightbrain_api import log
except ImportError:
    print("❌ Error: Could not import 'utils'.", file=sys.stderr)
    sys.exit(1)

def parse_existing_vendor_file(file_path: Path) -> dict:
    """
    Reads the existing markdown file to extract context for the review.
    """
    if not file_path.exists():
        sys.exit(f"❌ Error: File not found at {file_path}")

    content = file_path.read_text(encoding="utf-8")
    
    # 1. Vendor Name (Inferred from filename if not in text)
    # Assumes filename is "vendor-name.md"
    vendor_name_guess = file_path.stem.replace("-", " ").title()
    
    # 2. Extract Data using parse_form_field from utils
    # Try to extract from the "Original Request" section first, then fallback to defaults
    usage_context = parse_form_field(content, "Vendor/Service Usage Context")
    if usage_context == "N/A":
        usage_context = "Reviewer to update."
    
    data_types = parse_form_field(content, "Data Types Involved")
    if data_types == "N/A":
        data_types = "Reviewer to update."
    
    service_desc = parse_form_field(content, "Service Description")
    if service_desc == "N/A":
        service_desc = "Reviewer to update."
    
    # 3. Determine Vendor Type based on path
    vendor_type = get_vendor_type_from_path(str(file_path))
    is_processor = vendor_type == "processor"
    
    return {
        "name": vendor_name_guess,
        "is_processor": is_processor,
        "usage_context": usage_context,
        "data_types": data_types,
        "service_desc": service_desc
    }

def construct_issue_body(data: dict, file_path: str) -> str:
    """
    Builds the Issue Body compliant with discover_documents.py
    """
    vendor_type_str = "Yes" if data["is_processor"] else "No"
    
    body = f"""
### Vendor Review: {data['name']}

**Source File:** `{file_path}`

---

### Supplier Name
{data['name']}

### Service Description
{data['service_desc']}

### Vendor/Service Usage Context
{data['usage_context']}

### Data Types Involved
{data['data_types']}

### Data Processor
{vendor_type_str}

### T&Cs
*(Paste new URL here)*

### Security Documents URL
*(Paste new URL here)*

### Internal Contact
@Reference-Owner

---
## Documents for Analysis
*Waiting for discovery...*
    """
    return body

def main():
    load_dotenv()
    
    # Inputs from Workflow
    vendor_file_path_str = os.getenv("VENDOR_FILE_PATH")
    repo_name = os.getenv("REPO_NAME")
    
    if not all([vendor_file_path_str, repo_name]):
        sys.exit("❌ Error: Missing VENDOR_FILE_PATH or REPO_NAME.")

    file_path = Path(vendor_file_path_str)
    
    print(f"🚀 Initiating Review for: {file_path.name}")
    
    # 1. Parse Existing Data
    vendor_data = parse_existing_vendor_file(file_path)
    
    # 2. Construct Issue Body
    issue_title = f"🔄 Vendor Review: {vendor_data['name']}"
    issue_body = construct_issue_body(vendor_data, vendor_file_path_str)
    
    # 3. Create Issue
    # We do NOT add 'ready-for-analysis' yet. The user must add the URL first.
    try:
        issue_data = create_github_issue(
            repo=repo_name,
            title=issue_title,
            body=issue_body,
            labels=["vendor-onboarding"] 
        )
        
        print(f"✅ Issue Created: {issue_data.get('html_url')}")
        
        # Optional: Add a comment tagging the user?
        # post_github_comment(repo_name, issue_data['number'], "Please update the **T&Cs URL** in the issue description and add the label `ready-for-discovery`.")

    except Exception as e:
        sys.exit(f"❌ Failed to create issue: {e}")

if __name__ == "__main__":
    main()