# 82. MCP Client Capabilities

Date: 2025-12-21

## Status

Proposed

## Category

Architecture & Integration (CRITICAL)

## Context

A multi-framework audit comparing mcp-server-langgraph against Claude Agent SDK, Google ADK, and OpenAI Agents SDK identified a **critical gap**: while we provide an MCP server for clients to consume, we lack MCP **client** capabilities to consume external MCP servers' tools.

**Current Architecture (MCP Server Only)**:
```
External Clients → MCP Protocol → Our Server → LangGraph Agents
                                      ↑
                            We are HERE (server only)
```

**Required Architecture (MCP Server + Client)**:
```
External Clients → MCP Protocol → Our Server → LangGraph Agents
                                                      ↓
                                              MCP Client Layer
                                                      ↓
                                        External MCP Servers (Playwright, GitHub, etc.)
```

**Framework Comparison - MCP Capabilities**:

| Framework | MCP Role | How It Works |
|-----------|----------|--------------|
| Claude Agent SDK | Consumer | `mcp_servers={"name": {"command": "...", "args": [...]}}` |
| Google ADK | Both | `McpToolset(...)` connects to servers, imports tools |
| OpenAI Agents SDK | Consumer | `mcp_servers=[server1, server2]` attaches servers |
| **mcp-server-langgraph** | Provider only | We expose tools, cannot consume external |

**What We Have**:
- ✅ Full MCP server implementation (we expose tools via MCP protocol)
- ✅ MCPClient class for testing connections
- ✅ ConnectionRepository for OAuth2/credential management
- ❌ **MCP Tool Import** (consume external MCP server tools)
- ❌ **MCP Tool Registry** (track tools from multiple servers)
- ❌ **MCP Tool Proxy** (adapt MCP tools → LangChain BaseTool)
- ❌ **MCP Executor** (route tool calls to external servers)

**Why This Matters**:
Without MCP client capabilities, our Multi-Agent Orchestrator cannot:
1. Use tools from external MCP servers (Playwright, GitHub, Slack, etc.)
2. Dynamically expand tool availability without code changes
3. Integrate with the growing MCP ecosystem
4. Achieve parity with other agent frameworks

## Decision

Implement comprehensive MCP client capabilities enabling our agents to consume tools from external MCP servers.

### Core Components

#### 1. MCPToolRegistry

**Purpose**: Track and manage tools from multiple external MCP servers.

**Implementation**: `src/mcp_server_langgraph/mcp/client/tool_registry.py`

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MCPToolDefinition:
    """Definition of a tool from an external MCP server."""
    server_name: str
    name: str
    description: str
    input_schema: dict[str, Any]
    qualified_name: str = field(init=False)

    def __post_init__(self):
        self.qualified_name = f"{self.server_name}:{self.name}"

@dataclass
class MCPServerConfig:
    """Configuration for connecting to an external MCP server."""
    name: str
    command: str | None = None        # For stdio transport
    args: list[str] | None = None
    url: str | None = None            # For HTTP/SSE transport
    env: dict[str, str] | None = None
    auth: dict[str, Any] | None = None
    timeout: float = 30.0
    tool_allowlist: list[str] | None = None  # Only expose these tools
    tool_blocklist: list[str] | None = None  # Hide these tools

class MCPToolRegistry:
    """Registry for tools from external MCP servers."""

    def __init__(self):
        self._servers: dict[str, MCPClientSession] = {}
        self._tools: dict[str, MCPToolDefinition] = {}
        self._server_tools: dict[str, list[str]] = {}

    async def register_server(
        self,
        config: MCPServerConfig,
    ) -> list[MCPToolDefinition]:
        """Register an MCP server and import its tools."""
        ...

    async def unregister_server(self, name: str) -> None:
        """Disconnect from an MCP server and remove its tools."""
        ...

    def get_tools(
        self,
        server_name: str | None = None,
    ) -> list[MCPToolDefinition]:
        """Get all tools or tools from a specific server."""
        ...

    async def refresh_tools(self, server_name: str) -> list[MCPToolDefinition]:
        """Refresh tool list from a server."""
        ...

    def get_tool(self, qualified_name: str) -> MCPToolDefinition | None:
        """Get a specific tool by qualified name (server:tool)."""
        ...
```

#### 2. MCPToolProxy

**Purpose**: Wrap external MCP tools as LangChain BaseTool for agent use.

**Implementation**: `src/mcp_server_langgraph/mcp/client/tool_proxy.py`

```python
from langchain_core.tools import BaseTool
from pydantic import Field
from typing import Any

class MCPToolProxy(BaseTool):
    """Proxy that wraps an external MCP tool as a LangChain BaseTool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    mcp_server: str = Field(description="Source MCP server name")
    mcp_tool_name: str = Field(description="Original tool name on server")
    args_schema: type = Field(description="Pydantic model for arguments")
    executor: "MCPExecutor" = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    async def _arun(self, **kwargs: Any) -> str:
        """Execute the tool via MCP protocol."""
        return await self.executor.call_tool(
            server=self.mcp_server,
            tool=self.mcp_tool_name,
            arguments=kwargs,
        )

    def _run(self, **kwargs: Any) -> str:
        """Synchronous execution (not recommended)."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._arun(**kwargs)
        )
```

#### 3. MCPExecutor

**Purpose**: Route tool calls to external MCP servers with resilience.

**Implementation**: `src/mcp_server_langgraph/mcp/client/executor.py`

```python
from typing import Any
from dataclasses import dataclass

@dataclass
class MCPToolCall:
    """A tool call to execute on an MCP server."""
    server: str
    tool: str
    arguments: dict[str, Any]
    call_id: str | None = None

@dataclass
class MCPToolResult:
    """Result from an MCP tool execution."""
    call_id: str
    success: bool
    content: Any | None = None
    error: str | None = None
    duration_ms: float = 0.0

class MCPExecutor:
    """Execute tool calls on external MCP servers."""

    def __init__(
        self,
        registry: MCPToolRegistry,
        auth_provider: AuthProvider | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.registry = registry
        self.auth_provider = auth_provider
        self.timeout = timeout
        self.max_retries = max_retries

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> Any:
        """Execute a tool on the specified MCP server."""
        ...

    async def batch_call(
        self,
        calls: list[MCPToolCall],
    ) -> list[MCPToolResult]:
        """Execute multiple tool calls in parallel."""
        ...

    async def health_check(self, server: str) -> bool:
        """Check if an MCP server is healthy."""
        ...
```

#### 4. MCPClientSession

**Purpose**: Manage connection lifecycle to a single MCP server.

**Implementation**: `src/mcp_server_langgraph/mcp/client/session_manager.py`

```python
from enum import Enum
from typing import Any

class MCPTransportType(Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"

class MCPClientSession:
    """Manages connection to a single MCP server."""

    def __init__(
        self,
        config: MCPServerConfig,
        transport_type: MCPTransportType | None = None,
    ):
        self.config = config
        self.transport_type = transport_type or self._detect_transport()
        self._connected = False
        self._tools: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        ...

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the server."""
        ...

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool on this server."""
        ...

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _detect_transport(self) -> MCPTransportType:
        """Detect transport type from config."""
        if self.config.url:
            if "ws://" in self.config.url or "wss://" in self.config.url:
                return MCPTransportType.WEBSOCKET
            return MCPTransportType.HTTP
        return MCPTransportType.STDIO
```

### Integration Points

#### Agent Config Extension

**File**: `src/mcp_server_langgraph/core/agent_config.py`

```python
class AgentConfig(BaseModel):
    # ... existing fields ...

    mcp_servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="External MCP servers whose tools are available to agents",
    )
```

#### Tool Registry Extension

**File**: `src/mcp_server_langgraph/tools/__init__.py`

```python
def get_all_tools(
    agent_config: AgentConfig | None = None,
    mcp_registry: MCPToolRegistry | None = None,
) -> list[BaseTool]:
    """Get all available tools including external MCP tools."""
    tools = _get_builtin_tools()

    if mcp_registry and agent_config:
        for server_name, config in agent_config.mcp_servers.items():
            # Get tools as LangChain BaseTools
            mcp_tools = mcp_registry.get_tools_as_langchain(server_name)
            tools.extend(mcp_tools)

    return tools
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Agent Layer                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Tool Registry                                   │ │
│  │                                                                    │ │
│  │   Built-in Tools        │      External MCP Tools (via Proxy)     │ │
│  │   ───────────────       │      ─────────────────────────────      │ │
│  │   read_file             │      playwright:screenshot              │ │
│  │   write_file            │      github:create_pr                   │ │
│  │   edit_file             │      slack:send_message                 │ │
│  │   web_search            │      filesystem:read_file               │ │
│  │   execute_python        │      ...                                │ │
│  │                                                                    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    MCP Client Layer                                │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │ MCPTool     │  │ MCPTool     │  │    MCPExecutor          │   │ │
│  │  │ Registry    │  │ Proxy       │  │    (with resilience)    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │                    Session Manager                          │  │ │
│  │  │  STDIO │ HTTP │ SSE │ WebSocket transports                  │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
         ┌──────────────────┐              ┌──────────────────┐
         │ External MCP     │              │ External MCP     │
         │ Server           │              │ Server           │
         │ (Playwright)     │              │ (GitHub)         │
         └──────────────────┘              └──────────────────┘
```

### Security Considerations

1. **Tool Allowlist/Blocklist**: Per-server control over which tools are exposed
2. **Credential Isolation**: Each server has its own auth config
3. **Rate Limiting**: Per-server rate limits
4. **Timeout Enforcement**: Configurable per-server timeouts
5. **Input Sanitization**: Validate arguments before forwarding
6. **Output Sanitization**: Validate/filter responses from external tools
7. **Transport Security**: HTTPS/WSS for network transports

### Configuration

```python
# Environment variables
MCP_CLIENT_ENABLED = True
MCP_CLIENT_DEFAULT_TIMEOUT = 30.0
MCP_CLIENT_MAX_RETRIES = 3
MCP_CLIENT_MAX_SERVERS = 20  # Limit registered servers

# Example agent config with MCP servers
agent_config = AgentConfig(
    mcp_servers={
        "playwright": MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
            tool_allowlist=["screenshot", "click", "navigate"],
        ),
        "github": MCPServerConfig(
            name="github",
            url="https://mcp.github.com/v1",
            auth={"token": "${GITHUB_TOKEN}"},
        ),
    }
)
```

### Feature Flag

| Flag | Default | Description |
|------|---------|-------------|
| `enable_mcp_client` | False | Enable external MCP tool consumption |

## Consequences

### Positive

1. **Ecosystem Access**: Agents can use any MCP-compatible tool
2. **Dynamic Tool Expansion**: Add capabilities without code changes
3. **Framework Parity**: Matches Claude SDK, Google ADK, OpenAI SDK patterns
4. **Multi-Agent Power**: Orchestrator can delegate to specialized tool servers
5. **Future-Proof**: Ready for MCP ecosystem growth

### Negative

1. **Complexity**: New infrastructure to maintain
2. **Dependencies**: Relies on external server availability
3. **Security Surface**: More external integrations = more risk
4. **Latency**: Network calls to external servers

### Neutral

1. **Feature Flagged**: Disabled by default, opt-in
2. **LLM Agnostic**: Works with any LLM via LiteLLM
3. **Backward Compatible**: Existing tools unchanged

## Implementation Plan

### TDD Test Cases (Write FIRST)

**`tests/unit/mcp/test_mcp_tool_registry.py`**:
```python
async def test_register_server_imports_tools()
async def test_unregister_server_removes_tools()
def test_get_tools_returns_all_tools()
def test_get_tools_by_server_filters_correctly()
async def test_refresh_tools_updates_tool_list()
def test_duplicate_tool_names_use_qualified_names()
def test_tool_allowlist_filters_tools()
def test_tool_blocklist_hides_tools()
```

**`tests/unit/mcp/test_mcp_tool_proxy.py`**:
```python
async def test_proxy_wraps_mcp_tool_as_langchain()
async def test_proxy_forwards_arguments_correctly()
async def test_proxy_handles_timeout()
async def test_proxy_handles_server_errors()
async def test_proxy_validates_arguments()
def test_proxy_has_correct_metadata()
```

**`tests/unit/mcp/test_mcp_executor.py`**:
```python
async def test_executor_routes_to_correct_server()
async def test_executor_handles_auth()
async def test_executor_batch_call_parallel()
async def test_executor_respects_timeout()
async def test_executor_retries_on_failure()
async def test_executor_health_check()
```

**`tests/unit/mcp/test_mcp_client_session.py`**:
```python
async def test_session_connects_via_stdio()
async def test_session_connects_via_http()
async def test_session_lists_tools()
async def test_session_calls_tool()
async def test_session_handles_disconnect()
async def test_session_detects_transport_type()
```

**`tests/integration/test_external_mcp_tools.py`**:
```python
@pytest.mark.integration
async def test_connect_to_filesystem_mcp_server()
async def test_call_tool_on_external_server()
async def test_multi_server_tool_routing()
async def test_tool_appears_in_agent_tools()
```

### Files to Create

```
src/mcp_server_langgraph/mcp/client/
├── __init__.py              # Module exports
├── session_manager.py       # MCPClientSession
├── tool_registry.py         # MCPToolRegistry, MCPServerConfig
├── tool_proxy.py            # MCPToolProxy
└── executor.py              # MCPExecutor

tests/unit/mcp/
├── test_mcp_client_session.py
├── test_mcp_tool_registry.py
├── test_mcp_tool_proxy.py
└── test_mcp_executor.py

tests/integration/
└── test_external_mcp_tools.py
```

### Files to Modify

```
src/mcp_server_langgraph/tools/__init__.py      # Extend get_all_tools()
src/mcp_server_langgraph/core/agent_config.py   # Add mcp_servers field
src/mcp_server_langgraph/core/feature_flags.py  # Add enable_mcp_client
```

## Related ADRs

- ADR-0077: Claude Agent SDK Integration (foundation patterns)
- ADR-0078: Multi-Agent Orchestrator Patterns (tool access for subagents)
- ADR-0079: Multi-Framework Tool Parity (built-in tools)
- ADR-0080: LLM-Level Callback System (hook integration)

## References

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Claude Agent SDK - MCP](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [Google ADK - MCP Tools](https://google.github.io/adk-docs/mcp/)
- [OpenAI Agents SDK - MCP](https://openai.github.io/openai-agents-python/mcp/)
