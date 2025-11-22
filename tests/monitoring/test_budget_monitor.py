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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.monitoring.budget_monitor import AlertLevel, BudgetMonitor, BudgetPeriod

pytestmark = pytest.mark.unit

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def budget_monitor():
    """Create a fresh BudgetMonitor instance for testing."""
    return BudgetMonitor()


@pytest.fixture
def sample_budget_data():
    """Sample budget data for testing."""
    return {
        "id": "test_budget_001",
        "name": "Test Monthly Budget",
        "limit_usd": Decimal("1000.00"),
        "period": BudgetPeriod.MONTHLY,
        "start_date": datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
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
        before = datetime.now(timezone.utc)

        # Act
        budget = await budget_monitor.create_budget(
            id="budget_002",
            name="Test Budget",
            limit_usd=Decimal("500.00"),
            period=BudgetPeriod.WEEKLY,
            start_date=None,  # Not provided
        )

        # Assert
        after = datetime.now(timezone.utc)
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

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 11, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert period_end == datetime(2025, 11, 16, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_weekly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for WEEKLY period (Monday-Sunday)."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.WEEKLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        # Friday, November 15, 2025
        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=timezone.utc)  # Friday

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

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert period_end == datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_monthly_budget_in_december(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() handles December → January transition."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.MONTHLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 12, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert period_end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_quarterly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for QUARTERLY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.QUARTERLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        # Q4: October, November, December
        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert period_end == period_start + timedelta(days=90)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_period_boundaries_for_yearly_budget(self, budget_monitor, sample_budget_data):
        """Test _calculate_period_boundaries() for YEARLY period."""
        # Arrange
        sample_budget_data["period"] = BudgetPeriod.YEARLY
        budget = await budget_monitor.create_budget(**sample_budget_data)

        current_time = datetime(2025, 11, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Act
        period_start, period_end = budget_monitor._calculate_period_boundaries(budget, current_time)

        # Assert
        assert period_start == datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert period_end == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


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
        monitor = BudgetMonitor()  # No SMTP config

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
        """Test _send_webhook_alert() sends HTTP POST to webhook URL."""
        # Arrange
        monitor = BudgetMonitor(webhook_url="https://hooks.slack.com/services/ABC123")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            # Act
            await monitor._send_webhook_alert(
                level="critical", message="Budget exceeded", budget_id="budget_001", utilization=95.0
            )

            # Assert
            mock_post.assert_called_once()
            call_args = mock_post.call_args
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
        monitor = BudgetMonitor()  # No webhook URL

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            # Act
            await monitor._send_webhook_alert(
                level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0
            )

            # Assert
            mock_post.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_webhook_alert_includes_timestamp(self):
        """Test _send_webhook_alert() includes ISO 8601 timestamp in payload."""
        # Arrange
        monitor = BudgetMonitor(webhook_url="https://example.com/webhook")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        before = datetime.now(timezone.utc)

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            # Act
            await monitor._send_webhook_alert(
                level="warning", message="Budget alert", budget_id="budget_001", utilization=80.0
            )

            # Assert
            after = datetime.now(timezone.utc)
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
