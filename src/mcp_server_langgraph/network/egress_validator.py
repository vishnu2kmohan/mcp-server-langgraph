"""Network egress validator for SSRF protection.

Validates outbound connections against blocked IP ranges, metadata hostnames,
port allowlists, and optional host allowlists. Provides TOCTOU-safe DNS
resolution via validate_and_resolve().

See ADR-0029 for exception hierarchy details.
"""

import asyncio
import ipaddress
import os
import socket

from mcp_server_langgraph.execution.sql.exceptions import EgressValidationError


class EgressValidator:
    """Validates network egress to prevent SSRF and internal network access.

    Checks in order:
    1. Port allowlist
    2. Hostname blocklist (cloud metadata services)
    3. Production allowlist requirement
    4. Host allowlist enforcement (if configured)
    5. DNS resolution + IP range validation
    """

    # RFC1918 + link-local + loopback + IPv6 equivalents + IPv4-mapped IPv6
    BLOCKED_RANGES = [
        # IPv4
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        # IPv6
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
        # IPv4-mapped IPv6
        ipaddress.ip_network("::ffff:10.0.0.0/104"),
        ipaddress.ip_network("::ffff:172.16.0.0/108"),
        ipaddress.ip_network("::ffff:192.168.0.0/112"),
        ipaddress.ip_network("::ffff:169.254.0.0/112"),
        ipaddress.ip_network("::ffff:127.0.0.0/104"),
    ]

    BLOCKED_HOSTNAMES = frozenset(
        {
            "metadata.google.internal",
            "metadata.goog",
            "169.254.169.254",
            "fd00:ec2::254",
        }
    )

    ALLOWED_PORTS = frozenset(
        {443, 1433, 1521, 3306, 5432, 5439, 6379, 8080, 8123, 9000, 9440, 27017}
    )  # 9000 = ClickHouse native protocol

    def __init__(
        self,
        allowed_hosts: set[str] | None = None,
        require_allowlist_in_production: bool = True,
    ) -> None:
        self._allowed_hosts = allowed_hosts
        self._require_allowlist_in_production = require_allowlist_in_production

    def _is_ip_blocked(self, ip_str: str) -> bool:
        """Check if an IP address falls within any blocked range."""
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            # If we cannot parse it, treat it as blocked for safety
            return True

        return any(addr in network for network in self.BLOCKED_RANGES)

    def _check_port(self, port: int) -> tuple[bool, str]:
        """Check if port is in the allowlist."""
        if port not in self.ALLOWED_PORTS:
            return False, f"Port {port} is not in the allowed port list: {sorted(self.ALLOWED_PORTS)}"
        return True, ""

    def _check_hostname_blocklist(self, host: str) -> tuple[bool, str]:
        """Check if hostname is in the metadata blocklist."""
        normalized = host.lower().strip()
        if normalized in self.BLOCKED_HOSTNAMES:
            return False, f"Hostname '{host}' is blocked (metadata service endpoint)"
        return True, ""

    def _check_production_allowlist(self) -> tuple[bool, str]:
        """Check if production environment requires an allowlist."""
        if self._require_allowlist_in_production and self._allowed_hosts is None:
            env = os.environ.get("ENVIRONMENT", "").lower()
            if env in {"production", "prod", "staging"}:
                return False, (
                    "Production environment requires an explicit host allowlist. "
                    "Configure allowed_hosts to permit connections."
                )
        return True, ""

    def _check_host_allowlist(self, host: str) -> tuple[bool, str]:
        """Check if host is in the configured allowlist."""
        if self._allowed_hosts is not None:
            normalized = host.lower().strip()
            if normalized not in {h.lower() for h in self._allowed_hosts}:
                return False, f"Host '{host}' is not in the allowed host list"
        return True, ""

    def _resolve_dns(self, host: str, port: int) -> tuple[bool, str, list[str]]:
        """Resolve DNS and validate all returned IPs."""
        try:
            results = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            return False, f"DNS resolution failed for '{host}': {exc}", []

        if not results:
            return False, f"DNS resolution returned no results for '{host}'", []

        ips: list[str] = []
        for family, socktype, proto, canonname, sockaddr in results:
            # sockaddr is (ip, port) for IPv4, (ip, port, flow, scope) for IPv6
            ip_str = sockaddr[0]
            if self._is_ip_blocked(ip_str):
                return (
                    False,
                    f"Resolved IP {ip_str} for '{host}' is in a blocked/private range",
                    [],
                )
            ips.append(ip_str)

        return True, "", ips

    def validate_connection(self, host: str, port: int) -> tuple[bool, str]:
        """Validate whether a connection to host:port is permitted.

        Checks are performed in order:
        1. Port allowlist
        2. Hostname blocklist
        3. Production allowlist requirement
        4. Host allowlist (if configured)
        5. DNS resolution + IP validation

        Args:
            host: Target hostname or IP address.
            port: Target port number.

        Returns:
            Tuple of (allowed, reason). If allowed is False, reason describes why.
        """
        # 1. Port check
        ok, reason = self._check_port(port)
        if not ok:
            return False, reason

        # 2. Hostname blocklist
        ok, reason = self._check_hostname_blocklist(host)
        if not ok:
            return False, reason

        # 3. Production allowlist requirement
        ok, reason = self._check_production_allowlist()
        if not ok:
            return False, reason

        # 4. Host allowlist
        ok, reason = self._check_host_allowlist(host)
        if not ok:
            return False, reason

        # 5. DNS resolution + IP validation
        ok, reason, _ips = self._resolve_dns(host, port)
        return ok, reason

    def validate_and_resolve(self, host: str, port: int) -> tuple[bool, str, list[str]]:
        """Validate connection and return resolved IPs for TOCTOU prevention.

        Same checks as validate_connection, but DNS is resolved exactly once
        and the validated IPs are returned so the caller can connect directly
        to the IP (bypassing a second DNS lookup that could return different results).

        Args:
            host: Target hostname or IP address.
            port: Target port number.

        Returns:
            Tuple of (allowed, reason, ips). If allowed is False, ips is empty.
        """
        # 1. Port check
        ok, reason = self._check_port(port)
        if not ok:
            return False, reason, []

        # 2. Hostname blocklist
        ok, reason = self._check_hostname_blocklist(host)
        if not ok:
            return False, reason, []

        # 3. Production allowlist requirement
        ok, reason = self._check_production_allowlist()
        if not ok:
            return False, reason, []

        # 4. Host allowlist
        ok, reason = self._check_host_allowlist(host)
        if not ok:
            return False, reason, []

        # 5. DNS resolution + IP validation (single call)
        return self._resolve_dns(host, port)


class RuntimeEgressValidator:
    """Async wrapper for EgressValidator to avoid blocking the event loop.

    Runs validate_and_resolve in an executor thread so that DNS resolution
    and IP validation do not block the asyncio event loop.
    """

    def __init__(self, validator: EgressValidator) -> None:
        self._validator = validator

    async def validate_before_connect(self, host: str, port: int) -> tuple[str, str]:
        """Validate egress and return (ip_to_use, "").

        Runs the synchronous validator in an executor to keep the event
        loop non-blocking.

        Args:
            host: Target hostname or IP address.
            port: Target port number.

        Returns:
            Tuple of (ip_to_use, ""). The first validated IP is returned.

        Raises:
            EgressValidationError: If validation fails for any reason.
        """
        loop = asyncio.get_running_loop()
        allowed, reason, ips = await loop.run_in_executor(
            None,
            self._validator.validate_and_resolve,
            host,
            port,
        )

        if not allowed:
            raise EgressValidationError(message=reason)

        return ips[0], ""
