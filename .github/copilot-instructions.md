# GitHub Copilot Instructions for MCP Server with LangGraph

## Project Context

You are working on a **production-ready LangGraph agent** with Model Context Protocol (MCP) implementation. This is enterprise-grade software with:

- **Multi-LLM Support**: 100+ providers via LiteLLM
- **Security**: JWT auth + OpenFGA fine-grained authorization
- **Secrets**: Infisical integration
- **Observability**: OpenTelemetry (traces, metrics, logs)
- **Deployment**: Kubernetes with Helm/Kustomize

## Code Style

### Python Standards
- **Black formatter**: 127 character line length
- **Type hints**: Always required for public APIs
- **Docstrings**: Google-style for all public functions
- **Import order**: Standard → Third-party → Local (via isort)

```python
# Example
def process_message(message: str, user_id: str) -> AgentResponse:
    """
    Process a user message through the agent.

    Args:
        message: The user's input message
        user_id: Unique user identifier

    Returns:
        AgentResponse with the agent's reply

    Raises:
        AuthorizationError: If user lacks permissions
    """
    pass
```

### Testing Standards
- Mark all tests: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
- Mock external services (LLMs, OpenFGA, Infisical)
- Aim for >80% coverage on critical paths

```python
@pytest.mark.unit
def test_process_message_success():
    """Test message processing with valid input."""
    # Arrange
    message = "Hello, agent"
    user_id = "user-123"

    # Act
    response = process_message(message, user_id)

    # Assert
    assert response.status == "success"
    assert len(response.content) > 0
```

## Security Requirements

### Authentication
- **Never** hardcode secrets
- Use `settings.jwt_secret_key` from config
- Validate tokens on every request
- Log all auth failures

```python
# ✅ Good
token = settings.jwt_secret_key

# ❌ Bad
token = "hardcoded-secret"
```

### Authorization
- Check OpenFGA before protected operations
- Use principle of least privilege
- Log authorization failures with context

```python
# Always check authorization
allowed = await openfga_client.check(
    user=f"user:{user_id}",
    relation="viewer",
    object=f"document:{doc_id}"
)
if not allowed:
    logger.warning("Authorization denied", extra={"user_id": user_id, "doc_id": doc_id})
    raise PermissionError("Not authorized")
```

## Observability

### Tracing
- Wrap major operations in spans
- Set meaningful span attributes
- Use `with tracer.start_as_current_span()` pattern

```python
with tracer.start_as_current_span("process_llm_request") as span:
    span.set_attribute("user_id", user_id)
    span.set_attribute("model", model_name)
    span.set_attribute("message.length", len(message))

    response = await llm_client.complete(message)
```

### Logging
- Use structured logging with context
- Include trace IDs automatically
- Log at appropriate levels (INFO for normal, ERROR for failures)

```python
logger.info(
    "Processing user request",
    extra={"user_id": user_id, "tool": "chat", "message_length": len(message)}
)
```

### Metrics
- Increment counters for important events
- Use histograms for latency tracking

```python
metrics.tool_calls.add(1, {"tool": "chat"})
metrics.response_time.record(duration_ms, {"tool": "chat"})
```

## API Design

### FastAPI Endpoints
- Use Pydantic models for validation
- Include OpenAPI documentation
- Handle errors gracefully

```python
class ChatRequest(BaseModel):
    """Chat request schema."""
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    user_id: str = Field(..., description="User identifier")

@app.post("/api/chat", response_model=ChatResponse, tags=["mcp"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message.

    Requires authentication and authorization.
    """
    pass
```

### Error Responses
- Use appropriate HTTP status codes
- Return structured error messages
- Don't expose internal details

```python
raise HTTPException(
    status_code=403,
    detail="Insufficient permissions to access this resource"
)
```

## LangGraph Patterns

### State Management
- Use typed state classes
- Implement proper checkpointing
- Keep state immutable where possible

```python
from typing import TypedDict

class AgentState(TypedDict):
    """Agent state schema."""
    messages: list[dict]
    user_id: str
    thread_id: str
    context: dict
```

### Tool Implementation
- Define clear input schemas
- Add comprehensive error handling
- Include authorization checks

```python
@agent_graph.tool
async def search_documents(query: str, user_id: str) -> str:
    """
    Search documents accessible to the user.

    Args:
        query: Search query
        user_id: User making the request

    Returns:
        Search results as formatted string
    """
    # Check authorization
    # Execute search
    # Return results
    pass
```

## Common Tasks

### Adding a New Tool

1. **Define the tool function** in `agent.py`
2. **Create input schema** with Pydantic
3. **Add authorization check**
4. **Implement telemetry** (spans, metrics, logs)
5. **Write tests** (unit + integration)
6. **Update documentation**

### Adding Environment Variables

1. **Add to `.env.example`** with description
2. **Add to `config.py`** with type and validation
3. **Add to Kubernetes secrets** if sensitive
4. **Update documentation**

### Adding Dependencies

1. **Add to `requirements.txt`** (unpinned)
2. **Pin in `requirements-pinned.txt`**
3. **Add to `pyproject.toml`** if needed
4. **Test thoroughly**
5. **Update CHANGELOG.md**

## Performance Targets

- **Agent response**: p95 < 5 seconds
- **LLM calls**: p95 < 10 seconds
- **Authorization checks**: p95 < 50ms
- **JWT validation**: p95 < 2ms

Optimize accordingly and add benchmarks for critical paths.

## Async Patterns

### Use async for I/O
```python
# ✅ Good
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ❌ Bad (blocking)
def fetch_data():
    response = requests.get(url)
    return response.json()
```

### Concurrent Operations
```python
# Run multiple operations concurrently
results = await asyncio.gather(
    fetch_user_data(user_id),
    fetch_permissions(user_id),
    fetch_preferences(user_id)
)
```

## Error Handling

### Specific Exceptions
```python
# ✅ Good
try:
    result = await dangerous_operation()
except OpenFGAError as e:
    logger.error("Authorization service failed", exc_info=e)
    raise ServiceUnavailableError("Authorization temporarily unavailable")
except LLMError as e:
    logger.error("LLM request failed", exc_info=e)
    raise
```

### Context Managers
```python
# Always clean up resources
async with tracer.start_as_current_span("operation"):
    try:
        result = await perform_operation()
    except Exception as e:
        logger.error("Operation failed", exc_info=e)
        raise
    finally:
        await cleanup_resources()
```

## Kubernetes Considerations

### Health Checks
```python
@app.get("/health/live")
async def liveness():
    """Liveness probe - is the service running?"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """Readiness probe - can the service handle traffic?"""
    # Check dependencies
    return {"status": "ready"}
```

### Graceful Shutdown
```python
@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await close_database_connections()
    await flush_metrics()
    logger.info("Application shutdown complete")
```

## Documentation

### Code Comments
- Explain **why**, not **what**
- Update comments when code changes
- Remove obsolete comments

### API Documentation
- Keep OpenAPI schemas updated
- Provide request/response examples
- Document error codes

## What to Avoid

### Security
- ❌ Hardcoded secrets
- ❌ Skipping authorization checks
- ❌ Exposing internal errors
- ❌ Logging sensitive data

### Performance
- ❌ Synchronous I/O in request handlers
- ❌ N+1 queries
- ❌ Unbounded loops
- ❌ Memory leaks

### Code Quality
- ❌ Missing type hints
- ❌ Untested code
- ❌ Magic numbers
- ❌ Deep nesting (> 3 levels)

## Useful Commands

```bash
# Run tests
pytest -m unit -v
pytest -m integration -v

# Format code
black . --exclude venv
isort . --skip venv

# Lint
flake8 . --exclude venv
mypy *.py

# Security scan
bandit -r . -x ./tests,./venv -ll

# Run server
python mcp_server_streamable.py

# Generate OpenAPI
python scripts/generate_openapi.py
```

## Key Files

- `agent.py` - LangGraph agent implementation
- `mcp_server_streamable.py` - MCP StreamableHTTP server
- `auth.py` - JWT authentication
- `openfga_client.py` - Authorization client
- `config.py` - Configuration management
- `observability.py` - OpenTelemetry setup

## Resources

- **Architecture**: See `README.md` and `docs/architecture/` (ADRs)
- **Deployment**: See `docs/deployment/` (Kubernetes, Helm, Cloud Run, LangGraph Platform)
- **Security**: See `SECURITY.md` and `docs/security/`
- **Contributing**: See `CONTRIBUTING.md` and `docs/advanced/contributing.mdx`
- **Development**: See `docs/advanced/development-setup.mdx`
- **Testing**: See `docs/advanced/testing.mdx`
- **Mintlify Docs**: See `docs/mint.json` (100% coverage)

## Current Project State (2025-10-14)

- **LangGraph Version**: 0.6.10 (upgraded from 0.2.28 - all 15 Dependabot PRs merged)
- **Documentation**: Mintlify integration complete with docs/ directory structure
- **Test Coverage**: High coverage across all modules
- **Production Ready**: Full observability, security, and compliance features
