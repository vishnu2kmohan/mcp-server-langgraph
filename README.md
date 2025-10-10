# LangGraph MCP Agent with OpenFGA & Infisical

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen.svg)](PRODUCTION_DEPLOYMENT.md)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)](KUBERNETES_DEPLOYMENT.md)
[![Security Audit](https://img.shields.io/badge/security-audited-success.svg)](SECURITY_AUDIT.md)

A production-ready LangGraph agent exposed via Model Context Protocol (MCP) with comprehensive authentication, fine-grained authorization (OpenFGA), secrets management (Infisical), and OpenTelemetry-based observability.

## Features

- **Multi-LLM Support (LiteLLM)**: 100+ LLM providers - Anthropic, OpenAI, Google, Azure, AWS Bedrock, Ollama
- **Open-Source Models**: Llama 3.1, Qwen 2.5, Mistral, DeepSeek, and more via Ollama
- **LangGraph Functional API**: Stateful agent with conditional routing and checkpointing
- **MCP Server**: Standard protocol for exposing AI agents as tools (stdio, StreamableHTTP, SSE)
- **Authentication**: JWT-based authentication with token validation
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) relationship-based access control
- **Secrets Management**: Infisical integration for secure secret storage and retrieval
- **Distributed Tracing**: OpenTelemetry tracing with Jaeger backend
- **Metrics**: Prometheus-compatible metrics for monitoring
- **Structured Logging**: JSON logging with trace context correlation
- **Full Observability Stack**: Docker Compose setup with OpenFGA, Jaeger, Prometheus, and Grafana
- **Automatic Fallback**: Resilient multi-model fallback for high availability

## Architecture

```
┌─────────────────┐
│  MCP Client     │
│  (Claude Desktop│
│   or other)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  MCP Server (mcp_server.py)     │
│  ┌──────────────────────────┐   │
│  │ Auth Middleware          │   │
│  │ - JWT Verification       │   │
│  │ - RBAC Authorization     │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │ LangGraph Agent          │   │
│  │ - Routing                │   │
│  │ - Tool Usage             │   │
│  │ - Response Generation    │   │
│  └──────────────────────────┘   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Observability (OTEL)           │
│  ┌──────────┐  ┌──────────┐    │
│  │ Traces   │  │ Metrics  │    │
│  │ (Jaeger) │  │(Prometheus)   │
│  └──────────┘  └──────────┘    │
│         └──────┬────────┘       │
│                ▼                │
│         ┌──────────┐            │
│         │ Grafana  │            │
│         └──────────┘            │
└─────────────────────────────────┘
```

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Start infrastructure**:
```bash
docker-compose up -d
```

This starts:
- **OpenFGA**: http://localhost:8080 (authorization)
- **Jaeger UI**: http://localhost:16686 (distributed tracing)
- **Prometheus**: http://localhost:9090 (metrics)
- **Grafana**: http://localhost:3000 (visualization, admin/admin)
- **PostgreSQL**: localhost:5432 (OpenFGA storage)

3. **Setup OpenFGA**:
```bash
python setup_openfga.py
```

Save the generated `OPENFGA_STORE_ID` and `OPENFGA_MODEL_ID` to your `.env` file.

4. **Setup Infisical** (Optional):
```bash
python setup_infisical.py
```

5. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and OpenFGA IDs
# Get your Gemini API key from: https://aistudio.google.com/apikey
```

6. **Test the system**:
```bash
# Test OpenFGA authorization
python example_openfga_usage.py

# Test MCP server
python example_client.py
```

## Usage

### Running the MCP Server

```bash
python mcp_server.py
```

### Testing with Example Client

```bash
python example_client.py
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["/path/to/langgraph_mcp_agent/mcp_server.py"]
    }
  }
}
```

## Authentication & Authorization

### JWT Authentication

```python
from auth import AuthMiddleware

auth = AuthMiddleware(secret_key=settings.jwt_secret_key)

# Create token
token = auth.create_token("alice", expires_in=3600)

# Authenticate user
result = await auth.authenticate("alice")
```

### OpenFGA Fine-Grained Authorization

Uses relationship-based access control (Google Zanzibar model):

```python
from openfga_client import OpenFGAClient

client = OpenFGAClient(
    api_url=settings.openfga_api_url,
    store_id=settings.openfga_store_id,
    model_id=settings.openfga_model_id
)

# Check permission
allowed = await client.check_permission(
    user="user:alice",
    relation="executor",
    object="tool:chat"
)

# Grant permission
await client.write_tuples([
    {"user": "user:alice", "relation": "executor", "object": "tool:chat"}
])

# List accessible resources
resources = await client.list_objects(
    user="user:alice",
    relation="executor",
    object_type="tool"
)
```

### Default Users (Development Only)

- **alice**: Premium user, member and admin of organization:acme
- **bob**: Standard user, member of organization:acme
- **admin**: Admin user with elevated privileges

See `auth.py:30-50` for user definitions.

**⚠️ Production**: Configure real users and authentication before deployment.

## Observability

### Distributed Tracing

Every request is traced end-to-end with OpenTelemetry:

```python
from observability import tracer

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

View traces in Jaeger: http://localhost:16686

### Metrics

Standard metrics are automatically collected:

- `agent.tool.calls`: Tool invocation counter
- `agent.calls.successful`: Successful operation counter
- `agent.calls.failed`: Failed operation counter
- `auth.failures`: Authentication failure counter
- `authz.failures`: Authorization failure counter
- `agent.response.duration`: Response time histogram

View metrics in Prometheus: http://localhost:9090

### Logging

Structured logging with trace context:

```python
from observability import logger

logger.info("Event occurred", extra={
    "user_id": "user_123",
    "custom_field": "value"
})
```

Logs include trace_id and span_id for correlation with traces.

## LangGraph Agent

The agent uses the functional API with:

- **State Management**: TypedDict-based state with message history
- **Conditional Routing**: Dynamic routing based on message content
- **Tool Integration**: Extensible tool system (extend in `agent.py`)
- **Checkpointing**: Conversation persistence with MemorySaver

### Extending the Agent

Add tools in `agent.py`:

```python
def custom_tool(state: AgentState) -> AgentState:
    # Your tool logic
    return state

workflow.add_node("custom_tool", custom_tool)
workflow.add_edge("router", "custom_tool")
```

## Configuration

All settings via environment variables, Infisical, or `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `langgraph-mcp-agent` |
| `OTLP_ENDPOINT` | OpenTelemetry collector | `http://localhost:4317` |
| `JWT_SECRET_KEY` | Secret for JWT signing | (loaded from Infisical) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (loaded from Infisical) |
| `MODEL_NAME` | Claude model to use | `claude-3-5-sonnet-20241022` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENFGA_API_URL` | OpenFGA server URL | `http://localhost:8080` |
| `OPENFGA_STORE_ID` | OpenFGA store ID | (from setup) |
| `OPENFGA_MODEL_ID` | OpenFGA model ID | (from setup) |
| `INFISICAL_CLIENT_ID` | Infisical auth client ID | (optional) |
| `INFISICAL_CLIENT_SECRET` | Infisical auth secret | (optional) |
| `INFISICAL_PROJECT_ID` | Infisical project ID | (optional) |

See `config.py` for all options.

### Secrets Loading Priority

1. **Infisical** (if configured)
2. **Environment variables** (fallback)
3. **Default values** (last resort)

## Monitoring Dashboard

Access Grafana at http://localhost:3000 (admin/admin) and create dashboards using:

- **Prometheus datasource**: Metrics visualization
- **Jaeger datasource**: Trace exploration

Example queries:
- Request rate: `rate(agent_tool_calls_total[5m])`
- Error rate: `rate(agent_calls_failed_total[5m])`
- P95 latency: `histogram_quantile(0.95, agent_response_duration_bucket)`

## Security Considerations

🔒 **Production Checklist**:

- [ ] Store JWT secret in Infisical
- [ ] Use production Infisical project with proper access controls
- [ ] Configure OpenFGA with PostgreSQL backend (not in-memory)
- [ ] Enable OpenFGA audit logging
- [ ] Enable TLS for all services (OTLP, OpenFGA, PostgreSQL)
- [ ] Implement rate limiting on MCP endpoints
- [ ] Use production-grade user database
- [ ] Review and minimize OpenFGA permissions
- [ ] Set up secret rotation in Infisical
- [ ] Enable monitoring alerts for auth failures
- [ ] Implement token rotation and revocation
- [ ] Use separate OpenFGA stores per environment
- [ ] Enable MFA for Infisical access

## Kubernetes Deployment

The agent is fully containerized and ready for Kubernetes deployment. Supported platforms:
- Google Kubernetes Engine (GKE)
- Amazon Elastic Kubernetes Service (EKS)
- Azure Kubernetes Service (AKS)
- Rancher
- VMware Tanzu

### Quick Deploy

```bash
# Build and push image
docker build -t your-registry/langgraph-agent:v1.0.0 .
docker push your-registry/langgraph-agent:v1.0.0

# Deploy with Helm
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=your-registry/langgraph-agent \
  --set image.tag=v1.0.0

# Or deploy with Kustomize
kubectl apply -k kustomize/overlays/production
```

See **[KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md)** for complete deployment guide.

## API Gateway & Rate Limiting

Kong API Gateway integration provides:
- **Rate Limiting**: Tiered limits (60-1000 req/min) per consumer/tier
- **Authentication**: JWT, API Key, OAuth2
- **Traffic Control**: Request transformation, routing, load balancing
- **Security**: IP restriction, bot detection, CORS
- **Monitoring**: Prometheus metrics, request logging

```bash
# Deploy with Kong rate limiting
helm install langgraph-agent ./helm/langgraph-agent \
  --set kong.enabled=true \
  --set kong.rateLimitTier=premium

# Or apply Kong manifests directly
kubectl apply -k kubernetes/kong/
```

See **[KONG_INTEGRATION.md](KONG_INTEGRATION.md)** for complete Kong setup and rate limiting configuration.

## MCP Transports & Registry

The agent supports multiple MCP transports:
- **StreamableHTTP** (Recommended): Modern HTTP streaming for production
- **stdio**: For Claude Desktop and local applications
- **HTTP/SSE** (Deprecated): Legacy Server-Sent Events

```bash
# StreamableHTTP (recommended for web/production)
python mcp_server_streamable.py

# stdio (local/desktop)
python mcp_server.py

# HTTP/SSE (deprecated, legacy only)
python mcp_server_http.py

# Access StreamableHTTP endpoints
POST /message         # Main MCP endpoint (streaming or regular)
GET /tools            # List tools
GET /resources        # List resources
```

**Why StreamableHTTP?**
- ✅ Modern HTTP/2+ streaming
- ✅ Better load balancer/proxy compatibility
- ✅ Proper request/response pairs
- ✅ Full MCP spec compliance
- ✅ Works with Kong rate limiting

**Registry compliant** - Includes manifest files for MCP Registry publication.

See **[MCP_REGISTRY.md](MCP_REGISTRY.md)** for registry deployment and transport configuration.

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Tests pass
- Code follows style guidelines
- Documentation is updated
- Observability is maintained
