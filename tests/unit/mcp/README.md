# MCP Unit Tests

Tests for `src/mcp_server_langgraph/mcp/` package.

## Namespace Collision Warning

**CRITICAL: Do NOT create `__init__.py` files in this directory or subdirectories.**

### Why?

The `mcp` package name conflicts with the installed MCP SDK (Model Context Protocol):

- **Installed SDK**: `mcp` package from PyPI (`mcp.server`, `mcp.types`, etc.)
- **This directory**: `tests/unit/mcp/` for testing our internal `mcp_server_langgraph.mcp`

If `tests/unit/mcp/__init__.py` exists, Python's import resolution may:
1. Treat `tests/unit/mcp/` as a package
2. Resolve `import mcp.server` to the test directory (WRONG!)
3. Cause `ImportError: No module named 'mcp.server'`

### Symptoms

- Tests pass individually but fail when run together
- `ModuleNotFoundError: No module named 'mcp.server'`
- `TextContent` becomes `MagicMock` instead of real type

### Prevention

1. **Validation Hook**: `check-mcp-namespace-collision` pre-commit hook
   - Blocks commits adding `__init__.py` to this directory
   - Run: `python scripts/validators/check_mcp_namespace_collision.py`

2. **SDK Check in conftest.py**: `tests/unit/mcp/client/conftest.py`
   - Checks if real MCP SDK is available before injecting mocks
   - Prevents mock pollution when SDK is installed

### Why Not Rename the Directory?

We evaluated renaming to `tests/unit/mcp_pkg/` to avoid collision entirely.

**Decision: Keep `tests/unit/mcp/`**

Rationale:
- 46 test files would need to move
- Validation hook prevents regression
- Conftest properly handles SDK availability
- Directory mirrors source structure (`src/mcp_server_langgraph/mcp/`)

### Directory Structure

```
tests/unit/mcp/
├── client/           # Tests for mcp_server_langgraph.mcp.client
│   └── conftest.py   # SDK mock injection (with availability check)
├── handlers/         # Tests for mcp_server_langgraph.mcp.handlers
├── websocket/        # Tests for mcp_server_langgraph.mcp.websocket
└── README.md         # This file
```

### See Also

- ADR-0073: MCP WebSocket Migration
- `scripts/validators/check_mcp_namespace_collision.py`
- `tests/unit/mcp/client/conftest.py` (SDK Mock Pattern documentation)
