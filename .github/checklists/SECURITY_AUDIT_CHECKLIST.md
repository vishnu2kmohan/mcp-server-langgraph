# Security Audit Checklist

## Overview

Comprehensive security audit checklist for the MCP Server LangGraph project. Use this checklist for periodic security reviews, pre-release audits, or incident response preparation.

## Authentication & Authorization

### Authentication
- [ ] All API endpoints require authentication (except health/metrics)
- [ ] JWT tokens use RS256 signing (not HS256)
- [ ] Token expiration times are appropriate (access: 15min, refresh: 7 days)
- [ ] Refresh token rotation implemented
- [ ] Failed login attempts are rate-limited
- [ ] Account lockout after N failed attempts
- [ ] Password requirements enforced (if applicable)
- [ ] Multi-factor authentication supported (if required)

### Authorization
- [ ] OpenFGA authorization checks on all protected resources
- [ ] Principle of least privilege enforced
- [ ] RBAC roles properly defined and documented
- [ ] No hardcoded admin credentials
- [ ] Service accounts use separate credentials
- [ ] API keys have expiration dates
- [ ] API keys can be revoked
- [ ] Authorization failures logged to SIEM

## Secrets Management

- [ ] No secrets in environment variables (use Infisical or Kubernetes secrets)
- [ ] Secrets rotation policy defined and documented
- [ ] Database credentials stored in secrets manager
- [ ] API keys stored in secrets manager
- [ ] Private keys stored securely (not in repo)
- [ ] `.env` files in `.gitignore`
- [ ] Gitleaks scan passing (no leaked secrets)
- [ ] Production secrets different from staging/dev

## Input Validation

- [ ] All user inputs validated (API, UI, CLI)
- [ ] Pydantic models used for request/response validation
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Command injection prevention (no shell=True with user input)
- [ ] Path traversal prevention (validate file paths)
- [ ] File upload size limits enforced
- [ ] File upload type validation (if applicable)
- [ ] Rate limiting on all public endpoints

## Data Protection

### Encryption
- [ ] Data in transit encrypted (TLS 1.2+ only)
- [ ] Data at rest encrypted (database, storage)
- [ ] PII encrypted in database
- [ ] Encryption keys rotated periodically
- [ ] TLS certificates valid and not expired
- [ ] TLS certificates from trusted CA
- [ ] No self-signed certificates in production

### Privacy & Compliance
- [ ] GDPR compliance for EU users (if applicable)
- [ ] HIPAA compliance for health data (if applicable)
- [ ] Data retention policy defined
- [ ] PII deletion capabilities implemented (GDPR Article 17)
- [ ] Data export capabilities implemented (GDPR Article 15)
- [ ] Privacy policy published
- [ ] Terms of service published

## Infrastructure Security

### Kubernetes/Cloud
- [ ] Network policies restrict pod-to-pod communication
- [ ] RBAC configured (no cluster-admin in production)
- [ ] Pod security policies/standards enforced
- [ ] Containers run as non-root users
- [ ] Read-only root filesystem where possible
- [ ] Security contexts defined for all pods
- [ ] Resource limits set (prevent DoS)
- [ ] ImagePullPolicy: Always (prevent image tampering)
- [ ] Container image scanning enabled (Trivy/Snyk)
- [ ] No privileged containers

### Database
- [ ] Database access restricted by IP/network
- [ ] Database users have minimal privileges
- [ ] Database backups encrypted
- [ ] Database audit logging enabled
- [ ] PostgreSQL SSL connections enforced
- [ ] Redis password authentication enabled
- [ ] No default passwords used

## Dependency Security

- [ ] Dependabot/Renovate enabled for dependency updates
- [ ] `pip-audit` or `safety` scan passing
- [ ] No known critical vulnerabilities (CVE)
- [ ] Outdated dependencies identified and tracked
- [ ] Dependencies pinned in `uv.lock`
- [ ] Regular dependency updates (monthly)
- [ ] License compliance checked

## Code Security

- [ ] Bandit security scan passing
- [ ] No hardcoded credentials in code
- [ ] No sensitive data in logs
- [ ] Error messages don't leak sensitive info
- [ ] Exception handling doesn't expose stack traces to users
- [ ] CSRF protection enabled (if applicable)
- [ ] CORS configured properly (no wildcards with credentials)
- [ ] Content Security Policy headers set (if applicable)

## Logging & Monitoring

- [ ] Authentication events logged
- [ ] Authorization failures logged
- [ ] Admin actions logged
- [ ] Logs centralized (SIEM/ELK/CloudWatch)
- [ ] Logs retained for minimum period (90 days)
- [ ] No PII in logs
- [ ] Log injection prevention
- [ ] Security alerts configured (failed auth, privilege escalation, etc.)
- [ ] Incident response plan documented

## API Security

- [ ] OpenAPI schema validated
- [ ] Rate limiting per endpoint
- [ ] API versioning implemented
- [ ] Deprecated endpoints documented
- [ ] CORS headers configured properly
- [ ] HTTP security headers set (HSTS, X-Frame-Options, etc.)
- [ ] API documentation doesn't expose sensitive endpoints
- [ ] GraphQL query depth limiting (if applicable)

## CI/CD Security

- [ ] Secrets not in CI/CD logs
- [ ] CI/CD workflows use minimal permissions
- [ ] Branch protection rules enforced (main/master)
- [ ] Code review required before merge
- [ ] Security scans in CI pipeline (SAST, DAST, SCA)
- [ ] Container image scanning in CI
- [ ] Dependency scanning in CI
- [ ] No force pushes to main branch
- [ ] Signed commits (optional but recommended)

## Incident Response

- [ ] Incident response plan documented
- [ ] Security contact information published
- [ ] Vulnerability disclosure policy published
- [ ] Backup and recovery plan documented
- [ ] Disaster recovery plan tested
- [ ] Runbooks for common security incidents
- [ ] Security team contact list up-to-date

## Testing

- [ ] Security tests in test suite (34+ security tests exist)
- [ ] Penetration testing performed (annually)
- [ ] Threat modeling completed
- [ ] Security regression tests for past vulnerabilities
- [ ] Fuzz testing for critical endpoints (optional)

## Documentation

- [ ] Security architecture documented
- [ ] Threat model documented
- [ ] Security decisions documented in ADRs
- [ ] SECURITY.md in repository root
- [ ] Security training for developers completed

## Validation Commands

```bash
# Run security scans
make security-check  # Bandit
gitleaks detect      # Secret scanning
trivy image <image>  # Container scanning
pip-audit            # Dependency vulnerabilities

# Run security tests
pytest tests/security/ -v

# Check for hardcoded credentials
grep -r "password\s*=\s*['\"]" src/
grep -r "api_key\s*=\s*['\"]" src/
```

## Success Criteria

- [ ] All checklist items completed or documented as N/A
- [ ] No critical or high vulnerabilities
- [ ] Security scan reports reviewed
- [ ] Findings remediated or risk-accepted with justification
- [ ] Security audit report created
- [ ] Team briefed on findings

---

**Frequency**: Quarterly + before major releases
**Owner**: Security Team + Lead Developer
**Last Audit**: TBD
**Next Audit**: TBD
