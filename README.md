# AI-Powered Vendor Onboarding Tool

For most startups, vendor compliance is a distraction. You either waste hours chasing PDFs and trying to manage it yourself, or you ignore it altogether until investors ask for your data room.

This repository offers a better way: turning compliance into a git-backed CI/CD pipeline. Instead of scrambling to find documents later, you open a GitHub Issue today. The system spiders the vendor's documentation, runs parallel legal and security analysis using specialized LLM tasks, and commits the results directly to your repo as a version-controlled audit trail.

# ⚡ Architecture

This tool treats compliance as an event-driven workflow:

1. Trigger: A new Issue (New Supplier) triggers the on_issue_opened workflow.
1. Discovery (Spidering): scripts/discover_documents.py executes a Rightbrain Discovery Task to crawl the provided URL, identifying deep-linked assets (DPAs, SOC2 reports, Sub-processor lists) and distinguishing them from defined terms.
1. Analysis (Parallel Execution):
	- Legal: scripts/consolidate_and_analyze.py pipes compiled text to a Legal Analyst Task (extracting indemnities, liability caps, jurisdiction).
	- Security: Parallel execution of a Security Posture Task (extracting ISO/SOC2 validity, encryption standards, breach notification SLAs).
1. Synthesis (The "Risk Call"): A Risk Reporter Task aggregates raw findings and evaluates them against your specific company_profile.json (Risk Tolerance) to generate a Pass/Fail recommendation.
1. Persistence: Upon approval, scripts/commit_approved_vendor.py commits the finalized data to suppliers/data-processors.json and generates a permanent Markdown audit log.

# 🏁 Quick Start



### 1. Fork & Clone

Fork this repository to your private organization. This repo will become your central vendor registry.

### 2: Configure secrets

You need a Rightbrain API key to power the intelligence layer.

1. Create a free account at [app.rightbrain.ai](https://app.rightbrain.ai/).
1. Get your keys from Rightbrain Settings > API Clients.
1. Add the following to your Repo Secrets (Settings > Secrets and variables > Actions):

| Column 1  | Column 2  |
|:----------|:----------|
| `API_ROOT`    | `https://app.rightbrain.ai/api/v1`    |
| `RB_CLIENT_ID`    | OAuth Client ID    |
| `RB_CLIENT_SECRET`    | OAuth Client Secret    |
| `RB_ORG_ID`    | Your Rightbrain Org ID    |
| `RB_PROJECT_ID`    | Your Rightbrain Project ID    |
| `RIGHTBRAIN_ENVIRONMENT`    | `production`    |
| `TOKEN_URI`    | `https://oauth.rightbrain.ai/oauth2/token`    |


### 3: Deploy AI Tasks

This repo comes with pre-configured task definitions in tasks/. You need to deploy these to your Rightbrain project so the API can call them.

We've provided a bootstrap script to handle this:

```
# Locally, with env vars set, or via the "Setup Rightbrain Tasks" Action in the UI
python3 scripts/setup_rightbrain.py
```
This registers 5 tasks (Discovery, Classification, Legal, Security, Reporting) in your Rightbrain project.

# ⚙️ Configuration (The "Risk Lens")

The AI doesn't guess your risk appetite; it reads it from `config/company_profile.json.`

This is where you (or your external counsel) define the "Hard Checks". Configure it once, and the AI enforces your legal standard on every new vendor - no hourly billing required.

```
{
  "company_name": "Pied Piper Inc.",
  "description": "We are a Series B startup building a decentralized internet based on middle-out compression technology.",
  "jurisdiction": "California, USA (Silicon Valley)",
  "key_data_processed": [
    "User Metadata (Decentralized IDs)",
    "Encrypted Shards of User Files",
    "Compressed Video Streams (4K/8K)"
  ],
  "compliance_frameworks": [
    "COPPA (The 'PiperChat' Incident)",
    "GDPR (Global Users)",
    "CCPA",
    "App Store Guidelines"
  ],
  "risk_tolerance": {
    "privacy_and_security": "Zero. We pitch a 'new internet' that respects privacy. A leak destroys our core value proposition.",
    "legal_liability": "High (Strategic). Hooli will sue us regardless of what our contracts say. We treat legal defense as a distraction. We prefer to move fast and break things rather than die waiting for perfect indemnities.",
    "operational_uptime": "Critical. Our Weissman Score depends on low latency. We cannot tolerate slow vendors.",
    "reputational": "Very High. Our entire moat is the trust of the Open Source developer community. We cannot be associated with 'surveillance capitalism' vendors or data brokers."
  },
  "hard_requirements": [
    "MUST NOT be a subsidiary of Hooli or Endframe.",
    "MUST support decentralized storage protocols (IPFS/Filecoin compatible).",
    "MUST NOT track user data for advertising purposes."
  ],
  "risk_strategy_context": {
    "legal_bandwidth": "None. Jared is doing everything. If a contract requires redlining, we probably just won't sign it.",
    "engineering_bandwidth": "Infinite (Gilfoyle). We prefer to just hack around vendor limitations or encrypt data before sending it to them.",
    "financial_budget": "Volatile. We are cash-poor. We prefer Open Source or self-hosted solutions.",
    "preferred_resolution_hierarchy": [
      "1. Technical Control (encrypt it ourselves)",
      "2. Build it internal (Dinesh/Gilfoyle build)",
      "3. Legal Negotiation (Jared begs)",
      "4. Insurance (We probably can't afford it)"
    ]
  }
}
```
_Pro Tip: Because this is code, you can create a PR to update your risk policy. If you hire a fractional GC or get advice from a law firm, have them review this file. Merging their advice here scales their expertise across every future vendor review automatically._

# 🛠️ Usage

### 1. Engineer Workflow

- Go to Issues > New Issue.
- Select New Supplier.
- Paste the Vendor's URL (e.g., https://intercom.com) and a 1-sentence description of usage.
- Submit.

### 2. Reviewer Workflow

- Wait for Spidering: The bot will comment with a checklist of found documents (DPA, Privacy Policy, Security Whitepaper).
- Manual Override: If the bot missed a doc (e.g., a PDF behind a login), drag-and-drop it into a comment.
- Analysis: The bot posts a Risk Summary.
- Approval: Edit the JSON block in the final comment (if you want to override the AI's mitigations) and close the issue as Completed.

### 3. The Audit Trail

- Registry: Updates suppliers/data-processors.json.
- Audit Log: Creates suppliers/subprocessors/<vendor>/<vendor>.md containing the full decision log, links to analyzed docs, and the snapshot of terms agreed to.



# 🧠 Extending the Intelligence

The logic for how the AI analyzes documents is defined in tasks/*.json. You can modify these prompts to suit your specific risks.

- Want stricter GDPR checks? Edit `tasks/sub_processor_terms_analyzer.json`.
- Want to check for specific ISO certifications? Edit `tasks/security_posture_analyzer.json`.

If you work with external counsel, ask them for their "red lines" and bake them directly into these system prompts. After editing a task definition, re-run scripts/setup_rightbrain.py to update the active task in Rightbrain.

```
.
├── .github/workflows/          # CI/CD Orchestration
├── config/
│   └── company_profile.json    # <--- EDIT THIS (Your Risk Appetite)
├── scripts/                    # Python Logic
│   ├── discover_documents.py   # Spidering & Classification
│   ├── consolidate_and_analyze.py # RAG & Synthesis
│   └── commit_approved_vendor.py # Git Persistence
├── suppliers/                  # <--- YOUR DATA
│   ├── data-processors.json    # JSON Registry of all vendors
│   └── subprocessors/          # Folder per vendor with MD audit logs
└── tasks/                      # Rightbrain Task Definitions (Prompts)
```

## License

MIT
