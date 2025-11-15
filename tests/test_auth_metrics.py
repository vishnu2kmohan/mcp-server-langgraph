"""
Tests for authentication metrics

Verifies that all authentication metrics are properly defined
and helper functions work correctly.
"""

import gc
from unittest.mock import patch

import pytest

from mcp_server_langgraph.auth import metrics


@pytest.mark.unit
@pytest.mark.xdist_group(name="testmetricdefinitions")
class TestMetricDefinitions:
    """Test that all metrics are properly defined"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_login_metrics_defined(self):
        """Test login-related metrics are defined"""
        assert hasattr(metrics, "auth_login_attempts")
        assert hasattr(metrics, "auth_login_duration")
        assert hasattr(metrics, "auth_login_failures")

    def test_token_metrics_defined(self):
        """Test token-related metrics are defined"""
        assert hasattr(metrics, "auth_token_created")
        assert hasattr(metrics, "auth_token_verifications")
        assert hasattr(metrics, "auth_token_verify_duration")
        assert hasattr(metrics, "auth_token_refresh_attempts")

    def test_jwks_metrics_defined(self):
        """Test JWKS cache metrics are defined"""
        assert hasattr(metrics, "auth_jwks_cache_operations")
        assert hasattr(metrics, "auth_jwks_fetch_duration")
        assert hasattr(metrics, "auth_jwks_refresh_count")

    def test_session_metrics_defined(self):
        """Test session management metrics are defined"""
        assert hasattr(metrics, "auth_sessions_active")
        assert hasattr(metrics, "auth_session_created")
        assert hasattr(metrics, "auth_session_retrieved")
        assert hasattr(metrics, "auth_session_refreshed")
        assert hasattr(metrics, "auth_session_revoked")
        assert hasattr(metrics, "auth_session_expired")
        assert hasattr(metrics, "auth_session_duration")
        assert hasattr(metrics, "auth_session_operations_duration")

    def test_user_provider_metrics_defined(self):
        """Test user provider metrics are defined"""
        assert hasattr(metrics, "auth_provider_calls")
        assert hasattr(metrics, "auth_provider_duration")
        assert hasattr(metrics, "auth_provider_errors")

    def test_openfga_metrics_defined(self):
        """Test OpenFGA integration metrics are defined"""
        assert hasattr(metrics, "auth_openfga_sync_attempts")
        assert hasattr(metrics, "auth_openfga_sync_duration")
        assert hasattr(metrics, "auth_openfga_tuples_written")
        assert hasattr(metrics, "auth_openfga_sync_errors")

    def test_authorization_metrics_defined(self):
        """Test authorization metrics are defined"""
        assert hasattr(metrics, "auth_authz_checks")
        assert hasattr(metrics, "auth_authz_duration")
        assert hasattr(metrics, "auth_authz_cache_operations")

    def test_role_mapping_metrics_defined(self):
        """Test role mapping metrics are defined"""
        assert hasattr(metrics, "auth_role_mapping_operations")
        assert hasattr(metrics, "auth_role_mapping_rules_applied")
        assert hasattr(metrics, "auth_role_mapping_tuples_generated")
        assert hasattr(metrics, "auth_role_mapping_duration")

    def test_concurrent_session_metrics_defined(self):
        """Test concurrent session metrics are defined"""
        assert hasattr(metrics, "auth_concurrent_sessions")
        assert hasattr(metrics, "auth_session_limit_reached")


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordloginattempt")
class TestRecordLoginAttempt:
    """Test record_login_attempt helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_login_attempt_success(self):
        """Test recording successful login attempt"""
        with patch.object(metrics.auth_login_attempts, "add") as mock_add:
            with patch.object(metrics.auth_login_duration, "record") as mock_record:
                metrics.record_login_attempt("keycloak", "success", 150.5)

                mock_add.assert_called_once_with(1, {"provider": "keycloak", "result": "success"})
                mock_record.assert_called_once_with(150.5, {"provider": "keycloak"})

    def test_record_login_attempt_failure(self):
        """Test recording failed login attempt"""
        with patch.object(metrics.auth_login_attempts, "add") as mock_attempts:
            with patch.object(metrics.auth_login_duration, "record") as mock_duration:
                with patch.object(metrics.auth_login_failures, "add") as mock_failures:
                    metrics.record_login_attempt("inmemory", "invalid_credentials", 50.2)

                    mock_attempts.assert_called_once_with(1, {"provider": "inmemory", "result": "invalid_credentials"})
                    mock_duration.assert_called_once_with(50.2, {"provider": "inmemory"})
                    mock_failures.assert_called_once_with(1, {"provider": "inmemory", "reason": "invalid_credentials"})


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordtokenverification")
class TestRecordTokenVerification:
    """Test record_token_verification helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_token_verification_success(self):
        """Test recording successful token verification"""
        with patch.object(metrics.auth_token_verifications, "add") as mock_add:
            with patch.object(metrics.auth_token_verify_duration, "record") as mock_record:
                metrics.record_token_verification("valid", 25.3, "keycloak")

                mock_add.assert_called_once_with(1, {"result": "valid", "provider": "keycloak"})
                mock_record.assert_called_once_with(25.3, {"provider": "keycloak"})

    def test_record_token_verification_expired(self):
        """Test recording expired token verification"""
        with patch.object(metrics.auth_token_verifications, "add") as mock_add:
            with patch.object(metrics.auth_token_verify_duration, "record") as mock_record:
                metrics.record_token_verification("expired", 10.1, "jwt")

                mock_add.assert_called_once_with(1, {"result": "expired", "provider": "jwt"})
                mock_record.assert_called_once_with(10.1, {"provider": "jwt"})

    def test_record_token_verification_default_provider(self):
        """Test token verification with default provider"""
        with patch.object(metrics.auth_token_verifications, "add") as mock_add:
            with patch.object(metrics.auth_token_verify_duration, "record") as mock_record:
                metrics.record_token_verification("valid", 15.0)

                mock_add.assert_called_once_with(1, {"result": "valid", "provider": "unknown"})
                mock_record.assert_called_once_with(15.0, {"provider": "unknown"})


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordsessionoperation")
class TestRecordSessionOperation:
    """Test record_session_operation helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_session_create_success(self):
        """Test recording successful session creation"""
        with patch.object(metrics.auth_session_created, "add") as mock_created:
            with patch.object(metrics.auth_sessions_active, "add") as mock_active:
                with patch.object(metrics.auth_session_operations_duration, "record") as mock_duration:
                    metrics.record_session_operation("create", "redis", "success", 45.2)

                    mock_created.assert_called_once_with(1, {"backend": "redis", "result": "success"})
                    mock_active.assert_called_once_with(1, {"backend": "redis"})
                    mock_duration.assert_called_once_with(45.2, {"operation": "create", "backend": "redis"})

    def test_record_session_create_failure(self):
        """Test recording failed session creation"""
        with patch.object(metrics.auth_session_created, "add") as mock_created:
            with patch.object(metrics.auth_sessions_active, "add") as mock_active:
                with patch.object(metrics.auth_session_operations_duration, "record") as mock_duration:
                    metrics.record_session_operation("create", "redis", "error", 12.5)

                    mock_created.assert_called_once_with(1, {"backend": "redis", "result": "error"})
                    # Active count should NOT be incremented on failure
                    mock_active.assert_not_called()
                    mock_duration.assert_called_once()

    def test_record_session_retrieve(self):
        """Test recording session retrieval"""
        with patch.object(metrics.auth_session_retrieved, "add") as mock_retrieved:
            with patch.object(metrics.auth_session_operations_duration, "record") as mock_duration:
                metrics.record_session_operation("retrieve", "inmemory", "success", 5.1)

                mock_retrieved.assert_called_once_with(1, {"backend": "inmemory", "result": "success"})
                mock_duration.assert_called_once_with(5.1, {"operation": "retrieve", "backend": "inmemory"})

    def test_record_session_refresh(self):
        """Test recording session refresh"""
        with patch.object(metrics.auth_session_refreshed, "add") as mock_refreshed:
            with patch.object(metrics.auth_session_operations_duration, "record") as mock_duration:
                metrics.record_session_operation("refresh", "redis", "success", 8.3)

                mock_refreshed.assert_called_once_with(1, {"backend": "redis", "result": "success"})
                mock_duration.assert_called_once()

    def test_record_session_revoke_success(self):
        """Test recording successful session revocation"""
        with patch.object(metrics.auth_session_revoked, "add") as mock_revoked:
            with patch.object(metrics.auth_sessions_active, "add") as mock_active:
                with patch.object(metrics.auth_session_operations_duration, "record") as mock_duration:
                    metrics.record_session_operation("revoke", "redis", "success", 15.7)

                    mock_revoked.assert_called_once_with(1, {"backend": "redis", "result": "success"})
                    # Active count should be decremented
                    mock_active.assert_called_once_with(-1, {"backend": "redis"})
                    mock_duration.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordjwksoperation")
class TestRecordJWKSOperation:
    """Test record_jwks_operation helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_jwks_cache_hit(self):
        """Test recording JWKS cache hit"""
        with patch.object(metrics.auth_jwks_cache_operations, "add") as mock_add:
            metrics.record_jwks_operation("hit", "success")

            mock_add.assert_called_once_with(1, {"type": "hit"})

    def test_record_jwks_cache_miss(self):
        """Test recording JWKS cache miss"""
        with patch.object(metrics.auth_jwks_cache_operations, "add") as mock_add:
            metrics.record_jwks_operation("miss", "success")

            mock_add.assert_called_once_with(1, {"type": "miss"})

    def test_record_jwks_refresh(self):
        """Test recording JWKS refresh"""
        with patch.object(metrics.auth_jwks_refresh_count, "add") as mock_add:
            with patch.object(metrics.auth_jwks_fetch_duration, "record") as mock_record:
                metrics.record_jwks_operation("refresh", "success", 125.5)

                mock_add.assert_called_once_with(1, {"result": "success"})
                mock_record.assert_called_once_with(125.5)

    def test_record_jwks_without_duration(self):
        """Test recording JWKS operation without duration"""
        with patch.object(metrics.auth_jwks_cache_operations, "add") as mock_add:
            with patch.object(metrics.auth_jwks_fetch_duration, "record") as mock_record:
                metrics.record_jwks_operation("hit", "success", None)

                mock_add.assert_called_once()
                # Duration should not be recorded when None
                mock_record.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordopenfgasync")
class TestRecordOpenFGASync:
    """Test record_openfga_sync helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_openfga_sync_success(self):
        """Test recording successful OpenFGA sync"""
        with patch.object(metrics.auth_openfga_sync_attempts, "add") as mock_attempts:
            with patch.object(metrics.auth_openfga_sync_duration, "record") as mock_duration:
                with patch.object(metrics.auth_openfga_tuples_written, "record") as mock_tuples:
                    metrics.record_openfga_sync("success", 250.5, 15)

                    mock_attempts.assert_called_once_with(1, {"result": "success"})
                    mock_duration.assert_called_once_with(250.5)
                    mock_tuples.assert_called_once_with(15)

    def test_record_openfga_sync_failure(self):
        """Test recording failed OpenFGA sync"""
        with patch.object(metrics.auth_openfga_sync_attempts, "add") as mock_attempts:
            with patch.object(metrics.auth_openfga_sync_duration, "record") as mock_duration:
                with patch.object(metrics.auth_openfga_sync_errors, "add") as mock_errors:
                    with patch.object(metrics.auth_openfga_tuples_written, "record") as mock_tuples:
                        metrics.record_openfga_sync("error", 100.0, 0)

                        mock_attempts.assert_called_once_with(1, {"result": "error"})
                        mock_duration.assert_called_once_with(100.0)
                        mock_errors.assert_called_once_with(1, {"result": "error"})
                        # Tuples should not be recorded on error
                        mock_tuples.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testrecordrolemapping")
class TestRecordRoleMapping:
    """Test record_role_mapping helper function"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_record_role_mapping(self):
        """Test recording role mapping operation"""
        with patch.object(metrics.auth_role_mapping_operations, "add") as mock_operations:
            with patch.object(metrics.auth_role_mapping_rules_applied, "record") as mock_rules:
                with patch.object(metrics.auth_role_mapping_tuples_generated, "record") as mock_tuples:
                    with patch.object(metrics.auth_role_mapping_duration, "record") as mock_duration:
                        metrics.record_role_mapping("user_roles", 5, 12, 75.3)

                        mock_operations.assert_called_once_with(1, {"type": "user_roles"})
                        mock_rules.assert_called_once_with(5)
                        mock_tuples.assert_called_once_with(12)
                        mock_duration.assert_called_once_with(75.3)

    def test_record_role_mapping_with_zero_rules(self):
        """Test recording role mapping with no rules applied"""
        with patch.object(metrics.auth_role_mapping_operations, "add") as mock_operations:
            with patch.object(metrics.auth_role_mapping_rules_applied, "record") as mock_rules:
                with patch.object(metrics.auth_role_mapping_tuples_generated, "record") as mock_tuples:
                    with patch.object(metrics.auth_role_mapping_duration, "record") as mock_duration:
                        metrics.record_role_mapping("group_mapping", 0, 0, 10.5)

                        mock_operations.assert_called_once()
                        mock_rules.assert_called_once_with(0)
                        mock_tuples.assert_called_once_with(0)
                        mock_duration.assert_called_once_with(10.5)


@pytest.mark.unit
@pytest.mark.xdist_group(name="testmetricattributes")
class TestMetricAttributes:
    """Test that metrics can be called with proper attributes"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_login_metrics_accept_attributes(self):
        """Test that login metrics accept proper attributes"""
        with patch.object(metrics.auth_login_attempts, "add") as mock_add:
            # Should not raise exception
            metrics.auth_login_attempts.add(1, {"provider": "test", "result": "success"})
            mock_add.assert_called_once()

    def test_session_active_counter_up_down(self):
        """Test that sessions_active counter can increment and decrement"""
        with patch.object(metrics.auth_sessions_active, "add") as mock_add:
            # Increment
            metrics.auth_sessions_active.add(1, {"backend": "redis"})
            # Decrement
            metrics.auth_sessions_active.add(-1, {"backend": "redis"})

            assert mock_add.call_count == 2
