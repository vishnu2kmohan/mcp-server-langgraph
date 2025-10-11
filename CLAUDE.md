# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **production-ready MCP (Model Context Protocol) server** built with LangGraph, featuring:
- Multi-LLM support via LiteLLM (100+ providers: Anthropic, OpenAI, Google, Azure, Bedrock, Ollama)
- Fine-grained authorization using OpenFGA (Zanzibar-style)
- Secrets management with Infisical
- Dual observability: OpenTelemetry (traces/metrics) + LangSmith (LLM-specific)
- Multiple MCP transports: stdio, HTTP/SSE (deprecated), StreamableHTTP (recommended)
- Kubernetes-ready with Helm/Kustomize deployment

## Essential Commands

### Development Setup
```bash
# Install dependencies
make install-dev              # Install all dev dependencies
pip install -r requirements-pinned.txt

# Start infrastructure (OpenFGA, Jaeger, Prometheus, Grafana)
make setup-infra              # Docker Compose stack
make setup-openfga            # Initialize OpenFGA (get STORE_ID and MODEL_ID)

# Configure environment
cp .env.example .env
# Edit .env with OPENFGA_STORE_ID, OPENFGA_MODEL_ID, and API keys
```

### Running Servers
```bash
make run-streamable           # StreamableHTTP server (production, port 8000)
make run                      # stdio server (for Claude Desktop)
make run-http                 # HTTP/SSE server (deprecated)

# Direct execution
python mcp_server_streamable.py
python mcp_server.py
```

### Testing
```bash
make test                     # All tests
make test-unit                # Unit tests only
make test-integration         # Integration tests (requires infrastructure)
make test-coverage            # Generate coverage report (htmlcov/index.html)
pytest -m unit -v             # Verbose unit tests
pytest tests/test_agent.py::test_specific -v  # Single test

# Manual testing
make test-mcp                 # Test MCP server (runs example_client.py)
make test-auth                # Test OpenFGA (runs example_openfga_usage.py)

# Benchmarks
make benchmark                # Performance benchmarks
pytest -m benchmark -v --benchmark-only
```

### Code Quality
```bash
make format                   # Format with black + isort
make lint                     # Run flake8 + mypy
make security-check           # Run bandit security scan

# Individual tools
black . --exclude venv --line-length=127
isort . --skip venv --profile=black
flake8 . --exclude=venv
mypy *.py --ignore-missing-imports
```

### Infrastructure Management
```bash
make logs                     # Follow Docker logs
docker-compose up -d          # Start services
docker-compose down -v        # Stop and remove volumes
make clean                    # Stop services and clean caches
make reset                    # Clean + restart infrastructure + reinitialize OpenFGA
```

## Architecture Overview

### Core Components

**Agent Layer** (agent.py)
- LangGraph functional API with StateGraph
- TypedDict-based state management (`AgentState`)
- Conditional routing based on message content
- Checkpointing with MemorySaver
- Three-node workflow: router → tools → respond

**LLM Abstraction** (llm_factory.py)
- LiteLLM-based multi-provider factory
- Automatic fallback to alternative models
- Sync/async invocation support
- Message format translation (LangChain ↔ LiteLLM)

**MCP Server** (mcp_server_streamable.py, mcp_server.py)
- Transport layer for MCP protocol
- Tool registration and invocation
- Resource management
- JSON-RPC message handling
- StreamableHTTP is production standard

**Authentication** (auth.py)
- JWT token creation and validation
- In-memory user database (replace in production)
- Integration with OpenFGA for authorization
- `AuthMiddleware` class for request handling

**Authorization** (openfga_client.py)
- OpenFGA SDK wrapper
- Relationship-based access control
- Permission checking: `check_permission(user, relation, object)`
- Tuple management: `write_tuples()`, `delete_tuples()`
- Authorization model: user, organization, tool, conversation, role types

**Configuration** (config.py)
- Pydantic Settings-based configuration
- Infisical integration for secret loading
- Multi-LLM provider support
- Environment-based overrides

**Observability** (observability.py)
- OpenTelemetry setup: traces, metrics, logging
- LangSmith integration (optional)
- Structured JSON logging with trace context
- Standard metrics: tool_calls, successful_calls, failed_calls, auth_failures, authz_failures

**Secrets** (secrets_manager.py)
- Infisical client wrapper
- Secret caching with TTL
- Fallback to environment variables
- Automatic rotation support

### Data Flow

```
MCP Client → MCP Server → AuthMiddleware → Agent Graph → LLM Factory → LiteLLM → Provider
                ↓              ↓               ↓
          Tool Handler    OpenFGA      Checkpointing
                           (AuthZ)       (MemorySaver)
```

### Authorization Model

OpenFGA relationships:
- **organization**: `member`, `admin`
- **tool**: `owner`, `executor`, `organization` (relation to org)
- **conversation**: `owner`, `viewer`, `editor`
- **role**: `assignee`

Permission inheritance:
- Tool executors: direct assignment OR owner OR org member
- Conversation viewers: direct assignment OR owner
- Conversation editors: direct assignment OR owner

### State Management

**AgentState TypedDict**:
- `messages`: List of BaseMessage (conversation history)
- `next_action`: Routing decision ("use_tools", "respond", "end")
- `user_id`: Current user identifier
- `request_id`: Request tracking ID

**Checkpointing**: Uses LangGraph's MemorySaver with thread_id for conversation persistence.

### Observability Architecture

**Dual Backend**:
- **OpenTelemetry**: Infrastructure metrics, distributed tracing
- **LangSmith**: LLM-specific tracing, prompt engineering, evaluations

**Key Spans**:
- `mcp.call_tool`: Tool invocation
- `agent.chat`: Agent processing
- `llm.invoke`/`llm.ainvoke`: LLM calls
- `openfga.check`: Authorization checks
- `auth.authenticate`: User authentication

**Metrics**:
- Counters: `tool_calls`, `successful_calls`, `failed_calls`, `auth_failures`, `authz_failures`
- Histograms: `response_duration`

## Development Patterns

### Adding a New Tool

1. **Define tool schema** in MCP server:
```python
Tool(
    name="my_tool",
    description="Tool description",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {"type": "string"},
            "username": {"type": "string"}
        },
        "required": ["param", "username"]
    }
)
```

2. **Add tool handler** in `call_tool()` method with authorization:
```python
async def _handle_my_tool(self, arguments, span, user_id):
    with tracer.start_as_current_span("agent.my_tool"):
        # Check authorization
        authorized = await self.auth.authorize(
            user_id=user_id,
            relation="executor",
            resource="tool:my_tool"
        )
        if not authorized:
            raise PermissionError("Not authorized")

        # Process tool logic
        result = process_tool(arguments["param"])

        # Return response
        return [TextContent(type="text", text=result)]
```

3. **Add OpenFGA tuples** for permissions (in setup_openfga.py or runtime)

4. **Write tests** with proper markers:
```python
@pytest.mark.unit
def test_my_tool_success():
    """Test my_tool with valid input."""
    pass

@pytest.mark.integration
@pytest.mark.auth
async def test_my_tool_authorization():
    """Test my_tool authorization."""
    pass
```

### Adding a New LLM Provider

1. **Add configuration** to config.py:
```python
# Provider-specific settings
my_provider_api_key: Optional[str] = None
my_provider_base_url: str = "https://api.provider.com"
```

2. **Update llm_factory.py** provider mapping:
```python
api_key_map = {
    "my_provider": config.my_provider_api_key,
}

provider_kwargs = {
    "api_base": config.my_provider_base_url,
}
```

3. **Add to fallback models** in config.py if desired

4. **Test** with actual provider:
```python
@pytest.mark.integration
async def test_my_provider_llm():
    """Test LLM factory with my_provider."""
    pass
```

### Working with OpenFGA

**Check permission**:
```python
allowed = await openfga_client.check_permission(
    user="user:alice",
    relation="executor",
    object="tool:chat"
)
```

**Grant permission** (write tuple):
```python
await openfga_client.write_tuples([
    {"user": "user:bob", "relation": "viewer", "object": "conversation:thread_2"}
])
```

**List accessible resources**:
```python
conversations = await openfga_client.list_objects(
    user="user:alice",
    relation="viewer",
    object_type="conversation"
)
```

**Expand relation** (see all users with access):
```python
tree = await openfga_client.expand_relation(
    relation="executor",
    object="tool:chat"
)
```

### Observability Patterns

**Tracing**:
```python
from observability import tracer

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("custom.field", value)
    result = await do_work()
```

**Logging**:
```python
from observability import logger

logger.info(
    "Operation completed",
    extra={
        "user_id": user_id,
        "duration_ms": duration,
        "result_count": len(results)
    }
)
```

**Metrics**:
```python
from observability import metrics

metrics.tool_calls.add(1, {"tool": "chat"})
metrics.response_duration.record(duration_ms, {"tool": "chat"})
```

## Code Standards

### Type Hints
Always use type hints for public APIs:
```python
async def process_message(
    message: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> AgentResponse:
    """Process message with proper typing."""
    pass
```

### Docstrings
Use Google-style docstrings:
```python
def my_function(param: str) -> int:
    """
    Brief description.

    Args:
        param: Parameter description

    Returns:
        Return value description

    Raises:
        ValueError: When validation fails
    """
    pass
```

### Testing Markers
```python
@pytest.mark.unit           # Fast, no external dependencies
@pytest.mark.integration    # Requires infrastructure
@pytest.mark.auth           # Authentication/authorization tests
@pytest.mark.openfga        # OpenFGA-specific
@pytest.mark.mcp            # MCP protocol tests
@pytest.mark.benchmark      # Performance tests
@pytest.mark.slow           # Tests > 1 second
```

### Error Handling
```python
# Specific exceptions
try:
    result = await operation()
except OpenFGAError as e:
    logger.error("OpenFGA failed", exc_info=e)
    raise ServiceUnavailableError()
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

### Async Patterns
```python
# ✅ Good - concurrent operations
results = await asyncio.gather(
    fetch_user(user_id),
    check_permissions(user_id),
    get_preferences(user_id)
)

# ❌ Bad - sequential when could be parallel
user = await fetch_user(user_id)
perms = await check_permissions(user_id)
prefs = await get_preferences(user_id)
```

## Security Requirements

### Never Hardcode Secrets
```python
# ✅ Good
secret = settings.jwt_secret_key

# ❌ Bad
secret = "hardcoded-secret-key"
```

### Always Check Authorization
```python
# ✅ Good
authorized = await auth.authorize(user_id, "viewer", resource)
if not authorized:
    raise PermissionError()

# ❌ Bad - skip authorization
result = process_request()
```

### Validate All Inputs
```python
# ✅ Good - Pydantic validation
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    user_id: str = Field(..., pattern=r"^user:[a-z]+$")

# ❌ Bad - no validation
def chat(message, user_id):
    pass
```

### Log Security Events
```python
# Always log auth failures
logger.warning(
    "Authorization denied",
    extra={
        "user_id": user_id,
        "resource": resource,
        "relation": relation
    }
)
metrics.authz_failures.add(1, {"resource": resource})
```

## Performance Targets

- Agent response: p95 < 5 seconds
- LLM calls: p95 < 10 seconds
- Authorization checks: p95 < 50ms
- JWT validation: p95 < 2ms

Monitor with Prometheus queries:
```promql
histogram_quantile(0.95, rate(agent_response_duration_bucket[5m]))
rate(agent_calls_failed_total[5m])
```

## Common Issues

### OpenFGA Not Configured
**Symptom**: "OpenFGA not available, using fallback mode"
**Solution**: Run `make setup-openfga` and update .env with STORE_ID and MODEL_ID

### Test Failures Due to Missing Infrastructure
**Symptom**: Integration tests fail with connection errors
**Solution**: Run `make setup-infra` before tests, or use `-m unit` for unit tests only

### LLM API Key Issues
**Symptom**: "API key not found" or authentication errors
**Solution**: Set provider API key in .env (GOOGLE_API_KEY, ANTHROPIC_API_KEY, etc.)

### Import Errors
**Symptom**: ModuleNotFoundError
**Solution**: Run `make install-dev` to ensure all dependencies are installed

## Deployment

### Docker
```bash
docker build -t langgraph-agent:latest .
docker run -p 8000:8000 --env-file .env langgraph-agent:latest
```

### Kubernetes
```bash
# Helm
helm install langgraph-agent ./helm/langgraph-agent \
  --namespace langgraph-agent \
  --create-namespace

# Kustomize
kubectl apply -k kustomize/overlays/production
```

### LangGraph Platform
```bash
langgraph login
langgraph deploy
```

## Pydantic AI Integration

The project uses Pydantic AI for type-safe agent responses:

**Key Features**:
- **Type-safe routing**: Structured routing decisions with confidence scores
- **Validated responses**: LLM outputs conforming to Pydantic models
- **Structured streaming**: Type-safe streaming chunks with validation

**Usage**:
```python
from pydantic_ai_agent import create_pydantic_agent

agent = create_pydantic_agent()

# Route with type-safe decision
decision = await agent.route_message("Search for Python tutorials")
print(decision.action)      # "use_tools"
print(decision.confidence)  # 0.92

# Generate validated response
response = await agent.generate_response(messages)
print(response.content)
print(response.confidence)
```

**See**: `docs/PYDANTIC_AI_INTEGRATION.md` for complete guide

## Key Files Reference

- **agent.py**: LangGraph agent with Pydantic AI type-safe routing
- **pydantic_ai_agent.py**: Pydantic AI wrapper for structured responses
- **llm_validators.py**: Response validation utilities
- **mcp_streaming.py**: Type-safe streaming with validation
- **llm_factory.py**: Multi-provider LLM abstraction with fallback
- **mcp_server_streamable.py**: StreamableHTTP MCP server (production)
- **mcp_server.py**: stdio MCP server (Claude Desktop)
- **auth.py**: JWT authentication + OpenFGA integration
- **openfga_client.py**: Authorization client and model definitions
- **config.py**: Pydantic Settings configuration with Infisical
- **observability.py**: OpenTelemetry + LangSmith setup
- **secrets_manager.py**: Infisical wrapper for secure secrets
- **health_check.py**: Health check endpoints (liveness/readiness)

## Environment Variables

Critical variables (add to .env):
```bash
# OpenFGA (required)
OPENFGA_STORE_ID=<from setup_openfga.py>
OPENFGA_MODEL_ID=<from setup_openfga.py>

# LLM Provider (at least one required)
GOOGLE_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>

# JWT (production required)
JWT_SECRET_KEY=<secure-random-string>

# Optional
LANGSMITH_API_KEY=<your-key>
LANGSMITH_TRACING=true
INFISICAL_CLIENT_ID=<your-id>
INFISICAL_CLIENT_SECRET=<your-secret>
```

## Testing Strategy

### Unit Tests (Fast, No External Dependencies)
- Mock LLM responses
- Mock OpenFGA client
- Mock Infisical client
- Test pure logic and validation

### Integration Tests (Require Infrastructure)
- Real OpenFGA instance
- Real observability stack
- Test end-to-end flows
- Verify authorization logic

### Benchmark Tests
- Performance-critical paths
- LLM latency tracking
- Authorization overhead
- End-to-end agent response time

Run with: `pytest -m benchmark --benchmark-only --benchmark-autosave`
