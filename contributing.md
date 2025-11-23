# 🤝 Contributing Guide

First off, thank you for considering contributing to the AI-Powered Vendor Onboarding Tool! We're excited to have you.

This project welcomes two main types of contributions:

1. Subject Matter Experts (SMEs): You help by improving the AI's intelligence. This involves editing the JSON task templates (like system_prompt) to make the AI's analysis and risk reporting more accurate and insightful.

2. Developers: You help by improving the Python code, fixing bugs, or adding new features to the automation workflows.

# 📜 The Golden Rules

- **Start with an Issue:** All contributions—whether they are bug reports, feature requests, or prompt tweaks—must begin by creating a GitHub Issue. This prevents duplicated work.

- **Be Respectful:** Please be friendly, respectful, and collaborative in all discussions.

- **Get Help:** If you have questions, file an Issue or email support.

# 🧑‍⚖️ How to Contribute as a Subject Matter Expert (AI Prompt Editor)

Your role is to improve the intelligence of the AI Tasks defined in the .json files within the task_templates/ directory.

## ⚠️ SME Golden Rules: Managing Automation Risk

The AI tasks are tightly integrated with Python automation scripts. Because the Python code injects specific data into the prompts and reads specific data from the outputs, you must follow these rules to avoid breaking the tool.

### ✅ Safe to Edit (Go Wild!)

These changes are low-risk and high-impact:

**System Prompt (system_prompt):** This is the best place to contribute. You can completely rewrite the AI's instructions, persona, and reasoning logic.

- _Safe Change:_ "You are a cynical security auditor who distrusts vagueness."

- _Safe Change:_ "Focus specifically on UK GDPR data transfer mechanisms."

**Output Descriptions:** Inside output_format, you can edit the description of any field. This is often the best way to fix AI hallucinations.

**Adding New Output Fields:** You can generally add new fields to the output_format.

- _Example:_ Adding a confidence_score field to an existing object.

- _Result:_ The AI will generate it, and it will appear in the raw JSON logs. (Note: It won't appear in the GitHub comment summary until a developer updates the Python formatter, but it won't break the build).

### ☢️ Dangerous (Requires Developer Pair)

These changes will likely break the Python automation:

**User Prompt Variables (user_prompt):** The user_prompt contains variables wrapped in curly braces, like {company_profile} or {document_text}.

- **Do NOT remove variables:** The Python script specifically injects data here. Removing them effectively "blinds" the AI to that data.

- **Do NOT add new variables:** If you add {new_data_point} to the prompt, the Python script does not know it needs to send that data. The task will fail or the variable will remain as raw text.

**Renaming/Deleting Output Fields:** The Python scripts look for specific JSON keys (e.g., overall_assessment, key_legal_risks) to generate the final report.

- **Do NOT rename keys:** If you rename overall_assessment to risk_score, the report generation will fail.

- **Do NOT delete fields:** If you delete a field the code expects, the script may crash.

## 🧪 How to Test Your Changes

**Use the Rightbrain UI:** The best way to test is to copy your modified JSON into a temporary task in your Rightbrain account.

**Manually Fill Variables:** When you run the task in the UI, it will ask you to manually fill in the variables (like {company_profile}). You can copy this data from a previous GitHub issue comment to test realistic scenarios.

**Verify Output:** Check that the AI output follows your new instructions and that the JSON structure is valid.

# 👩‍💻 How to Contribute as a Developer (Python Code)

## 🔀 The Workflow

1. Fork the repository to your own GitHub account.

2. Clone your fork: git clone https://github.com/YOUR-USERNAME/vendor-risk-tool.git

3. Branch: git checkout -b feat/my-new-feature

4. Edit: Make your changes.

5. Commit & Push: Push to your fork.

6. Pull Request: Open a PR linking to the Issue.

## 💻 Local Setup

1. Ensure you have Python 3.9+ installed.

2. Install dependencies: pip install -r requirements.txt

3. Set up your .env file with RB_API_KEY and GITHUB_TOKEN (see .env.example).

# 📋 Checklist Before Submitting

- [ ] Linked your Pull Request to the GitHub Issue it resolves.

- [ ] SMEs: Confirmed you did not remove {variables} from the User Prompt or rename Output keys.

- [ ] Developers: Ensured code passes linting and local tests.

Thank you for helping make this tool better!
