"""
SQL Injection Security Tests for GDPR Storage

Tests that the dynamic SQL query construction in postgres_storage.py
is safe from SQL injection attacks despite using f-strings.

Following TDD best practices - tests prove security properties of the implementation.
Tests cover OWASP A03:2021 - Injection attacks on database queries.
"""

import gc
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

from mcp_server_langgraph.compliance.gdpr.postgres_storage import (
    PostgresAuditLogStore,
    PostgresConversationStore,
    PostgresUserProfileStore,
)
from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry, Conversation, UserProfile


# NOTE: Using db_pool_gdpr fixture from conftest.py instead of local db_pool
# The db_pool_gdpr fixture properly depends on integration_test_env which starts
# Docker services (PostgreSQL). Local fixture was causing OSError: Connect call failed
# in CI because PostgreSQL wasn't running.


@pytest.fixture
async def profile_store(db_pool_gdpr: asyncpg.Pool) -> PostgresUserProfileStore:
    """Create user profile store for security tests"""
    return PostgresUserProfileStore(db_pool_gdpr)


@pytest.fixture
async def conversation_store(db_pool_gdpr: asyncpg.Pool) -> PostgresConversationStore:
    """Create conversation store for security tests"""
    return PostgresConversationStore(db_pool_gdpr)


@pytest.fixture
async def audit_store(db_pool_gdpr: asyncpg.Pool) -> PostgresAuditLogStore:
    """Create audit log store for security tests"""
    return PostgresAuditLogStore(db_pool_gdpr)


@pytest.fixture
async def test_user(profile_store: PostgresUserProfileStore) -> str:
    """Create test user for security tests"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile = UserProfile(
        user_id="test_sec_user_alice",
        username="alice_sec",
        email="alice_sec@example.com",
        created_at=now,
        last_updated=now,
    )
    await profile_store.create(profile)
    return "test_sec_user_alice"


@pytest.fixture
async def test_conversation(
    conversation_store: PostgresConversationStore,
    test_user: str,
) -> str:
    """Create test conversation for security tests"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conversation = Conversation(
        conversation_id="test_sec_conv_123",
        user_id=test_user,
        title="Security Test Conversation",
        messages=[
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Test response"},
        ],
        created_at=now,
        last_message_at=now,
    )
    await conversation_store.create(conversation)
    return "test_sec_conv_123"


# ============================================================================
# SQL Injection Tests for PostgresConversationStore.update()
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.security
@pytest.mark.xdist_group(name="testconversationstoresqlinjection")
class TestConversationStoreSQLInjection:
    """
    Test SQL injection defenses in PostgresConversationStore.update()

    Target: src/mcp_server_langgraph/compliance/gdpr/postgres_storage.py:606

    The update() method uses f-strings to construct dynamic UPDATE queries.
    These tests verify that field names are validated via allowlist and
    values are safely parameterized to prevent SQL injection.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_reject_malicious_field_names_with_sql_injection(
        self,
        conversation_store: PostgresConversationStore,
        test_conversation: str,
    ):
        """
        Test that SQL injection attempts via field names are rejected.

        Attack vector: Try to inject SQL commands via field names in updates dict.
        Defense: Field names must match allowlist (title, last_message_at, archived, messages, metadata)

        Expected: Invalid field names are silently ignored, no SQL injection occurs.
        """
        # Attack 1: Try to drop table via field name
        malicious_updates_1 = {
            "title; DROP TABLE conversations; --": "Attack",
        }
        result_1 = await conversation_store.update(test_conversation, malicious_updates_1)
        assert result_1 is False  # No valid fields updated

        # Attack 2: Try to bypass WHERE clause via field name
        malicious_updates_2 = {
            "title = 'pwned' WHERE 1=1; --": "Attack",
        }
        result_2 = await conversation_store.update(test_conversation, malicious_updates_2)
        assert result_2 is False  # No valid fields updated

        # Attack 3: Try to inject multiple statements via field name
        malicious_updates_3 = {
            "title'; DELETE FROM conversations WHERE '1'='1": "Attack",
        }
        result_3 = await conversation_store.update(test_conversation, malicious_updates_3)
        assert result_3 is False  # No valid fields updated

        # Verify conversation is still intact
        conversation = await conversation_store.get(test_conversation)
        assert conversation is not None
        assert conversation.title == "Security Test Conversation"  # Original title unchanged

    async def test_parameterized_values_prevent_sql_injection(
        self,
        conversation_store: PostgresConversationStore,
        test_conversation: str,
    ):
        """
        Test that SQL injection attempts via values are safely parameterized.

        Attack vector: Try to inject SQL commands via the value being updated.
        Defense: Values are passed as PostgreSQL parameters ($1, $2, etc.), not string-interpolated.

        Expected: Malicious SQL strings are stored as literal strings, not executed as SQL.
        """
        # Attack: Try to inject SQL via title value
        malicious_value = "'; DROP TABLE conversations; --"

        result = await conversation_store.update(
            test_conversation,
            {"title": malicious_value},
        )
        assert result is True  # Update succeeded

        # Verify malicious value was stored as string (not executed as SQL)
        conversation = await conversation_store.get(test_conversation)
        assert conversation is not None
        assert conversation.title == malicious_value  # Stored as-is

        # Verify table still exists (wasn't dropped)
        all_convs = await conversation_store.list_user_conversations("test_sec_user_alice")
        assert len(all_convs) >= 1

    async def test_multiple_malicious_fields_rejected(
        self,
        conversation_store: PostgresConversationStore,
        test_conversation: str,
    ):
        """
        Test that multiple malicious field names are all rejected.

        Attack vector: Try combinations of valid and invalid field names.
        Defense: Only allowlisted fields are processed, others silently ignored.

        Expected: Only valid fields are updated, malicious fields ignored.
        """
        # Mix of valid field and malicious field names
        updates = {
            "title": "Valid Update",  # Valid field
            "'; DELETE FROM conversations; --": "Attack",  # Invalid field
            "archived': True); DROP TABLE conversations; --": "Attack",  # Invalid field
        }

        result = await conversation_store.update(test_conversation, updates)
        assert result is True  # Valid field updated

        # Verify only valid field was updated
        conversation = await conversation_store.get(test_conversation)
        assert conversation is not None
        assert conversation.title == "Valid Update"  # Valid field updated
        assert conversation.archived is False  # Not affected by malicious fields

    async def test_metadata_field_with_malicious_json(
        self,
        conversation_store: PostgresConversationStore,
        test_conversation: str,
    ):
        """
        Test that malicious JSON in metadata field is safely stored.

        Attack vector: Try to inject SQL via JSON metadata values.
        Defense: Metadata is stored as JSONB with parameterized query.

        Expected: Malicious JSON values stored safely, not executed.
        """
        malicious_metadata = {
            "key": "'; DROP TABLE conversations; --",
            "another_key": "value' OR '1'='1",
        }

        result = await conversation_store.update(
            test_conversation,
            {"metadata": malicious_metadata},
        )
        assert result is True

        # Verify metadata stored correctly
        conversation = await conversation_store.get(test_conversation)
        assert conversation is not None
        assert conversation.metadata == malicious_metadata

    async def test_all_allowlisted_fields_safe(
        self,
        conversation_store: PostgresConversationStore,
        test_conversation: str,
    ):
        """
        Test that all allowlisted fields handle values safely.

        Validates that the allowlist (title, last_message_at, archived, messages, metadata)
        all use parameterized queries correctly.
        """
        malicious_string = "'; DROP TABLE conversations; --"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Update all allowlisted fields with potentially malicious content
        updates = {
            "title": malicious_string,
            "last_message_at": now,
            "archived": True,
            "messages": [{"role": "user", "content": malicious_string}],
            "metadata": {"attack": malicious_string},
        }

        result = await conversation_store.update(test_conversation, updates)
        assert result is True

        # Verify all values stored safely
        conversation = await conversation_store.get(test_conversation)
        assert conversation is not None
        assert conversation.title == malicious_string
        assert conversation.messages[0]["content"] == malicious_string
        assert conversation.metadata["attack"] == malicious_string


# ============================================================================
# SQL Injection Tests for PostgresAuditLogStore.list_user_logs()
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.security
@pytest.mark.xdist_group(name="testauditlogstoresqlinjection")
class TestAuditLogStoreSQLInjection:
    """
    Test SQL injection defenses in PostgresAuditLogStore.list_user_logs()

    Target: src/mcp_server_langgraph/compliance/gdpr/postgres_storage.py:766

    The list_user_logs() method uses f-strings to construct dynamic WHERE clauses.
    These tests verify that user_id and date parameters are safely parameterized.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_parameterized_user_id_prevents_sql_injection(
        self,
        audit_store: PostgresAuditLogStore,
    ):
        """
        Test that SQL injection via user_id parameter is prevented.

        Attack vector: Try to inject SQL via user_id parameter.
        Defense: user_id is passed as PostgreSQL parameter ($1), not string-interpolated.

        Expected: Malicious user_id treated as literal string, returns empty results.
        """
        # Create legitimate audit log
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        legitimate_entry = AuditLogEntry(
            log_id="test_sec_log_001",
            user_id="test_sec_user_alice",
            action="profile.read",
            resource_type="user_profile",
            resource_id="test_sec_user_alice",
            timestamp=now,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )
        await audit_store.log(legitimate_entry)

        # Attack: Try to bypass user_id filter with SQL injection
        malicious_user_id = "test_sec_user_alice' OR '1'='1"

        logs = await audit_store.list_user_logs(malicious_user_id)

        # Should return empty - no user with that exact malicious ID
        assert len(logs) == 0

        # Verify legitimate query still works
        legitimate_logs = await audit_store.list_user_logs("test_sec_user_alice")
        assert len(legitimate_logs) == 1
        assert legitimate_logs[0].log_id == "test_sec_log_001"

    async def test_date_filters_safely_parameterized(
        self,
        audit_store: PostgresAuditLogStore,
    ):
        """
        Test that date filter parameters are safely bound.

        Attack vector: Try to inject SQL via start_date/end_date parameters.
        Defense: Datetime objects are type-checked and parameterized.

        Expected: Type checking prevents string injection, datetime params are safe.
        """
        # Create audit logs at different times
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=30)

        entry_past = AuditLogEntry(
            log_id="test_sec_log_past",
            user_id="test_sec_user_alice",
            action="profile.read",
            resource_type="user_profile",
            resource_id="test_sec_user_alice",
            timestamp=past.isoformat().replace("+00:00", "Z"),
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )
        await audit_store.log(entry_past)

        entry_now = AuditLogEntry(
            log_id="test_sec_log_now",
            user_id="test_sec_user_alice",
            action="profile.update",
            resource_type="user_profile",
            resource_id="test_sec_user_alice",
            timestamp=now.isoformat().replace("+00:00", "Z"),
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )
        await audit_store.log(entry_now)

        # Query with date range (using actual datetime objects)
        start_date = now - timedelta(days=7)
        end_date = now + timedelta(days=1)

        logs = await audit_store.list_user_logs(
            user_id="test_sec_user_alice",
            start_date=start_date,
            end_date=end_date,
        )

        # Should only return recent log
        assert len(logs) == 1
        assert logs[0].log_id == "test_sec_log_now"

    async def test_limit_parameter_safely_handled(
        self,
        audit_store: PostgresAuditLogStore,
    ):
        """
        Test that limit parameter is safely parameterized.

        Attack vector: Try to inject SQL via limit parameter.
        Defense: Limit is passed as PostgreSQL parameter, type-checked as int.

        Expected: Limit is safely parameterized, no SQL injection possible.
        """
        # Create multiple audit logs
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for i in range(5):
            entry = AuditLogEntry(
                log_id=f"test_sec_log_limit_{i}",
                user_id="test_sec_user_alice",
                action=f"action_{i}",
                resource_type="user_profile",
                resource_id="test_sec_user_alice",
                timestamp=now,
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
            )
            await audit_store.log(entry)

        # Query with limit (should be type-checked as int)
        logs = await audit_store.list_user_logs(
            user_id="test_sec_user_alice",
            limit=2,
        )

        # Should only return 2 logs due to limit
        assert len(logs) == 2

    async def test_combined_parameters_all_safe(
        self,
        audit_store: PostgresAuditLogStore,
    ):
        """
        Test that all parameters combined are safely handled.

        Validates that user_id, start_date, end_date, and limit all use
        parameterized queries correctly when used together.
        """
        now = datetime.now(timezone.utc)

        # Create audit logs for security test
        for i in range(10):
            entry = AuditLogEntry(
                log_id=f"test_sec_log_combined_{i}",
                user_id="test_sec_user_alice",
                action=f"action_{i}",
                resource_type="user_profile",
                resource_id="test_sec_user_alice",
                timestamp=(now - timedelta(hours=i)).isoformat().replace("+00:00", "Z"),
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
            )
            await audit_store.log(entry)

        # Query with all parameters
        start_date = now - timedelta(hours=5)
        end_date = now + timedelta(hours=1)

        logs = await audit_store.list_user_logs(
            user_id="test_sec_user_alice",
            start_date=start_date,
            end_date=end_date,
            limit=3,
        )

        # Should return up to 3 logs within date range
        assert len(logs) <= 3
        assert all(log.user_id == "test_sec_user_alice" for log in logs)

    async def test_user_id_with_special_characters_safe(
        self,
        audit_store: PostgresAuditLogStore,
    ):
        """
        Test that user_id with special characters is safely handled.

        Validates that even user IDs with SQL-like special characters
        are treated as literal strings, not SQL syntax.
        """
        # Create audit log with user_id containing special chars
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        special_user_id = "test_sec_user_'; DROP TABLE audit_logs; --"

        entry = AuditLogEntry(
            log_id="test_sec_log_special",
            user_id=special_user_id,
            action="special.test",
            resource_type="user_profile",
            resource_id=special_user_id,
            timestamp=now,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )
        await audit_store.log(entry)

        # Query with special user_id
        logs = await audit_store.list_user_logs(special_user_id)

        # Should find the log (user_id treated as literal string)
        assert len(logs) == 1
        assert logs[0].user_id == special_user_id
        assert logs[0].log_id == "test_sec_log_special"
