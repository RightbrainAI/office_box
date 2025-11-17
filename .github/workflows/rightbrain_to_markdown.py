import json

# Load the Rightbrain JSON output
with open('rightbrain_output.json', 'r') as f:
    data = json.load(f)

# Extract relevant data
risk_analysis = data['response']['Risk analysis']
risk_register = data['response']['Risk register']
dpa_amendments = data['response']['Rightbrain DPA amendments']

# Create Markdown content
markdown_content = f"""
## Risk Analysis

{risk_analysis}

## Risk Register

| Risk ID | Description | Likelihood | Impact | Mitigation Measures | Priority |
|---|---|---|---|---|---|
"""

for risk in risk_register:
    markdown_content += f"| {risk['Risk ID']} | {risk['Description']} | {risk['Likelihood']} | {risk['Impact']} | {risk['Mitigation Measures']} | {risk['Priority']} |\n"

markdown_content += f"""

## Rightbrain DPA Amendments

{dpa_amendments}
"""

# Save the Markdown file
with open('rightbrain_results.md', 'w') as f:
    f.write(markdown_content)
