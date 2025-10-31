"""
Keycloak integration for authentication and user management

Provides production-ready authentication using Keycloak as the identity provider.
Supports multiple authentication flows, token verification, and role/group mapping
to OpenFGA for fine-grained authorization.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import jwt
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class KeycloakUser(BaseModel):
    """Keycloak user model"""

    id: str = Field(description="Keycloak user ID (UUID)")
    username: str = Field(description="Username")
    email: Optional[str] = Field(default=None, description="Email address")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")
    enabled: bool = Field(default=True, description="Whether user account is enabled")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    realm_roles: List[str] = Field(default_factory=list, description="Realm-level roles")
    client_roles: Dict[str, List[str]] = Field(default_factory=dict, description="Client-specific roles")
    groups: List[str] = Field(default_factory=list, description="Group memberships")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes")

    @property
    def user_id(self) -> str:
        """Get user ID in format compatible with OpenFGA"""
        return f"user:{self.username}"

    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts) or self.username


class KeycloakConfig(BaseModel):
    """Keycloak configuration"""

    server_url: str = Field(description="Keycloak server URL (e.g., http://localhost:8180)")
    realm: str = Field(description="Keycloak realm name")
    client_id: str = Field(description="OAuth2/OIDC client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth2/OIDC client secret")
    admin_username: Optional[str] = Field(default=None, description="Admin username for admin API access")
    admin_password: Optional[str] = Field(default=None, description="Admin password for admin API access")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")

    @property
    def realm_url(self) -> str:
        """Get realm base URL"""
        return f"{self.server_url}/realms/{self.realm}"

    @property
    def admin_url(self) -> str:
        """Get admin API base URL"""
        return f"{self.server_url}/admin/realms/{self.realm}"

    @property
    def token_endpoint(self) -> str:
        """Get token endpoint URL"""
        return f"{self.realm_url}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get userinfo endpoint URL"""
        return f"{self.realm_url}/protocol/openid-connect/userinfo"

    @property
    def jwks_uri(self) -> str:
        """Get JWKS URI for public key retrieval"""
        return f"{self.realm_url}/protocol/openid-connect/certs"

    @property
    def well_known_url(self) -> str:
        """Get OpenID configuration URL"""
        return f"{self.realm_url}/.well-known/openid-configuration"


class TokenValidator:
    """JWT token validator using Keycloak JWKS"""

    def __init__(self, config: KeycloakConfig) -> None:
        self.config = config
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

    async def get_jwks(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get JSON Web Key Set from Keycloak

        Args:
            force_refresh: Force refresh of cached keys

        Returns:
            JWKS dictionary
        """
        with tracer.start_as_current_span("keycloak.get_jwks"):
            # Check cache
            if not force_refresh and self._jwks_cache and self._jwks_cache_time:
                if datetime.now(timezone.utc) - self._jwks_cache_time < self._cache_ttl:
                    logger.debug("Using cached JWKS")
                    return self._jwks_cache

            # Fetch from Keycloak
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                try:
                    response = await client.get(self.config.jwks_uri)
                    response.raise_for_status()
                    jwks = response.json()

                    # Cache the result
                    self._jwks_cache = jwks
                    self._jwks_cache_time = datetime.now(timezone.utc)

                    logger.info("JWKS fetched and cached", extra={"keys_count": len(jwks.get("keys", []))})
                    return jwks  # type: ignore[no-any-return]

                except httpx.HTTPError as e:
                    logger.error(f"Failed to fetch JWKS: {e}", exc_info=True)
                    metrics.failed_calls.add(1, {"operation": "get_jwks"})
                    raise

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token using Keycloak public keys

        Args:
            token: JWT access token

        Returns:
            Decoded token payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
        """
        with tracer.start_as_current_span("keycloak.verify_token") as span:
            try:
                # Decode header to get key ID
                unverified_header = jwt.get_unverified_header(token)
                kid = unverified_header.get("kid")

                if not kid:
                    raise jwt.InvalidTokenError("Token missing 'kid' in header")

                span.set_attribute("token.kid", kid)

                # Get JWKS
                jwks = await self.get_jwks()

                # Find matching key
                public_key = None
                for key_data in jwks.get("keys", []):
                    if key_data.get("kid") == kid:
                        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                        break

                if not public_key:
                    # Try refreshing JWKS in case keys were rotated
                    logger.warning(f"Key ID {kid} not found, refreshing JWKS")
                    jwks = await self.get_jwks(force_refresh=True)

                    for key_data in jwks.get("keys", []):
                        if key_data.get("kid") == kid:
                            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                            break

                if not public_key:
                    raise jwt.InvalidTokenError(f"Public key not found for kid: {kid}")

                # Verify and decode token
                payload = jwt.decode(
                    token,
                    public_key,  # type: ignore[arg-type]
                    algorithms=["RS256"],
                    audience=self.config.client_id,
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_aud": True,
                    },
                )

                span.set_attribute("token.sub", payload.get("sub"))
                span.set_attribute("token.preferred_username", payload.get("preferred_username"))

                logger.info(
                    "Token verified successfully",
                    extra={"sub": payload.get("sub"), "username": payload.get("preferred_username")},
                )

                metrics.successful_calls.add(1, {"operation": "verify_token"})

                return payload  # type: ignore[no-any-return]

            except jwt.ExpiredSignatureError:
                logger.warning("Token expired")
                metrics.auth_failures.add(1, {"reason": "expired_token"})
                raise
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token: {e}")
                metrics.auth_failures.add(1, {"reason": "invalid_token"})
                raise
            except Exception as e:
                logger.error(f"Token verification error: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "verify_token"})
                raise


class KeycloakClient:
    """
    Keycloak client for authentication and user management

    Provides methods for:
    - Token verification (OIDC)
    - User authentication (ROPC flow)
    - Token refresh
    - User info retrieval
    - Admin API operations
    """

    def __init__(self, config: KeycloakConfig) -> None:
        """
        Initialize Keycloak client

        Args:
            config: Keycloak configuration
        """
        self.config = config
        self.token_validator = TokenValidator(config)
        self._admin_token: Optional[str] = None
        self._admin_token_expiry: Optional[datetime] = None

    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user using Resource Owner Password Credentials (ROPC) flow

        Args:
            username: Username
            password: Password

        Returns:
            Token response with access_token, refresh_token, etc.

        Raises:
            httpx.HTTPError: If authentication fails
        """
        with tracer.start_as_current_span("keycloak.authenticate_user") as span:
            span.set_attribute("user.name", username)

            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                try:
                    data = {
                        "grant_type": "password",
                        "client_id": self.config.client_id,
                        "username": username,
                        "password": password,
                    }

                    if self.config.client_secret:
                        data["client_secret"] = self.config.client_secret

                    response = await client.post(self.config.token_endpoint, data=data)
                    response.raise_for_status()

                    tokens = response.json()

                    logger.info("User authenticated successfully", extra={"username": username})
                    metrics.successful_calls.add(1, {"operation": "authenticate_user"})

                    return tokens  # type: ignore[no-any-return]

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"Authentication failed for {username}",
                        extra={"status_code": e.response.status_code, "detail": e.response.text},
                    )
                    metrics.auth_failures.add(1, {"reason": "invalid_credentials"})
                    raise
                except httpx.HTTPError as e:
                    logger.error(f"Authentication error: {e}", exc_info=True)
                    metrics.failed_calls.add(1, {"operation": "authenticate_user"})
                    raise

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token

        Args:
            token: JWT access token

        Returns:
            Decoded token payload
        """
        return await self.token_validator.verify_token(token)

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New token response with access_token, refresh_token, etc.
        """
        with tracer.start_as_current_span("keycloak.refresh_token"):
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                try:
                    data = {
                        "grant_type": "refresh_token",
                        "client_id": self.config.client_id,
                        "refresh_token": refresh_token,
                    }

                    if self.config.client_secret:
                        data["client_secret"] = self.config.client_secret

                    response = await client.post(self.config.token_endpoint, data=data)
                    response.raise_for_status()

                    tokens = response.json()

                    logger.info("Token refreshed successfully")
                    metrics.successful_calls.add(1, {"operation": "refresh_token"})

                    return tokens  # type: ignore[no-any-return]

                except httpx.HTTPStatusError as e:
                    logger.warning("Token refresh failed", extra={"status_code": e.response.status_code})
                    metrics.auth_failures.add(1, {"reason": "refresh_failed"})
                    raise
                except httpx.HTTPError as e:
                    logger.error(f"Token refresh error: {e}", exc_info=True)
                    metrics.failed_calls.add(1, {"operation": "refresh_token"})
                    raise

    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from userinfo endpoint

        Args:
            access_token: Access token

        Returns:
            User information dictionary
        """
        with tracer.start_as_current_span("keycloak.get_userinfo"):
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                try:
                    headers = {"Authorization": f"Bearer {access_token}"}

                    response = await client.get(self.config.userinfo_endpoint, headers=headers)
                    response.raise_for_status()

                    userinfo = response.json()

                    logger.info("User info retrieved", extra={"sub": userinfo.get("sub")})
                    metrics.successful_calls.add(1, {"operation": "get_userinfo"})

                    return userinfo  # type: ignore[no-any-return]

                except httpx.HTTPError as e:
                    logger.error(f"Failed to get user info: {e}", exc_info=True)
                    metrics.failed_calls.add(1, {"operation": "get_userinfo"})
                    raise

    async def get_admin_token(self) -> str:
        """
        Get admin access token for admin API calls

        Returns:
            Admin access token
        """
        # Check if we have a valid cached token
        if self._admin_token and self._admin_token_expiry:
            if datetime.now(timezone.utc) < self._admin_token_expiry - timedelta(minutes=1):
                return self._admin_token

        # Get new admin token
        with tracer.start_as_current_span("keycloak.get_admin_token"):
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                try:
                    data = {
                        "grant_type": "password",
                        "client_id": "admin-cli",
                        "username": self.config.admin_username,
                        "password": self.config.admin_password,
                    }

                    # Admin token endpoint is at master realm
                    admin_token_url = f"{self.config.server_url}/realms/master/protocol/openid-connect/token"

                    response = await client.post(admin_token_url, data=data)
                    response.raise_for_status()

                    tokens = response.json()
                    self._admin_token = tokens["access_token"]
                    expires_in = tokens.get("expires_in", 300)  # Default 5 min
                    self._admin_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    logger.info("Admin token obtained")
                    return self._admin_token

                except httpx.HTTPError as e:
                    logger.error(f"Failed to get admin token: {e}", exc_info=True)
                    raise

    async def get_user_by_username(self, username: str) -> Optional[KeycloakUser]:
        """
        Get user by username using admin API

        Args:
            username: Username to search for

        Returns:
            KeycloakUser if found, None otherwise
        """
        with tracer.start_as_current_span("keycloak.get_user_by_username") as span:
            span.set_attribute("user.name", username)

            try:
                admin_token = await self.get_admin_token()

                async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                    headers = {"Authorization": f"Bearer {admin_token}"}
                    params = {"username": username, "exact": "true"}

                    url = f"{self.config.admin_url}/users"
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()

                    users = response.json()

                    if not users:
                        logger.info(f"User not found: {username}")
                        return None

                    user_data = users[0]

                    # Get user roles
                    user_id = user_data["id"]
                    realm_roles = await self._get_user_realm_roles(user_id, admin_token)
                    client_roles = await self._get_user_client_roles(user_id, admin_token)
                    groups = await self._get_user_groups(user_id, admin_token)

                    # Build KeycloakUser
                    keycloak_user = KeycloakUser(
                        id=user_id,
                        username=user_data["username"],
                        email=user_data.get("email"),
                        first_name=user_data.get("firstName"),
                        last_name=user_data.get("lastName"),
                        enabled=user_data.get("enabled", True),
                        email_verified=user_data.get("emailVerified", False),
                        realm_roles=realm_roles,
                        client_roles=client_roles,
                        groups=groups,
                        attributes=user_data.get("attributes", {}),
                    )

                    logger.info(f"User retrieved: {username}", extra={"user_id": user_id})
                    return keycloak_user

            except httpx.HTTPError as e:
                logger.error(f"Failed to get user: {e}", exc_info=True)
                return None

    async def _get_user_realm_roles(self, user_id: str, admin_token: str) -> List[str]:
        """Get user's realm-level roles"""
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                headers = {"Authorization": f"Bearer {admin_token}"}
                url = f"{self.config.admin_url}/users/{user_id}/role-mappings/realm"

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                roles = response.json()
                return [role["name"] for role in roles]
        except httpx.HTTPError:
            logger.warning(f"Failed to get realm roles for user {user_id}")
            return []

    async def _get_user_client_roles(self, user_id: str, admin_token: str) -> Dict[str, List[str]]:
        """Get user's client-level roles"""
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                headers = {"Authorization": f"Bearer {admin_token}"}

                # Get all clients
                clients_url = f"{self.config.admin_url}/clients"
                response = await client.get(clients_url, headers=headers)
                response.raise_for_status()
                clients = response.json()

                client_roles = {}

                # Get roles for our specific client
                for client_data in clients:
                    if client_data.get("clientId") == self.config.client_id:
                        client_id = client_data["id"]
                        roles_url = f"{self.config.admin_url}/users/{user_id}/role-mappings/clients/{client_id}"

                        roles_response = await client.get(roles_url, headers=headers)
                        if roles_response.status_code == 200:
                            roles = roles_response.json()
                            client_roles[self.config.client_id] = [role["name"] for role in roles]

                return client_roles

        except httpx.HTTPError:
            logger.warning(f"Failed to get client roles for user {user_id}")
            return {}

    async def _get_user_groups(self, user_id: str, admin_token: str) -> List[str]:
        """Get user's group memberships"""
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl, timeout=self.config.timeout) as client:
                headers = {"Authorization": f"Bearer {admin_token}"}
                url = f"{self.config.admin_url}/users/{user_id}/groups"

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                groups = response.json()
                return [group.get("path", group.get("name", "")) for group in groups]

        except httpx.HTTPError:
            logger.warning(f"Failed to get groups for user {user_id}")
            return []

    # Admin API Methods (stubs for new functionality)
    # These methods interact with Keycloak Admin API for user/client management

    async def create_client(self, client_config: Dict[str, Any]) -> str:
        """Create Keycloak client (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client creation
        raise NotImplementedError("create_client needs implementation")

    async def create_user(self, user_config: Dict[str, Any]) -> str:
        """Create Keycloak user (stub for SCIM/service principals)"""
        # TODO: Implement Keycloak Admin API user creation
        raise NotImplementedError("create_user needs implementation")

    async def update_user(self, user_id: str, user_config: Dict[str, Any]) -> None:
        """Update Keycloak user (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API user update
        raise NotImplementedError("update_user needs implementation")

    async def set_user_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Set user password (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API password update
        raise NotImplementedError("set_user_password needs implementation")

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API user retrieval
        raise NotImplementedError("get_user needs implementation")

    async def get_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """Get user attributes (stub for API keys)"""
        # TODO: Implement Keycloak Admin API attribute retrieval
        raise NotImplementedError("get_user_attributes needs implementation")

    async def update_user_attributes(self, user_id: str, attributes: Dict[str, Any]) -> None:
        """Update user attributes (stub for API keys)"""
        # TODO: Implement Keycloak Admin API attribute update
        raise NotImplementedError("update_user_attributes needs implementation")

    async def update_client_attributes(self, client_id: str, attributes: Dict[str, Any]) -> None:
        """Update client attributes (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client attribute update
        raise NotImplementedError("update_client_attributes needs implementation")

    async def update_client_secret(self, client_id: str, secret: str) -> None:
        """Update client secret (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client secret update
        raise NotImplementedError("update_client_secret needs implementation")

    async def get_clients(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get clients (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client listing
        raise NotImplementedError("get_clients needs implementation")

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client retrieval
        raise NotImplementedError("get_client needs implementation")

    async def delete_client(self, client_id: str) -> None:
        """Delete client (stub for service principals)"""
        # TODO: Implement Keycloak Admin API client deletion
        raise NotImplementedError("delete_client needs implementation")

    async def delete_user(self, user_id: str) -> None:
        """Delete user (stub for service principals/SCIM)"""
        # TODO: Implement Keycloak Admin API user deletion
        raise NotImplementedError("delete_user needs implementation")

    async def search_users(
        self, query: Optional[Dict[str, Any]] = None, first: int = 0, max: int = 100
    ) -> List[Dict[str, Any]]:
        """Search users (stub for API keys/SCIM)"""
        # TODO: Implement Keycloak Admin API user search
        raise NotImplementedError("search_users needs implementation")

    async def get_users(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get users with optional query (stub for service principals)"""
        # TODO: Implement Keycloak Admin API user listing
        raise NotImplementedError("get_users needs implementation")

    async def create_group(self, group_config: Dict[str, Any]) -> str:
        """Create group (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API group creation
        raise NotImplementedError("create_group needs implementation")

    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get group by ID (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API group retrieval
        raise NotImplementedError("get_group needs implementation")

    async def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Get group members (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API group member listing
        raise NotImplementedError("get_group_members needs implementation")

    async def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """Add user to group (stub for SCIM)"""
        # TODO: Implement Keycloak Admin API group membership
        raise NotImplementedError("add_user_to_group needs implementation")

    async def issue_token_for_user(self, user_id: str) -> Dict[str, Any]:
        """Issue JWT token for user (stub for API key exchange)"""
        # TODO: Implement token issuance (possibly via impersonation or token exchange)
        raise NotImplementedError("issue_token_for_user needs implementation")


async def sync_user_to_openfga(
    keycloak_user: KeycloakUser, openfga_client: Any, role_mapper: Optional[Any] = None, use_legacy_mapping: bool = False
) -> None:
    """
    Synchronize Keycloak user roles/groups to OpenFGA tuples

    Supports two modes:
    1. RoleMapper (recommended): Uses configurable YAML-based mapping
    2. Legacy (backward compatible): Uses hardcoded mapping rules

    Args:
        keycloak_user: Keycloak user to sync
        openfga_client: OpenFGA client instance
        role_mapper: RoleMapper instance (optional, will use default if None)
        use_legacy_mapping: Use legacy hardcoded mapping (default: False)
    """
    with tracer.start_as_current_span("keycloak.sync_to_openfga") as span:
        span.set_attribute("user.id", keycloak_user.user_id)
        span.set_attribute("mapping.mode", "legacy" if use_legacy_mapping else "role_mapper")

        tuples = []

        if use_legacy_mapping:
            # Legacy hardcoded mapping for backward compatibility
            logger.info("Using legacy role mapping")

            # Map realm roles
            if "admin" in keycloak_user.realm_roles:
                tuples.append({"user": keycloak_user.user_id, "relation": "admin", "object": "system:global"})

            # Map groups to organizations
            for group in keycloak_user.groups:
                org_name = group.strip("/").split("/")[-1]
                if org_name:
                    tuples.append({"user": keycloak_user.user_id, "relation": "member", "object": f"organization:{org_name}"})

            # Map client roles
            client_roles = keycloak_user.client_roles.get(keycloak_user.client_id, [])  # type: ignore[attr-defined]
            for role in client_roles:
                tuples.append({"user": keycloak_user.user_id, "relation": "assignee", "object": f"role:{role}"})

            # Map premium role for backward compatibility
            if "premium" in keycloak_user.realm_roles or "premium" in client_roles:
                tuples.append({"user": keycloak_user.user_id, "relation": "assignee", "object": "role:premium"})

        else:
            # Use RoleMapper for flexible, configurable mapping
            if role_mapper is None:
                # Import here to avoid circular dependency
                from mcp_server_langgraph.auth.role_mapper import RoleMapper

                role_mapper = RoleMapper()  # Uses default config

            logger.info("Using RoleMapper for role mapping")
            tuples = await role_mapper.map_user_to_tuples(keycloak_user)

        # Write tuples to OpenFGA
        if tuples:
            try:
                await openfga_client.write_tuples(tuples)
                logger.info(f"Synced {len(tuples)} tuples to OpenFGA for user {keycloak_user.username}")
            except Exception as e:
                logger.error(f"Failed to sync user to OpenFGA: {e}", exc_info=True)
                raise
        else:
            logger.info(f"No tuples to sync for user {keycloak_user.username}")
