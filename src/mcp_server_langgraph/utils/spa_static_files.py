"""
SPA Static Files handler for React frontends.

Provides a FastAPI-compatible StaticFiles mount that serves single-page applications
with proper client-side routing support (fallback to index.html for non-file routes).

Features:
- Serves static assets (JS, CSS, images) normally
- Falls back to index.html for client-side routes (React Router, etc.)
- Returns 404 for missing static files (files with extensions)
- Optional caching headers for production performance

Usage:
    from mcp_server_langgraph.utils.spa_static_files import SPAStaticFiles

    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory="frontend/dist", html=True), name="spa")

Note: Mount SPA AFTER all API routes to ensure APIs take precedence.
"""

from pathlib import Path

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """
    StaticFiles mount that supports single-page application routing.

    When a file is not found, this handler checks if the request looks like
    a client-side route (no file extension) and serves index.html instead.
    This enables React Router, Vue Router, etc. to handle the routing.

    For requests with file extensions (e.g., /assets/app.js), it returns 404
    if the file doesn't exist.

    Args:
        directory: Path to the static files directory
        html: Whether to enable HTML mode (required for SPA)
        caching: Whether to add cache-control headers for static assets

    Raises:
        RuntimeError: If directory doesn't exist or index.html is missing
    """

    def __init__(
        self,
        *,
        directory: str,
        html: bool = True,
        caching: bool = False,
    ) -> None:
        """Initialize SPAStaticFiles with validation."""
        self.directory_path = Path(directory).resolve()
        self.caching = caching

        # Validate directory exists
        if not self.directory_path.exists():
            msg = f"Static files directory does not exist: {directory}"
            raise RuntimeError(msg)

        # Validate index.html exists
        index_path = self.directory_path / "index.html"
        if not index_path.exists():
            msg = f"index.html not found in {directory}. SPA requires index.html."
            raise RuntimeError(msg)

        super().__init__(directory=directory, html=html)

    async def get_response(self, path: str, scope: dict) -> Response:
        """
        Get response for the requested path.

        If the file exists, serve it. If not, and the path looks like a
        client-side route (no extension), serve index.html.

        Args:
            path: Requested path (e.g., "assets/app.js" or "dashboard")
            scope: ASGI scope

        Returns:
            Response with file content or index.html fallback
        """
        try:
            # Try to serve the requested file
            response = await super().get_response(path, scope)

            # Add caching headers if enabled
            if self.caching:
                response = self._add_cache_headers(path, response)

            return response

        except Exception as ex:
            # Check if this is a 404-like error
            # HTTPException has status_code, starlette raises it for missing files
            status_code = getattr(ex, "status_code", None)

            if status_code == 404:
                # Check if this looks like a static file request (has extension)
                if "." in path.split("/")[-1]:
                    # Missing static file - return 404
                    raise

                # Looks like a client-side route - serve index.html
                response = await super().get_response("index.html", scope)

                # Don't cache index.html (always serve fresh)
                if self.caching:
                    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

                return response

            # Re-raise other errors
            raise

    def _add_cache_headers(self, path: str, response: Response) -> Response:
        """
        Add appropriate cache headers based on file type.

        Static assets (JS, CSS, images) get long cache times.
        index.html gets no-cache to ensure fresh content.

        Args:
            path: File path
            response: Response object

        Returns:
            Response with cache headers
        """
        # index.html should never be cached
        if path == "" or path == "index.html":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

        # Static assets with extensions can be cached
        file_ext = Path(path).suffix.lower()
        cacheable_extensions = {".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf"}

        if file_ext in cacheable_extensions:
            # Long cache time for immutable assets (Vite adds content hashes)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response


def create_spa_static_files(
    directory: str,
    *,
    caching: bool = False,
) -> SPAStaticFiles | None:
    """
    Factory function to create SPAStaticFiles handler.

    Returns None if the directory doesn't exist or is invalid,
    allowing graceful degradation when frontend is not built.

    Args:
        directory: Path to static files directory
        caching: Whether to add cache-control headers

    Returns:
        SPAStaticFiles instance or None if directory invalid
    """
    try:
        return SPAStaticFiles(directory=directory, html=True, caching=caching)
    except RuntimeError:
        return None
