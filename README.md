# MCP Server with LangGraph + OpenFGA & Infisical

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen.svg)](PRODUCTION_DEPLOYMENT.md)
[![Use This Template](https://img.shields.io/badge/use-this%20template-blue.svg?logo=cookiecutter)](TEMPLATE_USAGE.md)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)](KUBERNETES_DEPLOYMENT.md)
[![Security Audit](https://img.shields.io/badge/security-audited-success.svg)](SECURITY_AUDIT.md)

A **production-ready cookie-cutter template** for building MCP servers with LangGraph's Functional API. Features comprehensive authentication (JWT), fine-grained authorization (OpenFGA), secrets management (Infisical), and OpenTelemetry-based observability.

**🎯 Opinionated, production-grade foundation for your MCP server projects.**

## 🚀 Use This Template

```bash
# Generate your own MCP server project
uvx cookiecutter gh:vishnu2kmohan/mcp_server_langgraph

# Answer a few questions and get a fully configured project!
```

**See [TEMPLATE_USAGE.md](TEMPLATE_USAGE.md) for detailed instructions.**

## Features

- **Multi-LLM Support (LiteLLM)**: 100+ LLM providers - Anthropic, OpenAI, Google, Azure, AWS Bedrock, Ollama
- **Open-Source Models**: Llama 3.1, Qwen 2.5, Mistral, DeepSeek, and more via Ollama
- **LangGraph Functional API**: Stateful agent with conditional routing and checkpointing
- **MCP Server**: Standard protocol for exposing AI agents as tools (stdio, StreamableHTTP, SSE)
- **Authentication**: JWT-based authentication with token validation
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) relationship-based access control
- **Secrets Management**: Infisical integration for secure secret storage and retrieval
- **Dual Observability**: OpenTelemetry + LangSmith for comprehensive monitoring
  - **OpenTelemetry**: Distributed tracing with Jaeger, metrics with Prometheus
  - **LangSmith**: LLM-specific tracing, prompt engineering, evaluations
- **Structured Logging**: JSON logging with trace context correlation
- **Full Observability Stack**: Docker Compose setup with OpenFGA, Jaeger, Prometheus, and Grafana
- **LangGraph Platform**: Deploy to managed LangGraph Cloud with one command
- **Automatic Fallback**: Resilient multi-model fallback for high availability

## 📚 Documentation

- **[Full Documentation](https://mcp-server-langgraph.mintlify.app)** - Complete guides, API reference, and tutorials
- **[API Documentation](/docs)** - Interactive OpenAPI/Swagger UI (when running locally)
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Mintlify documentation deployment instructions

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

### 🐳 Docker Compose (Recommended)

Get the complete stack running in 2 minutes:

```bash
# Quick start script handles everything
./scripts/docker-compose-quickstart.sh
```

This starts:
- **Agent API**: http://localhost:8000 (MCP agent)
- **OpenFGA**: http://localhost:8080 (authorization)
- **OpenFGA Playground**: http://localhost:3001
- **Jaeger UI**: http://localhost:16686 (distributed tracing)
- **Prometheus**: http://localhost:9090 (metrics)
- **Grafana**: http://localhost:3000 (visualization, admin/admin)
- **PostgreSQL**: localhost:5432 (OpenFGA storage)

**Then setup OpenFGA**:
```bash
python scripts/setup_openfga.py
# Add OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env
docker-compose restart agent
```

**Test the agent**:
```bash
curl http://localhost:8000/health
```

See [Docker Compose documentation](docs/deployment/docker.mdx) for details.

### 🐍 Local Python Development

1. **Install dependencies**:
```bash
uv sync  # Install all dependencies and create virtual environment
# OR: uv pip install -r requirements.txt
```

2. **Start infrastructure** (without agent):
```bash
# Start only supporting services
docker-compose up -d openfga postgres otel-collector jaeger prometheus grafana
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your API keys:
# - GOOGLE_API_KEY (get from https://aistudio.google.com/apikey)
# - ANTHROPIC_API_KEY or OPENAI_API_KEY (optional)
```

4. **Setup OpenFGA**:
```bash
python scripts/setup_openfga.py
# Save OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env
```

5. **Run the agent locally**:
```bash
python mcp_server_streamable.py
```

6. **Test**:
```bash
# Test with example client
python examples/example_client.py

# Or curl
curl http://localhost:8000/health
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
      "args": ["/path/to/mcp_server_langgraph/mcp_server.py"]
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

This project supports **dual observability**: OpenTelemetry for infrastructure metrics and LangSmith for LLM-specific tracing.

### LangSmith Tracing (LLM Observability)

LangSmith provides comprehensive LLM and agent observability:

**Setup**:
```bash
# Add to .env
LANGSMITH_API_KEY=your-key-from-smith.langchain.com
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=mcp-server-langgraph
```

**Features**:
- 🔍 **Automatic Tracing**: All LLM calls and agent steps traced
- 🎯 **Prompt Engineering**: Iterate on prompts with production data
- 📊 **Evaluations**: Compare model performance on datasets
- 💬 **User Feedback**: Collect and analyze user ratings
- 💰 **Cost Tracking**: Monitor LLM API costs per user/session
- 🐛 **Debugging**: Root cause analysis with full context

**View traces**: https://smith.langchain.com/

See **[LANGSMITH_INTEGRATION.md](LANGSMITH_INTEGRATION.md)** for complete LangSmith guide.

### OpenTelemetry Tracing (Infrastructure)

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
| `SERVICE_NAME` | Service identifier | `mcp-server-langgraph` |
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

## Deployment Options

### LangGraph Platform (Managed Cloud)

Deploy to LangGraph Platform for fully managed, serverless hosting:

```bash
# Login (uvx runs langgraph-cli without installing it)
uvx langgraph-cli login

# Deploy
uvx langgraph-cli deploy
```

**Benefits**:
- ✅ Zero infrastructure management
- ✅ Integrated LangSmith observability
- ✅ Automatic versioning and rollbacks
- ✅ Built-in scaling and load balancing
- ✅ One-command deployment

See **[LANGGRAPH_PLATFORM_DEPLOYMENT.md](LANGGRAPH_PLATFORM_DEPLOYMENT.md)** for complete platform guide.

### Google Cloud Run (Serverless)

Deploy to Google Cloud Run for fully managed, serverless deployment:

```bash
# Quick deploy
cd cloudrun
./deploy.sh --setup

# Or use gcloud directly
gcloud run deploy mcp-server-langgraph \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

**Benefits**:
- ✅ Serverless autoscaling (0 to 100+ instances)
- ✅ Pay only for actual usage
- ✅ Automatic HTTPS and SSL certificates
- ✅ Integrated with Google Secret Manager
- ✅ Built-in monitoring and logging

See **[CLOUDRUN_DEPLOYMENT.md](CLOUDRUN_DEPLOYMENT.md)** for complete Cloud Run guide.

### Kubernetes Deployment

The agent is fully containerized and ready for Kubernetes deployment. Supported platforms:
- Google Kubernetes Engine (GKE)
- Amazon Elastic Kubernetes Service (EKS)
- Azure Kubernetes Service (AKS)
- Rancher
- VMware Tanzu

**Quick Deploy**:

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

## Contributors

Thanks to all the amazing people who have contributed to this project! 🙌

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification.

Want to be listed here? See [CONTRIBUTING.md](.github/CONTRIBUTING.md)!

## Support

Need help? Check out our [Support Guide](.github/SUPPORT.md) for:

- 📚 Documentation links
- 💬 Where to ask questions
- 🐛 How to report bugs
- 🔒 Security reporting

## License

MIT - see [LICENSE](LICENSE) file for details

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent framework
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [OpenFGA](https://openfga.dev/) - Authorization
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-LLM support
- [OpenTelemetry](https://opentelemetry.io/) - Observability

Special thanks to the open source community!

## Contributing

We welcome contributions from the community! 🎉

### Quick Start for Contributors

1. **Read the guides**:
   - [CONTRIBUTING.md](.github/CONTRIBUTING.md) - Contribution guidelines
   - [DEVELOPMENT.md](DEVELOPMENT.md) - Developer setup

2. **Find something to work on**:
   - [Good First Issues](https://github.com/vishnu2kmohan/mcp_server_langgraph/labels/good%20first%20issue)
   - [Help Wanted](https://github.com/vishnu2kmohan/mcp_server_langgraph/labels/help%20wanted)

3. **Get help**:
   - [GitHub Discussions](https://github.com/vishnu2kmohan/mcp_server_langgraph/discussions)
   - [Support Guide](.github/SUPPORT.md)

### Contribution Areas

- 💻 **Code**: Features, bug fixes, performance improvements
- 📖 **Documentation**: Guides, tutorials, API docs
- 🧪 **Testing**: Unit tests, integration tests, test coverage
- 🔒 **Security**: Security improvements, audits
- 🌐 **Translations**: i18n support (future)
- 💡 **Ideas**: Feature requests, architecture discussions

All contributors will be recognized in our [Contributors](#contributors) section!
