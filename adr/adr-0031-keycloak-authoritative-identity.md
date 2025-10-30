# 31. Keycloak as Authoritative Identity Provider

Date: 2025-01-28

## Status

Accepted

## Context

Modern enterprise applications integrate with multiple identity sources (LDAP, Active Directory, Azure AD, Google Workspace, Okta, GitHub) while maintaining consistent authentication, authorization, and user management. Operating multiple authentication systems in parallel creates significant challenges:

- **Identity Fragmentation**: Users exist in multiple systems with inconsistent attributes
- **Authorization Complexity**: Permissions scattered across identity providers
- **Operational Burden**: Managing user lifecycle across disparate systems
- **Security Gaps**: No centralized audit trail or access control
- **Integration Overhead**: Each application must integrate with N identity providers
- **Session Management**: Inconsistent token formats, lifetimes, and refresh mechanisms

Real-world requirements:
- **Enterprise SSO**: Users authenticate once across all applications
- **Federated Identity**: Support LDAP, ADFS, SAML, OIDC providers
- **Centralized Administration**: Single place to manage users, roles, permissions
- **Consistent Tokens**: JWT format across all authentication methods
- **API Access**: Programmatic user management (SCIM provisioning)
- **Long-lived Sessions**: Support for batch jobs, streaming tasks, background processes

## Decision

We will use **Keycloak as the single authoritative identity provider** for all authentication and identity management, with identity federation to existing enterprise identity sources.

### Architecture

```
External Identity Sources (LDAP/AD, ADFS, Azure AD, Google, Okta, GitHub, SAML)
                    ↓
            Keycloak (Authoritative)
    • User Storage (federated + local)
    • Identity Brokering (SAML, OIDC, LDAP)
    • JWT Token Issuance (RS256)
    • Role/Group Management
    • Session Management
    • Admin API (SCIM bridge)
                    ↓
        Application Layer
    (Kong Gateway → MCP Server → OpenFGA)
```

### Core Principles

1. **Single Source of Truth**: All identity data canonicalized in Keycloak
2. **Federation, Not Replication**: External users authenticate via federation
3. **JWT Standardization**: All auth flows produce Keycloak-issued JWTs
4. **Attribute Mapping**: External attributes mapped to Keycloak schema
5. **Centralized Administration**: All user management through Keycloak

### Configuration

```bash
AUTH_PROVIDER=keycloak
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=langgraph-agent
KEYCLOAK_CLIENT_ID=langgraph-client
KEYCLOAK_CLIENT_SECRET=<secret>
KEYCLOAK_LDAP_ENABLED=true
KEYCLOAK_SAML_PROVIDERS=adfs,azure-ad
KEYCLOAK_OIDC_PROVIDERS=google,microsoft,github,okta
```

## Consequences

### Positive Consequences
- Centralized identity, consistent authentication, enterprise SSO
- Simplified integration, centralized audit trail
- Single role/group hierarchy, consistent token lifecycle
- Future-proof, industry-standard OIDC/SAML

### Negative Consequences
- Single point of failure, operational complexity
- Migration effort, performance overhead
- Keycloak expertise required, SCIM gap (requires bridge)

### Mitigation Strategies
- Multi-replica HA deployment, PostgreSQL clustering
- JWKS caching, connection pooling, Redis sessions
- Custom FastAPI SCIM endpoints bridging to Keycloak Admin API

## Alternatives Considered

1. **Multiple Identity Providers**: Rejected - identity fragmentation, inconsistent tokens
2. **Cloud IAM (Auth0/Okta)**: Rejected - cost at scale, vendor lock-in, data sovereignty
3. **Custom Identity Service**: Rejected - development cost, security risks
4. **Hybrid Approach**: Rejected - inconsistent UX, creates technical debt

## Implementation Details

See `scripts/setup/setup_keycloak.py`, `scripts/setup/setup_ldap_federation.py`, `scripts/setup/setup_saml_idp.py`, `scripts/setup/setup_oidc_idp.py`

## References

- Keycloak Provider: `src/mcp_server_langgraph/auth/keycloak.py`
- Deployment: `deployments/base/keycloak-deployment.yaml`
- Related ADRs: [ADR-0007](adr-0007-authentication-provider-pattern.md), [ADR-0032](adr-0032-jwt-standardization.md), [ADR-0037](adr-0037-identity-federation.md), [ADR-0038](adr-0038-scim-implementation.md)
- External: [Keycloak Docs](https://www.keycloak.org/documentation), [SAML 2.0](https://docs.oasis-open.org/security/saml/v2.0/), [OIDC Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
