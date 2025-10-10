# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

### Preferred Method: GitHub Security Advisories

1. Go to the [Security tab](https://github.com/YOUR_ORG/langgraph_mcp_agent/security/advisories)
2. Click "Report a vulnerability"
3. Fill out the form with details

### Alternative: Email

Send an email to: **security@example.com**

Include the following information:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Regular Updates**: Every 7 days until resolved
- **Public Disclosure**: After patch is released (coordinated disclosure)

## Security Measures

### Current Security Features

- **Authentication**: JWT-based authentication
- **Authorization**: OpenFGA fine-grained access control
- **Secrets Management**: Infisical integration
- **Container Security**: Non-root user, minimal base image
- **Network Policies**: Kubernetes NetworkPolicies
- **TLS/SSL**: HTTPS enforcement for all endpoints
- **Rate Limiting**: Kong API Gateway integration
- **Audit Logging**: OpenTelemetry tracing

### Automated Security Scanning

We use the following automated tools:

- **CodeQL**: Static analysis for code vulnerabilities
- **Trivy**: Container image scanning
- **Bandit**: Python security linting
- **Safety/pip-audit**: Dependency vulnerability scanning
- **TruffleHog**: Secrets scanning
- **Dependabot**: Automated dependency updates

Scans run:
- On every PR
- Daily scheduled scans
- Before releases

## Security Best Practices

### For Users

#### Secrets Management

```bash
# ✅ DO: Use Infisical or environment variables
export ANTHROPIC_API_KEY="sk-ant-..."

# ❌ DON'T: Hardcode secrets in code
api_key = "sk-ant-..."  # Never do this!
```

#### JWT Tokens

```bash
# ✅ DO: Use strong secrets (32+ characters)
JWT_SECRET_KEY=$(openssl rand -base64 32)

# ❌ DON't: Use weak or default secrets
JWT_SECRET_KEY="secret"  # Never in production!
```

#### Docker Images

```bash
# ✅ DO: Use specific version tags
docker pull ghcr.io/YOUR_ORG/langgraph-mcp-agent:v1.2.3

# ❌ DON'T: Use 'latest' in production
docker pull ghcr.io/YOUR_ORG/langgraph-mcp-agent:latest
```

#### Kubernetes Deployments

```yaml
# ✅ DO: Use NetworkPolicies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: langgraph-agent-netpol
spec:
  podSelector:
    matchLabels:
      app: langgraph-agent
  policyTypes:
  - Ingress
  - Egress
```

### For Contributors

#### Before Committing

```bash
# 1. Run security scan
make security-check

# 2. Check for secrets
git diff | grep -i "api.key\|secret\|password\|token"

# 3. Scan dependencies
safety check
pip-audit
```

#### Code Review Checklist

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (input sanitization)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization checked
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies are up to date
- [ ] Security headers configured

## Known Security Considerations

### OpenFGA Setup

OpenFGA must be properly configured with:
- PostgreSQL backend (not in-memory)
- TLS/SSL enabled
- Network isolation
- Regular backups

### Infisical Integration

When using Infisical:
- Use Universal Auth with rotation
- Enable MFA for admin access
- Use separate projects per environment
- Enable audit logging

### JWT Tokens

- Tokens expire after 1 hour by default
- Refresh tokens should be implemented for production
- Secret keys must be rotated regularly
- Use RS256 for distributed systems

### Rate Limiting

Configure Kong rate limiting:
- Basic tier: 60 requests/minute
- Premium tier: 300 requests/minute
- Enterprise tier: 1000 requests/minute

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 2**: Acknowledged by security team
3. **Day 7**: Initial assessment and severity rating
4. **Day 14-30**: Patch developed and tested
5. **Day 30-60**: Patch released to supported versions
6. **Day 60-90**: Public disclosure (if applicable)

Timelines may vary based on severity and complexity.

## Security Updates

### Notification Channels

- **GitHub Security Advisories**: Primary notification method
- **Release Notes**: Security fixes highlighted
- **Email**: For critical vulnerabilities (if subscribed)
- **Slack/Discord**: Community announcements

### How to Stay Updated

```bash
# Watch repository for security advisories
# GitHub > Watch > Custom > Security alerts

# Subscribe to releases
# GitHub > Watch > Custom > Releases

# Enable Dependabot alerts
# Settings > Security & analysis > Dependabot alerts
```

## Security Hall of Fame

We recognize and thank security researchers who help improve our security:

<!-- Security researchers will be listed here -->

## Contact

- **Security Email**: security@example.com
- **Security Team**: @YOUR_ORG/security-team
- **PGP Key**: [Link to PGP public key]

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)

---

**Last Updated**: 2025-01-10
