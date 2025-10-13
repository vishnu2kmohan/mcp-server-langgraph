# MCP Server with LangGraph + OpenFGA & Infisical

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen.svg)](docs/deployment/production.md)
[![Use This Template](https://img.shields.io/badge/use-this%20template-blue.svg?logo=cookiecutter)](docs/template/usage.md)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?logo=kubernetes&logoColor=white)](docs/deployment/kubernetes.md)

[![CI/CD](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/ci.yaml)
[![PR Checks](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/pr-checks.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/pr-checks.yaml)
[![Quality Tests](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/quality-tests.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/quality-tests.yaml)
[![Security Scan](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml/badge.svg)](https://github.com/vishnu2kmohan/mcp-server-langgraph/actions/workflows/security-scan.yaml)

[![Security Audit](https://img.shields.io/badge/security-audited-success.svg)](docs/archive/SECURITY_AUDIT.md)
[![Code Quality](https://img.shields.io/badge/code%20quality-9.6%2F10-brightgreen.svg)](#quality-practices)
[![Property Tests](https://img.shields.io/badge/property%20tests-27%2B-blue.svg)](#testing-strategy)
[![Contract Tests](https://img.shields.io/badge/contract%20tests-20%2B-blue.svg)](#testing-strategy)
[![Mutation Testing](https://img.shields.io/badge/mutation%20testing-enabled-yellow.svg)](docs/MUTATION_TESTING.md)

A **production-ready cookie-cutter template** for building MCP servers with LangGraph's Functional API. Features comprehensive authentication (JWT), fine-grained authorization (OpenFGA), secrets management (Infisical), and OpenTelemetry-based observability.

**🎯 Opinionated, production-grade foundation for your MCP server projects.**

## 🚀 Use This Template

```bash
# Generate your own MCP server project
uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph

# Answer a few questions and get a fully configured project!
```

**See [Template Usage Guide](docs/template/usage.md) for detailed instructions.**

---

## 📖 Template vs Project Usage

### Using This as a Template

**For**: Creating your own MCP server with custom tools and logic

**How**:
1. Generate project: `uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph`
2. Customize tools in generated `agent.py`
3. Update authorization model in `scripts/setup/setup_openfga.py`
4. Deploy your custom server

**What gets customized**:
- Project name, author, license
- Which features to include (auth, observability, deployment configs)
- LLM provider preferences
- Tool implementations

**See**: [Template Usage Guide](docs/template/usage.md)

### Using This Project Directly

**For**: Learning, testing, or using the reference implementation

**How**:
1. Clone: `git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git`
2. Install: `uv sync`
3. Configure: Copy `.env.example` to `.env` and add API keys
4. Run: `make run-streamable`

**What you get**:
- Fully working MCP server with example tools (`chat`, `search`)
- Complete observability stack
- Production-ready deployment configs
- Comprehensive test suite

**See**: [Quick Start](#quick-start) below

---

## Features

### 🎯 Core Capabilities
- **Multi-LLM Support (LiteLLM)**: 100+ LLM providers - Anthropic, OpenAI, Google, Azure, AWS Bedrock, Ollama
- **Open-Source Models**: Llama 3.1, Qwen 2.5, Mistral, DeepSeek, and more via Ollama
- **LangGraph Functional API**: Stateful agent with conditional routing and checkpointing
- **MCP Server**: Standard protocol for exposing AI agents as tools (stdio, StreamableHTTP)
- **Enterprise Authentication**: Pluggable auth providers (InMemory, Keycloak SSO)
  - **JWT Authentication**: Token-based authentication with validation and expiration
  - **Keycloak Integration**: Production-ready SSO with OIDC/OAuth2 ([docs/integrations/keycloak.md](docs/integrations/keycloak.md))
  - **Token Refresh**: Automatic refresh token rotation
  - **JWKS Verification**: Public key verification without shared secrets
- **Session Management**: Flexible session storage backends
  - **InMemory**: Fast in-memory sessions for development
  - **Redis**: Persistent sessions with TTL, sliding windows, concurrent limits
  - **Advanced Features**: Session lifecycle management, bulk revocation, user tracking
- **Fine-Grained Authorization**: OpenFGA (Zanzibar-style) relationship-based access control
  - **Role Mapping**: Declarative role mappings with YAML configuration
  - **Keycloak Sync**: Automatic role/group synchronization to OpenFGA
  - **Hierarchies**: Role inheritance and conditional mappings
- **Secrets Management**: Infisical integration for secure secret storage and retrieval
- **Feature Flags**: Gradual rollouts with environment-based configuration
- **Dual Observability**: OpenTelemetry + LangSmith for comprehensive monitoring
  - **OpenTelemetry**: Distributed tracing with Jaeger, metrics with Prometheus (30+ auth metrics)
  - **LangSmith**: LLM-specific tracing, prompt engineering, evaluations
- **Structured Logging**: JSON logging with trace context correlation
- **Full Observability Stack**: Docker Compose setup with OpenFGA, Keycloak, Redis, Jaeger, Prometheus, and Grafana
- **LangGraph Platform**: Deploy to managed LangGraph Cloud with one command
- **Automatic Fallback**: Resilient multi-model fallback for high availability

### 🧪 Quality & Testing
- **Property-Based Testing**: 27+ Hypothesis tests discovering edge cases automatically
- **Contract Testing**: 20+ JSON Schema tests ensuring MCP protocol compliance
- **Performance Regression Testing**: Automated latency tracking against baselines
- **Mutation Testing**: Test effectiveness verification with mutmut (80%+ target)
- **Strict Typing**: Gradual mypy strict mode rollout (3 modules complete)
- **OpenAPI Validation**: Automated schema generation and breaking change detection
- **87%+ Code Coverage**: Comprehensive unit and integration tests

### 🚀 Production Deployment
- **Kubernetes Ready**: Production manifests for GKE, EKS, AKS, Rancher, VMware Tanzu
- **Helm Charts**: Flexible deployment with customizable values and dependencies
- **Kustomize**: Environment-specific overlays (dev/staging/production)
- **Multi-Platform**: Docker Compose, kubectl, Kustomize, Helm deployment options
- **CI/CD Pipeline**: Automated testing, validation, build, and deployment with GitHub Actions
- **Deployment Validation**: Comprehensive validation scripts for all deployment configurations
- **E2E Testing**: Automated deployment tests with kind clusters
- **High Availability**: Pod anti-affinity, HPA, PDB, rolling updates
- **Monitoring**: 25+ Prometheus alerts, 4 Grafana dashboards, 9 operational runbooks
- **Observability**: Full monitoring for Keycloak, Redis, sessions, and application
- **Secrets**: External secrets operator support, sealed secrets compatible
- **Service Mesh**: Compatible with Istio, Linkerd, and other service meshes

### 📚 Documentation & Architecture
- **Architecture Decision Records (ADRs)**: 21 documented design decisions ([docs/adr/](docs/adr/))
- **Comprehensive Guides**: Testing, typing, mutation testing, deployment
- **API Documentation**: Interactive OpenAPI/Swagger UI

## 📚 Documentation

- **[Full Documentation](https://mcp-server-langgraph.mintlify.app)** - Complete guides, API reference, and tutorials
- **[API Documentation](/docs)** - Interactive OpenAPI/Swagger UI (when running locally)
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Mintlify documentation deployment instructions

### 📖 Quality & Testing Guides
- **[Mutation Testing Guide](docs/MUTATION_TESTING.md)** - Test effectiveness measurement and improvement
- **[Strict Typing Guide](docs/STRICT_TYPING_GUIDE.md)** - Gradual mypy strict mode rollout
- **[Architecture Decision Records](docs/adr/)** - Documented architectural choices

### 🚀 Deployment & Operations
- **[Deployment Quickstart](deployments/QUICKSTART.md)** - Quick deployment guide for all platforms
- **[Deployment README](deployments/README.md)** - Comprehensive deployment documentation
- **[CI/CD Guide](docs/development/ci-cd.md)** - Continuous integration and deployment pipeline
- **[Operational Runbooks](docs/runbooks/)** - 9 runbooks for alert response and troubleshooting
- **[Keycloak Integration](docs/integrations/keycloak.md)** - Enterprise SSO setup and configuration

### 📝 Architecture Decision Records (ADRs)

See [docs/adr/README.md](docs/adr/README.md) for complete index of all 21 ADRs.

**Core Architecture**:
- [0001: Multi-Provider LLM Support (LiteLLM)](docs/adr/0001-llm-multi-provider.md)
- [0002: Fine-Grained Authorization (OpenFGA)](docs/adr/0002-openfga-authorization.md)
- [0003: Dual Observability Strategy](docs/adr/0003-dual-observability.md)
- [0004: MCP Transport Selection (StreamableHTTP)](docs/adr/0004-mcp-streamable-http.md)
- [0005: Type-Safe Responses (Pydantic AI)](docs/adr/0005-pydantic-ai-integration.md)

**Authentication & Sessions**:
- [0006: Pluggable Session Storage Architecture](docs/adr/0006-session-storage-architecture.md)
- [0007: Pluggable Authentication Provider Pattern](docs/adr/0007-authentication-provider-pattern.md)

**Infrastructure & Deployment**:
- [0008: Infisical for Secrets Management](docs/adr/0008-infisical-secrets-management.md)
- [0009: Feature Flag System](docs/adr/0009-feature-flag-system.md)
- [0013: Multi-Deployment Target Strategy](docs/adr/0013-multi-deployment-target-strategy.md)
- [0020: Dual MCP Transport Protocol](docs/adr/0020-dual-mcp-transport-protocol.md)
- [0021: CI/CD Pipeline Strategy](docs/adr/0021-cicd-pipeline-strategy.md)

**Development & Quality**:
- [0010: LangGraph Functional API](docs/adr/0010-langgraph-functional-api.md)
- [0014: Pydantic Type Safety Strategy](docs/adr/0014-pydantic-type-safety.md)
- [0015: Memory Checkpointing](docs/adr/0015-memory-checkpointing.md)
- [0016: Property-Based Testing](docs/adr/0016-property-based-testing-strategy.md)
- [0017: Error Handling Strategy](docs/adr/0017-error-handling-strategy.md)
- [0018: Semantic Versioning Strategy](docs/adr/0018-semantic-versioning-strategy.md)
- [0019: Async-First Architecture](docs/adr/0019-async-first-architecture.md)

**Compliance**:
- [0011: Cookiecutter Template Strategy](docs/adr/0011-cookiecutter-template-strategy.md)
- [0012: Built-In Compliance Framework](docs/adr/0012-compliance-framework-integration.md)

## Architecture

```
┌──────────────────────┐
│    MCP Client        │
│  (Claude Desktop     │
│   or other)          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────┐
│         MCP Server                   │
│  (server_stdio.py/streamable.py)    │
│  ┌────────────────────────────┐     │
│  │   Auth Middleware          │     │
│  │   - JWT Verification       │     │
│  │   - OpenFGA Authorization  │     │
│  └────────────────────────────┘     │
│  ┌────────────────────────────┐     │
│  │   LangGraph Agent          │     │
│  │   - Pydantic AI Routing    │     │
│  │   - Tool Usage             │     │
│  │   - Response Generation    │     │
│  └────────────────────────────┘     │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│    Observability Stack               │
│  ┌──────────┐    ┌──────────────┐   │
│  │ Traces   │    │   Metrics    │   │
│  │ (Jaeger) │    │ (Prometheus) │   │
│  └─────┬────┘    └──────┬───────┘   │
│        └────────────────┘            │
│                ▼                     │
│        ┌──────────────┐              │
│        │   Grafana    │              │
│        └──────────────┘              │
└──────────────────────────────────────┘
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
python scripts/setup/setup_openfga.py
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
python scripts/setup/setup_openfga.py
# Save OPENFGA_STORE_ID and OPENFGA_MODEL_ID to .env
```

5. **Run the agent locally**:
```bash
python -m mcp_server_langgraph.mcp.server_streamable
```

6. **Test**:
```bash
# Test with example client
python examples/examples/client_stdio.py

# Or curl
curl http://localhost:8000/health
```

## Usage

### Running the MCP Server

```bash
python -m mcp_server_langgraph.mcp.server_stdio
```

### Testing with Example Client

```bash
python examples/client_stdio.py
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "langgraph-agent": {
      "command": "python",
      "args": ["/path/to/mcp_server_langgraph/src/mcp_server_langgraph/mcp/server_stdio.py"]
    }
  }
}
```

## Authentication & Authorization

### JWT Authentication

```python
from mcp_server_langgraph.auth.middleware import AuthMiddleware

auth = AuthMiddleware(secret_key=settings.jwt_secret_key)

# Create token
token = auth.create_token("alice", expires_in=3600)

# Authenticate user
result = await auth.authenticate("alice")
```

### OpenFGA Fine-Grained Authorization

Uses relationship-based access control (Google Zanzibar model):

```python
from mcp_server_langgraph.auth.openfga import OpenFGAClient

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

See `src/mcp_server_langgraph/auth/middleware.py:30-50` for user definitions.

**⚠️ Production**: Configure real users and authentication before deployment.

## Testing Strategy

This project uses a comprehensive, multi-layered testing approach to ensure production quality:

### 🧪 Test Types

#### Unit Tests (Fast, No External Dependencies)
```bash
make test-unit
# OR: pytest -m unit -v
```
- **87%+ code coverage** with comprehensive assertions
- Mock all external dependencies (LLM, OpenFGA, Infisical)
- Test pure logic, validation, and error handling

#### Integration Tests (Require Infrastructure)
```bash
make test-integration
# OR: pytest -m integration -v
```
- Real OpenFGA authorization checks
- Real observability stack (Jaeger, Prometheus)
- End-to-end workflows with actual dependencies

#### Property-Based Tests (Edge Case Discovery)
```bash
make test-property
# OR: pytest -m property -v
```
- **27+ Hypothesis tests** generating thousands of test cases
- Automatic edge case discovery (empty strings, extreme values, malformed input)
- Tests properties like "JWT encode/decode should be reversible"
- **See**: `tests/property/test_llm_properties.py`, `tests/property/test_auth_properties.py`

#### Contract Tests (Protocol Compliance)
```bash
make test-contract
# OR: pytest -m contract -v
```
- **20+ JSON Schema tests** validating MCP protocol compliance
- Ensures JSON-RPC 2.0 format correctness
- Validates request/response schemas match specification
- **See**: `tests/contract/test_mcp_contract.py`, `tests/contract/mcp_schemas.json`

#### Performance Regression Tests
```bash
make test-regression
# OR: pytest -m regression -v
```
- Tracks latency metrics against baselines
- Alerts on >20% performance regressions
- Monitors: agent_response (p95 < 5s), llm_call (p95 < 10s), authorization (p95 < 50ms)
- **See**: `tests/regression/test_performance_regression.py`, `tests/regression/baseline_metrics.json`

#### Mutation Testing (Test Effectiveness)
```bash
make test-mutation
# OR: mutmut run && mutmut results
```
- **Measures test quality** by introducing code mutations
- **Target**: 80%+ mutation score on critical modules
- Identifies weak assertions and missing test cases
- **See**: [Mutation Testing Guide](docs/MUTATION_TESTING.md)

#### OpenAPI Validation
```bash
make validate-openapi
# OR: python scripts/validate_openapi.py
```
- Generates OpenAPI schema from code
- Validates schema correctness
- Detects breaking changes
- Ensures all endpoints documented

### 🎯 Running Tests

```bash
# Quick: Run all unit tests (2-5 seconds)
make test-unit

# All automated tests (unit + integration)
make test

# All quality tests (property + contract + regression)
make test-all-quality

# Coverage report
make test-coverage
# Opens htmlcov/index.html with detailed coverage

# Full test suite (including mutation tests - SLOW!)
make test-unit && make test-all-quality && make test-mutation
```

### 📊 Quality Metrics

- **Code Coverage**: 87%+ (target: 90%)
- **Property Tests**: 27+ test classes with thousands of generated cases
- **Contract Tests**: 20+ protocol compliance tests
- **Mutation Score**: 80%+ target on critical modules (src/mcp_server_langgraph/core/agent.py, src/mcp_server_langgraph/auth/middleware.py, src/mcp_server_langgraph/core/config.py)
- **Type Coverage**: Strict mypy on 3 modules (config, feature_flags, observability)
- **Performance**: All p95 latencies within target thresholds

### 🔄 CI/CD Integration

GitHub Actions runs quality tests on every PR:

```yaml
# .github/workflows/quality-tests.yaml
jobs:
  - property-tests     # 15min timeout
  - contract-tests     # MCP protocol validation
  - regression-tests   # Performance monitoring
  - openapi-validation # API schema validation
  - mutation-tests     # Weekly schedule (too slow for every PR)
```

**See**: [.github/workflows/quality-tests.yaml](.github/workflows/quality-tests.yaml)

## Feature Flags

Control features dynamically without code changes:

```bash
# Enable/disable features via environment variables
FF_ENABLE_PYDANTIC_AI_ROUTING=true      # Type-safe routing (default: true)
FF_ENABLE_LLM_FALLBACK=true             # Multi-model fallback (default: true)
FF_ENABLE_OPENFGA=true                  # Authorization (default: true)
FF_OPENFGA_STRICT_MODE=false            # Fail-closed vs fail-open (default: false)
FF_PYDANTIC_AI_CONFIDENCE_THRESHOLD=0.7 # Routing confidence (default: 0.7)

# All flags with FF_ prefix (20+ available)
```

**Key Flags**:
- `enable_pydantic_ai_routing`: Type-safe routing with confidence scores
- `enable_llm_fallback`: Automatic fallback to alternative models
- `enable_openfga`: Fine-grained authorization (disable for development)
- `openfga_strict_mode`: Fail-closed (deny on error) vs fail-open (allow on error)
- `enable_experimental_*`: Master switches for experimental features

**See**: `feature_flags.py` for all flags and validation

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
from mcp_server_langgraph.observability.telemetry import tracer

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
from mcp_server_langgraph.observability.telemetry import logger

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
- **Tool Integration**: Extensible tool system (extend in `src/mcp_server_langgraph/core/agent.py`)
- **Checkpointing**: Conversation persistence with MemorySaver

### Extending the Agent

Add tools in `src/mcp_server_langgraph/core/agent.py`:

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

See `src/mcp_server_langgraph/core/config.py` for all options.

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
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace \
  --set image.repository=your-registry/langgraph-agent \
  --set image.tag=v1.0.0

# Or deploy with Kustomize
kubectl apply -k deployments/kustomize/overlays/production
```

See **[Kubernetes Deployment Guide](docs/deployment/kubernetes.md)** for complete deployment guide.

## API Gateway & Rate Limiting

Kong API Gateway integration provides:
- **Rate Limiting**: Tiered limits (60-1000 req/min) per consumer/tier
- **Authentication**: JWT, API Key, OAuth2
- **Traffic Control**: Request transformation, routing, load balancing
- **Security**: IP restriction, bot detection, CORS
- **Monitoring**: Prometheus metrics, request logging

```bash
# Deploy with Kong rate limiting
helm install langgraph-agent ./deployments/helm/langgraph-agent \
  --set kong.enabled=true \
  --set kong.rateLimitTier=premium

# Or apply Kong manifests directly
kubectl apply -k deployments/kubernetes/kong/
```

See **[KONG_INTEGRATION.md](KONG_INTEGRATION.md)** for complete Kong setup and rate limiting configuration.

## MCP Transports & Registry

The agent supports multiple MCP transports:
- **StreamableHTTP** (Recommended): Modern HTTP streaming for production
- **stdio**: For Claude Desktop and local applications

```bash
# StreamableHTTP (recommended for web/production)
python -m mcp_server_langgraph.mcp.server_streamable

# stdio (local/desktop)
python -m mcp_server_langgraph.mcp.server_stdio

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

## Quality Practices

This project maintains high code quality through:

### 📈 Current Quality Score: **9.6/10**

Assessed across 7 dimensions:
- ✅ **Code Organization**: 9/10 - Clear module structure, separation of concerns
- ✅ **Testing**: 10/10 - Multi-layered testing (unit, integration, property, contract, regression, mutation)
- ✅ **Type Safety**: 9/10 - Gradual strict mypy rollout (3/11 modules strict, 8 remaining)
- ✅ **Documentation**: 10/10 - ADRs, guides, API docs, inline documentation
- ✅ **Error Handling**: 9/10 - Comprehensive error handling, fallback modes
- ✅ **Observability**: 10/10 - Dual observability (OpenTelemetry + LangSmith)
- ✅ **Security**: 9/10 - JWT auth, fine-grained authz, secrets management, security scanning

### 🎯 Quality Gates

**Pre-Commit**:
- Code formatting (black, isort)
- Linting (flake8, mypy)
- Security scan (bandit)

**CI/CD (GitHub Actions)**:
- Unit tests (Python 3.10, 3.11, 3.12)
- Integration tests
- Property-based tests
- Contract tests
- Performance regression tests
- OpenAPI validation
- Mutation tests (weekly)

**Commands**:
```bash
# Code quality checks
make format           # Format code (black + isort)
make lint             # Run linters (flake8 + mypy)
make security-check   # Security scan (bandit)

# Test suite
make test-unit        # Fast unit tests
make test-all-quality # Property + contract + regression
make test-coverage    # Coverage report
```

### 📝 Development Workflow

1. **Branch Protection**: All changes via Pull Requests
2. **Conventional Commits**: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
3. **Code Review**: Required before merge
4. **Quality Gates**: All tests must pass
5. **Documentation**: ADRs for architectural decisions

**See**: [CLAUDE.md](.github/CLAUDE.md) for complete development guide

### 🔄 Continuous Improvement

**In Progress**:
- Expanding strict mypy to all modules (3/11 complete)
- Increasing mutation score to 80%+ on all critical modules
- Adding more property-based tests for edge case discovery

**Recent Improvements** (2025):
- Added 27+ property-based tests (Hypothesis)
- Added 20+ contract tests (JSON Schema)
- Implemented performance regression tracking
- Set up mutation testing with mutmut
- Created 5+ Architecture Decision Records
- Implemented feature flag system

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
   - [Development Guide](docs/development/development.md) - Developer setup

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
