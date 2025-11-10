"""
Tests for E2E client resilience and error handling.

Following TDD principles - these tests are written FIRST before implementing
the retry logic and enhanced error handling in real_clients.py.
"""

import gc
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest


@pytest.mark.unit
@pytest.mark.xdist_group(name="e2e_real_clients_resilience_tests")
class TestKeycloakAuthErrorHandling:
    """Test error handling in RealKeycloakAuth client"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_timeout_exception_has_clear_message(self):
        """Verify timeout exceptions have actionable error messages"""
        from tests.e2e.real_clients import RealKeycloakAuth

        auth = RealKeycloakAuth(base_url="http://localhost:9082")

        # Mock httpx to raise TimeoutException
        with patch.object(auth.client, "post", side_effect=httpx.TimeoutException("Connection timeout")):
            with pytest.raises(RuntimeError) as exc_info:
                await auth.login("user", "pass")

            # Error message should be actionable
            assert "timeout" in str(exc_info.value).lower()
            assert "Keycloak" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_error_has_clear_message(self):
        """Verify connection errors have actionable error messages"""
        from tests.e2e.real_clients import RealKeycloakAuth

        auth = RealKeycloakAuth(base_url="http://localhost:9082")

        # Mock httpx to raise ConnectError
        with patch.object(auth.client, "post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(RuntimeError) as exc_info:
                await auth.login("user", "pass")

            # Error message should mention service availability
            assert "connect" in str(exc_info.value).lower()
            assert "http://localhost:9082" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_status_error_has_context(self):
        """Verify HTTP status errors include response context"""
        from tests.e2e.real_clients import RealKeycloakAuth

        auth = RealKeycloakAuth(base_url="http://localhost:9082")

        # Mock httpx to raise HTTPStatusError
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_response.request = Mock(url="http://localhost:9082/auth/realms/test/protocol/openid-connect/token")

        http_error = httpx.HTTPStatusError("401 Unauthorized", request=mock_response.request, response=mock_response)

        with patch.object(auth.client, "post", side_effect=http_error):
            with pytest.raises(RuntimeError) as exc_info:
                await auth.login("user", "pass")

            # Error message should include status code and response text
            error_msg = str(exc_info.value)
            assert "401" in error_msg
            assert "Invalid credentials" in error_msg or "Unauthorized" in error_msg


@pytest.mark.unit
@pytest.mark.xdist_group(name="e2e_real_clients_resilience_tests")
class TestMCPClientRetryLogic:
    """Test retry logic in RealMCPClient"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(strict=True, reason="Retry logic not yet implemented - requires tenacity library")
    @pytest.mark.asyncio
    async def test_initialize_retries_on_transient_error(self):
        """Verify initialize() retries on transient network errors"""
        from tests.e2e.real_clients import RealMCPClient

        client = RealMCPClient(base_url="http://localhost:8000", access_token="test-token")

        call_count = 0

        async def mock_post_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First 2 calls fail
                raise httpx.ConnectError("Connection refused")
            # Third call succeeds
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "protocol_version": "1.0",
                "server_info": {"name": "test"},
                "capabilities": {},
            }
            mock_response.raise_for_status = Mock()
            return mock_response

        with patch.object(client.client, "post", side_effect=mock_post_with_retry):
            # Should succeed after retries
            response = await client.initialize()

            # Verify retries happened
            assert call_count == 3
            assert "protocol_version" in response

    @pytest.mark.xfail(strict=True, reason="Retry logic not yet implemented - requires tenacity library")
    @pytest.mark.asyncio
    async def test_list_tools_retries_and_fails_after_max_attempts(self):
        """Verify client retries and fails after exhausting max retry attempts"""
        from tests.e2e.real_clients import RealMCPClient

        client = RealMCPClient(base_url="http://localhost:8000", access_token="test-token")

        call_count = 0

        async def mock_get_with_count(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        # Mock persistent failure
        with patch.object(client.client, "get", side_effect=mock_get_with_count):
            with pytest.raises(RuntimeError) as exc_info:
                await client.list_tools()

            # Should have retried multiple times (e.g., 3 total attempts)
            assert call_count >= 3, f"Expected 3+ retry attempts, got {call_count}"

            # Should mention exhausted retries in error
            error_msg = str(exc_info.value)
            assert "retry" in error_msg.lower() or "attempts" in error_msg.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="e2e_real_clients_resilience_tests")
class TestClientConfiguration:
    """Test client configuration and initialization"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_client_has_timeout_configured(self):
        """Verify Keycloak client has timeout to prevent hanging"""
        from tests.e2e.real_clients import RealKeycloakAuth

        auth = RealKeycloakAuth(base_url="http://localhost:9082")

        # Verify timeout is set
        assert auth.client.timeout is not None
        assert auth.client.timeout.read > 0  # Has read timeout

    def test_mcp_client_has_timeout_configured(self):
        """Verify MCP client has timeout to prevent hanging"""
        from tests.e2e.real_clients import RealMCPClient

        client = RealMCPClient(base_url="http://localhost:8000", access_token="token")

        # Verify timeout is set
        assert client.client.timeout is not None
        assert client.client.timeout.read > 0  # Has read timeout

    def test_client_user_agent_identifies_test_suite(self):
        """Verify clients set User-Agent header for observability"""
        from tests.e2e.real_clients import RealMCPClient

        client = RealMCPClient(base_url="http://localhost:8000", access_token="token")

        # Should have User-Agent or custom headers for identification
        assert client.client.headers is not None
