---
purpose: Backend Python patterns for core infrastructure and API development
priority: high
category: patterns
codebase-size: ~100 source files, 101+ ADRs
last-updated: 2026-02-05
---

# Backend Code Patterns

Python patterns for the mcp-server-langgraph backend.

**See also**: [Frontend patterns](code-patterns-frontend.md)

---

## Project Structure

```
src/mcp_server_langgraph/
├── core/                     # Core functionality
│   ├── agent.py             # LangGraph agent (functional API)
│   ├── config.py            # Settings (Pydantic BaseSettings)
│   ├── feature_flags.py     # Feature flag system
│   └── compliance/          # GDPR, HIPAA, SOC2
├── auth/                    # Authentication & authorization
│   ├── middleware.py        # JWT auth middleware
│   ├── keycloak.py         # Keycloak SSO integration
│   ├── session.py          # Session management (InMemory, Redis)
│   └── openfga.py          # Fine-grained authorization
├── llm/                     # LLM factory and utilities
│   ├── factory.py          # LiteLLM multi-provider factory
│   └── pydantic_agent.py   # Type-safe routing
├── mcp/                     # MCP server implementations
│   ├── server_stdio.py     # stdio transport
│   └── server_streamable.py # StreamableHTTP transport
├── api/                     # REST API endpoints
├── tools/                   # Agent tools
├── observability/           # OpenTelemetry setup
└── secrets/                 # Infisical integration
```

---

## Pattern 1: Pydantic Settings for Configuration

**Location**: `src/mcp_server_langgraph/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    service_name: str = "mcp-server-langgraph"
    log_level: str = "INFO"
    environment: str = "development"

    # Feature flags
    enable_pydantic_ai_routing: bool = True
    enable_llm_fallback: bool = True

    # API keys (loaded from env or Infisical)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Infrastructure
    redis_url: str = "redis://localhost:6379"
    openfga_api_url: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Singleton instance
settings = Settings()
```

**Key Points**: Extends `BaseSettings` for auto env var loading, provide sensible defaults, export singleton.

---

## Pattern 2: Factory Pattern for Dependency Injection

**Location**: `src/mcp_server_langgraph/llm/factory.py`

```python
def create_llm_from_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ChatLiteLLM:
    """Create LLM client from configuration. Supports 100+ providers."""
    from mcp_server_langgraph.core.config import settings

    final_provider = provider or settings.llm_provider
    final_model = model or settings.model_name

    if final_provider == "anthropic":
        api_key = kwargs.get("api_key", settings.anthropic_api_key)
    elif final_provider == "openai":
        api_key = kwargs.get("api_key", settings.openai_api_key)
    else:
        api_key = kwargs.get("api_key")

    return ChatLiteLLM(model=final_model, api_key=api_key, **kwargs)
```

**Key Points**: Allow override + fallback to config, support multiple providers with same interface.

---

## Pattern 3: Abstract Base Class with Multiple Implementations

**Location**: `src/mcp_server_langgraph/auth/session.py`

```python
from abc import ABC, abstractmethod

class SessionStore(ABC):
    """Abstract base class for session storage"""

    @abstractmethod
    async def create(self, user_id: str, roles: list[str]) -> str:
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionData]:
        pass

class InMemorySessionStore(SessionStore):
    """In-memory session storage for development"""
    def __init__(self, default_ttl_seconds: int = 3600):
        self._sessions: dict[str, SessionData] = {}

class RedisSessionStore(SessionStore):
    """Redis-backed session storage for production"""
    def __init__(self, redis_url: str):
        self._redis = redis.asyncio.from_url(redis_url)

# Factory function
def create_session_store(backend: str = "inmemory") -> SessionStore:
    if backend == "inmemory":
        return InMemorySessionStore()
    elif backend == "redis":
        return RedisSessionStore(redis_url=settings.redis_url)
    raise ValueError(f"Unknown backend: {backend}")
```

**Key Points**: Use `ABC` + `@abstractmethod`, factory to instantiate correct implementation.

---

## Pattern 4: Async Context Managers for Resource Management

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def get_redis_connection() -> AsyncGenerator[Redis, None]:
    """Async context manager for Redis connections"""
    redis = await redis.asyncio.from_url(settings.redis_url)
    try:
        yield redis
    finally:
        await redis.close()

# Usage
async def store_data(key: str, value: str):
    async with get_redis_connection() as redis:
        await redis.set(key, value, ex=3600)
```

**Key Points**: Use `@asynccontextmanager`, yield in try block, cleanup in finally.

---

## Pattern 5: Pydantic Models for Data Validation

```python
from pydantic import BaseModel, Field, validator

class SessionData(BaseModel):
    """Session data model with validation"""
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., pattern=r"^user:[a-z0-9_-]+$")
    roles: list[str] = Field(default_factory=list)
    expires_at: datetime

    @validator("roles")
    def validate_roles(cls, v):
        if not v:
            raise ValueError("At least one role is required")
        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

**Key Points**: Use `Field()` for constraints, `@validator` for complex validation.

---

## Pattern 6: Feature Flags for Gradual Rollout

**Location**: `src/mcp_server_langgraph/core/feature_flags.py`

```python
class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout"""
    enable_pydantic_ai_routing: bool = Field(
        default=True,
        description="Enable type-safe routing with Pydantic AI"
    )
    enable_llm_fallback: bool = Field(default=True)
    openfga_strict_mode: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> "FeatureFlags":
        import os
        return cls(
            enable_pydantic_ai_routing=os.getenv("FF_ENABLE_PYDANTIC_AI_ROUTING", "true").lower() == "true",
        )

feature_flags = FeatureFlags.from_env()

# Usage
if feature_flags.enable_pydantic_ai_routing:
    return pydantic_ai_router(request)
```

**Key Points**: Centralized config, env var support (FF_ prefix), default to safe behavior.

---

## Pattern 7: Observability with OpenTelemetry

**Location**: `src/mcp_server_langgraph/observability/telemetry.py`

```python
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter("http.requests.total")
request_duration = meter.create_histogram("http.request.duration", unit="ms")

async def handle_request(request):
    with tracer.start_as_current_span("handle_request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("user.id", request.user_id)
        try:
            result = await process(request)
            span.set_status(Status(StatusCode.OK))
            request_counter.add(1, {"status": "success"})
            return result
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            request_counter.add(1, {"status": "error"})
            raise
```

**Key Points**: Get tracer/meter per module, add attributes for context, record exceptions.

---

## Pattern 8: Error Handling with Graceful Degradation

```python
async def get_user_with_fallback(user_id: str) -> Optional[User]:
    """Get user with fallback to cache. Returns None if all sources fail."""
    try:
        user = await primary_user_store.get(user_id)
        if user:
            return user
    except Exception as e:
        logger.warning(f"Primary user store failed: {e}")

    try:
        user = await cache.get(f"user:{user_id}")
        if user:
            logger.info(f"Served user {user_id} from cache")
            return user
    except Exception as e:
        logger.warning(f"Cache failed: {e}")

    logger.error(f"All sources failed for user {user_id}")
    return None  # Graceful degradation
```

**Key Points**: Try primary first, fallback to cache, return None instead of raising.

---

## Pattern 9: Async Batch Operations

**Location**: `src/mcp_server_langgraph/core/dynamic_context_loader.py`

```python
import asyncio

async def load_batch(items: List[str], max_concurrent: int = 5) -> List[Result]:
    """Load items concurrently with parallelism limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def load_one(item: str) -> Result:
        async with semaphore:
            return await fetch(item)

    results = await asyncio.gather(
        *[load_one(item) for item in items],
        return_exceptions=True  # Don't fail batch on single error
    )
    return results
```

**Key Points**: Use `Semaphore` for concurrency limit, `gather` for parallel execution, preserve order.

---

## Pattern 10: Type-Safe API Responses

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """Type-safe API response wrapper"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def success_response(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def error_response(cls, error: str) -> "APIResponse[T]":
        return cls(success=False, error=error)

# Usage
async def get_user(user_id: str) -> APIResponse[UserData]:
    try:
        user = await user_store.get(user_id)
        if user:
            return APIResponse.success_response(data=UserData(...))
        return APIResponse.error_response(error="User not found")
    except Exception as e:
        return APIResponse.error_response(error=str(e))
```

**Key Points**: Generic types for reusable wrappers, factory methods, consistent structure.

---

## Related Documents

- **Frontend Patterns**: `context/code-patterns-frontend.md`
- **Testing Patterns**: `context/testing-patterns.md`
- **API Schema Transforms**: `context/api-schema-patterns.md`
- **Architecture**: `adr/README.md` (101+ ADRs)
