---
name: gdpr-audit
version: 1.0.0
description: GDPR compliance audit and data protection assessment
category: compliance
author: Emergence AI
dependencies:
  - pydantic>=2.0.0
sandbox_config:
  network: none
  filesystem: readonly
required_secrets: []
optional_secrets: []
compliance_frameworks:
  - GDPR
  - EU-AI-Act
---

# GDPR Audit Skill

Comprehensive GDPR (General Data Protection Regulation) compliance audit skill for assessing data protection practices and identifying compliance gaps.

## Capabilities

- **Data Mapping**: Identify personal data processing activities
- **Legal Basis Check**: Verify legal grounds for processing
- **Rights Assessment**: Evaluate data subject rights implementation
- **Security Review**: Assess technical and organizational measures
- **DPIA Support**: Assist with Data Protection Impact Assessments

## Usage Examples

- "Audit this system for GDPR compliance"
- "Identify personal data in this codebase"
- "Check if this data processing has valid legal basis"
- "Assess data subject rights implementation"

## GDPR Articles Covered

### Chapter II - Principles (Art. 5-11)
- Art. 5: Principles relating to processing
- Art. 6: Lawfulness of processing
- Art. 7: Conditions for consent
- Art. 9: Special categories of data

### Chapter III - Rights (Art. 12-23)
- Art. 15: Right of access
- Art. 16: Right to rectification
- Art. 17: Right to erasure
- Art. 20: Right to data portability

### Chapter IV - Controller/Processor (Art. 24-43)
- Art. 25: Data protection by design and default
- Art. 30: Records of processing activities
- Art. 32: Security of processing
- Art. 35: Data protection impact assessment

## Audit Checklist

### Data Inventory
- [ ] Personal data types identified
- [ ] Data sources documented
- [ ] Data flows mapped
- [ ] Retention periods defined
- [ ] Third-party transfers identified

### Legal Compliance
- [ ] Legal basis documented for each processing
- [ ] Consent mechanisms verified (where applicable)
- [ ] Legitimate interest assessments completed
- [ ] Privacy notices updated and accessible

### Technical Measures
- [ ] Encryption at rest and in transit
- [ ] Access controls implemented
- [ ] Audit logging enabled
- [ ] Pseudonymization/anonymization applied
- [ ] Data minimization practiced

### Organizational Measures
- [ ] DPO appointed (if required)
- [ ] Staff training conducted
- [ ] Incident response procedures
- [ ] Vendor contracts reviewed

## Output Format

```markdown
# GDPR Compliance Audit Report

## Executive Summary
- Overall Compliance Score: X/100
- Critical Gaps: X
- High Priority Items: X

## Data Processing Inventory
| Process | Data Types | Legal Basis | Risk Level |
|---------|------------|-------------|------------|
| ...     | ...        | ...         | ...        |

## Compliance Gaps

### Critical
1. [Gap Description]
   - GDPR Article: Art. X
   - Remediation: [Action required]
   - Timeline: Immediate

### High Priority
1. [Gap Description]
   - GDPR Article: Art. X
   - Remediation: [Action required]

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

## Next Steps
- [ ] Address critical gaps
- [ ] Update documentation
- [ ] Schedule follow-up audit
```

## Limitations

- This is an automated assessment tool, not legal advice
- Requires human review for final compliance determination
- Cannot assess all organizational measures
- Does not cover all GDPR articles
