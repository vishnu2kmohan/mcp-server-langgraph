# OpenFGA Authorization Architecture

**Author**: System
**Last Updated**: 2026-01-03
**Status**: Active
**Related ADRs**: ADR-0002 (OpenFGA Authorization), ADR-0039 (Permission Inheritance), ADR-0068 (Gateway Auth), ADR-0086 (Security Audit)

---

## Overview

This document provides comprehensive documentation for the OpenFGA authorization architecture in MCP Server LangGraph. It covers the authorization model schema, relationship patterns, integration points, and best practices.

## Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Request Flow                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Client ──▶ Keycloak (AuthN) ──▶ API Gateway ──▶ FastAPI           │
│                                        │                             │
│                                        ▼                             │
│                                   OpenFGA (AuthZ)                    │
│                                        │                             │
│                                        ▼                             │
│                              check_permission()                      │
│                                        │                             │
│                              ┌─────────┴─────────┐                   │
│                              ▼                   ▼                   │
│                           ALLOW              DENY                    │
│                              │                   │                   │
│                              ▼                   ▼                   │
│                         Resource             HTTP 403                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Authorization Model Schema

The OpenFGA model is defined in `config/openfga/model.json` and contains **28 resource types** with their relations.

### Core Types and Relations

| Type | Description | Relations |
|------|-------------|-----------|
| `user` | Base user type | None (referenced by other types) |
| `organization` | Multi-tenant organizations | `member`, `admin` |
| `project` | Unified workspace container | `owner`, `editor`, `viewer`, `executor` |
| `workflow` | LangGraph workflow definitions | `owner`, `editor`, `viewer`, `executor` |
| `session` | Workflow execution instances | `owner`, `editor`, `viewer` |
| `conversation` | Chat conversations | `owner`, `viewer`, `editor` |
| `tool` | MCP tools | `owner`, `executor`, `organization` |

### Observability Types

| Type | Description | Relations |
|------|-------------|-----------|
| `observability` | Traces, metrics, logs access | `admin`, `viewer`, `organization` |
| `cost` | Cost tracking and analysis | `admin`, `viewer`, `organization` |
| `dashboard` | Grafana dashboards | `admin`, `editor`, `viewer`, `organization` |
| `logs` | Loki log access | `admin`, `viewer` |
| `traces` | Tempo trace access | `admin`, `viewer` |
| `metrics` | Mimir metrics access | `admin`, `viewer` |

### Infrastructure Types

| Type | Description | Relations |
|------|-------------|-----------|
| `gateway` | Traefik dashboard access | `admin`, `viewer` |
| `identity` | Keycloak management | `admin`, `viewer` |
| `authz` | OpenFGA playground | `admin`, `viewer` |
| `config` | System configuration | `admin`, `viewer` |

### Feature Types

| Type | Description | Relations |
|------|-------------|-----------|
| `mcp_connection` | MCP WebSocket connections | `owner`, `viewer` |
| `connection` | MCP server integrations | `owner`, `viewer`, `organization` |
| `agent` | Agent configuration/HITL | `owner`, `admin`, `viewer`, `organization` |
| `ai` | AI features and suggestions | `user`, `admin`, `viewer` |
| `budget` | Cost limits and alerts | `admin`, `viewer`, `organization` |
| `skill` | Skill management | `admin`, `viewer` |
| `execution` | Workflow execution tracking | `owner`, `viewer`, `organization` |
| `compliance` | GDPR/HIPAA/SOC2 reports | `admin`, `viewer` |
| `marketplace` | Marketplace admin | `admin` |

---

## Relationship Patterns

### 1. Direct Assignment

The simplest pattern - user is directly assigned a relation to a resource.

```
user:alice -> viewer -> conversation:conv-123
```

**Check**: `check_permission(user="user:alice", relation="viewer", object="conversation:conv-123")`

### 2. Computed Relations (Inheritance)

Relations that inherit from other relations. For example, `owner` implies `viewer`:

```json
"viewer": {
  "union": {
    "child": [
      {"this": {}},
      {"computedUserset": {"relation": "owner"}}
    ]
  }
}
```

**Effect**: If Alice is `owner` of a conversation, she automatically has `viewer` access.

### 3. Organizational Membership Inheritance

Resources can inherit access from organization membership:

```json
"viewer": {
  "union": {
    "child": [
      {"this": {}},
      {"computedUserset": {"relation": "editor"}},
      {
        "tupleToUserset": {
          "tupleset": {"relation": "organization"},
          "computedUserset": {"relation": "member"}
        }
      }
    ]
  }
}
```

**Effect**: If a workflow belongs to Organization A, all members of Organization A can view it.

### 4. Project-Based Inheritance

Resources in a project inherit from project permissions:

```json
"editor": {
  "union": {
    "child": [
      {"this": {}},
      {"computedUserset": {"relation": "owner"}},
      {
        "tupleToUserset": {
          "tupleset": {"relation": "project"},
          "computedUserset": {"relation": "editor"}
        }
      }
    ]
  }
}
```

**Effect**: If Alice is an `editor` of Project X, she can edit all workflows/sessions in that project.

---

## Integration with Application

### OpenFGA Client (`auth/openfga.py`)

The main integration point is the `OpenFGAClient` class:

```python
from mcp_server_langgraph.auth.openfga import get_openfga_client

openfga = await get_openfga_client()

# Check permission (with resilience)
allowed = await openfga.check_permission(
    user="user:alice",
    relation="viewer",
    object="session:session-123"
)
```

### Resilience Features

The `check_permission` method includes:

1. **Circuit Breaker**: Opens after 10 failures, 30s timeout
2. **Retry Logic**: 3 attempts with exponential backoff
3. **Timeout**: 5s for auth operations
4. **Bulkhead**: Max 50 concurrent auth checks
5. **Caching**: Redis-backed with 60s TTL

```python
@circuit_breaker(name="openfga", fail_max=10, timeout=30)
@retry_with_backoff()
@with_timeout(operation_type="auth")
@with_bulkhead(resource_type="openfga")
async def check_permission(
    self, user: str, relation: str, object: str,
    context: dict | None = None, critical: bool = True
) -> bool:
```

### Fail-Closed vs Fail-Open

- **Critical resources** (default): Fail-closed (deny on OpenFGA failure)
- **Non-critical resources**: Fail-open (allow on OpenFGA failure)

```python
# Critical: Fail-closed (security-sensitive)
await openfga.check_permission(user, "executor", "tool:dangerous", critical=True)

# Non-critical: Fail-open (observability)
await openfga.check_permission(user, "viewer", "logs:app", critical=False)
```

---

## WebSocket Authorization

WebSocket endpoints use the same authorization patterns:

```python
# From websocket/handlers/cost_tracking.py
handler = CostTrackingHandler(
    config=WebSocketConfig(
        endpoint_name="cost-tracking",
        require_auth=True,
        authz_resource_type="cost",
        authz_resource_id="usage",
        authz_required_relation="viewer",
    ),
    cost_service=cost_service,
)
```

### Authorization Matrix (WebSocket Endpoints)

| Endpoint | Resource Type | Resource ID | Required Relation |
|----------|---------------|-------------|-------------------|
| `/ws/cost-tracking` | `cost` | `usage` | `viewer` |
| `/ws/heart-metrics` | `observability` | `heart` | `viewer` |
| `/ws/connections-realtime` | `mcp_connection` | `health` | `viewer` |
| `/ws/orchestrator/status` | `ai` | `orchestrator` | `viewer` |
| `/ws/notifications` | `user` | `{user_id}` | `viewer` |
| `/ws/hitl-workflow` | `agent` | `hitl` | `editor` |
| `/ws/audit-logs` | `compliance` | `audit` | `viewer` |
| `/ws/dashboard-alerts` | `dashboard` | `alerts` | `admin` |

---

## Organization Access Patterns

### Organization Switch (`api/v1/auth.py:1616`)

When a user switches organizations:

```python
# Check if user has membership
has_access = await openfga_client.check_permission(
    user=user_id,
    relation="member",
    object=f"organization:{org_id}",
)

if not has_access:
    # Also check admin access
    has_access = await openfga_client.check_permission(
        user=user_id,
        relation="admin",
        object=f"organization:{org_id}",
    )

if not has_access:
    raise HTTPException(status_code=403, detail="Not authorized")
```

### Creating Relationship Tuples

```python
# Add user to organization
await openfga.write_tuple(
    user="user:alice",
    relation="member",
    object="organization:org-123"
)

# Make user workflow owner
await openfga.write_tuple(
    user="user:alice",
    relation="owner",
    object="workflow:workflow-456"
)

# Link workflow to organization
await openfga.write_tuple(
    user="organization:org-123",
    relation="organization",
    object="workflow:workflow-456"
)
```

---

## Testing Authorization

### Unit Tests

Use `pytest.mark.xdist_group` for memory safety:

```python
@pytest.mark.xdist_group(name="openfga")
class TestOpenFGAAuthorization:
    def teardown_method(self):
        gc.collect()

    @pytest.mark.asyncio
    async def test_viewer_access_allowed(self):
        # Mock OpenFGA client
        mock_client = AsyncMock()
        mock_client.check_permission.return_value = True

        # Test authorization check
        result = await mock_client.check_permission(
            user="user:alice",
            relation="viewer",
            object="session:123"
        )
        assert result is True
```

### Integration Tests

```python
# tests/integration/test_openfga_client.py
@pytest.mark.integration
@pytest.mark.openfga
async def test_check_permission_with_real_openfga():
    client = await get_openfga_client()

    # Seed test data
    await client.write_tuple("user:test", "member", "organization:test-org")

    # Check permission
    result = await client.check_permission(
        user="user:test",
        relation="member",
        object="organization:test-org"
    )
    assert result is True
```

---

## Best Practices

### 1. Use Consistent User Identifiers

```python
# Good: Prefixed identifiers
user = f"user:{keycloak_user_id}"
object = f"session:{session_id}"

# Bad: Raw identifiers
user = keycloak_user_id  # Missing prefix
```

### 2. Handle Authorization Failures Gracefully

```python
try:
    allowed = await openfga.check_permission(user, relation, object)
except CircuitBreakerOpenError:
    # Log and deny (fail-closed)
    logger.warning("OpenFGA circuit breaker open")
    allowed = False
```

### 3. Cache Authorization Decisions

The client automatically caches results in Redis for 60 seconds. Invalidate on permission changes:

```python
# After updating permissions
await cache.adelete(f"authz:{user}:{relation}:{object}")
```

### 4. Audit Authorization Decisions

```python
logger.info(
    "Permission check",
    extra={
        "user": user,
        "relation": relation,
        "object": object,
        "allowed": allowed,
        "latency_ms": latency
    }
)
```

---

## Monitoring

### Metrics

- `openfga_check_latency_seconds`: Authorization check latency
- `openfga_check_total`: Total checks by result (allow/deny)
- `openfga_cache_hits`: Cache hit rate
- `openfga_circuit_breaker_state`: Circuit breaker state

### Dashboards

- **Grafana**: `monitoring/grafana/dashboards/Auth/openfga.json`
- **Helm**: `deployments/helm/mcp-server-langgraph/dashboards/openfga.json`

---

## Troubleshooting

### Common Issues

1. **Permission Denied When Expected Allowed**
   - Check user identifier format: `user:{id}`
   - Verify relationship tuple exists
   - Check organization/project inheritance chain

2. **High Latency**
   - Check Redis cache health
   - Verify circuit breaker is not in half-open state
   - Check OpenFGA server load

3. **Circuit Breaker Open**
   - OpenFGA server may be down
   - Check network connectivity
   - Review error logs for root cause

### Debugging Commands

```bash
# Check OpenFGA health
curl http://localhost:8080/healthz

# List tuples for a user
curl -X POST http://localhost:8080/stores/{store_id}/read \
  -H "Content-Type: application/json" \
  -d '{"tuple_key": {"user": "user:alice"}}'
```

---

## Related Documentation

- [ADR-0002: OpenFGA Authorization](../adr/adr-0002-openfga-authorization.md)
- [ADR-0039: Permission Inheritance](../adr/adr-0039-openfga-permission-inheritance.md)
- [ADR-0068: Gateway Auth](../adr/adr-0068-gateway-level-authentication.md)
- [ADR-0086: Security Audit](../adr/adr-0086-security-audit-keycloak-openfga.md)
- [WEBSOCKET_STANDARDIZATION.md](./WEBSOCKET_STANDARDIZATION.md) - WebSocket authorization patterns
