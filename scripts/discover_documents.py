import os
import sys
import json
import re
import requests
import subprocess
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote as url_quote # Needed for creating safe URLs
from utils.github_api import update_issue_body, post_failure_and_exit
from utils.rightbrain_api import get_rb_token, run_rb_task

# --- Helper: Filename Sanitization ---

def create_safe_filename(name: str, issue_number: str) -> str:
    """Creates a safe filename for saving document text."""
    # Remove potentially problematic characters like slashes, colons, etc.
    safe_name = re.sub(r'[<>:"/\\|?*\s]+', '_', name)
    # Basic sanitization against leading/trailing dots or spaces
    safe_name = safe_name.strip('._ ')
    # Handle potentially empty names after sanitization
    if not safe_name:
        safe_name = "unnamed_document"
    # Truncate if too long (common filesystem limit is 255 bytes, be conservative)
    safe_name = safe_name[:100]
    return f"issue-{issue_number}-{safe_name}.txt"

# --- Helper: GitHub & Manifest ---

def parse_urls_from_issue_form(issue_body: str, label: str) -> List[str]:
    """Parses a URL from a GitHub issue form body based on its markdown label."""
    # REFACTORED: Use \s+ to flexibly match any whitespace (including newlines)
    # between the label and the URL. This is more robust.
    pattern = re.compile(f"### {label}\\s+(https?://[^\s`<>\"']+)", re.IGNORECASE)
    match = pattern.search(issue_body)
    if not match:
        return []
    return [match.group(1).strip()]

def parse_text_from_issue_form(issue_body: str, label: str) -> str:
    """Parses a text block from a GitHub issue form body based on its markdown label."""
    # This pattern captures everything until the next markdown heading or end of string
    pattern = re.compile(f"### {label}\\s*\\n(.*?)(?=\\n###|\\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(issue_body)
    if not match:
        return ""
    # Clean up the captured text
    return match.group(1).strip()


def load_task_manifest() -> Dict[str, str]:
    """Loads the task_manifest.json file."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    manifest_path = project_root / "tasks" / "task_manifest.json"
    if not manifest_path.exists():
        sys.exit(f"❌ Error: Task manifest not found at '{manifest_path}'.")
    with open(manifest_path, 'r') as f:
        return json.load(f)

# --- Helper: Text Compilation & Git ---

def save_and_commit_source_text(text: str, repo_name: str, issue_number: str, filename: str):
    """Saves a single document's text to a file and commits it."""
    source_dir = Path("_vendor_analysis_source")
    source_dir.mkdir(exist_ok=True)
    file_path = source_dir / filename

    # Only write if text is not empty
    if not text or not text.strip():
        print(f"ℹ️ Skipping save for '{filename}' due to empty content.")
        return

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"📝 Saved source text to '{file_path}'.")
    except IOError as e:
        print(f"❌ Error writing file {file_path}: {e}")
        # Continue script execution if one file fails? Or exit? Let's continue for now.
        return

    try:
        print(f"🚀 Committing '{filename}'...")
        # Configure git user for this action
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True, capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True, capture_output=True)

        # Add the specific file
        subprocess.run(["git", "add", str(file_path)], check=True, capture_output=True)

        # Check if there are changes to commit for *this* file
        status_result = subprocess.run(["git", "status", "--porcelain", str(file_path)], capture_output=True, text=True)

        if file_path.name in status_result.stdout:
            # Extract a meaningful name for the commit message
            doc_name_part = filename.replace(f"issue-{issue_number}-", "").replace(".txt", "").replace("_", " ")
            commit_message = f"docs(vendor): Add source text for '{doc_name_part}' (issue #{issue_number})"

            # Try to commit
            commit_result = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)
            if commit_result.returncode != 0:
                 # Handle potential commit failure (e.g., empty commit)
                 if "nothing to commit" in commit_result.stdout or "nothing added to commit" in commit_result.stderr:
                     print(f"ℹ️ No changes detected for '{filename}' to commit.")
                     return # Nothing more to do for this file
                 else:
                    print(f"❌ Git commit failed for '{filename}': {commit_result.stderr}")
                    # Decide if we should exit or continue trying other files
                    return # Continue for now

            # Pull remote changes before pushing
            print("Pulling remote changes before pushing...")
            pull_result = subprocess.run(["git", "pull", "--rebase"], check=True, capture_output=True, text=True)
            print(f"Git pull output:\n{pull_result.stdout}")

            # Push the commit
            push_result = subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
            print(f"✅ Source text '{filename}' committed and pushed successfully.")
            print(f"Git push output:\n{push_result.stdout}")

        else:
            print(f"ℹ️ No changes detected for '{filename}'. Already up-to-date.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed for '{filename}': {e}")
        print(f"Command: {' '.join(e.cmd)}")
        # e.stderr and e.stdout are already strings because text=True was used
        print(f"Stderr: {e.stderr if e.stderr else 'N/A'}")
        print(f"Stdout: {e.stdout if e.stdout else 'N/A'}")
        # Consider whether to exit or just warn
        print("⚠️ Warning: Failed to commit or push. Manual check may be required.")
    except FileNotFoundError:
        # Handle case where git is not installed
        sys.exit("❌ Git command not found. Please ensure Git is installed in your Actions runner.")
    except Exception as e:
        # Catch any other unexpected errors during git operations
        print(f"❌ An unexpected error occurred during git operations for '{filename}': {e}")
        print("⚠️ Warning: Failed to commit or push. Manual check may be required.")


def extract_text_from_run_data(full_task_run: Dict[str, Any]) -> str:
    """
    Extracts the fetched text from the 'run_data.submitted.document_url' field.
    This assumes the classifier task's input param was 'document_url'.
    """
    try:
        # The fetched text is stored in run_data.submitted keyed by the param_name used in input_processors
        # Based on document_classifier.json, the param_name is 'document_url'
        text = full_task_run.get("run_data", {}).get("submitted", {}).get("document_url", "")
        if not text:
            print(f"⚠️ Warning: Could not find text in 'run_data.submitted.document_url' for task run {full_task_run.get('id', 'N/A')}.")
        return text if text else "" # Ensure we return empty string, not None
    except Exception as e:
        print(f"⚠️ Error extracting text from run_data: {e}")
        return ""

# --- Helper: Checklist Formatting ---

def format_documents_as_checklist(main_legal: List, classified_docs: List,
                                  unlinked_docs: List, main_security: List,
                                  repo_name: str, issue_number: str) -> str:
    """Builds the rich Markdown checklist with links to saved files."""

    online_items = []
    github_base_url = f"https://github.com/{repo_name}/blob/main/" # Assumes default branch is 'main'

    # --- Process Main Legal URL ---
    for url in main_legal:
        # Assume main T&Cs are always legal, generate filename, create link
        safe_filename = create_safe_filename("Main T&Cs", issue_number)
        file_path_relative = f"_vendor_analysis_source/{safe_filename}"
        # URL encode the filename part for safety in the URL
        github_file_url = github_base_url + url_quote(file_path_relative)
        online_items.append(f"- [x] **Legal**: [`Main T&Cs`]({github_file_url}) (`{url}`)")

    # --- Process Main Security URL ---
    for url in main_security:
        # Assume main Security doc is always security, generate filename, create link
        safe_filename = create_safe_filename("Main Security Page", issue_number)
        file_path_relative = f"_vendor_analysis_source/{safe_filename}"
        github_file_url = github_base_url + url_quote(file_path_relative)
        online_items.append(f"- [x] **Security**: [`Main Security Page`]({github_file_url}) (`{url}`)")

    # --- Process Classified Linked Documents ---
    # REFACTORED to use relevance_categories for TAGS and relevance_status for CHECKBOX
    for doc in classified_docs:
        name = doc.get("document_name", "Unknown Document")
        original_url = doc.get("document_url", "")
        # This now comes from the classifier_task
        relevance_categories = doc.get("relevance_categories", []) # e.g., [{"category": "legal"}]
        # This comes from the discovery_task
        relevance_status = doc.get("relevance_status", "irrelevant")


        if not original_url: continue # Skip if no URL

        safe_filename = create_safe_filename(name, issue_number)
        file_path_relative = f"_vendor_analysis_source/{safe_filename}"
        github_file_url = github_base_url + url_quote(file_path_relative)

        # Correctly extract categories from the list of dicts
        categories = [item.get("category", "none") for item in relevance_categories if isinstance(item, dict)]
        # Handle case where relevance might be returned incorrectly as simple list
        if not categories and isinstance(relevance_categories, list):
             categories = [item for item in relevance_categories if isinstance(item, str)]

        # Filter out "none" unless it's the only category
        filtered_categories = [cat for cat in categories if cat != "none"]
        if not filtered_categories and "none" in categories:
            final_categories = ["none"]
        elif not filtered_categories: # Handle empty list if API failed strangely
             final_categories = ["none"]
        else:
            final_categories = filtered_categories

        # --- REFACTORED LOGIC ---
        
        # 1. Determine the TAG based on classifier categories
        if "none" in final_categories:
            tag = "None"
        else:
            # Format as "Legal, Security" etc.
            tag = ", ".join([cat.title() for cat in final_categories])

        # 2. Determine the CHECKBOX based on discovery status
        if relevance_status == "relevant":
            is_checked = "x" # Pre-check relevant items
        else:
            is_checked = " " # Default to unchecked for "irrelevant" or "check_manually"

        # 3. Assemble the item
        item_md = f"- [{is_checked}] **{tag}**: [`{name}`]({github_file_url}) (`{original_url}`)"

        online_items.append(item_md)

    # --- Process Unlinked Documents ---
    offline_items = []
    for doc in unlinked_docs:
        # The schema is {"document": {...}}
        doc_data = doc.get("document", {})
        name = doc_data.get("document_name", "Unknown Reference")
        quote = doc_data.get("context_quote", "No context provided.")
        relevance = doc_data.get("relevance_status", "irrelevant").title()

        # Truncate long quotes for the issue body
        if len(quote) > 150:
            quote = quote[:150] + "..."
            
        # Add the relevance status as a tag
        offline_items.append(f"- [ ] **Awaiting Document ({relevance})**: `{name}`\n  > *Mentioned in: \"{quote}\"*")

    # --- Assemble Final Sections ---
    online_section = "### Online Documents Found\n*(Links point to the fetched text saved in the repo)*\n\n" + "\n".join(online_items)
    offline_section = ""
    if offline_items:
        offline_section = "\n### Offline / Unlinked References\n*(Please upload these manually)*\n\n" + "\n".join(offline_items)

    return online_section + offline_section

# --- Main Execution ---

def main():
    load_dotenv()

    # --- 1. Load Config & Environment Variables ---
    gh_token = os.environ["GITHUB_TOKEN"]
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    repo_name = os.environ["REPO_NAME"] # e.g., "your-org/your-repo"
    rb_org_id = os.environ["RB_ORG_ID"]
    rb_project_id = os.environ["RB_PROJECT_ID"]
    rb_client_id = os.environ["RB_CLIENT_ID"]
    rb_client_secret = os.environ["RB_CLIENT_SECRET"]
    rb_api_url = os.environ["RB_API_URL"] # Should include /api/v1
    rb_token_url = f"{os.environ['RB_OAUTH2_URL']}{os.environ['RB_OAUTH2_TOKEN_PATH']}"

    manifest = load_task_manifest()
    # Use task filenames as keys in the manifest
    discovery_task_id = manifest.get("discovery_task.json")
    classifier_task_id = manifest.get("document_classifier.json")

    if not discovery_task_id or not classifier_task_id:
        sys.exit("❌ Could not find 'discovery_task.json' or 'document_classifier.json' in task_manifest.json")

    # --- 2. Initialize ---
    rb_token = get_rb_token()
    classified_docs_for_checklist = []
    
    # REFACTORED: Use a single list for all discovered documents
    all_discovered_documents = []

    # REFACTORED: Get BOTH Usage and Data Context and combine them
    usage_context_text = parse_text_from_issue_form(issue_body, "Vendor/Service Usage Context")
    if not usage_context_text:
        print("⚠️ Warning: Could not parse 'Vendor/Service Usage Context' from issue body. Using a generic value.")
        usage_context_text = "Usage context not provided."

    data_types_text = parse_text_from_issue_form(issue_body, "Data Types Involved")
    if not data_types_text:
        print("⚠️ Warning: Could not parse 'Data Types Involved' from issue body. Using a generic value.")
        data_types_text = "Data types not provided."

    # Combine both fields for the AI task
    usage_context = (
        f"**Usage Context:**\n{usage_context_text}\n\n"
        f"**Data Types Involved:**\n{data_types_text}"
    )

    search_context_legal = "Find legally binding documents (T&Cs, DPA, Privacy Policy, etc.)"
    search_context_security = "Find security evidence (Security Page, SOC2, Certifications, etc.)"


    # --- 3. Process Main Legal T&Cs ---
    legal_urls = parse_urls_from_issue_form(issue_body, "T&Cs")
    if not legal_urls:
        print("ℹ️ No T&Cs URL found. Skipping legal document discovery.")
    else:
        main_terms_url = legal_urls[0]

        # --- STAGE 1: DISCOVERY (LEGAL) ---
        print("\n--- STAGE 1: DISCOVERY (LEGAL) ---")
        
        # REFACTORED: Prepare context-aware task input
        legal_discovery_input = {
            "document_text": main_terms_url,       # This will be intercepted by url_fetcher
            "original_url": main_terms_url,
            "usage_context": usage_context,
            "search_context": search_context_legal
        }
        
        discovery_run = run_rb_task(rb_token, discovery_task_id,
                                    legal_discovery_input, "Discovery Task (Legal)")

        # REFACTORED: Add critical failure check
        if not discovery_run or discovery_run.get("is_error"):
            # Refactored to use new util function
            post_failure_and_exit(
                repo_name, issue_number, issue_body,
                f"Discovery Task (Legal) failed. API returned: {discovery_run.get('response', 'No response')}"
            )

        discovery_response = discovery_run.get("response", {})
        # --- DEBUGGING: PRINT THE RAW DISCOVERY RESPONSE ---
        print(f"\nDEBUG: Legal Discovery Task Response:\n{json.dumps(discovery_response, indent=2)}\n")
        
        # REFACTORED: Add to combined list from new schema
        discovered_docs = discovery_response.get("discovered_documents", [])
        all_discovered_documents.extend(discovered_docs)

        # --- STAGE 1.5: CLASSIFY & FETCH (Main T&Cs) ---
        print("\n--- STAGE 1.5: CLASSIFY, FETCH & SAVE (Main T&Cs) ---")
        print("Processing Main T&Cs...")
        
        # REFACTORED: Use new run_rb_task signature
        classifier_input_main_legal = {"document_url": main_terms_url}
        main_terms_run = run_rb_task(rb_token, rb_api_url, rb_org_id, rb_project_id,
                                     classifier_task_id, classifier_input_main_legal, "Classifier Task (Main T&Cs)")

        if main_terms_run:
            relevance_dicts = main_terms_run.get("response", {}).get("relevance_categories", [{"category": "none"}])
            # Assume main T&Cs are always legal
            if not any(d.get("category") == "legal" for d in relevance_dicts if isinstance(d, dict)):
                 relevance_dicts.append({"category": "legal"})
                 # Filter out 'none' if legal was added
                 relevance_dicts = [d for d in relevance_dicts if d.get("category") != "none"]

            text = extract_text_from_run_data(main_terms_run)
            safe_filename = create_safe_filename("Main T&Cs", issue_number)
            # Save if not classified as 'none' only
            if not (len(relevance_dicts) == 1 and relevance_dicts[0].get("category") == "none"):
                 save_and_commit_source_text(text, repo_name, issue_number, safe_filename)
        else:
             # Handle API failure for main T&Cs - perhaps skip saving?
             print(f"⚠️ Classifier task failed for Main T&Cs ({main_terms_url}). Skipping text save.")


    # --- 4. Process Main Security URL ---
    security_urls = parse_urls_from_issue_form(issue_body, "Security Documents URL")
    if not security_urls:
        print("ℹ️ No main Security URL found. Skipping.")
    else:
        main_sec_url = security_urls[0]
        print(f"\nProcessing Main Security URL: {main_sec_url}...")
        
        # --- STAGE 1.6: DISCOVERY (SECURITY) ---
        print("\n--- STAGE 1.6: DISCOVERY (SECURITY) ---")
        
        # REFACTORED: Prepare context-aware task input
        sec_discovery_input = {
            "document_text": main_sec_url,       # This will be intercepted by url_fetcher
            "original_url": main_sec_url,
            "usage_context": usage_context,
            "search_context": search_context_security
        }
        
        sec_discovery_run = run_rb_task(rb_token, discovery_task_id,
                                    sec_discovery_input, "Discovery Task (Security)")

        # REFACTORED: Add critical failure check
        if not sec_discovery_run or sec_discovery_run.get("is_error"):
            # Refactored to use new util function
            post_failure_and_exit(
                repo_name, issue_number, issue_body,
                f"Discovery Task (Security) failed. API returned: {sec_discovery_run.get('response', 'No response')}"
            )

        sec_discovery_response = sec_discovery_run.get("response", {})
        # --- DEBUGGING: PRINT THE RAW DISCOVERY RESPONSE ---
        print(f"\nDEBUG: Security Discovery Task Response:\n{json.dumps(sec_discovery_response, indent=2)}\n")

        # REFACTORED: Add to combined list from new schema
        sec_discovered_docs = sec_discovery_response.get("discovered_documents", [])
        all_discovered_documents.extend(sec_discovered_docs)


        # --- STAGE 1.7: CLASSIFY & FETCH (Main Security) ---
        print("\n--- STAGE 1.7: CLASSIFY, FETCH & SAVE (Main Security) ---")
        
        # REFACTORED: Use new run_rb_task signature
        classifier_input_main_sec = {"document_url": main_sec_url}
        sec_run = run_rb_task(rb_token, rb_api_url, rb_org_id, rb_project_id,
                              classifier_task_id, classifier_input_main_sec, "Classifier Task (Main Security)")

        sec_run = run_rb_task(rb_token, classifier_task_id,
                              classifier_input_main_sec, "Classifier Task (Main Security)")

        if sec_run and not sec_run.get("is_error"):
            relevance_dicts = sec_run.get("response", {}).get("relevance_categories", [{"category": "none"}])

            text = extract_text_from_run_data(sec_run)
            safe_filename = create_safe_filename("Main Security Page", issue_number)
            # Save if not classified as 'none' only
            if not (len(relevance_dicts) == 1 and relevance_dicts[0].get("category") == "none"):
                save_and_commit_source_text(text, repo_name, issue_number, safe_filename)
        else:
            # Handle API failure for main Security URL
            print(f"⚠️ Classifier task failed for Main Security URL ({main_sec_url}). Skipping text save.")


    # --- 5. REFACTORED: De-duplicate and Fetch ALL Discovered Documents ---
    print("\n--- STAGE 2: DE-DUPLICATE, FETCH & SAVE (ALL DISCOVERED DOCS) ---")
    
    unique_linked_docs = []
    unique_unlinked_docs = []

    # REFACTORED: Pre-seed the seen URLs with the main URLs
    # to prevent them from being added to the list a second time.
    seen_linked_urls = set()
    if legal_urls:
        seen_linked_urls.add(legal_urls[0])
    if security_urls:
        seen_linked_urls.add(security_urls[0])

    seen_unlinked_names = set()

    for item in all_discovered_documents:
        # Defensive coding: ensure item is a dict and has 'document'
        if not isinstance(item, dict) or "document" not in item:
            print(f"⚠️ Skipping malformed discovery item: {item}")
            continue
            
        doc = item.get("document", {})
        if not isinstance(doc, dict):
            print(f"⚠️ Skipping malformed document data: {doc}")
            continue

        link_type = doc.get("link_type")
        
        if link_type == "linked":
            doc_url = doc.get("absolute_url")
            if not doc_url:
                continue
            if doc_url not in seen_linked_urls:
                seen_linked_urls.add(doc_url)
                unique_linked_docs.append(item) # Append the whole original item
        
        elif link_type == "unlinked":
            doc_name = doc.get("document_name")
            if not doc_name:
                continue
            if doc_name.lower() not in seen_unlinked_names:
                seen_unlinked_names.add(doc_name.lower())
                unique_unlinked_docs.append(item) # Append the whole original item

    print(f"\nProcessing {len(unique_linked_docs)} unique linked documents from all discovery runs...")
    
    # This loop now fetches text based on the relevance_status from discovery
    for item in unique_linked_docs:
        doc = item.get("document", {})
        doc_url = doc.get("absolute_url")
        doc_name = doc.get("document_name", "Unknown Document")
        # This is the new field from the discovery_task
        relevance_status = doc.get("relevance_status", "irrelevant")

        # --- THIS BLOCK IS THE BUG. IT'S BEING REMOVED. ---
        # Add document to the checklist data regardless of relevance
        # We will use the relevance_status in the formatting function
        # classified_docs_for_checklist.append({
        #     "document_name": doc_name,
        #     "document_url": doc_url,
        #     "relevance_status": relevance_status, # Discovery status
        #     "relevance_categories": relevance_dicts # Classifier status
        # })
        # --- END BUGGY BLOCK ---

        # REFACTORED: Always run classifier to get categories and text
        print(f"Fetching/Classifying doc: {doc_name} ({doc_url})")
        
        classifier_input_doc = {"document_url": doc_url}
        classifier_run = run_rb_task(rb_token, classifier_task_id,
                                     classifier_input_doc, f"Classifier Task ({doc_name})")

        if classifier_run and not classifier_run.get("is_error"):
            text = extract_text_from_run_data(classifier_run)
            safe_filename = create_safe_filename(doc_name, issue_number)
            # Always save the text, since we fetched it.
            save_and_commit_source_text(text, repo_name, issue_number, safe_filename)
            # Get the categories from the response
            relevance_dicts = classifier_run.get("response", {}).get("relevance_categories", [{"category": "none"}])
        else:
             print(f"⚠️ Classifier (fetcher) task failed for {doc_name} ({doc_url}). Skipping text save.")
             text = ""
             relevance_dicts = [{"category": "none"}] # Default on failure

        # REFACTORED: Add all data to the checklist
        classified_docs_for_checklist.append({
            "document_name": doc_name,
            "document_url": doc_url,
            "relevance_status": relevance_status, # From discovery (for checkbox)
            "relevance_categories": relevance_dicts # From classifier (for tags)
        })

    
    print(f"Found {len(unique_unlinked_docs)} unique unlinked documents.")
    # --- END REFACTOR ---


    # --- 6. Format and Post Final Checklist to Issue ---
    print("\n--- STAGE 3: UPDATING GITHUB ISSUE ---")
    final_checklist_md = format_documents_as_checklist(
        legal_urls,
        classified_docs_for_checklist,
        unique_unlinked_docs, # Pass the de-duplicated list
        security_urls,
        repo_name,
        issue_number
    )

    # Use the marker for idempotency
    CHECKLIST_MARKER = "<!--CHECKLIST_MARKER-->"

    final_comment_body = (
        f"{CHECKLIST_MARKER}\n" # Add marker at the beginning
        "## Documents for Analysis\n\n"
        "🤖 AI has performed discovery, classification, and fetched text for relevant documents. The fetched text files have been committed to the `_vendor_analysis_source` directory.\n\n"
        "**ACTION REQUIRED:**\n"
        "1.  **Review the checklist below.** Uncheck any documents you deem irrelevant for the final analysis.\n"
        "2.  For **'Awaiting Document'** items, please upload the corresponding file(s) manually to the `_vendor_analysis_source` directory. Name them clearly (e.g., `issue-{issue_number}-Order_Form.pdf`).\n"
        "3.  Once all documents are reviewed and uploaded, add the `ready-for-analysis` label to trigger the analysis workflow.\n\n"
        f"{final_checklist_md}"
    ).strip()

    try:
        update_issue_body(repo_name, issue_number, issue_body, final_comment_body)
    except Exception as e:
        # If update_issue_body fails, it will raise an error. We catch it here.
        # post_failure_and_exit will try to update the issue *again* with a failure message.
        post_failure_and_exit(repo_name, issue_number, issue_body, f"Failed to post final checklist: {e}")
        
    print("\n✅ Discovery and initial text fetch process complete.")

if __name__ == "__main__":
    main()