"""
Abstract user provider interface for pluggable authentication backends

Enables switching between different user management systems:
- InMemoryUserProvider (development/testing)
- KeycloakUserProvider (production)
- Custom providers (future extensions)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig, KeycloakUser, sync_user_to_openfga
from mcp_server_langgraph.observability.telemetry import logger, tracer

# ============================================================================
# Pydantic Models for Type-Safe Authentication Responses
# ============================================================================


class UserData(BaseModel):
    """
    Type-safe user data structure

    Represents user information returned from user queries.
    """

    user_id: str = Field(..., description="User identifier (e.g., 'user:alice')")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    roles: List[str] = Field(default_factory=list, description="User roles")
    active: bool = Field(default=True, description="Whether user account is active")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "user_id": "user:alice",
                "username": "alice",
                "email": "alice@acme.com",
                "roles": ["user", "premium"],
                "active": True,
            }
        },
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserData":
        """Create UserData from dictionary"""
        return cls(**data)


class AuthResponse(BaseModel):
    """
    Type-safe authentication response

    Returned from authenticate() operations.
    """

    authorized: bool = Field(..., description="Whether authentication was successful")
    username: Optional[str] = Field(None, description="Username if authorized")
    user_id: Optional[str] = Field(None, description="User ID if authorized")
    email: Optional[str] = Field(None, description="Email if authorized")
    roles: List[str] = Field(default_factory=list, description="User roles if authorized")
    reason: Optional[str] = Field(None, description="Failure reason if not authorized")
    error: Optional[str] = Field(None, description="Error details if not authorized")
    # Keycloak-specific fields (optional)
    access_token: Optional[str] = Field(None, description="JWT access token (Keycloak)")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token (Keycloak)")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds (Keycloak)")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "authorized": True,
                "username": "alice",
                "user_id": "user:alice",
                "email": "alice@acme.com",
                "roles": ["user", "premium"],
                "reason": None,
                "error": None,
                "access_token": "eyJ...",
                "refresh_token": "eyJ...",
                "expires_in": 300,
            }
        },
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthResponse":
        """Create AuthResponse from dictionary"""
        return cls(**data)


class TokenVerification(BaseModel):
    """
    Type-safe token verification response

    Returned from verify_token() operations.
    """

    valid: bool = Field(..., description="Whether token is valid")
    payload: Optional[Dict[str, Any]] = Field(None, description="Token payload if valid")
    error: Optional[str] = Field(None, description="Error message if not valid")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        json_schema_extra={"example": {"valid": True, "payload": {"sub": "user:alice", "exp": 1234567890}, "error": None}},
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenVerification":
        """Create TokenVerification from dictionary"""
        return cls(**data)


class UserProvider(ABC):
    """
    Abstract base class for user providers

    Defines the interface that all authentication backends must implement.
    """

    @abstractmethod
    async def authenticate(self, username: str, password: Optional[str] = None) -> AuthResponse:
        """
        Authenticate user by username/password

        Args:
            username: Username
            password: Password (optional for some providers)

        Returns:
            AuthResponse with authentication result
        """
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[UserData]:
        """
        Get user by user ID

        Args:
            user_id: User identifier (e.g., "user:alice")

        Returns:
            UserData or None if not found
        """
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        """
        Get user by username

        Args:
            username: Username

        Returns:
            UserData or None if not found
        """
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> TokenVerification:
        """
        Verify JWT token

        Args:
            token: JWT token to verify

        Returns:
            TokenVerification with validation result
        """
        pass

    @abstractmethod
    async def list_users(self) -> List[UserData]:
        """
        List all users (for admin operations)

        Returns:
            List of UserData objects
        """
        pass


class InMemoryUserProvider(UserProvider):
    """
    In-memory user provider for development and testing

    Maintains a static dictionary of users. NOT suitable for production.
    """

    def __init__(self, secret_key: str = "your-secret-key-change-in-production"):
        """
        Initialize in-memory user provider

        Args:
            secret_key: Secret key for JWT token signing
        """
        self.secret_key = secret_key

        # User database (same as original AuthMiddleware)
        self.users_db = {
            "alice": {"user_id": "user:alice", "email": "alice@acme.com", "roles": ["user", "premium"], "active": True},
            "bob": {"user_id": "user:bob", "email": "bob@acme.com", "roles": ["user"], "active": True},
            "admin": {"user_id": "user:admin", "email": "admin@acme.com", "roles": ["admin"], "active": True},
        }

        logger.info("Initialized InMemoryUserProvider", extra={"user_count": len(self.users_db)})

    async def authenticate(self, username: str, password: Optional[str] = None) -> AuthResponse:
        """Authenticate user by username lookup"""
        with tracer.start_as_current_span("inmemory.authenticate") as span:
            span.set_attribute("auth.username", username)

            # Check user database
            if username in self.users_db:
                user = self.users_db[username]

                if not user["active"]:
                    logger.warning("User account inactive", extra={"username": username})
                    return AuthResponse(authorized=False, reason="account_inactive")

                logger.info("User authenticated", extra={"username": username, "user_id": user["user_id"]})

                return AuthResponse(
                    authorized=True,
                    username=username,
                    user_id=user["user_id"],
                    email=user["email"],
                    roles=user["roles"],
                )

            logger.warning("Authentication failed - user not found", extra={"username": username})
            return AuthResponse(authorized=False, reason="user_not_found")

    async def get_user_by_id(self, user_id: str) -> Optional[UserData]:
        """Get user by ID"""
        # Extract username from user_id format "user:username"
        username = user_id.split(":")[-1] if ":" in user_id else user_id
        return await self.get_user_by_username(username)

    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        """Get user by username"""
        if username in self.users_db:
            user_data = self.users_db[username]
            return UserData(
                username=username,
                user_id=user_data["user_id"],
                email=user_data["email"],
                roles=user_data["roles"],
                active=user_data["active"],
            )
        return None

    async def verify_token(self, token: str) -> TokenVerification:
        """Verify self-issued JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            logger.info("Token verified", extra={"user_id": payload.get("sub")})
            return TokenVerification(valid=True, payload=payload)
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return TokenVerification(valid=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return TokenVerification(valid=False, error="Invalid token")

    async def list_users(self) -> List[UserData]:
        """List all users"""
        return [
            UserData(
                username=username,
                user_id=user_data["user_id"],
                email=user_data["email"],
                roles=user_data["roles"],
                active=user_data["active"],
            )
            for username, user_data in self.users_db.items()
        ]

    def create_token(self, username: str, expires_in: int = 3600) -> str:
        """
        Create JWT token for user (helper method for in-memory provider)

        Args:
            username: Username
            expires_in: Token expiration in seconds

        Returns:
            JWT token string
        """
        if username not in self.users_db:
            raise ValueError(f"User not found: {username}")

        user = self.users_db[username]

        payload = {
            "sub": user["user_id"],
            "username": username,
            "email": user["email"],
            "roles": user["roles"],
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        logger.info("Token created", extra={"username": username, "user_id": user["user_id"], "expires_in": expires_in})

        return token


class KeycloakUserProvider(UserProvider):
    """
    Keycloak user provider for production

    Uses Keycloak as the identity provider for authentication and user management.
    """

    def __init__(self, config: KeycloakConfig, openfga_client: Optional[Any] = None, sync_on_login: bool = True):
        """
        Initialize Keycloak user provider

        Args:
            config: Keycloak configuration
            openfga_client: Optional OpenFGA client for role synchronization
            sync_on_login: Whether to sync roles to OpenFGA on login
        """
        self.client = KeycloakClient(config)
        self.config = config
        self.openfga_client = openfga_client
        self.sync_on_login = sync_on_login

        logger.info(
            "Initialized KeycloakUserProvider",
            extra={"realm": config.realm, "client_id": config.client_id, "sync_on_login": sync_on_login},
        )

    async def authenticate(self, username: str, password: Optional[str] = None) -> AuthResponse:
        """
        Authenticate user using Keycloak

        Args:
            username: Username
            password: Password

        Returns:
            AuthResponse with tokens
        """
        with tracer.start_as_current_span("keycloak.authenticate") as span:
            span.set_attribute("auth.username", username)

            if not password:
                logger.warning("Password required for Keycloak authentication")
                return AuthResponse(authorized=False, reason="password_required")

            try:
                # Authenticate with Keycloak
                tokens = await self.client.authenticate_user(username, password)

                # Get user info from token or userinfo endpoint
                access_token = tokens["access_token"]
                userinfo = await self.client.get_userinfo(access_token)

                # Get full user details for role sync
                keycloak_user = await self.client.get_user_by_username(username)

                if not keycloak_user:
                    logger.error(f"User authenticated but not found in admin API: {username}")
                    return AuthResponse(authorized=False, reason="user_data_error")

                # Sync to OpenFGA if enabled
                if self.sync_on_login and self.openfga_client:
                    try:
                        await sync_user_to_openfga(keycloak_user, self.openfga_client)
                    except Exception as e:
                        logger.error(f"Failed to sync user to OpenFGA: {e}", exc_info=True)
                        # Don't fail authentication if sync fails

                logger.info("User authenticated via Keycloak", extra={"username": username, "user_id": keycloak_user.user_id})

                return AuthResponse(
                    authorized=True,
                    username=keycloak_user.username,
                    user_id=keycloak_user.user_id,
                    email=keycloak_user.email or "",
                    roles=keycloak_user.realm_roles,
                    access_token=tokens["access_token"],
                    refresh_token=tokens.get("refresh_token"),
                    expires_in=tokens.get("expires_in", 300),
                )

            except Exception as e:
                logger.warning(f"Keycloak authentication failed for {username}: {e}")
                return AuthResponse(authorized=False, reason="authentication_failed", error=str(e))

    async def get_user_by_id(self, user_id: str) -> Optional[UserData]:
        """Get user by ID"""
        # Extract username from user_id format "user:username"
        username = user_id.split(":")[-1] if ":" in user_id else user_id
        return await self.get_user_by_username(username)

    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        """Get user by username from Keycloak"""
        try:
            keycloak_user = await self.client.get_user_by_username(username)

            if keycloak_user:
                return UserData(
                    username=keycloak_user.username,
                    user_id=keycloak_user.user_id,
                    email=keycloak_user.email or "",
                    roles=keycloak_user.realm_roles,
                    active=keycloak_user.enabled,
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get user {username}: {e}", exc_info=True)
            return None

    async def verify_token(self, token: str) -> TokenVerification:
        """Verify Keycloak-issued JWT token"""
        try:
            payload = await self.client.verify_token(token)
            return TokenVerification(valid=True, payload=payload)
        except Exception as e:
            return TokenVerification(valid=False, error=str(e))

    async def list_users(self) -> List[UserData]:
        """
        List users (requires admin permissions)

        Note: This is a placeholder. In production, you'd implement pagination
        and filtering using Keycloak admin API.
        """
        logger.warning("list_users() not fully implemented for KeycloakUserProvider")
        return []

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token

        Args:
            refresh_token: Refresh token

        Returns:
            New tokens
        """
        try:
            tokens = await self.client.refresh_token(refresh_token)
            return {"success": True, "tokens": tokens}
        except Exception as e:
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


def create_user_provider(
    provider_type: str = "inmemory",
    secret_key: Optional[str] = None,
    keycloak_config: Optional[KeycloakConfig] = None,
    openfga_client: Optional[Any] = None,
) -> UserProvider:
    """
    Factory function to create user provider based on configuration

    Args:
        provider_type: Type of provider ("inmemory", "keycloak")
        secret_key: Secret key for in-memory provider
        keycloak_config: Keycloak configuration for keycloak provider
        openfga_client: OpenFGA client for role synchronization

    Returns:
        User provider instance

    Raises:
        ValueError: If provider type is unknown or required config is missing
    """
    provider_type = provider_type.lower()

    if provider_type == "inmemory":
        logger.info("Creating InMemoryUserProvider (development mode)")
        return InMemoryUserProvider(secret_key=secret_key or "your-secret-key-change-in-production")

    elif provider_type == "keycloak":
        if not keycloak_config:
            raise ValueError("keycloak_config required for KeycloakUserProvider")

        logger.info("Creating KeycloakUserProvider (production mode)")
        return KeycloakUserProvider(config=keycloak_config, openfga_client=openfga_client)

    else:
        raise ValueError(f"Unknown provider type: {provider_type}. Supported: 'inmemory', 'keycloak'")
