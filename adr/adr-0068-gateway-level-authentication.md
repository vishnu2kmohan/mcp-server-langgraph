# ADR-0068: Gateway-Level Authentication with Traefik ForwardAuth

## Status
Proposed

## Context

Currently, authentication in the MCP Server LangGraph stack is handled at the **application level**:
- Each service (MCP Server, Builder, Playground) independently validates JWT tokens from Keycloak
- Observability UIs (Grafana, Qdrant Dashboard, Traefik Dashboard) have no authentication
- This creates security gaps and duplicated authentication logic

### Problems with Current Approach
1. **Security Gap**: Observability dashboards expose sensitive data without auth
2. **Duplicated Logic**: Each service implements JWT validation independently
3. **Inconsistent UX**: Some routes require auth, others don't
4. **No SSO**: Users must authenticate separately per service

## Decision

Implement **gateway-level authentication** using Traefik's ForwardAuth middleware with a dedicated authentication proxy service.

### Architecture

```
                                    ┌─────────────────┐
                                    │    Keycloak     │
                                    │   (OIDC IdP)    │
                                    └────────┬────────┘
                                             │
                                             │ OIDC
                                             │
┌──────────┐     ┌─────────────┐     ┌───────▼────────┐
│  Client  │────▶│   Traefik   │────▶│  traefik-     │
│          │     │   Gateway   │     │  forward-auth  │
└──────────┘     └──────┬──────┘     └───────┬────────┘
                        │                     │
                        │ ForwardAuth         │ Token
                        │ Middleware          │ Validation
                        │                     │
                ┌───────▼──────────────────────▼───────┐
                │                                       │
     ┌──────────┼──────────┬──────────┬───────────────┐
     │          │          │          │               │
     ▼          ▼          ▼          ▼               ▼
┌─────────┐┌─────────┐┌─────────┐┌─────────┐    ┌──────────┐
│   MCP   ││ Builder ││Playground││ Grafana │    │  Qdrant  │
│ Server  ││         ││         ││         │    │Dashboard │
└─────────┘└─────────┘└─────────┘└─────────┘    └──────────┘
```

### Route Classification

| Category | Routes | Auth Required |
|----------|--------|---------------|
| **Public** | `/authn/*` (Keycloak), `*/health*`, `*/ready*` | No |
| **Protected - Apps** | `/mcp/*`, `/build/*`, `/chat/*` | Yes |
| **Protected - Observability** | `/dashboards/*`, `/telemetry/*`, `/gateway/*` | Yes |
| **Internal Only** | `/traces/*`, `/logs/*`, `/metrics/*`, `/vectors/*` | Network isolation |

### Implementation Components

#### 1. traefik-forward-auth Service

Using [thomseddon/traefik-forward-auth](https://github.com/thomseddon/traefik-forward-auth):

```yaml
traefik-forward-auth:
  image: thomseddon/traefik-forward-auth:2
  environment:
    - DEFAULT_PROVIDER=oidc
    - PROVIDERS_OIDC_ISSUER_URL=http://keycloak-test:8080/authn/realms/master
    - PROVIDERS_OIDC_CLIENT_ID=mcp-server
    - PROVIDERS_OIDC_CLIENT_SECRET=test-client-secret-for-e2e-tests
    - SECRET=random-secret-for-cookie-signing
    - AUTH_HOST=auth.localhost
    - COOKIE_DOMAIN=localhost
    - INSECURE_COOKIE=true  # For local dev (no HTTPS)
  labels:
    - "traefik.enable=true"
    - "traefik.http.middlewares.forward-auth.forwardauth.address=http://traefik-forward-auth:4181"
    - "traefik.http.middlewares.forward-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Auth-User"
    - "traefik.http.services.forward-auth.loadbalancer.server.port=4181"
```

#### 2. Traefik Middleware Configuration

Apply middleware to protected routes:

```yaml
# Protected service example
builder-test:
  labels:
    - "traefik.http.routers.builder.middlewares=forward-auth@docker,builder-strip@docker"
```

#### 3. Public Route Bypass

Health/readiness endpoints bypass auth:

```yaml
# Health check route (no auth)
- "traefik.http.routers.mcp-health.rule=PathPrefix(`/mcp/health`)"
- "traefik.http.routers.mcp-health.priority=20"  # Higher priority
# No middlewares = no auth

# Protected route (with auth)
- "traefik.http.routers.mcp-api.rule=PathPrefix(`/mcp`)"
- "traefik.http.routers.mcp-api.priority=10"
- "traefik.http.routers.mcp-api.middlewares=forward-auth@docker,mcp-strip@docker"
```

## Consequences

### Positive
- **Centralized Authentication**: Single point of auth enforcement
- **Consistent Security**: All protected routes use same auth flow
- **SSO Experience**: One login works across all services
- **Reduced Code**: Remove JWT validation from individual services
- **Observability Protection**: Grafana, Qdrant UI now protected

### Negative
- **Additional Service**: traefik-forward-auth adds complexity
- **Single Point of Failure**: Auth proxy down = all protected routes fail
- **Cookie-Based**: Session management adds state
- **Local Dev Complexity**: Need to handle auth in development

### Neutral
- **Migration Required**: Existing services need middleware configuration
- **Testing Changes**: Integration tests need auth awareness

## Alternatives Considered

### 1. OAuth2 Proxy
More feature-rich but heavier weight. Better for complex scenarios.

### 2. Application-Level Only
Current approach. Simple but duplicates logic and leaves gaps.

### 3. Keycloak Gatekeeper
Deprecated (louketo-proxy). Not recommended.

### 4. Kong/Ambassador
Full API gateway. Overkill for test infrastructure.

## Implementation Plan

1. [ ] Add traefik-forward-auth service to docker-compose.test.yml
2. [ ] Create forward-auth middleware in Traefik
3. [ ] Apply middleware to protected routes (priority ordering)
4. [ ] Add public health check routes (higher priority, no auth)
5. [ ] Update tests to handle authentication
6. [ ] Document auth flow for developers

## OpenFGA Authorization Model Updates (2026-01)

As part of the comprehensive authorization audit aligned with this ADR, the following OpenFGA model improvements were implemented:

### Organization Context Enforcement (Phase 3)

Added `user_in_context` relation to `organization` type for contextual tuples:
```json
{
  "type": "organization",
  "relations": {
    "member": {"this": {}},
    "admin": {"this": {}},
    "user_in_context": {"this": {}}
  }
}
```

**Feature Flags** (use FF_ prefix per naming convention):
- `FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT=true` - Require org context in authorization checks
- `FF_OPENFGA_ORG_CONTEXT_FAIL_CLOSED=true` - Fail closed when org context missing

### Conditions Support (Phase 6)

Added conditional authorization for time-bound and tier-based access:

```json
"conditions": {
  "time_bound_share": {
    "expression": "current_time < expiry_time",
    "parameters": {
      "current_time": {"type_name": "TYPE_NAME_TIMESTAMP"},
      "expiry_time": {"type_name": "TYPE_NAME_TIMESTAMP"}
    }
  },
  "subscription_tier": {
    "expression": "user_tier == required_tier || user_tier == 'enterprise' || (user_tier == 'premium' && required_tier == 'free')",
    "parameters": {
      "user_tier": {"type_name": "TYPE_NAME_STRING"},
      "required_tier": {"type_name": "TYPE_NAME_STRING"}
    }
  }
}
```

**Feature Flag**: `FF_OPENFGA_CONDITIONS_ENABLED=false` (default OFF for gradual rollout)

**Server Requirement**: OpenFGA v1.11.2 or higher

### System Type Hierarchy Fix

Fixed monotonic chain in `system` type to properly inherit:
- `admin` → `developer` → `user` → `viewer`

Previously all relations incorrectly inherited directly from `admin`.

### Service Principal Parity (Phase 5)

Extended metadata to include `service_principal` in all user-accepting relations across 14+ types:
- `tool`, `workflow`, `session`, `artifact`, `project`, `agent`, `skill`
- `vector_store`, `dashboard`, `cost`, `observability`, `connection`, `execution`

See also: [ADR-0039](adr-0039-openfga-permission-inheritance.md) for `acts_as` pattern.

### Partner Access Pattern (Phase 9)

Added cross-tenant partnership model for resource sharing between organizations:

```json
{
  "type": "partner",
  "relations": {
    "source_org": {"this": {}},
    "target_org": {"this": {}},
    "admin": {
      "union": {
        "child": [
          {"this": {}},
          {"tupleToUserset": {"tupleset": {"relation": "source_org"}, "computedUserset": {"relation": "admin"}}}
        ]
      }
    },
    "viewer": {
      "union": {
        "child": [
          {"this": {}},
          {"computedUserset": {"relation": "admin"}},
          {"tupleToUserset": {"tupleset": {"relation": "target_org"}, "computedUserset": {"relation": "member"}}}
        ]
      }
    }
  }
}
```

**Key Features**:
- `source_org` - Organization sharing resources
- `target_org` - Organization receiving access
- `admin` - Inherits from source org admins
- `viewer` - Target org members can view shared resources

**Usage Pattern**:
```python
# Create partnership tuple
await openfga_client.write_tuple(
    user="organization:acme",
    relation="source_org",
    object="partner:acme-widgets-partnership"
)
await openfga_client.write_tuple(
    user="organization:widgets-inc",
    relation="target_org",
    object="partner:acme-widgets-partnership"
)

# Now widgets-inc members can view resources shared via this partnership
```

**Modular Definition**: See `config/openfga/modules/04-access-control.fga`

### Removed Types

Removed deprecated `role` type per OpenFGA audit (Phase 0 Task 0.3). Role-based access is handled via Keycloak groups mapped to organization membership, not a separate `role` type.

## References

- [Traefik ForwardAuth Middleware](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [traefik-forward-auth](https://github.com/thomseddon/traefik-forward-auth)
- [Keycloak OIDC Configuration](https://www.keycloak.org/docs/latest/securing_apps/)
- [OpenFGA Conditions](https://openfga.dev/docs/modeling/conditions)
- [OpenFGA Organization Context](https://openfga.dev/docs/modeling/organization-context-authorization)
