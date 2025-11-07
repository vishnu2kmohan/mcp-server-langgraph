"""
Abstract user provider interface for pluggable authentication backends

Enables switching between different user management systems:
- InMemoryUserProvider (development/testing)
- KeycloakUserProvider (production)
- Custom providers (future extensions)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TypedDict

import jwt
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig, sync_user_to_openfga
from mcp_server_langgraph.observability.telemetry import logger, tracer

# Try to import bcrypt for password hashing
try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    # Note: logger warning deferred to InMemoryUserProvider.__init__
    # to avoid import-time observability dependency

# ============================================================================
# Pydantic Models for Type-Safe Authentication Responses
# ============================================================================


class UserDBEntry(TypedDict):
    """Type definition for user database entries"""

    user_id: str
    email: str
    password: str
    roles: List[str]
    active: bool


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
    username: Optional[str] = Field(default=None, description="Username if authorized")
    user_id: Optional[str] = Field(default=None, description="User ID if authorized")
    email: Optional[str] = Field(default=None, description="Email if authorized")
    roles: List[str] = Field(default_factory=list, description="User roles if authorized")
    reason: Optional[str] = Field(default=None, description="Failure reason if not authorized")
    error: Optional[str] = Field(default=None, description="Error details if not authorized")
    # Keycloak-specific fields (optional)
    access_token: Optional[str] = Field(default=None, description="JWT access token (Keycloak)")
    refresh_token: Optional[str] = Field(default=None, description="JWT refresh token (Keycloak)")
    expires_in: Optional[int] = Field(default=None, description="Token expiration in seconds (Keycloak)")

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
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Token payload if valid")
    error: Optional[str] = Field(default=None, description="Error message if not valid")

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

    Features:
    - Optional bcrypt password hashing (install bcrypt package)
    - JWT token generation
    - User lookup and authentication

    NOT suitable for large-scale production (use KeycloakUserProvider instead).
    """

    def __init__(self, secret_key: Optional[str] = None, use_password_hashing: bool = False) -> None:
        """
        Initialize in-memory user provider

        Args:
            secret_key: Secret key for JWT token signing.
                       Required for production use. Should be loaded from environment variables.
            use_password_hashing: Enable bcrypt password hashing (requires bcrypt package).
                                 If True and bcrypt not available, falls back to plaintext.
        """
        if not secret_key:
            # Use a random key for testing/development only
            import secrets as secrets_module

            secret_key = secrets_module.token_urlsafe(32)
            logger.warning(
                "No secret_key provided to InMemoryUserProvider. Using random key. "
                "This is only suitable for testing/development. "
                "In production, always provide a secure secret key via environment variables."
            )
        self.secret_key = secret_key

        # Check bcrypt availability if hashing requested
        if use_password_hashing and not BCRYPT_AVAILABLE:
            # SECURITY: Fail-closed pattern - refuse to start with insecure config
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Password hashing requested (use_password_hashing=True) "
                "but bcrypt library is not available. "
                "This would result in INSECURE plaintext passwords. "
                "\n\nTo fix:\n"
                "1. Install bcrypt: Add 'bcrypt' to pyproject.toml dependencies, then run: uv sync\n"
                "2. Or disable password hashing: USE_PASSWORD_HASHING=false (NOT recommended for production)\n"
                "\nRefusing to start with insecure configuration."
            )

        self.use_password_hashing = use_password_hashing and BCRYPT_AVAILABLE

        # SECURITY (OpenAI Codex Finding #2): Start with empty user database
        # No hard-coded credentials. Users must be explicitly created via add_user() or configuration.
        # This prevents CWE-798: Use of Hard-coded Credentials
        self.users_db: Dict[str, UserDBEntry] = {}

        if self.use_password_hashing:
            logger.info(
                "InMemoryUserProvider initialized with BCRYPT password hashing (secure)",
                extra={"user_count": len(self.users_db)},
            )
        else:
            logger.warning(
                "InMemoryUserProvider initialized with PLAINTEXT PASSWORDS (INSECURE). "
                "This is only suitable for development/testing. "
                "Use password hashing (use_password_hashing=True) or KeycloakUserProvider for production.",
                extra={"user_count": len(self.users_db)},
            )

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt

        Args:
            password: Plaintext password

        Returns:
            Bcrypt password hash
        """
        if not BCRYPT_AVAILABLE:
            return password  # Fallback to plaintext

        password_bytes = password.encode("utf-8")

        # bcrypt 5.0+ enforces 72-byte password limit (raises ValueError instead of silent truncation)
        if len(password_bytes) > 72:
            raise ValueError(
                f"Password exceeds bcrypt's 72-byte limit ({len(password_bytes)} bytes). "
                "Consider hashing long passwords with SHA256 before bcrypt."
            )

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Plaintext password to verify
            password_hash: Stored password hash (or plaintext if hashing disabled)

        Returns:
            True if password matches, False otherwise
        """
        if not self.use_password_hashing:
            # Plaintext comparison (insecure, dev/test only)
            return password == password_hash

        # Bcrypt comparison (secure)
        password_bytes = password.encode("utf-8")

        # Silently handle overly long passwords during verification
        # (they would have been rejected during hashing with bcrypt 5.0+)
        if len(password_bytes) > 72:
            return False

        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)

    def add_user(self, username: str, password: str, email: str, roles: list[str]) -> None:
        """
        Add a new user to the in-memory database

        IMPORTANT: InMemoryUserProvider no longer seeds default users for security.
        You must explicitly create users for testing/development using this method.

        Example:
            provider = InMemoryUserProvider(use_password_hashing=True)
            provider.add_user(
                username="testuser",
                password="secure-password-123",
                email="testuser@example.com",
                roles=["user", "premium"]
            )

        Args:
            username: Username (unique identifier)
            password: Plaintext password (will be hashed if use_password_hashing=True)
            email: Email address
            roles: List of role names (e.g., ["user"], ["admin"], ["user", "premium"])

        Security:
            - Passwords are automatically hashed with bcrypt if use_password_hashing=True
            - For production, use KeycloakUserProvider instead of InMemoryUserProvider
        """
        stored_password = self._hash_password(password) if self.use_password_hashing else password

        self.users_db[username] = UserDBEntry(
            user_id=f"user:{username}",
            email=email,
            password=stored_password,
            roles=roles,
            active=True,
        )

        logger.info(f"Added user: {username}", extra={"user_id": f"user:{username}", "roles": roles})

    async def authenticate(self, username: str, password: Optional[str] = None) -> AuthResponse:
        """
        Authenticate user by username and password

        SECURITY: This method now requires a password for authentication.
        Plaintext comparison is used for development/testing only.
        Use KeycloakUserProvider or implement password hashing for production.

        Args:
            username: Username to authenticate
            password: Password (REQUIRED for InMemoryUserProvider)

        Returns:
            AuthResponse with authentication result
        """
        with tracer.start_as_current_span("inmemory.authenticate") as span:
            span.set_attribute("auth.username", username)

            # SECURITY: Require password
            if not password:
                logger.warning("Authentication failed - password required", extra={"username": username})
                return AuthResponse(authorized=False, reason="password_required")

            # Check user database
            if username not in self.users_db:
                logger.warning("Authentication failed - user not found", extra={"username": username})
                # Use same error message as invalid password to prevent username enumeration
                return AuthResponse(authorized=False, reason="invalid_credentials")

            user = self.users_db[username]

            # Check if account is active
            if not user["active"]:
                logger.warning("User account inactive", extra={"username": username})
                return AuthResponse(authorized=False, reason="account_inactive")

            # SECURITY: Validate password using bcrypt (if enabled) or plaintext comparison
            if not self._verify_password(password, user["password"]):
                logger.warning("Authentication failed - invalid password", extra={"username": username})
                return AuthResponse(authorized=False, reason="invalid_credentials")

            logger.info("User authenticated", extra={"username": username, "user_id": user["user_id"]})

            return AuthResponse(
                authorized=True,
                username=username,
                user_id=user["user_id"],
                email=user["email"],
                roles=user["roles"],
            )

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

        # Use timestamp with microseconds for unique jti to ensure each token is different
        now = datetime.now(timezone.utc)
        jti = f"{username}_{int(now.timestamp() * 1000000)}"  # Microsecond precision

        payload = {
            "sub": user["user_id"],
            "username": username,
            "email": user["email"],
            "roles": user["roles"],
            "exp": now + timedelta(seconds=expires_in),
            "iat": now,
            "jti": jti,  # Unique token ID to ensure each token is different
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        logger.info("Token created", extra={"username": username, "user_id": user["user_id"], "expires_in": expires_in})

        return token


class KeycloakUserProvider(UserProvider):
    """
    Keycloak user provider for production

    Uses Keycloak as the identity provider for authentication and user management.
    """

    def __init__(self, config: KeycloakConfig, openfga_client: Optional[Any] = None, sync_on_login: bool = True) -> None:
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
    Factory function to create user provider based on explicit parameters (test use)

    This factory is designed for test code where you want explicit control
    over provider configuration without requiring a Settings object.

    For production code, use `mcp_server_langgraph.auth.factory.create_user_provider()`
    which reads from application settings.

    Args:
        provider_type: Type of provider ("inmemory", "keycloak")
        secret_key: Secret key for in-memory provider
        keycloak_config: Keycloak configuration for keycloak provider
        openfga_client: OpenFGA client for role synchronization

    Returns:
        User provider instance

    Raises:
        ValueError: If provider type is unknown or required config is missing

    See Also:
        mcp_server_langgraph.auth.factory.create_user_provider: Recommended for production use
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
