"""
Rate limiting middleware for FastAPI with tiered limits.

Provides DoS protection with:
- Tiered rate limits (anonymous, free, standard, premium, enterprise)
- Redis-backed distributed rate limiting
- User-based and IP-based limiting
- Automatic X-RateLimit-* headers
- Graceful degradation (fail-open if Redis is down)

See ADR-0027 for design rationale.
"""

from typing import Callable, Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

# Rate limit tiers (requests per minute)
RATE_LIMITS = {
    "anonymous": "10/minute",
    "free": "60/minute",
    "standard": "300/minute",
    "premium": "1000/minute",
    "enterprise": "999999/minute",  # Effectively unlimited
}

# Endpoint-specific rate limits (override tier limits)
ENDPOINT_RATE_LIMITS = {
    "auth_login": "10/minute",  # Prevent brute force
    "auth_register": "5/minute",  # Prevent spam registration
    "llm_chat": "30/minute",  # LLM-heavy endpoints (cost control)
    "search": "100/minute",  # Search endpoints
    "read": "200/minute",  # Read-only endpoints
}


def get_user_id_from_jwt(request: Request) -> Optional[str]:
    """
    Extract user ID from JWT token in request.

    Args:
        request: FastAPI request object

    Returns:
        User ID if JWT is valid, None otherwise
    """
    try:
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")

        # Decode JWT to get user ID
        import jwt

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,  # type: ignore[arg-type]
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},  # Don't verify expiration for rate limiting
            )
            return payload.get("sub") or payload.get("user_id")  # type: ignore[no-any-return]
        except jwt.InvalidTokenError:
            return None

    except Exception as e:
        logger.debug(f"Failed to extract user ID from JWT: {e}")
        return None


def get_user_tier(request: Request) -> str:
    """
    Determine user tier from JWT claims.

    Args:
        request: FastAPI request object

    Returns:
        User tier (anonymous, free, standard, premium, enterprise)
    """
    try:
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return "anonymous"

        token = auth_header.replace("Bearer ", "")

        # Decode JWT to get tier
        import jwt

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,  # type: ignore[arg-type]
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )

            # Extract tier from JWT payload
            tier = payload.get("tier") or payload.get("plan") or "free"
            return tier if tier in RATE_LIMITS else "free"

        except jwt.InvalidTokenError:
            return "anonymous"

    except Exception as e:
        logger.debug(f"Failed to extract tier from JWT: {e}")
        return "anonymous"


def get_rate_limit_key(request: Request) -> str:
    """
    Determine rate limit key (user ID > IP > global).

    Hierarchy:
    1. User ID from JWT (most specific)
    2. IP address (less specific)
    3. Global anonymous (least specific)

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string
    """
    # Try to get user ID from JWT
    if user_id := get_user_id_from_jwt(request):
        return f"user:{user_id}"

    # Fall back to IP address
    ip_address = get_remote_address(request)
    if ip_address:
        return f"ip:{ip_address}"

    # Last resort: global anonymous
    return "global:anonymous"


def get_rate_limit_for_tier(tier: str) -> str:
    """
    Get rate limit string for a tier.

    Args:
        tier: User tier name

    Returns:
        Rate limit string (e.g., "60/minute")
    """
    return RATE_LIMITS.get(tier, RATE_LIMITS["free"])


def get_dynamic_limit(request: Request) -> str:
    """
    Get dynamic rate limit based on user tier.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit string for the user's tier
    """
    tier = get_user_tier(request)
    limit = get_rate_limit_for_tier(tier)

    logger.debug(
        "Rate limit determined",
        extra={
            "tier": tier,
            "limit": limit,
            "key": get_rate_limit_key(request),
        },
    )

    return limit


# Configure Redis storage for distributed rate limiting
def get_redis_storage_uri() -> str:
    """
    Get Redis storage URI for rate limiting.

    Returns:
        Redis URI string

    Fallback: If Redis is unavailable, slowapi will use in-memory storage
    """
    redis_host = getattr(settings, "redis_host", "localhost")
    redis_port = getattr(settings, "redis_port", 6379)
    redis_db = getattr(settings, "redis_rate_limit_db", 3)  # DB 3 for rate limiting

    return f"redis://{redis_host}:{redis_port}/{redis_db}"


# Create limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[get_dynamic_limit],  # Dynamic limits based on tier
    storage_uri=get_redis_storage_uri(),
    strategy="fixed-window",  # fixed-window, moving-window
    headers_enabled=True,  # Add X-RateLimit-* headers
    swallow_errors=True,  # Fail-open: allow requests if rate limiting fails
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> None:
    """
    Custom handler for rate limit exceeded errors.

    Provides structured error response with retry information.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with rate limit error
    """
    from fastapi.responses import JSONResponse

    from mcp_server_langgraph.core.exceptions import RateLimitExceededError

    # Get user tier for error message
    tier = get_user_tier(request)
    limit = get_rate_limit_for_tier(tier)

    # Create custom exception
    rate_limit_error = RateLimitExceededError(
        message=f"Rate limit exceeded for tier '{tier}' ({limit})",
        metadata={
            "tier": tier,
            "limit": limit,
            "retry_after": 60,  # Default retry after 60 seconds
        },
    )

    # Emit metric
    from mcp_server_langgraph.observability.telemetry import error_counter

    try:
        error_counter.add(
            1,
            attributes={
                "error_code": rate_limit_error.error_code,
                "tier": tier,
                "endpoint": request.url.path,
            },
        )
    except Exception:
        pass  # Don't let metrics failure break error handling

    # Log rate limit violation
    logger.warning(
        "Rate limit exceeded",
        extra={
            "tier": tier,
            "limit": limit,
            "key": get_rate_limit_key(request),
            "endpoint": request.url.path,
            "method": request.method,
        },
    )

    # Return structured error response
    return JSONResponse(  # type: ignore[return-value]
        status_code=429,
        content=rate_limit_error.to_dict(),
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": str(limit.split("/")[0]),
            "X-RateLimit-Remaining": "0",
        },
    )


def setup_rate_limiting(app) -> None:  # type: ignore[no-untyped-def]
    """
    Setup rate limiting for FastAPI application.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from mcp_server_langgraph.middleware.rate_limiter import setup_rate_limiting

        app = FastAPI()
        setup_rate_limiting(app)
    """
    # Add limiter to app state
    app.state.limiter = limiter

    # Register custom exception handler
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

    logger.info(
        "Rate limiting configured",
        extra={
            "storage": get_redis_storage_uri(),
            "strategy": "fixed-window",
            "tiers": list(RATE_LIMITS.keys()),
        },
    )


# Decorators for endpoint-specific rate limits
def rate_limit_for_auth(func: Callable) -> Callable:  # type: ignore[type-arg]
    """Rate limit decorator for authentication endpoints"""
    return limiter.limit(ENDPOINT_RATE_LIMITS["auth_login"])(func)  # type: ignore[no-any-return]


def rate_limit_for_llm(func: Callable) -> Callable:  # type: ignore[type-arg]
    """Rate limit decorator for LLM endpoints"""
    return limiter.limit(ENDPOINT_RATE_LIMITS["llm_chat"])(func)  # type: ignore[no-any-return]


def rate_limit_for_search(func: Callable) -> Callable:  # type: ignore[type-arg]
    """Rate limit decorator for search endpoints"""
    return limiter.limit(ENDPOINT_RATE_LIMITS["search"])(func)  # type: ignore[no-any-return]


def exempt_from_rate_limit(func: Callable) -> Callable:  # type: ignore[type-arg]
    """Exempt endpoint from rate limiting (health checks, metrics)"""
    return limiter.exempt(func)  # type: ignore[no-any-return,no-untyped-call]
