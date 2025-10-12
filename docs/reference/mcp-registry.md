# MCP Registry Deployment Guide

Complete guide for deploying LangGraph Agent to the Model Context Protocol (MCP) Registry with HTTP/SSE transport support.

## Table of Contents

- [Overview](#overview)
- [Transports](#transports)
- [Registry Manifest](#registry-manifest)
- [Publishing to Registry](#publishing-to-registry)
- [Client Configuration](#client-configuration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)

## Overview

The MCP Server with LangGraph supports multiple MCP transports:
- **stdio** (Standard Input/Output) - For local/desktop applications
- **HTTP/SSE** (Server-Sent Events) - For web applications and remote access

The agent is fully compatible with the MCP specification and can be published to any standards-compliant MCP registry.

## Transports

The agent supports three MCP transports:

1. **StreamableHTTP** (Recommended) - Modern HTTP streaming
2. **stdio** - Local/desktop applications
3. **HTTP/SSE** (Deprecated) - Legacy Server-Sent Events

### stdio Transport

**Used by:** Claude Desktop, local CLI tools

**Configuration:**
```json
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["src/mcp_server_langgraph/mcp/server_stdio.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

**Files:**
- `src/mcp_server_langgraph/mcp/server_stdio.py` - stdio transport implementation

### StreamableHTTP Transport (Recommended)

**Used by:** Web applications, remote clients, mobile apps, production deployments

**Why StreamableHTTP?**
- Modern HTTP/2+ streaming
- Better compatibility with load balancers and proxies
- Proper request/response pairs
- Native HTTP streaming without SSE limitations
- Full MCP spec compliance

**Configuration:**
```json
{
  "mcpServers": {
    "langgraph-agent": {
      "transport": "streamable-http",
      "url": "https://mcp.langgraph-agent.example.com/message",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

**Endpoints:**
- `POST /message` - Main MCP endpoint (streaming or regular)
- `GET /tools` - List available tools (convenience)
- `GET /resources` - List available resources (convenience)
- `GET /health` - Health check
- `GET /` - Server info and capabilities

**Files:**
- `src/mcp_server_langgraph/mcp/server_streamable.py` - StreamableHTTP transport implementation

**Streaming Support:**
- Set `Accept: application/x-ndjson` or `Accept: text/event-stream` for streaming responses
- Responses are newline-delimited JSON
- Works with standard HTTP infrastructure

### HTTP/SSE Transport (Deprecated)

**⚠️ This transport is deprecated in the MCP specification. Use StreamableHTTP instead.**

**Used by:** Legacy clients

**Configuration:**
```json
{
  "mcpServers": {
    "langgraph-agent": {
      "transport": "http-sse",
      "url": "https://mcp.langgraph-agent.example.com",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

**Endpoints:**
- `GET /sse` - Server-Sent Events stream
- `POST /messages` - MCP JSON-RPC messages
- `GET /tools` - List available tools
- `GET /resources` - List available resources

**Files:**
- `mcp_server_http.py` - HTTP/SSE transport implementation (legacy)

## Registry Manifest

### manifest.json

Located at `.mcp/manifest.json`, this file contains:

```json
{
  "schemaVersion": "1.0.0",
  "name": "langgraph-agent",
  "version": "1.0.0",
  "transports": {
    "stdio": {
      "command": "python",
      "args": ["src/mcp_server_langgraph/mcp/server_stdio.py"]
    },
    "http": {
      "url": "https://langgraph-agent.example.com",
      "endpoints": {
        "sse": "/sse",
        "messages": "/messages",
        "tools": "/tools",
        "resources": "/resources"
      }
    }
  },
  "capabilities": {
    "tools": {
      "listSupported": true,
      "callSupported": true
    },
    "resources": {
      "listSupported": true,
      "readSupported": true
    }
  }
}
```

**Key fields:**
- `name` - Unique identifier for the registry
- `version` - Semantic version (semver)
- `transports` - Supported transport configurations
- `capabilities` - MCP protocol capabilities
- `tools` - List of available tools with schemas
- `configuration` - Required and optional environment variables

### registry.json

Located at `.mcp/registry.json`, this file contains registry-specific metadata:

```json
{
  "schemaVersion": "1.0.0",
  "registry": {
    "name": "langgraph-agent",
    "displayName": "LangGraph AI Agent",
    "shortDescription": "Production AI agent with OpenFGA authorization"
  },
  "endpoints": {
    "production": {
      "url": "https://langgraph-agent.example.com",
      "transport": "http"
    }
  },
  "pricing": {
    "model": "tiered",
    "tiers": [...]
  }
}
```

## Publishing to Registry

### Automated Publishing

Use the provided script:

```bash
# Set registry credentials
export MCP_REGISTRY_URL="https://registry.modelcontextprotocol.io"
export MCP_REGISTRY_TOKEN="your-registry-token"

# Publish
./scripts/publish_to_registry.sh
```

**Script workflow:**
1. Validates manifest files
2. Builds package tarball
3. Uploads to registry
4. Generates registry card

### Manual Publishing

```bash
# 1. Build package
mkdir -p dist/mcp-package
cp .mcp/*.json dist/mcp-package/
cp *.py requirements.txt README.md dist/mcp-package/

# 2. Create tarball
cd dist
tar -czf langgraph-agent-1.0.0.tar.gz mcp-package/

# 3. Upload to registry
curl -X POST https://registry.modelcontextprotocol.io/api/v1/packages \
  -H "Authorization: Bearer $MCP_REGISTRY_TOKEN" \
  -F "package=@langgraph-agent-1.0.0.tar.gz" \
  -F "manifest=@../.mcp/manifest.json"
```

## Client Configuration

### Claude Desktop

**MacOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["/path/to/src/mcp_server_langgraph/mcp/server_stdio.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "OPENFGA_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Web Application (HTTP/SSE)

```javascript
// Connect to MCP server via HTTP/SSE
const mcpClient = new MCPClient({
  transport: 'http',
  url: 'https://mcp.langgraph-agent.example.com',
  headers: {
    'Authorization': 'Bearer your-jwt-token'
  }
});

// Connect to SSE stream
const eventSource = new EventSource('https://mcp.langgraph-agent.example.com/sse');

eventSource.addEventListener('connected', (event) => {
  console.log('Connected to MCP server:', event.data);
});

// Send MCP message
const response = await fetch('https://mcp.langgraph-agent.example.com/messages', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-jwt-token'
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'tools/call',
    params: {
      name: 'chat',
      arguments: {
        message: 'Hello!',
        username: 'alice'
      }
    },
    id: 1
  })
});

const result = await response.json();
console.log('Agent response:', result);
```

### Python Client (HTTP/SSE)

```python
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

async def main():
    # Connect via HTTP/SSE
    async with sse_client(
        url="https://mcp.langgraph-agent.example.com"
    ) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print("Available tools:", tools)

            # Call tool
            result = await session.call_tool(
                "chat",
                arguments={
                    "message": "Explain quantum computing",
                    "username": "alice"
                }
            )
            print("Response:", result.content[0].text)

asyncio.run(main())
```

## Testing

### Test stdio Transport

```bash
# Run server
python -m mcp_server_langgraph.mcp.server_stdio

# Test with example client
python examples/client_stdio.py
```

### Test HTTP/SSE Transport

```bash
# Run HTTP server
python mcp_server_http.py

# Test SSE connection
curl -N https://mcp.langgraph-agent.example.com/sse

# Test message endpoint
curl -X POST https://mcp.langgraph-agent.example.com/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Test tools endpoint
curl https://mcp.langgraph-agent.example.com/tools
```

### Test with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Inspect stdio server
mcp-inspector python -m mcp_server_langgraph.mcp.server_stdio

# Inspect HTTP server
mcp-inspector --transport http --url https://mcp.langgraph-agent.example.com
```

## Production Deployment

### Deploy HTTP/SSE Server to Kubernetes

```bash
# Build and push image
docker build -t your-registry/langgraph-agent:1.0.0 .
docker push your-registry/langgraph-agent:1.0.0

# Deploy with Helm
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.tag=1.0.0 \
  --set ingress.enabled=true \
  --set ingress.hosts[0]=mcp.langgraph-agent.example.com

# Apply HTTP ingress
kubectl apply -f kubernetes/base/ingress-http.yaml
```

### Configure Kong for MCP

```bash
# Apply Kong configurations with extended timeouts for SSE
kubectl apply -f kubernetes/kong/kong-ingress.yaml
```

**Key Kong settings for SSE:**
- `read-timeout: 86400000` (24 hours)
- `write-timeout: 86400000` (24 hours)
- Session affinity for SSE connections

### DNS Configuration

```
# A record for HTTP/SSE endpoint
mcp.langgraph-agent.example.com -> LoadBalancer IP

# Optional: Separate endpoints per tier
free.mcp.langgraph-agent.example.com
premium.mcp.langgraph-agent.example.com
enterprise.mcp.langgraph-agent.example.com
```

### SSL/TLS

Use cert-manager for automatic certificate provisioning:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: mcp-langgraph-agent-tls
  namespace: langgraph-agent
spec:
  secretName: langgraph-agent-http-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - mcp.langgraph-agent.example.com
```

### Health Checks

```bash
# Check service health
curl https://mcp.langgraph-agent.example.com/health

# Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "openfga": {"status": "healthy"},
    "infisical": {"status": "healthy"},
    "secrets": {"status": "healthy"}
  }
}
```

### Monitoring

**Prometheus metrics:**
```
# SSE connections
mcp_sse_connections_active{server="langgraph-agent"}

# Message throughput
mcp_messages_total{method="tools/call",status="success"}

# Tool invocations
mcp_tool_calls_total{tool="chat",status="success"}
```

**Grafana dashboard queries:**
```promql
# Active SSE connections
sum(mcp_sse_connections_active)

# Message rate
rate(mcp_messages_total[5m])

# Error rate
rate(mcp_messages_total{status="error"}[5m])
```

## Registry Compliance Checklist

- [x] **Manifest file** - `.mcp/manifest.json` with all required fields
- [x] **Registry info** - `.mcp/registry.json` with metadata
- [x] **stdio transport** - Implemented in `src/mcp_server_langgraph/mcp/server_stdio.py`
- [x] **HTTP/SSE transport** - Implemented in `mcp_server_http.py`
- [x] **Tools** - Documented with JSON schemas
- [x] **Resources** - Documented and accessible
- [x] **Health checks** - `/health` endpoint
- [x] **Documentation** - README, deployment guides
- [x] **Versioning** - Semantic versioning (1.0.0)
- [x] **Authentication** - JWT and API Key support
- [x] **Rate limiting** - Kong integration
- [x] **CORS** - Configured for web clients
- [x] **SSL/TLS** - Certificate provisioning
- [x] **Monitoring** - Prometheus metrics

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io)
- [MCP Registry](https://registry.modelcontextprotocol.io)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## Support

For registry-related issues:
- Registry support: registry-support@modelcontextprotocol.io
- Agent issues: https://github.com/your-org/mcp-server-langgraph/issues
