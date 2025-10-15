"""
Tests for Data Retention Service (GDPR Article 5(1)(e) Storage Limitation)

Covers automated data retention policies and cleanup schedules.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml

from mcp_server_langgraph.auth.session import InMemorySessionStore
from mcp_server_langgraph.core.compliance.retention import DataRetentionService, RetentionPolicy, RetentionResult


@pytest.fixture
def mock_session_store():
    """Create mock session store"""
    return InMemorySessionStore()


@pytest.fixture
def sample_config():
    """Sample retention configuration"""
    return {
        "global": {
            "enabled": True,
            "dry_run": False,
            "cleanup_schedule": "0 3 * * *",
        },
        "retention_periods": {
            "user_sessions": {"inactive": 90},
            "conversations": {"archived": 180},
            "audit_logs": {"standard": 2555},
        },
        "notifications": {
            "enabled": True,
        },
    }


@pytest.mark.unit
class TestRetentionPolicy:
    """Test RetentionPolicy model"""

    def test_retention_policy_creation(self):
        """Test creating retention policy"""
        policy = RetentionPolicy(
            data_type="sessions",
            retention_days=90,
            enabled=True,
            soft_delete=False,
        )

        assert policy.data_type == "sessions"
        assert policy.retention_days == 90
        assert policy.enabled is True
        assert policy.soft_delete is False

    def test_retention_policy_defaults(self):
        """Test retention policy default values"""
        policy = RetentionPolicy(data_type="logs", retention_days=365)

        assert policy.enabled is True
        assert policy.soft_delete is False
        assert policy.notify_before is False


@pytest.mark.unit
class TestRetentionResult:
    """Test RetentionResult model"""

    def test_retention_result_creation(self):
        """Test creating retention result"""
        result = RetentionResult(
            policy_name="sessions",
            execution_timestamp="2025-10-13T12:00:00Z",
            deleted_count=10,
            archived_count=5,
            errors=["Error 1"],
            dry_run=False,
        )

        assert result.policy_name == "sessions"
        assert result.deleted_count == 10
        assert result.archived_count == 5
        assert len(result.errors) == 1
        assert result.dry_run is False

    def test_retention_result_defaults(self):
        """Test retention result default values"""
        result = RetentionResult(policy_name="test", execution_timestamp="2025-10-13T12:00:00Z")

        assert result.deleted_count == 0
        assert result.archived_count == 0
        assert result.errors == []
        assert result.dry_run is False


@pytest.mark.unit
class TestDataRetentionServiceInit:
    """Test DataRetentionService initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        service = DataRetentionService()

        assert service.config_path == Path("config/retention_policies.yaml")
        assert service.session_store is None
        assert service.dry_run is False
        assert service.config is not None

    def test_init_with_params(self, mock_session_store):
        """Test initialization with custom parameters"""
        service = DataRetentionService(
            config_path="custom/config.yaml",
            session_store=mock_session_store,
            dry_run=True,
        )

        assert service.config_path == Path("custom/config.yaml")
        assert service.session_store == mock_session_store
        assert service.dry_run is True

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            service = DataRetentionService(config_path="nonexistent.yaml")

            # Should use default config
            assert "global" in service.config
            assert "retention_periods" in service.config

    def test_load_config_success(self, sample_config):
        """Test successful config loading"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                assert service.config == sample_config

    def test_load_config_error(self):
        """Test config loading error handling"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Read error")):
                service = DataRetentionService(config_path="error.yaml")

                # Should fall back to default config
                assert "global" in service.config

    def test_default_config(self):
        """Test default configuration"""
        service = DataRetentionService()
        config = service._default_config()

        assert config["global"]["enabled"] is True
        assert "user_sessions" in config["retention_periods"]
        assert "conversations" in config["retention_periods"]
        assert "audit_logs" in config["retention_periods"]


@pytest.mark.unit
class TestSessionCleanup:
    """Test session cleanup functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_sessions_no_session_store(self):
        """Test cleanup when session store is not available"""
        service = DataRetentionService(session_store=None)

        result = await service.cleanup_sessions()

        assert result.policy_name == "user_sessions"
        assert result.deleted_count == 0
        assert len(result.errors) == 1
        assert "Session store not configured" in result.errors[0]

    @pytest.mark.asyncio
    async def test_cleanup_sessions_success(self, mock_session_store, sample_config):
        """Test successful session cleanup"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                # Mock the cleanup method
                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    result = await service.cleanup_sessions()

                    assert result.policy_name == "user_sessions"
                    assert result.deleted_count == 5
                    assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_cleanup_sessions_dry_run(self, mock_session_store, sample_config):
        """Test session cleanup in dry-run mode"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(
                    session_store=mock_session_store,
                    config_path="test.yaml",
                    dry_run=True,
                )

                with patch.object(service, "_cleanup_inactive_sessions", return_value=3):
                    result = await service.cleanup_sessions()

                    assert result.dry_run is True
                    assert result.deleted_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_sessions_error_handling(self, mock_session_store, sample_config):
        """Test error handling during session cleanup"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                # Mock cleanup to raise exception
                with patch.object(
                    service,
                    "_cleanup_inactive_sessions",
                    side_effect=Exception("Database error"),
                ):
                    result = await service.cleanup_sessions()

                    assert result.deleted_count == 0
                    assert len(result.errors) == 1
                    assert "Database error" in result.errors[0]


@pytest.mark.unit
class TestConversationCleanup:
    """Test conversation cleanup functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_conversations(self, sample_config):
        """Test conversation cleanup"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                # Mock the cleanup method
                with patch.object(service, "_cleanup_old_conversations", return_value=10):
                    result = await service.cleanup_conversations()

                    assert result.policy_name == "conversations"
                    assert result.deleted_count == 10

    @pytest.mark.asyncio
    async def test_cleanup_conversations_error(self, sample_config):
        """Test conversation cleanup error handling"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                with patch.object(
                    service,
                    "_cleanup_old_conversations",
                    side_effect=Exception("Cleanup failed"),
                ):
                    result = await service.cleanup_conversations()

                    assert len(result.errors) > 0


@pytest.mark.unit
class TestAuditLogCleanup:
    """Test audit log cleanup functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_audit_logs(self, sample_config):
        """Test audit log cleanup"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                with patch.object(service, "_cleanup_old_audit_logs", return_value=100):
                    result = await service.cleanup_audit_logs()

                    assert result.policy_name == "audit_logs"
                    assert result.archived_count == 100  # Audit logs are archived, not deleted

    @pytest.mark.asyncio
    async def test_cleanup_audit_logs_long_retention(self, sample_config):
        """Test audit logs have longer retention period"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                # Verify audit logs have 7 year retention (2555 days)
                retention_days = service.config["retention_periods"]["audit_logs"]["standard"]
                assert retention_days == 2555  # ~7 years for compliance


@pytest.mark.unit
class TestRunAllCleanups:
    """Test running all cleanup policies"""

    @pytest.mark.asyncio
    async def test_run_all_cleanups(self, mock_session_store, sample_config):
        """Test running all cleanup policies together"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                # Mock all cleanup methods
                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    with patch.object(service, "_cleanup_old_conversations", return_value=10):
                        with patch.object(service, "_cleanup_old_audit_logs", return_value=20):
                            results = await service.run_all_cleanups()

                            # Should return results for all policies
                            assert len(results) >= 1
                            assert isinstance(results[0], RetentionResult)

    @pytest.mark.asyncio
    async def test_run_all_cleanups_dry_run(self, mock_session_store, sample_config):
        """Test running all cleanups in dry-run mode"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(
                    session_store=mock_session_store,
                    config_path="test.yaml",
                    dry_run=True,
                )

                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    with patch.object(service, "_cleanup_old_conversations", return_value=10):
                        results = await service.run_all_cleanups()

                        # All results should be marked as dry_run
                        for result in results:
                            assert result.dry_run is True


@pytest.mark.unit
class TestRetentionMetrics:
    """Test retention metrics tracking"""

    @pytest.mark.asyncio
    async def test_metrics_tracked_on_cleanup(self, mock_session_store, sample_config):
        """Test that metrics are tracked during cleanup"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    with patch("mcp_server_langgraph.core.compliance.retention.metrics") as mock_metrics:
                        await service.cleanup_sessions()

                        # Verify metrics were recorded
                        mock_metrics.successful_calls.add.assert_called()

    @pytest.mark.asyncio
    async def test_no_metrics_in_dry_run(self, mock_session_store, sample_config):
        """Test that metrics are not tracked in dry-run mode"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(
                    session_store=mock_session_store,
                    config_path="test.yaml",
                    dry_run=True,
                )

                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    with patch("mcp_server_langgraph.core.compliance.retention.metrics") as mock_metrics:
                        await service.cleanup_sessions()

                        # Metrics should not be recorded in dry-run
                        mock_metrics.successful_calls.add.assert_not_called()


@pytest.mark.unit
class TestRetentionLogging:
    """Test retention logging and audit trail"""

    @pytest.mark.asyncio
    async def test_cleanup_logged(self, mock_session_store, sample_config):
        """Test that cleanups are logged"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                with patch.object(service, "_cleanup_inactive_sessions", return_value=5):
                    with patch("mcp_server_langgraph.core.compliance.retention.logger") as mock_logger:
                        await service.cleanup_sessions()

                        # Verify logging occurred
                        assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_errors_logged(self, mock_session_store, sample_config):
        """Test that errors are logged"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(session_store=mock_session_store, config_path="test.yaml")

                with patch.object(
                    service,
                    "_cleanup_inactive_sessions",
                    side_effect=Exception("Test error"),
                ):
                    with patch("mcp_server_langgraph.core.compliance.retention.logger") as mock_logger:
                        await service.cleanup_sessions()

                        # Verify error was logged
                        mock_logger.error.assert_called()


@pytest.mark.unit
class TestRetentionCompliance:
    """Test GDPR and SOC 2 compliance aspects"""

    def test_gdpr_storage_limitation(self, sample_config):
        """Test compliance with GDPR Article 5(1)(e) storage limitation"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                # Verify retention periods are defined
                assert "user_sessions" in service.config["retention_periods"]
                assert "conversations" in service.config["retention_periods"]

    def test_audit_trail_retention(self, sample_config):
        """Test audit logs have longer retention for compliance"""
        config_yaml = yaml.dump(sample_config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=config_yaml)):
                service = DataRetentionService(config_path="test.yaml")

                # Audit logs should have significantly longer retention
                audit_retention = service.config["retention_periods"]["audit_logs"]["standard"]
                session_retention = service.config["retention_periods"]["user_sessions"]["inactive"]

                assert audit_retention > session_retention
