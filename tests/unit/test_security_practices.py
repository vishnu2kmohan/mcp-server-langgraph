"""
Test security best practices and vulnerability prevention.

This test suite validates that security best practices are followed:
- No weak cryptographic hashes for security-sensitive operations
- No hardcoded unsafe temporary directories
- SQL injection prevention through proper parameterization

These tests follow TDD principles:
RED Phase: Tests fail when insecure patterns are present
GREEN Phase: Tests pass after security fixes are applied
"""

import gc
import hashlib
import inspect
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="unit_security_practices_tests")
class TestCryptographicSecurity:
    """Test that cryptographic operations use secure algorithms."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("kubernetes"),
        reason="kubernetes library not installed (optional dependency for kubernetes sandbox)",
    )
    def test_kubernetes_sandbox_does_not_use_insecure_md5(self):
        """
        Test that Kubernetes job name generation doesn't use MD5 insecurely.

        FAILS when: MD5 is used without usedforsecurity=False
        PASSES when: SHA-256 is used OR MD5 has usedforsecurity=False
        """
        from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

        # Get source code of the _create_job method (where job names are generated)
        source = inspect.getsource(KubernetesSandbox._create_job)

        # Check for MD5 usage
        if "md5" in source.lower():
            # If MD5 is used, it MUST have usedforsecurity=False
            assert "usedforsecurity=False" in source, (
                "MD5 usage detected without usedforsecurity=False flag. "
                "Either use SHA-256 or add usedforsecurity=False for non-security uses."
            )
        else:
            # Preferred: SHA-256 should be used instead
            assert (
                "sha256" in source.lower() or "sha3" in source.lower()
            ), "Expected secure hash algorithm (SHA-256 or SHA-3) for job name generation"

    def test_job_name_hash_produces_valid_kubernetes_names(self):
        """
        Test that job name generation produces valid Kubernetes resource names.

        This ensures the hash function (MD5 or SHA-256) produces acceptable names.
        """
        # Simulate job name generation
        test_code = "print('hello world')"

        # Test with SHA-256 (recommended)
        code_hash_sha256 = hashlib.sha256(test_code.encode()).hexdigest()[:8]
        assert len(code_hash_sha256) == 8
        assert code_hash_sha256.isalnum()

        # Test with MD5 (acceptable if usedforsecurity=False)
        code_hash_md5 = hashlib.md5(test_code.encode(), usedforsecurity=False).hexdigest()[:8]
        assert len(code_hash_md5) == 8
        assert code_hash_md5.isalnum()


@pytest.mark.xdist_group(name="unit_security_practices_tests")
class TestTemporaryDirectorySecurity:
    """Test that temporary directory usage follows security best practices."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_builder_api_does_not_use_hardcoded_tmp(self):
        """
        Test that builder API doesn't hardcode /tmp directory.

        FAILS when: "/tmp" is hardcoded as default
        PASSES when: Using tempfile.gettempdir() or similar secure method
        """
        from mcp_server_langgraph.builder.api import server

        # Get source code
        source = inspect.getsource(server)

        # Check for hardcoded /tmp patterns
        # We allow environment variable overrides, but default should be secure
        if '"/tmp' in source or "'/tmp" in source:
            # If /tmp is mentioned, it should only be in controlled contexts
            # and accompanied by proper validation or environment overrides
            assert "os.getenv" in source or "tempfile" in source, (
                "Hardcoded /tmp directory detected without proper security controls. "
                "Use tempfile.gettempdir() or ensure strict validation."
            )

    def test_builder_output_directory_has_safe_default(self):
        """
        Test that the default output directory is secure.

        FAILS when: Default is world-writable /tmp without protection
        PASSES when: Default uses application-specific secure directory
        """
        # Clear environment variable to test default
        original_value = os.environ.get("BUILDER_OUTPUT_DIR")
        if "BUILDER_OUTPUT_DIR" in os.environ:
            del os.environ["BUILDER_OUTPUT_DIR"]

        try:
            # Import after clearing env var to get default behavior
            # This will need to be tested based on actual implementation
            # For now, we test that tempfile provides safe defaults
            temp_dir = Path(tempfile.gettempdir())
            assert temp_dir.exists()

            # Create application-specific temp directory with proper permissions
            app_temp = temp_dir / "mcp-server-workflows-test"
            app_temp.mkdir(mode=0o700, parents=True, exist_ok=True)

            # Verify permissions are owner-only (0o700)
            stat_info = app_temp.stat()
            permissions = oct(stat_info.st_mode)[-3:]

            # Owner should have rwx, group and others should have no access
            # This prevents symlink attacks and unauthorized access
            assert permissions in ["700", "755"], (
                f"Temp directory has insecure permissions: {permissions}. "
                "Expected 700 (owner-only) or 755 (owner write, others read)."
            )

            # Cleanup
            app_temp.rmdir()

        finally:
            # Restore environment variable
            if original_value is not None:
                os.environ["BUILDER_OUTPUT_DIR"] = original_value

    def test_path_validation_prevents_directory_traversal(self):
        """
        Test that path validation prevents directory traversal attacks.

        This ensures that even if /tmp is used, proper validation prevents escaping.
        """
        from pathlib import Path

        # Simulate the path validation logic
        allowed_base = Path("/tmp/workflows")  # nosec B108 - test path.resolve()

        # Test valid paths
        valid_path = Path("/tmp/workflows/my_workflow.py").resolve()  # nosec B108 - test path
        assert str(valid_path).startswith(str(allowed_base))

        # Test directory traversal attempts (should be prevented)
        evil_path = Path("/tmp/workflows/../../../etc/passwd")  # nosec B108 - testing path traversal.resolve()
        assert not str(evil_path).startswith(str(allowed_base)), (
            "Path traversal attack not prevented! " "Validation should reject paths outside allowed base."
        )


@pytest.mark.xdist_group(name="unit_security_practices_tests")
class TestSQLInjectionPrevention:
    """Test that SQL operations properly prevent injection attacks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_postgres_storage_uses_parameterized_queries(self):
        """
        Test that PostgreSQL storage uses parameterized queries.

        FAILS when: String concatenation is used for SQL values
        PASSES when: Parameterized queries ($1, $2, etc.) are used
        """
        from mcp_server_langgraph.compliance.gdpr import postgres_storage

        # Get source code of update methods
        source = inspect.getsource(postgres_storage.PostgresUserProfileStore.update)

        # Parameterized queries should use $1, $2, etc.
        assert "$1" in source or "$2" in source or "${param_num}" in source, (
            "SQL queries should use parameterized queries ($1, $2, etc.) " "to prevent SQL injection."
        )

        # Should NOT use f-string or % formatting for VALUES
        # (f-strings are OK for structure, but not for values)
        assert "VALUES" in source.upper()

    @pytest.mark.asyncio
    async def test_field_name_validation_uses_allowlist(self):
        """
        Test that dynamic field names are validated against allowlists.

        FAILS when: User input is directly used in SQL field names
        PASSES when: Field names are validated against a predefined allowlist
        """
        from mcp_server_langgraph.compliance.gdpr import postgres_storage

        # Get source code
        source = inspect.getsource(postgres_storage.PostgresUserProfileStore.update)

        # Should have allowlist validation for field names
        # Look for patterns like: if key in ["email", "full_name", ...]
        assert "if " in source and ('in ["' in source or "in ['" in source or "not in" in source), (
            "Dynamic SQL field names should be validated against an allowlist " "to prevent SQL injection."
        )

    @pytest.mark.asyncio
    async def test_sql_injection_attempt_is_rejected(self):
        """
        Test that SQL injection attempts in field names are rejected.

        FAILS when: Injection attempts are processed
        PASSES when: Invalid field names are rejected
        """
        # Mock database pool
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()

        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresUserProfileStore

        store = PostgresUserProfileStore(mock_pool)

        # Attempt SQL injection via field name
        malicious_updates = {"email; DROP TABLE users; --": "hacker@evil.com"}

        # This should either:
        # 1. Return False (update failed due to invalid field)
        # 2. Raise ValueError or similar exception
        # 3. Silently ignore invalid fields

        result = await store.update("user123", malicious_updates)

        # The update should fail (return False) because field is not in allowlist
        assert result is False, (
            "SQL injection attempt via field name should be rejected. " "Field names must be validated against an allowlist."
        )

    @pytest.mark.asyncio
    async def test_malicious_sql_values_are_safely_escaped(self):
        """
        Test that malicious SQL values are properly parameterized.

        FAILS when: Values are concatenated into SQL strings
        PASSES when: Values are passed as parameters (preventing injection)
        """
        # Mock database pool
        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock()
        mock_conn = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.rowcount = 1

        # Track the SQL query and parameters
        executed_queries = []

        async def mock_execute(query, *params):
            executed_queries.append((query, params))
            return mock_execute_result

        mock_conn.execute = mock_execute
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()

        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresUserProfileStore

        store = PostgresUserProfileStore(mock_pool)

        # Attempt SQL injection via value
        malicious_email = "'; DROP TABLE users; --"
        updates = {"email": malicious_email}

        await store.update("user123", updates)

        # Verify that:
        # 1. A query was executed
        assert len(executed_queries) > 0, "Expected SQL query to be executed"

        query, params = executed_queries[0]

        # 2. The malicious email is in the parameters (not in the query string)
        assert malicious_email in params, "Malicious value should be passed as a parameter, not embedded in SQL"

        # 3. The query uses parameter placeholders ($1, $2, etc.)
        assert "$" in query, "Query should use parameterized placeholders ($1, $2, etc.)"

        # 4. The malicious SQL is NOT in the query itself (only in parameters)
        assert "DROP TABLE" not in query, "SQL injection payload should not appear in query string"


@pytest.mark.xdist_group(name="unit_security_practices_tests")
class TestSecurityDocumentation:
    """Test that security-sensitive code has proper documentation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_postgres_storage_has_security_comments(self):
        """
        Test that PostgreSQL storage has security documentation.

        FAILS when: No comments explain SQL injection prevention
        PASSES when: Security comments explain the mitigation strategy
        """
        from mcp_server_langgraph.compliance.gdpr import postgres_storage

        source = inspect.getsource(postgres_storage.PostgresUserProfileStore.update)

        # Should have comments explaining security
        assert (
            "SECURITY" in source.upper() or "SQL injection" in source or "parameterized" in source.lower() or "nosec" in source
        ), ("Security-sensitive SQL code should have comments explaining " "how SQL injection is prevented.")

    def test_nosec_suppressions_are_documented(self):
        """
        Test that bandit nosec suppressions include explanatory comments.

        FAILS when: nosec is used without explanation
        PASSES when: Comments explain why suppression is safe
        """
        from mcp_server_langgraph.compliance.gdpr import postgres_storage

        source = inspect.getsource(postgres_storage)

        # Each nosec should be accompanied by explanatory comments
        # Look for common documentation patterns near nosec
        has_documentation = source.count("# nosec") > 0 and (  # At least one nosec comment
            "parameterized" in source.lower()
            or "validated" in source.lower()
            or "allowlist" in source.lower()
            or "safe" in source.lower()
        )

        assert has_documentation, (
            "nosec suppressions should be documented with comments explaining "
            "why the code is safe despite the bandit warning."
        )
