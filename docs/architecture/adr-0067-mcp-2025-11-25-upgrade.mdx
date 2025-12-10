# ADR-0067: MCP Specification Upgrade to 2025-11-25

## Status

Accepted

## Date

2025-12-10

## Context

The Model Context Protocol (MCP) specification was updated to version 2025-11-25, introducing several new features and improvements. Our mcp-server-langgraph implementation needed to upgrade from the previous 2025-06-18 specification to support the latest capabilities.

Key drivers for this upgrade:
1. SDK compatibility with MCP Python SDK 1.23.3+
2. Enhanced elicitation with enumNames and defaults (SEP-1330)
3. Sampling with tool definitions for agentic loops (SEP-1577)
4. Improved error handling for tool validation (SEP-1303)
5. Icons metadata for better UI rendering (SEP-973)
6. URL mode elicitation for OAuth flows (SEP-1036)
7. Tasks feature for long-running operations (SEP-1686)

## Decision

We will upgrade the MCP implementation to support all major features of the 2025-11-25 specification.

### Implemented Features

| Feature | SEP | Status | Description |
|---------|-----|--------|-------------|
| Protocol Version | - | Done | Updated to 2025-11-25 |
| SDK Version | - | Done | Upgraded to mcp>=1.23.3 |
| Sampling with Tools | SEP-1577 | Done | `tools` and `toolChoice` params |
| Enhanced Enum Schema | SEP-1330 | Done | `enumNames`, `default` values |
| Tool Validation Errors | SEP-1303 | Done | Return as Tool Errors |
| Icons Metadata | SEP-973 | Done | Icons for tools/resources/prompts |
| URL Mode Elicitation | SEP-1036 | Done | OAuth credential collection |
| HTTP 403 Origin | - | Done | Origin header validation |
| Tasks | SEP-1686 | Done | Long-running operation tracking |
| MCP Metrics | - | Done | Prometheus metrics integration |

### Files Modified/Created

#### New Python Modules
- `src/mcp_server_langgraph/mcp/tasks.py` - SEP-1686 Tasks implementation
- `src/mcp_server_langgraph/mcp/icons.py` - SEP-973 Icons implementation
- `src/mcp_server_langgraph/mcp/tool_errors.py` - SEP-1303 Validation errors
- `src/mcp_server_langgraph/mcp/origin_validation.py` - HTTP 403 Origin validation
- `src/mcp_server_langgraph/mcp/metrics.py` - Prometheus metrics

#### Modified Python Modules
- `src/mcp_server_langgraph/mcp/sampling.py` - SEP-1577 tools/toolChoice
- `src/mcp_server_langgraph/mcp/elicitation.py` - SEP-1330 enumNames, SEP-1036 URL mode

#### TypeScript Updates
- `playground/frontend/src/api/mcp-types.ts` - All new type definitions

#### Tests
- 90+ new unit tests covering all features
- Located in `tests/unit/mcp/test_*.py`

### Deferred Features

| Feature | Reason |
|---------|--------|
| Enterprise XAA Authorization | Requires additional Keycloak configuration |
| Code Execution with Tasks | Integration pending |
| LLM Fallback via Sampling | Integration pending |
| Enhanced Approval Elicitation | Integration pending |

## Consequences

### Positive

1. **Future Compatibility**: Server is compatible with MCP 2025-11-25 clients
2. **Enhanced UX**: Icons and enumNames provide better user experience
3. **Better Error Handling**: Tool validation errors are more user-friendly
4. **Long-Running Operations**: Tasks feature enables complex workflows
5. **Observability**: Prometheus metrics for MCP operations
6. **OAuth Support**: URL mode elicitation enables OAuth flows

### Negative

1. **SDK Dependency**: Requires mcp>=1.23.3
2. **Breaking Change**: Clients must support 2025-11-25 protocol

### Neutral

1. **Backward Compatibility**: New features are additive; older clients degrade gracefully
2. **Testing Overhead**: 90+ new tests added to maintain quality

## References

- [MCP 2025-11-25 Changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog)
- [MCP Python SDK 1.23.3](https://github.com/modelcontextprotocol/python-sdk/releases)
- [One Year of MCP Blog Post](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)

## Related ADRs

- ADR-0004: MCP Streamable HTTP Transport
