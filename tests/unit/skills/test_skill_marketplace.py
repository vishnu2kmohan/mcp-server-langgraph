"""
Unit tests for Skill Marketplace

Tests multi-marketplace integration for discovering and installing
skills from various sources including Anthropic's official skills repo.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.skills_marketplace]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_config")
class TestMarketplaceConfig:
    """Test suite for marketplace configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_marketplace_config_exists(self):
        """GIVEN the skills module
        WHEN importing MarketplaceConfig
        THEN it should be available
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceConfig

        config = MarketplaceConfig(
            name="anthropic",
            uri="https://github.com/anthropics/skills",
            type="github",
        )
        assert config is not None

    def test_marketplace_config_fields(self):
        """GIVEN a MarketplaceConfig
        WHEN checking fields
        THEN all required fields should be present
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceConfig

        config = MarketplaceConfig(
            name="anthropic",
            uri="https://github.com/anthropics/skills",
            type="github",
            trusted=True,
            auto_sync=True,
            requires_approval=False,
        )

        assert config.name == "anthropic"
        assert "anthropics/skills" in config.uri
        assert config.type == "github"
        assert config.trusted is True
        assert config.auto_sync is True
        assert config.requires_approval is False

    def test_marketplace_types(self):
        """GIVEN MarketplaceConfig
        WHEN setting type
        THEN valid types should be accepted
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceConfig

        # GitHub repo
        github = MarketplaceConfig(
            name="github-skills",
            uri="https://github.com/org/skills",
            type="github",
        )
        assert github.type == "github"

        # OCI registry
        oci = MarketplaceConfig(
            name="oci-skills",
            uri="oci://registry.io/skills",
            type="oci",
        )
        assert oci.type == "oci"

        # Custom registry
        registry = MarketplaceConfig(
            name="custom-skills",
            uri="https://skills.example.com/api",
            type="registry",
        )
        assert registry.type == "registry"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_registry")
class TestMarketplaceRegistry:
    """Test suite for marketplace registry management"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_marketplace_registry_exists(self):
        """GIVEN the skills module
        WHEN importing MarketplaceRegistry
        THEN it should be available
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceRegistry

        registry = MarketplaceRegistry()
        assert registry is not None

    def test_default_anthropic_marketplace(self):
        """GIVEN a new MarketplaceRegistry
        WHEN checking default marketplaces
        THEN Anthropic should be registered
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceRegistry

        registry = MarketplaceRegistry()

        anthropic = registry.get("anthropic")
        assert anthropic is not None
        assert "anthropics/skills" in anthropic.uri
        assert anthropic.trusted is True

    def test_register_marketplace(self):
        """GIVEN a MarketplaceRegistry
        WHEN registering a new marketplace
        THEN it should be stored
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceConfig,
            MarketplaceRegistry,
        )

        registry = MarketplaceRegistry()
        config = MarketplaceConfig(
            name="enterprise",
            uri="https://github.com/myorg/skills",
            type="github",
            trusted=True,
        )

        registry.register(config)

        assert registry.get("enterprise") is not None

    def test_list_all_marketplaces(self):
        """GIVEN a MarketplaceRegistry with multiple marketplaces
        WHEN listing all
        THEN all should be returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceConfig,
            MarketplaceRegistry,
        )

        registry = MarketplaceRegistry()
        registry.register(
            MarketplaceConfig(
                name="custom",
                uri="https://example.com/skills",
                type="registry",
            )
        )

        all_marketplaces = registry.list_all()

        # Should include default Anthropic + custom
        assert len(all_marketplaces) >= 2
        names = [m.name for m in all_marketplaces]
        assert "anthropic" in names
        assert "custom" in names

    def test_unregister_marketplace(self):
        """GIVEN a MarketplaceRegistry with custom marketplace
        WHEN unregistering
        THEN it should be removed
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceConfig,
            MarketplaceRegistry,
        )

        registry = MarketplaceRegistry()
        registry.register(
            MarketplaceConfig(
                name="removable",
                uri="https://example.com/skills",
                type="registry",
            )
        )

        registry.unregister("removable")

        assert registry.get("removable") is None

    def test_cannot_unregister_anthropic(self):
        """GIVEN a MarketplaceRegistry
        WHEN attempting to unregister Anthropic
        THEN it should remain (protected)
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceRegistry

        registry = MarketplaceRegistry()

        # Anthropic marketplace is protected
        registry.unregister("anthropic")

        # Should still exist
        assert registry.get("anthropic") is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_client")
class TestMarketplaceClient:
    """Test suite for marketplace client operations"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_marketplace_client_exists(self):
        """GIVEN the skills module
        WHEN importing MarketplaceClient
        THEN it should be available
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()
        assert client is not None

    def test_client_has_cache_ttl(self):
        """GIVEN a MarketplaceClient
        WHEN checking configuration
        THEN cache TTL should be set
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()

        assert hasattr(client, "cache_ttl_seconds")
        assert client.cache_ttl_seconds > 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_installer")
class TestSkillInstaller:
    """Test suite for skill installation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_installer_exists(self):
        """GIVEN the skills module
        WHEN importing SkillInstaller
        THEN it should be available
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller()
        assert installer is not None

    def test_installer_has_install_path(self):
        """GIVEN a SkillInstaller
        WHEN checking configuration
        THEN install path should be set
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller()

        assert hasattr(installer, "install_path")
        assert installer.install_path is not None

    def test_installation_result_model(self):
        """GIVEN a skill installation
        WHEN installation completes
        THEN result should contain expected fields
        """
        from mcp_server_langgraph.skills.installer import InstallationResult

        result = InstallationResult(
            success=True,
            skill_name="web-research",
            version="1.0.0",
            source="anthropic",
            installed_path="/path/to/skill",
        )

        assert result.success is True
        assert result.skill_name == "web-research"
        assert result.version == "1.0.0"

    def test_installation_result_failure(self):
        """GIVEN a failed skill installation
        WHEN creating result
        THEN error should be captured
        """
        from mcp_server_langgraph.skills.installer import InstallationResult

        result = InstallationResult(
            success=False,
            skill_name="broken-skill",
            error="Failed to download skill: 404 Not Found",
        )

        assert result.success is False
        assert result.error is not None
        assert "404" in result.error


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_github_api")
class TestMarketplaceGitHubAPI:
    """Test suite for GitHub API integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_skills_calls_github_api(self):
        """GIVEN a marketplace client with mocked HTTP
        WHEN listing skills from a GitHub marketplace
        THEN the GitHub API should be called
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="anthropic",
            uri="https://github.com/anthropics/skills",
            type="github",
            trusted=True,
        )

        # Mock HTTP client response
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value=[
                {"name": "web-research", "type": "dir"},
                {"name": "code-review", "type": "dir"},
                {"name": "README.md", "type": "file"},  # Should be filtered out
            ]
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            # Should have called the API
            mock_client.get.assert_called_once()
            # Should filter to only directories (skill folders)
            assert len(skills) == 2
            skill_names = [s["name"] for s in skills]
            assert "web-research" in skill_names
            assert "code-review" in skill_names

    @pytest.mark.asyncio
    async def test_fetch_skill_downloads_skill_md(self):
        """GIVEN a marketplace client
        WHEN fetching a specific skill
        THEN the SKILL.md content should be downloaded
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="anthropic",
            uri="https://github.com/anthropics/skills",
            type="github",
            trusted=True,
        )

        skill_md_content = """---
name: web-research
description: Research topics using web search
---

# Web Research Skill
"""

        mock_response = MagicMock()
        mock_response.text = skill_md_content
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "web-research")

            assert skill is not None
            assert skill["name"] == "web-research"
            assert "description" in skill

    @pytest.mark.asyncio
    async def test_list_skills_uses_cache(self):
        """GIVEN a marketplace client with cached data
        WHEN listing skills again
        THEN cached data should be returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="cached-test",
            uri="https://github.com/test/skills",
            type="github",
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value=[
                {"name": "skill-1", "type": "dir"},
            ]
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()

            # First call should hit API
            await client.list_skills(marketplace)

            # Second call should use cache
            await client.list_skills(marketplace)

            # API should only be called once
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_skill_returns_none_on_404(self):
        """GIVEN a marketplace client
        WHEN fetching a non-existent skill
        THEN None should be returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="anthropic",
            uri="https://github.com/anthropics/skills",
            type="github",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "non-existent")

            assert skill is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_coverage")
class TestMarketplaceCoverage:
    """Additional tests to improve marketplace.py coverage.

    These tests cover edge cases and error handling paths.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_trusted_returns_only_trusted(self):
        """GIVEN a registry with mixed trusted/untrusted marketplaces
        WHEN calling list_trusted()
        THEN only trusted marketplaces are returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceConfig,
            MarketplaceRegistry,
        )

        registry = MarketplaceRegistry()

        # Register an untrusted marketplace
        untrusted = MarketplaceConfig(
            name="untrusted-source",
            uri="https://github.com/unknown/skills",
            type="github",
            trusted=False,
        )
        registry.register(untrusted)

        trusted_list = registry.list_trusted()

        # Should only return anthropic (default trusted) not the untrusted one
        trusted_names = [m.name for m in trusted_list]
        assert "anthropic" in trusted_names
        assert "untrusted-source" not in trusted_names

    @pytest.mark.asyncio
    async def test_list_skills_non_github_type_returns_empty(self):
        """GIVEN a marketplace with non-github type
        WHEN listing skills
        THEN an empty list is returned (placeholder behavior)
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="oci-registry",
            uri="oci://registry.io/skills",
            type="oci",
        )

        client = MarketplaceClient()
        skills = await client.list_skills(marketplace)

        # Non-github types return empty list as placeholder
        assert skills == []

    @pytest.mark.asyncio
    async def test_fetch_skill_unsupported_type_returns_none(self):
        """GIVEN a marketplace with unsupported type
        WHEN fetching a skill
        THEN None is returned

        Note: This test manually sets an unsupported type to simulate
        future/unknown marketplace types that may not have handlers.
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        # Create a valid config first
        marketplace = MarketplaceConfig(
            name="custom-type",
            uri="https://skills.example.com/api",
            type="registry",  # Start with valid type
        )
        # Manually override to simulate unsupported type (bypassing Pydantic)
        # This tests the handler map fallback behavior
        object.__setattr__(marketplace, "type", "unsupported")

        client = MarketplaceClient()
        skill = await client.fetch_skill(marketplace, "some-skill")

        assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills_invalid_github_url(self):
        """GIVEN a marketplace with invalid GitHub URL
        WHEN listing skills
        THEN an empty list is returned
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        # URL doesn't match GitHub pattern
        marketplace = MarketplaceConfig(
            name="bad-url",
            uri="https://gitlab.com/org/repo",  # Not github.com
            type="github",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            # Should return empty without making API call
            assert skills == []

    @pytest.mark.asyncio
    async def test_fetch_skill_invalid_github_url(self):
        """GIVEN a marketplace with invalid GitHub URL format
        WHEN fetching a skill
        THEN None is returned
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        # URL doesn't match GitHub pattern
        marketplace = MarketplaceConfig(
            name="invalid-url",
            uri="https://not-github.com/org/repo",
            type="github",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "some-skill")

            assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills_github_api_error(self):
        """GIVEN a marketplace client
        WHEN GitHub API returns non-200 status
        THEN an empty list is returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="api-error",
            uri="https://github.com/org/repo",
            type="github",
        )

        mock_response = MagicMock()
        mock_response.status_code = 403  # Rate limited or forbidden

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            assert skills == []

    @pytest.mark.asyncio
    async def test_list_skills_exception_handling(self):
        """GIVEN a marketplace client
        WHEN an exception occurs during API call
        THEN the exception is re-raised with metrics recorded
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="exception-test",
            uri="https://github.com/org/repo",
            type="github",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=ConnectionError("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()

            with pytest.raises(ConnectionError):
                await client.list_skills(marketplace)

    @pytest.mark.asyncio
    async def test_fetch_skill_exception_handling(self):
        """GIVEN a marketplace client
        WHEN an exception occurs during skill fetch
        THEN the exception is re-raised with metrics recorded
        """
        from unittest.mock import AsyncMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="exception-test",
            uri="https://github.com/org/repo",
            type="github",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=TimeoutError("Request timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()

            with pytest.raises(TimeoutError):
                await client.fetch_skill(marketplace, "some-skill")

    def test_parse_skill_md_no_frontmatter(self):
        """GIVEN a SKILL.md without YAML frontmatter
        WHEN parsing
        THEN name and content are returned
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()

        # Content without frontmatter
        content = "# Simple Skill\n\nThis skill has no frontmatter."

        result = client._parse_skill_md(content, "simple-skill")

        assert result["name"] == "simple-skill"
        assert result["content"] == content

    def test_parse_skill_md_with_single_quoted_values(self):
        """GIVEN a SKILL.md with single-quoted YAML values
        WHEN parsing
        THEN quotes are properly removed
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()

        content = """---
name: 'quoted-skill'
description: 'A skill with single quotes'
version: '1.0.0'
---

# Skill Content
"""

        result = client._parse_skill_md(content, "fallback-name")

        assert result["name"] == "quoted-skill"
        assert result["description"] == "A skill with single quotes"
        assert result["version"] == "1.0.0"

    def test_parse_skill_md_with_double_quoted_values(self):
        """GIVEN a SKILL.md with double-quoted YAML values
        WHEN parsing
        THEN quotes are properly removed
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()

        content = """---
name: "double-quoted"
description: "A skill with double quotes"
---

# Instructions
"""

        result = client._parse_skill_md(content, "fallback-name")

        assert result["name"] == "double-quoted"
        assert result["description"] == "A skill with double quotes"

    def test_parse_skill_md_preserves_instructions(self):
        """GIVEN a SKILL.md with frontmatter and content
        WHEN parsing
        THEN instructions are extracted from markdown
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        client = MarketplaceClient()

        content = """---
name: test-skill
---

# Main Instructions

These are the instructions for the skill.

## Guidelines

- Follow these guidelines
- Do good work
"""

        result = client._parse_skill_md(content, "test")

        assert result["name"] == "test-skill"
        assert "instructions" in result
        assert "Main Instructions" in result["instructions"]
        assert "Guidelines" in result["instructions"]


# =============================================================================
# OCI MARKETPLACE TESTS (TDD: RED PHASE)
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_oci")
class TestMarketplaceOCI:
    """Test suite for OCI registry marketplace type.

    OCI (Open Container Initiative) registries can store skill artifacts
    following the OCI Distribution specification.

    URI format: oci://registry.io/namespace/skills
    Example: oci://ghcr.io/anthropics/skills
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_oci_uri_parsing(self):
        """GIVEN an OCI marketplace config
        WHEN parsing the URI
        THEN registry, namespace, and repository should be extracted
        """
        from mcp_server_langgraph.skills.marketplace import parse_oci_uri

        uri = "oci://ghcr.io/anthropics/skills"
        result = parse_oci_uri(uri)

        assert result is not None
        assert result["registry"] == "ghcr.io"
        assert result["namespace"] == "anthropics"
        assert result["repository"] == "skills"

    def test_oci_uri_parsing_with_port(self):
        """GIVEN an OCI URI with port number
        WHEN parsing
        THEN port should be included in registry
        """
        from mcp_server_langgraph.skills.marketplace import parse_oci_uri

        uri = "oci://localhost:5000/myorg/skills"
        result = parse_oci_uri(uri)

        assert result is not None
        assert result["registry"] == "localhost:5000"
        assert result["namespace"] == "myorg"
        assert result["repository"] == "skills"

    def test_oci_uri_parsing_invalid(self):
        """GIVEN an invalid OCI URI
        WHEN parsing
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.marketplace import parse_oci_uri

        # Not an OCI URI
        result = parse_oci_uri("https://github.com/org/repo")
        assert result is None

        # Missing components
        result = parse_oci_uri("oci://registry.io")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_skills_oci_calls_registry(self):
        """GIVEN an OCI marketplace
        WHEN listing skills
        THEN the OCI registry API should be called
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="oci-skills",
            uri="oci://ghcr.io/anthropics/skills",
            type="oci",
        )

        # Mock the OCI registry tags list response
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "name": "anthropics/skills",
                "tags": ["web-research", "code-review", "document-analysis"],
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            # Should return skills based on tags
            assert len(skills) == 3
            skill_names = [s["name"] for s in skills]
            assert "web-research" in skill_names
            assert "code-review" in skill_names

    @pytest.mark.asyncio
    async def test_fetch_skill_oci_downloads_manifest(self):
        """GIVEN an OCI marketplace
        WHEN fetching a specific skill
        THEN the skill manifest should be downloaded
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="oci-skills",
            uri="oci://ghcr.io/anthropics/skills",
            type="oci",
        )

        # Mock manifest response with skill metadata
        skill_config = {
            "name": "web-research",
            "description": "Research topics using web search",
            "version": "1.0.0",
        }

        mock_manifest_response = MagicMock()
        mock_manifest_response.json = MagicMock(
            return_value={
                "schemaVersion": 2,
                "config": {
                    "mediaType": "application/vnd.mcp.skill.config.v1+json",
                    "digest": "sha256:abc123",
                },
                "layers": [
                    {
                        "mediaType": "application/vnd.mcp.skill.instructions.v1+md",
                        "digest": "sha256:def456",
                    },
                ],
            }
        )
        mock_manifest_response.status_code = 200

        mock_config_response = MagicMock()
        mock_config_response.json = MagicMock(return_value=skill_config)
        mock_config_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[
                    mock_manifest_response,
                    mock_config_response,
                ]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "web-research")

            assert skill is not None
            assert skill["name"] == "web-research"
            assert skill["description"] == "Research topics using web search"

    @pytest.mark.asyncio
    async def test_list_skills_oci_invalid_uri(self):
        """GIVEN an OCI marketplace with invalid URI
        WHEN listing skills
        THEN empty list should be returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="bad-oci",
            uri="oci://invalid",  # Missing namespace/repo
            type="oci",
        )

        client = MarketplaceClient()
        skills = await client.list_skills(marketplace)

        assert skills == []

    @pytest.mark.asyncio
    async def test_fetch_skill_oci_invalid_uri(self):
        """GIVEN an OCI marketplace with invalid URI
        WHEN fetching a skill
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="bad-oci",
            uri="oci://invalid",
            type="oci",
        )

        client = MarketplaceClient()
        skill = await client.fetch_skill(marketplace, "some-skill")

        assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills_oci_api_error(self):
        """GIVEN an OCI marketplace
        WHEN registry returns error
        THEN empty list should be returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="oci-error",
            uri="oci://ghcr.io/org/skills",
            type="oci",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401  # Unauthorized

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            assert skills == []

    @pytest.mark.asyncio
    async def test_list_skills_oci_uses_cache(self):
        """GIVEN an OCI marketplace
        WHEN listing skills twice
        THEN second call should use cache
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="oci-cache",
            uri="oci://ghcr.io/org/skills",
            type="oci",
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "name": "org/skills",
                "tags": ["skill-1"],
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()

            # First call hits API
            await client.list_skills(marketplace)

            # Second call uses cache
            await client.list_skills(marketplace)

            # API should only be called once
            assert mock_client.get.call_count == 1


# =============================================================================
# REGISTRY MARKETPLACE TESTS (TDD: RED PHASE)
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_marketplace_registry_api")
class TestMarketplaceRegistryAPI:
    """Test suite for custom registry marketplace type.

    Registry type supports custom REST APIs for skill discovery and download.
    Expected API endpoints:
    - GET /skills - List available skills
    - GET /skills/{name} - Get skill metadata

    URI format: https://skills.example.com/api/v1
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_registry_uri_parsing(self):
        """GIVEN a registry marketplace config
        WHEN parsing the URI
        THEN base URL should be extracted
        """
        from mcp_server_langgraph.skills.marketplace import parse_registry_uri

        uri = "https://skills.example.com/api/v1"
        result = parse_registry_uri(uri)

        assert result is not None
        assert result["base_url"] == "https://skills.example.com/api/v1"

    def test_registry_uri_parsing_with_trailing_slash(self):
        """GIVEN a registry URI with trailing slash
        WHEN parsing
        THEN trailing slash should be stripped
        """
        from mcp_server_langgraph.skills.marketplace import parse_registry_uri

        uri = "https://skills.example.com/api/v1/"
        result = parse_registry_uri(uri)

        assert result is not None
        assert result["base_url"] == "https://skills.example.com/api/v1"

    def test_registry_uri_parsing_invalid(self):
        """GIVEN an invalid registry URI
        WHEN parsing
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.marketplace import parse_registry_uri

        # Not https
        result = parse_registry_uri("http://insecure.com/api")
        assert result is None

        # OCI scheme
        result = parse_registry_uri("oci://registry.io/org/repo")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_skills_registry_calls_api(self):
        """GIVEN a registry marketplace
        WHEN listing skills
        THEN the registry API should be called
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="custom-registry",
            uri="https://skills.example.com/api/v1",
            type="registry",
        )

        # Mock the registry API response
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "skills": [
                    {"name": "web-research", "version": "1.0.0"},
                    {"name": "code-review", "version": "2.1.0"},
                ],
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            # Should return skills from API
            assert len(skills) == 2
            skill_names = [s["name"] for s in skills]
            assert "web-research" in skill_names
            assert "code-review" in skill_names

    @pytest.mark.asyncio
    async def test_fetch_skill_registry_calls_api(self):
        """GIVEN a registry marketplace
        WHEN fetching a specific skill
        THEN the skill endpoint should be called
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="custom-registry",
            uri="https://skills.example.com/api/v1",
            type="registry",
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "name": "web-research",
                "description": "Research topics using web search",
                "version": "1.0.0",
                "instructions": "# Web Research\n\nSearch the web for topics.",
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "web-research")

            assert skill is not None
            assert skill["name"] == "web-research"
            assert skill["description"] == "Research topics using web search"

    @pytest.mark.asyncio
    async def test_list_skills_registry_invalid_uri(self):
        """GIVEN a registry marketplace with invalid URI
        WHEN listing skills
        THEN empty list should be returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="bad-registry",
            uri="http://insecure.com/api",  # HTTP not allowed
            type="registry",
        )

        client = MarketplaceClient()
        skills = await client.list_skills(marketplace)

        assert skills == []

    @pytest.mark.asyncio
    async def test_fetch_skill_registry_invalid_uri(self):
        """GIVEN a registry marketplace with invalid URI
        WHEN fetching a skill
        THEN None should be returned
        """
        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="bad-registry",
            uri="http://insecure.com/api",
            type="registry",
        )

        client = MarketplaceClient()
        skill = await client.fetch_skill(marketplace, "some-skill")

        assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills_registry_api_error(self):
        """GIVEN a registry marketplace
        WHEN API returns error
        THEN empty list should be returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="error-registry",
            uri="https://skills.example.com/api/v1",
            type="registry",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500  # Server error

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skills = await client.list_skills(marketplace)

            assert skills == []

    @pytest.mark.asyncio
    async def test_fetch_skill_registry_404(self):
        """GIVEN a registry marketplace
        WHEN skill is not found
        THEN None should be returned
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="registry",
            uri="https://skills.example.com/api/v1",
            type="registry",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()
            skill = await client.fetch_skill(marketplace, "non-existent")

            assert skill is None

    @pytest.mark.asyncio
    async def test_list_skills_registry_uses_cache(self):
        """GIVEN a registry marketplace
        WHEN listing skills twice
        THEN second call should use cache
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            MarketplaceConfig,
        )

        marketplace = MarketplaceConfig(
            name="cache-registry",
            uri="https://skills.example.com/api/v1",
            type="registry",
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "skills": [{"name": "skill-1"}],
            }
        )
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MarketplaceClient()

            # First call hits API
            await client.list_skills(marketplace)

            # Second call uses cache
            await client.list_skills(marketplace)

            # API should only be called once (cache)
            assert mock_client.get.call_count == 1
