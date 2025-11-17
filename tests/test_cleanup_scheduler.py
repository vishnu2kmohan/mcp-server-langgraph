"""
Tests for data cleanup scheduler

Covers scheduled background jobs for data retention policy enforcement.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.auth.session import InMemorySessionStore
from mcp_server_langgraph.compliance.retention import RetentionResult
from mcp_server_langgraph.schedulers.cleanup import (
    CleanupScheduler,
    get_cleanup_scheduler,
    start_cleanup_scheduler,
    stop_cleanup_scheduler,
)


@pytest.fixture
def mock_session_store():
    """Create mock session store"""
    return InMemorySessionStore()


@pytest.fixture
def mock_retention_config():
    """Create mock retention configuration"""
    return {
        "global": {
            "cleanup_schedule": "0 3 * * *",  # Daily at 3 AM
            "default_retention_days": 90,
        },
        "notifications": {
            "enabled": True,
        },
    }


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestCleanupSchedulerInit:
    """Test CleanupScheduler initialization"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_initialization_default(self):
        """Test default initialization"""
        scheduler = CleanupScheduler()

        assert scheduler.session_store is None
        assert scheduler.config_path == "config/retention_policies.yaml"
        assert scheduler.dry_run is False
        assert scheduler.scheduler is not None
        assert scheduler.retention_service is None

    def test_initialization_with_params(self, mock_session_store):
        """Test initialization with parameters"""
        scheduler = CleanupScheduler(
            session_store=mock_session_store,
            config_path="custom/config.yaml",
            dry_run=True,
        )

        assert scheduler.session_store == mock_session_store
        assert scheduler.config_path == "custom/config.yaml"
        assert scheduler.dry_run is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestCleanupSchedulerStart:
    """Test scheduler startup"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_start_creates_retention_service(self, mock_session_store, mock_retention_config):
        """Test that start creates retention service"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            await scheduler.start()

            # Verify retention service was created
            MockService.assert_called_once()
            assert scheduler.retention_service is not None

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_schedules_job(self, mock_session_store, mock_retention_config):
        """Test that start schedules cleanup job"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            await scheduler.start()

            # Verify job was scheduled
            job = scheduler.scheduler.get_job("data_retention_cleanup")
            assert job is not None
            assert job.name == "Data Retention Cleanup"

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_with_custom_schedule(self, mock_session_store):
        """Test scheduling with custom cron expression"""
        custom_config = {
            "global": {
                "cleanup_schedule": "0 2 * * 1",  # Every Monday at 2 AM
            },
            "notifications": {"enabled": False},
        }

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = custom_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            await scheduler.start()

            job = scheduler.scheduler.get_job("data_retention_cleanup")
            assert job is not None

            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_with_invalid_schedule(self, mock_session_store):
        """Test handling of invalid cron expression"""
        invalid_config = {
            "global": {
                "cleanup_schedule": "invalid schedule",
            },
            "notifications": {"enabled": False},
        }

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = invalid_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)

            with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
                await scheduler.start()

                # Should log error but not crash
                mock_logger.error.assert_called()

            await scheduler.stop()


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestCleanupSchedulerStop:
    """Test scheduler shutdown"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self, mock_session_store, mock_retention_config):
        """Test that stop shuts down scheduler"""
        import asyncio

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            await scheduler.start()

            # Verify scheduler is running
            assert scheduler.scheduler.running is True

            await scheduler.stop()

            # Give scheduler a moment to fully shutdown
            await asyncio.sleep(0.01)

            # Verify scheduler is stopped
            assert scheduler.scheduler.running is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestCleanupExecution:
    """Test cleanup execution"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_cleanup_success(self, mock_session_store, mock_retention_config):
        """Test successful cleanup execution"""
        # Create mock results
        mock_results = [
            RetentionResult(
                policy_name="sessions",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=10,
                archived_count=5,
                errors=[],
            ),
            RetentionResult(
                policy_name="logs",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=20,
                archived_count=0,
                errors=[],
            ),
        ]

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            mock_service.run_all_cleanups.return_value = mock_results
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            scheduler.retention_service = mock_service

            # Run cleanup
            await scheduler._run_cleanup()

            # Verify cleanup was executed
            mock_service.run_all_cleanups.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cleanup_with_errors(self, mock_session_store, mock_retention_config):
        """Test cleanup execution with errors"""
        mock_results = [
            RetentionResult(
                policy_name="sessions",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=5,
                archived_count=0,
                errors=["Error deleting session X", "Error deleting session Y"],
            ),
        ]

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            mock_service.run_all_cleanups.return_value = mock_results
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            scheduler.retention_service = mock_service

            with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
                await scheduler._run_cleanup()

                # Should log as error when there are errors
                assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_run_cleanup_without_service(self):
        """Test cleanup execution when service not initialized"""
        scheduler = CleanupScheduler()

        with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
            await scheduler._run_cleanup()

            # Should log error and return early
            mock_logger.error.assert_called_with("Retention service not initialized")

    @pytest.mark.asyncio
    async def test_run_cleanup_exception_handling(self, mock_session_store, mock_retention_config):
        """Test that exceptions in cleanup are caught"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            mock_service.run_all_cleanups.side_effect = Exception("Database error")
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            scheduler.retention_service = mock_service

            with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
                # Should not raise exception
                await scheduler._run_cleanup()

                # Should log error
                mock_logger.error.assert_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestNotifications:
    """Test cleanup notifications"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_cleanup_notification(self, mock_session_store, mock_retention_config):
        """Test sending cleanup notification"""
        mock_results = [
            RetentionResult(
                policy_name="test",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=10,
                archived_count=5,
                errors=[],
            ),
        ]

        scheduler = CleanupScheduler(session_store=mock_session_store)

        with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
            await scheduler._send_cleanup_notification(mock_results)

            # Should log notification
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_notifications_disabled(self, mock_session_store):
        """Test that notifications can be disabled"""
        config_no_notifications = {
            "global": {"cleanup_schedule": "0 3 * * *"},
            "notifications": {"enabled": False},
        }

        mock_results = [
            RetentionResult(
                policy_name="test",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=10,
                archived_count=0,
                errors=[],
            ),
        ]

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = config_no_notifications
            mock_service.run_all_cleanups.return_value = mock_results
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            scheduler.retention_service = mock_service

            with patch.object(scheduler, "_send_cleanup_notification", new_callable=AsyncMock) as mock_notify:
                await scheduler._run_cleanup()

                # Notification should not be sent
                mock_notify.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestManualExecution:
    """Test manual cleanup triggering"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_now(self, mock_session_store, mock_retention_config):
        """Test manual cleanup trigger"""
        mock_results = [
            RetentionResult(
                policy_name="manual",
                execution_timestamp="2025-10-14T00:00:00Z",
                deleted_count=5,
                archived_count=0,
                errors=[],
            ),
        ]

        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            mock_service.run_all_cleanups.return_value = mock_results
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            scheduler.retention_service = mock_service

            with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
                await scheduler.run_now()

                # Should log manual trigger
                mock_logger.info.assert_any_call("Manual cleanup triggered")


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestHelperFunctions:
    """Test helper functions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_next_run_time(self, mock_session_store, mock_retention_config):
        """Test getting next scheduled run time"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store)
            await scheduler.start()

            # Get next run time
            next_run = scheduler._get_next_run_time()

            # Should return ISO formatted time or "Not scheduled"
            assert isinstance(next_run, str)
            assert next_run != "Not scheduled"

            await scheduler.stop()

    def test_get_next_run_time_not_scheduled(self):
        """Test getting next run time when not scheduled"""
        scheduler = CleanupScheduler()

        next_run = scheduler._get_next_run_time()

        assert next_run == "Not scheduled"


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestGlobalScheduler:
    """Test global scheduler functions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_start_cleanup_scheduler(self, mock_session_store, mock_retention_config):
        """Test starting global cleanup scheduler"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            # Reset global state
            import mcp_server_langgraph.schedulers.cleanup as cleanup_module

            cleanup_module._cleanup_scheduler = None

            await start_cleanup_scheduler(session_store=mock_session_store, dry_run=True)

            # Verify global scheduler was created
            assert get_cleanup_scheduler() is not None
            assert get_cleanup_scheduler().dry_run is True

            await stop_cleanup_scheduler()

    @pytest.mark.asyncio
    async def test_start_cleanup_scheduler_already_running(self, mock_session_store, mock_retention_config):
        """Test starting scheduler when already running"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            # Start once
            await start_cleanup_scheduler(session_store=mock_session_store)

            with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
                # Try to start again
                await start_cleanup_scheduler(session_store=mock_session_store)

                # Should log warning
                mock_logger.warning.assert_called_with("Cleanup scheduler already running")

            await stop_cleanup_scheduler()

    @pytest.mark.asyncio
    async def test_stop_cleanup_scheduler(self, mock_session_store, mock_retention_config):
        """Test stopping global cleanup scheduler"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            await start_cleanup_scheduler(session_store=mock_session_store)
            await stop_cleanup_scheduler()

            # Verify global scheduler was cleared
            assert get_cleanup_scheduler() is None

    @pytest.mark.asyncio
    async def test_stop_cleanup_scheduler_not_running(self):
        """Test stopping scheduler when not running"""
        # Reset global state
        import mcp_server_langgraph.schedulers.cleanup as cleanup_module

        cleanup_module._cleanup_scheduler = None

        with patch("mcp_server_langgraph.schedulers.cleanup.logger") as mock_logger:
            await stop_cleanup_scheduler()

            # Should log warning
            mock_logger.warning.assert_called_with("Cleanup scheduler not running")

    def test_get_cleanup_scheduler_none(self):
        """Test getting scheduler when none exists"""
        # Reset global state
        import mcp_server_langgraph.schedulers.cleanup as cleanup_module

        cleanup_module._cleanup_scheduler = None

        scheduler = get_cleanup_scheduler()

        assert scheduler is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="cleanup_scheduler_tests")
class TestDryRunMode:
    """Test dry-run mode"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, mock_session_store, mock_retention_config):
        """Test that dry-run mode is passed through"""
        with patch("mcp_server_langgraph.schedulers.cleanup.DataRetentionService") as MockService:
            mock_service = AsyncMock()
            mock_service.config = mock_retention_config
            MockService.return_value = mock_service

            scheduler = CleanupScheduler(session_store=mock_session_store, dry_run=True)

            assert scheduler.dry_run is True

            # Verify dry_run is passed to retention service
            await scheduler.start()

            MockService.assert_called_with(
                config_path="config/retention_policies.yaml",
                session_store=mock_session_store,
                dry_run=True,
            )

            await scheduler.stop()
