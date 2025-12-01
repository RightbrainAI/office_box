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

# --- Import pypdf ---
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    print("⚠️ pypdf not installed. PDF attachments will not be processed.", file=sys.stderr)

# --- Import Utils ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from utils.github_api import update_issue_body, post_failure_and_exit, fetch_issue_comments, parse_form_field
    from utils.rightbrain_api import get_rb_token, run_rb_task, log, get_task_id_by_name, get_api_root, get_rb_config
except ImportError as e:
    print(f"❌ Error importing 'utils' modules: {e}", file=sys.stderr)
    sys.exit(1)

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def create_safe_filename(doc_name: str, supplier_name: str, issue_number: str, extension: str = ".txt") -> str:
    """Creates a standardized filename: {Supplier}-{IssueID}-{DocName}.txt"""
    safe_supplier = re.sub(r'[<>:"/\\|?*\s]+', '_', supplier_name).strip('._ ') or "Vendor"
    safe_doc = re.sub(r'[<>:"/\\|?*\s]+', '_', doc_name).strip('._ ') or "doc"
    
    # Truncate to avoid filesystem limits
    safe_supplier = safe_supplier[:30]
    safe_doc = safe_doc[:50]
    
    if not safe_doc.endswith(extension): safe_doc += extension
    return f"{safe_supplier}-issue-{issue_number}-{safe_doc}"

def parse_multiline_urls(issue_body: str, label: str) -> List[str]:
    pattern = re.compile(f"### {re.escape(label)}\s*(.*?)(?=\\n###|\\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(issue_body)
    if not match: return []
    
    raw_block = match.group(1)
    urls = re.findall(r'(https?://[^\s,]+)', raw_block)
    
    clean_urls = []
    for u in urls:
        u = u.strip(').,')
        if "github.com" in u and "/files/" in u: continue
        clean_urls.append(u)
    return list(set(clean_urls))

def extract_text_from_pdf_bytes(file_content: bytes) -> str:
    if not PdfReader: return "[Error: pypdf not installed]"
    try:
        if not file_content: return "[Error: Empty file content]"
        reader = PdfReader(io.BytesIO(file_content))
        text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted: text.append(extracted)
        return "\n".join(text)
    except Exception as e:
        print(f"❌ PDF Extraction Error: {e}", file=sys.stderr)
        return f"[Error extracting PDF: {e}]"

def scan_comments_for_inputs(repo_name: str, issue_number: str, gh_token: str) -> List[Dict[str, Any]]:
    comments = fetch_issue_comments(repo_name, issue_number)
    found_inputs = []
    headers = {"Authorization": f"token {gh_token}"}
    print(f"🔎 Scanning {len(comments)} comments...")

    url_pattern = re.compile(r'(https://github\.com/.*?/files/\d+/[^\s)]+)')
    paste_pattern = re.compile(r'### Manual Document:\s*(.*?)\n(.*?)(?=\n###|\Z)', re.DOTALL | re.IGNORECASE)

    for comment in comments:
        body = comment.get("body", "")
        # Attachments
        for url in url_pattern.findall(body):
            url = url.rstrip(').')
            from urllib.parse import unquote
            filename = unquote(url.split('/')[-1])
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.pdf', '.txt', '.md']: continue
            
            print(f"  📎 Found attachment: {filename}")
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                content = extract_text_from_pdf_bytes(resp.content) if ext == '.pdf' else resp.content.decode('utf-8')
                found_inputs.append({"type": "attachment", "name": filename, "url": url, "text": content})
            except Exception as e: print(f"  ❌ Download Error: {e}")

        # Manual Pastes
        for doc_name, doc_content in paste_pattern.findall(body):
            print(f"  📋 Found manual paste: {doc_name.strip()}")
            found_inputs.append({"type": "paste", "name": doc_name.strip(), "url": "N/A", "text": doc_content.strip()})

    return found_inputs

def save_and_commit_source_text(text: str, repo_name: str, issue_number: str, filename: str):
    source_dir = Path("_vendor_analysis_source")
    source_dir.mkdir(exist_ok=True)
    file_path = source_dir / filename

    if not text or not text.strip(): return

    try:
        with open(file_path, "w", encoding="utf-8") as f: f.write(text)
    except IOError as e:
        log("error", f"Failed to write {file_path}", details=str(e))
        return

    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], capture_output=True)
        subprocess.run(["git", "add", str(file_path)], check=True, capture_output=True)
        
        status = subprocess.run(["git", "status", "--porcelain", str(file_path)], capture_output=True, text=True)
        if file_path.name in status.stdout:
            clean_name = filename.replace(f"issue-{issue_number}-", "")
            msg = f"docs(vendor): Add source '{clean_name}' (#{issue_number})"
            subprocess.run(["git", "commit", "-m", msg], capture_output=True)
            subprocess.run(["git", "pull", "--rebase"], capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print(f"  🚀 Committed: {filename}")
        else: print(f"  ℹ️  Up-to-date: {filename}")
    except Exception as e: log("warning", f"Git failed for '{filename}'", details=str(e))

def extract_text_from_run_data(full_task_run: Dict[str, Any]) -> str:
    try: return full_task_run.get("run_data", {}).get("submitted", {}).get("document_url", "") or ""
    except Exception: return ""

def format_documents_as_checklist(all_docs: List[Dict[str, Any]], repo_name: str, issue_number: str, supplier_name: str) -> str:
    """Builds Markdown checklist."""
    online, manual, existing = [], [], []
    base_url = f"https://github.com/{repo_name}/blob/main/"

    # Sort docs by name for consistent list order
    all_docs.sort(key=lambda x: x.get("name", "").lower())

    for doc in all_docs:
        name = doc.get("name", "Unknown")
        original_url = doc.get("url", "")
        # Use filename if explicitly provided (for reconciliation), else generate
        safe_filename = doc.get("filename") 
        if not safe_filename:
            safe_filename = create_safe_filename(name, supplier_name, issue_number)
            
        gh_url = base_url + url_quote(f"_vendor_analysis_source/{safe_filename}")
        
        cats = doc.get("categories", [])
        tag = ", ".join([c.title() for c in cats]) if (cats and "none" not in cats) else "Unclassified"

        # Checkbox Logic
        checked = "x"
        if doc.get("source_type") == "fetched":
            if "none" in cats or "fetch_failed" in cats:
                checked = " "
        if doc.get("source_type") in ["attachment", "paste", "existing"]:
            checked = "x"

        # Formatting based on source
        if doc.get("source_type") == "fetched":
            note = f"(Source: `{original_url}`)"
            if "fetch_failed" in cats: note = "⚠️ **FETCH FAILED** (Attach manually)"
            online.append(f"- [{checked}] **{tag}**: [`{name}`]({gh_url}) {note}")
        elif doc.get("source_type") == "existing":
            # Just display the name for recovered files
            existing.append(f"- [{checked}] **{tag}**: [`{name}`]({gh_url}) (Previously Discovered)")
        else:
            type_note = "Attachment" if doc.get("source_type") == "attachment" else "Paste"
            manual.append(f"- [{checked}] **{tag}** ({type_note}): [`{name}`]({gh_url})")

    output = ""
    if online: output += "### 🌐 Scraped Documents\n" + "\n".join(online) + "\n\n"
    if existing: output += "### 🗄️ Existing / Previously Discovered\n" + "\n".join(existing) + "\n\n"
    if manual: output += "### 📎 Manual Uploads\n" + "\n".join(manual) + "\n\n"
    return output

# ==========================================
# 2. MAIN EXECUTION
# ==========================================

def main():
    env_path = project_root / ".env"
    if env_path.exists(): load_dotenv(env_path)

    gh_token = os.environ["GITHUB_TOKEN"]
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = os.environ["ISSUE_NUMBER"]
    repo_name = os.environ["REPO_NAME"]
    
    get_rb_config()
    rb_api_root = get_api_root()
    
    orig_root = os.environ.get("API_ROOT")
    os.environ["API_ROOT"] = rb_api_root
    
    discovery_task_id = get_task_id_by_name("Document Discovery Task")
    classifier_task_id = get_task_id_by_name("Document Classifier Task")
    
    if orig_root: os.environ["API_ROOT"] = orig_root
    elif "API_ROOT" in os.environ: del os.environ["API_ROOT"]

    if not discovery_task_id or not classifier_task_id:
        sys.exit("❌ Missing Task IDs in manifest.")

    rb_token = get_rb_token()
    
    # STAGE 0: CONTEXT
    supplier_name = parse_form_field(issue_body, "Supplier Name")
    if not supplier_name: supplier_name = "UnknownVendor"
    print(f"🚀 Starting Discovery for: {supplier_name} (Issue #{issue_number})")

    # STAGE 1: HARVEST
    legal_seeds = parse_multiline_urls(issue_body, "Legal URLs") or parse_multiline_urls(issue_body, "T&Cs")
    security_seeds = parse_multiline_urls(issue_body, "Security URLs")
    manual_inputs = scan_comments_for_inputs(repo_name, issue_number, gh_token)
    urls_to_process = [] 

    # STAGE 2: SPIDER
    discovery_prompts = [
        {"seeds": legal_seeds, "prompt": "Find legally binding documents (Terms, DPA, Privacy Policy)."},
        {"seeds": security_seeds, "prompt": "Find security evidence (SOC2, ISO27001, Whitepapers)."}
    ]
    print(f"\n--- STAGE 2: Running Discovery (Spidering) ---")
    
    for u in legal_seeds: urls_to_process.append({"url": u, "origin": "seed"})
    for u in security_seeds: urls_to_process.append({"url": u, "origin": "seed"})

    for group in discovery_prompts:
        for seed_url in group["seeds"]:
            # IDEMPOTENCY CHECK
            doc_name = seed_url.split('/')[-1] or "webpage"
            safe_filename = create_safe_filename(doc_name, supplier_name, issue_number)
            local_path = Path("_vendor_analysis_source") / safe_filename

            if local_path.exists():
                print(f"⏩ Skipping Spider for {seed_url} - Seed file already exists.")
                continue

            print(f"🕷️ Spidering: {seed_url}")
            discovery_input = {
                "document_text": seed_url,
                "original_url": seed_url,
                "usage_context": f"Vendor Review for {supplier_name}",
                "search_context": group["prompt"]
            }
            run = run_rb_task(rb_token, discovery_task_id, discovery_input, f"Discover: {seed_url}")
            if run and not run.get("is_error"):
                found_docs = run.get("response", {}).get("discovered_documents", [])
                print(f"   -> Found {len(found_docs)} links.")
                for doc_item in found_docs:
                    doc_data = doc_item.get("document", {})
                    if doc_data.get("absolute_url"):
                        urls_to_process.append({"url": doc_data["absolute_url"], "origin": "spider"})
            else:
                log("warning", f"Discovery failed for {seed_url}. Proceeding with seed only.")

    # STAGE 3: FETCH & CLASSIFY
    unique_urls = {item['url']: item for item in urls_to_process}.values()
    all_final_docs = []
    
    # Track which files we have "touched" in this run to identify orphans later
    processed_filenames = set()

    print(f"\n--- STAGE 3: Fetching {len(unique_urls)} Unique URLs ---")

    for item in unique_urls:
        url = item['url']
        doc_name = url.split('/')[-1] or "webpage"
        safe_filename = create_safe_filename(doc_name, supplier_name, issue_number)
        
        # Track this file
        processed_filenames.add(safe_filename)

        local_path = Path("_vendor_analysis_source") / safe_filename
        
        if local_path.exists():
            print(f"⏩ Skipping {url} - Exists: {safe_filename}")
            all_final_docs.append({"name": doc_name, "url": url, "source_type": "fetched", "relevance": "relevant", "categories": ["existing_file"], "filename": safe_filename})
            continue

        print(f"Fetching: {url}")
        run = run_rb_task(rb_token, classifier_task_id, {"document_url": url}, f"Fetch: {url}")
        
        if run and not run.get("is_error"):
            text = extract_text_from_run_data(run)
            relevance_data = run.get("response", {}).get("relevance_categories", [{"category": "none"}])
            categories = [d.get("category", "none") for d in relevance_data if isinstance(d, dict)]
            
            if not text:
                all_final_docs.append({"name": "Failed Fetch: " + doc_name, "url": url, "source_type": "fetched", "relevance": "irrelevant", "categories": ["fetch_failed"], "filename": safe_filename})
                continue

            save_and_commit_source_text(text, repo_name, issue_number, safe_filename)
            all_final_docs.append({"name": doc_name, "url": url, "source_type": "fetched", "relevance": "relevant", "categories": categories, "filename": safe_filename})
        else:
            log("warning", f"Fetch failed for {url}")

    # STAGE 4: MANUAL INPUTS
    print(f"\n--- STAGE 4: Processing Manual Inputs ---")
    for inp in manual_inputs:
        safe_filename = create_safe_filename(inp['name'], supplier_name, issue_number)
        processed_filenames.add(safe_filename)
        
        save_and_commit_source_text(inp['text'], repo_name, issue_number, safe_filename)
        all_final_docs.append({"name": inp['name'], "url": inp['url'], "source_type": inp['type'], "relevance": "relevant", "categories": ["uploaded"], "filename": safe_filename})

    # --- NEW STAGE 4.5: RECONCILE WITH DISK ---
    print(f"\n--- STAGE 4.5: Reconciling with Local Files ---")
    source_dir = Path("_vendor_analysis_source")
    if source_dir.exists():
        # Find all files belonging to this issue
        for file_path in source_dir.glob(f"*issue-{issue_number}-*"):
            if file_path.name not in processed_filenames:
                print(f"  🗄️  Found orphaned file (previously discovered): {file_path.name}")
                # We add it back to the list so it appears in the checklist
                all_final_docs.append({
                    "name": file_path.name, # Use filename as display name
                    "url": "Local File",
                    "source_type": "existing",
                    "relevance": "relevant",
                    "categories": ["existing_file"],
                    "filename": file_path.name
                })

    # STAGE 5: UPDATE ISSUE
    print("\n--- STAGE 5: Updating Checklist ---")
    checklist_md = format_documents_as_checklist(all_final_docs, repo_name, issue_number, supplier_name)
    
    CHECKLIST_MARKER = ""
    new_section = (
        f"{CHECKLIST_MARKER}\n"
        "## Documents for Analysis\n\n"
        "🤖 **Status:**\n"
        f"- Spidered {len(legal_seeds) + len(security_seeds)} seed URLs.\n"
        f"- Processed {len(all_final_docs)} total documents.\n\n"
        "**Missing something?**\n"
        "1. **Drag & Drop** a PDF into a comment below.\n"
        "2. **Or Paste Text** in a comment with the header: `### Manual Document: [Doc Name]`\n"
        "3. Add the label `refresh-documents` to retry.\n\n"
        f"{checklist_md}"
    ).strip()

    try:
        update_issue_body(repo_name, issue_number, issue_body, new_section)
    except Exception as e:
        post_failure_and_exit(repo_name, issue_number, issue_body, f"Failed to post checklist: {e}")

    log("success", "Discovery complete.")

if __name__ == "__main__":
    main()