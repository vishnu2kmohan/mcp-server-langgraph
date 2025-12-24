"""
User storage module.

Provides PostgreSQL-backed storage for user preferences, including:
- Sub-persona selection
- Feature flags
- UI preferences

Usage:
    from mcp_server_langgraph.storage.user import UserPreferencesRepository, UserPreferences
"""

from mcp_server_langgraph.storage.user.models import UserPreferences
from mcp_server_langgraph.storage.user.postgres_models import UserPreferencesModel
from mcp_server_langgraph.storage.user.repository import UserPreferencesRepository

__all__ = [
    "UserPreferences",
    "UserPreferencesModel",
    "UserPreferencesRepository",
]
