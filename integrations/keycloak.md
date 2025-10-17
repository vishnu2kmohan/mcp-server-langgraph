# Keycloak Integration Guide

Complete guide to production-ready authentication with Keycloak for MCP Server with LangGraph.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [User Provider Pattern](#user-provider-pattern)
- [Authentication Flows](#authentication-flows)
- [Token Management](#token-management)
- [Role Mapping](#role-mapping-to-openfga)
- [Troubleshooting](#troubleshooting)
- [Production Best Practices](#production-best-practices)

---

## Overview

Keycloak integration provides **production-grade authentication** for your MCP server:

### Key Features

✅ **OAuth2/OIDC Compliance**: Industry-standard authentication protocols
✅ **JWKS Token Verification**: No shared secrets, uses public key cryptography
✅ **Automatic Token Refresh**: Seamless session extension without re-authentication
✅ **Role Synchronization**: Automatic mapping of Keycloak roles/groups to OpenFGA
✅ **User Provider Pattern**: Pluggable architecture supporting multiple backends
✅ **Backward Compatible**: Defaults to in-memory provider for development

### When to Use

| Environment | Provider | Use Case |
|------------|----------|----------|
| **Development** | InMemory | Local testing, no external dependencies |
| **Staging** | Keycloak | Pre-production validation |
| **Production** | Keycloak | Enterprise authentication, SSO, compliance |

---

## Quick Start

### 1. Start Keycloak

```bash
# Start infrastructure (includes Keycloak on port 8180)
make setup-infra

# Wait for Keycloak to start (60+ seconds)
# Check: http://localhost:8180
```

### 2. Initialize Keycloak

```bash
# Create realm, client, and test users
make setup-keycloak

# Output will include client secret - copy to .env
```

### 3. Configure Environment

Add to `.env`:

```bash
# Authentication Provider
AUTH_PROVIDER=keycloak  # Switch from "inmemory" to "keycloak"

# Keycloak Configuration
KEYCLOAK_SERVER_URL=http://localhost:8180
KEYCLOAK_REALM=langgraph-agent
KEYCLOAK_CLIENT_ID=langgraph-client
KEYCLOAK_CLIENT_SECRET=<paste-from-setup-output>
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# Optional: SSL verification (disable for local dev)
KEYCLOAK_VERIFY_SSL=false
```

### 4. Test Authentication

```bash
# Run example
python examples/keycloak_usage.py

# Test users created by setup:
# - alice / alice123  (roles: user, premium)
# - bob / bob123      (roles: user)
# - admin / admin123  (roles: admin)
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Application                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐        ┌──────────────────┐           │
│  │ AuthMiddleware  │───────▶│  UserProvider    │           │
│  └─────────────────┘        │   (Interface)    │           │
│          │                  └──────────────────┘           │
│          │                           │                       │
│          │          ┌────────────────┴────────────────┐     │
│          │          │                                  │     │
│          │    ┌──────────────┐           ┌─────────────────┐│
│          │    │   InMemory   │           │   Keycloak      ││
│          │    │   Provider   │           │   Provider      ││
│          │    └──────────────┘           └─────────────────┘│
│          │                                         │         │
│          │                                         │         │
│          ▼                                         ▼         │
│   ┌──────────────┐                   ┌──────────────────┐  │
│   │   OpenFGA    │◀──────────────────│ KeycloakClient   │  │
│   │ (Authorizat.) │                   │ - authenticate() │  │
│   └──────────────┘                   │ - verify_token() │  │
│                                       │ - refresh_token()│  │
│                                       └──────────────────┘  │
│                                                │             │
└────────────────────────────────────────────────┼─────────────┘
                                                 │
                                                 ▼
                                    ┌───────────────────────┐
                                    │   Keycloak Server     │
                                    │  - OIDC/OAuth2        │
                                    │  - User Management    │
                                    │  - JWKS Endpoints     │
                                    └───────────────────────┘
```

### Authentication Flow (ROPC)

```
Client                 MCP Server              Keycloak
  │                         │                       │
  ├──POST /auth/login──────▶│                       │
  │  {username, password}   │                       │
  │                         ├──POST /token─────────▶│
  │                         │  grant_type=password  │
  │                         │  username=alice       │
  │                         │  password=***         │
  │                         │                       │
  │                         │◀──200 OK──────────────┤
  │                         │  {access_token,       │
  │                         │   refresh_token}      │
  │                         │                       │
  │                         ├──Verify Token────────▶│
  │                         │  (JWKS public key)    │
  │                         │                       │
  │                         ├──Sync Roles──────────▶│
  │                         │  (to OpenFGA)         │
  │                         │                       │
  │◀──200 OK────────────────┤                       │
  │  {user_id, roles,       │                       │
  │   access_token}         │                       │
```

### Token Verification Flow

```
Client                 MCP Server              Keycloak
  │                         │                       │
  ├──Request w/ Token──────▶│                       │
  │  Authorization: Bearer  │                       │
  │                         │                       │
  │                         ├──GET /certs──────────▶│
  │                         │  (JWKS endpoint)      │
  │                         │                       │
  │                         │◀──JWKS────────────────┤
  │                         │  {public keys}        │
  │                         │  [cached 1 hour]      │
  │                         │                       │
  │                         ├──Verify Signature─────┤
  │                         │  (RSA public key)     │
  │                         │  Check expiration     │
  │                         │  Validate audience    │
  │                         │                       │
  │◀──Response──────────────┤                       │
```

---

## Configuration

### Settings Reference

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| **Provider Type** | `AUTH_PROVIDER` | `inmemory` | `inmemory` or `keycloak` |
| **Server URL** | `KEYCLOAK_SERVER_URL` | `http://localhost:8180` | Keycloak base URL |
| **Realm** | `KEYCLOAK_REALM` | `langgraph-agent` | Keycloak realm name |
| **Client ID** | `KEYCLOAK_CLIENT_ID` | `langgraph-client` | OAuth2 client ID |
| **Client Secret** | `KEYCLOAK_CLIENT_SECRET` | None | OAuth2 client secret (required) |
| **Admin Username** | `KEYCLOAK_ADMIN_USERNAME` | `admin` | Admin API username |
| **Admin Password** | `KEYCLOAK_ADMIN_PASSWORD` | None | Admin API password |
| **Verify SSL** | `KEYCLOAK_VERIFY_SSL` | `true` | Verify SSL certificates |
| **Timeout** | `KEYCLOAK_TIMEOUT` | `30` | HTTP request timeout (seconds) |

### Feature Flags

Control Keycloak features via environment variables with `FF_` prefix:

```bash
# Keycloak features (default: all enabled)
FF_ENABLE_KEYCLOAK=true
FF_ENABLE_TOKEN_REFRESH=true
FF_KEYCLOAK_ROLE_SYNC=true
FF_OPENFGA_SYNC_ON_LOGIN=true
```

### Programmatic Configuration

```python
from mcp_server_langgraph.auth.keycloak import KeycloakConfig, KeycloakClient
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.user_provider import KeycloakUserProvider

# Create Keycloak configuration
keycloak_config = KeycloakConfig(
    server_url="https://keycloak.example.com",
    realm="production",
    client_id="mcp-server",
    client_secret="your-secret-here",
    admin_username="admin",
    admin_password="admin-password",
    verify_ssl=True,
    timeout=30,
)

# Create user provider
keycloak_provider = KeycloakUserProvider(
    config=keycloak_config,
    openfga_client=openfga_client,  # Optional
    sync_on_login=True,  # Sync roles to OpenFGA on login
)

# Use with AuthMiddleware
auth = AuthMiddleware(
    secret_key=settings.jwt_secret_key,
    openfga_client=openfga_client,
    user_provider=keycloak_provider,
)
```

---

## User Provider Pattern

The User Provider pattern enables **pluggable authentication backends** without changing application code.

### Interface

All providers implement the `UserProvider` abstract base class:

```python
class UserProvider(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate user and return user details"""
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        pass
```

### Factory Function

Use `create_user_provider()` to switch providers:

```python
from mcp_server_langgraph.auth.user_provider import create_user_provider
from mcp_server_langgraph.core.config import settings

# Automatically selects provider based on settings.auth_provider
provider = create_user_provider(
    provider_type=settings.auth_provider,  # "inmemory" or "keycloak"
    secret_key=settings.jwt_secret_key,
    keycloak_config=keycloak_config if settings.auth_provider == "keycloak" else None,
    openfga_client=openfga_client,
)
```

### Switching Providers

**Development → Production Migration:**

```python
# Step 1: Development with InMemory (no external dependencies)
AUTH_PROVIDER=inmemory

# Step 2: Staging with Keycloak (pre-production testing)
AUTH_PROVIDER=keycloak
KEYCLOAK_SERVER_URL=https://staging-keycloak.example.com

# Step 3: Production with Keycloak (full SSO, compliance)
AUTH_PROVIDER=keycloak
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_VERIFY_SSL=true
```

---

## Authentication Flows

### 1. Resource Owner Password Credentials (ROPC)

**When to use:** Direct username/password authentication

```python
from mcp_server_langgraph.auth.keycloak import KeycloakClient

client = KeycloakClient(config)

# Authenticate user
tokens = await client.authenticate_user("alice", "alice123")

# Returns:
# {
#     "access_token": "eyJhbGci...",
#     "refresh_token": "eyJhbGci...",
#     "expires_in": 300,
#     "token_type": "Bearer"
# }
```

### 2. Token Verification (JWKS)

**When to use:** Verify tokens from other services

```python
# Verify token using Keycloak public keys
payload = await client.verify_token(access_token)

# Returns decoded payload:
# {
#     "sub": "550e8400-e29b-41d4-a716-446655440000",
#     "preferred_username": "alice",
#     "email": "alice@acme.com",
#     "realm_access": {"roles": ["user", "premium"]},
#     "exp": 1234567890,
#     "iat": 1234567590
# }
```

### 3. Token Refresh

**When to use:** Extend session without re-authentication

```python
# Refresh access token
new_tokens = await client.refresh_token(refresh_token)

# Returns new access_token and refresh_token
```

### 4. User Information

**When to use:** Get detailed user profile

```python
# Get user info from token
userinfo = await client.get_userinfo(access_token)

# Get full user details (requires admin token)
user = await client.get_user_by_username("alice")
# Returns KeycloakUser object with roles, groups, attributes
```

---

## Token Management

### Token Lifecycle

```
┌─────────────────┐
│  User Login     │
│  (ROPC Flow)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Access Token Issued    │
│  - Valid: 5 minutes     │
│  - Type: JWT (RS256)    │
│  - Contains: user info  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Token Used in Requests │
│  - Bearer Authorization │
│  - Verified via JWKS    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Token Expiration       │
│  (5 min before exp)     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Refresh Token Flow     │
│  - Get new access token │
│  - Extend session       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Logout / Revocation    │
│  - Token invalidated    │
└─────────────────────────┘
```

### JWKS Caching

To minimize HTTP calls to Keycloak:

```python
class TokenValidator:
    def __init__(self, config):
        self._jwks_cache = None
        self._jwks_cache_time = None
        self._cache_ttl = timedelta(hours=1)  # Cache public keys for 1 hour
```

**Benefits:**
- Reduces latency for token verification
- Decreases load on Keycloak server
- Handles key rotation automatically (refreshes if kid not found)

### Token Refresh Strategy

```python
# Automatic refresh before expiration
if token_expires_in < 300:  # 5 minutes
    new_tokens = await client.refresh_token(refresh_token)
    # Update session with new tokens
```

---

## Role Mapping to OpenFGA

### Automatic Synchronization

When a user authenticates, their Keycloak roles/groups are automatically synced to OpenFGA:

```python
async def sync_user_to_openfga(keycloak_user: KeycloakUser, openfga_client):
    """
    Maps Keycloak roles/groups to OpenFGA tuples
    """
    tuples = []

    # Admin role → system:global admin
    if "admin" in keycloak_user.realm_roles:
        tuples.append({
            "user": keycloak_user.user_id,
            "relation": "admin",
            "object": "system:global"
        })

    # Groups → organization memberships
    for group in keycloak_user.groups:
        org_name = group.strip("/").split("/")[-1]
        tuples.append({
            "user": keycloak_user.user_id,
            "relation": "member",
            "object": f"organization:{org_name}"
        })

    # Premium role → role assignment
    if "premium" in keycloak_user.realm_roles:
        tuples.append({
            "user": keycloak_user.user_id,
            "relation": "assignee",
            "object": "role:premium"
        })

    await openfga_client.write_tuples(tuples)
```

### Mapping Examples

| Keycloak | OpenFGA Tuple |
|----------|---------------|
| Realm role: `admin` | `user:alice admin system:global` |
| Group: `/acme` | `user:alice member organization:acme` |
| Group: `/acme/engineering` | `user:alice member organization:engineering` |
| Realm role: `premium` | `user:alice assignee role:premium` |
| Client role: `executor` | `user:alice assignee role:executor` |

### Custom Mapping

To customize role mapping, modify `sync_user_to_openfga()`:

```python
# Example: Map custom attributes
if keycloak_user.attributes.get("department") == ["finance"]:
    tuples.append({
        "user": keycloak_user.user_id,
        "relation": "viewer",
        "object": "resource:financial-reports"
    })
```

---

## Troubleshooting

### Common Issues

#### 1. "Client secret required"

**Problem:** Keycloak authentication fails
**Cause:** Missing or incorrect `KEYCLOAK_CLIENT_SECRET`
**Solution:**
```bash
# Re-run setup and copy the client secret
make setup-keycloak

# Update .env
KEYCLOAK_CLIENT_SECRET=<paste-secret-here>
```

#### 2. "Connection refused on port 8180"

**Problem:** Cannot connect to Keycloak
**Cause:** Keycloak not started or still initializing
**Solution:**
```bash
# Check if Keycloak is running
docker ps | grep keycloak

# Check Keycloak logs
docker-compose logs keycloak

# Restart if needed
docker-compose restart keycloak

# Wait 60+ seconds for initialization
```

#### 3. "Token verification failed: kid not found"

**Problem:** Token signed with unknown key
**Cause:** JWKS cache out of date or key rotation
**Solution:**
- TokenValidator automatically refreshes JWKS
- If persistent, check Keycloak realm settings
- Verify `client_id` matches token audience

#### 4. "User not found in admin API"

**Problem:** User authenticated but admin API lookup fails
**Cause:** Admin credentials incorrect
**Solution:**
```bash
# Verify admin credentials in .env
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# Check Keycloak admin console
# http://localhost:8180/admin
```

#### 5. "OpenFGA sync failed"

**Problem:** Role synchronization errors
**Cause:** OpenFGA not initialized or network issues
**Solution:**
```bash
# Verify OpenFGA is running
make setup-openfga

# Check OpenFGA connection in .env
OPENFGA_API_URL=http://localhost:8080
OPENFGA_STORE_ID=<store-id>
OPENFGA_MODEL_ID=<model-id>

# Note: Authentication succeeds even if sync fails
```

### Debug Mode

Enable detailed logging:

```bash
# Enable debug logging
FF_ENABLE_DETAILED_LOGGING=true
LOG_LEVEL=DEBUG

# Run server
make run-streamable
```

### Testing Connectivity

```bash
# Test Keycloak health
curl http://localhost:8180/health/ready

# Test JWKS endpoint
curl http://localhost:8180/realms/langgraph-agent/protocol/openid-connect/certs

# Test token endpoint
curl -X POST http://localhost:8180/realms/langgraph-agent/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=langgraph-client" \
  -d "username=alice" \
  -d "password=alice123"
```

---

## Production Best Practices

### Security

#### 1. Use HTTPS in Production

```bash
# Production configuration
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_VERIFY_SSL=true
```

#### 2. Rotate Secrets Regularly

```bash
# Rotate client secret every 90 days
# 1. Generate new secret in Keycloak admin console
# 2. Update KEYCLOAK_CLIENT_SECRET in secrets manager
# 3. Deploy updated configuration
# 4. Remove old secret after grace period
```

#### 3. Use Infisical for Secret Management

```python
from mcp_server_langgraph.secrets.manager import SecretsManager

secrets = SecretsManager()

# Store Keycloak credentials in Infisical
keycloak_config = KeycloakConfig(
    server_url=secrets.get("KEYCLOAK_SERVER_URL"),
    client_secret=secrets.get("KEYCLOAK_CLIENT_SECRET"),
    admin_password=secrets.get("KEYCLOAK_ADMIN_PASSWORD"),
)
```

### Performance

#### 1. Enable JWKS Caching

✅ Already enabled (1-hour TTL)
✅ Automatic cache refresh on key rotation

#### 2. Enable Role Sync on Login

```bash
# Sync only on login (not every request)
FF_OPENFGA_SYNC_ON_LOGIN=true

# Consider async background sync for high-traffic systems
```

#### 3. Connection Pooling

```python
# Use httpx connection pooling
client = httpx.AsyncClient(
    verify=True,
    timeout=30,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)
```

### Monitoring

#### 1. Track Authentication Metrics

```python
from mcp_server_langgraph.observability.telemetry import metrics

# Automatically tracked:
# - auth_failures (by reason: expired_token, invalid_credentials)
# - successful_calls (by operation: authenticate_user, verify_token)
# - failed_calls (by operation)
```

#### 2. Set Up Alerts

- High authentication failure rate (> 10%)
- Token verification errors (> 5%)
- Keycloak connection failures
- JWKS fetch failures

#### 3. Grafana Dashboards

See: `observability/grafana/auth_dashboard.json` (coming in Phase 2)

### High Availability

#### 1. Keycloak Clustering

For production, deploy Keycloak in clustered mode:

```yaml
# docker-compose.prod.yml
keycloak:
  image: quay.io/keycloak/keycloak:23.0
  command: start --optimized
  environment:
    - KC_DB=postgres
    - KC_DB_URL_HOST=postgres-primary
    - KC_CACHE=ispn
    - KC_CACHE_STACK=kubernetes
  replicas: 3
```

#### 2. Database Replication

Use PostgreSQL replication for Keycloak database

#### 3. Graceful Degradation

```python
# Keycloak provider gracefully handles failures
try:
    result = await keycloak_provider.authenticate(username, password)
except Exception as e:
    # Log error but don't crash
    logger.error(f"Keycloak authentication failed: {e}")
    # Consider fallback to cached credentials or maintenance mode
```

### Compliance

#### 1. GDPR Compliance

- Enable Keycloak audit logging
- Configure user data retention policies
- Implement right-to-be-forgotten workflows

#### 2. SOC 2 Requirements

- Enable MFA in Keycloak
- Implement session timeout policies
- Log all authentication events

#### 3. HIPAA Requirements

- Use encrypted connections (TLS 1.3)
- Implement strong password policies
- Enable comprehensive audit logging

---

## Next Steps

1. **Complete Setup**: Run `make setup-keycloak` and configure `.env`
2. **Test Integration**: Run `python examples/keycloak_usage.py`
3. **Customize Roles**: Modify role mapping in `sync_user_to_openfga()`
4. **Production Deploy**: Follow [Production Deployment Guide](../docs/deployment/production-checklist.mdx)
5. **Monitor & Alert**: Set up Grafana dashboards and alerts

## Related Documentation

- [OpenFGA & Infisical Integration](./openfga-infisical.md)
- [Production Deployment Guide](../docs/deployment/production-checklist.mdx)
- [Testing Guide](../docs/advanced/testing.mdx)
- [Feature Flags](../src/mcp_server_langgraph/core/feature_flags.py)

---

**Need Help?**
- [GitHub Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenFGA Documentation](https://openfga.dev/docs)
