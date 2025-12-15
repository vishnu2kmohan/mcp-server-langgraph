"""
Tests for MCP Connection Templates API

TDD: Tests for pre-configured connection templates that make it easy
to set up connections to common MCP servers (GitHub, Slack, etc.).

Follows memory safety patterns for pytest-xdist.
"""

import gc

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


# ============================================================================
# Mock Data and Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Create a test FastAPI app with the templates router."""
    from mcp_server_langgraph.api.v1.connection_templates import templates_router

    app = FastAPI()
    app.include_router(templates_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Template List Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestListTemplates:
    """Tests for GET /connection-templates"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_templates_returns_all(self, client):
        """Should return list of all available templates."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0

    def test_list_templates_includes_github(self, client):
        """Should include GitHub MCP template."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]
        github_templates = [t for t in templates if t["id"] == "github"]
        assert len(github_templates) == 1
        assert github_templates[0]["name"] == "GitHub"

    def test_list_templates_includes_slack(self, client):
        """Should include Slack MCP template."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]
        slack_templates = [t for t in templates if t["id"] == "slack"]
        assert len(slack_templates) == 1
        assert slack_templates[0]["name"] == "Slack"

    def test_list_templates_includes_notion(self, client):
        """Should include Notion MCP template."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]
        notion_templates = [t for t in templates if t["id"] == "notion"]
        assert len(notion_templates) == 1
        assert notion_templates[0]["name"] == "Notion"

    def test_template_has_required_fields(self, client):
        """Each template should have required fields."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]

        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "icon" in template
            assert "auth_type" in template
            assert "default_url" in template
            assert "category" in template

    def test_list_templates_filter_by_category(self, client):
        """Should filter templates by category."""
        response = client.get("/connection-templates?category=productivity")
        assert response.status_code == 200
        templates = response.json()["templates"]
        for template in templates:
            assert template["category"] == "productivity"

    def test_list_templates_filter_by_auth_type(self, client):
        """Should filter templates by authentication type."""
        response = client.get("/connection-templates?auth_type=oauth2")
        assert response.status_code == 200
        templates = response.json()["templates"]
        for template in templates:
            assert template["auth_type"] == "oauth2"

    def test_list_templates_search(self, client):
        """Should search templates by name."""
        response = client.get("/connection-templates?search=git")
        assert response.status_code == 200
        templates = response.json()["templates"]
        assert len(templates) >= 1
        for template in templates:
            assert "git" in template["name"].lower() or "git" in template["description"].lower()


# ============================================================================
# Get Template Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestGetTemplate:
    """Tests for GET /connection-templates/{template_id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_template_exists(self, client):
        """Should return template details."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "github"
        assert data["name"] == "GitHub"

    def test_get_template_not_found(self, client):
        """Should return 404 for nonexistent template."""
        response = client.get("/connection-templates/nonexistent")
        assert response.status_code == 404

    def test_get_template_includes_config_fields(self, client):
        """Should include configuration fields required for setup."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert "config_fields" in data
        # GitHub should require OAuth2 configuration
        assert any(f["name"] == "oauth2_client_id" for f in data["config_fields"])

    def test_get_template_includes_oauth2_scopes(self, client):
        """OAuth2 templates should include recommended scopes."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        if data["auth_type"] == "oauth2":
            assert "oauth2_scopes" in data
            assert len(data["oauth2_scopes"]) > 0


# ============================================================================
# Template Categories Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestTemplateCategories:
    """Tests for GET /connection-templates/categories"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_categories(self, client):
        """Should return list of template categories."""
        response = client.get("/connection-templates/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_categories_include_common(self, client):
        """Should include common categories."""
        response = client.get("/connection-templates/categories")
        assert response.status_code == 200
        categories = response.json()["categories"]
        category_ids = [c["id"] for c in categories]
        assert "development" in category_ids
        assert "productivity" in category_ids
        assert "communication" in category_ids


# ============================================================================
# Apply Template Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestApplyTemplate:
    """Tests for POST /connection-templates/{template_id}/apply"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_apply_template_returns_connection_config(self, client):
        """Should return pre-filled connection configuration."""
        response = client.post(
            "/connection-templates/github/apply",
            json={
                "name": "My GitHub",
                "oauth2_client_id": "my-client-id",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "connection" in data
        assert data["connection"]["name"] == "My GitHub"
        assert data["connection"]["auth_type"] == "oauth2"

    def test_apply_template_not_found(self, client):
        """Should return 404 for nonexistent template."""
        response = client.post(
            "/connection-templates/nonexistent/apply",
            json={"name": "Test"},
        )
        assert response.status_code == 404

    def test_apply_template_validates_required_fields(self, client):
        """Should validate required configuration fields."""
        response = client.post(
            "/connection-templates/github/apply",
            json={
                # Missing name
                "oauth2_client_id": "my-client-id",
            },
        )
        assert response.status_code == 422

    def test_apply_template_includes_defaults(self, client):
        """Should include default values from template."""
        response = client.post(
            "/connection-templates/github/apply",
            json={
                "name": "My GitHub",
                "oauth2_client_id": "my-client-id",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Should have default URL from template
        assert "url" in data["connection"]
        assert data["connection"]["url"] == "https://api.github.com/mcp"


# ============================================================================
# Specific Template Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestSpecificTemplates:
    """Tests for specific template configurations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_github_template_config(self, client):
        """GitHub template should have correct configuration."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "oauth2"
        assert data["default_url"] == "https://api.github.com/mcp"
        assert data["category"] == "development"
        assert "repo" in data.get("oauth2_scopes", [])

    def test_slack_template_config(self, client):
        """Slack template should have correct configuration."""
        response = client.get("/connection-templates/slack")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "oauth2"
        assert data["category"] == "communication"

    def test_notion_template_config(self, client):
        """Notion template should have correct configuration."""
        response = client.get("/connection-templates/notion")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "oauth2"
        assert data["category"] == "productivity"

    def test_filesystem_template_config(self, client):
        """Filesystem template should use no auth."""
        response = client.get("/connection-templates/filesystem")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "none"
        assert data["category"] == "local"

    def test_custom_api_template_config(self, client):
        """Custom API template should use API key auth."""
        response = client.get("/connection-templates/custom-api")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "api_key"
