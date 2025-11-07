"""
Integration Tests for PostgreSQL Storage Backends

Tests real PostgreSQL storage implementations for GDPR/HIPAA compliance.
Addresses OpenAI Codex finding: "Compliance storage tests stop at Pydantic instantiation"

TDD Approach:
- RED: These tests will fail initially without proper database schema
- GREEN: Tests pass once schema is created
- REFACTOR: Optimize and document

Compliance:
- GDPR Article 30: Records of processing activities (audit logs)
- HIPAA §164.312(b): Audit controls (7-year retention)
- SOC2 CC6.6: Audit logging and monitoring
"""

import uuid
from datetime import datetime, timedelta

import pytest

from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry, ConsentRecord


@pytest.mark.integration
@pytest.mark.asyncio
class TestPostgresAuditLogStore:
    """
    Test PostgresAuditLogStore with real PostgreSQL

    TDD: RED phase - These tests should fail without proper schema
    """

    @pytest.fixture
    async def audit_store(self, postgres_with_schema, postgres_connection_clean):
        """Create PostgresAuditLogStore with real database and schema"""
        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresAuditLogStore

        # Ensure schema is initialized
        _ = postgres_with_schema

        # Create a pool from the connection (simplified for testing)
        # In production, this would be a real connection pool
        class SimplePool:
            def __init__(self, conn):
                self.conn = conn

            def acquire(self):
                return self

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, *args):
                pass

        pool = SimplePool(postgres_connection_clean)
        return PostgresAuditLogStore(pool)

    async def test_create_audit_log_entry(self, audit_store):
        """
        TDD RED: Test creating audit log entry in PostgreSQL

        This test will fail initially without the audit_logs table schema.
        Once schema is created, it should pass (GREEN phase).
        """
        # Create audit log entry
        entry = AuditLogEntry(
            log_id=f"log_{uuid.uuid4().hex[:8]}",
            user_id="user:alice",
            action="conversation.create",
            resource_type="conversation",
            resource_id="conv_123",
            timestamp=datetime.utcnow().isoformat() + "Z",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"source": "test", "priority": "high"},
        )

        # Should persist to PostgreSQL
        log_id = await audit_store.log(entry)
        assert log_id == entry.log_id

        # Should be retrievable
        retrieved = await audit_store.get(log_id)
        assert retrieved is not None
        assert retrieved.user_id == "user:alice"
        assert retrieved.action == "conversation.create"
        assert retrieved.resource_type == "conversation"
        assert retrieved.resource_id == "conv_123"
        assert retrieved.ip_address == "192.168.1.1"
        assert retrieved.metadata["source"] == "test"
        assert retrieved.metadata["priority"] == "high"

    async def test_get_nonexistent_audit_log(self, audit_store):
        """Test retrieving non-existent log returns None"""
        result = await audit_store.get("nonexistent_log_id")
        assert result is None

    async def test_get_user_logs(self, audit_store):
        """Test retrieving all logs for a specific user"""
        # Create multiple logs for different users
        entries = [
            AuditLogEntry(
                log_id=f"log_alice_1_{uuid.uuid4().hex[:8]}",
                user_id="user:alice",
                action="login",
                resource_type="auth",
                timestamp=datetime.utcnow().isoformat() + "Z",
            ),
            AuditLogEntry(
                log_id=f"log_alice_2_{uuid.uuid4().hex[:8]}",
                user_id="user:alice",
                action="conversation.view",
                resource_type="conversation",
                timestamp=datetime.utcnow().isoformat() + "Z",
            ),
            AuditLogEntry(
                log_id=f"log_bob_1_{uuid.uuid4().hex[:8]}",
                user_id="user:bob",
                action="login",
                resource_type="auth",
                timestamp=datetime.utcnow().isoformat() + "Z",
            ),
        ]

        for entry in entries:
            await audit_store.log(entry)

        # Get logs for Alice
        alice_logs = await audit_store.get_user_logs("user:alice")
        assert len(alice_logs) >= 2
        assert all(log.user_id == "user:alice" for log in alice_logs)

        # Get logs for Bob
        bob_logs = await audit_store.get_user_logs("user:bob")
        assert len(bob_logs) >= 1
        assert all(log.user_id == "user:bob" for log in bob_logs)

    async def test_get_logs_by_date_range(self, audit_store):
        """Test retrieving logs within date range"""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create log entry for today
        entry = AuditLogEntry(
            log_id=f"log_today_{uuid.uuid4().hex[:8]}",
            user_id="user:alice",
            action="data.access",
            resource_type="user_data",
            timestamp=now.isoformat() + "Z",
        )
        await audit_store.log(entry)

        # Query logs from yesterday to tomorrow (should include today's log)
        logs = await audit_store.get_logs_by_date_range(
            start_date=yesterday.isoformat() + "Z", end_date=tomorrow.isoformat() + "Z"
        )

        # Should include the log we just created
        log_ids = [log.log_id for log in logs]
        assert entry.log_id in log_ids

    async def test_anonymize_user_logs(self, audit_store):
        """
        Test anonymizing user logs for GDPR Article 17 (Right to Erasure)

        This is critical for GDPR compliance - when user requests deletion,
        we must anonymize their audit logs while retaining the audit trail.
        """
        # Create logs for user
        entry = AuditLogEntry(
            log_id=f"log_gdpr_{uuid.uuid4().hex[:8]}",
            user_id="user:charlie",
            action="data.view",
            resource_type="personal_data",
            timestamp=datetime.utcnow().isoformat() + "Z",
            ip_address="10.0.0.5",
            user_agent="Chrome/100",
        )
        await audit_store.log(entry)

        # Anonymize logs for user (GDPR Article 17)
        count = await audit_store.anonymize_user_logs("user:charlie")
        assert count >= 1

        # Verify log still exists but user_id is anonymized
        anonymized = await audit_store.get(entry.log_id)
        assert anonymized is not None
        assert anonymized.user_id.startswith("anonymous_")
        assert anonymized.action == "data.view"  # Action preserved for audit

    async def test_audit_log_immutability(self, audit_store):
        """
        Test that audit logs are immutable (append-only)

        HIPAA/SOC2 requirement: Audit logs must be immutable for compliance.
        This test verifies no update/delete methods exist.
        """
        # Verify store has no update method
        assert not hasattr(audit_store, "update"), "Audit logs must be immutable (no update method)"
        assert not hasattr(audit_store, "delete"), "Audit logs must be immutable (no delete method)"

    async def test_audit_log_with_empty_metadata(self, audit_store):
        """Test audit log with empty metadata (edge case)"""
        entry = AuditLogEntry(
            log_id=f"log_empty_meta_{uuid.uuid4().hex[:8]}",
            user_id="user:test",
            action="test.action",
            resource_type="test",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={},  # Empty metadata
        )

        log_id = await audit_store.log(entry)
        retrieved = await audit_store.get(log_id)

        assert retrieved is not None
        assert retrieved.metadata == {}

    async def test_audit_log_with_complex_metadata(self, audit_store):
        """Test audit log with nested JSON metadata"""
        entry = AuditLogEntry(
            log_id=f"log_complex_{uuid.uuid4().hex[:8]}",
            user_id="user:test",
            action="complex.action",
            resource_type="test",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={
                "nested": {"level1": {"level2": "value"}},
                "array": [1, 2, 3],
                "mixed": {"num": 42, "str": "test", "bool": True},
            },
        )

        log_id = await audit_store.log(entry)
        retrieved = await audit_store.get(log_id)

        assert retrieved is not None
        assert retrieved.metadata["nested"]["level1"]["level2"] == "value"
        assert retrieved.metadata["array"] == [1, 2, 3]
        assert retrieved.metadata["mixed"]["num"] == 42

    async def test_concurrent_audit_log_writes(self, audit_store):
        """Test concurrent writes to audit log (thread safety)"""
        import asyncio

        # Create 10 log entries concurrently
        async def create_log(i):
            entry = AuditLogEntry(
                log_id=f"log_concurrent_{i}_{uuid.uuid4().hex[:8]}",
                user_id=f"user:concurrent_{i}",
                action="concurrent.test",
                resource_type="test",
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            return await audit_store.log(entry)

        # Run concurrently
        log_ids = await asyncio.gather(*[create_log(i) for i in range(10)])

        # All should succeed
        assert len(log_ids) == 10
        assert len(set(log_ids)) == 10  # All unique

        # All should be retrievable
        for log_id in log_ids:
            retrieved = await audit_store.get(log_id)
            assert retrieved is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestPostgresConsentStore:
    """
    Test PostgresConsentStore with real PostgreSQL

    TDD: RED phase - These tests should fail without proper schema
    """

    @pytest.fixture
    async def consent_store(self, postgres_with_schema, postgres_connection_clean):
        """Create PostgresConsentStore with real database and schema"""
        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresConsentStore

        # Ensure schema is initialized
        _ = postgres_with_schema

        class SimplePool:
            def __init__(self, conn):
                self.conn = conn

            def acquire(self):
                return self

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, *args):
                pass

        pool = SimplePool(postgres_connection_clean)
        return PostgresConsentStore(pool)

    async def test_create_consent_record(self, consent_store):
        """
        TDD RED: Test creating consent record in PostgreSQL

        This test will fail initially without the consent_records table schema.
        """
        record = ConsentRecord(
            consent_id=f"consent_{uuid.uuid4().hex[:8]}",
            user_id="user:alice",
            consent_type="analytics",
            granted=True,
            timestamp=datetime.utcnow().isoformat() + "Z",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            metadata={"version": "1.0"},
        )

        consent_id = await consent_store.create(record)
        assert consent_id == record.consent_id

        # Should be retrievable
        user_consents = await consent_store.get_user_consents("user:alice")
        assert len(user_consents) >= 1
        assert any(c.consent_id == consent_id for c in user_consents)

    async def test_get_latest_consent(self, consent_store):
        """Test getting latest consent for a specific type"""
        # Create multiple consent records for same user and type
        consent_1 = ConsentRecord(
            consent_id=f"consent_old_{uuid.uuid4().hex[:8]}",
            user_id="user:bob",
            consent_type="marketing",
            granted=False,  # Initially declined
            timestamp=(datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
        )

        consent_2 = ConsentRecord(
            consent_id=f"consent_new_{uuid.uuid4().hex[:8]}",
            user_id="user:bob",
            consent_type="marketing",
            granted=True,  # Later accepted
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        await consent_store.create(consent_1)
        await consent_store.create(consent_2)

        # Get latest consent
        latest = await consent_store.get_latest_consent("user:bob", "marketing")
        assert latest is not None
        assert latest.consent_id == consent_2.consent_id
        assert latest.granted is True  # Latest consent should be True

    async def test_consent_audit_trail(self, consent_store):
        """
        Test consent audit trail (GDPR Article 7)

        GDPR requires demonstrating that consent was given.
        All consent changes must be recorded for audit trail.
        """
        user_id = "user:audit_test"

        # Create consent history: granted → revoked → granted
        consents = [
            ConsentRecord(
                consent_id=f"consent_1_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                consent_type="analytics",
                granted=True,
                timestamp=(datetime.utcnow() - timedelta(days=10)).isoformat() + "Z",
            ),
            ConsentRecord(
                consent_id=f"consent_2_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                consent_type="analytics",
                granted=False,
                timestamp=(datetime.utcnow() - timedelta(days=5)).isoformat() + "Z",
            ),
            ConsentRecord(
                consent_id=f"consent_3_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                consent_type="analytics",
                granted=True,
                timestamp=datetime.utcnow().isoformat() + "Z",
            ),
        ]

        for consent in consents:
            await consent_store.create(consent)

        # Get full audit trail
        all_consents = await consent_store.get_user_consents(user_id)
        assert len(all_consents) >= 3

        # Verify complete history is preserved
        consent_ids = [c.consent_id for c in all_consents]
        for consent in consents:
            assert consent.consent_id in consent_ids

    async def test_multiple_consent_types(self, consent_store):
        """Test managing multiple consent types for same user"""
        user_id = "user:multi_consent"

        # Create different consent types
        consent_types = ["analytics", "marketing", "third_party", "profiling"]

        for consent_type in consent_types:
            record = ConsentRecord(
                consent_id=f"consent_{consent_type}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                consent_type=consent_type,
                granted=(consent_type in ["analytics", "marketing"]),  # Some granted, some not
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            await consent_store.create(record)

        # Verify all types recorded
        all_consents = await consent_store.get_user_consents(user_id)
        recorded_types = {c.consent_type for c in all_consents}

        for consent_type in consent_types:
            assert consent_type in recorded_types

    async def test_consent_with_metadata(self, consent_store):
        """Test consent record with rich metadata"""
        record = ConsentRecord(
            consent_id=f"consent_meta_{uuid.uuid4().hex[:8]}",
            user_id="user:metadata_test",
            consent_type="marketing",
            granted=True,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={
                "source": "web_form",
                "version": "2.0",
                "jurisdiction": "EU",
                "method": "explicit_opt_in",
            },
        )

        await consent_store.create(record)

        # Retrieve and verify metadata
        latest = await consent_store.get_latest_consent("user:metadata_test", "marketing")
        assert latest is not None
        assert latest.metadata["source"] == "web_form"
        assert latest.metadata["jurisdiction"] == "EU"

    async def test_consent_immutability(self, consent_store):
        """
        Test that consent records are immutable (append-only)

        GDPR Article 7(1): Controller must demonstrate consent was given.
        Consent records must be immutable for legal validity.
        """
        # Verify store has no update method
        assert not hasattr(consent_store, "update"), "Consent records must be immutable (no update)"
        assert not hasattr(consent_store, "delete"), "Consent records must be immutable (no delete)"

        # Only create() and get methods should exist
        assert hasattr(consent_store, "create")
        assert hasattr(consent_store, "get_user_consents")
        assert hasattr(consent_store, "get_latest_consent")


@pytest.mark.integration
@pytest.mark.asyncio
class TestPostgresStorageEdgeCases:
    """Test edge cases and error handling for PostgreSQL storage"""

    @pytest.fixture
    async def audit_store(self, postgres_connection_clean):
        """Create PostgresAuditLogStore"""
        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresAuditLogStore

        class SimplePool:
            def __init__(self, conn):
                self.conn = conn

            def acquire(self):
                return self

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, *args):
                pass

        pool = SimplePool(postgres_connection_clean)
        return PostgresAuditLogStore(pool)

    async def test_audit_log_with_null_optional_fields(self, audit_store):
        """Test creating audit log with None for optional fields"""
        entry = AuditLogEntry(
            log_id=f"log_nulls_{uuid.uuid4().hex[:8]}",
            user_id="user:test",
            action="test.action",
            resource_type="test",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # All optional fields None
            resource_id=None,
            ip_address=None,
            user_agent=None,
            metadata={},
        )

        log_id = await audit_store.log(entry)
        retrieved = await audit_store.get(log_id)

        assert retrieved is not None
        assert retrieved.resource_id is None
        assert retrieved.ip_address is None
        assert retrieved.user_agent is None

    async def test_special_characters_in_metadata(self, audit_store):
        """Test handling special characters and SQL injection prevention"""
        entry = AuditLogEntry(
            log_id=f"log_special_{uuid.uuid4().hex[:8]}",
            user_id="user:test",
            action="test.action",
            resource_type="test",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={
                "sql_injection": "'; DROP TABLE audit_logs; --",
                "unicode": "こんにちは 🎉",
                "quotes": 'She said "hello"',
                "backslash": "C:\\Users\\test",
            },
        )

        log_id = await audit_store.log(entry)
        retrieved = await audit_store.get(log_id)

        assert retrieved is not None
        assert retrieved.metadata["sql_injection"] == "'; DROP TABLE audit_logs; --"
        assert retrieved.metadata["unicode"] == "こんにちは 🎉"
        assert retrieved.metadata["quotes"] == 'She said "hello"'
        assert retrieved.metadata["backslash"] == "C:\\Users\\test"

    async def test_large_metadata_storage(self, audit_store):
        """Test storing large metadata objects"""
        # Create large metadata (but within reasonable limits)
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}

        entry = AuditLogEntry(
            log_id=f"log_large_{uuid.uuid4().hex[:8]}",
            user_id="user:test",
            action="test.large",
            resource_type="test",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata=large_metadata,
        )

        log_id = await audit_store.log(entry)
        retrieved = await audit_store.get(log_id)

        assert retrieved is not None
        assert len(retrieved.metadata) == 50
        assert retrieved.metadata["key_0"] == "value_0" * 100
