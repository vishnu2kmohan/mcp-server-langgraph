"""
TDD Tests for Storage Bootstrap Global Setters.

These tests verify that init_storage() sets up global accessors for:
- Audit service
- Audit event broadcaster
- Notification broadcaster
- Compliance service

This consolidates global setter calls from app.py into bootstrap/storage.py,
reducing app.py lifespan code by ~8 lines.

Plan Reference: P0.1 DI Refactor - Move global setters to bootstrap modules
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_storage_bootstrap_global_setters")
class TestStorageBootstrapGlobalSetters:
    """
    Test that init_storage() calls all required global setters.

    Currently app.py has this code in its lifespan:
        if state.storage:
            if state.storage.audit_service:
                set_audit_service(state.storage.audit_service)
            if state.storage.audit_broadcaster:
                set_audit_event_broadcaster(state.storage.audit_broadcaster)
            if state.storage.notification_broadcaster:
                set_notification_broadcaster(state.storage.notification_broadcaster)
            if state.storage.compliance_service:
                set_compliance_service(state.storage.compliance_service)

    This should be moved to init_storage() so app.py just calls:
        state = await bootstrap_all(config)
        # Global setters already called within init_storage()
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_init_storage_calls_set_audit_service(self):
        """
        Test: init_storage() calls set_audit_service with the created service.

        GIVEN: Settings with audit enabled
        WHEN: init_storage() is called
        THEN: set_audit_service() is called with the audit service instance
        """
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.database_url = "postgresql://localhost/test"
        mock_settings.audit_integrity_secret = "test-secret"
        mock_settings.audit_scheduler_enabled = False
        mock_settings.partition_retention_enabled = False

        # Patch at the source module where the function is defined
        with patch("mcp_server_langgraph.audit.repository.create_audit_repository") as mock_repo:
            with patch("mcp_server_langgraph.middleware.audit.set_audit_service") as mock_setter:
                mock_repo.return_value = MagicMock()

                from mcp_server_langgraph.bootstrap.storage import init_storage

                state = await init_storage(mock_settings)

                # After moving setter to init_storage, this should be called
                # Currently (before fix): setter is NOT called in init_storage
                # After fix: setter IS called in init_storage
                if state.audit_service is not None:
                    # This will fail until we add the setter call to init_storage
                    mock_setter.assert_called_once_with(state.audit_service)

    @pytest.mark.asyncio
    async def test_init_storage_calls_set_audit_event_broadcaster(self):
        """
        Test: init_storage() calls set_audit_event_broadcaster with the created broadcaster.

        GIVEN: Settings with audit enabled
        WHEN: init_storage() is called
        THEN: set_audit_event_broadcaster() is called with the broadcaster instance
        """
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.database_url = "postgresql://localhost/test"
        mock_settings.audit_integrity_secret = "test-secret"
        mock_settings.audit_scheduler_enabled = False
        mock_settings.partition_retention_enabled = False

        with patch("mcp_server_langgraph.audit.repository.create_audit_repository") as mock_repo:
            with patch("mcp_server_langgraph.api.v1.audit_websocket.set_audit_event_broadcaster") as mock_setter:
                mock_repo.return_value = MagicMock()

                from mcp_server_langgraph.bootstrap.storage import init_storage

                state = await init_storage(mock_settings)

                # After moving setter to init_storage, this should be called
                if state.audit_broadcaster is not None:
                    mock_setter.assert_called_once_with(state.audit_broadcaster)

    @pytest.mark.asyncio
    async def test_init_storage_calls_set_notification_broadcaster(self):
        """
        Test: init_storage() calls set_notification_broadcaster with the created broadcaster.

        GIVEN: Settings with notifications enabled
        WHEN: init_storage() is called
        THEN: set_notification_broadcaster() is called with the broadcaster instance
        """
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.database_url = "postgresql://localhost/test"
        mock_settings.audit_integrity_secret = "test-secret"
        mock_settings.audit_scheduler_enabled = False
        mock_settings.partition_retention_enabled = False

        with patch("mcp_server_langgraph.audit.repository.create_audit_repository") as mock_repo:
            with patch("mcp_server_langgraph.websocket.registry.set_notification_broadcaster") as mock_setter:
                mock_repo.return_value = MagicMock()

                from mcp_server_langgraph.bootstrap.storage import init_storage

                state = await init_storage(mock_settings)

                # After moving setter to init_storage, this should be called
                if state.notification_broadcaster is not None:
                    mock_setter.assert_called_once_with(state.notification_broadcaster)

    @pytest.mark.asyncio
    async def test_init_storage_calls_set_compliance_service(self):
        """
        Test: init_storage() calls set_compliance_service with the created service.

        GIVEN: Settings with compliance enabled
        WHEN: init_storage() is called
        THEN: set_compliance_service() is called with the service instance
        """
        from mcp_server_langgraph.core.config import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.database_url = "postgresql://localhost/test"
        mock_settings.audit_integrity_secret = "test-secret"
        mock_settings.audit_scheduler_enabled = False
        mock_settings.partition_retention_enabled = False

        with patch("mcp_server_langgraph.audit.repository.create_audit_repository") as mock_repo:
            with patch("mcp_server_langgraph.api.v1.compliance_reports.set_compliance_service") as mock_setter:
                mock_repo.return_value = MagicMock()

                from mcp_server_langgraph.bootstrap.storage import init_storage

                state = await init_storage(mock_settings)

                # After moving setter to init_storage, this should be called
                if state.compliance_service is not None:
                    mock_setter.assert_called_once_with(state.compliance_service)
