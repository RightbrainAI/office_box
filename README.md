# AI-Powered Vendor Onboarding Tool

This project provides a complete, automated workflow for conducting vendor risk assessments using GitHub Issues and Rightbrain AI Tasks.

It listens for new vendor onboarding requests, automatically discovers and analyzes all associated legal and security documents, and produces a high-level risk report to accelerate your compliance workflow.

# 🏁 Quick Start: Zero-Code Setup Guide

*Target Audience*: Legal Ops, Security Managers, & Counsel.

No coding or terminal required. Follow these 5 steps to get your own private risk analyst.

### Step 1: Get your own copy

1. Look at the top-right corner of this page and click the "Fork" button.
2. Click "Create Fork".
3. You now have your own copy of this tool! You will do all the following steps on your version.

### Step 2: Get your Rightbrain API Keys

1. Log in to your Rightbrain account.
1. Go to Settings > API Clients.
1. Click "Create OAuth Client".
1. Keep this tab open. You will need the Client ID, Client Secret, Organization ID, and Project ID for the next step.

### Step 3: Connect GitHub to Rightbrain

1. In your GitHub repository, click the Settings tab (top menu).
1. On the left sidebar, scroll down to Secrets and variables and click Actions.
1. Click the green "New repository secret" button.
1. You need to add the following 6 secrets (copy/paste the values from your Rightbrain tab):

| Name | Value |
|------|-------|
|RB_ORG_ID| Your Organization ID|
|RB_PROJECT_ID|Your Project ID|
|RB_CLIENT_ID|Your Client ID|
|RB_CLIENT_SECRET|Your Client Secret|
|RB_OAUTH2_URL|https://oauth.rightbrain.ai/oauth2/auth|
|RB_API_URL|https://app.rightbrain.ai/api/v1|

_Note: You will also need a *GITHUB__TOKEN*, but GitHub creates this for you automatically! You don't need to add it._

### Step 4: The "Magic Button" (Install AI Tasks)

1. Click the Actions tab (top menu).
_Note: If you see a big green button saying "I understand my workflows...", click it to enable automation._
1. On the left sidebar, click "Setup Rightbrain Tasks".
1. On the right side, click the "Run workflow" dropdown, then click the green "Run workflow" button.
1. Wait about 30 seconds. When you see a green checkmark, the AI is installed!

### Step 5: Train Your AI (Configure Company Profile)

1. This is the most important step! You need to tell the AI who "we" are so it knows what risks matter to you.
2. Go to the Code tab (top menu).
3. Navigate to the config/ folder and click on company_profile.json.
4. Click the Pencil Icon (Edit file) in the top right.
5. Change the details to match your company.
	- Risk Tolerance: Be specific (e.g., "Zero tolerance for Privacy risks," but "Moderate tolerance for Operational uptime").
	- Hard Requirements: List non-negotiables (e.g., "MUST have SOC 2," "MUST NOT sell data").
	- Risk Strategy: Tell the AI how to solve problems (e.g., "Legal bandwidth is low" -> Prefer technical controls over contract negotiation).
6. Click Commit changes (green button) to save.

# 📖 How to Use (Daily Workflow)

### 1. Request a New Vendor

- Go to the Issues tab.
- Click New Issue.
- Select "New Supplier".
- Fill in the form (Website, T&Cs link, Service Description).
- Click Submit.
- The AI will immediately start searching for documents.

### 2. Review Documents

- Wait for the AI to comment with a Checklist of Documents.
- It will find T&Cs, Privacy Policies, and Security pages automatically.
- Uncheck any documents that look irrelevant.
- (Optional) Upload any offline PDFs if you have them.
- When ready, add the Label: ready-for-analysis (on the right sidebar).

### 3. Get the Risk Report

- The AI will read everything and post a Detailed Risk Analysis comment.
- It covers GDPR, Security Controls, and Liability risks.
- It also drafts a "Reviewer-Approved Data" block.

### 4. Approve & Archive

- Read the report.
- Edit the JSON block in the comment if you want to change the risk rating or mitigations.
- Close the Issue as "Completed".
- The system will automatically save the approved vendor to your database (suppliers/ folder) and archive the audit trail.

# ⚙️ For Developers (Under the Hood)

This system uses Python scripts triggered by GitHub Actions to orchestrate the workflow.

### Core Scripts:

- `scripts/discover_documents.py`: Crawls URLs and builds the document checklist.
- `scripts/consolidate_and_analyze.py`: Compiles text and runs the Security/Legal AI analysis tasks.
- `scripts/commit_approved_vendor.py`: Parses the final human review and commits the data to JSON storage.

### Customization:

Company Profile: Edit `config/company_profile.json` to change the "Lens" the AI uses for risk assessment.

Prompt Engineering: Edit the JSON files in task_templates/ to change how the AI thinks. If you change a template, re-run the "Setup Rightbrain Tasks" workflow to update the live AI.

## 📂 Code Structure

This project follows a modular structure designed for automated risk analysis.

- `.github/`:
	- `workflows/`: The automation engine. Contains YAML files for Discovery, Analysis, and Approval triggers.
	- `ISSUE_TEMPLATE/`: Defines the "New Supplier" intake form (structured-new-supplier.yml).

- `config/`:
	- `company_profile.json`: Critical. This is the commercial context for the AI — defining your risk tolerance, hard requirements, and compliance needs.
	- `rightbrain.config.json & model_manifest.json`: Configuration for the AI client and model versions.

- `scripts/`: The Python logic that powers the tool.
	- `discover_documents.py`: Finds and downloads PDFs/Webpages.
	- `consolidate_and_analyze.py`: Sends data to the AI for legal/security review.
	- `commit_approved_vendor.py`: Saves the final approved data to the suppliers/ database.
	- `update_existing_vendor.py`: Re-evaluates vendors periodically.
	- `setup_rightbrain.py`: One-time script to deploy AI tasks to your project.

- `suppliers/`: Your database of approved vendors.
	- *Example*: `subprocessors/anthropic/` contains the full audit trail, approved T&Cs (snapshot in time), and risk report for Anthropic.
	- `data-processors.json`: A central registry of all approved processors.

- `tasks/`: The AI Task definitions.
	- `discovery_task.json`: Instructions for the AI to crawl and find documents.
	- `document_classifier.json`: Instructions for categorizing files (Legal vs. Security).
	- `security_posture_analyzer.json`: Instructions for the AI to find security controls.
	- `sub_processor_terms_analyzer.json`: Instructions for the AI to review legal liability and DPA terms.
	- `vendor_risk_reporter.json`: Instructions for synthesizing the final executive summary.

- `utils/`: Shared Python libraries for API interactions (github_api.py, rightbrain_api.py).

## License

This project is licensed under the MIT License. See the LICENSE file for details.
