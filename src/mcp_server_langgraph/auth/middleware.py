"""
Authentication and Authorization middleware with OpenFGA integration
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

import jwt

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.observability.telemetry import logger, tracer


class AuthMiddleware:
    """
    Authentication and authorization handler with OpenFGA

    Combines JWT-based authentication with fine-grained relationship-based
    authorization using OpenFGA.
    """

    def __init__(
        self, secret_key: str = "your-secret-key-change-in-production", openfga_client: Optional[OpenFGAClient] = None
    ):
        self.secret_key = secret_key
        self.openfga = openfga_client

        # User database (in production, use real database)
        self.users_db = {
            "alice": {"user_id": "user:alice", "email": "alice@acme.com", "roles": ["user", "premium"], "active": True},
            "bob": {"user_id": "user:bob", "email": "bob@acme.com", "roles": ["user"], "active": True},
            "admin": {"user_id": "user:admin", "email": "admin@acme.com", "roles": ["admin"], "active": True},
        }

    async def authenticate(self, username: str) -> Dict[str, Any]:
        """
        Authenticate user by username

        Args:
            username: Username to authenticate

        Returns:
            Authentication result with user details
        """
        with tracer.start_as_current_span("auth.authenticate") as span:
            span.set_attribute("auth.username", username)

            # Check user database
            if username in self.users_db:
                user = self.users_db[username]

                if not user["active"]:
                    logger.warning("User account inactive", extra={"username": username})
                    return {"authorized": False, "reason": "account_inactive"}

                logger.info("User authenticated", extra={"username": username, "user_id": user["user_id"]})

                return {
                    "authorized": True,
                    "username": username,
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "roles": user["roles"],
                }

            logger.warning("Authentication failed - user not found", extra={"username": username})
            return {"authorized": False, "reason": "user_not_found"}

    async def authorize(self, user_id: str, relation: str, resource: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user is authorized using OpenFGA

        Args:
            user_id: User identifier (e.g., "user:alice")
            relation: Relation to check (e.g., "executor", "viewer")
            resource: Resource identifier (e.g., "tool:chat")
            context: Additional context for authorization

        Returns:
            True if authorized, False otherwise
        """
        with tracer.start_as_current_span("auth.authorize") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("auth.relation", relation)
            span.set_attribute("auth.resource", resource)

            # Use OpenFGA if available
            if self.openfga:
                try:
                    authorized = await self.openfga.check_permission(
                        user=user_id, relation=relation, object=resource, context=context
                    )

                    span.set_attribute("auth.authorized", authorized)
                    logger.info(
                        "Authorization check (OpenFGA)",
                        extra={"user_id": user_id, "relation": relation, "resource": resource, "authorized": authorized},
                    )

                    return authorized

                except Exception as e:
                    logger.error(
                        f"OpenFGA authorization check failed: {e}",
                        extra={"user_id": user_id, "relation": relation, "resource": resource},
                        exc_info=True,
                    )
                    # Fail closed - deny access on error
                    return False

            # Fallback: simple permission check
            logger.warning("OpenFGA not available, using fallback authorization")

            # Extract username from user_id
            username = user_id.split(":")[-1] if ":" in user_id else user_id

            if username not in self.users_db:
                return False

            user = self.users_db[username]

            # Admin users have access to everything
            if "admin" in user["roles"]:
                return True

            # Basic resource-based checks
            if relation == "executor" and resource.startswith("tool:"):
                return "premium" in user["roles"] or "user" in user["roles"]

            if relation == "viewer" and resource.startswith("conversation:"):
                # Users can view their own conversations
                return True

            return False

    async def list_accessible_resources(self, user_id: str, relation: str, resource_type: str) -> list[str]:
        """
        List all resources user has access to

        Args:
            user_id: User identifier
            relation: Relation to check (e.g., "executor", "viewer")
            resource_type: Type of resources (e.g., "tool", "conversation")

        Returns:
            List of accessible resource identifiers
        """
        if not self.openfga:
            logger.warning("OpenFGA not available for resource listing")
            return []

        try:
            resources = await self.openfga.list_objects(user=user_id, relation=relation, object_type=resource_type)

            logger.info(
                "Listed accessible resources",
                extra={"user_id": user_id, "relation": relation, "resource_type": resource_type, "count": len(resources)},
            )

            return resources

        except Exception as e:
            logger.error(f"Failed to list accessible resources: {e}", exc_info=True)
            return []

    def create_token(self, username: str, expires_in: int = 3600) -> str:
        """
        Create JWT token for user

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

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            logger.info("Token verified", extra={"user_id": payload.get("user_id")})
            return {"valid": True, "payload": payload}
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return {"valid": False, "error": "Invalid token"}


def require_auth(
    relation: Optional[str] = None, resource: Optional[str] = None, openfga_client: Optional[OpenFGAClient] = None
):
    """
    Decorator for requiring authentication/authorization

    Args:
        relation: Required relation (e.g., "executor")
        resource: Resource to check access to
        openfga_client: OpenFGA client instance
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth = AuthMiddleware(openfga_client=openfga_client)
            username = kwargs.get("username")
            user_id = kwargs.get("user_id")

            if not username and not user_id:
                raise PermissionError("Authentication required")

            # Authenticate
            if username:
                auth_result = await auth.authenticate(username)
                if not auth_result["authorized"]:
                    raise PermissionError("Authentication failed")
                user_id = auth_result["user_id"]

            # Authorize if relation and resource specified
            if relation and resource:
                if not await auth.authorize(user_id, relation, resource):
                    raise PermissionError(f"Not authorized: {user_id} cannot {relation} {resource}")

            # Add user_id to kwargs if authenticated
            kwargs["user_id"] = user_id
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def verify_token(token: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Standalone token verification function

    Args:
        token: JWT token to verify
        secret_key: Secret key for verification

    Returns:
        Token verification result
    """
    auth = AuthMiddleware(secret_key=secret_key or "your-secret-key-change-in-production")
    return auth.verify_token(token)
