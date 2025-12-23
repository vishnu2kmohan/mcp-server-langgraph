"""
Integration tests for PII MCP Middleware

Tests the middleware that automatically tokenizes PII in MCP
request/response flows before LLM exposure.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.pii]


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_basic")
class TestPIIMiddlewareBasic:
    """Test suite for basic middleware functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_middleware_class_exists(self):
        """GIVEN the privacy module
        WHEN importing PIIMiddleware
        THEN it should be available
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        assert middleware is not None

    def test_middleware_has_process_request_method(self):
        """GIVEN a PIIMiddleware instance
        WHEN checking its methods
        THEN it should have process_request method
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        assert hasattr(middleware, "process_request")
        assert callable(middleware.process_request)

    def test_middleware_has_process_response_method(self):
        """GIVEN a PIIMiddleware instance
        WHEN checking its methods
        THEN it should have process_response method
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        assert hasattr(middleware, "process_response")
        assert callable(middleware.process_response)


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_request")
class TestPIIMiddlewareRequest:
    """Test suite for request processing"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_process_request_tokenizes_pii(self):
        """GIVEN a request containing PII
        WHEN processing through middleware
        THEN PII should be tokenized
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {"method": "tools/call", "params": {"input": "Email: john@example.com"}}

        processed, context = await middleware.process_request(request)

        # PII should be tokenized
        assert "john@example.com" not in str(processed)
        assert "<<PII_EMAIL_" in str(processed)

        # Context should contain lookup for untokenization
        assert "pii_lookup" in context

    @pytest.mark.asyncio
    async def test_process_request_preserves_structure(self):
        """GIVEN a request with nested structure
        WHEN processing through middleware
        THEN structure should be preserved
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "Contact test@example.com"},
            },
        }

        processed, _ = await middleware.process_request(request)

        assert "method" in processed
        assert "params" in processed
        assert "arguments" in processed["params"]

    @pytest.mark.asyncio
    async def test_process_request_without_pii_unchanged(self):
        """GIVEN a request without PII
        WHEN processing through middleware
        THEN request should be unchanged
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {"method": "tools/list", "params": {}}

        processed, context = await middleware.process_request(request)

        assert processed == request
        assert context.get("pii_lookup", {}) == {}


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_response")
class TestPIIMiddlewareResponse:
    """Test suite for response processing"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_process_response_untokenizes_pii(self):
        """GIVEN a response with tokens and a lookup table
        WHEN processing through middleware
        THEN tokens should be restored to original values
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()

        # First, process a request to get the lookup table
        request = {"method": "tools/call", "params": {"input": "Email: john@example.com"}}
        processed_req, context = await middleware.process_request(request)

        # Simulate LLM response with the token
        # Extract the token from processed request
        token = None
        for key, value in context.get("pii_lookup", {}).items():
            if value == "john@example.com":
                token = key
                break

        response = {"result": f"Found email: {token}"}
        restored = await middleware.process_response(response, context)

        assert "john@example.com" in str(restored)

    @pytest.mark.asyncio
    async def test_process_response_without_context_unchanged(self):
        """GIVEN a response without PII context
        WHEN processing through middleware
        THEN response should be unchanged
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        response = {"result": "No PII here"}

        restored = await middleware.process_response(response, {})

        assert restored == response


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_roundtrip")
class TestPIIMiddlewareRoundtrip:
    """Test suite for complete request/response roundtrip"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_all_pii(self):
        """GIVEN a request with multiple PII types
        WHEN processing request and response through middleware
        THEN all original values should be restored
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()

        # Request with multiple PII
        request = {
            "method": "tools/call",
            "params": {"input": "Contact: john@example.com, Phone: 555-123-4567, SSN: 123-45-6789"},
        }

        # Process request (tokenize)
        processed_req, context = await middleware.process_request(request)

        # Verify PII is tokenized
        input_str = str(processed_req)
        assert "john@example.com" not in input_str
        assert "555-123-4567" not in input_str
        assert "123-45-6789" not in input_str

        # Simulate response echoing the tokens
        response = {"result": processed_req["params"]["input"]}

        # Process response (untokenize)
        restored = await middleware.process_response(response, context)

        # Verify all PII is restored
        result_str = str(restored)
        assert "john@example.com" in result_str
        assert "555-123-4567" in result_str
        assert "123-45-6789" in result_str


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_feature_flag")
class TestPIIMiddlewareFeatureFlag:
    """Test suite for feature flag integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_middleware_disabled_passes_through(self):
        """GIVEN PII feature flag is disabled
        WHEN processing request with PII
        THEN request should pass through unchanged
        """
        from unittest.mock import patch

        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {"method": "tools/call", "params": {"input": "Email: john@example.com"}}

        with patch(
            "mcp_server_langgraph.privacy.middleware.is_feature_enabled",
            return_value=False,
        ):
            processed, context = await middleware.process_request(request)

            # Should pass through unchanged
            assert processed == request
            assert context.get("pii_lookup", {}) == {}


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_pii_middleware_mcp_methods")
class TestPIIMiddlewareMCPMethods:
    """Test suite for MCP method-specific handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_skip_tokenization_for_tools_list(self):
        """GIVEN a tools/list request
        WHEN processing through middleware
        THEN no tokenization should occur (no user content)
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {"method": "tools/list", "params": {}}

        processed, context = await middleware.process_request(request)

        assert processed == request
        assert context.get("pii_lookup", {}) == {}

    @pytest.mark.asyncio
    async def test_tokenize_for_tools_call(self):
        """GIVEN a tools/call request with PII
        WHEN processing through middleware
        THEN tokenization should occur
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {
            "method": "tools/call",
            "params": {"name": "send_email", "arguments": {"to": "john@example.com"}},
        }

        processed, context = await middleware.process_request(request)

        assert "john@example.com" not in str(processed)
        assert len(context.get("pii_lookup", {})) > 0

    @pytest.mark.asyncio
    async def test_tokenize_for_prompts_get(self):
        """GIVEN a prompts/get request with PII in arguments
        WHEN processing through middleware
        THEN tokenization should occur
        """
        from mcp_server_langgraph.privacy.middleware import PIIMiddleware

        middleware = PIIMiddleware()
        request = {
            "method": "prompts/get",
            "params": {"name": "analyze", "arguments": {"user_email": "test@example.com"}},
        }

        processed, context = await middleware.process_request(request)

        assert "test@example.com" not in str(processed)
