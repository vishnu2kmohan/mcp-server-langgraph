"""
OAuth 2.0 Device Authorization Grant (RFC 8628).

Provides headless/CLI authentication without user interaction on the client device.
The user authenticates via a browser on another device (e.g., phone, laptop).

Flow:
1. Client requests device code from authorization server
2. Server returns device_code, user_code, and verification URI
3. User visits verification URI and enters user_code
4. Client polls token endpoint until authorization completes
5. Client receives access token

Usage:
    from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

    client = DeviceAuthClient(
        server_url="https://keycloak.example.com",
        realm="mcp-server",
        client_id="mcp-cli",
    )

    # Step 1: Request device code
    device_response = await client.request_device_code()
    print(f"Visit {device_response['verification_uri']}")
    print(f"Enter code: {device_response['user_code']}")

    # Step 2: Wait for user authorization
    tokens = await client.wait_for_authorization(
        device_response['device_code'],
        interval=device_response['interval'],
    )

    # tokens contains access_token, refresh_token, etc.

References:
- RFC 8628: OAuth 2.0 Device Authorization Grant
  https://datatracker.ietf.org/doc/rfc8628/
- Keycloak Device Authorization Grant
  https://www.keycloak.org/docs/latest/securing_apps/#device-authorization-grant
"""

import asyncio
from typing import Any, cast

import httpx

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


# Error classes for device authorization flow (RFC 8628 Section 3.5)
class DeviceAuthError(Exception):
    """Base exception for device authorization errors."""

    pass


class AuthorizationPending(DeviceAuthError):
    """Authorization is pending - user has not yet completed authorization."""

    pass


class SlowDown(DeviceAuthError):
    """Client is polling too frequently - should increase polling interval."""

    pass


class ExpiredToken(DeviceAuthError):
    """Device code has expired - user did not complete authorization in time."""

    pass


class AccessDenied(DeviceAuthError):
    """User denied the authorization request."""

    pass


class DeviceAuthClient:
    """
    OAuth 2.0 Device Authorization Grant client.

    Implements RFC 8628 for headless/CLI authentication flows.
    Designed for integration with Keycloak but works with any
    RFC 8628-compliant authorization server.
    """

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: str | None = None,
        device_authorization_endpoint: str | None = None,
        token_endpoint: str | None = None,
        scope: str = "openid profile email",
        polling_interval: int = 5,
        timeout: int = 300,
        verify_ssl: bool = True,
    ) -> None:
        """
        Initialize device authorization client.

        Args:
            server_url: Keycloak server URL (e.g., https://keycloak.example.com)
            realm: Keycloak realm name
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret (optional for public clients)
            device_authorization_endpoint: Device auth endpoint (auto-derived if not provided)
            token_endpoint: Token endpoint (auto-derived if not provided)
            scope: OAuth2 scopes to request
            polling_interval: Default polling interval in seconds
            timeout: Default timeout for authorization flow in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.polling_interval = polling_interval
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Build endpoints if not provided
        realm_url = f"{self.server_url}/realms/{self.realm}"
        self.device_authorization_endpoint = (
            device_authorization_endpoint or f"{realm_url}/protocol/openid-connect/auth/device"
        )
        self.token_endpoint = token_endpoint or f"{realm_url}/protocol/openid-connect/token"

    async def request_device_code(self) -> dict[str, Any]:
        """
        Request device code from authorization server.

        Returns:
            Dict with:
                - device_code: Code for client to use in polling
                - user_code: Code for user to enter in browser
                - verification_uri: URL for user to visit
                - verification_uri_complete: URL with user_code embedded (for QR codes)
                - expires_in: Validity period in seconds
                - interval: Polling interval in seconds

        Raises:
            httpx.HTTPError: If request fails
        """
        with tracer.start_as_current_span("device_auth.request_device_code"):
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30) as client:
                data = {
                    "client_id": self.client_id,
                    "scope": self.scope,
                }

                if self.client_secret:
                    data["client_secret"] = self.client_secret

                response = await client.post(self.device_authorization_endpoint, data=data)
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "Device code requested",
                    extra={
                        "user_code": result.get("user_code"),
                        "expires_in": result.get("expires_in"),
                    },
                )

                metrics.successful_calls.add(1, {"operation": "request_device_code"})

                return cast(dict[str, Any], result)

    async def poll_for_token(self, device_code: str) -> dict[str, Any]:
        """
        Poll token endpoint for authorization result.

        This method should be called repeatedly until it returns tokens
        or raises a terminal error (ExpiredToken, AccessDenied).

        Args:
            device_code: Device code from request_device_code()

        Returns:
            Token response with access_token, refresh_token, etc.

        Raises:
            AuthorizationPending: User has not yet completed authorization
            SlowDown: Client should increase polling interval
            ExpiredToken: Device code has expired
            AccessDenied: User denied authorization
        """
        with tracer.start_as_current_span("device_auth.poll_for_token"):
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30) as client:
                data = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": self.client_id,
                }

                if self.client_secret:
                    data["client_secret"] = self.client_secret

                response = await client.post(self.token_endpoint, data=data)

                # Handle error responses (RFC 8628 Section 3.5)
                if response.status_code == 400:
                    error_body = response.json()
                    error_code = error_body.get("error", "")

                    if error_code == "authorization_pending":
                        raise AuthorizationPending()
                    elif error_code == "slow_down":
                        raise SlowDown()
                    elif error_code == "expired_token":
                        raise ExpiredToken()
                    elif error_code == "access_denied":
                        raise AccessDenied()
                    else:
                        # Unknown error
                        error_desc = error_body.get("error_description", error_code)
                        raise DeviceAuthError(f"Token request failed: {error_desc}")

                response.raise_for_status()

                result = response.json()

                logger.info("Device authorization completed successfully")
                metrics.successful_calls.add(1, {"operation": "device_auth_complete"})

                return cast(dict[str, Any], result)

    async def wait_for_authorization(
        self,
        device_code: str,
        interval: float | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Wait for user to complete authorization.

        Polls the token endpoint at the specified interval until
        authorization is complete or times out.

        Args:
            device_code: Device code from request_device_code()
            interval: Polling interval in seconds (default: from constructor)
            timeout: Timeout in seconds (default: from constructor)

        Returns:
            Token response with access_token, refresh_token, etc.

        Raises:
            TimeoutError: User did not complete authorization in time
            ExpiredToken: Device code expired
            AccessDenied: User denied authorization
        """
        interval = interval or self.polling_interval
        timeout = timeout or self.timeout
        elapsed = 0.0

        with tracer.start_as_current_span("device_auth.wait_for_authorization"):
            while elapsed < timeout:
                try:
                    return await self.poll_for_token(device_code)
                except AuthorizationPending:
                    # User hasn't completed auth yet, keep polling
                    logger.debug(f"Authorization pending, waiting {interval}s...")
                except SlowDown:
                    # Increase polling interval
                    interval = interval + 5
                    logger.info(f"Server requested slow down, new interval: {interval}s")

                await asyncio.sleep(interval)
                elapsed += interval

            raise TimeoutError(f"Authorization timed out after {timeout} seconds")


def format_user_instructions(device_response: dict[str, Any]) -> str:
    """
    Format user-friendly instructions for device authorization.

    Args:
        device_response: Response from request_device_code()

    Returns:
        Formatted instructions string for display to user
    """
    verification_uri = device_response.get("verification_uri", "")
    user_code = device_response.get("user_code", "")
    expires_in = device_response.get("expires_in", 600)

    minutes = expires_in // 60

    return f"""
To authenticate, please:

1. Visit: {verification_uri}
2. Enter the code: {user_code}

This code expires in {minutes} minutes.
"""


def generate_qr_code(url: str) -> str:
    """
    Generate QR code as ASCII art for terminal display.

    Args:
        url: URL to encode in QR code (typically verification_uri_complete)

    Returns:
        QR code as ASCII art string

    Note:
        Requires 'qrcode' package to be installed.
        Install with: pip install qrcode[pil]
    """
    try:
        import io

        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create ASCII art
        output = io.StringIO()
        qr.print_ascii(out=output)
        return output.getvalue()

    except ImportError:
        logger.warning("qrcode package not installed, cannot generate QR code")
        return f"QR code not available. Please visit: {url}"
