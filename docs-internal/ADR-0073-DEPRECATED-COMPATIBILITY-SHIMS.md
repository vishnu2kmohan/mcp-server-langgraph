# ADR-0073: Deprecated Compatibility Shims (v3.0 → v4.0 Migration)

**Status**: Accepted
**Date**: 2025-12-22
**Authors**: Claude Code Session (mcp-server-langgraph-session-20251208-224026)
**Supersedes**: N/A
**Related**: ADR-0072 (Anthropic Best Practices)

## Context

During the v2.0 → v3.0 migration, WebSocket handlers were reorganized from scattered `api/v1/*_websocket.py` modules into a centralized `websocket/` package. Additionally, a new `hitl/` (Human-in-the-Loop) module was created to consolidate HITL-related logic.

To maintain backward compatibility during the transition, **compatibility shims** were introduced in the original file locations. These shims:
1. Issue `DeprecationWarning` on import
2. Re-export symbols from new locations
3. Maintain API parity for tests and external consumers

**All shims are scheduled for removal in v4.0.**

## Decision

Document all deprecated compatibility shims and their replacements to:
1. Enable safe removal in v4.0
2. Guide developers to new module locations
3. Facilitate test migration

## Deprecated Module Shims

### WebSocket Handler Shims

| Deprecated Module | New Location | Removal Version |
|-------------------|--------------|-----------------|
| `api.v1.agent_request_websocket` | `hitl` + `websocket.handlers.agent_request` | v4.0 |
| `api.v1.alert_websocket` | `websocket.handlers.alert` | v4.0 |
| `api.v1.audit_websocket` | `websocket.handlers.audit` | v4.0 |
| `api.v1.mcp_task_websocket` | `websocket.handlers.mcp_task` | v4.0 |
| `api.v1.notification_websocket` | `websocket.handlers.notification` | v4.0 |
| `api.v1.connection_health_ws` | `websocket.handlers.connection_health` | v4.0 |
| `api.v1.workflow_execution_ws` | `websocket.handlers.workflow_execution` | v4.0 |

### Endpoint URL Shims

| Deprecated Endpoint | New Endpoint | Removal Version |
|---------------------|--------------|-----------------|
| `/api/v1/mcp/ws` | `/api/v1/ws/mcp` | v4.0 |
| `/api/v1/mcp/ws/auth` | `/api/v1/ws/mcp/auth` | v4.0 |
| `/api/v1/mcp/ws/{session_id}` | `/api/v1/ws/mcp/{session_id}` | v4.0 |
| `/api/v1/ws/alerts/alerts` | `/api/v1/ws/alerts` | v4.0 |
| `/api/v1/audit/stream` | `/api/v1/ws/audit` | v4.0 |
| `/api/v1/ws/connection-health` | `/api/v1/ws/connections/health` | v4.0 |

### Data Field Shims

| Module | Deprecated Field | New Field | Removal Version |
|--------|------------------|-----------|-----------------|
| `api.v1.sessions.SessionCreate` | `title` | `name` | v4.0 |

## Symbol Re-exports

Each shim module re-exports symbols from new locations for backward compatibility:

### agent_request_websocket.py
```python
# From mcp_server_langgraph.hitl.broadcast:
- AgentRequestBroadcaster
- AgentRequestWSMessageType
- ApprovalRequiredMessage
- ApprovalUpdatedMessage
- ClarificationRequiredMessage
- ExecutionResumedMessage
- WebSocketConnection

# From mcp_server_langgraph.websocket.registry:
- get_agent_request_broadcaster
- set_agent_request_broadcaster
```

### alert_websocket.py
```python
# From mcp_server_langgraph.alerts.broadcaster:
- AlertBroadcaster

# From mcp_server_langgraph.websocket.registry:
- get_alert_broadcaster
- set_alert_broadcaster
```

### audit_websocket.py
```python
# From mcp_server_langgraph.audit.broadcast:
- AuditEventBroadcaster

# From mcp_server_langgraph.websocket.registry:
- get_audit_event_broadcaster (aliased as get_audit_broadcaster)
- set_audit_event_broadcaster (aliased as set_audit_broadcaster)
```

### connection_health_ws.py
```python
# From mcp_server_langgraph.websocket.handlers.connection_health:
- ConnectionHealthHandler

# From mcp_server_langgraph.websocket.registry:
- get_connection_health_broadcaster
```

### notification_websocket.py
```python
# From mcp_server_langgraph.notifications.broadcast:
- NotificationBroadcaster

# From mcp_server_langgraph.websocket.registry:
- get_notification_broadcaster
```

### workflow_execution_ws.py
```python
# From mcp_server_langgraph.websocket.handlers.workflow_execution:
- WorkflowExecutionHandler
```

## Migration Guide

### For Test Authors

**Before (deprecated):**
```python
from mcp_server_langgraph.api.v1.agent_request_websocket import (
    AgentRequestBroadcaster,
    get_agent_request_broadcaster,
)
```

**After (v3.0+):**
```python
from mcp_server_langgraph.hitl.broadcast import AgentRequestBroadcaster
from mcp_server_langgraph.websocket.registry import get_agent_request_broadcaster
```

### For API Consumers

**Before (deprecated):**
```
ws://localhost:8000/api/v1/mcp/ws
```

**After (v3.0+):**
```
ws://localhost:8000/api/v1/ws/mcp
```

## v4.0 Removal Checklist

Before removing these shims in v4.0:

- [ ] Search codebase for imports from deprecated modules
- [ ] Update all tests to use new imports
- [ ] Update documentation/examples
- [ ] Add migration notes to CHANGELOG
- [ ] Remove deprecated modules
- [ ] Remove deprecated API endpoints from router
- [ ] Run full test suite to verify no regressions

### Files to Delete in v4.0

```bash
# WebSocket shim modules
src/mcp_server_langgraph/api/v1/agent_request_websocket.py
src/mcp_server_langgraph/api/v1/alert_websocket.py
src/mcp_server_langgraph/api/v1/audit_websocket.py
src/mcp_server_langgraph/api/v1/mcp_task_websocket.py
src/mcp_server_langgraph/api/v1/notification_websocket.py
src/mcp_server_langgraph/api/v1/connection_health_ws.py
src/mcp_server_langgraph/api/v1/workflow_execution_ws.py
```

## Consequences

### Positive
- Clear documentation of migration path
- Backward compatibility maintained during transition
- Deprecation warnings alert developers to pending changes

### Negative
- Maintaining shim modules increases codebase size
- Potential confusion between old and new locations
- Type checking complexity with re-exports

### Neutral
- Shims will be completely removed in v4.0
- No performance impact (shims are thin wrappers)

## References

- [Python warnings module](https://docs.python.org/3/library/warnings.html)
- [PEP 565 - DeprecationWarning visibility](https://peps.python.org/pep-0565/)
- Project `websocket/` module structure
- Project `hitl/` module structure
