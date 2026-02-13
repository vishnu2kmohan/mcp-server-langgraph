# Security Scan Profiles Reference

---

## Security Categories (OWASP Top 10)

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

## Severity Levels

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

## Options

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

## Security Metrics

Track security posture over time:

```bash
# Store scan results with timestamp
mkdir -p .security-scans/
bandit -r src/ -f json -o .security-scans/scan_$(date +%Y%m%d).json

# Track trends
echo "$(date +%Y-%m-%d),$(jq '[.results[]] | length' .security-scans/scan_*.json | tail -1)" \
  >> .security-scans/trend.csv
```
