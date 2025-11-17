## 🤝 Contributing Guide

First off, thank you for considering contributing to the AI-Powered Vendor Onboarding Tool! We're excited to have you.

This project welcomes two main types of contributions:

For Subject Matter Experts (SMEs): You can help by improving the AI's intelligence. This involves editing the JSON task templates (like system_prompt and user_prompt) to make the AI's analysis and risk reporting more accurate and insightful.

For Developers: You can help by improving the Python code, fixing bugs, or adding new features to the automation workflows.

## 📜 The Golden Rules

Start with an Issue: All contributions—whether they are bug reports, feature requests, or simple prompt tweaks—must begin by creating a GitHub Issue. This prevents duplicated work and allows us to discuss the change before you spend time on it.

Be Respectful: Please be friendly, respectful, and collaborative in all discussions and contributions.

Get Help: If you have questions about the contribution process, you can file an Issue or email us at support@rightbrain.ai.

## 🧑‍⚖️ How to Contribute as a Subject Matter Expert (AI Prompt Editor)

Your role is to improve the intelligence of the AI Tasks, which are defined in the .json files within the task_templates/ directory.

### ⚠️ SME Golden Rules: What to Edit

To prevent breaking the automation, it is critical that you only edit specific fields within the JSON task files.

### ✅ Safe to Edit:

These fields control the AI's "brain" and are perfect for SME contributions:

* **name:** The display name of the task.

* **description:** A high-level description of what the task does.

* **system_prompt:** The AI's persona, rules, and overall instructions.

* **user_prompt:** The specific instructions and dynamic inputs ({variable}) for a single run.

### ❌ Do Not Edit (File an Issue Instead):

Changing these fields will break the Python scripts and is considered a "Developer Change."

* **output_format:** (Critical) Do not add, remove, or rename any fields here. This JSON schema is what the Python code expects. If you think the schema is wrong or missing something, please file an Issue to discuss it.

* **llm_model_id:** Do not change the AI model.

* input_processors:** Do not change any input processors.

* Any other top-level field not in the "Safe to Edit" list.

If you believe one of these fields needs to be changed, please file a new Issue with the "feature request" template to discuss it.

## 📝 Your First Contribution (The Easy Way)

You don't need to be a Git expert. You can make your changes entirely through the GitHub website.

1. **Find the file:** Navigate to the task_templates/ directory in this repository.

2. **Open the file:** Click on the task you want to improve (e.g., sub_processor_terms_analyzer.json).

3. **Click the Edit icon:** In the top-right corner of the file view, click the pencil icon (✏️) to "Edit this file."

4. **Make your changes:** Edit the system_prompt or user_prompt in the text editor.

5. **Save your changes:** Once you're done, scroll to the bottom of the page.

6. **Write a clear commit message** (e.g., "task: Improves risk analysis in vendor_risk_reporter").

7. **Add a description** (e.g., "Updated the system prompt to be more aggressive in flagging liability carve-outs.")

8. Make sure "Create a new branch for this commit and start a pull request" is selected.

9. Click "Propose changes."

10. **Open the Pull Request:** On the next screen, click "Create pull request." Please fill out the template, linking to the Issue you created in Step 1.

### 🧪 Testing Your Changes (Highly Recommended)

The best way to test your prompt changes is in your own Rightbrain account.

1. In your Rightbrain project, create a new, temporary Task.

2. Copy and paste your entire edited JSON from GitHub into the task's JSON editor.

3. Go to the "Run Task" view in the Rightbrain UI.

4. Fill in the input variables with test data and run the task.

5. Check the results. Does the AI's output match your new instructions? Is the JSON output still valid?

6. In your Pull Request, please describe the tests you ran and confirm that the new prompt produced better results. If you don't have a Rightbrain account, please explain in detail why you believe your changes are an improvement.

## 👩‍💻 How to Contribute as a Developer (Python Code)

(Note: This section is a placeholder. We will add details on code style and testing soon!)

### The Workflow

Fork the repository to your own GitHub account.

Clone your fork to your local machine: git clone https://github.com/YOUR-USERNAME/vendor-risk-tool.git

Create a branch for your changes: git checkout -b feat/my-new-feature

Make your changes.

Commit and push to your fork.

Open a Pull Request.

⚙️ Local Setup

(Placeholder)

We will add details on setting up a Python virtual environment and installing dependencies from requirements.txt here.

🎨 Code Style

(Placeholder)

We will add details on our linter (e.g., black, flake8) and any code formatting standards here.

🔬 Running Tests

(Placeholder)

We will add details on how to run the test suite (e.g., pytest) here.

✅ Submitting Your Pull Request

Before you submit your Pull Request, please make sure you've done the following:

[ ] Linked your Pull Request to the GitHub Issue it resolves.

[ ] Written a clear, descriptive title (e.g., fix: ..., feat: ..., task: ...).

[ ] For SMEs: Confirmed you only edited "Safe to Edit" fields.

[ ] For SMEs: Described your testing process and results in the PR description.

[ ] For Developers: Ensured your code passes all (forthcoming) tests and style checks.

Thank you for helping make this tool better!