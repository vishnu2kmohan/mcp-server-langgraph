# OpenAI Codex Instructions for MCP Server with LangGraph

## Project Overview

This is a **production-ready LangGraph agent** implementing the Model Context Protocol (MCP) with enterprise-grade features:

- **Multi-LLM Support**: 100+ providers via LiteLLM (Anthropic, OpenAI, Google, Azure, AWS)
- **Security**: JWT authentication + OpenFGA fine-grained authorization
- **Secrets Management**: Infisical integration with fallback to environment variables
- **Observability**: OpenTelemetry (distributed tracing, metrics, structured logging)
- **Deployment**: Kubernetes-ready with Helm charts and Kustomize overlays

## Code Style Standards

### Python Formatting
```python
# Line length: 127 characters (Black formatter)
# Type hints: Required for all public functions
# Docstrings: Google style for all public APIs

def process_request(message: str, user_id: str, thread_id: str | None = None) -> AgentResponse:
    """
    Process a user request through the LangGraph agent.

    Args:
        message: User input message to process
        user_id: Unique identifier for the authenticated user
        thread_id: Optional conversation thread identifier for context

    Returns:
        AgentResponse containing the agent's reply and metadata

    Raises:
        AuthorizationError: If user lacks required permissions
        ValidationError: If input validation fails
    """
    pass
```

### Import Organization
```python
# Standard library imports
import asyncio
import json
from typing import Any, Dict, List

# Third-party imports
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Local imports
from agent import agent_graph
from auth import AuthMiddleware
from observability import tracer, logger, metrics
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `AgentState`, `MCPServer`)
- **Functions/Methods**: `snake_case` (e.g., `process_message`, `validate_token`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private methods**: `_leading_underscore` (e.g., `_internal_helper`)

## Architecture Patterns

### 1. Agent Design (LangGraph)
```python
from langgraph.graph import StateGraph
from typing import TypedDict

class AgentState(TypedDict):
    """State schema for the agent."""
    messages: list[dict]
    user_id: str
    thread_id: str
    context: dict

# Define agent graph
graph = StateGraph(AgentState)
graph.add_node("process", process_node)
graph.add_node("respond", respond_node)
graph.add_edge("process", "respond")
agent = graph.compile()
```

### 2. Authentication Flow
```python
from auth import AuthMiddleware

# Always validate JWT tokens
auth = AuthMiddleware(secret_key=settings.jwt_secret_key)

async def protected_endpoint(request: Request):
    # Validate token
    user_id = await auth.verify_token(request.headers.get("Authorization"))

    # Check authorization
    allowed = await openfga_client.check(
        user=f"user:{user_id}",
        relation="viewer",
        object=f"resource:{resource_id}"
    )

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
```

### 3. Observability Pattern
```python
from observability import tracer, logger, metrics

async def process_llm_request(prompt: str, model: str) -> str:
    """Process LLM request with full observability."""
    with tracer.start_as_current_span("llm_request") as span:
        # Add span attributes
        span.set_attribute("model", model)
        span.set_attribute("prompt.length", len(prompt))

        # Structured logging
        logger.info(
            "Processing LLM request",
            extra={"model": model, "prompt_length": len(prompt)}
        )

        try:
            # Make LLM call
            start_time = time.time()
            response = await llm_client.complete(prompt, model=model)
            duration = (time.time() - start_time) * 1000

            # Record metrics
            metrics.llm_duration.record(duration, {"model": model})
            metrics.llm_requests.add(1, {"model": model, "status": "success"})

            return response

        except Exception as e:
            logger.error("LLM request failed", exc_info=e, extra={"model": model})
            metrics.llm_requests.add(1, {"model": model, "status": "error"})
            raise
```

## Security Requirements

### 1. Never Hardcode Secrets
```python
# ✅ GOOD - Use configuration
from config import settings
jwt_secret = settings.jwt_secret_key
openfga_api_key = settings.openfga_api_key

# ❌ BAD - Hardcoded secrets
jwt_secret = "my-secret-key-123"
api_key = "sk-1234567890abcdef"
```

### 2. Input Validation
```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    """Validated chat request schema."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message"
    )
    user_id: str = Field(..., regex=r"^[a-zA-Z0-9_-]+$")

    @validator("message")
    def sanitize_message(cls, v):
        # Remove control characters
        return "".join(char for char in v if char.isprintable() or char in "\n\t")
```

### 3. Authorization Checks
```python
async def access_document(doc_id: str, user_id: str) -> dict:
    """Access a document with authorization check."""
    # ALWAYS check authorization before data access
    allowed = await openfga_client.check(
        user=f"user:{user_id}",
        relation="viewer",
        object=f"document:{doc_id}"
    )

    if not allowed:
        logger.warning(
            "Unauthorized document access attempt",
            extra={"user_id": user_id, "doc_id": doc_id}
        )
        raise PermissionError("Not authorized to access this document")

    # Proceed with data access
    return await fetch_document(doc_id)
```

### 4. Secure Logging
```python
# ✅ GOOD - Log IDs and metadata, not sensitive data
logger.info("User authenticated", extra={"user_id": user_id})

# ❌ BAD - Never log passwords, tokens, or secrets
logger.info(f"Password: {password}")  # NEVER DO THIS
logger.info(f"Token: {jwt_token}")    # NEVER DO THIS
```

## API Design Patterns

### FastAPI Endpoints
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI(
    title="MCP Server with LangGraph",
    description="Production-ready AI agent with MCP",
    version="1.0.0"
)

class ChatRequest(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    metadata: dict

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    status_code=200,
    tags=["mcp"],
    summary="Process chat message",
    description="Send a message to the AI agent and receive a response"
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message through the agent.

    Requires authentication via JWT token in Authorization header.
    """
    with tracer.start_as_current_span("api_chat"):
        # Validate and process
        result = await agent_graph.invoke({
            "messages": [{"role": "user", "content": request.message}],
            "user_id": request.user_id
        })

        return ChatResponse(
            reply=result["messages"][-1]["content"],
            thread_id=result["thread_id"],
            metadata=result.get("metadata", {})
        )
```

### Error Handling
```python
from fastapi import HTTPException

async def handle_request(request_data: dict):
    """Handle request with proper error handling."""
    try:
        result = await process_request(request_data)
        return result

    except ValidationError as e:
        # Input validation failed
        raise HTTPException(
            status_code=422,
            detail=f"Invalid input: {str(e)}"
        )

    except PermissionError as e:
        # Authorization failed
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

    except OpenFGAError as e:
        # Authorization service unavailable
        logger.error("OpenFGA service error", exc_info=e)
        raise HTTPException(
            status_code=503,
            detail="Authorization service temporarily unavailable"
        )

    except Exception as e:
        # Unexpected error
        logger.error("Unexpected error", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

## Testing Patterns

### Unit Tests
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.unit
async def test_process_message_success():
    """Test message processing with valid input."""
    # Arrange
    message = "Hello, agent"
    user_id = "user-123"
    mock_llm = AsyncMock(return_value="Hello! How can I help?")

    # Act
    result = await process_message(message, user_id, llm_client=mock_llm)

    # Assert
    assert result.status == "success"
    assert len(result.reply) > 0
    mock_llm.assert_called_once()

@pytest.mark.unit
async def test_process_message_unauthorized():
    """Test message processing with unauthorized user."""
    # Arrange
    message = "Hello"
    user_id = "user-unauthorized"

    # Act & Assert
    with pytest.raises(PermissionError):
        await process_message(message, user_id)
```

### Integration Tests
```python
@pytest.mark.integration
async def test_full_chat_flow():
    """Test complete chat flow with real services."""
    # Arrange
    async with TestClient(app) as client:
        # Authenticate
        token = await get_test_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Act
        response = await client.post(
            "/api/v1/chat",
            json={"message": "Test message", "user_id": "test-user"},
            headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "thread_id" in data
```

### Performance Benchmarks
```python
@pytest.mark.benchmark
def test_jwt_validation_performance(benchmark):
    """Benchmark JWT validation speed."""
    token = generate_test_token()

    def validate():
        return verify_jwt_token(token)

    result = benchmark(validate)

    # Assert performance target: < 2ms
    assert benchmark.stats["mean"] < 0.002
```

## Async Patterns

### Concurrent Operations
```python
async def fetch_user_context(user_id: str) -> dict:
    """Fetch user context with concurrent operations."""
    # Run multiple operations concurrently
    user_data, permissions, preferences = await asyncio.gather(
        fetch_user_data(user_id),
        fetch_user_permissions(user_id),
        fetch_user_preferences(user_id)
    )

    return {
        "user": user_data,
        "permissions": permissions,
        "preferences": preferences
    }
```

### Proper Resource Cleanup
```python
async def process_with_cleanup(request_data: dict):
    """Process request with guaranteed cleanup."""
    async with tracer.start_as_current_span("process_request"):
        connection = None
        try:
            connection = await get_connection()
            result = await process_data(connection, request_data)
            return result
        finally:
            if connection:
                await connection.close()
```

## Performance Targets

| Operation | Target (p95) | How to Achieve |
|-----------|--------------|----------------|
| Agent response | < 5 seconds | Async LLM calls, caching |
| LLM call | < 10 seconds | Provider selection, streaming |
| Authorization check | < 50ms | Connection pooling, caching |
| JWT validation | < 2ms | Efficient crypto, no I/O |

### Optimization Example
```python
from functools import lru_cache

# Cache OpenFGA model definitions (they rarely change)
@lru_cache(maxsize=1)
async def get_openfga_model():
    """Get OpenFGA model with caching."""
    return await openfga_client.get_model()

# Use connection pooling for database
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

## Common Tasks

### Adding a New Tool to the Agent
```python
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(10, ge=1, le=100)

@agent_graph.tool
async def search_documents(
    query: str,
    max_results: int,
    user_id: str
) -> str:
    """
    Search documents accessible to the user.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        user_id: User performing the search

    Returns:
        Formatted search results as string
    """
    with tracer.start_as_current_span("search_documents") as span:
        span.set_attribute("query", query)
        span.set_attribute("user_id", user_id)

        # Check authorization
        allowed = await openfga_client.check(
            user=f"user:{user_id}",
            relation="searcher",
            object="system:search"
        )

        if not allowed:
            raise PermissionError("Not authorized to search")

        # Perform search
        results = await search_service.search(query, max_results, user_id)

        # Log and return
        logger.info(
            "Search completed",
            extra={"user_id": user_id, "results_count": len(results)}
        )

        return format_search_results(results)
```

### Adding Environment Variables
```python
# 1. Add to .env.example
"""
# Search Configuration
SEARCH_API_URL=http://localhost:9200
SEARCH_API_KEY=change-in-production
MAX_SEARCH_RESULTS=100
"""

# 2. Add to config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # Search configuration
    search_api_url: str = "http://localhost:9200"
    search_api_key: str = Field(..., min_length=32)
    max_search_results: int = Field(100, ge=1, le=1000)

    class Config:
        env_file = ".env"

# 3. Use in code
from config import settings

search_client = SearchClient(
    url=settings.search_api_url,
    api_key=settings.search_api_key
)
```

## What to Avoid

### Security Anti-Patterns
```python
# ❌ BAD - Hardcoded secrets
API_KEY = "sk-1234567890"

# ❌ BAD - SQL injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# ❌ BAD - Logging sensitive data
logger.info(f"Password: {password}")

# ❌ BAD - Missing authorization
def get_document(doc_id):
    return database.fetch(doc_id)  # No auth check!
```

### Performance Anti-Patterns
```python
# ❌ BAD - Synchronous I/O in async function
async def fetch_data():
    response = requests.get(url)  # Blocking!
    return response.json()

# ❌ BAD - N+1 queries
async def get_users_with_posts():
    users = await fetch_users()
    for user in users:
        user.posts = await fetch_posts(user.id)  # N queries!

# ❌ BAD - No timeout
async def call_external_api():
    response = await client.get(url)  # Hangs forever if slow
```

### Code Quality Anti-Patterns
```python
# ❌ BAD - Missing type hints
def process(data):
    return data["result"]

# ❌ BAD - No docstring
def complex_calculation(x, y, z):
    return (x * y) / z if z != 0 else 0

# ❌ BAD - Deep nesting
async def process_request(request):
    if request.valid:
        if request.authorized:
            if request.data:
                if request.data.complete:
                    # Too deep!
```

## File Structure Reference

```
mcp_server_langgraph/
├── agent.py                  # LangGraph agent implementation
├── mcp_server.py             # MCP stdio transport
├── mcp_server_streamable.py # MCP StreamableHTTP transport
├── mcp_server_http.py        # MCP HTTP/SSE transport
├── auth.py                   # JWT authentication
├── openfga_client.py         # Authorization client
├── secrets_manager.py        # Infisical integration
├── observability.py          # OpenTelemetry setup
├── config.py                 # Configuration management
├── llm_factory.py            # LLM client factory
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── performance/          # Benchmark tests
└── scripts/
    ├── validate_production.py
    └── generate_openapi.py
```

## Useful Commands

```bash
# Run all tests
pytest -v

# Run specific test types
pytest -m unit -v
pytest -m integration -v
pytest -m benchmark -v

# Format code
black . --exclude venv
isort . --skip venv

# Lint code
flake8 . --exclude venv
mypy *.py --ignore-missing-imports

# Security scan
bandit -r . -x ./tests,./venv -ll

# Run development server
python mcp_server_streamable.py

# Generate OpenAPI schema
python scripts/generate_openapi.py

# Validate production readiness
python scripts/validate_production.py
```

## Resources

- **README.md** - Project overview and quick start
- **DEVELOPMENT.md** - Development environment setup
- **CONTRIBUTING.md** - Contribution guidelines
- **TESTING.md** - Testing strategy and examples
- **SECURITY_AUDIT.md** - Security checklist
- **KUBERNETES_DEPLOYMENT.md** - Deployment guide
- **API Docs** - http://localhost:8000/docs (when running)

## Quick Reference

### Import What You Need
```python
# Configuration
from config import settings

# Authentication
from auth import AuthMiddleware, verify_token

# Authorization
from openfga_client import OpenFGAClient

# Observability
from observability import tracer, logger, metrics

# Agent
from agent import agent_graph, AgentState

# LLM
from llm_factory import create_llm_client
```

### Common Patterns
```python
# Async endpoint with auth + authz + observability
@app.post("/api/resource")
async def create_resource(
    request: ResourceRequest,
    user_id: str = Depends(get_current_user)
):
    with tracer.start_as_current_span("create_resource"):
        # Authorize
        if not await check_permission(user_id, "create", "resource"):
            raise HTTPException(403)

        # Process
        result = await process_resource(request)

        # Log
        logger.info("Resource created", extra={"user_id": user_id})

        return result
```

This codebase prioritizes **security, performance, observability, and maintainability**. Follow these patterns and you'll write production-ready code that integrates seamlessly with the existing architecture.
