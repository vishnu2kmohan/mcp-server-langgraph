"""
API Version Metadata Endpoint

Provides version information for API clients to determine compatibility and features.
Supports semantic versioning and breaking change detection.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings


router = APIRouter(prefix="/api", tags=["API Metadata"])


class APIVersionInfo(BaseModel):
    """
    API version metadata

    Follows semantic versioning (MAJOR.MINOR.PATCH):
    - MAJOR: Breaking changes (incompatible API changes)
    - MINOR: New features (backward-compatible)
    - PATCH: Bug fixes (backward-compatible)
    """

    version: str = Field(description="Application version (semantic versioning: MAJOR.MINOR.PATCH)", examples=["2.8.0"])
    api_version: str = Field(description="Current API version (e.g., 'v1')", examples=["v1"])
    supported_versions: list[str] = Field(description="List of supported API versions", examples=[["v1"]])
    deprecated_versions: list[str] = Field(
        description="List of deprecated API versions (still functional but will be removed)",
        default_factory=list,
        examples=[[]],
    )
    sunset_dates: dict[str, str] = Field(
        description="Sunset dates for deprecated versions (ISO 8601 format)", default_factory=dict, examples=[{}]
    )
    changelog_url: str | None = Field(
        None, description="URL to API changelog", examples=["https://docs.example.com/api/changelog"]
    )
    documentation_url: str | None = Field(
        None, description="URL to API documentation", examples=["https://docs.example.com/api/v1"]
    )


@router.get(
    "/version",
    response_model=APIVersionInfo,
    summary="Get API version information",
    description="""
    Returns API version metadata for client compatibility checking.

    **Versioning Strategy:**
    - **Semantic Versioning**: MAJOR.MINOR.PATCH
    - **URL Versioning**: `/api/v1`, `/api/v2`, etc.
    - **Header Negotiation**: `X-API-Version: 1.0` (optional)
    - **Deprecation Policy**: 6-month sunset period for deprecated versions

    **Breaking Changes:**
    - Removing fields from responses
    - Changing field types
    - Removing endpoints
    - Changing authentication methods

    **Non-Breaking Changes:**
    - Adding new endpoints
    - Adding new optional fields to requests
    - Adding new fields to responses
    - Adding new query parameters (optional)

    Use this endpoint to:
    - Check current API version
    - Determine if your client is compatible
    - Find out when deprecated versions will be removed
    - Locate API documentation
    """,
    responses={
        200: {
            "description": "API version information",
            "content": {
                "application/json": {
                    "example": {
                        "version": "2.8.0",
                        "api_version": "v1",
                        "supported_versions": ["v1"],
                        "deprecated_versions": [],
                        "sunset_dates": {},
                        "changelog_url": None,
                        "documentation_url": "/docs",
                    }
                }
            },
        }
    },
    operation_id="get_api_version_metadata",
)  # type: ignore[misc]  # FastAPI decorator lacks complete type stubs
async def get_version() -> APIVersionInfo:
    """
    Get API version metadata

    Returns current version, supported versions, and deprecation information.
    """
    return APIVersionInfo(
        version=settings.service_version,
        api_version="v1",
        supported_versions=["v1"],
        deprecated_versions=[],
        sunset_dates={},
        changelog_url=None,
        documentation_url="/docs",
    )
