"""
Unit tests for Skills Marketplace API endpoints.

Tests for:
- GET /admin/skills/list - List marketplace skills
- POST /admin/skills/install - Install a skill
- GET /admin/skills/installed - List installed skills
- DELETE /admin/skills/{skill_name} - Uninstall a skill

TDD Phase: Tests define expected behavior for API implementation.
"""

from __future__ import annotations

import gc
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.auth.dependencies import (
    require_skill_viewer_global,
    require_skill_author_global,
)

pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.api]


# =============================================================================
# Fixtures
# =============================================================================


def mock_skill_viewer() -> dict[str, str]:
    """Mock skill viewer dependency for testing (all users can view)."""
    return {"user_id": "bob", "sub": "bob", "roles": ["user"]}


def mock_skill_author() -> dict[str, str]:
    """Mock skill author dependency for testing (alice/admin can author)."""
    return {"user_id": "alice", "sub": "alice", "roles": ["author"]}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client with OpenFGA auth bypassed."""
    from mcp_server_langgraph.api.v1.skills import router

    app = FastAPI()
    app.include_router(router)

    # Override OpenFGA authorization dependencies
    app.dependency_overrides[require_skill_viewer_global] = mock_skill_viewer
    app.dependency_overrides[require_skill_author_global] = mock_skill_author

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


# =============================================================================
# Test: List Marketplace Skills
# =============================================================================


@pytest.mark.xdist_group(name="skills_marketplace_api")
class TestListMarketplaceSkills:
    """Test GET /admin/skills/list endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_list_skills_returns_skills_from_marketplace(
        self,
        client: TestClient,
    ) -> None:
        """Test listing skills from a marketplace returns skill metadata."""
        mock_skills = [
            {
                "name": "web-research",
                "description": "Web research tool",
                "version": "1.0.0",
                "author": "Anthropic",
                "tags": ["research", "web"],
            },
            {
                "name": "code-review",
                "description": "Code review assistant",
                "version": "2.1.0",
                "author": "Anthropic",
                "tags": ["code", "review"],
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.skills.list_skills_from_marketplace",
            new_callable=AsyncMock,
            return_value=mock_skills,
        ):
            response = client.get("/admin/skills/list?marketplace=anthropic")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert len(data["skills"]) == 2
        assert data["skills"][0]["name"] == "web-research"
        assert data["marketplace"] == "anthropic"

    def test_list_skills_with_search_filter(
        self,
        client: TestClient,
    ) -> None:
        """Test filtering skills by search query."""
        mock_skills = [
            {
                "name": "web-research",
                "description": "Web research tool",
                "version": "1.0.0",
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.skills.list_skills_from_marketplace",
            new_callable=AsyncMock,
            return_value=mock_skills,
        ):
            response = client.get("/admin/skills/list?marketplace=anthropic&search=web")

        assert response.status_code == 200
        data = response.json()
        assert len(data["skills"]) == 1
        assert "web" in data["skills"][0]["name"]

    def test_list_skills_with_tags_filter(
        self,
        client: TestClient,
    ) -> None:
        """Test filtering skills by tags."""
        mock_skills = [
            {
                "name": "code-review",
                "description": "Code review",
                "version": "1.0.0",
                "tags": ["code"],
            },
        ]

        with patch(
            "mcp_server_langgraph.api.v1.skills.list_skills_from_marketplace",
            new_callable=AsyncMock,
            return_value=mock_skills,
        ):
            response = client.get("/admin/skills/list?marketplace=anthropic&tags=code")

        assert response.status_code == 200
        data = response.json()
        assert len(data["skills"]) >= 1

    def test_list_skills_unknown_marketplace_returns_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that unknown marketplace returns 404."""
        with patch(
            "mcp_server_langgraph.api.v1.skills.list_skills_from_marketplace",
            new_callable=AsyncMock,
            side_effect=ValueError("Unknown marketplace: invalid-marketplace"),
        ):
            response = client.get("/admin/skills/list?marketplace=invalid-marketplace")

        assert response.status_code == 404

    def test_list_skills_defaults_to_anthropic_marketplace(
        self,
        client: TestClient,
    ) -> None:
        """Test that default marketplace is anthropic."""
        mock_skills = []

        with patch(
            "mcp_server_langgraph.api.v1.skills.list_skills_from_marketplace",
            new_callable=AsyncMock,
            return_value=mock_skills,
        ) as mock_list:
            response = client.get("/admin/skills/list")

        assert response.status_code == 200
        mock_list.assert_called_once()
        # First arg should be marketplace="anthropic"
        call_args = mock_list.call_args
        assert "anthropic" in str(call_args)


# =============================================================================
# Test: Install Skill
# =============================================================================


@pytest.mark.xdist_group(name="skills_install_api")
class TestInstallSkill:
    """Test POST /admin/skills/install endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_install_skill_success(
        self,
        client: TestClient,
    ) -> None:
        """Test successful skill installation."""
        mock_result = {
            "success": True,
            "skill_name": "web-research",
            "version": "1.0.0",
            "source": "anthropic",
            "installed_path": "/home/user/.mcp-langgraph/skills/web-research",
            "dependencies_installed": ["requests>=2.28.0"],
        }

        with patch(
            "mcp_server_langgraph.api.v1.skills.install_skill",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/admin/skills/install",
                json={"skill_name": "web-research", "marketplace": "anthropic"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["skill_name"] == "web-research"
        assert data["version"] == "1.0.0"

    def test_install_skill_with_version(
        self,
        client: TestClient,
    ) -> None:
        """Test installing a specific version of a skill."""
        mock_result = {
            "success": True,
            "skill_name": "code-review",
            "version": "2.0.0",
            "source": "anthropic",
            "installed_path": "/home/user/.mcp-langgraph/skills/code-review",
            "dependencies_installed": [],
        }

        with patch(
            "mcp_server_langgraph.api.v1.skills.install_skill",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/admin/skills/install",
                json={
                    "skill_name": "code-review",
                    "marketplace": "anthropic",
                    "version": "2.0.0",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"

    def test_install_skill_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test installing a skill that doesn't exist."""
        mock_result = {
            "success": False,
            "skill_name": "nonexistent-skill",
            "error": "Skill not found: nonexistent-skill in anthropic",
        }

        with patch(
            "mcp_server_langgraph.api.v1.skills.install_skill",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/admin/skills/install",
                json={"skill_name": "nonexistent-skill"},
            )

        assert response.status_code == 200  # Request succeeded, but installation failed
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_install_skill_missing_skill_name(
        self,
        client: TestClient,
    ) -> None:
        """Test installing without skill_name returns validation error."""
        response = client.post(
            "/admin/skills/install",
            json={"marketplace": "anthropic"},
        )

        assert response.status_code == 422  # Validation error

    def test_install_skill_defaults_to_anthropic_marketplace(
        self,
        client: TestClient,
    ) -> None:
        """Test that default marketplace for install is anthropic."""
        mock_result = {
            "success": True,
            "skill_name": "test-skill",
            "version": "1.0.0",
            "source": "anthropic",
            "installed_path": "/home/user/.mcp-langgraph/skills/test-skill",
            "dependencies_installed": [],
        }

        with patch(
            "mcp_server_langgraph.api.v1.skills.install_skill",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_install:
            response = client.post(
                "/admin/skills/install",
                json={"skill_name": "test-skill"},
            )

        assert response.status_code == 200
        # Verify default marketplace was used
        mock_install.assert_called_once()


# =============================================================================
# Test: List Installed Skills
# =============================================================================


@pytest.mark.xdist_group(name="skills_installed_api")
class TestListInstalledSkills:
    """Test GET /admin/skills/installed endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_list_installed_skills_returns_installed(
        self,
        client: TestClient,
    ) -> None:
        """Test listing installed skills."""
        mock_installed = ["web-research", "code-review"]

        with patch(
            "mcp_server_langgraph.api.v1.skills.list_installed_skills",
            new_callable=AsyncMock,
            return_value=mock_installed,
        ):
            response = client.get("/admin/skills/installed")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert len(data["skills"]) == 2
        assert "web-research" in data["skills"]

    def test_list_installed_skills_empty(
        self,
        client: TestClient,
    ) -> None:
        """Test listing installed skills when none installed."""
        with patch(
            "mcp_server_langgraph.api.v1.skills.list_installed_skills",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/admin/skills/installed")

        assert response.status_code == 200
        data = response.json()
        assert data["skills"] == []
        assert data["count"] == 0


# =============================================================================
# Test: Uninstall Skill
# =============================================================================


@pytest.mark.xdist_group(name="skills_uninstall_api")
class TestUninstallSkill:
    """Test DELETE /admin/skills/{skill_name} endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_uninstall_skill_success(
        self,
        client: TestClient,
    ) -> None:
        """Test successful skill uninstallation."""
        with patch(
            "mcp_server_langgraph.api.v1.skills.uninstall_skill",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.delete("/admin/skills/web-research")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["skill_name"] == "web-research"

    def test_uninstall_skill_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test uninstalling a skill that's not installed."""
        with patch(
            "mcp_server_langgraph.api.v1.skills.uninstall_skill",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.delete("/admin/skills/nonexistent-skill")

        assert response.status_code == 404


# =============================================================================
# Test: Check Skill Updates
# =============================================================================


@pytest.mark.xdist_group(name="skills_updates_api")
class TestCheckSkillUpdates:
    """Test GET /admin/skills/updates endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_check_updates_returns_available_updates(
        self,
        client: TestClient,
    ) -> None:
        """Test checking for updates returns available updates."""
        from mcp_server_langgraph.skills.auto_update import SkillUpdate

        mock_updates = [
            SkillUpdate(
                skill_name="web-research",
                current_version="1.0.0",
                new_version="1.1.0",
                marketplace="anthropic",
                changelog="Bug fixes and improvements",
            ),
            SkillUpdate(
                skill_name="code-review",
                current_version="2.0.0",
                new_version="2.1.0",
                marketplace="anthropic",
                changelog="New features",
            ),
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.check_updates_available = AsyncMock(return_value=mock_updates)

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.get("/admin/skills/updates")

        assert response.status_code == 200
        data = response.json()
        assert "updates" in data
        assert data["count"] == 2
        assert data["updates"][0]["skill_name"] == "web-research"
        assert data["updates"][0]["current_version"] == "1.0.0"
        assert data["updates"][0]["new_version"] == "1.1.0"
        assert data["updates"][1]["skill_name"] == "code-review"

    def test_check_updates_returns_empty_when_no_updates(
        self,
        client: TestClient,
    ) -> None:
        """Test checking for updates returns empty list when no updates available."""
        mock_scheduler = AsyncMock()
        mock_scheduler.check_updates_available = AsyncMock(return_value=[])

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.get("/admin/skills/updates")

        assert response.status_code == 200
        data = response.json()
        assert data["updates"] == []
        assert data["count"] == 0

    def test_check_updates_handles_scheduler_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that scheduler errors are handled gracefully."""
        mock_scheduler = AsyncMock()
        mock_scheduler.check_updates_available = AsyncMock(
            side_effect=RuntimeError("Scheduler unavailable")
        )

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.get("/admin/skills/updates")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to check updates" in data["detail"]


# =============================================================================
# Test: Apply Skill Updates
# =============================================================================


@pytest.mark.xdist_group(name="skills_apply_updates_api")
class TestApplySkillUpdates:
    """Test POST /admin/skills/updates/apply endpoint."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_apply_updates_success(
        self,
        client: TestClient,
    ) -> None:
        """Test applying updates returns success results."""
        mock_results = [
            {"skill_name": "web-research", "success": True, "version": "1.1.0"},
            {"skill_name": "code-review", "success": True, "version": "2.1.0"},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.apply_updates = AsyncMock(return_value=mock_results)

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.post("/admin/skills/updates/apply")

        assert response.status_code == 200
        data = response.json()
        assert "applied" in data
        assert data["count"] == 2
        assert data["success_count"] == 2

    def test_apply_updates_partial_success(
        self,
        client: TestClient,
    ) -> None:
        """Test applying updates with partial success."""
        mock_results = [
            {"skill_name": "web-research", "success": True, "version": "1.1.0"},
            {"skill_name": "code-review", "success": False, "error": "Network error"},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.apply_updates = AsyncMock(return_value=mock_results)

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.post("/admin/skills/updates/apply")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["success_count"] == 1

    def test_apply_updates_no_updates_available(
        self,
        client: TestClient,
    ) -> None:
        """Test applying updates when none available returns empty list."""
        mock_scheduler = AsyncMock()
        mock_scheduler.apply_updates = AsyncMock(return_value=[])

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.post("/admin/skills/updates/apply")

        assert response.status_code == 200
        data = response.json()
        assert data["applied"] == []
        assert data["count"] == 0
        assert data["success_count"] == 0

    def test_apply_updates_handles_scheduler_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that scheduler errors are handled gracefully."""
        mock_scheduler = AsyncMock()
        mock_scheduler.apply_updates = AsyncMock(
            side_effect=RuntimeError("Update failed")
        )

        with patch(
            "mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler",
            return_value=mock_scheduler,
        ):
            response = client.post("/admin/skills/updates/apply")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to apply updates" in data["detail"]
