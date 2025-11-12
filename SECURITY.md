# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.8.x   | :white_check_mark: |
| 2.7.x   | :white_check_mark: |
| 2.6.x   | :white_check_mark: |
| < 2.6   | :x:                |

## Reporting a Vulnerability

We take the security of our project seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories** (Preferred)
   - Navigate to the [Security tab](https://github.com/vishnu2kmohan/mcp-server-langgraph/security)
   - Click "Report a vulnerability"
   - Fill out the advisory form with details

2. **Email**
   - Send an email to: `security@vishnu2kmohan.dev`
   - Include "SECURITY" in the subject line
   - Provide a detailed description of the vulnerability

### What to Include

Please include the following information in your report:

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
- **Location** (file path, line number, component)
- **Step-by-step instructions** to reproduce the issue
- **Proof of concept** or exploit code (if applicable)
- **Impact** of the vulnerability
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up questions

### What to Expect

When you report a vulnerability, you can expect:

1. **Acknowledgment**: We will acknowledge receipt within 48 hours
2. **Initial Assessment**: We will provide an initial assessment within 7 days
3. **Regular Updates**: We will keep you informed about our progress
4. **Coordinated Disclosure**: We will work with you on a disclosure timeline
5. **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

### Our Commitment

- We will respond promptly to security reports
- We will keep you informed throughout the investigation and remediation process
- We will notify users about security issues in a timely manner
- We will credit researchers who report valid security issues (unless anonymity is requested)

## Security Measures

This project implements several security best practices:

### Authentication & Authorization

- **JWT Authentication**: Token-based authentication with RS256 signing
- **OpenFGA Authorization**: Fine-grained, relationship-based access control
- **Keycloak Integration**: Enterprise SSO with OIDC/OAuth2
- **Session Management**: Secure session storage with Redis backend
- **Role Mapping**: Declarative role mappings with conditional logic

### Secrets Management

- **Infisical Integration**: Secure secret storage and retrieval
- **Environment Variables**: Support for `.env` files (never committed)
- **Sealed Secrets**: Kubernetes sealed secrets support
- **External Secrets Operator**: Cloud provider secret integration

### Data Protection

- **GDPR Compliance**: Data subject rights (access, rectification, erasure, portability)
- **HIPAA Safeguards**: PHI audit logging, data integrity controls, emergency access
- **SOC 2 Controls**: Automated evidence collection, access reviews
- **Data Retention**: Configurable policies with automated cleanup
- **Encryption**: TLS for data in transit, encryption at rest for sensitive data

### Application Security

- **Input Validation**: Pydantic models with strict type checking
- **SQL Injection Protection**: Parameterized queries, no raw SQL
- **XSS Prevention**: Output encoding, Content Security Policy
- **CSRF Protection**: Token-based CSRF protection for web endpoints
- **Rate Limiting**: API rate limiting to prevent abuse
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options

### Dependency Security

- **Automated Scanning**: Bandit for Python security issues
- **Dependency Auditing**: pip-audit for known vulnerabilities
- **Dependabot**: Automated dependency updates
- **Secret Scanning**: GitHub secret scanning with push protection
- **SBOM Generation**: Software Bill of Materials for supply chain security

### Infrastructure Security

- **Network Policies**: Kubernetes network policies for pod isolation
- **Pod Security**: Security contexts, non-root containers
- **RBAC**: Kubernetes role-based access control
- **Service Mesh**: Compatible with Istio/Linkerd for mTLS
- **Secrets Encryption**: etcd encryption at rest

### Observability & Monitoring

- **Audit Logging**: Comprehensive audit logs for security events
- **OpenTelemetry**: Distributed tracing with security context
- **Prometheus Metrics**: Security-relevant metrics and alerts
- **Grafana Dashboards**: Real-time security monitoring
- **SLA Monitoring**: Automated tracking of security SLAs

## Security Checklist for Deployments

Before deploying to production, ensure:

- [ ] All secrets are stored in Infisical or external secrets manager
- [ ] TLS/HTTPS is enabled for all endpoints
- [ ] JWT signing keys are generated securely (RS256, 2048-bit minimum)
- [ ] OpenFGA authorization model is properly configured
- [ ] Database credentials are rotated and stored securely
- [ ] Network policies are configured for pod isolation
- [ ] RBAC is configured with least privilege
- [ ] Security scanning is enabled in CI/CD pipeline
- [ ] Audit logging is enabled and centralized
- [ ] Monitoring and alerting are configured
- [ ] Backup and disaster recovery procedures are in place
- [ ] Compliance controls are enabled (GDPR, HIPAA, SOC 2 as needed)

## Security Configurations

### Minimum Security Requirements

**Production deployments MUST:**

1. **Use HTTPS/TLS** for all endpoints
2. **Enable authentication** (JWT or Keycloak)
3. **Enable authorization** (OpenFGA)
4. **Use external secrets manager** (Infisical, AWS Secrets Manager, etc.)
5. **Enable audit logging**
6. **Configure network policies**
7. **Use non-root containers**
8. **Enable pod security standards**
9. **Implement rate limiting**
10. **Enable security scanning** in CI/CD

### Environment-Specific Settings

**Development:**
- In-memory session storage acceptable
- Reduced token expiration times
- Verbose security logging
- Relaxed rate limits

**Staging:**
- Redis session storage required
- Production-like security settings
- Security testing enabled
- Moderate rate limits

**Production:**
- Redis session storage required
- Strict security settings
- Minimal security logging (PII protection)
- Aggressive rate limits
- 24/7 monitoring and alerting

## Compliance

This project supports compliance with:

- **GDPR**: EU General Data Protection Regulation
- **HIPAA**: Health Insurance Portability and Accountability Act
- **SOC 2**: Service Organization Control 2
- **ISO 27001**: Information Security Management

See compliance documentation:
- [Compliance Overview](docs/security/compliance.mdx) - Comprehensive compliance guide (GDPR, HIPAA, SOC 2)
- [Compliance Framework](docs-internal/COMPLIANCE.md) - Internal compliance documentation
- [ADR-0012: Compliance Framework Integration](docs/architecture/adr-0012-compliance-framework-integration.mdx)

## Security Audits

| Date | Scope | Auditor | Report |
|------|-------|---------|--------|
| 2025-10-12 | Full codebase | Internal | [SECURITY_AUDIT.md](archive/SECURITY_AUDIT.md) |

## Security Updates

Security updates are released as:

- **Critical**: Immediate patch release (< 24 hours)
- **High**: Patch release within 7 days
- **Medium**: Patch release within 30 days
- **Low**: Included in next minor release

Subscribe to security advisories:
- GitHub Security Advisories: [Security tab](https://github.com/vishnu2kmohan/mcp-server-langgraph/security)
- Release notifications: Watch repository releases

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Cloud Security Alliance](https://cloudsecurityalliance.org/)

## Questions?

If you have questions about security that are not covered here:

1. Check our [documentation](docs/)
2. Review our [security guides](docs/security/)
3. Open a public discussion (for non-sensitive questions)
4. Contact us via email (for sensitive questions)

---

**Last Updated**: 2025-10-13
**Policy Version**: 1.0.0
