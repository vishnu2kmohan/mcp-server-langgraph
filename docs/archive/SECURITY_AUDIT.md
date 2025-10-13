# Security Audit Checklist

Comprehensive security audit checklist for production deployment of MCP Server with LangGraph.

## Quick Security Scan

Run automated security checks:

```bash
# Full security audit
make security-check

# Or run individual checks
bandit -r . -x ./tests,./venv -ll
safety check --json
pip-audit
```

---

## Pre-Production Security Checklist

### 🔐 Authentication & Authorization

- [ ] **JWT Secret Strength**
  - [ ] Minimum 256 bits (32 bytes) entropy
  - [ ] Generated with cryptographically secure random generator
  - [ ] Not using default or example values
  - [ ] Stored in secrets manager (Infisical/Vault)
  - [ ] Rotation policy defined (90 days recommended)

- [ ] **JWT Configuration**
  - [ ] Token expiration set appropriately (≤ 1 hour for production)
  - [ ] Algorithm set to HS256 or RS256 (not none)
  - [ ] Token validation on every request
  - [ ] Token revocation mechanism implemented

- [ ] **OpenFGA Authorization**
  - [ ] Production store created (not test/dev store)
  - [ ] Authorization model reviewed and validated
  - [ ] Least-privilege principle applied
  - [ ] Audit logging enabled
  - [ ] PostgreSQL backend configured (not in-memory)
  - [ ] Store and Model IDs stored securely

### 🔑 Secrets Management

- [ ] **No Hardcoded Secrets**
  - [ ] No API keys in code
  - [ ] No passwords in configuration files
  - [ ] No secrets in environment files committed to git
  - [ ] `.env` file in `.gitignore`
  - [ ] Pre-commit hooks prevent secret commits

- [ ] **Secrets Manager Configuration**
  - [ ] Infisical or equivalent configured
  - [ ] Machine identities with least privilege
  - [ ] Secrets rotation enabled
  - [ ] Access logs monitored
  - [ ] Fallback mechanism tested

- [ ] **API Keys Security**
  - [ ] All LLM provider keys stored in secrets manager
  - [ ] Keys scoped to minimum required permissions
  - [ ] Usage monitoring and alerting configured
  - [ ] Key rotation schedule defined

### 🛡️ Container Security

- [ ] **Docker Image Hardening**
  - [ ] Multi-stage build implemented
  - [ ] Non-root user (UID 1000)
  - [ ] Minimal base image (python:3.12-slim)
  - [ ] No unnecessary packages installed
  - [ ] Layer caching optimized
  - [ ] Image vulnerability scanning enabled

- [ ] **Container Runtime Security**
  - [ ] Read-only root filesystem where possible
  - [ ] Capabilities dropped (no CAP_SYS_ADMIN)
  - [ ] Seccomp profile applied
  - [ ] AppArmor/SELinux enabled
  - [ ] Resource limits defined (CPU/memory)

### ☸️ Kubernetes Security

- [ ] **Pod Security**
  - [ ] Pod Security Standards enforced (restricted)
  - [ ] Non-root user enforced in pod spec
  - [ ] Privilege escalation disabled
  - [ ] Host network/PID/IPC disabled
  - [ ] Read-only root filesystem

- [ ] **Network Security**
  - [ ] Network policies defined and applied
  - [ ] Ingress/egress rules restricted
  - [ ] Service mesh implemented (optional but recommended)
  - [ ] mTLS between services
  - [ ] TLS for ingress (Let's Encrypt or equivalent)

- [ ] **RBAC Configuration**
  - [ ] Service accounts with minimal permissions
  - [ ] Role bindings audited
  - [ ] No cluster-admin usage in production
  - [ ] Namespace isolation enforced

- [ ] **Secrets in Kubernetes**
  - [ ] Secrets encrypted at rest
  - [ ] External secrets operator used (CSI driver)
  - [ ] No secrets in ConfigMaps
  - [ ] Secret rotation automated

### 🌐 API & Network Security

- [ ] **Rate Limiting**
  - [ ] Kong or equivalent API gateway configured
  - [ ] Tiered rate limits per user/organization
  - [ ] DDoS protection enabled
  - [ ] Request size limits enforced

- [ ] **Input Validation**
  - [ ] All user inputs validated
  - [ ] Pydantic models for type safety
  - [ ] SQL injection prevention (not applicable - no SQL in app)
  - [ ] XSS prevention in responses
  - [ ] JSON schema validation

- [ ] **TLS/SSL**
  - [ ] TLS 1.2+ only (disable TLS 1.0/1.1)
  - [ ] Strong cipher suites configured
  - [ ] Certificate from trusted CA
  - [ ] Certificate auto-renewal (cert-manager)
  - [ ] HSTS headers enabled

- [ ] **CORS Configuration**
  - [ ] Restricted origins (not `*`)
  - [ ] Credentials handling reviewed
  - [ ] Allowed methods minimized

### 📊 Logging & Monitoring

- [ ] **Audit Logging**
  - [ ] Authentication events logged
  - [ ] Authorization decisions logged
  - [ ] Failed access attempts logged
  - [ ] Admin actions logged
  - [ ] Logs include correlation IDs

- [ ] **Log Security**
  - [ ] No sensitive data in logs (PII, secrets)
  - [ ] Logs encrypted in transit
  - [ ] Log retention policy defined
  - [ ] Log tampering protection
  - [ ] Centralized log aggregation

- [ ] **Monitoring & Alerting**
  - [ ] Failed authentication alerts
  - [ ] Authorization failure alerts
  - [ ] Rate limit violation alerts
  - [ ] Error rate spike alerts
  - [ ] Resource exhaustion alerts

### 🔍 Dependency Security

- [ ] **Dependency Management**
  - [ ] All dependencies pinned to specific versions
  - [ ] `requirements-pinned.txt` used in production
  - [ ] Regular dependency updates scheduled
  - [ ] Automated vulnerability scanning (Dependabot/Renovate)
  - [ ] Security advisories monitored

- [ ] **Vulnerability Scanning**
  - [ ] `pip-audit` run regularly
  - [ ] `safety check` in CI/CD
  - [ ] Snyk or equivalent integrated
  - [ ] No critical/high vulnerabilities in production

### 🗄️ Data Security

- [ ] **Data at Rest**
  - [ ] OpenFGA PostgreSQL encrypted
  - [ ] Backup encryption enabled
  - [ ] Encryption keys rotated regularly

- [ ] **Data in Transit**
  - [ ] All inter-service communication encrypted
  - [ ] LLM API calls over HTTPS
  - [ ] Database connections encrypted (SSL/TLS)
  - [ ] OpenTelemetry exporter uses TLS

- [ ] **Data Privacy**
  - [ ] PII handling reviewed
  - [ ] Data retention policy defined
  - [ ] GDPR compliance (if applicable)
  - [ ] Data deletion procedures implemented

### 🚨 Incident Response

- [ ] **Incident Response Plan**
  - [ ] Security incident runbook created
  - [ ] On-call rotation defined
  - [ ] Escalation procedures documented
  - [ ] Post-mortem process defined

- [ ] **Backup & Recovery**
  - [ ] OpenFGA database backups automated
  - [ ] Secrets backup procedure defined
  - [ ] Disaster recovery plan tested
  - [ ] RTO/RPO defined and achievable

- [ ] **Secret Rotation**
  - [ ] JWT secret rotation procedure
  - [ ] API key rotation procedure
  - [ ] Certificate rotation automated
  - [ ] Emergency rotation process defined

### 🔬 Code Security

- [ ] **Static Analysis**
  - [ ] Bandit security linting passing
  - [ ] No hardcoded secrets detected
  - [ ] No weak cryptography usage
  - [ ] No insecure random number generation

- [ ] **Code Review**
  - [ ] Security-focused code review completed
  - [ ] Authentication/authorization logic reviewed
  - [ ] Secret handling reviewed
  - [ ] Third-party integrations reviewed

### 🏗️ Infrastructure Security

- [ ] **Kubernetes Cluster Hardening**
  - [ ] API server access restricted
  - [ ] etcd encryption enabled
  - [ ] Kubelet security configured
  - [ ] Admission controllers enabled
  - [ ] Regular security updates applied

- [ ] **Cloud Provider Security**
  - [ ] IAM roles with least privilege
  - [ ] Service accounts with minimal permissions
  - [ ] Cloud audit logging enabled
  - [ ] Security groups/firewall rules restrictive
  - [ ] Multi-factor authentication enforced

### ✅ Compliance

- [ ] **Regulatory Compliance** (if applicable)
  - [ ] GDPR compliance verified
  - [ ] SOC 2 requirements met
  - [ ] HIPAA compliance (if handling health data)
  - [ ] Industry-specific regulations reviewed

- [ ] **Internal Policies**
  - [ ] Security policy compliance verified
  - [ ] Change management process followed
  - [ ] Deployment approval obtained

---

## Security Testing

### Automated Testing

```bash
# Run full security test suite
make security-check

# Static analysis
bandit -r . -x ./tests,./venv -ll -f json -o bandit-report.json

# Dependency vulnerabilities
safety check --json --output safety-report.json
pip-audit --format json --output pip-audit-report.json

# Container scanning
trivy image ghcr.io/vishnu2kmohan/langgraph-agent:1.0.0

# Kubernetes manifest scanning
kubesec scan kubernetes/base/*.yaml
```

### Manual Security Testing

```bash
# Test authentication
python scripts/security_tests/test_src/mcp_server_langgraph/auth/middleware.py

# Test authorization
python scripts/security_tests/test_authz.py

# Test rate limiting
python scripts/security_tests/test_rate_limits.py

# Test input validation
python scripts/security_tests/test_input_validation.py
```

### Penetration Testing

- [ ] OWASP Top 10 testing completed
- [ ] API security testing performed
- [ ] Authentication bypass attempts
- [ ] Authorization bypass attempts
- [ ] Injection attack testing
- [ ] Rate limiting effectiveness tested

---

## Security Monitoring

### Key Metrics to Monitor

1. **Authentication Failures**: `auth.failures` counter
2. **Authorization Failures**: `authz.failures` counter
3. **Rate Limit Violations**: Kong metrics
4. **Error Rates**: `agent.calls.failed` counter
5. **Latency Anomalies**: `agent.response.duration` histogram
6. **Pod Restarts**: Kubernetes metrics
7. **Resource Exhaustion**: CPU/memory usage

### Recommended Alerts

```yaml
# High authentication failure rate
- alert: HighAuthFailureRate
  expr: rate(auth_failures_total[5m]) > 0.1
  severity: warning

# Authorization failures
- alert: AuthorizationFailures
  expr: rate(authz_failures_total[5m]) > 0.05
  severity: warning

# Rate limit violations
- alert: RateLimitViolations
  expr: rate(kong_http_status{code="429"}[5m]) > 10
  severity: info

# Suspicious error patterns
- alert: SuspiciousErrorSpike
  expr: rate(agent_calls_failed_total[5m]) > 0.2
  severity: critical
```

---

## Post-Deployment Security Verification

Run this script after deployment:

```bash
python scripts/verify_security.py --environment production

# Expected output:
# ✓ JWT secret is strong (256 bits)
# ✓ No default secrets detected
# ✓ TLS configured correctly
# ✓ Rate limiting active
# ✓ RBAC configured properly
# ✓ Network policies applied
# ✓ Secrets encrypted at rest
# ✓ Audit logging enabled
```

---

## Security Contacts

**Report security vulnerabilities to:**
- Email: security@yourdomain.com
- Bug bounty program: https://yourdomain.com/security
- Responsible disclosure policy: [SECURITY.md](SECURITY.md)

**Security Team:**
- Security Lead: security-lead@yourdomain.com
- On-call: Use PagerDuty/incident management system

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Cloud Security Alliance](https://cloudsecurityalliance.org/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)

---

**Last Updated**: 2025-10-10
**Next Review**: Quarterly (2026-01-10)
