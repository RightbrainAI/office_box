import os
import sys
import json
import re
import requests
import subprocess
import io
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any, Tuple
from urllib.parse import quote as url_quote
# New dependency for PDF handling
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # Handle gracefully if not installed

# --- Fix Import Path for 'utils' ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.github_api import update_issue_body, post_failure_and_exit, fetch_issue_comments
    from utils.rightbrain_api import get_rb_token, run_rb_task, log, get_task_id_by_name, get_api_root, get_rb_config
except ImportError as e:
    print(f"❌ Error importing 'utils' modules: {e}", file=sys.stderr)
    sys.exit(1)


# --- Helper: Filename Sanitization ---

def create_safe_filename(name: str, issue_number: str, extension: str = ".txt") -> str:
    """Creates a safe filename for saving document text."""
    safe_name = re.sub(r'[<>:"/\\|?*\s]+', '_', name)
    safe_name = safe_name.strip('._ ')
    if not safe_name:
        safe_name = "unnamed_document"
    safe_name = safe_name[:100]
    return f"issue-{issue_number}-{safe_name}{extension}"

# --- Helper: Parsing ---

def parse_multiline_urls(issue_body: str, label: str) -> List[str]:
    """
    Parses multiple URLs from a GitHub issue form body based on its markdown label.
    Splits by newlines or commas.
    """
    pattern = re.compile(f"### {re.escape(label)}\s*(.*?)(?=\\n###|\\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(issue_body)
    if not match:
        return []
    
    raw_block = match.group(1)
    # Find all http/https links
    urls = re.findall(r'(https?://[^\s,]+)', raw_block)
    # Clean up (remove trailing Markdown parenthesis if captured)
    clean_urls = [u.strip(').,') for u in urls if "github.com" not in u or "/files/" not in u]
    return list(set(clean_urls))

# --- Helper: Attachment & Paste Handling ---

def extract_text_from_pdf_bytes(file_content: bytes) -> str:
    """Extracts text from PDF binary data using pypdf."""
    if not PdfReader:
        return "[Error: pypdf not installed, cannot read PDF]"
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
        return "\n".join(text)
    except Exception as e:
        return f"[Error extracting PDF: {e}]"

def scan_comments_for_inputs(repo_name: str, issue_number: str, gh_token: str) -> List[Dict[str, Any]]:
    """
    Scans comments for:
    1. Attachments (PDF/TXT) -> Downloads and extracts text.
    2. Manual Pastes (Headers like '### Manual Document: Name') -> Extracts text.
    """
    comments = fetch_issue_comments(repo_name, issue_number)
    found_inputs = []
    headers = {"Authorization": f"token {gh_token}"}

    print(f"🔎 Scanning {len(comments)} comments for attachments or manual pastes...")

    # Regex for GitHub Attachments: [Name](url)
    attachment_pattern = re.compile(r'\[(.*?)\]\((https://github\.com/[^/]+/[^/]+/files/\d+/.*?)\)')
    
    # Regex for Manual Pastes: ### Manual Document: Name \n Content
    paste_pattern = re.compile(r'### Manual Document:\s*(.*?)\n(.*?)(?=\n###|\Z)', re.DOTALL | re.IGNORECASE)

    for comment in comments:
        body = comment.get("body", "")
        
        # 1. Process Attachments
        for filename, url in attachment_pattern.findall(body):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.txt', '.md']:
                continue
            
            print(f"  📎 Downloading attachment: {filename}...")
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                
                content_text = ""
                if ext == '.pdf':
                    content_text = extract_text_from_pdf_bytes(resp.content)
                else:
                    content_text = resp.content.decode('utf-8')
                
                found_inputs.append({
                    "type": "attachment",
                    "name": filename,
                    "url": url, # Link to the github asset
                    "text": content_text,
                    "source": "Comment Attachment"
                })
            except Exception as e:
                print(f"  ❌ Failed to download/read {filename}: {e}")

        # 2. Process Manual Pastes
        # Users can paste text directly into a comment with the header "### Manual Document: [Name]"
        for doc_name, doc_content in paste_pattern.findall(body):
            print(f"  📋 Found manual text paste: {doc_name.strip()}")
            found_inputs.append({
                "type": "paste",
                "name": doc_name.strip(),
                "url": "N/A (Manual Paste)",
                "text": doc_content.strip(),
                "source": "Manual Comment Paste"
            })

    return found_inputs

# --- Helper: Text Compilation & Git ---

def save_and_commit_source_text(text: str, repo_name: str, issue_number: str, filename: str):
    """Saves a single document's text to a file and commits it."""
    source_dir = Path("_vendor_analysis_source")
    source_dir.mkdir(exist_ok=True)
    file_path = source_dir / filename

    if not text or not text.strip():
        return

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    except IOError as e:
        log("error", f"Failed to write file {file_path}", details=str(e))
        return

    try:
        # Configure git (idempotent)
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], capture_output=True)

        subprocess.run(["git", "add", str(file_path)], check=True, capture_output=True)
        
        # Check status
        status_result = subprocess.run(["git", "status", "--porcelain", str(file_path)], capture_output=True, text=True)

        if file_path.name in status_result.stdout:
            doc_name_part = filename.replace(f"issue-{issue_number}-", "").replace(".txt", "").replace("_", " ")
            commit_message = f"docs(vendor): Add source text for '{doc_name_part}' (issue #{issue_number})"
            
            subprocess.run(["git", "commit", "-m", commit_message], capture_output=True)
            subprocess.run(["git", "pull", "--rebase"], capture_output=True) # Rebase to avoid conflicts
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print(f"  🚀 Committed and pushed: {filename}")
        else:
            print(f"  ℹ️  No changes for {filename}")

    except Exception as e:
        log("warning", f"Git operation failed for '{filename}'", details=str(e))

def extract_text_from_run_data(full_task_run: Dict[str, Any]) -> str:
    """Extracts fetched text from RB task run data."""
    try:
        text = full_task_run.get("run_data", {}).get("submitted", {}).get("document_url", "")
        return text if text else ""
    except Exception:
        return ""

# --- Helper: Checklist Formatting ---

def format_documents_as_checklist(all_docs: List[Dict[str, Any]], repo_name: str, issue_number: str) -> str:
    """Builds the rich Markdown checklist."""
    
    online_items = []
    manual_items = []
    github_base_url = f"https://github.com/{repo_name}/blob/main/"

    for doc in all_docs:
        name = doc.get("name", "Unknown Document")
        original_url = doc.get("url", "")
        source_type = doc.get("source_type", "fetched") # fetched, attachment, paste
        
        # Generate the link to the local committed file
        safe_filename = create_safe_filename(name, issue_number)
        file_path_relative = f"_vendor_analysis_source/{safe_filename}"
        github_file_url = github_base_url + url_quote(file_path_relative)
        
        # Determine Checkbox Status
        is_checked = " "
        if doc.get("relevance") == "relevant" or source_type in ["attachment", "paste"]:
            is_checked = "x"

        # Determine Tag
        categories = doc.get("categories", [])
        if not categories or "none" in categories:
             # Heuristic for manual files
             if "legal" in name.lower() or "terms" in name.lower(): tag = "Legal"
             elif "security" in name.lower() or "soc" in name.lower(): tag = "Security"
             else: tag = "Unclassified"
        else:
            tag = ", ".join([c.title() for c in categories])

        # Formatting
        if source_type == "fetched":
            item_md = f"- [{is_checked}] **{tag}**: [`{name}`]({github_file_url}) (Scraped from: `{original_url}`)"
            online_items.append(item_md)
        elif source_type == "attachment":
            item_md = f"- [{is_checked}] **{tag}** (Attachment): [`{name}`]({github_file_url}) (Original: [Download]({original_url}))"
            manual_items.append(item_md)
        elif source_type == "paste":
            item_md = f"- [{is_checked}] **{tag}** (Manual Paste): [`{name}`]({github_file_url})"
            manual_items.append(item_md)

    section_scraped = ""
    section_manual = ""

    if online_items:
        section_scraped = "### 🌐 Online Documents Found\n" + "\n".join(online_items) + "\n\n"
    if manual_items:
        section_manual = "### 📎 Manual Uploads & Pastes\n" + "\n".join(manual_items) + "\n\n"

    return section_scraped + section_manual

# --- Main Execution ---

def main():
    env_path = project_root / ".env"
    if env_path.exists(): load_dotenv(env_path)

    gh_token = os.environ["GITHUB_TOKEN"]
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    repo_name = os.environ["REPO_NAME"]
    
    get_rb_config() # Validate RB config
    rb_api_root = get_api_root()
    
    # Setup Task IDs
    original_api_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root
    classifier_task_id = get_task_id_by_name("Document Classifier Task")
    if original_api_root: os.environ["API_ROOT"] = original_api_root
    elif "API_ROOT" in os.environ: del os.environ["API_ROOT"]

    if not classifier_task_id:
        sys.exit("❌ Could not find 'Document Classifier Task' ID.")

    rb_token = get_rb_token()
    
    # --- 1. Harvest Inputs ---
    
    # A. URLs from Issue Body (Now supports lists)
    legal_urls = parse_multiline_urls(issue_body, "Legal URLs") # Changed label to plural in form if possible
    security_urls = parse_multiline_urls(issue_body, "Security URLs")
    # Fallback for singular label if user hasn't updated form template
    if not legal_urls: legal_urls = parse_multiline_urls(issue_body, "T&Cs")
    
    # B. Attachments & Pastes from Comments
    manual_inputs = scan_comments_for_inputs(repo_name, issue_number, gh_token)

    # --- 2. Process Inputs ---
    
    all_final_docs = []

    # Process URLs (Fetch via Rightbrain)
    urls_to_process = []
    for u in legal_urls: urls_to_process.append({"url": u, "context": "legal"})
    for u in security_urls: urls_to_process.append({"url": u, "context": "security"})
    
    # Deduplicate URLs
    unique_urls = {d['url']: d for d in urls_to_process}.values()

    print(f"\n--- STAGE 1: Processing {len(unique_urls)} URLs ---")
    for item in unique_urls:
        url = item['url']
        print(f"Fetching & Classifying: {url}")
        
        # We skip the "Discovery" task for direct URLs and go straight to Classifier/Fetcher
        # Note: In a production V2, you might still want Discovery to find sub-pages. 
        # For now, we assume direct links are direct documents.
        
        run = run_rb_task(rb_token, classifier_task_id, {"document_url": url}, f"Classifier: {url}")
        
        if run and not run.get("is_error"):
            text = extract_text_from_run_data(run)
            relevance_dicts = run.get("response", {}).get("relevance_categories", [{"category": "none"}])
            categories = [d.get("category", "none") for d in relevance_dicts if isinstance(d, dict)]
            
            if not text:
                log("warning", f"No text returned for {url}. It might be a SPA (Vanta/React).")
                # We still add it to the list, but unchecked, so user knows it failed
                all_final_docs.append({
                    "name": "Failed Fetch: " + url.split('/')[-1][:30],
                    "url": url,
                    "source_type": "fetched",
                    "relevance": "irrelevant",
                    "categories": ["fetch_failed"]
                })
                continue

            # Save Text
            doc_name = url.split('/')[-1]
            if not doc_name: doc_name = "webpage"
            safe_filename = create_safe_filename(doc_name, issue_number)
            save_and_commit_source_text(text, repo_name, issue_number, safe_filename)

            all_final_docs.append({
                "name": doc_name,
                "url": url,
                "source_type": "fetched",
                "relevance": "relevant", # If we fetched it successfully, assume relevant for now
                "categories": categories
            })
        else:
             log("warning", f"Classifier task failed for {url}")

    print(f"\n--- STAGE 2: Processing {len(manual_inputs)} Manual Inputs ---")
    for inp in manual_inputs:
        # Save Text immediately
        safe_filename = create_safe_filename(inp['name'], issue_number)
        save_and_commit_source_text(inp['text'], repo_name, issue_number, safe_filename)
        
        all_final_docs.append({
            "name": inp['name'],
            "url": inp['url'],
            "source_type": inp['type'], # attachment or paste
            "relevance": "relevant", # Manual uploads are always relevant
            "categories": ["uploaded"]
        })

    # --- 3. Update Issue ---
    print("\n--- STAGE 3: Updating Checklist ---")
    final_checklist_md = format_documents_as_checklist(all_final_docs, repo_name, issue_number)
    
    CHECKLIST_MARKER = ""
    final_comment_body = (
        f"{CHECKLIST_MARKER}\n"
        "## Documents for Analysis\n\n"
        "🤖 **Status:**\n"
        f"- Scraped {len(unique_urls)} URLs.\n"
        f"- Ingested {len(manual_inputs)} manual files/pastes from comments.\n\n"
        "**Usage Note:** If a document failed to scrape (e.g., Vanta), please:\n"
        "1. Copy the text or download the PDF.\n"
        "2. Add a **Comment** to this issue with the file attached OR paste the text starting with `### Manual Document: Name`.\n"
        "3. Re-add the `ready-for-analysis` label.\n\n"
        f"{final_checklist_md}"
    ).strip()

    try:
        update_issue_body(repo_name, issue_number, issue_body, final_comment_body)
    except Exception as e:
        post_failure_and_exit(repo_name, issue_number, issue_body, f"Failed to post checklist: {e}")

    log("success", "Discovery complete.")

if __name__ == "__main__":
    main()