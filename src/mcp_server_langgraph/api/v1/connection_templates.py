"""
MCP Connection Templates API Endpoints

Provides pre-configured templates for common MCP servers (GitHub, Slack, etc.)
to simplify connection setup.

Usage:
    from mcp_server_langgraph.api.v1.connection_templates import templates_router
    app.include_router(templates_router)
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field


# ============================================================================
# Models
# ============================================================================


class ConfigField(BaseModel):
    """Configuration field definition for a template."""

    name: str
    label: str
    type: Literal["text", "password", "url", "textarea"]
    required: bool = True
    placeholder: str | None = None
    description: str | None = None
    default: str | None = None


class ConnectionTemplate(BaseModel):
    """MCP connection template definition."""

    id: str
    name: str
    description: str
    icon: str
    auth_type: Literal["none", "api_key", "oauth2"]
    default_url: str
    category: str
    oauth2_scopes: list[str] = Field(default_factory=list)
    config_fields: list[ConfigField] = Field(default_factory=list)


class TemplateCategory(BaseModel):
    """Template category."""

    id: str
    name: str
    description: str


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: list[ConnectionTemplate]


class CategoryListResponse(BaseModel):
    """Response for listing categories."""

    categories: list[TemplateCategory]


class ApplyTemplateRequest(BaseModel):
    """Request to apply a template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    oauth2_client_id: str | None = None
    oauth2_scopes: list[str] | None = None
    api_key: str | None = None
    url: str | None = None
    project_id: str | None = None


class ConnectionConfig(BaseModel):
    """Pre-filled connection configuration."""

    name: str
    description: str | None
    url: str
    auth_type: Literal["none", "api_key", "oauth2"]
    oauth2_client_id: str | None = None
    oauth2_scopes: list[str] | None = None


class ApplyTemplateResponse(BaseModel):
    """Response from applying a template."""

    connection: ConnectionConfig


# ============================================================================
# Template Data
# ============================================================================

CATEGORIES: list[TemplateCategory] = [
    TemplateCategory(
        id="development",
        name="Development",
        description="Tools for software development workflows",
    ),
    TemplateCategory(
        id="productivity",
        name="Productivity",
        description="Productivity and project management tools",
    ),
    TemplateCategory(
        id="communication",
        name="Communication",
        description="Team communication and collaboration tools",
    ),
    TemplateCategory(
        id="local",
        name="Local",
        description="Local system and filesystem access",
    ),
    TemplateCategory(
        id="custom",
        name="Custom",
        description="Custom API integrations",
    ),
]

TEMPLATES: list[ConnectionTemplate] = [
    ConnectionTemplate(
        id="github",
        name="GitHub",
        description="Access GitHub repositories, issues, and pull requests",
        icon="github",
        auth_type="oauth2",
        default_url="https://api.github.com/mcp",
        category="development",
        oauth2_scopes=["repo", "user", "read:org"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your GitHub OAuth App Client ID",
                description="Create at https://github.com/settings/developers",
            ),
            ConfigField(
                name="oauth2_scopes",
                label="Scopes",
                type="text",
                required=False,
                placeholder="repo,user,read:org",
                default="repo,user,read:org",
                description="Comma-separated list of GitHub OAuth scopes",
            ),
        ],
    ),
    ConnectionTemplate(
        id="slack",
        name="Slack",
        description="Access Slack workspaces, channels, and messages",
        icon="slack",
        auth_type="oauth2",
        default_url="https://slack.com/api/mcp",
        category="communication",
        oauth2_scopes=["channels:read", "chat:write", "users:read"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your Slack App Client ID",
                description="Create at https://api.slack.com/apps",
            ),
        ],
    ),
    ConnectionTemplate(
        id="notion",
        name="Notion",
        description="Access Notion workspaces, pages, and databases",
        icon="notion",
        auth_type="oauth2",
        default_url="https://api.notion.com/mcp",
        category="productivity",
        oauth2_scopes=["read", "write"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your Notion Integration Client ID",
                description="Create at https://www.notion.so/my-integrations",
            ),
        ],
    ),
    ConnectionTemplate(
        id="gitlab",
        name="GitLab",
        description="Access GitLab repositories, issues, and merge requests",
        icon="gitlab",
        auth_type="oauth2",
        default_url="https://gitlab.com/api/v4/mcp",
        category="development",
        oauth2_scopes=["api", "read_user", "read_repository"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your GitLab Application ID",
                description="Create at https://gitlab.com/-/profile/applications",
            ),
            ConfigField(
                name="url",
                label="GitLab URL",
                type="url",
                required=False,
                placeholder="https://gitlab.com",
                default="https://gitlab.com",
                description="For self-hosted GitLab instances",
            ),
        ],
    ),
    ConnectionTemplate(
        id="jira",
        name="Jira",
        description="Access Jira projects, issues, and boards",
        icon="jira",
        auth_type="oauth2",
        default_url="https://api.atlassian.com/mcp",
        category="productivity",
        oauth2_scopes=["read:jira-work", "write:jira-work", "read:jira-user"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your Atlassian OAuth2 Client ID",
                description="Create at https://developer.atlassian.com/console/myapps/",
            ),
        ],
    ),
    ConnectionTemplate(
        id="linear",
        name="Linear",
        description="Access Linear issues, projects, and cycles",
        icon="linear",
        auth_type="oauth2",
        default_url="https://api.linear.app/mcp",
        category="productivity",
        oauth2_scopes=["read", "write"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your Linear OAuth Application ID",
                description="Create at https://linear.app/settings/api",
            ),
        ],
    ),
    ConnectionTemplate(
        id="discord",
        name="Discord",
        description="Access Discord servers, channels, and messages",
        icon="discord",
        auth_type="oauth2",
        default_url="https://discord.com/api/mcp",
        category="communication",
        oauth2_scopes=["bot", "messages.read"],
        config_fields=[
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your Discord Application Client ID",
                description="Create at https://discord.com/developers/applications",
            ),
        ],
    ),
    ConnectionTemplate(
        id="filesystem",
        name="Filesystem",
        description="Access local filesystem for reading and writing files",
        icon="folder",
        auth_type="none",
        default_url="http://localhost:3001",
        category="local",
        config_fields=[
            ConfigField(
                name="url",
                label="MCP Server URL",
                type="url",
                required=False,
                placeholder="http://localhost:3001",
                default="http://localhost:3001",
                description="URL of the local filesystem MCP server",
            ),
        ],
    ),
    ConnectionTemplate(
        id="sqlite",
        name="SQLite",
        description="Access SQLite databases for querying and data manipulation",
        icon="database",
        auth_type="none",
        default_url="http://localhost:3002",
        category="local",
        config_fields=[
            ConfigField(
                name="url",
                label="MCP Server URL",
                type="url",
                required=False,
                placeholder="http://localhost:3002",
                default="http://localhost:3002",
                description="URL of the SQLite MCP server",
            ),
        ],
    ),
    ConnectionTemplate(
        id="custom-api",
        name="Custom API",
        description="Connect to any MCP server using API key authentication",
        icon="key",
        auth_type="api_key",
        default_url="https://your-mcp-server.example.com",
        category="custom",
        config_fields=[
            ConfigField(
                name="url",
                label="MCP Server URL",
                type="url",
                required=True,
                placeholder="https://your-mcp-server.example.com",
                description="The URL of your MCP server",
            ),
            ConfigField(
                name="api_key",
                label="API Key",
                type="password",
                required=True,
                placeholder="Your API key",
                description="The API key for authentication",
            ),
        ],
    ),
    ConnectionTemplate(
        id="custom-oauth2",
        name="Custom OAuth2",
        description="Connect to any MCP server using OAuth2 authentication",
        icon="lock",
        auth_type="oauth2",
        default_url="https://your-mcp-server.example.com",
        category="custom",
        oauth2_scopes=[],
        config_fields=[
            ConfigField(
                name="url",
                label="MCP Server URL",
                type="url",
                required=True,
                placeholder="https://your-mcp-server.example.com",
                description="The URL of your MCP server",
            ),
            ConfigField(
                name="oauth2_client_id",
                label="OAuth2 Client ID",
                type="text",
                required=True,
                placeholder="Your OAuth2 Client ID",
                description="The OAuth2 client ID for your application",
            ),
            ConfigField(
                name="oauth2_scopes",
                label="Scopes",
                type="text",
                required=False,
                placeholder="scope1,scope2",
                description="Comma-separated list of OAuth scopes",
            ),
        ],
    ),
]

# Create lookup dict for faster access
TEMPLATES_BY_ID = {t.id: t for t in TEMPLATES}


# ============================================================================
# Router
# ============================================================================

templates_router = APIRouter(prefix="/connection-templates", tags=["connection-templates"])


@templates_router.get("/categories")
async def list_categories() -> CategoryListResponse:
    """
    List all template categories.

    Returns list of categories that templates can belong to.
    """
    return CategoryListResponse(categories=CATEGORIES)


@templates_router.get("")
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    auth_type: Literal["none", "api_key", "oauth2"] | None = Query(None, description="Filter by authentication type"),
    search: str | None = Query(None, min_length=1, description="Search by name or description"),
) -> TemplateListResponse:
    """
    List all available connection templates.

    Supports filtering by category, authentication type, and search.
    """
    templates = TEMPLATES.copy()

    # Filter by category
    if category:
        templates = [t for t in templates if t.category == category]

    # Filter by auth type
    if auth_type:
        templates = [t for t in templates if t.auth_type == auth_type]

    # Search by name or description
    if search:
        search_lower = search.lower()
        templates = [t for t in templates if search_lower in t.name.lower() or search_lower in t.description.lower()]

    return TemplateListResponse(templates=templates)


@templates_router.get("/{template_id}")
async def get_template(template_id: str) -> ConnectionTemplate:
    """
    Get a specific template by ID.

    Returns full template details including configuration fields.
    """
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    return template


@templates_router.post("/{template_id}/apply")
async def apply_template(
    template_id: str,
    request: ApplyTemplateRequest,
) -> ApplyTemplateResponse:
    """
    Apply a template to create a pre-filled connection configuration.

    Takes the template and user-provided values to generate a connection
    configuration that can be used to create a new connection.
    """
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    # Use provided URL or template default
    url = request.url or template.default_url

    # Use provided scopes or template defaults
    oauth2_scopes = request.oauth2_scopes or template.oauth2_scopes

    connection = ConnectionConfig(
        name=request.name,
        description=request.description or template.description,
        url=url,
        auth_type=template.auth_type,
        oauth2_client_id=request.oauth2_client_id if template.auth_type == "oauth2" else None,
        oauth2_scopes=oauth2_scopes if template.auth_type == "oauth2" else None,
    )

    return ApplyTemplateResponse(connection=connection)
