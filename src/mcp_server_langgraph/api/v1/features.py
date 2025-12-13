"""
Features Router

Provides UI feature flags to the frontend based on user role.

Usage:
    GET /api/v1/features - Get features for default (user) role
    GET /api/v1/features?role=admin - Get features for admin role
"""

from fastapi import APIRouter, Query

from mcp_server_langgraph.core.feature_flags import get_feature_flags

features_router = APIRouter(tags=["features"])


@features_router.get("/features")
async def get_features(
    role: str = Query(
        default="user",
        description="User role for feature access (user, admin, viewer)",
        examples=["user", "admin"],
    ),
) -> dict[str, bool]:
    """
    Get UI feature availability based on user role.

    Returns a dictionary of feature names to boolean enabled status.
    Admins get access to all features, while regular users may have
    restricted access to certain features (e.g., cost dashboard).

    Args:
        role: User role for determining feature access.

    Returns:
        Dictionary mapping feature names to their enabled status.

    Example Response:
        {
            "workflows": true,
            "sessions": true,
            "cost_dashboard": false,
            "observability": true,
            "code_export": true,
            "ai_suggestions": true,
            "mcp_websocket": false
        }
    """
    flags = get_feature_flags()
    return flags.get_ui_features_for_role(role)
