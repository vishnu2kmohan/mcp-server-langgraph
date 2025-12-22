---
name: hipaa-audit
version: 1.0.0
description: HIPAA compliance audit for healthcare data protection
category: compliance
author: Emergence AI
dependencies: []
sandbox_config:
  network: none
  filesystem: readonly
required_secrets: []
compliance_frameworks:
  - HIPAA
  - HITECH
---

# HIPAA Audit Skill

Comprehensive HIPAA compliance audit for assessing Protected Health Information (PHI) handling.

## Capabilities

- **PHI Identification**: Detect PHI in systems and code
- **Access Control Review**: Verify authorization mechanisms
- **Encryption Assessment**: Check data protection measures
- **Audit Log Review**: Assess logging and monitoring

## HIPAA Rules Covered

### Privacy Rule
- Use and disclosure of PHI
- Minimum necessary standard
- Patient rights

### Security Rule
- Administrative safeguards
- Physical safeguards
- Technical safeguards

### Breach Notification Rule
- Incident response procedures
- Notification requirements

## Audit Checklist

### Technical Safeguards
- [ ] Encryption (at rest and in transit)
- [ ] Access controls
- [ ] Audit controls
- [ ] Integrity controls
- [ ] Transmission security

### Administrative Safeguards
- [ ] Security officer designated
- [ ] Risk analysis conducted
- [ ] Workforce training
- [ ] Contingency plan

## Output Format

```markdown
# HIPAA Compliance Audit Report

## Compliance Score: X/100

## PHI Inventory
[Identified PHI locations]

## Safeguard Assessment
| Safeguard | Status | Gap |
|-----------|--------|-----|

## Remediation Plan
[Prioritized action items]
```
