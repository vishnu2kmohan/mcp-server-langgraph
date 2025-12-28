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
| `api.v1.notification_websocket` | `websocket.handlers.notifications` | **REMOVED** (2025-12-28) |
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

### notification_websocket.py (**REMOVED** 2025-12-28)

> **This shim has been removed.** Use the new locations directly:
>
> ```python
> from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
> from mcp_server_langgraph.websocket.registry import get_notification_broadcaster
> ```

### mcp_websocket.py (Partial Migration 2025-12-28)

MCP-specific classes have been migrated to a new `mcp/websocket/` package:

| Class | Old Location | New Location |
|-------|--------------|--------------|
| `ConnectionManager` | `api.v1.mcp_websocket` | `mcp.websocket.connection_manager` |
| `StreamingToolCallHandler` | `api.v1.mcp_websocket` | `mcp.websocket.streaming` |
| `StreamingMetricsCollector` | `api.v1.mcp_websocket` | `mcp.websocket.streaming` |
| `MCPWebSocketLifecycleManager` | `api.v1.mcp_websocket` | `mcp.websocket.lifecycle` |
| `OTelMCPMetrics` | `api.v1.mcp_websocket` | `mcp.websocket.metrics` |
| `UserRateLimiterManager` | `api.v1.mcp_websocket` | `mcp.websocket.rate_limiter` |
| `OutboundRateLimiter` | `api.v1.mcp_websocket` | `mcp.websocket.rate_limiter` |

The `mcp_websocket.py` shim uses `__getattr__` for lazy imports with `DeprecationWarning`:

```python
from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager  # Issues warning
# DeprecationWarning: ConnectionManager has moved to mcp_server_langgraph.mcp.websocket.connection_manager
```

**New imports (preferred):**
```python
from mcp_server_langgraph.mcp.websocket import ConnectionManager
from mcp_server_langgraph.mcp.websocket import StreamingToolCallHandler
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
# src/mcp_server_langgraph/api/v1/notification_websocket.py  # DELETED 2025-12-28
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

## Test Namespace Collision Fix (2025-12-28)

### Problem

The `tests/unit/mcp/` directory name collides with the installed `mcp` SDK package (Model Context Protocol). When `tests/unit/mcp/__init__.py` exists, Python's import system may resolve `import mcp.server` to the test directory instead of the installed package, causing:

- `ImportError: No module named 'mcp.server'`
- Tests pass individually but fail when run together
- Mock pollution from `conftest.py` affecting unrelated tests

### Root Cause

`tests/unit/mcp/client/conftest.py` injected mock modules into `sys.modules` at import time:

```python
# BEFORE (problematic)
if "mcp" not in sys.modules:
    sys.modules["mcp"] = _create_mcp_module()  # Pollutes when SDK not yet imported
```

Combined with `tests/unit/mcp/__init__.py`, this caused Python to treat the test directory as the `mcp` package.

### Solution

1. **Deleted `__init__.py` files** that caused namespace collision:
   - `tests/unit/mcp/__init__.py`
   - `tests/unit/mcp/client/__init__.py`

2. **Added SDK availability check** in `tests/unit/mcp/client/conftest.py`:
   ```python
   # AFTER (safe)
   try:
       from mcp.types import TextContent
       _MCP_SDK_AVAILABLE = True
   except ImportError:
       _MCP_SDK_AVAILABLE = False

   if not _MCP_SDK_AVAILABLE:
       if "mcp" not in sys.modules:
           sys.modules["mcp"] = _create_mcp_module()
   ```

3. **Added validation hook** (`scripts/validators/check_mcp_namespace_collision.py`):
   - Pre-commit hook blocks `__init__.py` in `tests/unit/mcp/`
   - Provides clear error message explaining the issue

4. **Added documentation**:
   - `tests/unit/mcp/README.md` - Documents the issue and prevention
   - `tests/unit/mcp/client/conftest.py` - Enhanced docstring explaining SDK Mock Pattern

### Prevention

The `check-mcp-namespace-collision` pre-commit hook prevents regression:

```yaml
- id: check-mcp-namespace-collision
  name: Check MCP Namespace Collision
  entry: uv run --frozen python -u scripts/validators/check_mcp_namespace_collision.py
  files: ^tests/unit/mcp/.*__init__\.py$
```

### Directory Rename Evaluation

We evaluated renaming `tests/unit/mcp/` to `tests/unit/mcp_pkg/` to eliminate collision entirely.

**Decision: Keep `tests/unit/mcp/`**

| Factor | Keep Current | Rename |
|--------|--------------|--------|
| Files affected | 0 | 46 test files |
| Collision risk | Mitigated by hook | Eliminated |
| Maintenance | Validation hook | None |

The validation hook and SDK availability check provide sufficient protection without requiring a large refactor.

## References

- [Python warnings module](https://docs.python.org/3/library/warnings.html)
- [PEP 565 - DeprecationWarning visibility](https://peps.python.org/pep-0565/)
- Project `websocket/` module structure
- Project `hitl/` module structure
- `scripts/validators/check_mcp_namespace_collision.py` - Validation hook
- `tests/unit/mcp/README.md` - Test directory documentation
