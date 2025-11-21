"""
Unit tests for custom exception hierarchy.

Tests exception creation, HTTP mapping, and error responses.
"""

import gc
from unittest.mock import Mock, patch

import pytest

from mcp_server_langgraph.core.exceptions import (  # Configuration errors; Authentication errors; Authorization errors; Rate limiting errors; Validation errors; External service errors; Resilience errors; Storage errors; Compliance errors; Internal errors  # noqa: E501

pytestmark = pytest.mark.unit

    AuthenticationError,
    AuthorizationError,
    BulkheadRejectedError,
    CircuitBreakerOpenError,
    ComplianceError,
    ConfigurationError,
    ConstraintViolationError,
    DataIntegrityError,
    DataNotFoundError,
    ErrorCategory,
    ExternalServiceError,
    GDPRViolationError,
    HIPAAViolationError,
    InputValidationError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    KeycloakError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    MCPServerException,
    MFARequiredError,
    OpenFGAError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    RateLimitExceededError,
    RedisError,
    ResilienceError,
    ResourceNotFoundError,
    RetryExhaustedError,
    RetryPolicy,
    SchemaValidationError,
    SOC2ViolationError,
    StorageError,
    TimeoutError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
)


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestMCPServerExceptionBase:
    """Test base MCPServerException class"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_exception_creation_with_defaults(self):
        """Test creating exception with default values"""
        exc = MCPServerException()
        assert exc.message == "An error occurred"
        assert exc.error_code == "server.error"
        assert exc.status_code == 500
        assert exc.category == ErrorCategory.SERVER_ERROR
        assert exc.retry_policy == RetryPolicy.NEVER

    @pytest.mark.unit
    def test_exception_creation_with_custom_values(self):
        """Test creating exception with custom values"""
        exc = MCPServerException(
            message="Custom error",
            error_code="custom.error",
            status_code=418,
            metadata={"key": "value"},
        )
        assert exc.message == "Custom error"
        assert exc.error_code == "custom.error"
        assert exc.status_code == 418
        assert exc.metadata == {"key": "value"}

    @pytest.mark.unit
    def test_exception_to_dict(self):
        """Test converting exception to dictionary"""
        exc = MCPServerException(
            message="Test error",
            error_code="test.error",
            metadata={"user_id": "123"},
        )

        error_dict = exc.to_dict()

        assert "error" in error_dict
        assert error_dict["error"]["code"] == "test.error"
        assert error_dict["error"]["metadata"]["user_id"] == "123"

    @pytest.mark.unit
    def test_exception_string_representation(self):
        """Test exception string representation"""
        exc = MCPServerException(
            message="Test error",
            error_code="test.error",
            metadata={"key": "value"},
        )

        str_repr = str(exc)
        assert "test.error" in str_repr
        assert "Test error" in str_repr

    @pytest.mark.unit
    def test_exception_with_cause(self):
        """Test exception with original cause"""
        original = ValueError("Original error")
        exc = MCPServerException(message="Wrapped error", cause=original)

        assert exc.cause == original
        assert exc.message == "Wrapped error"


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestAuthenticationExceptions:
    """Test authentication exception types"""

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError"""
        exc = InvalidCredentialsError()
        assert exc.status_code == 401
        assert exc.category == ErrorCategory.AUTH_ERROR
        assert "password" in exc.user_message.lower()

    @pytest.mark.unit
    def test_token_expired_error(self):
        """Test TokenExpiredError"""
        exc = TokenExpiredError()
        assert exc.status_code == 401
        assert exc.error_code == "auth.token_expired"
        assert exc.retry_policy == RetryPolicy.CONDITIONAL
        assert "expired" in exc.user_message.lower()

    @pytest.mark.unit
    def test_token_invalid_error(self):
        """Test TokenInvalidError"""
        exc = TokenInvalidError()
        assert exc.status_code == 401
        assert exc.error_code == "auth.token_invalid"

    @pytest.mark.unit
    def test_mfa_required_error(self):
        """Test MFARequiredError"""

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

        exc = MFARequiredError()
        assert exc.status_code == 403
        assert "mfa" in exc.user_message.lower()


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestAuthorizationExceptions:
    """Test authorization exception types"""

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_permission_denied_error(self):
        """Test PermissionDeniedError"""
        exc = PermissionDeniedError(metadata={"user": "alice", "resource": "doc_123"})
        assert exc.status_code == 403
        assert exc.error_code == "authz.permission_denied"
        assert "permission" in exc.user_message.lower()

    @pytest.mark.unit
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError"""
        exc = ResourceNotFoundError()
        assert exc.status_code == 404
        assert "not found" in exc.user_message.lower()

    @pytest.mark.unit
    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError"""
        exc = InsufficientPermissionsError()
        assert exc.status_code == 403
        assert "upgrade" in exc.user_message.lower()


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestRateLimitExceptions:
    """Test rate limiting exception types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError"""
        exc = RateLimitExceededError(metadata={"retry_after": 30})
        assert exc.status_code == 429
        assert exc.category == ErrorCategory.RATE_LIMIT
        assert "30" in exc.user_message

    @pytest.mark.unit
    def test_quota_exceeded_error(self):
        """Test QuotaExceededError"""
        exc = QuotaExceededError()
        assert exc.status_code == 429
        assert "quota" in exc.user_message.lower()


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestValidationExceptions:
    """Test validation exception types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_input_validation_error(self):
        """Test InputValidationError"""
        exc = InputValidationError(metadata={"field": "email"})
        assert exc.status_code == 400
        assert exc.category == ErrorCategory.CLIENT_ERROR
        assert exc.retry_policy == RetryPolicy.NEVER
        assert "email" in exc.user_message

    @pytest.mark.unit
    def test_schema_validation_error(self):
        """Test SchemaValidationError"""
        exc = SchemaValidationError()
        assert exc.status_code == 400

    @pytest.mark.unit
    def test_constraint_violation_error(self):
        """Test ConstraintViolationError"""
        exc = ConstraintViolationError()
        assert exc.status_code == 400


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExternalServiceExceptions:
    """Test external service exception types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_llm_provider_error(self):
        """Test LLMProviderError"""
        exc = LLMProviderError(metadata={"model": "claude-3-5-sonnet"})
        assert exc.status_code == 503
        assert exc.category == ErrorCategory.EXTERNAL_ERROR
        assert exc.retry_policy == RetryPolicy.ALWAYS

    @pytest.mark.unit
    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError"""
        exc = LLMRateLimitError()
        assert exc.status_code == 429

    @pytest.mark.unit
    def test_llm_timeout_error(self):
        """Test LLMTimeoutError"""
        exc = LLMTimeoutError()
        assert exc.status_code == 504

    @pytest.mark.unit
    def test_llm_model_not_found_error(self):
        """Test LLMModelNotFoundError"""
        exc = LLMModelNotFoundError()
        assert exc.status_code == 400
        assert exc.retry_policy == RetryPolicy.NEVER

    @pytest.mark.unit
    def test_openfga_error(self):
        """Test OpenFGAError"""
        exc = OpenFGAError()
        assert exc.status_code == 503

    @pytest.mark.unit
    def test_redis_error(self):
        """Test RedisError"""
        exc = RedisError()
        assert exc.status_code == 503

    @pytest.mark.unit
    def test_keycloak_error(self):
        """Test KeycloakError"""
        exc = KeycloakError()
        assert exc.status_code == 503


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestResilienceExceptions:
    """Test resilience pattern exception types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_circuit_breaker_open_error(self):
        """Test CircuitBreakerOpenError"""
        exc = CircuitBreakerOpenError(metadata={"service": "llm"})
        assert exc.status_code == 503
        assert "llm" in exc.user_message

    @pytest.mark.unit
    def test_retry_exhausted_error(self):
        """Test RetryExhaustedError"""
        exc = RetryExhaustedError()
        assert exc.status_code == 503

    @pytest.mark.unit
    def test_timeout_error(self):
        """Test TimeoutError"""
        exc = TimeoutError(metadata={"timeout_seconds": 30})
        assert exc.status_code == 504
        assert "30" in exc.user_message

    @pytest.mark.unit
    def test_bulkhead_rejected_error(self):
        """Test BulkheadRejectedError"""
        exc = BulkheadRejectedError()
        assert exc.status_code == 503
        assert "heavy load" in exc.user_message.lower()


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestComplianceExceptions:
    """Test compliance exception types"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_gdpr_violation_error(self):
        """Test GDPRViolationError"""
        exc = GDPRViolationError()
        assert exc.status_code == 403

    @pytest.mark.unit
    def test_hipaa_violation_error(self):
        """Test HIPAAViolationError"""
        exc = HIPAAViolationError()
        assert exc.status_code == 403

    @pytest.mark.unit
    def test_soc2_violation_error(self):
        """Test SOC2ViolationError"""
        exc = SOC2ViolationError()
        assert exc.status_code == 403


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestStorageExceptions:
    """Test storage exception types"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_data_not_found_error(self):
        """Test DataNotFoundError"""
        exc = DataNotFoundError()
        assert exc.status_code == 404

    @pytest.mark.unit
    def test_data_integrity_error(self):
        """Test DataIntegrityError"""
        exc = DataIntegrityError()
        assert exc.status_code == 500


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionMetadata:
    """Test exception metadata handling"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_exception_with_trace_id(self):
        """Test exception with trace ID"""
        exc = MCPServerException(trace_id="abc123")
        assert exc.trace_id == "abc123"

        error_dict = exc.to_dict()
        assert error_dict["error"]["trace_id"] == "abc123"

    @pytest.mark.unit
    def test_exception_with_metadata(self):
        """Test exception with rich metadata"""
        exc = MCPServerException(
            metadata={
                "user_id": "user_123",
                "resource_id": "resource_456",
                "action": "read",
            }
        )

        assert exc.metadata["user_id"] == "user_123"
        assert "user_id" in str(exc)

    @pytest.mark.unit
    def test_exception_auto_trace_id(self):
        """Test exception auto-captures trace ID"""
        with patch("mcp_server_langgraph.core.exceptions.trace") as mock_trace:
            # Mock valid span with trace ID
            mock_span = Mock()
            mock_context = Mock()
            mock_context.is_valid = True
            mock_context.trace_id = 12345678901234567890
            mock_span.get_span_context.return_value = mock_context
            mock_trace.get_current_span.return_value = mock_span

            exc = MCPServerException()
            assert exc.trace_id is not None


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionHTTPMapping:
    """Test HTTP status code mapping"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_auth_exceptions_map_to_401(self):
        """Test authentication exceptions map to 401"""
        exceptions = [InvalidCredentialsError(), TokenExpiredError(), TokenInvalidError()]

        for exc in exceptions:
            assert exc.status_code == 401

    @pytest.mark.unit
    def test_authz_exceptions_map_to_403(self):
        """Test authorization exceptions map to 403"""
        exceptions = [PermissionDeniedError(), InsufficientPermissionsError()]

        for exc in exceptions:
            assert exc.status_code == 403

    @pytest.mark.unit
    def test_rate_limit_exceptions_map_to_429(self):
        """Test rate limit exceptions map to 429"""
        exceptions = [RateLimitExceededError(), QuotaExceededError(), LLMRateLimitError()]

        for exc in exceptions:
            assert exc.status_code == 429

    @pytest.mark.unit
    def test_validation_exceptions_map_to_400(self):
        """Test validation exceptions map to 400"""
        exceptions = [InputValidationError(), SchemaValidationError(), ConstraintViolationError()]

        for exc in exceptions:
            assert exc.status_code == 400

    @pytest.mark.unit
    def test_not_found_exceptions_map_to_404(self):
        """Test not found exceptions map to 404"""
        exc = ResourceNotFoundError()
        assert exc.status_code == 404


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionRetryPolicy:
    """Test retry policy classification"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_client_errors_never_retry(self):
        """Test that client errors have NEVER retry policy"""
        exceptions = [
            ValidationError(),
            InputValidationError(),
            AuthorizationError(),
            PermissionDeniedError(),
        ]

        for exc in exceptions:
            assert exc.retry_policy == RetryPolicy.NEVER

    @pytest.mark.unit
    def test_external_errors_always_retry(self):
        """Test that external service errors have ALWAYS retry policy"""
        exceptions = [ExternalServiceError(), LLMProviderError(), OpenFGAError(), RedisError()]

        for exc in exceptions:
            assert exc.retry_policy == RetryPolicy.ALWAYS

    @pytest.mark.unit
    def test_resilience_errors_conditional_retry(self):
        """Test that resilience errors have CONDITIONAL retry policy"""
        exceptions = [CircuitBreakerOpenError(), TimeoutError(), BulkheadRejectedError()]

        for exc in exceptions:
            assert exc.retry_policy == RetryPolicy.CONDITIONAL


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionUserMessages:
    """Test user-friendly error messages"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_auth_error_user_message(self):
        """Test authentication error user message"""
        exc = TokenExpiredError()
        assert "sign in" in exc.user_message.lower()
        assert "expired" in exc.user_message.lower()

    @pytest.mark.unit
    def test_authz_error_user_message(self):
        """Test authorization error user message"""
        exc = PermissionDeniedError()
        assert "permission" in exc.user_message.lower()

    @pytest.mark.unit
    def test_rate_limit_error_user_message(self):
        """Test rate limit error user message"""
        exc = RateLimitExceededError(metadata={"retry_after": 45})
        assert "45" in exc.user_message
        assert "wait" in exc.user_message.lower()

    @pytest.mark.unit
    def test_custom_user_message(self):
        """Test custom user message override"""
        exc = MCPServerException(user_message="Custom message for user")
        assert exc.user_message == "Custom message for user"


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionCategories:
    """Test exception category classification"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_client_error_category(self):
        """Test CLIENT_ERROR category"""
        exceptions = [ValidationError(), InputValidationError()]

        for exc in exceptions:
            assert exc.category == ErrorCategory.CLIENT_ERROR

    @pytest.mark.unit
    def test_server_error_category(self):
        """Test SERVER_ERROR category"""
        exceptions = [ConfigurationError(), StorageError(), ComplianceError()]

        for exc in exceptions:
            assert exc.category == ErrorCategory.SERVER_ERROR

    @pytest.mark.unit
    def test_external_error_category(self):
        """Test EXTERNAL_ERROR category"""
        exceptions = [LLMProviderError(), OpenFGAError(), RedisError()]

        for exc in exceptions:
            assert exc.category == ErrorCategory.EXTERNAL_ERROR

    @pytest.mark.unit
    def test_auth_error_category(self):
        """Test AUTH_ERROR category"""
        exceptions = [AuthenticationError(), AuthorizationError()]

        for exc in exceptions:
            assert exc.category == ErrorCategory.AUTH_ERROR

    @pytest.mark.unit
    def test_rate_limit_category(self):
        """Test RATE_LIMIT category"""
        exc = RateLimitError()
        assert exc.category == ErrorCategory.RATE_LIMIT


@pytest.mark.xdist_group(name="core_exceptions_tests")
class TestExceptionInheritance:
    """Test exception inheritance hierarchy"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from MCPServerException"""
        exceptions = [
            ConfigurationError(),
            AuthenticationError(),
            AuthorizationError(),
            RateLimitError(),
            ValidationError(),
            ExternalServiceError(),
            ResilienceError(),
            StorageError(),
            ComplianceError(),
        ]

        for exc in exceptions:
            assert isinstance(exc, MCPServerException)
            assert isinstance(exc, Exception)

    @pytest.mark.unit
    def test_exception_subclass_hierarchy(self):
        """Test exception subclass hierarchy"""
        exc = TokenExpiredError()

        # Should be instance of all parent classes
        assert isinstance(exc, TokenExpiredError)
        assert isinstance(exc, AuthenticationError)
        assert isinstance(exc, MCPServerException)
        assert isinstance(exc, Exception)
