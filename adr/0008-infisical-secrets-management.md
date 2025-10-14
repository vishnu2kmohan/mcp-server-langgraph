# 8. Infisical for Secrets Management

Date: 2025-10-13

## Status

Accepted

## Context

Production applications require secure secret management for:
- API keys (LLM providers, OpenFGA, Keycloak)
- Database credentials
- JWT signing secrets
- Encryption keys

Environment variables alone create security risks:
- Secrets in `.env` files committed to git accidentally
- No secret rotation capability
- No audit trail of secret access
- Secrets visible in process listings
- No centralized secret management across environments

## Decision

Use **Infisical** as the primary secrets management solution with environment variable fallback.

### Why Infisical

- **Open Source**: Self-hosted option for compliance
- **Developer Friendly**: Simple SDK, good DX
- **Multi-Environment**: Dev, staging, production isolation
- **Secret Versioning**: Track secret changes over time
- **Access Control**: Fine-grained permissions
- **Audit Logging**: Who accessed what, when
- **Secret Rotation**: Programmatic secret updates
- **SDKs**: Python SDK available

## Consequences

### Positive Consequences

- **Security**: Secrets never in git, encrypted at rest
- **Rotation**: Easy programmatic secret rotation
- **Audit Trail**: Complete secret access history
- **Multi-Environment**: Separate secrets per environment
- **Compliance**: SOC 2, HIPAA audit requirements met

### Negative Consequences

- **Dependency**: External service dependency
- **Complexity**: Additional infrastructure to manage
- **Latency**: Network call to fetch secrets (mitigated by caching)

## Alternatives Considered

1. **HashiCorp Vault**: More complex, enterprise-focused
2. **AWS Secrets Manager**: Cloud vendor lock-in
3. **Environment Variables Only**: No rotation, audit, or security

**Why Rejected**: Infisical balance of features, simplicity, and open-source

## Implementation

```python
from infisical import InfisicalClient

client = InfisicalClient(token=os.getenv("INFISICAL_TOKEN"))
secrets = client.get_all_secrets(
    environment="production",
    path="/langgraph-agent"
)

# Fallback to environment variables
ANTHROPIC_API_KEY = secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
```

## References

- Dependency: `pyproject.toml:42` - `infisical-python>=2.1.7`
- Documentation: `docs/integrations/openfga-infisical.md`
- Related ADRs: [ADR-0002](0002-openfga-authorization.md), [ADR-0007](0007-authentication-provider-pattern.md)
