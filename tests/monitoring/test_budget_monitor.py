"""
Tests for Budget Monitor

Comprehensive test suite for budget monitoring and alerting following TDD principles.

Tests cover:
- Budget creation and retrieval
- Budget period calculations (daily, weekly, monthly, quarterly, yearly)
- Alert threshold detection (75%, 90%, custom)
- Email alert delivery via SMTP
- Webhook alert delivery via HTTP POST
- Budget status and utilization tracking
- Budget reset functionality
- Alert history and filtering
- Edge cases and error handling
"""

import gc
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from mcp_server_langgraph.monitoring.budget_monitor import AlertLevel, BudgetMonitor, BudgetPeriod

pytestmark = pytest.mark.unit

# ==============================================================================
# Test Fixtures
# ==============================================================================


def _create_mock_cost_collector() -> MagicMock:
    """Create a mock cost collector for testing BudgetMonitor without database."""
    mock = MagicMock()  # noqa: async-mock-config (methods configured below)
    mock.get_cost_summary = AsyncMock(return_value={"total_cost_usd": Decimal("0.00")})
    return mock


@pytest.fixture
def mock_cost_collector() -> MagicMock:
    """Fixture providing a mock cost collector for tests."""
    return _create_mock_cost_collector()


@pytest.fixture
def budget_monitor(mock_cost_collector):
    """Create a fresh BudgetMonitor instance for testing with mocked storage."""
    return BudgetMonitor(cost_collector=mock_cost_collector)


@pytest.fixture
def sample_budget_data():
    """Sample budget data for testing."""
    return {
        "id": "test_budget_001",
        "name": "Test Monthly Budget",
        "limit_usd": Decimal("1000.00"),
        "period": BudgetPeriod.MONTHLY,
        "start_date": datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        "alert_thresholds": [Decimal("0.75"), Decimal("0.90")],
    }


# ==============================================================================
# Test Budget Creation and Retrieval
# ==============================================================================


@pytest.mark.xdist_group(name="budget_monitor_tests")
class TestBudgetCreation:
    """Test suite for budget creation and retrieval."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_stores_budget(self, budget_monitor, sample_budget_data):
        """Test create_budget() stores budget in memory."""
        # Act
        budget = await budget_monitor.create_budget(**sample_budget_data)

        # Assert
        assert budget.id == sample_budget_data["id"]
        assert budget.name == sample_budget_data["name"]
        assert budget.limit_usd == sample_budget_data["limit_usd"]
        assert budget.period == sample_budget_data["period"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_retrieves_created_budget(self, budget_monitor, sample_budget_data):
        """Test get_budget() retrieves previously created budget."""
        # Arrange
        await budget_monitor.create_budget(**sample_budget_data)

        # Act
        budget = await budget_monitor.get_budget(sample_budget_data["id"])

        # Assert
        assert budget is not None
        assert budget.id == sample_budget_data["id"]
        assert budget.name == sample_budget_data["name"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_returns_none_for_nonexistent_budget(self, budget_monitor):
        """Test get_budget() returns None for non-existent budget."""
        # Act
        budget = await budget_monitor.get_budget("nonexistent_budget")

        # Assert
        assert budget is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_uses_default_start_date_if_not_provided(self, budget_monitor):
        """Test create_budget() uses current time as default start_date."""
        # Arrange
        before = datetime.now(UTC)

        # Act
        budget = await budget_monitor.create_budget(
            id="budget_002",
            name="Test Budget",
            limit_usd=Decimal("500.00"),
            period=BudgetPeriod.WEEKLY,
            start_date=None,  # Not provided
        )

        # Assert
        after = datetime.now(UTC)
        assert before <= budget.start_date <= after

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_uses_default_alert_thresholds(self, budget_monitor):
        """Test create_budget() uses [0.75, 0.90] as default alert thresholds."""
        # Act
        budget = await budget_monitor.create_budget(
            id="budget_003",
            name="Test Budget",
            limit_usd=Decimal("500.00"),
            period=BudgetPeriod.MONTHLY,
            alert_thresholds=None,  # Not provided
        )

        # Assert
        assert budget.alert_thresholds == [Decimal("0.75"), Decimal("0.90")]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_all_budgets_returns_all_created_budgets(self, budget_monitor):
        """Test get_all_budgets() returns list of all budgets."""
        # Arrange
        await budget_monitor.create_budget(
            id="budget_001", name="Budget 1", limit_usd=Decimal("100.00"), period=BudgetPeriod.DAILY
        )
        await budget_monitor.create_budget(
            id="budget_002", name="Budget 2", limit_usd=Decimal("200.00"), period=BudgetPeriod.WEEKLY
        )

        # Act
        budgets = await budget_monitor.get_all_budgets()

        # Assert
        assert len(budgets) == 2
        assert any(b.id == "budget_001" for b in budgets)
        assert any(b.id == "budget_002" for b in budgets)


# ==============================================================================
# Test Period Boundary Calculations
# ==============================================================================


@pytest.mark.xdist_group(name="budget_period_tests")
class TestBudgetPeriodCalculations:
    """Test suite for budget period boundary calculations."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_daily_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for DAILY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.DAILY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=UTC)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 11, 15, 0, 0, 0, tzinfo=UTC)
        assert period_end == datetime(2025, 11, 16, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_weekly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for WEEKLY period (Monday-Sunday)."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.WEEKLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        # Friday, November 15, 2025
        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=UTC)  # Friday

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert - Week starts Monday
        # November 10 (Monday) to November 17 (Monday)
        assert period_start.weekday() == 0  # Monday
        assert period_end == period_start + timedelta(weeks=1)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_monthly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for MONTHLY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.MONTHLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=UTC)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC)
        assert period_end == datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_monthly_budget_in_december(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() handles December → January transition."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.MONTHLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 12, 15, 14, 30, 0, tzinfo=UTC)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
        assert period_end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_quarterly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for QUARTERLY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.QUARTERLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        # Q4: October, November, December
        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=UTC)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 10, 1, 0, 0, 0, tzinfo=UTC)
        assert period_end == period_start + timedelta(days=90)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_yearly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for YEARLY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.YEARLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=UTC)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert period_end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


# ==============================================================================
# Test Alert Triggering
# ==============================================================================


@pytest.mark.xdist_group(name="budget_alert_tests")
class TestBudgetAlerts:
    """Test suite for budget alert triggering."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_triggers_alert_at_75_percent(self, budget_monitor, sample_budget_data):
        """Test check_budget() triggers WARNING alert at 75% utilization."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
            with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock) as mock_send_alert:
                # Act
                alert = await budget_monitor.check_budget(budget.id)

                # Assert
                assert alert is not None
                assert alert.level == AlertLevel.WARNING
                assert alert.utilization == Decimal("0.75")
                mock_send_alert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_triggers_alert_at_90_percent(self, budget_monitor, sample_budget_data):
        """Test check_budget() triggers CRITICAL alert at 90% utilization."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("900.00")):
            with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock) as mock_send_alert:
                # Act
                alert = await budget_monitor.check_budget(budget.id)

                # Assert
                assert alert is not None
                assert alert.level == AlertLevel.CRITICAL
                assert alert.utilization == Decimal("0.90")
                mock_send_alert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_no_alert_below_threshold(self, budget_monitor, sample_budget_data):
        """Test check_budget() does not trigger alert below 75%."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("500.00")):
            with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock) as mock_send_alert:
                # Act
                alert = await budget_monitor.check_budget(budget.id)

                # Assert
                assert alert is None
                mock_send_alert.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_only_alerts_once_per_threshold(self, budget_monitor, sample_budget_data):
        """Test check_budget() only alerts once per threshold (no duplicate alerts)."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
            with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock) as mock_send_alert:
                # Act - Check budget twice
                alert1 = await budget_monitor.check_budget(budget.id)
                alert2 = await budget_monitor.check_budget(budget.id)

                # Assert - Only one alert
                assert alert1 is not None
                assert alert2 is None
                assert mock_send_alert.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_returns_none_when_budget_disabled(self, budget_monitor, sample_budget_data):
        """Test check_budget() returns None when budget is disabled."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)
        budget.enabled = False

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("900.00")):
            # Act
            alert = await budget_monitor.check_budget(budget.id)

            # Assert
            assert alert is None


# ==============================================================================
# Test Email Alerts
# ==============================================================================


@pytest.mark.xdist_group(name="budget_email_tests")
class TestEmailAlerts:
    """Test suite for email alert delivery."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_email_alert_sends_smtp_message(self):
        """Test _send_email_alert() sends email via SMTP."""
        # Arrange
        monitor = BudgetMonitor(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            email_from="alerts@example.com",
            email_to=["recipient@example.com"],
            cost_collector=_create_mock_cost_collector(),
        )

        with patch.object(monitor, "_send_smtp", new=MagicMock()) as mock_send_smtp:
            # Act
            await monitor._send_email_alert(
                level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0
            )

            # Assert
            mock_send_smtp.assert_called_once()
            msg = mock_send_smtp.call_args[0][0]
            assert isinstance(msg, MIMEMultipart)
            assert msg["From"] == "alerts@example.com"
            assert msg["To"] == "recipient@example.com"
            assert "[CRITICAL]" in msg["Subject"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_email_alert_skips_when_smtp_not_configured(self):
        """Test _send_email_alert() skips sending when SMTP not configured."""
        # Arrange
        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())  # No SMTP config

        with patch.object(monitor, "_send_smtp", new=MagicMock()) as mock_send_smtp:
            # Act
            await monitor._send_email_alert(level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0)

            # Assert
            mock_send_smtp.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_email_alert_includes_utilization_percentage(self):
        """Test _send_email_alert() includes utilization percentage in message."""
        # Arrange
        monitor = BudgetMonitor(
            smtp_host="smtp.example.com",
            email_from="alerts@example.com",
            email_to=["recipient@example.com"],
            cost_collector=_create_mock_cost_collector(),
        )

        with patch.object(monitor, "_send_smtp", new=MagicMock()) as mock_send_smtp:
            # Act
            await monitor._send_email_alert(level="warning", message="Budget alert", budget_id="budget_001", utilization=87.5)

            # Assert
            msg = mock_send_smtp.call_args[0][0]
            # Check HTML body contains utilization
            html_part = msg.get_payload()[1]  # HTML is second part
            assert "87.5%" in html_part.get_payload()


# ==============================================================================
# Test Webhook Alerts
# ==============================================================================


@pytest.mark.xdist_group(name="budget_webhook_tests")
class TestWebhookAlerts:
    """Test suite for webhook alert delivery."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_posts_to_webhook_url(self):
        """Test _send_webhook_alert() sends HTTP POST to webhook URL.

        Uses spec=httpx.Response for proper mock isolation under xdist.
        The response.raise_for_status() is synchronous in httpx, so we use MagicMock.

        XDIST FIX: Mock the entire httpx module's AsyncClient class, not just the
        return value. The async context manager must return the mock client instance
        that we control, not a separate MagicMock instance.
        """
        import httpx

        # Arrange
        monitor = BudgetMonitor(
            webhook_url="https://hooks.slack.com/services/ABC123",
            cost_collector=_create_mock_cost_collector(),
        )

        # Mock response - raise_for_status is sync in httpx
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()

        # Create a mock that will be returned from the context manager
        # The key is to make AsyncClient() return an object whose __aenter__
        # returns our controllable mock_client
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        # Create the mock for AsyncClient class itself
        mock_async_client_class = MagicMock()
        mock_async_client_instance = MagicMock()
        mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_client_class.return_value = mock_async_client_instance

        with patch("mcp_server_langgraph.monitoring.budget_monitor.httpx.AsyncClient", mock_async_client_class):
            # Act
            await monitor._send_webhook_alert(
                level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0
            )

            # Assert
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/services/ABC123"
            payload = call_args[1]["json"]
            assert payload["alert_type"] == "budget"
            assert payload["level"] == "critical"
            assert payload["budget_id"] == "budget_001"
            assert payload["utilization"] == 95.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_skips_when_webhook_not_configured(self):
        """Test _send_webhook_alert() skips sending when webhook URL not configured."""
        # Arrange
        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())  # No webhook URL

        # Create mock client with proper async context manager protocol
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.monitoring.budget_monitor.httpx.AsyncClient", return_value=mock_client) as mock_class:
            # Act
            await monitor._send_webhook_alert(
                level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0
            )

            # Assert - AsyncClient should not be instantiated when webhook not configured
            mock_class.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_includes_timestamp(self):
        """Test _send_webhook_alert() includes ISO 8601 timestamp in payload.

        Uses AsyncMock with proper context manager protocol for xdist isolation.
        """
        # Arrange
        monitor = BudgetMonitor(
            webhook_url="https://example.com/webhook",
            cost_collector=_create_mock_cost_collector(),
        )

        # Mock response - raise_for_status is sync in httpx
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        before = datetime.now(UTC)

        # Create mock client with proper async context manager protocol
        # The post method is async, so it must be AsyncMock
        mock_post = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.post = mock_post

        # AsyncClient is used as async context manager: async with httpx.AsyncClient() as client
        # The __aenter__ returns the client object, __aexit__ handles cleanup
        mock_async_client_class = MagicMock()
        mock_async_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.monitoring.budget_monitor.httpx.AsyncClient", mock_async_client_class):
            # Act
            await monitor._send_webhook_alert(
                level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0
            )

            # Assert
            after = datetime.now(UTC)
            mock_post.assert_called_once()
            payload = mock_post.call_args[1]["json"]
            timestamp_str = payload["timestamp"]
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            assert before <= timestamp <= after


# ==============================================================================
# Test Budget Status
# ==============================================================================


@pytest.mark.xdist_group(name="budget_status_tests")
class TestBudgetStatus:
    """Test suite for budget status tracking."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_status_calculates_utilization(self, budget_monitor, sample_budget_data):
        """Test get_budget_status() calculates budget utilization percentage."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
            # Act
            status = await budget_monitor.get_budget_status(budget.id)

            # Assert
            assert status is not None
            assert status.spent_usd == Decimal("750.00")
            assert status.remaining_usd == Decimal("250.00")
            assert status.utilization == Decimal("0.75")
            assert status.is_exceeded is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_status_detects_exceeded_budget(self, budget_monitor, sample_budget_data):
        """Test get_budget_status() detects when budget is exceeded."""
        # Arrange
        budget = await budget_monitor.create_budget(**sample_budget_data)

        with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("1200.00")):
            # Act
            status = await budget_monitor.get_budget_status(budget.id)

            # Assert
            assert status.is_exceeded is True
            assert status.spent_usd > status.limit_usd

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_status_returns_none_for_nonexistent_budget(self, budget_monitor):
        """Test get_budget_status() returns None for non-existent budget."""
        # Act
        status = await budget_monitor.get_budget_status("nonexistent_budget")

        # Assert
        assert status is None


# ==============================================================================
# Test Budget Reset
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_budget_clears_alerted_thresholds(budget_monitor, sample_budget_data):
    """Test reset_budget() clears alerted thresholds so alerts can trigger again."""
    # Arrange
    budget = await budget_monitor.create_budget(**sample_budget_data)

    with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
        with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock):
            # Trigger alert
            await budget_monitor.check_budget(budget.id)

            # Act - Reset budget
            await budget_monitor.reset_budget(budget.id)

            # Check budget again - should alert again
            alert = await budget_monitor.check_budget(budget.id)

            # Assert - Alert triggered again after reset
            assert alert is not None


# ==============================================================================
# Test Alert History
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_alerts_returns_all_alerts(budget_monitor, sample_budget_data):
    """Test get_alerts() returns all triggered alerts."""
    # Arrange
    budget = await budget_monitor.create_budget(**sample_budget_data)

    with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
        with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock):
            # Trigger alert
            await budget_monitor.check_budget(budget.id)

            # Act
            alerts = await budget_monitor.get_alerts()

            # Assert
            assert len(alerts) == 1
            assert alerts[0].budget_id == budget.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_alerts_filters_by_budget_id(budget_monitor):
    """Test get_alerts() filters by budget_id."""
    # Arrange - Create two budgets and trigger alerts
    await budget_monitor.create_budget(
        id="budget_001", name="Budget 1", limit_usd=Decimal("100.00"), period=BudgetPeriod.DAILY
    )
    await budget_monitor.create_budget(
        id="budget_002", name="Budget 2", limit_usd=Decimal("100.00"), period=BudgetPeriod.DAILY
    )

    with patch.object(budget_monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("75.00")):
        with patch.object(budget_monitor, "send_alert", new_callable=AsyncMock):
            await budget_monitor.check_budget("budget_001")
            await budget_monitor.check_budget("budget_002")

            # Act
            alerts = await budget_monitor.get_alerts(budget_id="budget_001")

            # Assert
            assert len(alerts) == 1
            assert alerts[0].budget_id == "budget_001"


# ==============================================================================
# Test Error Handling for SMTP and Webhook
# ==============================================================================


@pytest.mark.xdist_group(name="budget_error_handling_tests")
class TestBudgetAlertErrorHandling:
    """Test suite for error handling in SMTP and webhook alerts."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_alert_catches_smtp_exception(self):
        """
        GIVEN SMTP configuration with a failing SMTP server
        WHEN send_alert() is called
        THEN SMTP exception is caught and logged (not propagated)
        """
        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            smtp_host="smtp.failing.com",
            email_from="alerts@example.com",
            email_to=["recipient@example.com"],
            cost_collector=mock_cost_collector,
        )

        with (
            patch.object(
                monitor, "_send_email_alert", new_callable=AsyncMock, side_effect=Exception("SMTP connection refused")
            ),
            patch("mcp_server_langgraph.monitoring.budget_monitor.logger") as mock_logger,
        ):
            # Act - should NOT raise exception
            await monitor.send_alert(level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0)

            # Assert - exception was logged
            mock_logger.exception.assert_called_once()
            assert "Failed to send email alert" in str(mock_logger.exception.call_args)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_alert_catches_webhook_exception(self):
        """
        GIVEN webhook configuration with a failing webhook endpoint
        WHEN send_alert() is called
        THEN webhook exception is caught and logged (not propagated)
        """
        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            webhook_url="https://hooks.failing.com/webhook",
            cost_collector=mock_cost_collector,
        )

        with (
            patch.object(monitor, "_send_webhook_alert", new_callable=AsyncMock, side_effect=Exception("Connection timeout")),
            patch("mcp_server_langgraph.monitoring.budget_monitor.logger") as mock_logger,
        ):
            # Act - should NOT raise exception
            await monitor.send_alert(level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0)

            # Assert - exception was logged
            mock_logger.exception.assert_called_once()
            assert "Failed to send webhook alert" in str(mock_logger.exception.call_args)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_alert_logging_succeeds_when_smtp_and_webhook_fail(self):
        """
        GIVEN both SMTP and webhook configured but failing
        WHEN send_alert() is called
        THEN logging alert still succeeds (fallback)
        """
        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            smtp_host="smtp.failing.com",
            email_from="alerts@example.com",
            email_to=["recipient@example.com"],
            webhook_url="https://hooks.failing.com/webhook",
            cost_collector=mock_cost_collector,
        )

        with (
            patch.object(monitor, "_send_email_alert", new_callable=AsyncMock, side_effect=Exception("SMTP error")),
            patch.object(monitor, "_send_webhook_alert", new_callable=AsyncMock, side_effect=Exception("Webhook error")),
            patch("mcp_server_langgraph.monitoring.budget_monitor.logger") as mock_logger,
        ):
            # Act - should NOT raise exception
            await monitor.send_alert(level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0)

            # Assert - both errors were logged, general alert log succeeded
            assert mock_logger.exception.call_count == 2  # SMTP + webhook
            mock_logger.log.assert_called()  # Alert logged via logger.log()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_email_alert_handles_smtp_auth_error(self):
        """
        GIVEN SMTP with invalid credentials
        WHEN _send_email_alert() is called
        THEN authentication error is raised (caller handles it)
        """
        import smtplib

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            smtp_host="smtp.example.com",
            smtp_username="invalid_user",
            smtp_password="invalid_password",
            email_from="alerts@example.com",
            email_to=["recipient@example.com"],
            cost_collector=mock_cost_collector,
        )

        with patch.object(monitor, "_send_smtp", side_effect=smtplib.SMTPAuthenticationError(535, b"Authentication failed")):
            # Act & Assert - exception is raised (caught by send_alert)
            with pytest.raises(smtplib.SMTPAuthenticationError):
                await monitor._send_email_alert(
                    level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_handles_http_error(self):
        """
        GIVEN webhook endpoint returning HTTP 500
        WHEN _send_webhook_alert() is called
        THEN HTTP error is raised (caller handles it)
        """
        import httpx

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            webhook_url="https://hooks.example.com/webhook",
            cost_collector=mock_cost_collector,
        )

        # Mock HTTP 500 response
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response)
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_async_client_class = MagicMock()
        mock_async_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.monitoring.budget_monitor.httpx.AsyncClient", mock_async_client_class):
            # Act & Assert - exception is raised (caught by send_alert)
            with pytest.raises(httpx.HTTPStatusError):
                await monitor._send_webhook_alert(
                    level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_handles_connection_timeout(self):
        """
        GIVEN webhook endpoint with connection timeout
        WHEN _send_webhook_alert() is called
        THEN timeout error is raised (caller handles it)
        """
        import httpx

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(
            webhook_url="https://hooks.example.com/webhook",
            cost_collector=mock_cost_collector,
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timeout"))

        mock_async_client_class = MagicMock()
        mock_async_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("mcp_server_langgraph.monitoring.budget_monitor.httpx.AsyncClient", mock_async_client_class):
            # Act & Assert - exception is raised (caught by send_alert)
            with pytest.raises(httpx.ConnectTimeout):
                await monitor._send_webhook_alert(
                    level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0
                )


# ==============================================================================
# Test Singleton Pattern for get_budget_monitor()
# ==============================================================================


@pytest.mark.xdist_group(name="budget_singleton_tests")
class TestBudgetMonitorSingleton:
    """Test suite for get_budget_monitor() singleton pattern."""

    def teardown_method(self):
        """Reset singleton and force GC after each test."""
        from mcp_server_langgraph.monitoring.budget_monitor import _reset_budget_monitor

        _reset_budget_monitor()
        gc.collect()

    @pytest.mark.unit
    def test_get_budget_monitor_returns_same_instance(self):
        """
        GIVEN get_budget_monitor() is called multiple times
        WHEN comparing returned instances
        THEN they should be the same object (singleton)
        """
        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_storage:
            mock_storage.return_value = MagicMock()

            from mcp_server_langgraph.monitoring.budget_monitor import get_budget_monitor

            # Act
            instance1 = get_budget_monitor()
            instance2 = get_budget_monitor()

            # Assert - same object
            assert instance1 is instance2

    @pytest.mark.unit
    def test_get_budget_monitor_returns_budget_monitor_instance(self):
        """
        GIVEN get_budget_monitor() is called
        WHEN checking the return type
        THEN it should be a BudgetMonitor instance
        """
        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_storage:
            mock_storage.return_value = MagicMock()

            from mcp_server_langgraph.monitoring.budget_monitor import get_budget_monitor

            # Act
            instance = get_budget_monitor()

            # Assert
            assert isinstance(instance, BudgetMonitor)

    @pytest.mark.unit
    def test_reset_budget_monitor_clears_singleton(self):
        """
        GIVEN a singleton BudgetMonitor exists
        WHEN _reset_budget_monitor() is called
        THEN subsequent get_budget_monitor() creates a new instance
        """
        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_storage:
            mock_storage.return_value = MagicMock()

            from mcp_server_langgraph.monitoring.budget_monitor import (
                get_budget_monitor,
                _reset_budget_monitor,
            )

            # Arrange - create initial instance
            instance1 = get_budget_monitor()

            # Act - reset and get new instance
            _reset_budget_monitor()
            instance2 = get_budget_monitor()

            # Assert - different objects
            assert instance1 is not instance2

    @pytest.mark.unit
    def test_singleton_preserves_budgets(self):
        """
        GIVEN a budget is created via the singleton
        WHEN get_budget_monitor() is called again
        THEN the budget should still exist
        """
        import asyncio

        with patch("mcp_server_langgraph.monitoring.cost_storage_factory.get_cost_storage_backend") as mock_storage:
            mock_storage.return_value = MagicMock()

            from mcp_server_langgraph.monitoring.budget_monitor import get_budget_monitor

            # Arrange - create a budget
            monitor = get_budget_monitor()
            asyncio.run(
                monitor.create_budget(
                    id="test_singleton_budget",
                    name="Test Budget",
                    limit_usd=Decimal("500.00"),
                    period=BudgetPeriod.MONTHLY,
                )
            )

            # Act - get singleton again
            same_monitor = get_budget_monitor()

            # Assert - budget still exists
            budget = asyncio.run(same_monitor.get_budget("test_singleton_budget"))
            assert budget is not None
            assert budget.name == "Test Budget"


# ==============================================================================
# Test Concurrent Operations
# ==============================================================================


@pytest.mark.xdist_group(name="budget_concurrent_tests")
class TestBudgetMonitorConcurrentOperations:
    """Test suite for concurrent operations on BudgetMonitor.

    Validates that asyncio.Lock correctly protects shared state when
    multiple coroutines access the same BudgetMonitor instance concurrently.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_budget_creation(self):
        """
        GIVEN multiple coroutines creating budgets concurrently
        WHEN all coroutines complete
        THEN all budgets should be stored without data corruption
        """
        import asyncio

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(cost_collector=mock_cost_collector)

        async def create_budget(i: int):
            return await monitor.create_budget(
                id=f"concurrent_budget_{i}",
                name=f"Concurrent Budget {i}",
                limit_usd=Decimal(f"{100 + i}.00"),
                period=BudgetPeriod.MONTHLY,
            )

        # Act - create 20 budgets concurrently
        tasks = [create_budget(i) for i in range(20)]
        budgets = await asyncio.gather(*tasks)

        # Assert - all budgets created with correct data
        assert len(budgets) == 20

        all_budgets = await monitor.get_all_budgets()
        assert len(all_budgets) == 20

        for i in range(20):
            budget = await monitor.get_budget(f"concurrent_budget_{i}")
            assert budget is not None
            assert budget.name == f"Concurrent Budget {i}"
            assert budget.limit_usd == Decimal(f"{100 + i}.00")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_check_budget_calls(self):
        """
        GIVEN a budget exists and multiple check_budget calls run concurrently
        WHEN all check_budget calls complete
        THEN alerts are triggered correctly without duplicate alerting
        """
        import asyncio

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(cost_collector=mock_cost_collector)

        await monitor.create_budget(
            id="concurrent_check_budget",
            name="Concurrent Check Budget",
            limit_usd=Decimal("1000.00"),
            period=BudgetPeriod.MONTHLY,
        )

        with (
            patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("800.00")),
            patch.object(monitor, "send_alert", new_callable=AsyncMock),
        ):
            # Act - 10 concurrent check_budget calls
            tasks = [monitor.check_budget("concurrent_check_budget") for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # Assert - only one alert triggered (threshold only fires once)
            alerts_triggered = [r for r in results if r is not None]
            assert len(alerts_triggered) == 1
            assert alerts_triggered[0].budget_id == "concurrent_check_budget"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_get_budget_status(self):
        """
        GIVEN a budget exists and multiple get_budget_status calls run concurrently
        WHEN all calls complete
        THEN all return consistent budget status (no data races)
        """
        import asyncio

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(cost_collector=mock_cost_collector)

        await monitor.create_budget(
            id="concurrent_status_budget",
            name="Concurrent Status Budget",
            limit_usd=Decimal("1000.00"),
            period=BudgetPeriod.MONTHLY,
        )

        with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("500.00")):
            # Act - 15 concurrent get_budget_status calls
            tasks = [monitor.get_budget_status("concurrent_status_budget") for _ in range(15)]
            statuses = await asyncio.gather(*tasks)

            # Assert - all statuses consistent
            assert all(s is not None for s in statuses)
            assert all(s.spent_usd == Decimal("500.00") for s in statuses)
            assert all(s.utilization == Decimal("0.5") for s in statuses)
            assert all(s.remaining_usd == Decimal("500.00") for s in statuses)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_create_and_read_budgets(self):
        """
        GIVEN writers creating budgets and readers reading budgets concurrently
        WHEN all operations complete
        THEN no data races occur and all operations succeed
        """
        import asyncio

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(cost_collector=mock_cost_collector)

        results = {"reads_none": 0, "reads_found": 0, "creates_done": 0}

        async def create_budget(i: int):
            await monitor.create_budget(
                id=f"mixed_budget_{i}",
                name=f"Mixed Budget {i}",
                limit_usd=Decimal("100.00"),
                period=BudgetPeriod.DAILY,
            )
            results["creates_done"] += 1

        async def read_budget(i: int):
            budget = await monitor.get_budget(f"mixed_budget_{i}")
            if budget is None:
                results["reads_none"] += 1
            else:
                results["reads_found"] += 1

        # Act - interleave creates and reads
        tasks = []
        for i in range(10):
            tasks.append(create_budget(i))
            tasks.append(read_budget(i))

        await asyncio.gather(*tasks)

        # Assert - all creates completed, no exceptions
        assert results["creates_done"] == 10

        # All budgets exist after completion
        all_budgets = await monitor.get_all_budgets()
        assert len(all_budgets) == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_reset_budget(self):
        """
        GIVEN a budget with alerted thresholds
        WHEN reset_budget is called concurrently with check_budget
        THEN no deadlock occurs and operations complete
        """
        import asyncio

        # Arrange - mock cost collector to avoid storage initialization
        mock_cost_collector = MagicMock()
        monitor = BudgetMonitor(cost_collector=mock_cost_collector)

        await monitor.create_budget(
            id="reset_concurrent_budget",
            name="Reset Concurrent Budget",
            limit_usd=Decimal("1000.00"),
            period=BudgetPeriod.MONTHLY,
        )

        # Trigger initial alert
        with (
            patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("800.00")),
            patch.object(monitor, "send_alert", new_callable=AsyncMock),
        ):
            await monitor.check_budget("reset_concurrent_budget")

        async def reset_loop():
            for _ in range(5):
                await monitor.reset_budget("reset_concurrent_budget")
                await asyncio.sleep(0.001)

        async def check_loop():
            with (
                patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("800.00")),
                patch.object(monitor, "send_alert", new_callable=AsyncMock),
            ):
                for _ in range(5):
                    await monitor.check_budget("reset_concurrent_budget")
                    await asyncio.sleep(0.001)

        # Act - run reset and check concurrently (should not deadlock)
        await asyncio.wait_for(
            asyncio.gather(reset_loop(), check_loop()),
            timeout=5.0,  # Deadlock would timeout
        )

        # Assert - completed without deadlock (reaching this line is success)
        budget = await monitor.get_budget("reset_concurrent_budget")
        assert budget is not None
