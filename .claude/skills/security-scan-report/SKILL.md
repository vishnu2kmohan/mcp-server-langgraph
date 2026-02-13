---
name: security-scan-report
description: Run security scans and generate security reports. Use when checking code for vulnerabilities, dependency issues, or secrets exposure.
allowed-tools:
  - Bash(uv:*)
  - Bash(npm:*)
  - Read
  - Glob
  - Grep
argument-hint: "[--detailed | --quick]"
context: fork
---
# Security Scan Report

**Usage**: `/security-scan-report` or `/security-scan-report --detailed`

**Purpose**: Run security scans and generate comprehensive security report

---

## What This Command Does

Executes multiple security scanning tools and consolidates results:

1. **Bandit** - Python security linter
2. **Safety** - Dependency vulnerability checker (if configured)
3. **Secrets detection** - Check for exposed credentials
4. **Dependency audit** - Check for known CVEs

---

## Execution Steps

### Step 1: Run Security Scans

Execute security scanning via Makefile:

```bash
# Run all security checks
make security-check

# Individual scans
bandit -r src/ -f json -o ${TMPDIR:-/tmp}/bandit_report.json
bandit -r src/ -ll  # Low/Medium/High severity

# Check dependencies (if safety installed)
safety check --json || echo "Safety not configured"

# Check for secrets in code
git secrets --scan || echo "Git secrets not configured"
```

Read [references/scan-profiles.md](references/scan-profiles.md) for scan options (Quick/Detailed/Specific checks).

### Step 2: Parse Results

Analyze findings from each scanner:

```bash
# Parse Bandit JSON output
if [ -f ${TMPDIR:-/tmp}/bandit_report.json ]; then
    jq '.results[] | {severity, confidence, test_id, issue_text, filename, line_number}' \
       ${TMPDIR:-/tmp}/bandit_report.json
fi

# Count by severity
CRITICAL=$(jq '[.results[] | select(.severity=="CRITICAL")] | length' ${TMPDIR:-/tmp}/bandit_report.json)
HIGH=$(jq '[.results[] | select(.severity=="HIGH")] | length' ${TMPDIR:-/tmp}/bandit_report.json)
MEDIUM=$(jq '[.results[] | select(.severity=="MEDIUM")] | length' ${TMPDIR:-/tmp}/bandit_report.json)
LOW=$(jq '[.results[] | select(.severity=="LOW")] | length' ${TMPDIR:-/tmp}/bandit_report.json)
```

### Step 3: Categorize Issues

Group findings by category:

**Code Security**:
- SQL injection risks
- XSS vulnerabilities
- Command injection
- Path traversal
- Insecure crypto

**Dependency Security**:
- Known CVEs
- Outdated packages
- Vulnerable versions

**Configuration Security**:
- Hardcoded secrets
- Weak crypto algorithms
- Insecure defaults

Read [references/scan-profiles.md](references/scan-profiles.md) for full OWASP security categories and severity level definitions.

### Step 4: Generate Report

Create comprehensive security report with these sections:

1. **Header** - Timestamp, scan tools used
2. **Critical Findings** - Table with Severity, Location, Issue, CWE
3. **High Priority Findings** - Detailed list
4. **Summary** - Total/Critical/High/Medium/Low counts with action guidance
5. **Security Checklist** - No critical vulns, deps up to date, no secrets, tests passing, HTTPS enforced, auth secure

Read [references/owasp-mapping.md](references/owasp-mapping.md) for issue resolution (false positives, real issues), example output, and troubleshooting.

Read [references/scan-profiles.md](references/scan-profiles.md) for security metrics tracking.

---

## Related Commands

- `/validate` - Full validation including security
- `/test-summary` - Test security-related tests
- `/benchmark` - Performance of security checks

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Security Tools**: Bandit, Safety (optional), Git Secrets (optional)
