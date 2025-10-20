# Security Scan Report

**Usage**: `/security-scan-report` or `/security-scan-report --detailed`

**Purpose**: Run security scans and generate comprehensive security report

---

## 🔒 What This Command Does

Executes multiple security scanning tools and consolidates results:

1. **Bandit** - Python security linter
2. **Safety** - Dependency vulnerability checker (if configured)
3. **Secrets detection** - Check for exposed credentials
4. **Dependency audit** - Check for known CVEs

---

## 📊 Execution Steps

### Step 1: Run Security Scans

Execute security scanning via Makefile:

```bash
# Run all security checks
make security-check

# Individual scans
bandit -r src/ -f json -o /tmp/bandit_report.json
bandit -r src/ -ll  # Low/Medium/High severity

# Check dependencies (if safety installed)
safety check --json || echo "Safety not configured"

# Check for secrets in code
git secrets --scan || echo "Git secrets not configured"
```

### Step 2: Parse Results

Analyze findings from each scanner:

```bash
# Parse Bandit JSON output
if [ -f /tmp/bandit_report.json ]; then
    jq '.results[] | {severity, confidence, test_id, issue_text, filename, line_number}' \
       /tmp/bandit_report.json
fi

# Count by severity
CRITICAL=$(jq '[.results[] | select(.severity=="CRITICAL")] | length' /tmp/bandit_report.json)
HIGH=$(jq '[.results[] | select(.severity=="HIGH")] | length' /tmp/bandit_report.json)
MEDIUM=$(jq '[.results[] | select(.severity=="MEDIUM")] | length' /tmp/bandit_report.json)
LOW=$(jq '[.results[] | select(.severity=="LOW")] | length' /tmp/bandit_report.json)
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

### Step 4: Generate Report

Create comprehensive security report:

```markdown
# Security Scan Report

**Generated**: YYYY-MM-DD HH:MM:SS
**Scan Tools**: Bandit, Safety, Secrets Detection

---

## 🔴 Critical Findings

**Count**: X critical issues found

| Severity | Location | Issue | CWE |
|----------|----------|-------|-----|
| CRITICAL | src/auth/jwt.py:45 | Weak crypto algorithm | CWE-327 |

---

## 🟡 High Priority Findings

**Count**: Y high issues found

[Detailed list...]

---

## 🟢 Summary

- Total issues: X
- Critical: A (must fix immediately)
- High: B (fix before release)
- Medium: C (fix soon)
- Low: D (informational)

---

## ✅ Security Checklist

- [ ] No critical vulnerabilities
- [ ] All dependencies up to date
- [ ] No secrets in code
- [ ] Security tests passing
- [ ] HTTPS enforced
- [ ] Auth mechanisms secure
```

---

## 📋 Security Categories

### Injection Attacks
- SQL injection (CWE-89)
- Command injection (CWE-77)
- LDAP injection (CWE-90)
- Code injection (CWE-94)

**Status**: Typically N/A (using ORMs, parameterized queries)

### Broken Authentication
- Weak password requirements
- Session management flaws
- JWT vulnerabilities
- Missing MFA

**Status**: Protected by Keycloak integration

### Sensitive Data Exposure
- Hardcoded credentials
- Logging sensitive data
- Insecure storage
- Missing encryption

**Status**: Using Infisical for secrets

### XML External Entities (XXE)
- XML parsing vulnerabilities

**Status**: N/A (no XML processing)

### Broken Access Control
- Missing authorization
- Privilege escalation
- IDOR vulnerabilities

**Status**: Protected by OpenFGA

### Security Misconfiguration
- Default credentials
- Unnecessary features enabled
- Missing security headers

**Status**: Hardened configuration

### Cross-Site Scripting (XSS)
- Reflected XSS
- Stored XSS
- DOM XSS

**Status**: N/A (API-only, no HTML rendering)

### Insecure Deserialization
- Pickle vulnerabilities
- YAML load issues

**Status**: Using safe deserialization

### Using Components with Known Vulnerabilities
- Outdated dependencies
- Known CVEs

**Status**: Dependabot monitoring

### Insufficient Logging & Monitoring
- Missing audit logs
- No alerting
- Insufficient monitoring

**Status**: Full observability with OpenTelemetry

---

## 🎯 Severity Levels

### Critical (Immediate Fix)
- Remote code execution
- Authentication bypass
- Data breach potential
- Privilege escalation

**Action**: Stop release, fix immediately

### High (Fix Before Release)
- Serious vulnerabilities
- Requires specific conditions
- Significant impact

**Action**: Fix in current sprint

### Medium (Fix Soon)
- Limited impact
- Requires multiple conditions
- Best practice violations

**Action**: Add to backlog

### Low (Informational)
- Code quality issues
- Minor improvements
- Defensive coding suggestions

**Action**: Consider during refactoring

---

## 📊 Example Output

```
=== Security Scan Report ===

Generated: 2025-10-20 14:30:00
Scanned: src/ directory (89 Python files)

Scan Results:
┌──────────┬───────┬────────────────────────────┐
│ Severity │ Count │ Category                   │
├──────────┼───────┼────────────────────────────┤
│ CRITICAL │   0   │ ✅ None                    │
│ HIGH     │   0   │ ✅ None                    │
│ MEDIUM   │   3   │ Weak cryptographic algo    │
│ LOW      │  12   │ Code quality suggestions   │
└──────────┴───────┴────────────────────────────┘

Medium Severity Issues (3):
1. src/auth/jwt.py:45
   - Issue: Use of SHA1 (weak hash)
   - Recommendation: Upgrade to SHA256
   - CWE: CWE-327 (Broken Crypto)

2. src/secrets/encryption.py:78
   - Issue: Hardcoded salt
   - Recommendation: Use random salt per user
   - CWE: CWE-760 (Predictable Salt)

3. src/api/server.py:120
   - Issue: Debug mode enabled check
   - Recommendation: Ensure disabled in production
   - CWE: CWE-489 (Debug Mode)

Low Severity Issues (12):
[Code quality suggestions - see full report]

Dependency Scan:
- Scanned: 143 dependencies
- Vulnerabilities: 0 ✅
- Outdated (non-security): 5
- Latest security patches: All applied ✅

Secret Detection:
- Scanned: All source files
- Secrets found: 0 ✅
- False positives: 2 (test fixtures)

Overall Security Score: 98/100 ✅

Recommendations:
1. Address 3 medium severity issues
2. Update 5 outdated dependencies
3. Review false positive suppressions

Status: ✅ SAFE TO DEPLOY
(No critical or high severity issues)

Full Reports:
- Bandit: /tmp/bandit_report.json
- Summary: /tmp/security_summary.md
```

---

## 🔧 Options

### Quick Scan

Fast scan, major issues only:

```bash
bandit -r src/ -ll  # Low confidence filtered
```

### Detailed Scan

Full scan with all details:

```bash
bandit -r src/ -f json -o bandit_full.json
bandit -r src/ -v  # Verbose output
```

### Specific Checks

Run specific security tests:

```bash
# Only check for hardcoded passwords
bandit -r src/ -t B105,B106,B107

# Only check crypto issues
bandit -r src/ -t B303,B304,B305,B306,B307
```

---

## 🚨 Issue Resolution

### False Positives

Suppress known false positives:

```python
# In code
# nosec B101 - This is a test fixture, not real credentials

# In configuration (.bandit)
[bandit]
skips = B101
```

### Real Issues

Fix security vulnerabilities:

1. **Assess severity** - Is it exploitable?
2. **Research fix** - Check CVE databases, security advisories
3. **Implement fix** - Code changes or dependency updates
4. **Test fix** - Verify vulnerability is resolved
5. **Re-scan** - Confirm issue is gone

---

## 📈 Security Metrics

Track security posture over time:

```bash
# Store scan results with timestamp
mkdir -p .security-scans/
bandit -r src/ -f json -o .security-scans/scan_$(date +%Y%m%d).json

# Track trends
echo "$(date +%Y-%m-%d),$(jq '[.results[]] | length' .security-scans/scan_*.json | tail -1)" \
  >> .security-scans/trend.csv
```

---

## 🔗 Related Commands

- `/validate` - Full validation including security
- `/test-summary` - Test security-related tests
- `/benchmark` - Performance of security checks

---

## 🛠️ Troubleshooting

### Issue: Too many false positives

```bash
# Create .bandit configuration
cat > .bandit << EOF
[bandit]
exclude = /tests/,/examples/
skips = B101,B601
EOF
```

### Issue: Bandit not found

```bash
# Install security tools
pip install bandit safety
```

### Issue: Cannot parse JSON output

```bash
# Check if bandit succeeded
if [ $? -eq 0 ]; then
    jq . /tmp/bandit_report.json
else
    echo "Scan failed, check output"
fi
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Security Tools**: Bandit, Safety (optional), Git Secrets (optional)
