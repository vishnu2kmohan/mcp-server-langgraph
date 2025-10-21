# ADR-0029: Custom Exception Hierarchy

**Status**: Accepted
**Date**: 2025-10-20
**Deciders**: Engineering Team
**Related**: [ADR-0017: Error Handling Strategy](0017-error-handling-strategy.md), [ADR-0030: Resilience Patterns](0030-resilience-patterns.md)

## Context

The MCP server currently uses generic Python exceptions (`Exception`, `ValueError`, `RuntimeError`) throughout the codebase. This leads to:

**Current Problems**:
1. **Poor Error Handling**: Cannot distinguish between different error types
2. **Vague Error Messages**: Generic exceptions don't provide context
3. **Difficult Debugging**: Hard to trace error source in logs
4. **Lost Context**: Stack traces don't show business logic errors clearly
5. **Poor Observability**: Cannot filter errors by type in metrics
6. **Inconsistent HTTP Status Codes**: Same exception → different status codes

**Analysis**:
```bash
# Count of custom exceptions: 0
$ grep -r "class.*Exception" src/ | wc -l
0

# Examples of generic exceptions in codebase:
src/auth/middleware.py:    raise Exception("JWT verification failed")
src/llm/factory.py:         raise ValueError(f"Unsupported model: {model}")
src/auth/openfga.py:        raise RuntimeError("OpenFGA check failed")
```

**Impact**:
- Error handling is reactive, not proactive
- Difficult to implement proper retry logic (which errors to retry?)
- Metrics are generic (all errors lumped together)
- User-facing errors lack clarity

## Decision

Implement a **comprehensive custom exception hierarchy** that:
1. Provides clear error semantics
2. Includes rich error context (metadata, trace IDs)
3. Maps to HTTP status codes automatically
4. Enables fine-grained error handling
5. Improves observability and debugging

### Exception Hierarchy

```
BaseException (Python built-in)
└── Exception
    └── MCPServerException (new base)
        ├── ConfigurationError
        │   ├── MissingConfigError
        │   ├── InvalidConfigError
        │   └── SecretNotFoundError
        │
        ├── AuthenticationError
        │   ├── InvalidCredentialsError
        │   ├── TokenExpiredError
        │   ├── TokenInvalidError
        │   └── MFARequiredError
        │
        ├── AuthorizationError
        │   ├── PermissionDeniedError
        │   ├── ResourceNotFoundError
        │   └── InsufficientPermissionsError
        │
        ├── RateLimitError
        │   ├── RateLimitExceededError
        │   └── QuotaExceededError
        │
        ├── ValidationError
        │   ├── InputValidationError
        │   ├── SchemaValidationError
        │   └── ConstraintViolationError
        │
        ├── ExternalServiceError
        │   ├── LLMProviderError
        │   │   ├── LLMRateLimitError
        │   │   ├── LLMTimeoutError
        │   │   └── LLMModelNotFoundError
        │   ├── OpenFGAError
        │   │   ├── OpenFGATimeoutError
        │   │   └── OpenFGAUnavailableError
        │   ├── RedisError
        │   │   ├── RedisConnectionError
        │   │   └── RedisTimeoutError
        │   └── KeycloakError
        │       ├── KeycloakAuthError
        │       └── KeycloakUnavailableError
        │
        ├── ResilienceError
        │   ├── CircuitBreakerOpenError
        │   ├── RetryExhaustedError
        │   ├── TimeoutError
        │   └── BulkheadRejectedError
        │
        ├── StorageError
        │   ├── StorageBackendError
        │   ├── DataNotFoundError
        │   └── DataIntegrityError
        │
        ├── ComplianceError
        │   ├── GDPRViolationError
        │   ├── HIPAAViolationError
        │   └── SOC2ViolationError
        │
        └── InternalServerError
            ├── UnexpectedError
            └── NotImplementedError
```

## Architecture

### New Module: `src/mcp_server_langgraph/core/exceptions.py`

```python
"""
Custom exception hierarchy for MCP server.

Features:
- Rich error context (metadata, trace IDs, user messages)
- Automatic HTTP status code mapping
- Structured error responses
- Observability integration (metrics, logging)
- Retry-ability classification
"""

from typing import Any, Dict, Optional
from enum import Enum


class ErrorCategory(str, Enum):
    """High-level error categories for metrics"""
    CLIENT_ERROR = "client_error"      # 4xx errors (user's fault)
    SERVER_ERROR = "server_error"      # 5xx errors (our fault)
    EXTERNAL_ERROR = "external_error"  # 5xx errors (external service's fault)
    RATE_LIMIT = "rate_limit"          # 429 errors
    AUTH_ERROR = "auth_error"          # 401/403 errors


class RetryPolicy(str, Enum):
    """Whether exception is retry-able"""
    NEVER = "never"          # Never retry (client errors, permanent failures)
    ALWAYS = "always"        # Always retry (transient failures)
    CONDITIONAL = "conditional"  # Retry with conditions (idempotent operations only)


class MCPServerException(Exception):
    """
    Base exception for all MCP server errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "auth.token_expired")
        status_code: HTTP status code (e.g., 401, 500)
        category: Error category for metrics
        retry_policy: Whether this error is retry-able
        metadata: Additional context (user_id, resource_id, etc.)
        trace_id: OpenTelemetry trace ID for correlation
        user_message: User-friendly message (safe to display)
    """

    # Default values (overridden by subclasses)
    default_message = "An error occurred"
    default_error_code = "server.error"
    default_status_code = 500
    default_category = ErrorCategory.SERVER_ERROR
    default_retry_policy = RetryPolicy.NEVER

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        category: Optional[ErrorCategory] = None,
        retry_policy: Optional[RetryPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        user_message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message or self.default_message
        self.error_code = error_code or self.default_error_code
        self.status_code = status_code or self.default_status_code
        self.category = category or self.default_category
        self.retry_policy = retry_policy or self.default_retry_policy
        self.metadata = metadata or {}
        self.trace_id = trace_id or self._get_current_trace_id()
        self.user_message = user_message or self._generate_user_message()
        self.cause = cause

        # Call parent constructor
        super().__init__(self.message)

    def _get_current_trace_id(self) -> Optional[str]:
        """Get current OpenTelemetry trace ID"""
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return None

    def _generate_user_message(self) -> str:
        """Generate safe user-facing message"""
        # Override in subclasses for user-friendly messages
        if self.category == ErrorCategory.CLIENT_ERROR:
            return "There was a problem with your request. Please check and try again."
        elif self.category == ErrorCategory.AUTH_ERROR:
            return "Authentication failed. Please sign in and try again."
        elif self.category == ErrorCategory.RATE_LIMIT:
            return "You've made too many requests. Please wait and try again."
        else:
            return "An unexpected error occurred. Please try again later."

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.user_message,
                "details": self.message,
                "trace_id": self.trace_id,
                "metadata": self.metadata,
            }
        }

    def __str__(self) -> str:
        """String representation with full context"""
        parts = [f"{self.error_code}: {self.message}"]
        if self.metadata:
            parts.append(f"metadata={self.metadata}")
        if self.trace_id:
            parts.append(f"trace_id={self.trace_id}")
        return " | ".join(parts)


# ============================================================================
# Configuration Errors (4xx - Client Error)
# ============================================================================

class ConfigurationError(MCPServerException):
    """Base class for configuration errors"""
    default_message = "Configuration error"
    default_error_code = "config.error"
    default_status_code = 500
    default_category = ErrorCategory.SERVER_ERROR


class MissingConfigError(ConfigurationError):
    """Required configuration is missing"""
    default_message = "Required configuration is missing"
    default_error_code = "config.missing"


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid"""
    default_message = "Configuration value is invalid"
    default_error_code = "config.invalid"


class SecretNotFoundError(ConfigurationError):
    """Secret not found in secrets manager"""
    default_message = "Secret not found"
    default_error_code = "config.secret_not_found"


# ============================================================================
# Authentication Errors (401 - Unauthorized)
# ============================================================================

class AuthenticationError(MCPServerException):
    """Base class for authentication errors"""
    default_message = "Authentication failed"
    default_error_code = "auth.failed"
    default_status_code = 401
    default_category = ErrorCategory.AUTH_ERROR
    default_retry_policy = RetryPolicy.NEVER


class InvalidCredentialsError(AuthenticationError):
    """Username or password is incorrect"""
    default_message = "Invalid credentials"
    default_error_code = "auth.invalid_credentials"

    def _generate_user_message(self) -> str:
        return "Invalid username or password. Please try again."


class TokenExpiredError(AuthenticationError):
    """JWT token has expired"""
    default_message = "Token has expired"
    default_error_code = "auth.token_expired"
    default_retry_policy = RetryPolicy.CONDITIONAL  # Retry with refresh token

    def _generate_user_message(self) -> str:
        return "Your session has expired. Please sign in again."


class TokenInvalidError(AuthenticationError):
    """JWT token is invalid"""
    default_message = "Token is invalid"
    default_error_code = "auth.token_invalid"

    def _generate_user_message(self) -> str:
        return "Authentication failed. Please sign in again."


class MFARequiredError(AuthenticationError):
    """Multi-factor authentication is required"""
    default_message = "MFA required"
    default_error_code = "auth.mfa_required"
    default_status_code = 403

    def _generate_user_message(self) -> str:
        return "Multi-factor authentication is required. Please complete MFA."


# ============================================================================
# Authorization Errors (403 - Forbidden)
# ============================================================================

class AuthorizationError(MCPServerException):
    """Base class for authorization errors"""
    default_message = "Authorization failed"
    default_error_code = "authz.failed"
    default_status_code = 403
    default_category = ErrorCategory.AUTH_ERROR
    default_retry_policy = RetryPolicy.NEVER


class PermissionDeniedError(AuthorizationError):
    """User does not have required permission"""
    default_message = "Permission denied"
    default_error_code = "authz.permission_denied"

    def _generate_user_message(self) -> str:
        return "You don't have permission to perform this action."


class ResourceNotFoundError(AuthorizationError):
    """Resource not found (or user doesn't have access)"""
    default_message = "Resource not found"
    default_error_code = "authz.resource_not_found"
    default_status_code = 404

    def _generate_user_message(self) -> str:
        return "The requested resource was not found."


class InsufficientPermissionsError(AuthorizationError):
    """User's tier/plan doesn't allow this action"""
    default_message = "Insufficient permissions"
    default_error_code = "authz.insufficient_permissions"

    def _generate_user_message(self) -> str:
        return "Your current plan doesn't include this feature. Please upgrade."


# ============================================================================
# Rate Limiting Errors (429 - Too Many Requests)
# ============================================================================

class RateLimitError(MCPServerException):
    """Base class for rate limiting errors"""
    default_message = "Rate limit exceeded"
    default_error_code = "rate_limit.exceeded"
    default_status_code = 429
    default_category = ErrorCategory.RATE_LIMIT
    default_retry_policy = RetryPolicy.CONDITIONAL

    def _generate_user_message(self) -> str:
        retry_after = self.metadata.get("retry_after", 60)
        return f"Rate limit exceeded. Please wait {retry_after} seconds and try again."


class RateLimitExceededError(RateLimitError):
    """Request rate limit exceeded"""
    pass


class QuotaExceededError(RateLimitError):
    """Usage quota exceeded"""
    default_error_code = "quota.exceeded"

    def _generate_user_message(self) -> str:
        return "You've exceeded your usage quota. Please upgrade your plan."


# ============================================================================
# Validation Errors (400 - Bad Request)
# ============================================================================

class ValidationError(MCPServerException):
    """Base class for validation errors"""
    default_message = "Validation failed"
    default_error_code = "validation.failed"
    default_status_code = 400
    default_category = ErrorCategory.CLIENT_ERROR
    default_retry_policy = RetryPolicy.NEVER


class InputValidationError(ValidationError):
    """User input failed validation"""
    default_error_code = "validation.input"

    def _generate_user_message(self) -> str:
        field = self.metadata.get("field", "input")
        return f"Invalid {field}. Please check and try again."


class SchemaValidationError(ValidationError):
    """Data doesn't match expected schema"""
    default_error_code = "validation.schema"


class ConstraintViolationError(ValidationError):
    """Business rule constraint violated"""
    default_error_code = "validation.constraint"


# ============================================================================
# External Service Errors (502/503/504)
# ============================================================================

class ExternalServiceError(MCPServerException):
    """Base class for external service errors"""
    default_message = "External service error"
    default_error_code = "external.error"
    default_status_code = 503
    default_category = ErrorCategory.EXTERNAL_ERROR
    default_retry_policy = RetryPolicy.ALWAYS


class LLMProviderError(ExternalServiceError):
    """LLM API error"""
    default_error_code = "external.llm.error"


class LLMRateLimitError(LLMProviderError):
    """LLM provider rate limit exceeded"""
    default_error_code = "external.llm.rate_limit"
    default_status_code = 429


class LLMTimeoutError(LLMProviderError):
    """LLM request timed out"""
    default_error_code = "external.llm.timeout"
    default_status_code = 504


class LLMModelNotFoundError(LLMProviderError):
    """LLM model not found"""
    default_error_code = "external.llm.model_not_found"
    default_status_code = 400
    default_retry_policy = RetryPolicy.NEVER


class OpenFGAError(ExternalServiceError):
    """OpenFGA service error"""
    default_error_code = "external.openfga.error"


class RedisError(ExternalServiceError):
    """Redis service error"""
    default_error_code = "external.redis.error"


class KeycloakError(ExternalServiceError):
    """Keycloak service error"""
    default_error_code = "external.keycloak.error"


# ============================================================================
# Resilience Errors (Circuit Breaker, Retry, Timeout)
# ============================================================================

class ResilienceError(MCPServerException):
    """Base class for resilience pattern errors"""
    default_message = "Resilience error"
    default_error_code = "resilience.error"
    default_status_code = 503
    default_category = ErrorCategory.SERVER_ERROR
    default_retry_policy = RetryPolicy.CONDITIONAL


class CircuitBreakerOpenError(ResilienceError):
    """Circuit breaker is open, failing fast"""
    default_error_code = "resilience.circuit_breaker_open"

    def _generate_user_message(self) -> str:
        service = self.metadata.get("service", "the service")
        return f"{service} is temporarily unavailable. Please try again later."


class RetryExhaustedError(ResilienceError):
    """Retry attempts exhausted"""
    default_error_code = "resilience.retry_exhausted"


class TimeoutError(ResilienceError):
    """Operation timed out"""
    default_error_code = "resilience.timeout"
    default_status_code = 504


class BulkheadRejectedError(ResilienceError):
    """Bulkhead rejected request (concurrency limit)"""
    default_error_code = "resilience.bulkhead_rejected"
    default_status_code = 503

    def _generate_user_message(self) -> str:
        return "Service is under heavy load. Please try again in a moment."


# ============================================================================
# Storage Errors
# ============================================================================

class StorageError(MCPServerException):
    """Base class for storage errors"""
    default_message = "Storage error"
    default_error_code = "storage.error"
    default_status_code = 500
    default_category = ErrorCategory.SERVER_ERROR


class DataNotFoundError(StorageError):
    """Data not found in storage"""
    default_error_code = "storage.not_found"
    default_status_code = 404


class DataIntegrityError(StorageError):
    """Data integrity check failed"""
    default_error_code = "storage.integrity"


# ============================================================================
# Compliance Errors
# ============================================================================

class ComplianceError(MCPServerException):
    """Base class for compliance errors"""
    default_message = "Compliance violation"
    default_error_code = "compliance.violation"
    default_status_code = 403
    default_category = ErrorCategory.SERVER_ERROR


class GDPRViolationError(ComplianceError):
    """GDPR compliance violation"""
    default_error_code = "compliance.gdpr"


class HIPAAViolationError(ComplianceError):
    """HIPAA compliance violation"""
    default_error_code = "compliance.hipaa"


class SOC2ViolationError(ComplianceError):
    """SOC 2 compliance violation"""
    default_error_code = "compliance.soc2"
```

## FastAPI Integration

### Exception Handler

```python
# src/mcp_server_langgraph/api/error_handlers.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp_server_langgraph.core.exceptions import MCPServerException
from mcp_server_langgraph.observability.telemetry import logger

def register_exception_handlers(app: FastAPI):
    """Register custom exception handlers"""

    @app.exception_handler(MCPServerException)
    async def mcp_exception_handler(request: Request, exc: MCPServerException):
        """Handle MCP server exceptions"""
        # Log with full context
        logger.error(
            f"Exception: {exc.error_code}",
            exc_info=True,
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "category": exc.category.value,
                "retry_policy": exc.retry_policy.value,
                "trace_id": exc.trace_id,
                "metadata": exc.metadata,
                "user_message": exc.user_message,
            }
        )

        # Record metric
        from mcp_server_langgraph.observability.telemetry import error_counter
        error_counter.add(
            1,
            attributes={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "category": exc.category.value,
            }
        )

        # Return JSON response
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers={"X-Trace-ID": exc.trace_id} if exc.trace_id else {},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        # Wrap in InternalServerError
        from mcp_server_langgraph.core.exceptions import InternalServerError

        wrapped_exc = InternalServerError(
            message=str(exc),
            cause=exc,
        )

        return await mcp_exception_handler(request, wrapped_exc)
```

## Migration Guide

### Before (Generic Exceptions)

```python
# OLD CODE
def check_permission(user_id: str, resource: str) -> bool:
    if not user_id:
        raise ValueError("User ID is required")  # ❌ Generic

    result = openfga_client.check(user_id, resource)
    if not result:
        raise Exception("Permission denied")  # ❌ Generic

    return True
```

### After (Custom Exceptions)

```python
# NEW CODE
from mcp_server_langgraph.core.exceptions import (
    InputValidationError,
    PermissionDeniedError,
)

def check_permission(user_id: str, resource: str) -> bool:
    if not user_id:
        raise InputValidationError(  # ✅ Specific
            message="User ID is required",
            metadata={"field": "user_id"},
        )

    result = openfga_client.check(user_id, resource)
    if not result:
        raise PermissionDeniedError(  # ✅ Specific
            message=f"User {user_id} denied access to {resource}",
            metadata={"user_id": user_id, "resource": resource},
        )

    return True
```

## Consequences

### Positive

1. **Better Error Handling**
   - Can catch specific exceptions: `except TokenExpiredError:`
   - Implement custom retry logic per exception type
   - Different handling for client vs server errors

2. **Improved Observability**
   - Error metrics by category/code
   - Trace IDs for debugging
   - Rich metadata in logs

3. **Better User Experience**
   - Clear, actionable error messages
   - Appropriate HTTP status codes
   - Retry hints (Retry-After header)

4. **Easier Debugging**
   - Stack traces show business logic errors
   - Metadata provides context
   - Trace IDs link to distributed traces

5. **Compliance**
   - Specific exceptions for GDPR/HIPAA/SOC2 violations
   - Audit trail of compliance errors

### Negative

1. **More Code**
   - 300+ lines for exception hierarchy
   - Need to update all exception raises

2. **Learning Curve**
   - Developers need to learn exception hierarchy
   - Need to choose correct exception type

3. **Migration Effort**
   - Update ~100+ exception raises across codebase
   - Test all error paths

## Implementation Plan

### Week 1: Foundation
- [x] Create ADR-0029 (this document)
- [ ] Create `core/exceptions.py` with hierarchy
- [ ] Add FastAPI exception handlers
- [ ] Write 50+ unit tests for exceptions
- [ ] Update developer documentation

### Week 2: Migration - Auth & Core
- [ ] Migrate `auth/` module to custom exceptions
- [ ] Migrate `core/` module to custom exceptions
- [ ] Update error handling tests
- [ ] Verify metrics are collected correctly

### Week 3: Migration - LLM & External Services
- [ ] Migrate `llm/` module to custom exceptions
- [ ] Add retry logic based on `retry_policy`
- [ ] Wrap external service errors properly
- [ ] Test circuit breaker integration

### Week 4: Migration - Remaining Modules
- [ ] Migrate `api/`, `mcp/`, `compliance/` modules
- [ ] Update all integration tests
- [ ] Verify HTTP status codes are correct
- [ ] Performance test (exception overhead)

### Week 5: Documentation & Rollout
- [ ] Update API documentation with error codes
- [ ] Create error code reference guide
- [ ] Deploy to staging, test error flows
- [ ] Deploy to production

## References

- **ADR-0017: Error Handling Strategy**: ./0017-error-handling-strategy.md
- **ADR-0030: Resilience Patterns**: ./0026-resilience-patterns.md
- **Python Exception Best Practices**: https://docs.python.org/3/tutorial/errors.html
- **HTTP Status Codes**: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
- **REST API Error Handling**: https://www.baeldung.com/rest-api-error-handling-best-practices

---

**Last Updated**: 2025-10-20
**Next Review**: 2025-11-20
