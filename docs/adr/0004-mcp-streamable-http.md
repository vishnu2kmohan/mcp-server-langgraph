# 4. MCP StreamableHTTP Transport Protocol

Date: 2025-10-11

## Status

Accepted

## Context

The Model Context Protocol (MCP) needs a transport layer to communicate between clients and servers. The original MCP specification supported two transports:

1. **stdio**: Standard input/output (pipes)
2. **SSE (Server-Sent Events)**: HTTP-based streaming

However, the MCP specification evolved to introduce **StreamableHTTP**, which offers significant improvements over SSE:
- True bidirectional communication
- Better error handling
- More efficient streaming
- Modern HTTP semantics
- Broader client support

Use cases for different transports:
- **stdio**: Claude Desktop app, local CLI tools
- **StreamableHTTP**: Web clients, cloud deployments, production services
- **SSE (deprecated)**: Legacy clients only

We need to choose which transport(s) to support as our primary production interface.

## Decision

We will support **three MCP server implementations**:

1. **mcp_server_streamable.py** (PRIMARY - StreamableHTTP)
   - Modern StreamableHTTP transport
   - Production-recommended
   - Full HTTP features (CORS, auth headers, rate limiting)
   - Port 8000

2. **mcp_server.py** (stdio)
   - For Claude Desktop integration
   - Local development tool
   - No network overhead

3. **mcp_server_http.py** (SSE - DEPRECATED)
   - Backwards compatibility only
   - Legacy client support
   - Will be removed in future version

**Default**: StreamableHTTP for all production deployments

## Consequences

### Positive Consequences

- **Future-Proof**: Aligned with latest MCP specification
- **Better Streaming**: More efficient than SSE
- **Bidirectional**: Client can stream to server
- **Standard HTTP**: Works with existing HTTP infrastructure
- **Cloud-Ready**: Ideal for Kubernetes/Docker deployments
- **Health Checks**: Built-in `/health` endpoints
- **API Docs**: FastAPI auto-generates OpenAPI docs
- **Flexibility**: Multiple transports for different use cases

### Negative Consequences

- **Multiple Servers**: Three separate server files to maintain
- **Confusion**: Users must choose correct server
- **SSE Deprecation Path**: Need migration plan for SSE users
- **Documentation**: Must explain when to use each transport

### Neutral Consequences

- **Code Duplication**: Some shared logic across servers (mitigated with imports)
- **Testing**: Must test all three transports

## Alternatives Considered

### 1. stdio Only

**Description**: Only support stdio transport

**Pros**:
- Simplest implementation
- Perfect for Claude Desktop
- No network complexity
- Lowest latency

**Cons**:
- Can't deploy to cloud
- No web client support
- No remote access
- Not scalable

**Why Rejected**: Insufficient for production deployments

### 2. SSE Only

**Description**: Only support SSE transport

**Pros**:
- HTTP-based
- Good browser support
- Simpler than bidirectional

**Cons**:
- Deprecated in MCP spec
- Unidirectional only
- Less efficient
- Not future-proof

**Why Rejected**: MCP spec moved away from SSE

### 3. WebSocket

**Description**: Use WebSocket instead of StreamableHTTP

**Pros**:
- Truly bidirectional
- Real-time
- Efficient

**Cons**:
- Not in MCP specification
- More complex protocol
- Harder to debug
- Connection management overhead

**Why Rejected**: Not part of MCP standard

### 4. gRPC

**Description**: Use gRPC for transport

**Pros**:
- Very efficient
- Bidirectional streaming
- Type-safe

**Cons**:
- Not in MCP spec
- Complex setup
- Poor browser support
- Requires protobuf

**Why Rejected**: Incompatible with MCP spec

### 5. Single Unified Server

**Description**: One server supporting multiple transports

**Pros**:
- Single codebase
- Easier to maintain
- Less confusion

**Cons**:
- Complex implementation
- Port conflicts
- Harder to configure
- Mixed concerns

**Why Rejected**: Cleaner to separate by transport

## Implementation Details

### StreamableHTTP Server (Primary)

```python
# mcp_server_streamable.py
app = FastAPI(title="MCP Server with LangGraph")

@app.post("/mcp")
async def handle_mcp_request(request: Request):
    # StreamableHTTP handler
    ...

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### stdio Server

```python
# mcp_server.py
async def main():
    server = Server("mcp-server-langgraph")
    # stdio transport
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1])
```

### SSE Server (Deprecated)

```python
# mcp_server_http.py
@app.get("/sse")
async def sse_endpoint():
    # Server-Sent Events
    # DEPRECATED: Use StreamableHTTP instead
    ...
```

### Docker Configuration

```dockerfile
# Dockerfile
CMD ["python", "mcp_server_streamable.py"]  # Default to StreamableHTTP
```

### Usage Examples

```bash
# Production: StreamableHTTP
python mcp_server_streamable.py
# → http://localhost:8000

# Claude Desktop: stdio
python mcp_server.py
# → stdio communication

# Legacy clients: SSE (deprecated)
python mcp_server_http.py
# → http://localhost:8000/sse
```

### Client Configuration

```json
// Claude Desktop config (.claude_desktop_config.json)
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["mcp_server.py"]  // stdio transport
    }
  }
}
```

## Migration Path

### Phase 1 (Current)
- All three transports supported
- StreamableHTTP recommended
- SSE marked as deprecated

### Phase 2 (6 months)
- SSE warnings in logs
- Documentation updated
- Migration guide published

### Phase 3 (12 months)
- Remove SSE server
- Only StreamableHTTP + stdio

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Transport Documentation](https://spec.modelcontextprotocol.io/specification/architecture/#transports)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Related Files: `mcp_server_streamable.py`, `mcp_server.py`, `mcp_server_http.py`
- Related ADRs: [0008 - OpenAPI Validation](future ADR for API contracts)
