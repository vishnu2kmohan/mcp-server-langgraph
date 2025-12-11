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
| **Protected - Apps** | `/mcp/*`, `/build/*`, `/play/*` | Yes |
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

## References

- [Traefik ForwardAuth Middleware](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [traefik-forward-auth](https://github.com/thomseddon/traefik-forward-auth)
- [Keycloak OIDC Configuration](https://www.keycloak.org/docs/latest/securing_apps/)
