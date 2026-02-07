"""
Unit tests for EgressValidator and RuntimeEgressValidator.

Tests network egress validation including SSRF protection via IP range blocking,
metadata hostname blocking, port allowlisting, DNS resolution, and TOCTOU prevention.
Following TDD best practices - these tests were written BEFORE the implementation.
"""

import gc
import socket
from unittest.mock import patch

import pytest

from mcp_server_langgraph.execution.sql.exceptions import EgressValidationError
from mcp_server_langgraph.network.egress_validator import (
    EgressValidator,
    RuntimeEgressValidator,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group("egress_validator"),
]


# ---------------------------------------------------------------------------
# Blocked IP ranges (RFC1918, link-local, loopback, IPv6 equivalents)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testegressvalidatorblockedranges")
class TestEgressValidatorBlockedRanges:
    """Verify that private/internal IP ranges are blocked."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    @pytest.mark.parametrize(
        "ip",
        [
            "10.0.0.1",
            "172.16.0.1",
            "192.168.0.1",
            "169.254.169.254",
            "127.0.0.1",
        ],
        ids=[
            "rfc1918-10-block",
            "rfc1918-172-block",
            "rfc1918-192-block",
            "link-local",
            "loopback",
        ],
    )
    def test_blocks_private_ipv4(self, validator, ip):
        """Private/internal IPv4 addresses must be blocked."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 5432))]
            allowed, reason = validator.validate_connection(ip, 5432)
            assert not allowed
            assert "blocked" in reason.lower() or "private" in reason.lower() or "internal" in reason.lower()

    @pytest.mark.parametrize(
        "ip",
        [
            "::1",
            "fe80::1",
            "fc00::1",
            "::ffff:169.254.169.254",
            "::ffff:10.0.0.1",
        ],
        ids=[
            "ipv6-loopback",
            "ipv6-link-local",
            "ipv6-unique-local",
            "ipv4-mapped-link-local",
            "ipv4-mapped-rfc1918",
        ],
    )
    def test_blocks_private_ipv6(self, validator, ip):
        """Private/internal IPv6 addresses (including IPv4-mapped) must be blocked."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", (ip, 5432, 0, 0))]
            allowed, reason = validator.validate_connection(ip, 5432)
            assert not allowed
            assert "blocked" in reason.lower() or "private" in reason.lower() or "internal" in reason.lower()


# ---------------------------------------------------------------------------
# Blocked metadata hostnames
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testegressvalidatormetadata")
class TestEgressValidatorMetadata:
    """Verify that cloud metadata service hostnames are blocked."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    @pytest.mark.parametrize(
        "hostname",
        [
            "metadata.google.internal",
            "metadata.goog",
            "169.254.169.254",
            "fd00:ec2::254",
        ],
        ids=[
            "gce-metadata-internal",
            "gce-metadata-goog",
            "aws-metadata-ipv4",
            "aws-metadata-ipv6",
        ],
    )
    def test_blocks_metadata_hostname(self, validator, hostname):
        """Cloud metadata service hostnames must be blocked before DNS resolution."""
        allowed, reason = validator.validate_connection(hostname, 443)
        assert not allowed
        assert "blocked" in reason.lower() or "metadata" in reason.lower()


# ---------------------------------------------------------------------------
# Port allowlist
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testegressvalidatorports")
class TestEgressValidatorPorts:
    """Verify port allowlist enforcement."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    @pytest.mark.parametrize(
        "port",
        [5432, 3306, 443, 5439, 8123, 8080, 9440],
        ids=["postgres", "mysql", "https", "redshift", "clickhouse", "trino", "snowflake"],
    )
    def test_allows_database_ports(self, validator, port):
        """Allowed database/service ports must pass port validation."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", port))]
            allowed, reason = validator.validate_connection("db.example.com", port)
            assert allowed, f"Port {port} should be allowed but got: {reason}"

    @pytest.mark.parametrize(
        "port",
        [22, 80, 3000, 8888],
        ids=["ssh", "http", "dev-server", "jupyter"],
    )
    def test_blocks_disallowed_ports(self, validator, port):
        """Non-allowlisted ports must be blocked."""
        allowed, reason = validator.validate_connection("db.example.com", port)
        assert not allowed
        assert "port" in reason.lower()


# ---------------------------------------------------------------------------
# Host allowlist
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testegressvalidatorallowlist")
class TestEgressValidatorAllowlist:
    """Verify host allowlist enforcement."""

    def teardown_method(self):
        gc.collect()

    def test_allows_host_in_allowlist(self):
        """When allowlist is configured, hosts in the list should be allowed."""
        validator = EgressValidator(allowed_hosts={"db.example.com", "analytics.corp.net"})
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.1", 5432))]
            allowed, reason = validator.validate_connection("db.example.com", 5432)
            assert allowed, f"Host in allowlist should be allowed but got: {reason}"

    def test_blocks_host_not_in_allowlist(self):
        """When allowlist is configured, hosts NOT in the list should be blocked."""
        validator = EgressValidator(allowed_hosts={"db.example.com"})
        allowed, reason = validator.validate_connection("evil.example.com", 5432)
        assert not allowed
        assert "allowlist" in reason.lower() or "allowed" in reason.lower()

    def test_production_requires_allowlist(self):
        """In production mode, connections require an allowlist to be configured."""
        validator = EgressValidator(
            allowed_hosts=None,
            require_allowlist_in_production=True,
        )
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            allowed, reason = validator.validate_connection("db.example.com", 5432)
            assert not allowed
            assert "allowlist" in reason.lower() or "production" in reason.lower()

    @pytest.mark.parametrize(
        "env_value",
        ["prod", "staging"],
        ids=["prod-alias", "staging"],
    )
    def test_prod_staging_also_require_allowlist(self, env_value):
        """Both 'prod' and 'staging' environments must enforce allowlist."""
        validator = EgressValidator(
            allowed_hosts=None,
            require_allowlist_in_production=True,
        )
        with patch.dict("os.environ", {"ENVIRONMENT": env_value}):
            allowed, reason = validator.validate_connection("db.example.com", 5432)
            assert not allowed
            assert "allowlist" in reason.lower() or "production" in reason.lower()


# ---------------------------------------------------------------------------
# DNS resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testegressvalidatordns")
class TestEgressValidatorDNS:
    """Verify DNS resolution handling."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    def test_dns_failure_blocks_connection(self, validator):
        """DNS resolution failure must block the connection."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror("Name resolution failed")
            allowed, reason = validator.validate_connection("nonexistent.example.com", 5432)
            assert not allowed
            assert "dns" in reason.lower() or "resolve" in reason.lower()

    def test_public_ip_passes(self, validator):
        """A public IP address should pass validation."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.50", 5432))]
            allowed, reason = validator.validate_connection("db.example.com", 5432)
            assert allowed


# ---------------------------------------------------------------------------
# validate_and_resolve (TOCTOU prevention)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testegressvalidatorresolve")
class TestEgressValidatorResolve:
    """Verify validate_and_resolve returns IPs and prevents TOCTOU."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    def test_validate_and_resolve_returns_ips(self, validator):
        """validate_and_resolve should return validated IP addresses."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.50", 5432)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.51", 5432)),
            ]
            allowed, reason, ips = validator.validate_and_resolve("db.example.com", 5432)
            assert allowed
            assert "203.0.113.50" in ips
            assert "203.0.113.51" in ips

    def test_validate_and_resolve_single_dns_call(self, validator):
        """DNS must be resolved exactly once to prevent TOCTOU attacks."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.50", 5432))]
            allowed, reason, ips = validator.validate_and_resolve("db.example.com", 5432)
            assert allowed
            assert mock_dns.call_count == 1

    def test_validate_and_resolve_blocks_private_ip(self, validator):
        """validate_and_resolve must block if any resolved IP is private."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 5432))]
            allowed, reason, ips = validator.validate_and_resolve("sneaky.example.com", 5432)
            assert not allowed
            assert len(ips) == 0


# ---------------------------------------------------------------------------
# RuntimeEgressValidator (async wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testruntimeegressvalidator")
class TestRuntimeEgressValidator:
    """Verify async RuntimeEgressValidator behavior."""

    def teardown_method(self):
        gc.collect()

    @pytest.fixture
    def validator(self):
        return EgressValidator()

    @pytest.fixture
    def runtime_validator(self, validator):
        return RuntimeEgressValidator(validator)

    async def test_validate_before_connect_success(self, runtime_validator):
        """Successful validation returns (ip, '')."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.50", 5432))]
            ip, msg = await runtime_validator.validate_before_connect("db.example.com", 5432)
            assert ip == "203.0.113.50"
            assert msg == ""

    async def test_validate_before_connect_failure_raises(self, runtime_validator):
        """Failed validation raises EgressValidationError."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 5432))]
            with pytest.raises(EgressValidationError):
                await runtime_validator.validate_before_connect("evil.internal", 5432)

    async def test_validate_before_connect_blocked_port_raises(self, runtime_validator):
        """Blocked port raises EgressValidationError."""
        with pytest.raises(EgressValidationError):
            await runtime_validator.validate_before_connect("db.example.com", 22)
