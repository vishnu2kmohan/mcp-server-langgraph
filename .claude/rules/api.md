---
description: API development rules for FastAPI endpoints and Pydantic models
paths:
  - "src/mcp_server_langgraph/api/**"
globs:
  - "**/api/**/*.py"
---

# API Development Rules

## Pydantic Models

```python
from pydantic import BaseModel, Field

class SessionData(BaseModel):
    """Use Field() for validation constraints"""
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., pattern=r"^user:[a-z0-9_-]+$")
    roles: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

## Response Pattern

```python
class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def success_response(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def error_response(cls, error: str) -> "APIResponse[T]":
        return cls(success=False, error=error)
```

## Field Naming Conventions

| Layer | Convention | Example |
|-------|------------|---------|
| OTEL attributes | snake_case | `thinking_content` |
| API response | snake_case | `model_name` |
| Frontend client | camelCase | `modelName` |

## Error Handling

```python
async def get_resource(resource_id: str) -> APIResponse[Resource]:
    try:
        resource = await store.get(resource_id)
        if resource:
            return APIResponse.success_response(data=resource)
        return APIResponse.error_response(error="Not found")
    except Exception as e:
        logger.error(f"Failed to get resource: {e}")
        return APIResponse.error_response(error=str(e))
```

## Observability

```python
with tracer.start_as_current_span("api_operation") as span:
    span.set_attribute("resource.id", resource_id)
    span.set_attribute("user.id", user_id)
    # ... operation
    span.set_status(Status(StatusCode.OK))
```

## Validation

- Use Pydantic validators for complex rules
- Return 400 for validation errors
- Return 404 for not found
- Return 500 for unexpected errors

---

## OTEL Attribute Naming (Shift-Left from check-otel-attribute-naming)

Use **dot notation** per OpenTelemetry semantic conventions:

| Correct | Wrong |
|---------|-------|
| `session.id` | `session_id` |
| `user.id` | `user_id` |
| `workflow.run_id` | `workflow_run_id` |

```python
# CORRECT - Dot notation (matches Tempo/Loki queries)
span.set_attribute("session.id", session_id)
span.set_attribute("user.id", user_id)

# WRONG - Underscore notation (won't match queries)
span.set_attribute("session_id", session_id)  # Bug: da0d442c
```

Underscore notation won't match Tempo/Loki queries.
