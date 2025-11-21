# Vendor Audit: Anthropic

**Original Issue:** [https://github.com/RightbrainAI/office_box/issues/4](https://github.com/RightbrainAI/office_box/issues/4)

---

## Original Request

### Supplier Name

Anthropic

### Data Processor

Yes

### Minimum Term Length

1 month

### Supplier Site

https://www.anthropic.com/

### Rightbrain contact

Product

### T&Cs

https://www.anthropic.com/legal/commercial-terms

### Security Documents URL

https://trust.anthropic.com/

### Vendor/Service Usage Context

We will use the Anthropic API to power AI functionality in our app

### Data Types Involved

Customer instructions relating to their role in a dungeons and dragons style game. 

### How will the supplier be paid?

Company credit card

### Reviewer

Vendor Risk Manager

---

<!--CHECKLIST_MARKER-->
## Documents for Analysis

🤖 AI has performed discovery, classification, and fetched text for relevant documents. The fetched text files have been committed to the `_vendor_analysis_source` directory.

**ACTION REQUIRED:**
1.  **Review the checklist below.** Uncheck any documents you deem irrelevant for the final analysis.
2.  For **'Awaiting Document'** items, please upload the corresponding file(s) manually to the `_vendor_analysis_source` directory. Name them clearly (e.g., `issue-{issue_number}-Order_Form.pdf`).
3.  Once all documents are reviewed and uploaded, add the `ready-for-analysis` label to trigger the analysis workflow.

### Online Documents Found
*(Links point to the fetched text saved in the repo)*

- [x] **Legal**: [`Main T&Cs`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Main_T%26Cs.txt) (`https://www.anthropic.com/legal/commercial-terms`)
- [x] **Security**: [`Main Security Page`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Main_Security_Page.txt) (`https://trust.anthropic.com/`)
- [ ] **Legal**: [`Consumer Terms of Service`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Consumer_Terms_of_Service.txt) (`https://www.anthropic.com/legal/terms`)
- [x] **Legal, Security**: [`Data Processing Addendum`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt) (`https://www.anthropic.com/legal/data-processing-addendum`)
- [x] **Legal**: [`Usage Policy`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Usage_Policy.txt) (`https://console.anthropic.com/legal/aup`)
- [ ] **Legal**: [`Supported Regions Policy`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Supported_Regions_Policy.txt) (`https://www.anthropic.com/supported-countries`)
- [x] **Legal, Security**: [`Service Specific Terms`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Service_Specific_Terms.txt) (`https://www.anthropic.com/legal/service-specific-terms`)
- [ ] **None**: [`Publicity Opt-out Form`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Publicity_Opt-out_Form.txt) (`https://ea4l3.share.hsforms.com/2SPy6FrbrRAGnV6R81qaHnA`)
- [x] **Legal, Security**: [`Model Pricing Page`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Model_Pricing_Page.txt) (`https://www.anthropic.com/pricing`)
- [x] **Legal**: [`Supplemental Credits Terms`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-4-Supplemental_Credits_Terms.txt) (`https://www.anthropic.com/legal/credit-terms`)
### Offline / Unlinked References
*(Please upload these manually)*

- [ ] **Awaiting Document (Relevant)**: `Vanta`
  > *Mentioned in: "Vanta"*

---

## Issue Discussion & Analysis

### Comment from @github-actions[bot] (at 2025-11-21T03:14:36Z)

## 🚀 AI-Generated Risk Summary
### **Overall Assessment: Low**
**Executive Summary:** Anthropic's API presents a LOW overall risk for powering AI functionality in our app for D&D game interactions. While the vendor has strong security certifications (SOC 2, ISO 27001, HIPAA) and robust technical controls, two contractual gaps exist: liability is capped at 12 months' fees with no data breach carve-out, and indemnification excludes regulatory fines. However, given the low-sensitivity nature of the data (game-related customer instructions) and Anthropic's explicit prohibition on training models with our data, these gaps do not elevate risk beyond acceptable levels for this specific use case. The 48-hour breach notification meets GDPR requirements, and comprehensive DPA with SCCs ensures compliant data transfers.

### ✅ Positive Findings
* **Comprehensive security certifications:** SOC 2 Type 2, ISO 27001, ISO 42001, CSA Star, and HIPAA certifications demonstrate mature security program exceeding requirements for game data processing.
* **Prohibition on training with customer data:** Explicit contractual prohibition on using customer content for model training eliminates IP leakage and confidentiality risks.
* **Strong technical security controls:** MFA for all production access, AES-256 encryption at rest, TLS 1.2+ in transit, and annual penetration testing provide robust data protection.
* **GDPR-compliant data processing framework:** Comprehensive DPA with SCCs, UK Addendum, 48-hour breach notification, and 30-day deletion timeline ensures regulatory compliance.

### ⚖️ Key Legal Risks
* **Risk:** Liability cap at 12 months' fees applies to data breaches
  * **Summary:** No special carve-out for data breach damages or GDPR fines could expose SecureCloud to uncovered losses if a breach occurs. However, given the low-sensitivity game data, actual exposure is minimal.
  * **Recommendation:** Accept risk for this use case but document in risk register. For future high-sensitivity use cases, negotiate higher liability caps.
* **Risk:** No indemnification for data breaches or regulatory fines
  * **Summary:** Anthropic only indemnifies IP claims, leaving us exposed for data protection violations. Given our role as a compliance provider, this gap could be material for sensitive data but is acceptable for game data.
  * **Recommendation:** Accept for current use case. Include contractual review trigger if expanding to sensitive data processing.

### 🛡️ Key Security Gaps
* **Gap:** Missing application security practices documentation
  * **Summary:** No evidence of security code reviews, SAST/DAST, or open-source vulnerability management. While vulnerability scanning is mentioned, specific application security controls are unclear.
  * **Recommendation:** Request SOC 2 Type 2 report to verify application security controls within 30 days of contract execution.
* **Gap:** No documented data backup or recovery testing procedures
  * **Summary:** While BC/DR plans exist, specific backup policies and recovery testing cadence are not documented, creating uncertainty about RPO/RTO for service restoration.
  * **Recommendation:** Accept for game data use case but clarify backup/recovery procedures if expanding usage.

---

## 📝 Reviewer-Approved Data (Draft)
Please review, edit, and confirm the details below. This JSON block will be committed to the central vendor registry upon issue closure.

**ACTION REQUIRED:** Before closing this issue, please **edit the `mitigations` field** (and any others) in the JSON block below to reflect the final, agreed-upon controls.
```json
{
  "mitigations": "Request SOC 2 report within 30 days; Document liability gap in risk register; Review contract if expanding to sensitive data",
  "risk_rating": "Low",
  "usage_summary": "AI functionality for customer D&D game interactions",
  "processor_name": "Anthropic",
  "key_legal_finding": "Liability capped at 12 months' fees with no data breach carve-out, but acceptable given low-sensitivity game data",
  "relationship_owner": "N/A",
  "termination_notice": "30 days prior notice by Anthropic; Customer may terminate at any time",
  "service_description": "Anthropic API to power AI functionality in our app",
  "key_security_finding": "Strong security certifications (SOC 2, ISO 27001) and controls, though application security practices need verification",
  "data_processing_status": "Processor"
}
```

---

## 🤖 Raw Analysis Data (for review)

### 🛡️ Security Posture Analysis (Raw)
```json
{
  "certifications": [
    {
      "quote": "Claude via Anthropic's API - SOC 2 Type 2 \u2705",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt",
      "certification_name": "SOC 2 Type 2"
    },
    {
      "quote": "Claude via Anthropic's API - ISO 27001 \u2705",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt",
      "certification_name": "ISO 27001"
    },
    {
      "quote": "Claude via Anthropic's API - ISO 42001 \u2705",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt",
      "certification_name": "ISO 42001"
    },
    {
      "quote": "Claude via Anthropic's API - CSA Star \u2705",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt",
      "certification_name": "CSA Star"
    },
    {
      "quote": "Claude via Anthropic's API - HIPAA \u2705",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt",
      "certification_name": "HIPAA"
    }
  ],
  "incident_response": {
    "customer_notification_timeline": {
      "quote": "Anthropic will notify Customer in writing without undue delay, but in any event within 48 hours, after becoming aware of any Security Breach",
      "answer": "48 hours",
      "summary": "The 48-hour notification timeline is acceptable for our game-related data processing given the low sensitivity of the data involved.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    }
  },
  "data_security_and_privacy": {
    "data_loss_prevention": {
      "quote": "",
      "answer": false,
      "summary": "No specific data loss prevention (DLP) controls or policies were mentioned in the provided documents.",
      "source_url": ""
    },
    "data_encryption_at_rest": {
      "quote": "All data that Anthropic stores is encrypted at rest using AES-256 GCM",
      "answer": true,
      "summary": "AES-256 encryption at rest exceeds requirements for our low-risk game data processing use case, providing strong data protection.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "data_classification_policy": {
      "quote": "Data classification policy established - The company has a data classification policy in place to help ensure that confidential data is properly secured and restricted to authorized personnel.",
      "answer": true,
      "summary": "The data classification policy is sufficient for our game-related data processing, providing adequate data handling frameworks.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "data_encryption_in_transit": {
      "quote": "protected in transit using TLS 1.2+",
      "answer": true,
      "summary": "TLS 1.2+ for data in transit is appropriate for our game data processing, ensuring secure data transmission.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "customer_data_access_policy": {
      "quote": "",
      "answer": false,
      "summary": "No specific customer data access policy or procedures were detailed in the provided documents.",
      "source_url": ""
    }
  },
  "governance_risk_and_compliance": {
    "risk_management_process": {
      "quote": "Risk management program established - The company has a documented risk management program in place that includes guidance on the identification of potential threats, rating the significance of the risks associated with the identified threats, and mitigation strategies for those risks.",
      "answer": true,
      "summary": "The risk management process is sufficient for our game-related data processing scenario.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "information_security_program": {
      "quote": "Anthropic maintains organizational management and dedicated staff responsible for the development, implementation, and maintenance of Anthropic's information security program",
      "answer": true,
      "summary": "The information security program provides adequate governance for our low-risk game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "third_party_vendor_management": {
      "quote": "Anthropic maintains a third-party information security risk management program, which includes the execution of periodic risk assessments to evaluate the security posture of Anthropic's third-party vendors.",
      "answer": true,
      "summary": "Third-party vendor management is adequate for our low-risk game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    }
  },
  "identity_and_access_management": {
    "password_policy": {
      "quote": "Anthropic maintains strong password requirements including: a minimum of 16 characters; changing of initial passwords; and the prevention of password re-use.",
      "answer": true,
      "summary": "The password policy exceeds standard requirements and is sufficient for our game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "periodic_access_reviews": {
      "quote": "Anthropic reviews privileged access to systems managing Customer Data on a regular basis to ensure provisioned access remains appropriate to job functions or business needs.",
      "answer": true,
      "summary": "Regular access reviews provide adequate assurance for our low-risk game data processing scenario.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "mfa_for_production_access": {
      "quote": "All access to systems processing Customer Data are protected by Multi Factor Authentication (MFA).",
      "answer": true,
      "summary": "MFA for production access provides strong authentication for our game data processing environment.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "least_privilege_access_control": {
      "quote": "Anthropic maintains a least privileged access approach to system access, using RBAC (Role Based Access Control), by restricting Anthropic personnel to only the system access needed to fulfill a specific job function or business needs.",
      "answer": true,
      "summary": "Least privilege access control is appropriate for our game data processing, ensuring proper access restrictions.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    }
  },
  "personnel_and_physical_security": {
    "employee_background_checks": {
      "quote": "As a part of pre-employment, all candidates complete a rigorous interview process, undergo background checks, and sign confidentiality agreements.",
      "answer": true,
      "summary": "Background checks provide adequate personnel security for our low-risk game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "security_awareness_training": {
      "quote": "Anthropic employees, at hire and annually thereafter, complete security awareness, HIPAA, and other relevant training regarding confidentiality and data security.",
      "answer": true,
      "summary": "Annual security awareness training is appropriate for our game data processing scenario.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "physical_data_center_security": {
      "quote": "",
      "answer": false,
      "summary": "While third-party data centers are mentioned (AWS, GCP), no specific physical security controls were detailed in the provided documents.",
      "source_url": ""
    }
  },
  "application_and_software_security": {
    "secure_sdlc_policy": {
      "quote": "Development lifecycle established - The company has a formal systems development life cycle (SDLC) methodology in place that governs the development, acquisition, implementation, changes (including emergency changes), and maintenance of information systems and related technology requirements.",
      "answer": true,
      "summary": "The SDLC policy is sufficient for our low-risk game-related data processing use case, providing adequate assurance for standard development practices.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "security_code_reviews": {
      "quote": "",
      "answer": false,
      "summary": "No explicit mention of security-focused code reviews was found in the provided documents.",
      "source_url": ""
    },
    "static_dynamic_code_analysis": {
      "quote": "",
      "answer": false,
      "summary": "No mention of static or dynamic code analysis tools or processes was found in the provided documents.",
      "source_url": ""
    },
    "open_source_vulnerability_management": {
      "quote": "",
      "answer": false,
      "summary": "No specific open-source vulnerability management program or tooling was mentioned in the provided documents.",
      "source_url": ""
    }
  },
  "threat_and_vulnerability_management": {
    "bug_bounty_program": {
      "quote": "",
      "answer": false,
      "summary": "No bug bounty program was mentioned in the provided documents.",
      "source_url": ""
    },
    "vulnerability_scanning": {
      "quote": "Anthropic utilizes a multi-faceted approach to vulnerability management, including: automated code vulnerability scanning; automated artifact vulnerability scanning; automated code review; manual peer code review",
      "answer": true,
      "summary": "Multi-layered vulnerability scanning is appropriate for our low-risk game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "patch_management_policy": {
      "quote": "Anthropic applies updates to mitigate vulnerabilities based on risk level and in alignment with industry-accepted timelines.",
      "answer": true,
      "summary": "The patch management policy is sufficient for our low-risk game data processing use case.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    },
    "third_party_penetration_testing": {
      "quote": "Anthropic engages qualified external assessors for the completion of annual penetration testing of systems that process Customer Data to identify vulnerabilities and attack vectors that can be used to exploit those systems",
      "answer": true,
      "summary": "Annual third-party penetration testing provides adequate assurance for our game data processing scenario.",
      "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt"
    }
  },
  "business_continuity_and_disaster_recovery": {
    "bcdr_plan_exists": {
      "quote": "Continuity and Disaster Recovery plans established - The company has Business Continuity and Disaster Recovery Plans in place that outline communication plans in order to maintain information security continuity in the event of the unavailability of key personnel.",
      "answer": true,
      "summary": "BC/DR plans are appropriate for our low-risk game data processing scenario, providing reasonable assurance of service continuity.",
      "source_url": "_vendor_analysis_source/issue-4-Main_Security_Page.txt"
    },
    "data_backup_policy": {
      "quote": "",
      "answer": false,
      "summary": "While BC/DR plans are mentioned, no specific data backup policy or procedures were detailed in the provided documents.",
      "source_url": ""
    },
    "recovery_plan_testing": {
      "quote": "",
      "answer": false,
      "summary": "No mention of recovery plan testing frequency or results was found in the provided documents.",
      "source_url": ""
    }
  }
}
```

### ⚖️ Legal & DPA Analysis (Raw)
```json
{
  "audit_rights": {
    "quote": "Upon Customer\u2019s written request, Anthropic will permit Customer, at Customer\u2019s expense, to audit Anthropic\u2019s applicable controls and compliance with this DPA... provided such Audit is... (b) Customer and Anthropic mutually agree on reasonable details of the Audit... (c) a similar Audit has not already been conducted less than twelve (12) months prior... Customer will pay any reasonably incurred costs and expenses incurred by Anthropic in the event Customer performs an Audit that is not (a) required by Applicable Data Protection Laws or (b) in response to a Security Breach.",
    "summary": "Medium-risk: Anthropic allows audits only once every 12 months unless triggered by breach or law, and we bear all costs unless the audit is legally mandated or follows a Security Breach.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "audit_procedure": "Written request \u2192 mutual agreement on scope/timing \u2192 auditor NDA \u2192 Customer pays unless mandated by law or Security Breach.",
    "has_audit_rights": true,
    "conditions_and_limitations": "12-month gap unless non-compliance indicators; scope & timing must be mutually agreed; Customer pays unless audit is legally required or post-breach."
  },
  "data_deletion": {
    "quote": "Within thirty (30) days of the date of termination or expiration of the Agreement, Anthropic will... delete all copies of Customer Data... except to the extent (i) Applicable Data Protection Laws... requires storage... (ii) retention... is necessary to resolve a dispute... or (iii) retention... is necessary to combat harmful use of the Services.",
    "comment": "30-day deletion is GDPR-compliant, but exceptions for legal holds or security investigations could keep data longer\u2014ensure we track deletion confirmations.",
    "summary": "Low-risk: 30-day deletion window aligns with GDPR; carve-outs for legal/regulatory holds, dispute resolution, or abuse mitigation are standard.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "timeline_days": 30.0
  },
  "governing_law": {
    "quote": "These Terms are governed by and construed in accordance with the Governing Laws... (i) for Customers in the EEA, Switzerland, or UK, the Laws of Ireland...",
    "answer": "Irish law for UK-based customers.",
    "comment": "Irish law mirrors UK GDPR post-Brexit, reducing legal-interpretation risk.",
    "summary": "Low-risk for UK entity: Irish law applies, keeping us inside familiar EU/UK GDPR jurisprudence and courts.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt"
  },
  "service_levels": {
    "quote": "Anthropic is audited annually against known, established industry standards performed by external auditors... Anthropic\u2019s current certifications are available for Customer\u2019s review at trust.anthropic.com.",
    "summary": "Medium-risk: No uptime SLA in Terms; only annual SOC 2 etc. audits available. Outages could disrupt our DLP service without contractual credits.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "remedy_credits": "None specified; only right is to review audit reports.",
    "uptime_commitment": "None specified."
  },
  "confidentiality": {
    "quote": "Recipient will protect Discloser\u2019s Confidential Information... with no less than reasonable care... Recipient will destroy Discloser\u2019s Confidential Information promptly upon request...",
    "summary": "Standard reasonable-care clause; destruction on request helps limit exposure after termination.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt",
    "survival_period": "Survives so long as the information remains confidential plus upon-request destruction."
  },
  "indemnification": {
    "quote": "Anthropic will defend Customer... from and against any Customer Claim... alleging that Customer\u2019s paid use of the Services... violates any third-party intellectual property right.",
    "comment": "IP-only indemnity is narrow; no indemnity for regulatory fines or data-breach claims\u2014high residual risk given our DLP/compliance role.",
    "summary": "High-risk: Indemnity covers only third-party IP claims; excludes data-breach, regulatory fines, or misuse of outputs\u2014leaving us exposed.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt",
    "covers_customer": true,
    "covers_data_breach": false,
    "covers_ip_infringement": true
  },
  "termination_rights": {
    "quote": "Each party may terminate these Terms at any time for convenience with Notice, except Anthropic must provide 30 days prior Notice... Anthropic may suspend... if... (ii) Customer or any User is using the Services in violation of Sections D.1 (Compliance), D.2 (Policies and Service Terms) or D.4 (Use Restrictions).",
    "summary": "30-day convenience termination; immediate suspension for policy breaches\u2014could halt our service without recourse if our game content trips usage rules.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt",
    "for_cause_conditions": "30-day cure period for material breach; immediate suspension for legal/policy violations.",
    "for_convenience_timeline": "30 days prior notice by Anthropic; Customer may terminate at any time."
  },
  "breach_notification": {
    "quote": "Anthropic will notify Customer in writing without undue delay, but in any event within 48 hours, after becoming aware of any Security Breach...",
    "summary": "48-hour breach notification meets GDPR \u2018without undue delay\u2019 standard.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "notification_timeline": "48 hours",
    "notification_procedure": "Written notice to Customer with categories/numbers of data subjects, likely consequences, and mitigation measures."
  },
  "subprocessor_flow_down": {
    "quote": "Anthropic will: (a) enter into a contractual agreement with each Subprocessor imposing data protection obligations... (b) remain liable... Anthropic will provide Customer reasonable notice of the new Subprocessor... Customer may... object... within fifteen (15) days...",
    "summary": "Standard GDPR sub-processor regime with 15-day objection right; list available online.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "objection_rights": true,
    "subprocessor_list_url": "https://www.anthropic.com/subprocessors",
    "right_to_use_subprocessors": true,
    "notification_for_new_subprocessors": "Reasonable notice before engagement; 15-day objection window."
  },
  "data_usage_for_training": {
    "quote": "Anthropic may not train models on Customer Content from Services.",
    "answer": false,
    "comment": "Clear contractual prohibition reduces IP & confidentiality risk; ensure Development Partner Mode stays disabled.",
    "summary": "Low-risk: express prohibition on using our inputs/outputs for model training.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt"
  },
  "limitation_of_liability": {
    "quote": "The liability of each party... is limited to Fees paid by Customer for the Services in the previous 12 months... The limitations... do not apply to either party\u2019s obligations under Section K (Indemnification).",
    "comment": "12-month cap includes data-breach damages\u2014high-risk because our DLP service could face large downstream claims; no carve-out for GDPR fines.",
    "summary": "High-risk: Liability capped at 12 months of fees with no special carve-out for data breaches or privacy fines\u2014potential exposure mismatch.",
    "cap_amount": "Fees paid in previous 12 months",
    "carve_outs": "Excludes consequential/indirect damages and does not apply to indemnification obligations.",
    "source_url": "_vendor_analysis_source/issue-4-Main_T&Cs.txt",
    "data_breach_liability_cap": "Same 12-month fee cap applies\u2014no special carve-out."
  },
  "data_processing_addendum": {
    "quote": "This Data Processing Addendum... applies to Anthropic\u2019s processing of Customer Data... Anthropic will not: (a) \u201csell\u201d or \u201cshare\u201d Customer Personal Data... (b) retain, use, or disclose Customer Personal Data outside of the direct business relationship...",
    "summary": "Comprehensive DPA with GDPR controller-processor terms; incorporates SCCs and UK Addendum for transfers.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "is_dpa_referenced": true,
    "data_transfer_mechanisms": "EU SCCs Module 2/3, UK Addendum, Swiss Addendum where applicable."
  },
  "data_residency_and_transfers": {
    "quote": "The parties agree that... the terms of the SCCs... are hereby incorporated by reference... For Customers in the EEA, Switzerland or UK... the courts of Ireland...",
    "summary": "Transfers governed by SCCs and UK Addendum with Ireland as forum; data may be processed globally via subprocessors.",
    "source_url": "_vendor_analysis_source/issue-4-Data_Processing_Addendum.txt",
    "transfer_mechanisms_uk_eu": "EU SCCs Module 2/3 + UK Addendum; Irish law & courts.",
    "storage_and_processing_locations": "Global\u2014subprocessor list includes US and other territories."
  }
}
```

---

