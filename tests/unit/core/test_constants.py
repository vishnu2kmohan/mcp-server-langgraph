"""Tests for core constants module."""

import gc

import pytest

from mcp_server_langgraph.core.constants import (
    COMPACTION_THRESHOLD_TOKENS,
    DEFAULT_DATABASE_TIMEOUT_SECONDS,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_REDIS_SOCKET_TIMEOUT_SECONDS,
    MESSAGE_PREVIEW_LENGTH,
    RECENT_MESSAGE_COUNT,
    TARGET_AFTER_COMPACTION_TOKENS,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_constants")
class TestContextManagementConstants:
    """Tests for context management constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_preview_length_is_reasonable(self):
        """Message preview should be between 100-500 characters."""
        assert 100 <= MESSAGE_PREVIEW_LENGTH <= 500
        assert MESSAGE_PREVIEW_LENGTH == 200

    def test_compaction_threshold_greater_than_target(self):
        """Compaction threshold should be larger than target."""
        assert COMPACTION_THRESHOLD_TOKENS > TARGET_AFTER_COMPACTION_TOKENS

    def test_compaction_threshold_is_reasonable(self):
        """Compaction threshold should be reasonable token count."""
        assert COMPACTION_THRESHOLD_TOKENS == 8000

    def test_target_after_compaction_is_reasonable(self):
        """Target after compaction should be reasonable."""
        assert TARGET_AFTER_COMPACTION_TOKENS == 4000

    def test_recent_message_count_is_positive(self):
        """Recent message count should be positive."""
        assert RECENT_MESSAGE_COUNT > 0
        assert RECENT_MESSAGE_COUNT == 5


@pytest.mark.xdist_group(name="test_constants")
class TestTimeoutConstants:
    """Tests for timeout constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_llm_timeout_is_reasonable(self):
        """LLM timeout should be between 30-120 seconds."""
        assert 30 <= DEFAULT_LLM_TIMEOUT_SECONDS <= 120

    def test_database_timeout_is_reasonable(self):
        """Database timeout should be short for health checks."""
        assert 1 <= DEFAULT_DATABASE_TIMEOUT_SECONDS <= 30

    def test_redis_timeout_is_reasonable(self):
        """Redis timeout should be very short."""
        assert 1 <= DEFAULT_REDIS_SOCKET_TIMEOUT_SECONDS <= 10
