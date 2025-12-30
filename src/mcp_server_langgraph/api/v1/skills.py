"""
Skills API Endpoints.

Provides REST API for skill management and auto-update operations.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from mcp_server_langgraph.auth.dependencies import require_admin
from mcp_server_langgraph.skills.auto_update import get_auto_update_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/skills", tags=["skills"])

# Type alias for admin user dependency
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]


@router.get("/updates")
async def check_skill_updates(admin_user: AdminUser) -> dict[str, Any]:
    """Check for available skill updates.

    Requires admin authorization.

    Returns:
        Dict with list of available updates
    """
    try:
        scheduler = get_auto_update_scheduler()
        updates = await scheduler.check_updates_available()

        return {
            "updates": [
                {
                    "skill_name": u.skill_name,
                    "current_version": u.current_version,
                    "new_version": u.new_version,
                    "marketplace": u.marketplace,
                    "changelog": u.changelog,
                }
                for u in updates
            ],
            "count": len(updates),
        }
    except Exception as e:
        logger.exception(f"Failed to check skill updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check updates: {e}",
        )


@router.post("/updates/apply")
async def apply_skill_updates(admin_user: AdminUser) -> dict[str, Any]:
    """Apply all available skill updates.

    Requires admin authorization.

    Returns:
        Dict with list of applied updates
    """
    try:
        scheduler = get_auto_update_scheduler()
        results = await scheduler.apply_updates()

        return {
            "applied": results,
            "count": len(results),
            "success_count": sum(1 for r in results if r.get("success", False)),
        }
    except Exception as e:
        logger.exception(f"Failed to apply skill updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply updates: {e}",
        )
