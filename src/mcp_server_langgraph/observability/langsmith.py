"""
LangSmith configuration and integration for LangGraph agent observability
"""

import os
from typing import Any

from mcp_server_langgraph.core.config import settings


def configure_langsmith() -> bool:
    """
    Configure LangSmith tracing using environment variables.

    Returns:
        bool: True if LangSmith is configured and enabled, False otherwise
    """
    if not settings.langsmith_tracing:
        return False

    # Set LangSmith environment variables for automatic tracing
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key  # Alias

    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langsmith_tracing_v2).lower()
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint

    print("✓ LangSmith tracing configured")
    print(f"  - Project: {settings.langsmith_project}")
    print(f"  - Endpoint: {settings.langsmith_endpoint}")
    print(f"  - Tracing V2: {settings.langsmith_tracing_v2}")

    return True


def get_run_metadata(
    user_id: str | None = None, request_id: str | None = None, additional_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Create metadata for LangSmith runs.

    Args:
        user_id: User identifier
        request_id: Request identifier for correlation
        additional_metadata: Additional custom metadata

    Returns:
        Dictionary of metadata for LangSmith runs
    """
    metadata = {
        "environment": settings.environment,
        "service_name": settings.service_name,
        "service_version": settings.service_version,
        "model_name": settings.model_name,
        "llm_provider": settings.llm_provider,
    }

    if user_id:
        metadata["user_id"] = user_id

    if request_id:
        metadata["request_id"] = request_id

    if additional_metadata:
        metadata.update(additional_metadata)

    return metadata


def get_run_tags(user_id: str | None = None, additional_tags: list[str] | None = None) -> list[str]:
    """
    Create tags for LangSmith runs.

    Args:
        user_id: User identifier to include as tag
        additional_tags: Additional custom tags

    Returns:
        List of tags for the run
    """
    tags = [
        settings.environment,
        settings.llm_provider,
        f"model:{settings.model_name}",
    ]

    if user_id:
        tags.append(f"user:{user_id}")

    if additional_tags:
        tags.extend(additional_tags)

    return tags


class LangSmithConfig:
    """LangSmith configuration helper class"""

    def __init__(self) -> None:
        self.enabled = configure_langsmith()

    def is_enabled(self) -> bool:
        """Check if LangSmith is enabled"""
        return self.enabled

    def get_client_kwargs(self) -> dict[str, Any]:
        """
        Get kwargs for LangSmith Client initialization.

        Returns:
            Dictionary of client configuration
        """
        if not self.enabled:
            return {}

        return {
            "api_key": settings.langsmith_api_key,
            "api_url": settings.langsmith_endpoint,
        }

    def create_run_config(
        self,
        run_name: str,
        user_id: str | None = None,
        request_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a run configuration for LangChain/LangGraph execution.

        Args:
            run_name: Name of the run
            user_id: User identifier
            request_id: Request identifier
            tags: Custom tags
            metadata: Custom metadata

        Returns:
            Run configuration dictionary
        """
        config = {
            "run_name": run_name,
            "project_name": settings.langsmith_project,
            "tags": get_run_tags(user_id, tags),
            "metadata": get_run_metadata(user_id, request_id, metadata),
        }

        return config


# Global instance
langsmith_config = LangSmithConfig()
