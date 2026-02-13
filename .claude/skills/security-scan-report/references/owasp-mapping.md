# OWASP Mapping & Issue Resolution Reference

---

## Issue Resolution

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

## Example Output

```
=== Security Scan Report ===

Generated: 2025-10-20 14:30:00
Scanned: src/ directory (89 Python files)

Scan Results:
+----------+-------+----------------------------+
| Severity | Count | Category                   |
+----------+-------+----------------------------+
| CRITICAL |   0   | None                       |
| HIGH     |   0   | None                       |
| MEDIUM   |   3   | Weak cryptographic algo    |
| LOW      |  12   | Code quality suggestions   |
+----------+-------+----------------------------+

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
- Vulnerabilities: 0
- Outdated (non-security): 5
- Latest security patches: All applied

Secret Detection:
- Scanned: All source files
- Secrets found: 0
- False positives: 2 (test fixtures)

Overall Security Score: 98/100

Recommendations:
1. Address 3 medium severity issues
2. Update 5 outdated dependencies
3. Review false positive suppressions

Status: SAFE TO DEPLOY
(No critical or high severity issues)

Full Reports:
- Bandit: ${TMPDIR:-/tmp}/bandit_report.json
- Summary: ${TMPDIR:-/tmp}/security_summary.md
```

---

## Troubleshooting

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
    jq . ${TMPDIR:-/tmp}/bandit_report.json
else
    echo "Scan failed, check output"
fi
```
