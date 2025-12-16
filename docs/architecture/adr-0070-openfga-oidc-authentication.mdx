# ADR-0070: OpenFGA OIDC Authentication Migration

**Status**: Accepted
**Date**: 2025-12-15
**Deciders**: Architecture Team
**Related**: ADR-0002 (OpenFGA Authorization), ADR-0068 (Gateway-Level Authentication)
**Update**: 2025-12-15 - Confirmed OIDC approach after evaluating gateway-level alternative

## Context

OpenFGA previously used preshared key authentication for API access. This approach, while simple, has several limitations:

### Limitations of Preshared Keys

1. **No Expiration**: Static tokens never expire, creating security risk if compromised
2. **No Rotation**: Changing keys requires manual coordination across all services
3. **No Revocation**: Cannot revoke access without changing the key everywhere
4. **Limited Audit Trail**: All services share the same credential, making audit attribution difficult
5. **Not Production-Grade**: Preshared keys are recommended only for development/testing

### Requirements

- Implement OAuth 2.0-based authentication for OpenFGA API access
- Support token expiration and automatic refresh
- Enable per-service credentials for better audit attribution
- Maintain backward compatibility during migration
- Follow industry standards (RFC 6749, RFC 8693)

## Decision

Migrate OpenFGA authentication from preshared keys to **OIDC (OpenID Connect) using OAuth 2.0 Client Credentials Grant** (RFC 6749 Section 4.4).

### Architecture

```
┌─────────────────┐                    ┌──────────────┐
│                 │  1. Request Token  │              │
│  Application    │───────────────────>│  Keycloak    │
│  (Service)      │<───────────────────│              │
│                 │  2. Access Token   └──────────────┘
└─────────────────┘  (JWT, expires 1h)
        │
        │ 3. API Request
        │    Authorization: Bearer <token>
        v
┌─────────────────┐
│                 │
│  OpenFGA        │  - Validates JWT signature (JWKS)
│  Server         │  - Checks audience claim
│                 │  - Verifies expiration
└─────────────────┘
```

### Implementation Details

#### 1. Keycloak Service Accounts

Created dedicated service account clients for each application:

- **openfga-server**: Client ID for OpenFGA internal operations
- **mcp-server**: Application client with service account enabled
- **authz-proxy**: Proxy service client

Configuration (`tests/e2e/default-realm.json`):
```json
{
  "clientId": "openfga-server",
  "serviceAccountsEnabled": true,
  "clientAuthenticatorType": "client-secret",
  "secret": "test-openfga-server-secret"
}
```

#### 2. OpenFGA Server Configuration

OpenFGA server configured for OIDC authentication:

```yaml
environment:
  - OPENFGA_AUTHN_METHOD=oidc
  - OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak:8080/authn/realms/default
  - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
```

#### 3. Client-Side Implementation

**OpenFGAClient** (`src/mcp_server_langgraph/auth/openfga.py`):

- Implements OAuth 2.0 client credentials grant
- Automatic token acquisition and caching
- Token refresh before expiration (30-second buffer)
- Graceful fallback to preshared key for backward compatibility

**Token Acquisition Flow**:
```python
async def _get_oidc_access_token(self) -> str | None:
    # 1. Check cached token (reuse if valid for >30s)
    if self._oidc_access_token and self._oidc_token_expires_at:
        if time.time() < (self._oidc_token_expires_at - 30):
            return self._oidc_access_token

    # 2. Obtain new token from Keycloak
    token_endpoint = f"{self.oidc_issuer}/protocol/openid-connect/token"
    response = await httpx.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "client_id": self.oidc_client_id,
            "client_secret": self.oidc_client_secret,
        }
    )

    # 3. Cache token with expiration
    self._oidc_access_token = response.json()["access_token"]
    self._oidc_token_expires_at = time.time() + expires_in

    return self._oidc_access_token
```

#### 4. Configuration

**Environment Variables**:
```bash
# OIDC authentication (recommended)
OPENFGA_OIDC_CLIENT_ID=openfga-server
OPENFGA_OIDC_CLIENT_SECRET=test-openfga-server-secret

# Keycloak settings (for issuer URL construction)
KEYCLOAK_SERVER_URL=http://keycloak:8080/authn
KEYCLOAK_REALM=default

# Legacy preshared key (deprecated, fallback only)
# OPENFGA_PRESHARED_KEY=test-openfga-preshared-key
```

**Settings Class** (`src/mcp_server_langgraph/core/config.py`):
```python
class Settings(BaseSettings):
    # OIDC authentication (recommended)
    openfga_oidc_client_id: str | None = None
    openfga_oidc_client_secret: str | None = None

    # Legacy preshared key (deprecated)
    openfga_preshared_key: str | None = None
```

### Migration Strategy

**Phase 1**: Dual Support (Current)
- OpenFGAClient supports both OIDC and preshared key
- Priority: OIDC > preshared key > none
- Enables gradual migration without breaking existing deployments

**Phase 2**: OIDC Default (Future)
- Make OIDC the default authentication method
- Log warnings for preshared key usage
- Update all deployment configurations

**Phase 3**: Deprecation (Future)
- Remove preshared key support
- OIDC becomes required

## Consequences

### Positive

1. **Security Improvements**
   - Token expiration limits exposure window (1 hour default)
   - Automatic token rotation prevents long-lived credential exposure
   - Revocation capability via Keycloak admin API
   - Per-service credentials enable attribution in audit logs

2. **Operational Benefits**
   - Centralized credential management via Keycloak
   - Token refresh handled automatically by client library
   - No manual key rotation required
   - Better observability (token acquisition logged)

3. **Standards Compliance**
   - OAuth 2.0 client credentials grant (RFC 6749 Section 4.4)
   - OIDC standard for token validation
   - Industry-standard approach used by major platforms

4. **Backward Compatibility**
   - Preshared key still supported during migration
   - No breaking changes to existing deployments
   - Gradual rollout possible

### Negative

1. **Additional Dependency**
   - Requires Keycloak to be running for OpenFGA access
   - Increased complexity in infrastructure setup
   - Token acquisition adds network round-trip on first request

2. **Migration Effort**
   - All environments need Keycloak service account configuration
   - Environment variables must be updated
   - Testing required for all services using OpenFGA

3. **Token Caching Complexity**
   - Need to manage token expiration and refresh
   - Clock skew considerations (30-second buffer)
   - Memory overhead for cached tokens

### Mitigations

1. **Dependency Risk**: Token caching minimizes Keycloak dependency
2. **Migration Complexity**: Dual support enables gradual rollout
3. **Performance**: Token reuse prevents excessive Keycloak calls

## Testing

### Unit Tests

**Tests Created**: `tests/unit/auth/test_openfga_oidc_client.py`

- Configuration validation (OIDC fields in `OpenFGAConfig`)
- Token acquisition logic (client credentials grant)
- Token caching and expiration (30-second buffer)
- Token refresh behavior (automatic on near-expiry)
- Error handling (HTTP failures, missing fields)
- Authentication priority (OIDC > preshared > none)

**Coverage**: 14 unit tests, all passing

### Integration Tests

**Tests Created**: `tests/integration/auth/test_openfga_oidc.py`

- OpenFGA rejects unauthenticated requests
- OpenFGA rejects invalid OIDC tokens
- Successful token acquisition from Keycloak
- OpenFGA accepts valid OIDC tokens
- OpenFGAClient automatic token management
- Token caching across multiple requests
- Automatic token refresh on expiration
- Write operations with OIDC authentication

**Coverage**: 8 integration tests (require docker infrastructure)

### Backward Compatibility

**Tests Verified**: `tests/api/test_auth_oauth2.py`

- 50 OAuth2 API tests, all passing
- No breaking changes to existing authentication flows

## Architecture Evaluation (2025-12-15)

### OpenFGA Playground Compatibility Issue

During implementation, we discovered that **OpenFGA Playground does not support OIDC authentication**. The Playground UI only supports two authentication methods:
1. `authn=none` (no authentication)
2. `authn=preshared` (preshared key)

When configured with `authn=oidc`, the Playground service crashes with:
```
panic: the playground only supports authn methods 'none' and 'preshared'
```

### Considered Alternatives

We evaluated two architectural approaches:

#### Option A: Gateway-Level Authentication
- **OpenFGA Server**: `authn=none`
- **Security Layer**: Traefik forward-auth middleware on Playground UI route
- **Service-to-Service**: No authentication required
- **✅ Pros**: Playground works, simpler configuration
- **❌ Cons**: No defense-in-depth, relies solely on network isolation

#### Option B: OIDC Authentication (Selected)
- **OpenFGA Server**: `authn=oidc`
- **Security Layer**: Token validation at OpenFGA + network isolation
- **Service-to-Service**: OIDC tokens via client credentials grant
- **✅ Pros**: Defense-in-depth security, proper authentication for service-to-service
- **❌ Cons**: Playground must be disabled

### Final Decision: OIDC with Disabled Playground

**Rationale**:
1. **Defense-in-Depth Security**: Even if an attacker gains access to the Docker network, they cannot call OpenFGA API without valid OIDC tokens
2. **Production Best Practice**: Service-to-service authentication is critical for production environments
3. **Playground is Development Tool**: Playground is primarily useful for development/debugging, not essential for production
4. **Future Flexibility**: Can enable Playground in non-production environments by switching to `authn=none` or `authn=preshared`

**Configuration**:
```yaml
# docker-compose.test.yml
openfga-test:
  environment:
    - OPENFGA_AUTHN_METHOD=oidc
    - OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak-test:8080/authn/realms/default
    - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
    - OPENFGA_PLAYGROUND_ENABLED=false  # Incompatible with OIDC
```

**Impact**:
- OpenFGA Playground UI is unavailable in OIDC mode
- All OpenFGA API access requires valid OIDC tokens
- authz-proxy, mcp-server, and other services obtain tokens via OAuth 2.0 client credentials grant
- Defense-in-depth: network isolation + token validation

## References

- **RFC 6749**: OAuth 2.0 Authorization Framework (Client Credentials Grant)
- **RFC 8693**: OAuth 2.0 Token Exchange
- **OpenFGA Docs**: [Authentication Configuration](https://openfga.dev/docs/getting-started/setup-openfga/configure-authentication)
- **OpenFGA Playground Limitation**: Playground only supports `authn=none` and `authn=preshared`
- **Keycloak Docs**: [Service Account Client](https://www.keycloak.org/docs/latest/server_admin/#_service_accounts)
- **ADR-0002**: OpenFGA Authorization (original authorization decision)
- **ADR-0068**: Gateway-Level Authentication (OAuth2 architecture)

## Implementation Checklist

- [x] Create Keycloak service account for OpenFGA
- [x] Update OpenFGA server configuration to use OIDC
- [x] Implement OIDC token acquisition in OpenFGAClient
- [x] Add token caching and automatic refresh
- [x] Update authz-proxy to use OIDC tokens
- [x] Update mcp-server to use OIDC configuration
- [x] Write comprehensive unit tests (14 tests)
- [x] Write integration tests (8 tests)
- [x] Verify backward compatibility (50 OAuth2 tests)
- [ ] Update production deployment configurations
- [ ] Document migration guide for operators
- [ ] Create runbook for token-related troubleshooting

## Migration Guide

### For Operators

1. **Create Keycloak Service Account**:
   ```bash
   # Login to Keycloak Admin Console
   # Navigate to: Clients -> Create
   # Client ID: openfga-server
   # Enable: Service Accounts Enabled
   # Save and note the client secret
   ```

2. **Update Environment Variables**:
   ```bash
   # Add OIDC credentials
   export OPENFGA_OIDC_CLIENT_ID=openfga-server
   export OPENFGA_OIDC_CLIENT_SECRET=<secret-from-keycloak>

   # Keep preshared key for fallback (optional)
   export OPENFGA_PRESHARED_KEY=<existing-key>
   ```

3. **Update OpenFGA Server Config**:
   ```yaml
   environment:
     - OPENFGA_AUTHN_METHOD=oidc
     - OPENFGA_AUTHN_OIDC_ISSUER=http://keycloak:8080/authn/realms/default
     - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server
   ```

4. **Restart Services**:
   ```bash
   docker compose restart openfga-test
   docker compose restart mcp-server-test
   docker compose restart authz-proxy-test
   ```

5. **Verify OIDC Authentication**:
   ```bash
   # Check logs for "OIDC access token obtained successfully"
   docker compose logs -f mcp-server-test | grep OIDC

   # Test API access
   curl -H "Authorization: Bearer $(get_oidc_token)" \
        http://localhost:9080/stores
   ```

### For Developers

See updated code examples in:
- `src/mcp_server_langgraph/auth/openfga.py` (OpenFGAClient)
- `src/mcp_server_langgraph/authz_proxy/server.py` (authz-proxy)
- `src/mcp_server_langgraph/mcp/server_streamable.py` (mcp-server)
- `tests/unit/auth/test_openfga_oidc_client.py` (test patterns)
