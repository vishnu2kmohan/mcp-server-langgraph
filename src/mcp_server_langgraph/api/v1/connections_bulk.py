"""
MCP Connections Bulk Operations API

Implements bulk operations for MCP connections:
- Bulk delete
- Bulk test (health check)
- Bulk status update

Usage:
    from mcp_server_langgraph.api.v1.connections_bulk import bulk_router
    app.include_router(bulk_router)
"""

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.dependencies import (
    MCPClient,
    get_connection_repository,
    get_mcp_client,
)
from mcp_server_langgraph.repositories.connections import ConnectionRepository


# ============================================================================
# Request/Response Models
# ============================================================================


class BulkDeleteRequest(BaseModel):
    """Request for bulk delete operation."""

    connection_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of connection IDs to delete (max 100)",
    )


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operation."""

    deleted_count: int
    failed_ids: list[str] = Field(default_factory=list)


class BulkTestRequest(BaseModel):
    """Request for bulk test operation."""

    connection_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of connection IDs to test (max 50)",
    )


class ConnectionTestResult(BaseModel):
    """Result of testing a single connection."""

    connection_id: str
    success: bool
    server_name: str | None = None
    server_version: str | None = None
    tool_count: int = 0
    error: str | None = None


class BulkTestResponse(BaseModel):
    """Response for bulk test operation."""

    results: list[ConnectionTestResult]
    not_found: list[str] = Field(default_factory=list)


class BulkStatusRequest(BaseModel):
    """Request for bulk status update."""

    connection_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of connection IDs to update (max 100)",
    )
    status: Literal["disconnected", "connecting", "connected", "error", "auth_required"]


class BulkStatusResponse(BaseModel):
    """Response for bulk status update."""

    updated_count: int
    failed_ids: list[str] = Field(default_factory=list)


# ============================================================================
# Router
# ============================================================================

bulk_router = APIRouter(prefix="/connections/bulk", tags=["connections-bulk"])


@bulk_router.post("/delete")
async def bulk_delete(
    request: BulkDeleteRequest,
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> BulkDeleteResponse:
    """
    Delete multiple connections at once.

    Performs best-effort deletion - returns count of successfully deleted
    connections and list of IDs that failed.
    """
    deleted_count = 0
    failed_ids: list[str] = []

    for connection_id in request.connection_ids:
        success = await repo.delete(connection_id)
        if success:
            deleted_count += 1
        else:
            failed_ids.append(connection_id)

    return BulkDeleteResponse(
        deleted_count=deleted_count,
        failed_ids=failed_ids,
    )


@bulk_router.post("/test")
async def bulk_test(
    request: BulkTestRequest,
    repo: ConnectionRepository = Depends(get_connection_repository),
    mcp_client: MCPClient = Depends(get_mcp_client),
) -> BulkTestResponse:
    """
    Test multiple connections at once.

    Performs parallel health checks and updates connection status.
    Returns test results for each connection.
    """
    # Get all connections
    connections = await repo.get_many(request.connection_ids)
    connection_map = {c.id: c for c in connections}

    # Find not found IDs
    found_ids = set(connection_map.keys())
    not_found = [cid for cid in request.connection_ids if cid not in found_ids]

    # Test connections in parallel
    async def test_single(connection_id: str) -> ConnectionTestResult:
        connection = connection_map.get(connection_id)
        if not connection:
            return ConnectionTestResult(
                connection_id=connection_id,
                success=False,
                error="Connection not found",
            )

        try:
            result = await mcp_client.test_connection(connection.url)

            # Update connection status
            if result.success:
                await repo.update_status(
                    connection_id=connection_id,
                    status="connected",
                    server_name=result.server_name,
                    server_version=result.server_version,
                    tool_count=result.tool_count,
                    resource_count=result.resource_count,
                    prompt_count=result.prompt_count,
                )
            else:
                await repo.update_status(
                    connection_id=connection_id,
                    status="error",
                    last_error=result.error,
                )

            return ConnectionTestResult(
                connection_id=connection_id,
                success=result.success,
                server_name=result.server_name,
                server_version=result.server_version,
                tool_count=result.tool_count,
                error=result.error,
            )
        except Exception as e:
            await repo.update_status(
                connection_id=connection_id,
                status="error",
                last_error=str(e),
            )
            return ConnectionTestResult(
                connection_id=connection_id,
                success=False,
                error=str(e),
            )

    # Run tests in parallel
    tasks = [test_single(cid) for cid in found_ids]
    results = await asyncio.gather(*tasks)

    return BulkTestResponse(
        results=list(results),
        not_found=not_found,
    )


@bulk_router.post("/status")
async def bulk_status_update(
    request: BulkStatusRequest,
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> BulkStatusResponse:
    """
    Update status for multiple connections.

    Useful for disconnecting all connections or marking them for re-authentication.
    """
    updated_count = 0
    failed_ids: list[str] = []

    for connection_id in request.connection_ids:
        connection = await repo.get(connection_id)
        if connection:
            await repo.update_status(connection_id, request.status)
            updated_count += 1
        else:
            failed_ids.append(connection_id)

    return BulkStatusResponse(
        updated_count=updated_count,
        failed_ids=failed_ids,
    )
