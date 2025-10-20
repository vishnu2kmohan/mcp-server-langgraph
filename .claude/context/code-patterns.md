# Code Patterns Context

**Last Updated**: 2025-10-20
**Purpose**: Common code patterns and conventions in mcp-server-langgraph
**Codebase Size**: ~100 source files, 25 ADRs, 77 doc pages

---

## 📊 Project Structure

```
src/mcp_server_langgraph/
├── core/                     # Core functionality
│   ├── agent.py             # LangGraph agent (functional API)
│   ├── config.py            # Settings (Pydantic BaseSettings)
│   ├── feature_flags.py     # Feature flag system
│   ├── context_manager.py   # Context & note-taking
│   └── compliance/          # GDPR, HIPAA, SOC2
├── auth/                    # Authentication & authorization
│   ├── middleware.py        # JWT auth middleware
│   ├── keycloak.py         # Keycloak SSO integration
│   ├── session.py          # Session management (InMemory, Redis)
│   ├── role_mapper.py      # Advanced role mapping
│   └── openfga.py          # Fine-grained authorization
├── llm/                     # LLM factory and utilities
│   ├── factory.py          # LiteLLM multi-provider factory
│   └── pydantic_agent.py   # Type-safe routing
├── mcp/                     # MCP server implementations
│   ├── server_stdio.py     # stdio transport
│   └── server_streamable.py # StreamableHTTP transport
├── api/                     # REST API endpoints
│   └── gdpr.py             # GDPR compliance endpoints
├── tools/                   # Agent tools
│   └── search_tools.py     # Web & knowledge base search
├── observability/           # Telemetry and monitoring
│   └── telemetry.py        # OpenTelemetry setup
└── secrets/                 # Secrets management
    └── manager.py          # Infisical integration
```

---

## 🎯 Core Design Patterns

### Pattern 1: Pydantic Settings for Configuration

**Location**: `src/mcp_server_langgraph/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Core settings
    service_name: str = "mcp-server-langgraph"
    log_level: str = "INFO"
    environment: str = "development"

    # Feature flags
    enable_pydantic_ai_routing: bool = True
    enable_llm_fallback: bool = True
    enable_openfga: bool = True

    # API keys (loaded from env or Infisical)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Infrastructure
    redis_url: str = "redis://localhost:6379"
    openfga_api_url: str = "http://localhost:8080"
    qdrant_url: str = "localhost"
    qdrant_port: int = 6333

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Singleton instance
settings = Settings()
```

**Key Points**:
- Extends `BaseSettings` for auto env var loading
- Use `Optional[str]` for optional settings
- Provide sensible defaults
- Use `Config` class for `.env` support
- Export singleton instance

---

### Pattern 2: Factory Pattern for Dependency Injection

**Location**: `src/mcp_server_langgraph/llm/factory.py`

```python
from typing import Optional
from litellm import completion

def create_llm_from_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ChatLiteLLM:
    """
    Create LLM client from configuration.

    Supports 100+ providers via LiteLLM.
    Falls back to env vars if not provided.
    """
    from mcp_server_langgraph.core.config import settings

    # Use provided or fall back to settings
    final_provider = provider or settings.llm_provider
    final_model = model or settings.model_name

    # Provider-specific configuration
    if final_provider == "anthropic":
        api_key = kwargs.get("api_key", settings.anthropic_api_key)
    elif final_provider == "openai":
        api_key = kwargs.get("api_key", settings.openai_api_key)
    elif final_provider == "google":
        api_key = kwargs.get("api_key", settings.google_api_key)
    else:
        api_key = kwargs.get("api_key")

    # Create client
    return ChatLiteLLM(
        model=final_model,
        api_key=api_key,
        **kwargs
    )
```

**Key Points**:
- Factory function pattern for complex object creation
- Allow override parameters + fallback to config
- Support multiple providers with same interface
- Document supported providers

---

### Pattern 3: Abstract Base Class with Multiple Implementations

**Location**: `src/mcp_server_langgraph/auth/session.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

class SessionStore(ABC):
    """Abstract base class for session storage"""

    @abstractmethod
    async def create(
        self,
        user_id: str,
        username: str,
        roles: list[str],
        metadata: Optional[dict] = None
    ) -> str:
        """Create a new session"""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        pass

    @abstractmethod
    async def update(
        self,
        session_id: str,
        metadata: dict
    ) -> bool:
        """Update session metadata"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete session"""
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session storage for development"""

    def __init__(self, default_ttl_seconds: int = 3600):
        self._sessions: dict[str, SessionData] = {}
        self._default_ttl = default_ttl_seconds

    async def create(self, user_id, username, roles, metadata=None):
        # Implementation
        pass


class RedisSessionStore(SessionStore):
    """Redis-backed session storage for production"""

    def __init__(self, redis_url: str, default_ttl_seconds: int = 3600):
        self._redis = redis.asyncio.from_url(redis_url)
        self._default_ttl = default_ttl_seconds

    async def create(self, user_id, username, roles, metadata=None):
        # Implementation
        pass


# Factory function
def create_session_store(backend: str = "inmemory") -> SessionStore:
    """Factory for session stores"""
    if backend == "inmemory":
        return InMemorySessionStore()
    elif backend == "redis":
        return RedisSessionStore(redis_url=settings.redis_url)
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

**Key Points**:
- Use `ABC` and `@abstractmethod` for interface
- Multiple implementations for different backends
- Factory function to instantiate correct implementation
- InMemory for dev, Redis/PostgreSQL for prod

---

### Pattern 4: Async Context Managers for Resource Management

**Location**: Throughout codebase (Redis, database connections, etc.)

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

**Key Points**:
- Use `@asynccontextmanager` for async resources
- Yield resource in try block
- Cleanup in finally block
- Ensures proper resource cleanup

---

### Pattern 5: Pydantic Models for Data Validation

**Location**: Throughout codebase (auth, api, tools)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class SessionData(BaseModel):
    """Session data model with validation"""

    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., pattern=r"^user:[a-z0-9_-]+$")
    username: str = Field(..., min_length=1, max_length=50)
    roles: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    metadata: dict = Field(default_factory=dict)

    @validator("roles")
    def validate_roles(cls, v):
        """Ensure roles are not empty"""
        if not v:
            raise ValueError("At least one role is required")
        return v

    @validator("expires_at")
    def validate_expiration(cls, v, values):
        """Ensure expiration is in the future"""
        if "created_at" in values and v <= values["created_at"]:
            raise ValueError("Expiration must be after creation")
        return v

    class Config:
        # Allow usage as dataclass
        arbitrary_types_allowed = True
        # JSON serialization
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Key Points**:
- Use `BaseModel` for all data structures
- Use `Field()` for validation and constraints
- Use `@validator` for complex validation
- Configure serialization in `Config`

---

### Pattern 6: Feature Flags for Gradual Rollout

**Location**: `src/mcp_server_langgraph/core/feature_flags.py`

```python
from pydantic import BaseModel, Field

class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout"""

    # Core features
    enable_pydantic_ai_routing: bool = Field(
        default=True,
        description="Enable type-safe routing with Pydantic AI"
    )

    enable_llm_fallback: bool = Field(
        default=True,
        description="Enable automatic LLM fallback on errors"
    )

    enable_openfga: bool = Field(
        default=True,
        description="Enable OpenFGA authorization"
    )

    openfga_strict_mode: bool = Field(
        default=False,
        description="Fail-closed vs fail-open on OpenFGA errors"
    )

    # Experimental features
    enable_experimental_parallel_execution: bool = Field(
        default=False,
        description="Enable parallel tool execution (experimental)"
    )

    # Load from environment
    @classmethod
    def from_env(cls) -> "FeatureFlags":
        import os
        return cls(
            enable_pydantic_ai_routing=os.getenv("FF_ENABLE_PYDANTIC_AI_ROUTING", "true").lower() == "true",
            enable_llm_fallback=os.getenv("FF_ENABLE_LLM_FALLBACK", "true").lower() == "true",
            # ... more flags
        )

# Singleton
feature_flags = FeatureFlags.from_env()


# Usage in code
def route_request(request):
    if feature_flags.enable_pydantic_ai_routing:
        return pydantic_ai_router(request)
    else:
        return legacy_router(request)
```

**Key Points**:
- Centralized feature flag configuration
- Environment variable support (FF_ prefix)
- Default to safe/stable behavior
- Clear descriptions for each flag
- Use throughout codebase for conditional logic

---

### Pattern 7: Observability with OpenTelemetry

**Location**: `src/mcp_server_langgraph/observability/telemetry.py`

```python
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

# Get tracer
tracer = trace.get_tracer(__name__)

# Get meter for metrics
meter = metrics.get_meter(__name__)

# Create metrics
request_counter = meter.create_counter(
    name="http.requests.total",
    description="Total HTTP requests",
    unit="1"
)

request_duration = meter.create_histogram(
    name="http.request.duration",
    description="HTTP request duration",
    unit="ms"
)


# Usage in code
async def handle_request(request):
    # Start span
    with tracer.start_as_current_span("handle_request") as span:
        # Add attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("user.id", request.user_id)

        try:
            # Process request
            result = await process(request)

            # Record success
            span.set_status(Status(StatusCode.OK))
            request_counter.add(1, {"status": "success"})

            return result

        except Exception as e:
            # Record error
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            request_counter.add(1, {"status": "error"})
            raise
```

**Key Points**:
- Get tracer/meter per module (`__name__`)
- Create metrics at module level
- Use `with tracer.start_as_current_span()` for tracing
- Add attributes for context
- Record status and exceptions
- Increment metrics on success/failure

---

### Pattern 8: Error Handling with Graceful Degradation

**Location**: Throughout codebase

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def get_user_with_fallback(user_id: str) -> Optional[User]:
    """
    Get user from primary source with fallback to cache.

    Returns None if all sources fail (graceful degradation).
    """
    try:
        # Try primary source
        user = await primary_user_store.get(user_id)
        if user:
            return user

    except Exception as e:
        logger.warning(f"Primary user store failed: {e}")

    try:
        # Fallback to cache
        user = await cache.get(f"user:{user_id}")
        if user:
            logger.info(f"Served user {user_id} from cache")
            return user

    except Exception as e:
        logger.warning(f"Cache failed: {e}")

    # All sources failed - return None (graceful degradation)
    logger.error(f"All sources failed for user {user_id}")
    return None
```

**Key Points**:
- Try primary source first
- Fallback to secondary/cache
- Log warnings for failures
- Return None for graceful degradation (don't raise)
- Document fallback behavior

---

### Pattern 9: Async Batch Operations

**Location**: `src/mcp_server_langgraph/core/dynamic_context_loader.py`

```python
import asyncio
from typing import List

async def load_batch(
    items: List[str],
    max_concurrent: int = 5
) -> List[Result]:
    """
    Load multiple items concurrently with parallelism limit.

    Args:
        items: List of items to load
        max_concurrent: Maximum concurrent operations

    Returns:
        List of results in same order as items
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def load_one(item: str) -> Result:
        async with semaphore:
            return await fetch(item)

    # Execute all with limited concurrency
    results = await asyncio.gather(
        *[load_one(item) for item in items],
        return_exceptions=True  # Don't fail entire batch on single error
    )

    return results
```

**Key Points**:
- Use `asyncio.Semaphore` for concurrency limit
- Use `asyncio.gather` for parallel execution
- Use `return_exceptions=True` for fault tolerance
- Preserve order of results

---

### Pattern 10: Type-Safe API Responses

**Location**: Throughout API endpoints

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """Type-safe API response wrapper"""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: dict = {}

    @classmethod
    def success_response(cls, data: T, **metadata) -> "APIResponse[T]":
        """Create success response"""
        return cls(
            success=True,
            data=data,
            metadata=metadata
        )

    @classmethod
    def error_response(cls, error: str, **metadata) -> "APIResponse[T]":
        """Create error response"""
        return cls(
            success=False,
            error=error,
            metadata=metadata
        )


# Usage
class UserData(BaseModel):
    user_id: str
    username: str
    roles: List[str]

async def get_user(user_id: str) -> APIResponse[UserData]:
    """Get user with type-safe response"""
    try:
        user = await user_store.get(user_id)
        if user:
            return APIResponse.success_response(
                data=UserData(
                    user_id=user.id,
                    username=user.name,
                    roles=user.roles
                )
            )
        else:
            return APIResponse.error_response(
                error="User not found"
            )
    except Exception as e:
        return APIResponse.error_response(
            error=str(e)
        )
```

**Key Points**:
- Use Generic types for reusable response wrappers
- Separate success/error factory methods
- Type-safe data field
- Consistent response structure

---

## 🎨 Coding Conventions

### Imports
```python
# Standard library
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Third-party
import pytest
from pydantic import BaseModel

# Local
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.auth.session import SessionStore
```

### Naming
- **Classes**: `PascalCase` (`SessionStore`, `UserProvider`)
- **Functions**: `snake_case` (`create_session`, `get_user`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private**: `_leading_underscore` (`_internal_method`)

### Docstrings
```python
async def create_session(
    user_id: str,
    username: str,
    roles: List[str],
    metadata: Optional[Dict] = None
) -> str:
    """
    Create a new session for the user.

    Args:
        user_id: Unique user identifier (format: "user:username")
        username: Username for the session
        roles: List of roles assigned to user
        metadata: Optional session metadata

    Returns:
        Session ID (UUID format)

    Raises:
        ValueError: If max concurrent sessions exceeded
        ConnectionError: If session store unavailable

    Example:
        >>> session_id = await create_session(
        ...     user_id="user:alice",
        ...     username="alice",
        ...     roles=["admin", "user"]
        ... )
    """
```

### Type Hints
```python
# Always use type hints
def process(data: dict) -> Optional[Result]:  # Good
def process(data):  # Bad

# Use typing module for complex types
from typing import Optional, List, Dict, Union

# Use modern syntax when possible (Python 3.10+)
def process(data: dict[str, any]) -> list[str]:  # Python 3.10+
def process(data: Dict[str, Any]) -> List[str]:  # Python 3.9
```

---

## 🔧 Common Utilities

### Logging
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed info for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
logger.critical("Critical error")
```

### Secrets
```python
from mcp_server_langgraph.secrets.manager import get_secret

# Get secret (fallback to env var)
api_key = get_secret("API_KEY")
```

### Feature Flags
```python
from mcp_server_langgraph.core.feature_flags import feature_flags

if feature_flags.enable_new_feature:
    # New code path
    pass
else:
    # Legacy code path
    pass
```

---

## 📚 Related Documents

- **Architecture**: `adr/README.md` (25 ADRs)
- **Configuration**: `src/mcp_server_langgraph/core/config.py`
- **Testing Patterns**: `.claude/context/testing-patterns.md`
- **Development Guide**: `.github/CLAUDE.md`
- **API Reference**: `docs/` (Mintlify)

---

**Auto-Update**: Review and update when new patterns emerge
**Last Review**: 2025-10-20
