"""
Legacy Redirect Module

Provides 301 redirects from old routes to new Studio routes.
"""

from typing import Any
from urllib.parse import urlparse

# Mapping of old route prefixes to new route prefixes
# NOTE: /playground redirect removed - playground has been decommissioned
REDIRECT_MAPPINGS: dict[str, str] = {
    # Frontend routes
    "/build": "/studio/workflows",
    "/chat": "/studio/chat",
    # API routes
    "/builder": "/api/v1/workflows",
}


def translate_legacy_path(path: str) -> str | None:
    """Translate a legacy path to the new Studio path.

    Args:
        path: The legacy path to translate

    Returns:
        The new path if translation is possible, None otherwise
    """
    # Parse the path to handle query parameters
    parsed = urlparse(path)
    path_only = parsed.path
    query_string = parsed.query

    # Check each mapping
    for old_prefix, new_prefix in REDIRECT_MAPPINGS.items():
        if path_only == old_prefix:
            # Exact match - redirect to new prefix
            result = new_prefix
            if query_string:
                result += f"?{query_string}"
            return result
        elif path_only.startswith(f"{old_prefix}/"):
            # Prefix match - translate the rest of the path
            rest = path_only[len(old_prefix) :]
            result = f"{new_prefix}{rest}"
            if query_string:
                result += f"?{query_string}"
            return result

    return None


class LegacyRedirectMiddleware:
    """ASGI middleware that redirects legacy routes to new Studio routes.

    Uses 301 Moved Permanently to indicate the routes have changed.

    Example:
        app = FastAPI()
        app.add_middleware(LegacyRedirectMiddleware)
    """

    REDIRECT_STATUS_CODE = 301

    def __init__(self, app: Any) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap
        """
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        """Handle an ASGI request.

        Args:
            scope: The ASGI scope
            receive: The receive callable
            send: The send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self._should_redirect(scope):
            await self._send_redirect(scope, send)
            return

        await self.app(scope, receive, send)

    def _should_redirect(self, scope: dict[str, Any]) -> bool:
        """Check if the request should be redirected.

        Args:
            scope: The ASGI scope

        Returns:
            True if redirect is needed
        """
        path = scope.get("path", "")
        return translate_legacy_path(path) is not None

    async def _send_redirect(
        self,
        scope: dict[str, Any],
        send: Any,
    ) -> None:
        """Send a 301 redirect response.

        Args:
            scope: The ASGI scope
            send: The send callable
        """
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode("utf-8")

        full_path = path
        if query_string:
            full_path += f"?{query_string}"

        new_location = translate_legacy_path(full_path)
        if new_location is None:
            # Should not happen since _should_redirect checked first
            return

        # Build redirect response
        await send(
            {
                "type": "http.response.start",
                "status": self.REDIRECT_STATUS_CODE,
                "headers": [
                    (b"location", new_location.encode("utf-8")),
                    (b"content-type", b"text/html; charset=utf-8"),
                ],
            }
        )

        body = f"""<!DOCTYPE html>
<html>
<head>
<title>301 Moved Permanently</title>
</head>
<body>
<h1>Moved Permanently</h1>
<p>This page has moved to <a href="{new_location}">{new_location}</a>.</p>
</body>
</html>""".encode()

        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
