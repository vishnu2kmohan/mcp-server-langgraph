"""
DevTools-specific APIs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from mcp_server_langgraph.auth.dependencies import require_observability_viewer

devtools_router = APIRouter(tags=["devtools"])


@devtools_router.get(
    "/devtools/services",
    response_model=list[str],
    summary="List known services for DevTools filters",
)
async def list_devtools_services(
    _viewer: dict[str, object] = Depends(require_observability_viewer),
) -> list[str]:
    """
    Return distinct service names based on Loki labels.

    Best-effort: on failure, returns an empty list rather than raising.
    """
    try:
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )
    except Exception as exc:  # pragma: no cover - import guarded
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Logging backend unavailable: {exc}",
        ) from exc

    client = LokiLoggingClient()
    services: list[str] = []
    try:
        services = await client.list_services()
    finally:
        try:
            await client.close()
        except Exception:
            pass

    return services
