# Vendor Audit: Sumsub

**Original Issue:** [https://github.com/RightbrainAI/office_box/issues/5](https://github.com/RightbrainAI/office_box/issues/5)

---

## Original Request

### Supplier Name

Sumsub

### Data Processor

Yes

### Minimum Term Length

12 months

### Supplier Site

https://sumsub.com

### Rightbrain contact

Tisats

### T&Cs

https://sumsub.com/terms-and-conditions/

### Security Documents URL

https://sumsub.com/sumsub-trust-center/

### Vendor/Service Usage Context

To verify customer identity as part of our KYC flow

### Data Types Involved

Selfie, name, copy of government ID, DoB

### How will the supplier be paid?

Company credit card

### Reviewer

tisats

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

- [x] **Legal**: [`Main T&Cs`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Main_T%26Cs.txt) (`https://sumsub.com/terms-and-conditions/`)
- [x] **Security**: [`Main Security Page`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Main_Security_Page.txt) (`https://sumsub.com/sumsub-trust-center/`)
- [ ] **Legal**: [`Cookie Policy`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Cookie_Policy.txt) (`https://sumsub.com/cookie-policy/`)
- [ ] **None**: [`Bahasa Indonesia Translation of Terms and Conditions`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Bahasa_Indonesia_Translation_of_Terms_and_Conditions.txt) (`https://sumsub.com/wp/files/Terms%20and%20Conditions%20-%20IND%20ver.pdf`)
- [x] **None**: [`Pricing Plans`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Pricing_Plans.txt) (`https://sumsub.com/pricing`)
- [ ] **Legal**: [`Copy Applicant Service Documentation`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Copy_Applicant_Service_Documentation.txt) (`https://docs.sumsub.com/docs/copy-applicant`)
- [ ] **Legal, Security**: [`Sumsub ID User Terms and Conditions`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Sumsub_ID_User_Terms_and_Conditions.txt) (`https://id.sumsub.com/terms`)
- [x] **Legal**: [`Privacy Notice`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Privacy_Notice.txt) (`https://sumsub.com/privacy-notice/`)
- [x] **Legal, Security**: [`Privacy Notice for Service`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt) (`https://sumsub.com/privacy-notice-service`)
- [ ] **Legal**: [`EU Standard Contractual Clauses`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-EU_Standard_Contractual_Clauses.txt) (`https://eur-lex.europa.eu`)
- [ ] **Legal, Security**: [`DIFC Standard Contractual Clauses`](https://github.com/RightbrainAI/office_box/blob/main/_vendor_analysis_source/issue-5-DIFC_Standard_Contractual_Clauses.txt) (`https://www.difc.ae/business/operating/data-protection/data-export-and-sharing/`)
### Offline / Unlinked References
*(Please upload these manually)*

- [ ] **Awaiting Document (Relevant)**: `Annex 1 – Service Level Agreement (SLA)`
  > *Mentioned in: "Annex 1 – Service Level Agreement"*
- [ ] **Awaiting Document (Relevant)**: `Annex 2 – Payment Terms`
  > *Mentioned in: "Annex 2 – Payment Terms"*
- [ ] **Awaiting Document (Relevant)**: `Annex 3 – Data Processing Agreement (DPA)`
  > *Mentioned in: "Annex 3 (Data Processing Agreement)"*
- [ ] **Awaiting Document (Relevant)**: `Annex A – Data Processing Instruction`
  > *Mentioned in: "Annex A: Data Processing Instruction"*
- [ ] **Awaiting Document (Relevant)**: `Annex B – Consent and Privacy Notice Wording`
  > *Mentioned in: "Annex B: Consent and Privacy Notice Wording"*
- [ ] **Awaiting Document (Check_Manually)**: `Annex C – International Data Transfer Safeguards`
  > *Mentioned in: "Annex С: International Data Transfer Safeguards"*

---

## Issue Discussion & Analysis

### Comment from @github-actions[bot] (at 2025-11-25T12:30:24Z)

## 🚀 AI-Generated Risk Summary
### **Overall Assessment: Medium**
**Executive Summary:** Sumsub presents a MEDIUM overall risk for our limited KYC identity verification use case, despite several HIGH-risk contractual gaps. The vendor demonstrates strong security certifications (ISO 27001/27018, SOC 2 Type 2) and EU data residency, which are critical for biometric/ID processing. However, the liability cap of USD 5,000 is dangerously inadequate for potential GDPR fines from biometric data breaches, and the lack of reciprocal indemnification leaves SecureCloud exposed. Given our narrow use case (KYC verification only, not core business operations), these risks are manageable with contractual amendments. Recommendation: APPROVE contingent on negotiating increased liability cap to £500K minimum and adding reciprocal data breach indemnity clause.

### ✅ Positive Findings
* **Comprehensive Security Certifications:** ISO 27001/27017/27018, SOC 2 Type 2, and PCI DSS certifications demonstrate mature security governance appropriate for biometric data processing
* **EU Data Residency:** Primary data storage in German Tier-3 data centers with encryption at rest provides strong GDPR compliance foundation for our EU customers
* **Robust Business Continuity:** ISO 22301 certification and 99.5% SLA provide adequate availability assurance for non-critical KYC verification services

### ⚖️ Key Legal Risks
* **Risk:** Liability Cap
  * **Summary:** USD 5,000 cap applies to ALL claims including data breaches involving biometric data. A single GDPR breach could result in fines up to 4% of annual revenue, leaving SecureCloud with catastrophic exposure.
  * **Recommendation:** Negotiate minimum £500K liability cap with unlimited liability for data protection breaches involving biometric/government ID data
* **Risk:** One-sided Indemnification
  * **Summary:** Customer must indemnify Sumsub for controller breaches, but no reciprocal protection exists for processor security failures or data breaches.
  * **Recommendation:** Require reciprocal indemnification clause for processor breaches, particularly for security incidents involving KYC data
* **Risk:** AI Training Rights
  * **Summary:** Sumsub may use customer biometric/ID data for AI model training if permitted by client consent, creating potential privacy risks and regulatory exposure.
  * **Recommendation:** Add explicit contractual prohibition on using our KYC data for AI training or any secondary purposes

### 🛡️ Key Security Gaps
* **Gap:** Missing IAM Controls Documentation
  * **Summary:** No evidence of MFA for production access, periodic access reviews, or least privilege controls - critical gaps for a service handling biometric data.
  * **Recommendation:** Require contractual attestation of MFA enforcement and quarterly access reviews for all personnel handling our KYC data
* **Gap:** Breach Notification Timeline
  * **Summary:** While notification is 'immediate', no specific timeline (e.g., 72 hours) is contractually guaranteed for GDPR/HIPAA compliance.
  * **Recommendation:** Amend contract to specify 24-hour notification for confirmed breaches, 72-hour maximum for suspected incidents
* **Gap:** Incomplete Application Security
  * **Summary:** No documented secure SDLC, code reviews, or vulnerability scanning processes despite handling sensitive biometric data.
  * **Recommendation:** Request SOC 2 Type 2 report for validation and require annual penetration test results sharing

---

## 📝 Reviewer-Approved Data (Draft)
Please review, edit, and confirm the details below. This JSON block will be committed to the central vendor registry upon issue closure.

**ACTION REQUIRED:** Before closing this issue, please **edit the `mitigations` field** (and any others) in the JSON block below to reflect the final, agreed-upon controls.
```json
{
  "mitigations": "Negotiate \u00a3500K minimum liability cap with data breach carve-out; Require reciprocal indemnification; Prohibit AI training use; Mandate MFA attestation and 24-hour breach notification",
  "risk_rating": "Medium",
  "usage_summary": "To verify customer identity as part of our KYC flow",
  "processor_name": "Sumsub",
  "key_legal_finding": "USD 5,000 liability cap with no data breach carve-out creates unacceptable GDPR fine exposure for biometric data incidents",
  "relationship_owner": "Not specified",
  "termination_notice": "30 days written notice for convenience; immediate for cause",
  "service_description": "Identity verification service for KYC compliance",
  "key_security_finding": "Strong certifications (ISO 27001, SOC 2) offset by undocumented IAM controls for production access to biometric data",
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
      "quote": "ISO/IEC 27001 Information Security Management System",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "ISO/IEC 27001"
    },
    {
      "quote": "ISO 22301:2019 Business continuity management system compliance",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "ISO 22301:2019"
    },
    {
      "quote": "ISO/IEC 27017 Independent security assessment",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "ISO/IEC 27017"
    },
    {
      "quote": "ISO/IEC 27018 Protection of personal data in the cloud",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "ISO/IEC 27018"
    },
    {
      "quote": "ISO 9001:2015 Quality management system compliance",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "ISO 9001:2015"
    },
    {
      "quote": "SOC 2 Type 2 Independent security assessment",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "SOC 2 Type 2"
    },
    {
      "quote": "PCI DSS Secure payment card data processing",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt",
      "certification_name": "PCI DSS"
    }
  ],
  "incident_response": {
    "customer_notification_timeline": {
      "quote": "Where a Personal data breach occurs...it is reported immediately to the Data Protection Officer...and, where applicable, to the data protection authority, the respective Client and, if applicable, to the individual affected by the breach.",
      "answer": "Not specified",
      "summary": "No fixed timeline is given; contractually we should require \u226472 h for GDPR and HIPAA breach notifications.",
      "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt"
    }
  },
  "data_security_and_privacy": {
    "data_loss_prevention": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "data_encryption_at_rest": {
      "quote": "all Personal data is encrypted",
      "answer": true,
      "summary": "Encryption of data at rest is explicitly confirmed; sufficient for the PII/biometric data we will transmit for KYC.",
      "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt"
    },
    "data_classification_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "data_encryption_in_transit": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "customer_data_access_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    }
  },
  "governance_risk_and_compliance": {
    "risk_management_process": {
      "quote": "ISO 31000:2018 Risk management framework compliance",
      "answer": true,
      "summary": "ISO 31000 adoption shows formal enterprise risk management; acceptable for our moderate-risk KYC processing.",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt"
    },
    "information_security_program": {
      "quote": "ISO/IEC 27001 Information Security Management System",
      "answer": true,
      "summary": "Certified ISMS demonstrates a systematic approach to InfoSec governance; aligns with our ISO 27001 requirement.",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt"
    },
    "third_party_vendor_management": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    }
  },
  "identity_and_access_management": {
    "password_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "periodic_access_reviews": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "mfa_for_production_access": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "least_privilege_access_control": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    }
  },
  "personnel_and_physical_security": {
    "employee_background_checks": {
      "quote": "personnel involved in Personal data processing...undergoes background checks, where it is obligatory",
      "answer": true,
      "summary": "Background checks are performed where legally required; acceptable but we should mandate contractual requirement for all personnel handling our KYC data.",
      "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt"
    },
    "security_awareness_training": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "physical_data_center_security": {
      "quote": "all personal data is stored and processed on specially designated servers in Germany...security level no lower than Tier 3",
      "answer": true,
      "summary": "Tier-3 EU data centres provide adequate physical assurance for the biometric/ID data we will process.",
      "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt"
    }
  },
  "application_and_software_security": {
    "secure_sdlc_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "security_code_reviews": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "static_dynamic_code_analysis": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "open_source_vulnerability_management": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    }
  },
  "threat_and_vulnerability_management": {
    "bug_bounty_program": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "vulnerability_scanning": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "patch_management_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "third_party_penetration_testing": {
      "quote": "We conduct regular penetration testing",
      "answer": true,
      "summary": "Regular third-party penetration tests are performed; good practice for a service handling biometric ID data.",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt"
    }
  },
  "business_continuity_and_disaster_recovery": {
    "bcdr_plan_exists": {
      "quote": "ISO 22301:2019 Business continuity management system compliance",
      "answer": true,
      "summary": "ISO 22301 certification provides assurance that Sumsub has a formally-managed business-continuity program; this is acceptable for our KYC-only use case.",
      "source_url": "_vendor_analysis_source/issue-5-Main_Security_Page.txt"
    },
    "data_backup_policy": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    },
    "recovery_plan_testing": {
      "quote": "",
      "answer": false,
      "summary": "",
      "source_url": ""
    }
  }
}
```

### ⚖️ Legal & DPA Analysis (Raw)
```json
{
  "audit_rights": {
    "quote": "Sumsub shall, in accordance with Data Protection Legislation, make available to the Customer any information as is reasonably necessary to demonstrate Sumsub's compliance with its obligations as a data processor under the Data Protection Legislation and allow for and contribute to audits, including inspections, by the Customer...",
    "summary": "High-risk: UK GDPR processor audit right is contractually recognised but only on 30-day notice, during business hours, at your cost, and with confidentiality obligations.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "audit_procedure": "30-day prior notice; remote electronic access to records & personnel; inspection of infrastructure; customer pays Sumsub's reasonable costs",
    "has_audit_rights": true,
    "conditions_and_limitations": "30-day notice; business-hours only; customer bears cost; confidentiality; excludes disruption to Sumsub/sub-processors/other customers"
  },
  "data_deletion": {
    "quote": "Sumsub will cease any processing and delete and/or return if directed in writing by the Customer, all or any Personal Data related to this Agreement... within 30 days after it completes the destruction.",
    "comment": "Deletion obligation is processor-standard; 30-day window acceptable if enforced. Ensure written instruction is served at termination.",
    "summary": "High-risk: Deletion on your written instruction within 30 days; biometric data destruction must be non-recoverable.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "timeline_days": 30.0
  },
  "governing_law": {
    "quote": "This Agreement and all disputes... are governed by English law... finally resolved by arbitration administered by the International Court of Arbitration... seat... London",
    "answer": "English law, ICC arbitration London",
    "comment": "Arbitration clause may delay urgent data-protection remedies; consider requesting carve-out for regulator/data-subject injunctive relief.",
    "summary": "English law & ICC arbitration London (single arbitrator, expedited); no carve-out for data-protection injunctive relief.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt"
  },
  "service_levels": {
    "quote": "Service Availability shall be at least ninety-nine and five tenths percent (99.5%) in each calendar month... Exclusions: Force Majeure, Scheduled Maintenance, Emergency Maintenance.",
    "summary": "99.5% monthly uptime SLA; 5h scheduled maintenance window; no credits specified for breach.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "remedy_credits": "Not specified (SLA silent on service credits)",
    "uptime_commitment": "99.5% per calendar month"
  },
  "confidentiality": {
    "quote": "The Customer shall: (i) maintain all Confidential Information in strict and absolute secrecy... (ii) take all necessary precautions to keep Confidential Information secure...",
    "summary": "Standard two-way confidentiality; survives indefinitely; no specific carve-out for mandatory data-subject or regulator disclosure.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "survival_period": "Indefinitely"
  },
  "indemnification": {
    "quote": "The Customer shall defend, indemnify, and hold... Sumsub... harmless from and against any and all claims... arising out of or incurred in connection with the Customer\u2019s breach... of clause 3.2 hereof [Customer Controller obligations].",
    "comment": "Negotiate reciprocal indemnity for processor data-breach or security failures; current clause leaves you exposed to third-party claims.",
    "summary": "High-risk: One-sided customer indemnity for Controller breaches (consent, notices, legal basis); no reciprocal indemnity for processor breaches.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "covers_customer": false,
    "covers_data_breach": false,
    "covers_ip_infringement": false
  },
  "termination_rights": {
    "quote": "Either Party may terminate these Terms and Conditions at any time for convenience by giving the other Party written notice at least 30 days prior...",
    "summary": "30-day convenience termination; immediate termination for material breach, insolvency, sanctions, security incidents, or daily volume >1000 checks.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "for_cause_conditions": "Material breach, violation of law, insolvency, sanctions, IP infringement, unauthorised access, reputational harm, daily volume >1000 checks",
    "for_convenience_timeline": "30 days written notice"
  },
  "breach_notification": {
    "quote": "Sumsub will immediately and without undue delay notify the Customer if it becomes aware of: any accidental, unauthorised or unlawful processing of the Personal Data; or any Personal Data Breach.",
    "summary": "High-risk: Processor must notify 'immediately' and provide details, but Customer alone decides whether to notify data subjects/supervisors.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "notification_timeline": "Immediately and without undue delay",
    "notification_procedure": "Written notice with nature, categories/numbers affected, likely consequences, measures taken/proposed; Sumsub may not inform third parties without Customer's prior consent (except legal requirement)"
  },
  "subprocessor_flow_down": {
    "quote": "Sumsub may authorise a subprocessor to process the Personal Data... Sumsub enters into a written contract with the subprocessor that contains terms substantially the same as those set out in this Agreement...",
    "summary": "General authorisation granted; list in Dashboard; right to object on legitimate grounds; Sumsub full liability for sub-processor failure.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "objection_rights": true,
    "subprocessor_list_url": "Dashboard notifications (updated periodically)",
    "right_to_use_subprocessors": true,
    "notification_for_new_subprocessors": "Via Dashboard updates; no prior notice required (general authorisation)"
  },
  "data_usage_for_training": {
    "quote": "Where it\u2019s not prohibited by applicable laws and provided we have permission from our Clients, we may process some Personal data to develop and improve existing Services to prevent and detect fraud... by means of artificial intelligence.",
    "answer": true,
    "comment": "Ensure contract prohibits or restricts this for KYC data; otherwise you must obtain explicit consent or rely on public-interest basis.",
    "summary": "High-risk: Sumsub may re-use biometric/ID data for AI model training under its own Controller capacity if Client consents and law permits.",
    "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt"
  },
  "limitation_of_liability": {
    "quote": "THE SERVICE PROVIDER\u2019S TOTAL AGGREGATE LIABILITY... SHALL IN ALL CIRCUMSTANCES BE LIMITED TO: (i) 100% OF THE TOTAL FEES PAID... DURING THE 3-MONTH PERIOD... OR (ii) 5,000 USD, WHICHEVER IS LESS.",
    "comment": "Cap is extremely low for biometric/ID data breach; negotiate higher cap or unlimited liability for data-protection breaches.",
    "summary": "High-risk: Hard cap at 3-month fees or USD 5k (whichever lower) for ALL claims; NO carve-out for data-breach damages or GDPR fines.",
    "cap_amount": "100% of fees paid in prior 3 months or USD 5,000, whichever is lower",
    "carve_outs": "Fraud, fraudulent misrepresentation, sums properly due, indemnities, unlawful exclusions",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "data_breach_liability_cap": "USD 5,000 / 3-month fees (no special carve-out)"
  },
  "data_processing_addendum": {
    "quote": "This Personal Data Processing Agreement... applies as set out therein. This Agreement sets out the additional terms... on which the Service Provider... will process Personal Data...",
    "summary": "Comprehensive UK/EU DPA with SCCs/IDTA incorporated; Sumsub acts as Processor; biometric & ID data explicitly listed.",
    "source_url": "_vendor_analysis_source/issue-5-Main_T&Cs.txt",
    "is_dpa_referenced": true,
    "data_transfer_mechanisms": "UK IDTA Addendum, EU SCCs (Modules 1-3), DIFC/ADGM SCCs, UAE DP Law safeguards; transfers to US under UK adequacy or SCCs; sub-processor general authorisation with right to object"
  },
  "data_residency_and_transfers": {
    "quote": "Sumsub confirms that all Personal data is stored on Sumsub\u2019s servers located in the EU and/or subject to any national localisation requirements...",
    "summary": "High-risk: Primary storage EU (Germany); optional localisation; international transfers use SCCs/adequacy; no specific UK-only hosting.",
    "source_url": "_vendor_analysis_source/issue-5-Privacy_Notice_for_Service.txt",
    "transfer_mechanisms_uk_eu": "EU SCCs, UK IDTA Addendum, UK adequacy for EEA, EU adequacy for UK, Swiss adequacy, US under UK/EU adequacy or SCCs",
    "storage_and_processing_locations": "Germany (default); optional local regions (e.g., Bahrain); transfers to US, UAE, Singapore, Brazil under SCCs/adequacy"
  }
}
```

---

