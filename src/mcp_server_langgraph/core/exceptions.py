"""
Custom exception hierarchy for MCP server.

Provides rich error context, automatic HTTP status code mapping,
and integration with observability stack.

See ADR-0029 for design rationale.
"""

from enum import Enum
from typing import Any

from opentelemetry import trace


class ErrorCategory(str, Enum):
    """High-level error categories for metrics"""

    CLIENT_ERROR = "client_error"  # 4xx errors (user's fault)
    SERVER_ERROR = "server_error"  # 5xx errors (our fault)
    EXTERNAL_ERROR = "external_error"  # 5xx errors (external service's fault)
    RATE_LIMIT = "rate_limit"  # 429 errors
    AUTH_ERROR = "auth_error"  # 401/403 errors


class RetryPolicy(str, Enum):
    """Whether exception is retry-able"""

    NEVER = "never"  # Never retry (client errors, permanent failures)
    ALWAYS = "always"  # Always retry (transient failures)
    CONDITIONAL = "conditional"  # Retry with conditions (idempotent operations only)


class MCPServerError(Exception):
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
        cause: Original exception that caused this error
    """

    # Default values (overridden by subclasses)
    default_message = "An error occurred"
    default_error_code = "server.error"
    default_status_code = 500
    default_category = ErrorCategory.SERVER_ERROR
    default_retry_policy = RetryPolicy.NEVER

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
        category: ErrorCategory | None = None,
        retry_policy: RetryPolicy | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        user_message: str | None = None,
        cause: Exception | None = None,
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

    def _get_current_trace_id(self) -> str | None:
        """Get current OpenTelemetry trace ID"""
        try:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return format(span.get_span_context().trace_id, "032x")
        except Exception:
            pass
        return None

    def _generate_user_message(self) -> str:
        """Generate safe user-facing message"""
        if self.category == ErrorCategory.CLIENT_ERROR:
            return "There was a problem with your request. Please check and try again."
        if self.category == ErrorCategory.AUTH_ERROR:
            return "Authentication failed. Please sign in and try again."
        if self.category == ErrorCategory.RATE_LIMIT:
            return "You've made too many requests. Please wait and try again."
        return "An unexpected error occurred. Please try again later."

    def to_dict(self) -> dict[str, Any]:
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


# ==============================================================================
# Configuration Errors (500 - Server Error)
# ==============================================================================


class ConfigurationError(MCPServerError):
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


# ==============================================================================
# Authentication Errors (401 - Unauthorized)
# ==============================================================================


class AuthenticationError(MCPServerError):
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


# ==============================================================================
# Authorization Errors (403 - Forbidden)
# ==============================================================================


class AuthorizationError(MCPServerError):
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


# ==============================================================================
# Rate Limiting Errors (429 - Too Many Requests)
# ==============================================================================


class RateLimitError(MCPServerError):
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


class QuotaExceededError(RateLimitError):
    """Usage quota exceeded"""

    default_error_code = "quota.exceeded"

    def _generate_user_message(self) -> str:
        return "You've exceeded your usage quota. Please upgrade your plan."


# ==============================================================================
# Validation Errors (400 - Bad Request)
# ==============================================================================


class ValidationError(MCPServerError):
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


# ==============================================================================
# External Service Errors (502/503/504)
# ==============================================================================


class ExternalServiceError(MCPServerError):
    """Base class for external service errors"""

    default_message = "External service error"
    default_error_code = "external.error"
    default_status_code = 503
    default_category = ErrorCategory.EXTERNAL_ERROR
    default_retry_policy = RetryPolicy.ALWAYS


class LLMProviderError(ExternalServiceError):
    """LLM API error"""

    default_message = "LLM provider error"
    default_error_code = "external.llm.error"


class LLMRateLimitError(LLMProviderError):
    """LLM provider rate limit exceeded"""

    default_message = "LLM provider rate limit exceeded"
    default_error_code = "external.llm.rate_limit"
    default_status_code = 429


class LLMTimeoutError(LLMProviderError):
    """LLM request timed out"""

    default_message = "LLM request timed out"
    default_error_code = "external.llm.timeout"
    default_status_code = 504


class LLMModelNotFoundError(LLMProviderError):
    """LLM model not found"""

    default_message = "LLM model not found"
    default_error_code = "external.llm.model_not_found"
    default_status_code = 400
    default_retry_policy = RetryPolicy.NEVER


class OpenFGAError(ExternalServiceError):
    """OpenFGA service error"""

    default_message = "OpenFGA service error"
    default_error_code = "external.openfga.error"


class OpenFGATimeoutError(OpenFGAError):
    """OpenFGA request timed out"""

    default_message = "OpenFGA request timed out"
    default_error_code = "external.openfga.timeout"
    default_status_code = 504


class OpenFGAUnavailableError(OpenFGAError):
    """OpenFGA service unavailable"""

    default_message = "OpenFGA service unavailable"
    default_error_code = "external.openfga.unavailable"


class RedisError(ExternalServiceError):
    """Redis service error"""

    default_message = "Redis service error"
    default_error_code = "external.redis.error"


class RedisConnectionError(RedisError):
    """Redis connection error"""

    default_message = "Redis connection error"
    default_error_code = "external.redis.connection"


class RedisTimeoutError(RedisError):
    """Redis request timed out"""

    default_message = "Redis request timed out"
    default_error_code = "external.redis.timeout"
    default_status_code = 504


class KeycloakError(ExternalServiceError):
    """Keycloak service error"""

    default_message = "Keycloak service error"
    default_error_code = "external.keycloak.error"


class KeycloakAuthError(KeycloakError):
    """Keycloak authentication error"""

    default_message = "Keycloak authentication error"
    default_error_code = "external.keycloak.auth"
    default_status_code = 401


class KeycloakUnavailableError(KeycloakError):
    """Keycloak service unavailable"""

    default_message = "Keycloak service unavailable"
    default_error_code = "external.keycloak.unavailable"


# ==============================================================================
# Resilience Errors (503/504 - Service Unavailable/Timeout)
# ==============================================================================


class ResilienceError(MCPServerError):
    """Base class for resilience pattern errors"""

    default_message = "Resilience error"
    default_error_code = "resilience.error"
    default_status_code = 503
    default_category = ErrorCategory.SERVER_ERROR
    default_retry_policy = RetryPolicy.CONDITIONAL


class CircuitBreakerOpenError(ResilienceError):
    """Circuit breaker is open, failing fast"""

    default_message = "Circuit breaker is open"
    default_error_code = "resilience.circuit_breaker_open"

    def _generate_user_message(self) -> str:
        service = self.metadata.get("service", "the service")
        return f"{service} is temporarily unavailable. Please try again later."


class RetryExhaustedError(ResilienceError):
    """Retry attempts exhausted"""

    default_message = "Retry attempts exhausted"
    default_error_code = "resilience.retry_exhausted"


class TimeoutError(ResilienceError):
    """Operation timed out"""

    default_message = "Operation timed out"
    default_error_code = "resilience.timeout"
    default_status_code = 504

    def _generate_user_message(self) -> str:
        timeout = self.metadata.get("timeout_seconds", "unknown")
        return f"Operation timed out after {timeout} seconds. Please try again."


class BulkheadRejectedError(ResilienceError):
    """Bulkhead rejected request (concurrency limit)"""

    default_message = "Bulkhead rejected request"
    default_error_code = "resilience.bulkhead_rejected"
    default_status_code = 503

    def _generate_user_message(self) -> str:
        return "Service is under heavy load. Please try again in a moment."


# ==============================================================================
# Storage Errors (500 - Server Error)
# ==============================================================================


class StorageError(MCPServerError):
    """Base class for storage errors"""

    default_message = "Storage error"
    default_error_code = "storage.error"
    default_status_code = 500
    default_category = ErrorCategory.SERVER_ERROR


class StorageBackendError(StorageError):
    """Storage backend error"""

    default_message = "Storage backend error"
    default_error_code = "storage.backend"


class DataNotFoundError(StorageError):
    """Data not found in storage"""

    default_message = "Data not found"
    default_error_code = "storage.not_found"
    default_status_code = 404


class DataIntegrityError(StorageError):
    """Data integrity check failed"""

    default_message = "Data integrity error"
    default_error_code = "storage.integrity"


# ==============================================================================
# Compliance Errors (403 - Forbidden)
# ==============================================================================


class ComplianceError(MCPServerError):
    """Base class for compliance errors"""

    default_message = "Compliance violation"
    default_error_code = "compliance.violation"
    default_status_code = 403
    default_category = ErrorCategory.SERVER_ERROR


class GDPRViolationError(ComplianceError):
    """GDPR compliance violation"""

    default_message = "GDPR compliance violation"
    default_error_code = "compliance.gdpr"


class HIPAAViolationError(ComplianceError):
    """HIPAA compliance violation"""

    default_message = "HIPAA compliance violation"
    default_error_code = "compliance.hipaa"


class SOC2ViolationError(ComplianceError):
    """SOC 2 compliance violation"""

    default_message = "SOC 2 compliance violation"
    default_error_code = "compliance.soc2"


# ==============================================================================
# Internal Server Errors (500)
# ==============================================================================


class InternalServerError(MCPServerError):
    """Unexpected internal server error"""

    default_message = "Internal server error"
    default_error_code = "server.internal"
    default_status_code = 500


class UnexpectedError(InternalServerError):
    """Unexpected error occurred"""

    default_message = "Unexpected error occurred"
    default_error_code = "server.unexpected"


class NotImplementedError(InternalServerError):
    """Feature not implemented"""

    default_message = "Feature not implemented"
    default_error_code = "server.not_implemented"
    default_status_code = 501
