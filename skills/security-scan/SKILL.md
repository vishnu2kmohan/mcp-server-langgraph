---
name: security-scan
description: Automated security vulnerability scanning and assessment. Use when scanning code for vulnerabilities, dependency issues, or security misconfigurations.
allowed-tools:
- Read
- Glob
- Grep
compatibility: Requires bandit>=1.7.0, safety>=2.0.0. No network access needed.
metadata:
  version: 1.0.0
  category: compliance
  author: Emergence AI
  dependencies:
  - bandit>=1.7.0
  - safety>=2.0.0
  sandbox_config:
    network: none
    filesystem: readonly
---
# Security Scan Skill

Automated security vulnerability scanning for codebases and dependencies.

## Capabilities

- **Static Analysis**: Scan code for vulnerabilities (SAST)
- **Dependency Audit**: Check for vulnerable dependencies
- **Secret Detection**: Find hardcoded secrets
- **OWASP Checks**: Verify OWASP Top 10 compliance

## OWASP Top 10 Coverage

1. Injection
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities (XXE)
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging & Monitoring

## Usage Examples

- "Scan this codebase for security vulnerabilities"
- "Check dependencies for known CVEs"
- "Find hardcoded secrets in this repository"

## Output Format

```markdown
# Security Scan Report

## Summary
- Critical: X
- High: X
- Medium: X
- Low: X

## Vulnerabilities

### Critical
| ID | Type | Location | Description |
|----|------|----------|-------------|

### High
| ID | Type | Location | Description |
|----|------|----------|-------------|

## Dependency Vulnerabilities
| Package | Version | CVE | Severity |
|---------|---------|-----|----------|

## Recommendations
1. [Priority action 1]
2. [Priority action 2]
```
