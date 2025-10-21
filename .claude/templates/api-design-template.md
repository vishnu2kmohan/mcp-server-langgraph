# API Design: [Feature Name]

**Date**: YYYY-MM-DD
**Status**: [Draft | Under Review | Approved | Implemented]
**Author**: [Name]
**Related ADR**: [ADR-XXXX if applicable]

---

## Overview

**Purpose**: [Brief 1-2 sentence description of what this API does]

**Use Cases**:
1. [Primary use case]
2. [Secondary use case]
3. [Edge case or special scenario]

**Target Users**:
- [Who will use this API? Internal services? External clients? Both?]

---

## API Specification

### Endpoint

```
[METHOD] /api/v1/[resource]/[action]
```

**Method**: `GET | POST | PUT | PATCH | DELETE`
**Path**: `/api/v1/resource/{id}/action`
**Authentication**: Required | Optional | Not Required
**Authorization**: [Required permissions or roles]

---

### Request

#### Path Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `id` | string | Yes | Resource identifier | `"user-123"` |
| `action` | string | No | Optional action | `"activate"` |

#### Query Parameters

| Parameter | Type | Required | Default | Description | Example |
|-----------|------|----------|---------|-------------|---------|
| `page` | integer | No | `1` | Page number for pagination | `2` |
| `limit` | integer | No | `20` | Items per page | `50` |
| `filter` | string | No | - | Filter criteria | `"status:active"` |
| `sort` | string | No | `"created_at"` | Sort field | `"name"` |
| `order` | string | No | `"asc"` | Sort order | `"desc"` |

#### Headers

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `Authorization` | Yes | Bearer token | `"Bearer eyJ..."` |
| `Content-Type` | Yes (POST/PUT) | Request content type | `"application/json"` |
| `X-Request-ID` | No | Request tracking ID | `"req-abc-123"` |

#### Request Body

**Content-Type**: `application/json`

**Schema**:
```typescript
interface RequestBody {
  // Required fields
  name: string;                    // Resource name (max 100 chars)
  email: string;                   // Valid email format

  // Optional fields
  description?: string;            // Optional description
  metadata?: Record<string, any>; // Arbitrary metadata

  // Nested objects
  settings: {
    enabled: boolean;              // Enable/disable flag
    priority: "low" | "medium" | "high";
  };

  // Arrays
  tags: string[];                  // List of tags (max 10)
}
```

**Example**:
```json
{
  "name": "User Session",
  "email": "user@example.com",
  "description": "Primary user session",
  "metadata": {
    "source": "web",
    "version": "2.0"
  },
  "settings": {
    "enabled": true,
    "priority": "high"
  },
  "tags": ["production", "monitored"]
}
```

**Validation Rules**:
- `name`: Required, 1-100 characters, alphanumeric and spaces only
- `email`: Required, valid email format, max 255 characters
- `description`: Optional, max 500 characters
- `tags`: Max 10 items, each 1-50 characters
- `settings.priority`: Must be one of: "low", "medium", "high"

---

### Response

#### Success Response (200 OK)

**Content-Type**: `application/json`

**Schema**:
```typescript
interface SuccessResponse {
  success: true;
  data: {
    id: string;                    // Resource ID
    name: string;                  // Resource name
    email: string;                 // User email
    status: "active" | "inactive"; // Current status
    created_at: string;            // ISO 8601 timestamp
    updated_at: string;            // ISO 8601 timestamp
  };
  meta: {
    request_id: string;            // Request tracking ID
    timestamp: string;             // Response timestamp
  };
}
```

**Example**:
```json
{
  "success": true,
  "data": {
    "id": "res-abc-123",
    "name": "User Session",
    "email": "user@example.com",
    "status": "active",
    "created_at": "2025-10-20T14:30:00Z",
    "updated_at": "2025-10-20T14:30:00Z"
  },
  "meta": {
    "request_id": "req-xyz-789",
    "timestamp": "2025-10-20T14:30:01Z"
  }
}
```

#### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format",
        "value": "not-an-email"
      }
    ]
  },
  "meta": {
    "request_id": "req-xyz-789",
    "timestamp": "2025-10-20T14:30:01Z"
  }
}
```

**401 Unauthorized** - Missing or invalid authentication
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

**403 Forbidden** - Insufficient permissions
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions to perform this action",
    "required_permission": "resource:write"
  }
}
```

**404 Not Found** - Resource doesn't exist
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "resource_type": "user",
    "resource_id": "user-123"
  }
}
```

**409 Conflict** - Resource already exists or state conflict
```json
{
  "success": false,
  "error": {
    "code": "CONFLICT",
    "message": "Resource already exists",
    "existing_id": "res-existing-456"
  }
}
```

**422 Unprocessable Entity** - Semantic errors
```json
{
  "success": false,
  "error": {
    "code": "UNPROCESSABLE",
    "message": "Cannot process request",
    "reason": "Account is locked"
  }
}
```

**429 Too Many Requests** - Rate limit exceeded
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

**500 Internal Server Error** - Server error
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "incident_id": "inc-abc-123"
  }
}
```

---

## Behavior Specification

### Happy Path

1. Client sends valid request with authentication
2. Server validates input schema
3. Server checks authorization (user has required permissions)
4. Server processes request (creates/updates/retrieves resource)
5. Server returns success response (200/201)

### Error Handling

**Validation Errors** (400):
- Invalid email format
- Missing required fields
- Field value out of range
- Invalid enum value

**Business Logic Errors** (422):
- Resource in invalid state for operation
- Dependency conflict
- Business rule violation

**Infrastructure Errors** (500):
- Database connection failure
- External service timeout
- Unexpected exception

### Idempotency

**Idempotent**: `GET, PUT, DELETE` (safe to retry)
**Non-Idempotent**: `POST, PATCH` (may have side effects on retry)

**Idempotency Key** (for POST requests):
```http
POST /api/v1/resource
Idempotency-Key: key-unique-123

{...}
```

If same key is used within 24 hours, returns cached response.

### Rate Limiting

**Limits**:
- Anonymous: 60 requests/minute
- Authenticated: 1000 requests/minute
- Premium: 5000 requests/minute

**Headers**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1634567890
```

### Pagination

**Request**:
```
GET /api/v1/resources?page=2&limit=50
```

**Response**:
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 50,
    "total_items": 250,
    "total_pages": 5,
    "has_next": true,
    "has_prev": true,
    "next_page": "/api/v1/resources?page=3&limit=50",
    "prev_page": "/api/v1/resources?page=1&limit=50"
  }
}
```

---

## Implementation Details

### File Structure

```
src/mcp_server_langgraph/
├── api/
│   ├── routes/
│   │   └── resource.py          # Route handlers
│   ├── schemas/
│   │   └── resource.py          # Pydantic models
│   ├── services/
│   │   └── resource_service.py  # Business logic
│   └── middleware/
│       └── auth.py               # Authentication/authorization
```

### Route Handler (FastAPI)

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])

class ResourceCreate(BaseModel):
    name: str
    email: str
    # ... other fields

@router.post("", status_code=201)
async def create_resource(
    resource: ResourceCreate,
    current_user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    """Create a new resource."""
    # Authorization check
    if not current_user.has_permission("resource:create"):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Business logic
    try:
        result = await service.create(resource, user_id=current_user.id)
        return {"success": True, "data": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

### Service Layer

```python
class ResourceService:
    """Business logic for resources."""

    async def create(self, data: ResourceCreate, user_id: str) -> Resource:
        """Create a new resource."""
        # Validate business rules
        if await self.exists(data.email):
            raise ConflictError("Resource with this email already exists")

        # Create resource
        resource = Resource(
            id=generate_id(),
            name=data.name,
            email=data.email,
            owner_id=user_id,
            created_at=utcnow(),
        )

        # Save to database
        await self.repository.save(resource)

        # Emit event
        await self.events.publish("resource.created", resource)

        return resource
```

---

## Security Considerations

**Authentication**:
- JWT bearer tokens required
- Tokens expire after 1 hour
- Refresh tokens valid for 7 days

**Authorization**:
- OpenFGA-based permissions
- Required permission: `resource:create`
- Owner can perform all operations
- Admin can override

**Input Validation**:
- All inputs sanitized
- SQL injection prevention (using ORM)
- XSS prevention (API only, no HTML)
- Size limits enforced (max 10 MB request body)

**Rate Limiting**:
- Per-user rate limits
- Global rate limits
- DDoS protection

**Audit Logging**:
- All mutations logged
- Includes: user, timestamp, action, resource
- Retained for 90 days

---

## Performance Requirements

**Latency**:
- P50: < 50ms
- P95: < 200ms
- P99: < 500ms

**Throughput**:
- 1000 requests/second sustained
- 5000 requests/second peak

**Database**:
- Connection pooling (min 5, max 20)
- Query timeout: 5 seconds
- Index on frequently queried fields

**Caching**:
- Redis cache for read-heavy operations
- TTL: 5 minutes
- Cache invalidation on updates

---

## Testing Strategy

### Unit Tests

```python
async def test_create_resource_success():
    """Test successful resource creation."""
    service = ResourceService(repo=mock_repo, events=mock_events)

    data = ResourceCreate(name="Test", email="test@example.com")
    result = await service.create(data, user_id="user-123")

    assert result.id is not None
    assert result.name == "Test"
    mock_repo.save.assert_called_once()
```

### Integration Tests

```python
async def test_api_create_resource():
    """Test resource creation endpoint."""
    async with AsyncClient(app=app) as client:
        response = await client.post(
            "/api/v1/resources",
            json={"name": "Test", "email": "test@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["success"] is True
```

### Contract Tests

```python
def test_response_schema():
    """Test response matches JSON schema."""
    response = {...}  # Sample response
    validate(response, schema=response_schema)
```

---

## Migration Plan

**Phase 1: Implementation**
- Week 1: Implement route handler and service layer
- Week 2: Add tests (unit + integration)
- Week 3: Documentation and review

**Phase 2: Deployment**
- Deploy to staging
- Run integration tests
- Performance testing
- Security audit

**Phase 3: Rollout**
- Deploy to production (canary: 5%)
- Monitor metrics
- Gradual rollout (25% → 50% → 100%)

**Rollback Plan**:
- Feature flag to disable new endpoint
- Database migrations are reversible
- Fallback to old implementation if needed

---

## Documentation

**OpenAPI Spec**: Auto-generated from FastAPI
**Postman Collection**: Available at `docs/api/postman/`
**Examples**: Available at `docs/api/examples/`
**Changelog**: Document in `CHANGELOG.md`

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [REST API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://httpstatuses.com/)
- [Related ADR-XXXX](adr/XXXX-title.md)

---

**Template Version**: 1.0
**Last Updated**: 2025-10-20
**Status**: Ready for Use
