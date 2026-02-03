# Keycloak OIDC Issuer Configuration Pattern

**Last Updated**: 2025-12-29
**Purpose**: Lessons learned from OIDC token issuer mismatch debugging
**Reference**: ADR-0070 - OpenFGA OIDC Authentication Migration

---

## The Problem: Inconsistent OIDC Issuer URLs

JWT tokens contain an `iss` (issuer) claim that MUST match what the token validator expects. When Keycloak is accessed via different URLs, it can return different issuer values, causing token validation failures.

### Access Methods and Default Issuer Behavior

| Access Method | URL | Default Issuer (without KC_HOSTNAME_URL) |
|---------------|-----|------------------------------------------|
| Host direct port | `http://localhost:9082/authn/...` | `http://localhost:9082/authn/realms/default` |
| Gateway (Traefik) | `http://localhost/authn/...` | `http://localhost/authn/realms/default` |
| Docker network | `http://keycloak-test:8080/authn/...` | `http://localhost:8080/authn/realms/default` |

The port in the issuer varies based on how Keycloak is accessed, causing `invalid_claims` errors.

---

## Solution: Use KC_HOSTNAME_URL for Consistent Issuer

Configure Keycloak with `KC_HOSTNAME_URL` to force a consistent issuer URL regardless of how it's accessed:

```yaml
# docker compose.test.yml - keycloak-test
environment:
  # KC_HOSTNAME_URL takes precedence and sets the exact base URL for all issuer claims
  # This ensures tokens always have issuer: http://localhost/authn/realms/default
  - KC_HOSTNAME_URL=http://localhost/authn
  - KC_HOSTNAME_BACKCHANNEL_DYNAMIC=false
  - KC_HOSTNAME_STRICT=false
  - KC_HOSTNAME_STRICT_HTTPS=false
```

### With KC_HOSTNAME_URL Set

| Access Method | URL | Issuer in Token |
|---------------|-----|-----------------|
| Host direct port | `http://localhost:9082/authn/...` | `http://localhost/authn/realms/default` |
| Gateway (Traefik) | `http://localhost/authn/...` | `http://localhost/authn/realms/default` |
| Docker network | `http://keycloak-test:8080/authn/...` | `http://localhost/authn/realms/default` |

All tokens now have the same issuer!

---

## OpenFGA OIDC Configuration

OpenFGA validates tokens and needs to:
1. Match the `iss` claim in the token
2. Fetch JWKS from the issuer's `.well-known/openid-configuration` endpoint

### Required Configuration

```yaml
# docker compose.test.yml - openfga-test
environment:
  - OPENFGA_AUTHN_METHOD=oidc
  - OPENFGA_AUTHN_OIDC_ISSUER=http://localhost/authn/realms/default
  # Aliases for backwards compatibility with tokens issued before KC_HOSTNAME_URL change
  - OPENFGA_AUTHN_OIDC_ISSUER_ALIASES=http://localhost:8080/authn/realms/default,http://keycloak-test:8080/authn/realms/default
  - OPENFGA_AUTHN_OIDC_AUDIENCE=openfga-server

# CRITICAL: OpenFGA needs to resolve 'localhost' to reach Keycloak for JWKS fetch
extra_hosts:
  - "localhost:host-gateway"
```

---

## Service Connection Patterns

### Services That MUST Use Gateway (localhost)

| Service | Reason |
|---------|--------|
| Browser OAuth flows | Browser can only resolve `localhost`, not Docker hostnames |
| traefik-forward-auth | OIDC discovery + browser redirects |
| Grafana OAuth | Auth URL is browser redirect |

### Services That CAN Use Direct Connection

| Service | URL | Notes |
|---------|-----|-------|
| openfga-seed-test | `http://keycloak-test:8080/authn` | Client credentials grant, no browser |
| mcp-server-test | `http://keycloak-test:8080/authn` | Token introspection |
| Grafana token/userinfo | `http://keycloak-test:8080/authn` | Server-to-server after auth |

### The "Grafana Pattern" - Best Practice

For services with both browser and server-to-server OAuth flows:

```yaml
# Browser redirect (must be gateway)
GF_AUTH_GENERIC_OAUTH_AUTH_URL=http://localhost/authn/realms/default/.../auth

# Server-to-server (direct is optimal)
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=http://keycloak-test:8080/authn/realms/default/.../token
GF_AUTH_GENERIC_OAUTH_API_URL=http://keycloak-test:8080/authn/realms/default/.../userinfo
```

---

## Debugging Token Issues

### Check Token Issuer

```bash
# Get token and decode
TOKEN=$(curl -s -X POST "http://localhost:9082/authn/realms/default/protocol/openid-connect/token" \
  -d "grant_type=client_credentials&client_id=openfga-server&client_secret=test-openfga-server-secret" \
  | jq -r '.access_token')

# Decode and show issuer
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq -r '.iss'
```

### Check Keycloak's Advertised Issuer

```bash
# From host
curl -s "http://localhost:9082/authn/realms/default/.well-known/openid-configuration" | jq -r '.issuer'

# From Docker network
docker run --rm --network mcp-test-network curlimages/curl:latest \
  -s "http://keycloak-test:8080/authn/realms/default/.well-known/openid-configuration" | jq -r '.issuer'
```

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `invalid_claims` | Token `iss` doesn't match expected issuer | Add issuer to `OPENFGA_AUTHN_OIDC_ISSUER_ALIASES` or configure `KC_HOSTNAME_URL` |
| `invalid_client` | Client ID not found in Keycloak | Add client to realm file or via Admin API |
| `JWKS fetch failed` | Can't reach issuer URL | Add `extra_hosts: localhost:host-gateway` |

---

## Key Takeaways

1. **Use KC_HOSTNAME_URL** for consistent issuer across all access methods
2. **Use extra_hosts** for services that need to resolve `localhost` inside Docker
3. **Browser flows through gateway**, server-to-server can be direct
4. **Keep issuer aliases** for backwards compatibility during migrations
5. **Validate realm files** to prevent duplicate clients (pre-commit hook: `validate-keycloak-realm`)
