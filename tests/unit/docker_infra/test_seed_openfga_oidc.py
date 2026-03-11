"""
Unit tests for Keycloak OIDC readiness check in seed_openfga.py.

These tests verify that the OpenFGA seeding script properly waits for
Keycloak's OIDC token endpoint to be ready before attempting to seed
authorization data.

Reference: Test Infrastructure Improvements Plan
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.docker]


class TestWaitForKeycloakOidc:
    """Tests for wait_for_keycloak_oidc() function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> Generator[None, None, None]:
        """Clear the OIDC token cache before each test."""
        # Import here to ensure module is loaded fresh
        from scripts.docker import seed_openfga

        seed_openfga._oidc_token_cache.clear()
        yield
        seed_openfga._oidc_token_cache.clear()

    def test_returns_true_when_oidc_not_configured(self) -> None:
        """
        GIVEN OIDC configuration is incomplete (missing env vars)
        WHEN wait_for_keycloak_oidc() is called
        THEN it should return True immediately (skip check)
        """
        from scripts.docker import seed_openfga

        # Patch environment to have no OIDC config
        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", None),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", None),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", None),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True

    def test_returns_true_when_only_client_id_missing(self) -> None:
        """
        GIVEN only OIDC client ID is missing
        WHEN wait_for_keycloak_oidc() is called
        THEN it should return True (skip check)
        """
        from scripts.docker import seed_openfga

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", None),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True

    def test_returns_true_on_successful_token_acquisition(self) -> None:
        """
        GIVEN OIDC is configured and Keycloak returns a valid token
        WHEN wait_for_keycloak_oidc() is called
        THEN it should return True and cache the token
        """
        from scripts.docker import seed_openfga

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token-12345",
            "expires_in": 3600,
        }

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "default"),
            patch("httpx.post", side_effect=lambda *a, **kw: mock_response),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True
        assert seed_openfga._oidc_token_cache.get("access_token") == "test-token-12345"
        assert "expires_at" in seed_openfga._oidc_token_cache

    def test_uses_exponential_backoff_on_connection_error(self) -> None:
        """
        GIVEN OIDC is configured but Keycloak connection fails initially
        WHEN wait_for_keycloak_oidc() is called
        THEN it should retry with exponential backoff and eventually succeed
        """
        from scripts.docker import seed_openfga

        call_count = 0

        def mock_post(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            # Succeed on third attempt
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "delayed-token",
                "expires_in": 3600,
            }
            return mock_resp

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "default"),
            patch.object(seed_openfga, "OIDC_MAX_RETRIES", 5),
            patch.object(seed_openfga, "OIDC_INITIAL_DELAY", 0.01),  # Fast for testing
            patch.object(seed_openfga, "OIDC_MAX_DELAY", 0.05),
            patch("httpx.post", side_effect=mock_post),
            patch("time.sleep"),  # Skip actual sleep
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True
        assert call_count == 3

    def test_returns_false_after_max_retries(self) -> None:
        """
        GIVEN OIDC is configured but Keycloak never responds
        WHEN wait_for_keycloak_oidc() is called
        THEN it should return False after max retries
        """
        from scripts.docker import seed_openfga

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "default"),
            patch.object(seed_openfga, "OIDC_MAX_RETRIES", 3),
            patch.object(seed_openfga, "OIDC_INITIAL_DELAY", 0.01),
            patch.object(seed_openfga, "OIDC_MAX_DELAY", 0.05),
            patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")),
            patch("time.sleep"),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is False

    def test_handles_timeout_exception(self) -> None:
        """
        GIVEN OIDC is configured but Keycloak times out
        WHEN wait_for_keycloak_oidc() is called
        THEN it should retry and handle TimeoutException
        """
        from scripts.docker import seed_openfga

        call_count = 0

        def mock_post(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("Request timed out")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "token-after-timeout",
                "expires_in": 3600,
            }
            return mock_resp

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "default"),
            patch.object(seed_openfga, "OIDC_MAX_RETRIES", 5),
            patch.object(seed_openfga, "OIDC_INITIAL_DELAY", 0.01),
            patch.object(seed_openfga, "OIDC_MAX_DELAY", 0.05),
            patch("httpx.post", side_effect=mock_post),
            patch("time.sleep"),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True
        assert call_count == 2

    def test_handles_non_200_response(self) -> None:
        """
        GIVEN OIDC is configured but Keycloak returns non-200 status initially
        WHEN wait_for_keycloak_oidc() is called
        THEN it should retry until success
        """
        from scripts.docker import seed_openfga

        call_count = 0

        def mock_post(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            if call_count < 3:
                mock_resp.status_code = 503  # Service unavailable
                return mock_resp
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "token-after-503",
                "expires_in": 3600,
            }
            return mock_resp

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "default"),
            patch.object(seed_openfga, "OIDC_MAX_RETRIES", 5),
            patch.object(seed_openfga, "OIDC_INITIAL_DELAY", 0.01),
            patch.object(seed_openfga, "OIDC_MAX_DELAY", 0.05),
            patch("httpx.post", side_effect=mock_post),
            patch("time.sleep"),
        ):
            result = seed_openfga.wait_for_keycloak_oidc()

        assert result is True
        assert call_count == 3

    def test_constructs_correct_token_endpoint(self) -> None:
        """
        GIVEN OIDC is configured with specific realm
        WHEN wait_for_keycloak_oidc() is called
        THEN it should construct the correct token endpoint URL
        """
        from scripts.docker import seed_openfga

        captured_url = None

        def mock_post(url: str, **kwargs: object) -> MagicMock:
            nonlocal captured_url
            captured_url = url
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "access_token": "test-token",
                "expires_in": 3600,
            }
            return mock_resp

        with (
            patch.object(seed_openfga, "KEYCLOAK_SERVER_URL", "http://keycloak:8080/"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_ID", "openfga-client"),
            patch.object(seed_openfga, "OPENFGA_OIDC_CLIENT_SECRET", "secret"),
            patch.object(seed_openfga, "KEYCLOAK_REALM", "test-realm"),
            patch("httpx.post", side_effect=mock_post),
        ):
            seed_openfga.wait_for_keycloak_oidc()

        expected_url = "http://keycloak:8080/realms/test-realm/protocol/openid-connect/token"
        assert captured_url == expected_url

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestMainIntegration:
    """Tests for main() function integration with wait_for_keycloak_oidc()."""

    def test_main_calls_oidc_check_before_openfga(self) -> None:
        """
        GIVEN the seeding script is running
        WHEN main() is called
        THEN wait_for_keycloak_oidc() should be called before wait_for_openfga()
        """
        from scripts.docker import seed_openfga

        call_order: list[str] = []

        def mock_oidc() -> bool:
            call_order.append("oidc")
            return True

        def mock_openfga() -> bool:
            call_order.append("openfga")
            return False  # Stop early

        with (
            patch.object(seed_openfga, "wait_for_keycloak_oidc", side_effect=mock_oidc),
            patch.object(seed_openfga, "wait_for_openfga", side_effect=mock_openfga),
        ):
            result = seed_openfga.main()

        assert call_order == ["oidc", "openfga"]
        assert result == 1  # Should fail because wait_for_openfga returned False

    def test_main_exits_early_if_oidc_fails(self) -> None:
        """
        GIVEN Keycloak OIDC is not ready
        WHEN main() is called
        THEN it should return 1 without calling wait_for_openfga()
        """
        from scripts.docker import seed_openfga

        openfga_called = False

        def mock_openfga() -> bool:
            nonlocal openfga_called
            openfga_called = True
            return True

        with (
            patch.object(seed_openfga, "wait_for_keycloak_oidc", side_effect=lambda: False),
            patch.object(seed_openfga, "wait_for_openfga", side_effect=mock_openfga),
        ):
            result = seed_openfga.main()

        assert result == 1
        assert openfga_called is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
