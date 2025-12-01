import os
import sys
import json
import re
import requests
import subprocess
import io
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote as url_quote

# --- Import pypdf for Attachment Handling ---
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    print("⚠️ pypdf not installed. PDF attachments will not be processed.", file=sys.stderr)

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
    safe_name = safe_name[:100] # Truncate
    
    # Ensure extension matches if provided in name, otherwise append
    if not safe_name.endswith(extension):
        safe_name += extension
        
    return f"issue-{issue_number}-{safe_name}"

# --- Helper: Input Parsing ---

def parse_multiline_urls(issue_body: str, label: str) -> List[str]:
    """
    Parses multiple URLs from a GitHub issue form block.
    Splits by newlines or commas.
    """
    pattern = re.compile(f"### {re.escape(label)}\s*(.*?)(?=\\n###|\\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(issue_body)
    if not match:
        return []
    
    raw_block = match.group(1)
    urls = re.findall(r'(https?://[^\s,]+)', raw_block)
    
    clean_urls = []
    for u in urls:
        u = u.strip(').,')
        if "github.com" in u and "/files/" in u:
            continue
        clean_urls.append(u)
        
    return list(set(clean_urls))

# --- Helper: Attachment & Paste Processing ---

def extract_text_from_pdf_bytes(file_content: bytes) -> str:
    """Extracts text from PDF binary data."""
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
    1. Attachments (PDF/TXT) - Scans for GitHub file URLs (supports user-attachments).
    2. Manual Pastes (Headers like '### Manual Document: Name').
    """
    comments = fetch_issue_comments(repo_name, issue_number)
    found_inputs = []
    headers = {"Authorization": f"token {gh_token}"}

    print(f"🔎 Scanning {len(comments)} comments for attachments or manual pastes...")

    # FIX: Loosened regex to match 'user-attachments' or 'org/repo'
    # It matches https://github.com/ + (anything non-greedy) + /files/ + (digits) + / + (filename)
    url_pattern = re.compile(r'(https://github\.com/.*?/files/\d+/[^\s)]+)')
    
    paste_pattern = re.compile(r'### Manual Document:\s*(.*?)\n(.*?)(?=\n###|\Z)', re.DOTALL | re.IGNORECASE)

    for comment in comments:
        body = comment.get("body", "")
        
        # 1. Process Attachments
        for url in url_pattern.findall(body):
            url = url.rstrip(').') 
            
            from urllib.parse import unquote
            filename = unquote(url.split('/')[-1])
            
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.txt', '.md']:
                continue
            
            print(f"  📎 Found attachment URL: {filename}...")
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
                    "url": url, 
                    "text": content_text
                })
            except Exception as e:
                print(f"  ❌ Failed to download/read {filename}: {e}")

        # 2. Process Manual Pastes
        for doc_name, doc_content in paste_pattern.findall(body):
            print(f"  📋 Found manual text paste: {doc_name.strip()}")
            found_inputs.append({
                "type": "paste",
                "name": doc_name.strip(),
                "url": "N/A (Manual Paste)",
                "text": doc_content.strip()
            })

    return found_inputs

# --- Helper: Git Operations (RESTORED) ---

def save_and_commit_source_text(text: str, repo_name: str, issue_number: str, filename: str):
    """Saves text to file and commits it."""
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
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], capture_output=True)

        subprocess.run(["git", "add", str(file_path)], check=True, capture_output=True)
        
        status = subprocess.run(["git", "status", "--porcelain", str(file_path)], capture_output=True, text=True)

        if file_path.name in status.stdout:
            doc_name_part = filename.replace(f"issue-{issue_number}-", "").replace(".txt", "").replace("_", " ")
            commit_msg = f"docs(vendor): Add source text for '{doc_name_part}' (issue #{issue_number})"
            
            subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
            subprocess.run(["git", "pull", "--rebase"], capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print(f"  🚀 Committed: {filename}")
        else:
            print(f"  ℹ️  File up-to-date: {filename}")

    except Exception as e:
        log("warning", f"Git operation failed for '{filename}'", details=str(e))

def extract_text_from_run_data(full_task_run: Dict[str, Any]) -> str:
    try:
        text = full_task_run.get("run_data", {}).get("submitted", {}).get("document_url", "")
        return text if text else ""
    except Exception:
        return ""

# --- Helper: Checklist Output ---

def format_documents_as_checklist(all_docs: List[Dict[str, Any]], repo_name: str, issue_number: str) -> str:
    """Builds the markdown checklist."""
    online_items = []
    manual_items = []
    github_base_url = f"https://github.com/{repo_name}/blob/main/"

    for doc in all_docs:
        name = doc.get("name", "Unknown")
        original_url = doc.get("url", "")
        source_type = doc.get("source_type", "fetched") 
        safe_filename = create_safe_filename(name, issue_number)
        file_path_relative = f"_vendor_analysis_source/{safe_filename}"
        github_file_url = github_base_url + url_quote(file_path_relative)
        
        is_checked = " "
        if doc.get("relevance") == "relevant" or source_type in ["attachment", "paste"]:
            is_checked = "x"

        categories = doc.get("categories", [])
        if not categories or "none" in categories:
             if "legal" in name.lower() or "terms" in name.lower(): tag = "Legal"
             elif "security" in name.lower() or "soc" in name.lower(): tag = "Security"
             else: tag = "Unclassified"
        else:
            tag = ", ".join([c.title() for c in categories])

        if source_type == "fetched":
            note = f"(Scraped from: `{original_url}`)"
            if "fetch_failed" in categories:
                note = f"⚠️ **FETCH FAILED** (Please attach manually)"
            item = f"- [{is_checked}] **{tag}**: [`{name}`]({github_file_url}) {note}"
            online_items.append(item)
        else:
            src_note = "Attachment" if source_type == "attachment" else "Manual Paste"
            item = f"- [{is_checked}] **{tag}** ({src_note}): [`{name}`]({github_file_url})"
            manual_items.append(item)

    output = ""
    if online_items: output += "### 🌐 Scraped Documents\n" + "\n".join(online_items) + "\n\n"
    if manual_items: output += "### 📎 Manual Uploads\n" + "\n".join(manual_items) + "\n\n"
    return output

# --- Main Execution ---

def main():
    env_path = project_root / ".env"
    if env_path.exists(): load_dotenv(env_path)

    gh_token = os.environ["GITHUB_TOKEN"]
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    repo_name = os.environ["REPO_NAME"]
    
    get_rb_config() 
    rb_api_root = get_api_root()
    
    original_api_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root
    classifier_task_id = get_task_id_by_name("Document Classifier Task")
    if original_api_root: os.environ["API_ROOT"] = original_api_root
    elif "API_ROOT" in os.environ: del os.environ["API_ROOT"]

    if not classifier_task_id:
        sys.exit("❌ Could not find 'Document Classifier Task' ID.")

    rb_token = get_rb_token()
    
    # --- 1. HARVEST INPUTS ---
    legal_urls = parse_multiline_urls(issue_body, "Legal URLs")
    security_urls = parse_multiline_urls(issue_body, "Security URLs")
    if not legal_urls: legal_urls = parse_multiline_urls(issue_body, "T&Cs")
    
    manual_inputs = scan_comments_for_inputs(repo_name, issue_number, gh_token)

    all_final_docs = []

    # --- 2. PROCESS URLS (With Idempotency) ---
    urls_to_process = []
    for u in legal_urls: urls_to_process.append({"url": u})
    for u in security_urls: urls_to_process.append({"url": u})
    
    unique_urls = {d['url']: d for d in urls_to_process}.values()

    print(f"\n--- STAGE 1: Processing {len(unique_urls)} URLs ---")
    
    for item in unique_urls:
        url = item['url']
        doc_name = url.split('/')[-1]
        if not doc_name: doc_name = "webpage"
        safe_filename = create_safe_filename(doc_name, issue_number)
        
        local_path = Path("_vendor_analysis_source") / safe_filename
        if local_path.exists():
            print(f"⏩ Skipping {url} - File already exists: {safe_filename}")
            all_final_docs.append({
                "name": doc_name,
                "url": url,
                "source_type": "fetched",
                "relevance": "relevant", 
                "categories": ["existing_file"]
            })
            continue

        print(f"Fetching: {url}")
        run = run_rb_task(rb_token, classifier_task_id, {"document_url": url}, f"Fetch: {url}")
        
        if run and not run.get("is_error"):
            text = extract_text_from_run_data(run)
            relevance = run.get("response", {}).get("relevance_categories", [{"category": "none"}])
            categories = [d.get("category", "none") for d in relevance if isinstance(d, dict)]
            
            if not text:
                log("warning", f"No text returned for {url}.")
                all_final_docs.append({
                    "name": "Failed Fetch: " + doc_name,
                    "url": url,
                    "source_type": "fetched",
                    "relevance": "irrelevant",
                    "categories": ["fetch_failed"]
                })
                continue

            save_and_commit_source_text(text, repo_name, issue_number, safe_filename)
            all_final_docs.append({
                "name": doc_name,
                "url": url,
                "source_type": "fetched",
                "relevance": "relevant",
                "categories": categories
            })
        else:
             log("warning", f"Fetch task failed for {url}")

    # --- 3. PROCESS MANUAL INPUTS ---
    print(f"\n--- STAGE 2: Processing {len(manual_inputs)} Manual Inputs ---")
    for inp in manual_inputs:
        safe_filename = create_safe_filename(inp['name'], issue_number)
        save_and_commit_source_text(inp['text'], repo_name, issue_number, safe_filename)
        
        all_final_docs.append({
            "name": inp['name'],
            "url": inp['url'],
            "source_type": inp['type'],
            "relevance": "relevant",
            "categories": ["uploaded"]
        })

    # --- 4. UPDATE ISSUE ---
    print("\n--- STAGE 3: Updating Checklist ---")
    checklist_md = format_documents_as_checklist(all_final_docs, repo_name, issue_number)
    
    CHECKLIST_MARKER = ""
    comment_body = (
        f"{CHECKLIST_MARKER}\n"
        "## Documents for Analysis\n\n"
        "🤖 **Status:**\n"
        f"- Processed {len(all_final_docs)} documents.\n\n"
        "**Missing something?**\n"
        "1. **Drag & Drop** a PDF into a comment below.\n"
        "2. Add the label `refresh-documents` to retry.\n\n"
        f"{checklist_md}"
    ).strip()

    try:
        update_issue_body(repo_name, issue_number, issue_body, comment_body)
    except Exception as e:
        post_failure_and_exit(repo_name, issue_number, issue_body, f"Failed to post checklist: {e}")

    log("success", "Discovery complete.")

if __name__ == "__main__":
    main()