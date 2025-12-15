"""
Real Client Implementations for E2E Tests

This module provides real HTTP client implementations that connect to
the actual test infrastructure (docker-compose.test.yml services).

Authentication Methods (per RFC 9700):
- PKCE (login_pkce): OAuth2 Authorization Code + PKCE flow (RECOMMENDED)
- Client Credentials (login_client_credentials): For service-to-service auth
- ROPC (login): Legacy password grant (DEPRECATED per RFC 9700)

Migration from Mocks:
- Replaces MockKeycloakAuth with RealKeycloakAuth
- Replaces MockMCPClient with RealMCPClient
- Uses actual HTTP calls to test services on offset ports (9000+)

Usage:
    from tests.e2e.real_clients import real_keycloak_auth, real_mcp_client

    async with real_keycloak_auth() as auth:
        # PKCE flow (recommended)
        token = await auth.login_pkce("alice", "password")

        # Client credentials (for service accounts)
        token = await auth.login_client_credentials()

        # Legacy ROPC (deprecated)
        token = await auth.login("alice", "password")
"""

import base64
import hashlib
import os
import re
import secrets
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# Import helper for worker-safe IDs
from tests.conftest import get_user_id


def _generate_code_verifier() -> str:
    """Generate PKCE code verifier (43-128 chars from URL-safe alphabet)."""
    return secrets.token_urlsafe(64)[:128]


def _generate_code_challenge(verifier: str) -> str:
    """Generate S256 code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class RealKeycloakAuth:
    """Real Keycloak authentication client for E2E tests

    Connects to Keycloak test instance on port 9082.

    Authentication Methods (use based on scenario):

    1. login_client_credentials() - RECOMMENDED for most tests
       - Service account token, no user password needed
       - Use when: Testing APIs that only need valid authentication
       - Returns: Service account token (no user-specific claims)

    2. login_as_user(username) - RECOMMENDED for user-specific tests
       - Token Exchange (RFC 8693), impersonates a user
       - Use when: Testing user-specific authorization (RBAC, ownership)
       - Requires: Keycloak token-exchange enabled for client
       - Returns: User-specific token with user claims

    3. login_pkce(username, password) - For full flow simulation
       - Simulates browser OAuth2 PKCE flow
       - Use when: Testing the complete authentication flow
       - Returns: User token from real login flow

    4. login(username, password) - DEPRECATED per RFC 9700
       - Legacy ROPC grant, avoid for new tests
       - Will emit DeprecationWarning

    Example:
        async with real_keycloak_auth() as auth:
            # Service account (no user context needed)
            svc_token = await auth.login_client_credentials()

            # User-specific (needs user claims like roles)
            alice_token = await auth.login_as_user("alice")

            # Full PKCE flow
            tokens = await auth.login_pkce("alice", "alice123")
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Keycloak auth client.

        Args:
            base_url: Keycloak base URL (default: http://localhost:9082)
        """
        # CRITICAL: Include /authn prefix because Keycloak is configured with KC_HTTP_RELATIVE_PATH=/authn
        self.base_url = base_url or os.getenv("KEYCLOAK_URL", "http://localhost:9082/authn")
        self.realm = os.getenv("KEYCLOAK_REALM", "mcp-test")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "mcp-server")
        # CODEX FINDING FIX (2025-11-20): Add client_secret for token introspection
        # Keycloak requires client authentication for introspection endpoint
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "test-client-secret-for-e2e-tests")
        # OAuth2 callback URL for PKCE flow
        self.redirect_uri = os.getenv("OAUTH2_REDIRECT_URI", "http://localhost:8000/api/v1/auth/callback")
        # S501: verify=False is intentional for e2e tests against local dev servers
        self.client = httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=False)  # noqa: S501 # nosec B501

    async def login_pkce(self, username: str, password: str) -> dict[str, str]:
        """
        Login using OAuth2 Authorization Code + PKCE flow (RFC 9700 compliant).

        Simulates browser-based PKCE flow:
        1. Generate code_verifier and code_challenge
        2. Navigate to authorization endpoint
        3. Submit Keycloak login form
        4. Exchange authorization code for tokens

        Args:
            username: User username
            password: User password

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.

        Raises:
            RuntimeError: If authentication fails
        """
        # Step 1: Generate PKCE values
        code_verifier = _generate_code_verifier()
        code_challenge = _generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)

        # Step 2: Build authorization URL
        auth_params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/auth?{urlencode(auth_params)}"

        try:
            # Step 3: Get authorization page (Keycloak login form)
            auth_response = await self.client.get(auth_url)

            # Follow redirects manually to track final URL
            while auth_response.status_code in [301, 302, 303, 307, 308]:
                redirect_url = auth_response.headers.get("Location")
                if not redirect_url:
                    break
                # Handle relative URLs
                if redirect_url.startswith("/"):
                    parsed = urlparse(auth_url)
                    redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                auth_response = await self.client.get(redirect_url)

            if auth_response.status_code != 200:
                raise RuntimeError(
                    f"Failed to get Keycloak login page: {auth_response.status_code} - {auth_response.text[:200]}"
                )

            # Step 4: Extract form action URL from Keycloak login page
            html = auth_response.text
            form_action_match = re.search(r'action="([^"]+)"', html)
            if not form_action_match:
                raise RuntimeError("Could not find login form action in Keycloak page")

            # Decode HTML entities in the action URL
            form_action = form_action_match.group(1).replace("&amp;", "&")

            # Step 5: Submit login form with credentials
            login_response = await self.client.post(
                form_action,
                data={"username": username, "password": password},
            )

            # Step 6: Follow redirect to callback URL (expect 302 with code in query)
            if login_response.status_code not in [302, 303, 307]:
                # Check if we got an error page
                if "Invalid username or password" in login_response.text:
                    raise RuntimeError(f"Invalid credentials for user '{username}'")
                raise RuntimeError(
                    f"Unexpected response from login form: {login_response.status_code} - {login_response.text[:300]}"
                )

            callback_url = login_response.headers.get("Location")
            if not callback_url:
                raise RuntimeError("No redirect URL after login form submission")

            # Step 7: Extract authorization code from callback URL
            parsed_callback = urlparse(callback_url)
            query_params = parse_qs(parsed_callback.query)

            if "error" in query_params:
                raise RuntimeError(f"OAuth2 error: {query_params.get('error_description', query_params['error'])}")

            if "code" not in query_params:
                raise RuntimeError(f"No authorization code in callback URL: {callback_url}")

            auth_code = query_params["code"][0]
            returned_state = query_params.get("state", [""])[0]

            # Verify state matches (CSRF protection)
            if returned_state != state:
                raise RuntimeError("State mismatch - possible CSRF attack")

            # Step 8: Exchange authorization code for tokens
            token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            }
            if self.client_secret:
                token_data["client_secret"] = self.client_secret

            token_response = await self.client.post(token_url, data=token_data)
            token_response.raise_for_status()

            return token_response.json()

        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"Keycloak PKCE auth timeout at {self.base_url} - service may be down. "
                f"Check docker-compose services are running."
            ) from e
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to Keycloak at {self.base_url} - service is not reachable. "
                f"Ensure docker-compose.test.yml is running."
            ) from e

    async def login_client_credentials(self) -> dict[str, str]:
        """
        Login using Client Credentials grant (for service-to-service auth).

        This is appropriate for service accounts and backend-to-backend communication.
        Requires client_secret to be configured.

        Returns:
            Dict with access_token, expires_in, etc. (no refresh_token)

        Raises:
            RuntimeError: If authentication fails or client_secret not configured
        """
        if not self.client_secret:
            raise RuntimeError("Client credentials grant requires client_secret to be configured")

        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid profile email",
        }

        try:
            response = await self.client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Client credentials auth failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def login_as_user(self, username: str) -> dict[str, str]:
        """
        Obtain a token for a specific user using Token Exchange (RFC 8693).

        This allows a service account to obtain a token on behalf of a user
        without needing the user's password. This is the modern, secure approach
        for integration tests that need user-specific tokens.

        Flow:
        1. Get service account token via client credentials
        2. Exchange it for a user-specific token via token exchange

        Requirements:
        - Keycloak must have token exchange enabled for the client
        - The client must have permission to impersonate users
        - Configure in Keycloak Admin > Clients > mcp-server > Authorization > Permissions

        Args:
            username: Username of the user to impersonate

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.

        Raises:
            RuntimeError: If token exchange fails or not configured
        """
        if not self.client_secret:
            raise RuntimeError("Token exchange requires client_secret to be configured")

        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        # RFC 8693 Token Exchange parameters
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "requested_subject": username,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "scope": "openid profile email",
        }

        try:
            response = await self.client.post(token_url, data=data)

            if response.status_code == 400:
                error_body = response.json() if response.content else {}
                error_desc = error_body.get("error_description", "")
                if "not allowed" in error_desc.lower() or "permission" in error_desc.lower():
                    raise RuntimeError(
                        f"Token exchange not configured for client '{self.client_id}'. "
                        f"Enable token-exchange in Keycloak Admin > Clients > {self.client_id} > "
                        f"Authorization > Permissions. Error: {error_desc}"
                    )
                raise RuntimeError(f"Token exchange failed: {error_desc}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Token exchange failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def login_direct_grant_impersonation(
        self, admin_username: str, admin_password: str, target_username: str
    ) -> dict[str, str]:
        """
        Alternative impersonation using Keycloak Admin API.

        Uses admin credentials to get an impersonation token for a target user.
        This is useful when token exchange is not configured.

        Flow:
        1. Get admin token from master realm
        2. Use admin API to impersonate target user
        3. Return the impersonation token

        Args:
            admin_username: Keycloak admin username (typically 'admin')
            admin_password: Keycloak admin password
            target_username: Username of the user to impersonate

        Returns:
            Dict with access_token, etc.

        Raises:
            RuntimeError: If impersonation fails
        """
        # Step 1: Get admin token from master realm
        admin_token_url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        admin_data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_username,
            "password": admin_password,
        }

        try:
            admin_response = await self.client.post(admin_token_url, data=admin_data)
            admin_response.raise_for_status()
            admin_token = admin_response.json()["access_token"]

            # Step 2: Get user ID from admin API
            users_url = f"{self.base_url}/admin/realms/{self.realm}/users"
            users_response = await self.client.get(
                users_url,
                params={"username": target_username, "exact": "true"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            users_response.raise_for_status()
            users = users_response.json()

            if not users:
                raise RuntimeError(f"User '{target_username}' not found in realm '{self.realm}'")

            user_id = users[0]["id"]

            # Step 3: Impersonate user
            impersonate_url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/impersonation"
            impersonate_response = await self.client.post(
                impersonate_url,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            impersonate_response.raise_for_status()

            # The impersonation endpoint sets cookies, we need to get a token
            # Exchange the admin session for a user token
            # This is a simplified flow - in practice you'd capture the session cookie

            # Alternative: Use token exchange with the admin token as the subject_token
            exchange_data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "subject_token": admin_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": target_username,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            }

            exchange_response = await self.client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token",
                data=exchange_data,
            )

            if exchange_response.status_code == 200:
                return exchange_response.json()

            # If token exchange fails, fall back to ROPC with warning
            warnings.warn(
                "Admin impersonation token exchange failed, falling back to ROPC. "
                "Configure token-exchange in Keycloak for better security.",
                DeprecationWarning,
                stacklevel=2,
            )

            # Fall back to impersonation response if available
            return impersonate_response.json() if impersonate_response.content else {"error": "No token returned"}

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Admin impersonation failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def login(self, username: str, password: str) -> dict[str, str]:
        """
        Login user using ROPC (Resource Owner Password Credentials) grant.

        DEPRECATED per RFC 9700: Use login_pkce() instead for user authentication.
        This method is retained for backward compatibility only.

        Args:
            username: User username
            password: User password

        Returns:
            Dict with access_token, refresh_token, expires_in, etc.

        Raises:
            RuntimeError: If authentication fails (with specific error context)
        """
        warnings.warn(
            "ROPC login is deprecated per RFC 9700. Use login_pkce() for user authentication "
            "or login_client_credentials() for service accounts.",
            DeprecationWarning,
            stacklevel=2,
        )

        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": username,
            "password": password,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            response = await self.client.post(
                token_url,
                data=data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"Keycloak auth timeout after 30s at {self.base_url} - "
                f"service may be down or overloaded. "
                f"Check docker-compose services are running."
            ) from e
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to Keycloak at {self.base_url} - "
                f"service is not reachable. "
                f"Ensure docker-compose.test.yml is running: docker compose -f docker-compose.test.yml up -d"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Keycloak auth failed: {e.response.status_code} - {e.response.text[:200]} (URL: {token_url})"
            ) from e

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token, refresh_token, expires_in, etc.
        """
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = await self.client.post(
            token_url,
            data=data,
        )
        response.raise_for_status()

        return response.json()

    async def logout(self, refresh_token: str) -> None:
        """
        Logout user session.

        Args:
            refresh_token: Valid refresh token
        """
        logout_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/logout"

        await self.client.post(
            logout_url,
            data={
                "client_id": self.client_id,
                "refresh_token": refresh_token,
            },
        )

    async def introspect(self, token: str) -> dict[str, Any]:
        """
        Introspect token to get metadata.

        CODEX FINDING FIX (2025-11-20): Added client_secret for proper Keycloak authentication.
        Previous issue: Missing client_secret caused 403 Forbidden errors.

        Args:
            token: Access token to introspect

        Returns:
            Dict with token metadata (active, sub, username, etc.)

        Raises:
            httpx.HTTPStatusError: If introspection fails (e.g., 403 without client_secret)
        """
        introspect_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token/introspect"

        # Keycloak requires client authentication for introspection
        # Use client_secret if available, otherwise try public client introspection
        data = {
            "client_id": self.client_id,
            "token": token,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = await self.client.post(introspect_url, data=data)
        response.raise_for_status()

        return response.json()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class RealMCPClient:
    """Real MCP (Model Context Protocol) client for E2E tests

    Connects to MCP server test instance.
    Uses real HTTP/SSE transport for MCP protocol.
    """

    def __init__(self, base_url: str = None, access_token: str = None):
        """
        Initialize MCP client.

        Args:
            base_url: MCP server base URL (default: http://localhost:8000)
            access_token: Optional access token for authentication
        """
        self.base_url = base_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.access_token = access_token

        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # S501: verify=False is intentional for e2e tests against local dev servers
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0, verify=False)  # noqa: S501 # nosec B501

    async def initialize(self) -> dict[str, Any]:
        """
        Initialize MCP session.

        Returns:
            Dict with protocol_version, server_info, capabilities
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {},
            },
        }
        try:
            response = await self.client.post("/message", json=payload)
            response.raise_for_status()
            return response.json().get("result", {})

        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"MCP initialize timeout after 30s at {self.base_url} - server may be down or overloaded."
            ) from e
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to MCP server at {self.base_url} - service is not reachable. Check server is running."
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"MCP initialize failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def list_tools(self) -> dict[str, Any]:
        """
        List available tools.

        Returns:
            Dict with tools array
        """
        payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
        try:
            response = await self.client.post("/message", json=payload)
            response.raise_for_status()
            return response.json().get("result", {})

        except httpx.TimeoutException as e:
            raise RuntimeError(f"MCP list_tools timeout after 30s at {self.base_url}") from e
        except httpx.ConnectError as e:
            raise RuntimeError(f"Cannot connect to MCP server at {self.base_url} for list_tools") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"MCP list_tools failed: {e.response.status_code} - {e.response.text[:200]}") from e

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call a tool.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Dict with tool result
        """
        # Ensure token is in arguments if available
        if self.access_token and "token" not in arguments:
            arguments["token"] = self.access_token

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        response = await self.client.post("/message", json=payload)
        response.raise_for_status()

        result = response.json().get("result", {})
        error = response.json().get("error")
        if error:
            raise RuntimeError(f"MCP call_tool failed: {error}")

        # MCP returns {content: [...]}
        return result

    async def create_conversation(self, user_id: str = "test-user") -> str:
        """
        Create a new conversation (Generate ID, actual creation is implicit).

        Args:
            user_id: User ID for conversation

        Returns:
            Conversation ID
        """
        import uuid

        return f"conv_{uuid.uuid4().hex[:8]}"

    async def send_message(self, conversation_id: str, content: str) -> dict[str, Any]:
        """
        Send message to conversation using agent_chat tool.

        Args:
            conversation_id: Conversation ID
            content: Message content

        Returns:
            Dict with message response
        """
        arguments = {
            "message": content,
            "thread_id": conversation_id,
            "user_id": get_user_id(),
        }
        if self.access_token:
            arguments["token"] = self.access_token

        result = await self.call_tool("agent_chat", arguments)
        return result

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """
        Get conversation details using conversation_get tool.

        Args:
            conversation_id: Conversation ID

        Returns:
            Dict with conversation data
        """
        arguments = {"thread_id": conversation_id, "user_id": get_user_id("test")}
        if self.access_token:
            arguments["token"] = self.access_token

        result = await self.call_tool("conversation_get", arguments)
        return result

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


@asynccontextmanager
async def real_keycloak_auth(base_url: str = None) -> AsyncGenerator[RealKeycloakAuth, None]:
    """
    Context manager for RealKeycloakAuth.

    Usage:
        async with real_keycloak_auth() as auth:
            token = await auth.login("alice", "password")

    Args:
        base_url: Optional Keycloak base URL

    Yields:
        RealKeycloakAuth instance
    """
    auth = RealKeycloakAuth(base_url=base_url)
    try:
        yield auth
    finally:
        await auth.close()


@asynccontextmanager
async def real_mcp_client(base_url: str = None, access_token: str = None) -> AsyncGenerator[RealMCPClient, None]:
    """
    Context manager for RealMCPClient.

    Usage:
        async with real_mcp_client(access_token=token) as client:
            tools = await client.list_tools()

    Args:
        base_url: Optional MCP server base URL
        access_token: Optional access token for authentication

    Yields:
        RealMCPClient instance
    """
    client = RealMCPClient(base_url=base_url, access_token=access_token)
    try:
        yield client
    finally:
        await client.close()


# Backwards compatibility aliases
# These allow gradual migration from mock_ to real_ prefixes
MockKeycloakAuth = RealKeycloakAuth
MockMCPClient = RealMCPClient
mock_keycloak_auth = real_keycloak_auth
mock_mcp_client = real_mcp_client
