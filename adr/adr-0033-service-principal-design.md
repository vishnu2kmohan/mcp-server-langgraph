# 33. Service Principal Design and Authentication Modes

Date: 2025-01-28

## Status

Accepted

## Context

Machine-to-machine authentication, batch jobs, streaming tasks, and background processes require persistent identity and long-lived credentials that differ from human user patterns. Challenges include:

- **Long-Running Tasks**: OAuth2 JWTs have short lifespans (15 min) unsuitable for batch jobs running hours/days
- **Streaming Sessions**: WebSocket connections need credentials persisting throughout session
- **Permission Attribution**: Automated processes need clear ownership and auditable identity
- **Permission Inheritance**: Background jobs often need to act on behalf of specific users
- **Credential Management**: Services need programmatic authentication without human interaction

Current system only supports human user authentication with 15-minute token lifetimes.

## Decision

We will implement **Service Principals as first-class identities** with two authentication modes and optional user association for permission inheritance.

### Core Principles

1. **First-Class Identity**: Service principals distinct from users in authorization model
2. **Dual Authentication**: Support OAuth2 client credentials AND service account users
3. **Optional User Association**: Service principals can act on behalf of specific users
4. **Permission Inheritance**: Can inherit permissions from associated user principals
5. **Long-Lived Credentials**: Support 30-day refresh tokens for persistent tasks
6. **Keycloak-Issued**: All service principal tokens issued by Keycloak (JWT standard)

### Architecture

**Service Principal Identity Format**:
- Subject (sub) claim: `service:<client-id>` (e.g., `service:batch-etl-job`)
- OpenFGA Object: `service_principal:batch-etl-job`

### Authentication Modes

#### Mode 1: Client Credentials Flow (Preferred)
**Use Case**: Dedicated services, microservices, batch jobs

**Keycloak Configuration**:
```json
{
  "clientId": "batch-etl-job",
  "serviceAccountsEnabled": true,
  "attributes": {
    "associatedUserId": "user:alice",
    "inheritPermissions": "true",
    "owner": "user:bob"
  }
}
```

**Authentication**:
```python
response = await httpx.post(token_endpoint, data={
    "grant_type": "client_credentials",
    "client_id": "batch-etl-job",
    "client_secret": "service-secret"
})
```

#### Mode 2: Service Account User (Alternative)
**Use Case**: Legacy systems migration, mixed authentication needs

**Keycloak Configuration**:
```json
{
  "username": "svc_batch_etl",
  "attributes": {
    "serviceAccount": "true",
    "associatedUserId": "user:alice",
    "inheritPermissions": "true"
  }
}
```

### User Association and Permission Inheritance

**OpenFGA Tuples**:
```python
[
    # Service acts as user (permission inheritance)
    {"user": "service:batch-etl-job", "relation": "acts_as", "object": "user:alice"},
    # User owns service principal
    {"user": "user:bob", "relation": "owner", "object": "service_principal:batch-etl-job"}
]
```

**Permission Check**: Service inherits user permissions via `acts_as` relationship.

### Configuration

```bash
ENABLE_SERVICE_PRINCIPALS=true
SERVICE_PRINCIPAL_DEFAULT_TTL=2592000  # 30 days
SERVICE_PRINCIPAL_REFRESH_TOKEN_LIFESPAN=2592000
SERVICE_PRINCIPAL_INHERIT_PERMISSIONS=true
SERVICE_PRINCIPAL_ROTATE_SECRET_DAYS=90
```

## Consequences

### Positive Consequences
- Long-running support (30-day tokens), clear attribution
- Permission delegation without password sharing
- Audit trail, flexible authentication (two modes)
- Security isolation, ownership tracking

### Negative Consequences
- Implementation complexity (two modes)
- Keycloak configuration expertise required
- OpenFGA model changes, additional secrets to manage
- Permission inheritance may be non-obvious

### Mitigation Strategies
- High-level SDK abstracting modes, clear documentation
- Automated secret rotation (90 days), IP whitelisting
- Audit reports showing effective permissions

## Alternatives Considered

1. **User Accounts Only**: Rejected - conflates humans with machines, poor audit trail
2. **API Keys Only**: Rejected - violates JWT standardization
3. **Client Credentials Only**: Rejected - lacks flexibility for legacy systems
4. **Impersonation Flow**: Rejected - security risk of admin credentials in services

## Implementation

**ServicePrincipalManager** (`src/mcp_server_langgraph/auth/service_principal.py`):
```python
class ServicePrincipalManager:
    async def create_service_principal(
        self, service_id, name, authentication_mode,
        associated_user_id=None, inherit_permissions=False
    ) -> ServicePrincipal:
        # Create in Keycloak (client or user)
        # Sync to OpenFGA with acts_as tuples
```

**API Endpoints** (`src/mcp_server_langgraph/api/service_principals.py`):
- POST `/api/v1/service-principals` - Create
- GET `/api/v1/service-principals` - List owned
- POST `/api/v1/service-principals/{id}/rotate-secret` - Rotate
- DELETE `/api/v1/service-principals/{id}` - Delete

## References

- Implementation: `src/mcp_server_langgraph/auth/service_principal.py` (to be created)
- API: `src/mcp_server_langgraph/api/service_principals.py` (to be created)
- Related ADRs: [ADR-0031](adr-0031-keycloak-authoritative-identity.md), [ADR-0032](adr-0032-jwt-standardization.md), [ADR-0036](adr-0036-hybrid-session-model.md), [ADR-0039](adr-0039-openfga-permission-inheritance.md)
- External: [OAuth 2.0 Client Credentials](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4), [Keycloak Service Accounts](https://www.keycloak.org/docs/latest/server_admin/#_service_accounts)
