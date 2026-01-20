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
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(templates_router)

    # Mock authenticated user
    mock_user = {
        "sub": "user-123",
        "preferred_username": "testuser",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

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

    def test_list_categories_returns_available_template_categories(self, client):
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


# ============================================================================
# Template Enhanced Fields Tests (ADR-0102)
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestTemplateEnhancedFields:
    """Tests for enhanced template fields: keywords, popularity, documentation_url."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_template_includes_keywords_field(self, client):
        """Each template should include keywords list for intent matching."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
        assert isinstance(data["keywords"], list)

    def test_github_has_relevant_keywords(self, client):
        """GitHub template should have relevant keywords for intent matching."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        keywords = data.get("keywords", [])
        # Should include terms users might use when asking about GitHub
        assert "github" in keywords
        assert "repository" in keywords or "repo" in keywords

    def test_template_includes_popularity_field(self, client):
        """Each template should include popularity score."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert "popularity" in data
        assert isinstance(data["popularity"], int)
        assert 0 <= data["popularity"] <= 100

    def test_popular_templates_have_high_popularity(self, client):
        """Popular templates (GitHub, Slack) should have high popularity scores."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]

        github = next((t for t in templates if t["id"] == "github"), None)
        slack = next((t for t in templates if t["id"] == "slack"), None)

        assert github is not None
        assert slack is not None
        assert github["popularity"] >= 80
        assert slack["popularity"] >= 80

    def test_template_includes_documentation_url_field(self, client):
        """Templates should include optional documentation URL."""
        response = client.get("/connection-templates/github")
        assert response.status_code == 200
        data = response.json()
        assert "documentation_url" in data
        # GitHub should have docs URL
        assert data["documentation_url"] is not None
        assert "github" in data["documentation_url"].lower()

    def test_all_templates_have_enhanced_fields(self, client):
        """All templates should have keywords, popularity, and documentation_url fields."""
        response = client.get("/connection-templates")
        assert response.status_code == 200
        templates = response.json()["templates"]

        for template in templates:
            # keywords should be list (can be empty)
            assert "keywords" in template, f"Template {template['id']} missing keywords"
            assert isinstance(template["keywords"], list)

            # popularity should be 0-100
            assert "popularity" in template, f"Template {template['id']} missing popularity"
            assert 0 <= template["popularity"] <= 100

            # documentation_url can be null
            assert "documentation_url" in template, f"Template {template['id']} missing documentation_url"


# ============================================================================
# Template Suggestions Tests (ADR-0102)
# ============================================================================


@pytest.mark.xdist_group(name="connection_templates_api")
class TestTemplateSuggestions:
    """Tests for GET /connection-templates/suggestions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_suggestions_returns_matching_templates(self, client):
        """Should return templates matching query keywords."""
        response = client.get("/connection-templates/suggestions?query=github pull request")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        # GitHub should match query about PRs
        template_ids = [t["id"] for t in data["templates"]]
        assert "github" in template_ids

    def test_suggestions_respects_limit(self, client):
        """Should respect limit parameter."""
        response = client.get("/connection-templates/suggestions?query=api&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) <= 2

    def test_suggestions_default_limit_is_three(self, client):
        """Default limit should be 3."""
        response = client.get("/connection-templates/suggestions?query=oauth")
        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) <= 3

    def test_suggestions_requires_query(self, client):
        """Should require query parameter."""
        response = client.get("/connection-templates/suggestions")
        assert response.status_code == 422

    def test_suggestions_query_minimum_length(self, client):
        """Query should have minimum length."""
        response = client.get("/connection-templates/suggestions?query=")
        assert response.status_code == 422

    def test_suggestions_matches_by_name(self, client):
        """Should match templates by name."""
        response = client.get("/connection-templates/suggestions?query=slack")
        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data["templates"]]
        assert "slack" in template_ids

    def test_suggestions_matches_by_keywords(self, client):
        """Should match templates by keywords."""
        response = client.get("/connection-templates/suggestions?query=channel message")
        assert response.status_code == 200
        data = response.json()
        # Slack has channel/message keywords
        template_ids = [t["id"] for t in data["templates"]]
        assert "slack" in template_ids

    def test_suggestions_sorted_by_relevance(self, client):
        """Results should be sorted by match relevance, then popularity."""
        response = client.get("/connection-templates/suggestions?query=github repo")
        assert response.status_code == 200
        data = response.json()
        # GitHub should be first for this query
        if len(data["templates"]) > 0:
            assert data["templates"][0]["id"] == "github"

    def test_suggestions_returns_total_count(self, client):
        """Should return total count of matches."""
        response = client.get("/connection-templates/suggestions?query=oauth")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_suggestions_returns_empty_for_no_match(self, client):
        """Should return empty list for queries with no matches."""
        response = client.get("/connection-templates/suggestions?query=nonexistentxyz123")
        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []
        assert data["total"] == 0
