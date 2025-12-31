# 87. Grafana Two-Tier Authentication Architecture

Date: 2025-12-31

## Status

Accepted

## Context

**Background**:

The MCP Server LangGraph integrates with Grafana for observability dashboards and alerting. Two distinct access patterns require authentication:

1. **UI Access**: Developers and operators accessing Grafana dashboards via browser
2. **API Access**: Backend services (MCP server) querying Grafana's Alerting API programmatically

The project mandate requires all services to authenticate via Keycloak as the central identity provider (see ADR-0031 Keycloak Authoritative Identity).

**Problem**:

Grafana's JWT authentication (`GF_AUTH_JWT_ENABLED`) requires HTTPS for the JWKS URL:
```
Error: jwt_set_url must have https scheme
```

In the test environment (Docker Compose) without TLS between containers, this requirement cannot be satisfied. The development environment needs a working authentication solution that:
- Maintains Keycloak as the identity provider for human users
- Provides secure API access for service-to-service communication
- Works without TLS in local development

**Requirements**:
- Human users authenticate via Keycloak SSO (browser-based OAuth flow)
- Backend services access Grafana API securely
- Solution must work in both test (HTTP) and production (HTTPS) environments
- Minimal configuration changes between environments

**Stakeholders**:
- Backend developers using the observability stack
- DevOps configuring production deployments
- Security team reviewing authentication architecture

## Decision

We will implement a **two-tier authentication architecture** for Grafana:

| Access Type | Authentication Method | Environment |
|-------------|----------------------|-------------|
| **UI Login** | Keycloak OAuth 2.0 (Generic OAuth) | All |
| **API Access (Test)** | Basic Auth with admin credentials | Test/Dev |
| **API Access (Production)** | JWT via Keycloak OIDC | Production (HTTPS) |

**Rationale**:
- Keycloak OAuth works over HTTP (browser handles redirects)
- JWT authentication requires HTTPS for JWKS URL validation
- Basic auth provides a simple fallback for test environments
- The `GrafanaAlertingClient` already supports both modes via `use_oidc` flag

**Implementation Details**:

### Test Environment (docker-compose.test.yml)

```yaml
# Grafana service
grafana-test:
  environment:
    # OAuth for UI login (works over HTTP)
    - GF_AUTH_GENERIC_OAUTH_ENABLED=true
    - GF_AUTH_GENERIC_OAUTH_CLIENT_ID=grafana
    - GF_AUTH_GENERIC_OAUTH_AUTH_URL=http://localhost/authn/realms/default/protocol/openid-connect/auth
    - GF_AUTH_GENERIC_OAUTH_TOKEN_URL=http://keycloak-test:8080/authn/realms/default/protocol/openid-connect/token
    - GF_AUTH_OAUTH_AUTO_LOGIN=true
    # Login form disabled - OAuth is the only UI auth method
    - GF_AUTH_DISABLE_LOGIN_FORM=true

# MCP Server service
mcp-server-test:
  environment:
    - GRAFANA_URL=http://grafana-test:3000
    # Basic auth for API access in test env
    - GRAFANA_USERNAME=admin
    - GRAFANA_PASSWORD=admin
```

### Production Environment (with HTTPS)

```yaml
# Grafana service
grafana:
  environment:
    # OAuth for UI login
    - GF_AUTH_GENERIC_OAUTH_ENABLED=true
    # JWT for API access (requires HTTPS)
    - GF_AUTH_JWT_ENABLED=true
    - GF_AUTH_JWT_HEADER_NAME=Authorization
    - GF_AUTH_JWT_JWK_SET_URL=https://keycloak/authn/realms/default/protocol/openid-connect/certs
    - GF_AUTH_JWT_EXPECT_CLAIMS={"iss":"https://keycloak/authn/realms/default"}

# MCP Server service
mcp-server:
  environment:
    - GRAFANA_URL=https://grafana:3000
    # OIDC for API access in production
    - GRAFANA_USE_OIDC=true
```

### GrafanaAlertingClient Implementation

```python
# src/mcp_server_langgraph/observability/query/backends/grafana.py

class GrafanaAlertingClient:
    def __init__(self, use_oidc: bool | None = None):
        self.use_oidc = use_oidc if use_oidc is not None else \
            os.getenv("GRAFANA_USE_OIDC", "").lower() in ("true", "1", "yes")

    async def initialize(self) -> None:
        if self.use_oidc:
            # Obtain token from Keycloak via client credentials grant
            token = await self._get_oidc_token()
            headers["Authorization"] = f"Bearer {token}"
        elif self.username and self.password:
            # Fall back to basic auth
            auth = httpx.BasicAuth(self.username, self.password)
```

**Components Affected**:
- `docker-compose.test.yml` - Environment configuration
- `src/mcp_server_langgraph/observability/query/backends/grafana.py` - Client implementation
- `deployments/kubernetes/` - Production Helm values (future)

## Consequences

### Positive Consequences

- **Unified Identity for UI**: All human users authenticate via Keycloak SSO, maintaining single source of identity
- **Environment Flexibility**: Same codebase works in test (HTTP) and production (HTTPS)
- **Security in Production**: JWT authentication with JWKS validation provides cryptographic security
- **Simple Local Development**: Basic auth removes TLS complexity for local testing

### Negative Consequences

- **Credential Management in Test**: Basic auth credentials in docker-compose.yml (acceptable for test env)
- **Configuration Variance**: Different auth methods between test and production require careful documentation
- **Potential Security Gap**: If production accidentally uses basic auth, it's less secure than JWT

### Neutral Consequences

- **Two Code Paths**: GrafanaAlertingClient supports both auth modes (already implemented)
- **Documentation Requirement**: Team must understand when to use which mode

## Alternatives Considered

### Alternative 1: TLS Everywhere (mTLS between containers)

**Description**: Set up TLS certificates for all internal Docker network communication, enabling JWT auth in test environment.

**Pros**:
- Identical auth configuration between test and production
- Enhanced security even in test environment
- No credential management differences

**Cons**:
- Significant complexity for local development
- Certificate management overhead
- Slower container startup (certificate generation/validation)
- Overkill for development/test purposes

**Why Rejected**: The complexity of setting up and maintaining TLS between Docker containers for local development outweighs the benefits. Production already uses Kubernetes ingress with TLS termination.

---

### Alternative 2: Grafana Service Accounts

**Description**: Create a Grafana service account with an API token, provisioned via Grafana's access-control provisioning.

**Pros**:
- More secure than basic auth
- Tokens can be scoped to specific permissions
- Follows Grafana's recommended pattern for API access

**Cons**:
- Service accounts cannot be provisioned via YAML files (must use API)
- Requires post-startup initialization script
- Token rotation complexity
- Additional infrastructure (token storage)

**Why Rejected**: Service accounts require API-based creation after Grafana starts, adding operational complexity. Basic auth with the existing admin user is simpler for test environments.

---

### Alternative 3: Keycloak Token Relay (OAuth2 Proxy)

**Description**: Deploy OAuth2 Proxy in front of Grafana to handle authentication and pass tokens to backend.

**Pros**:
- Single authentication mechanism
- Works with any backend service
- Industry-standard pattern

**Cons**:
- Additional service to deploy and maintain
- Latency overhead for every request
- More complex debugging
- Overkill for internal service-to-service calls

**Why Rejected**: Adds unnecessary complexity when Grafana already supports OAuth natively for UI and JWT/Basic auth for API.

---

## Related Decisions

- **Relates to**: [ADR-0031 - Keycloak Authoritative Identity](adr-0031-keycloak-authoritative-identity.md)
- **Relates to**: [ADR-0067 - Grafana LGTM Stack Migration](adr-0067-grafana-lgtm-stack-migration.md)
- **Relates to**: [ADR-0068 - Gateway Level Authentication](adr-0068-gateway-level-authentication.md)
- **Relates to**: [ADR-0070 - OpenFGA OIDC Authentication](adr-0070-openfga-oidc-authentication.md)

## Implementation Notes

**Timeline**:
- Phase 1 (Complete): Basic auth for test environment
- Phase 2 (Future): JWT auth configuration for production Helm charts
- Phase 3 (Future): Automated environment detection in GrafanaAlertingClient

**Testing Strategy**:
- Unit tests: Mock both auth modes in `GrafanaAlertingClient`
- Integration tests: Test against real Grafana container with basic auth
- Contract tests: Verify API response formats match frontend expectations

**Documentation Updates**:
- [x] Create this ADR
- [ ] Update deployment guide with production JWT configuration
- [ ] Add troubleshooting section for "jwt_set_url must have https scheme" error

**Success Criteria**:
- Grafana alerts API returns data in test environment
- No authentication errors in MCP server logs
- Production deployment uses JWT authentication
- Developers understand which mode applies in each environment

## References

**Internal**:
- Commit `2efb5eea`: fix(grafana): use basic auth for API access (JWT requires HTTPS)
- Commit `3b010d21`: feat(grafana): implement OIDC authentication for API access
- `src/mcp_server_langgraph/observability/query/backends/grafana.py`

**External**:
- [Grafana JWT Authentication](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/jwt/)
- [Grafana Generic OAuth](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth/)
- [Keycloak Client Credentials Grant](https://www.keycloak.org/docs/latest/securing_apps/#_client_credentials_grant)

**Prior Art**:
- Many organizations use different auth for UI (OAuth) vs API (tokens/basic auth)
- Grafana Cloud uses API keys for programmatic access alongside SSO for UI
