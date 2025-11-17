## AI-Powered Vendor Onboarding Tool

This project provides a complete, automated workflow for conducting vendor risk assessments using GitHub Issues and Rightbrain AI Tasks.

It listens for new vendor onboarding requests, automatically discovers and analyzes all associated legal and security documents, and produces a high-level risk report to accelerate your compliance workflow.

## How It Works

The system is built on three automated Python scripts triggered by GitHub Actions:

1. **Discovery** (scripts/discover_documents.py)

* **Trigger:** A new issue is created with the vendor-onboarding label.

**Action:** The script scans the issue for T&Cs and Security URLs, then uses the discovery_task to crawl those pages and find all linked documents. It then uses the document_classifier to categorize them, saves the text, and updates the issue with a checklist for human review.

2. **Analysis** (scripts/consolidate_and_analyze.py)

* **Trigger:** A human adds the ready-for-analysis label.

* **Action:** The script consolidates the text from all checked documents and sends them to the security_posture_analyzer and sub_processor_terms_analyzer tasks. The final vendor_risk_reporter task synthesizes these into a single report, which is posted as a comment.

3. **Commit** (scripts/commit_approved_vendor.py)

* **Trigger:** The issue is closed as "completed."

* **Action:** The script finds the last human-edited JSON block in the comments. It calculates review dates, archives the source documents and audit trail, and commits the final, approved vendor data to your central JSON database (e.g., eng/data-processors.json).

## 🚀 Open-Source Setup Guide

To get this tool running, you'll need to create a new public repository, create the AI tasks in your own Rightbrain project, and configure your GitHub repository.

**Step 1:** Clone and Prepare Your Repository

1. Clone the code from the private Rightbrain/suppliers repository to your local machine.

2. Create a new public repository on GitHub (e.g., your-org/vendor-risk-tool).

Push the cloned code to your new public repository.

**Step 2:** Configure Rightbrain Credentials

1. Log in to your Rightbrain account.

2. Create a new project (e.g., "Vendor Onboarding"). Note your Organization ID and Project ID.

3. Go to Settings > API Clients and create a new OAuth 2.0 Client.

4. Note the Client ID and Client Secret.

**Step 3:** Configure GitHub Secrets

In your new repository, go to Settings > Secrets and variables > Actions and create the following repository secrets:

`RB_ORG_ID`: Your Rightbrain Organization ID.

`RB_PROJECT_ID`: Your Rightbrain Project ID.

`RB_CLIENT_ID`: Your Rightbrain OAuth Client ID.

`RB_CLIENT_SECRET`: Your Rightbrain OAuth Client Secret.

`RB_OAUTH2_URL`: The full OAuth2 authentication endpoint URL (e.g., `https://oauth.rightbrain.ai/oauth2/auth`).

`RB_API_URL`: The full API base URL including the version path (e.g., `https://app.rightbrain.ai/api/v1`).

`GITHUB_TOKEN`: A GitHub Personal Access Token (classic) with repo and workflow scopes. This is needed for the setup script to create the Task Manifest.

**Step 4:** Run the Setup Script

You only need to do this once.

Go to the **Actions** tab in your repository.

Find the "Setup Rightbrain Tasks" workflow.

Click "Run workflow" from the main branch.

This script ('scripts/setup_rightbrain.py') will connect to the Rightbrain API, read all the files from the `/task_templates` directory, and create the five necessary AI tasks in your project. It will then generate a `tasks/task_manifest.json` file and commit it to your repository. This file maps the task names to the unique Task IDs in your project, allowing the other scripts to find and run them.

##Step 5: Final Configuration

**Issue Templates:** This repository includes GitHub Issue Templates. When you create a new issue, select the "Vendor Onboarding Request" template.

**Company Profile:** Edit the `config/company_profile.json` file to reflect your organization's details. This context is used by the AI during analysis.

You are now ready to use the tool!

##🔧 Code Structure & Refactoring Plan

This project has been refactored for clarity and maintainability for its open-source release.

* `scripts/`: Contains the three core workflow scripts (discover..., consolidate..., commit...) and the new setup_rightbrain.py.

* `task_templates/`: Contains the JSON definitions for the five Rightbrain tasks. These are used by the setup script.

* `tasks/`:

    * `task_manifest.json`: (Auto-generated) This critical file maps task names (e.g., discovery_task.json) to the unique Task IDs created in your project.

* `utils/`:

    * `rightbrain_api.py`: A central module for handling authentication and execution of Rightbrain tasks.

    * `github_api.py`: A central module for all interactions with the GitHub API (posting comments, updating issues).

* `config/`:

    * `company_profile.json`: Your company's profile, used as context for the AI.

* `.github/`:

    * `workflows/`: Contains the GitHub Actions YAML files that trigger the scripts.

    * `ISSUE_TEMPLATE/`: Contains the issue template needed for the discover_documents.py script to parse inputs.

* `eng/` & `general_vendors/`: (Auto-generated) These directories are created by commit_approved_vendor.py to store your final vendor data and audit logs.

* `_vendor_analysis_source/`: (Temporary) This directory is used to store fetched document text during an active review. It is automatically cleaned up by commit_approved_vendor.py.

License

This project is licensed under the MIT License. See the LICENSE file for details.
