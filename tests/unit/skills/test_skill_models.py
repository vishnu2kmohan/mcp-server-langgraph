"""
Unit tests for Skill Data Models

Tests the data models for skills including SKILL.md parsing
and validation per Anthropic's Agent Skills specification.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_model_basic")
class TestSkillModelBasic:
    """Test suite for basic Skill model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_model_exists(self):
        """GIVEN the skills module
        WHEN importing Skill
        THEN it should be a Pydantic model
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test-skill",
            description="A test skill",
        )
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"

    def test_skill_has_required_fields(self):
        """GIVEN a Skill model
        WHEN checking required fields
        THEN name and description should be required
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.skills.models import Skill

        with pytest.raises(ValidationError):
            Skill()  # Missing required fields

    def test_skill_has_optional_dependencies(self):
        """GIVEN a Skill model
        WHEN setting dependencies
        THEN it should accept a list of dependency strings
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="web-research",
            description="Research topics",
            dependencies=["beautifulsoup4>=4.12.0", "httpx>=0.25.0"],
        )
        assert len(skill.dependencies) == 2
        assert "beautifulsoup4>=4.12.0" in skill.dependencies

    def test_skill_has_optional_sandbox_config(self):
        """GIVEN a Skill model
        WHEN setting sandbox_config
        THEN it should accept a SandboxConfig object
        """
        from mcp_server_langgraph.skills.models import SandboxConfig, Skill

        sandbox = SandboxConfig(
            network="allowlist",
            allowed_domains=["*.google.com", "*.wikipedia.org"],
        )
        skill = Skill(
            name="web-research",
            description="Research topics",
            sandbox_config=sandbox,
        )
        assert skill.sandbox_config is not None
        assert skill.sandbox_config.network == "allowlist"

    def test_skill_has_instructions(self):
        """GIVEN a Skill model
        WHEN setting instructions
        THEN it should store the instruction text
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="web-research",
            description="Research topics",
            instructions="Use web search to find information...",
        )
        assert "web search" in skill.instructions

    def test_skill_has_examples(self):
        """GIVEN a Skill model
        WHEN setting examples
        THEN it should accept a list of example strings
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="web-research",
            description="Research topics",
            examples=["Research quantum computing", "Find recent AI news"],
        )
        assert len(skill.examples) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_sandbox_config_model")
class TestSandboxConfigModel:
    """Test suite for SandboxConfig model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sandbox_config_exists(self):
        """GIVEN the skills module
        WHEN importing SandboxConfig
        THEN it should be available
        """
        from mcp_server_langgraph.skills.models import SandboxConfig

        config = SandboxConfig()
        assert config is not None

    def test_sandbox_config_network_modes(self):
        """GIVEN a SandboxConfig
        WHEN setting network mode
        THEN it should accept valid modes
        """
        from mcp_server_langgraph.skills.models import SandboxConfig

        config = SandboxConfig(network="none")
        assert config.network == "none"

        config = SandboxConfig(network="allowlist")
        assert config.network == "allowlist"

        config = SandboxConfig(network="unrestricted")
        assert config.network == "unrestricted"

    def test_sandbox_config_allowed_domains(self):
        """GIVEN a SandboxConfig with allowlist
        WHEN setting allowed_domains
        THEN domains should be stored
        """
        from mcp_server_langgraph.skills.models import SandboxConfig

        config = SandboxConfig(
            network="allowlist",
            allowed_domains=["*.example.com", "api.service.io"],
        )
        assert len(config.allowed_domains) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_secret_config")
class TestSkillSecretConfig:
    """Test suite for skill secret configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_required_secrets(self):
        """GIVEN a Skill model
        WHEN setting required_secrets
        THEN it should accept a list of secret names
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="database-query",
            description="Query databases",
            required_secrets=["DATABASE_URL", "API_KEY"],
        )
        assert len(skill.required_secrets) == 2
        assert "DATABASE_URL" in skill.required_secrets

    def test_skill_optional_secrets(self):
        """GIVEN a Skill model
        WHEN setting optional_secrets
        THEN it should accept a list of secret names
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="caching-skill",
            description="Skill with cache",
            optional_secrets=["REDIS_URL"],
        )
        assert len(skill.optional_secrets) == 1

    def test_skill_secret_volumes(self):
        """GIVEN a Skill model
        WHEN setting secret_volumes
        THEN it should accept volume mount specifications
        """
        from mcp_server_langgraph.skills.models import SecretVolume, Skill

        volume = SecretVolume(type="tls", mount_path="/secrets/tls")
        skill = Skill(
            name="secure-skill",
            description="Skill with TLS",
            secret_volumes=[volume],
        )
        assert len(skill.secret_volumes) == 1
        assert skill.secret_volumes[0].type == "tls"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_metadata")
class TestSkillMetadata:
    """Test suite for skill metadata"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_has_version(self):
        """GIVEN a Skill model
        WHEN setting version
        THEN it should store the version
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="versioned-skill",
            description="A skill with version",
            version="1.2.3",
        )
        assert skill.version == "1.2.3"

    def test_skill_has_author(self):
        """GIVEN a Skill model
        WHEN setting author
        THEN it should store the author
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="authored-skill",
            description="A skill with author",
            author="anthropic",
        )
        assert skill.author == "anthropic"

    def test_skill_has_source(self):
        """GIVEN a Skill model
        WHEN setting source
        THEN it should store the marketplace source
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="marketplace-skill",
            description="From marketplace",
            source="https://github.com/anthropics/skills",
        )
        assert "anthropics/skills" in skill.source

    def test_skill_has_tags(self):
        """GIVEN a Skill model
        WHEN setting tags
        THEN it should store the tags
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="tagged-skill",
            description="A skill with tags",
            tags=["research", "web", "automation"],
        )
        assert len(skill.tags) == 3
        assert "research" in skill.tags


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_compliance_fields")
class TestSkillComplianceFields:
    """Test suite for AgentSkills.io compliance fields (Appendix B)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_license_field(self):
        """GIVEN a Skill model
        WHEN setting license
        THEN it should store the license identifier
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="licensed-skill",
            description="A skill with license",
            license="MIT",
        )
        assert skill.license == "MIT"

    def test_skill_license_defaults_to_empty(self):
        """GIVEN a Skill model
        WHEN license is not set
        THEN it should default to empty string
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(name="test-skill", description="Test")
        assert skill.license == ""

    def test_skill_allowed_tools_field(self):
        """GIVEN a Skill model
        WHEN setting allowed_tools
        THEN it should store the pre-approved tool list
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="restricted-skill",
            description="A skill with pre-approved tools",
            allowed_tools=["filesystem:read_file", "filesystem:write_file"],
        )
        assert skill.allowed_tools == ["filesystem:read_file", "filesystem:write_file"]

    def test_skill_allowed_tools_defaults_to_empty(self):
        """GIVEN a Skill model
        WHEN allowed_tools is not set
        THEN it should default to empty list
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(name="test-skill", description="Test")
        assert skill.allowed_tools == []

    def test_skill_category_field(self):
        """GIVEN a Skill model
        WHEN setting category
        THEN it should store the skill category
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="research-skill",
            description="A categorized skill",
            category="research",
        )
        assert skill.category == "research"

    def test_skill_category_defaults_to_empty(self):
        """GIVEN a Skill model
        WHEN category is not set
        THEN it should default to empty string
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(name="test-skill", description="Test")
        assert skill.category == ""

    def test_skill_with_all_compliance_fields(self):
        """GIVEN a Skill model
        WHEN all AgentSkills.io compliance fields are set
        THEN all should be stored correctly
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="compliant-skill",
            description="A fully compliant skill",
            version="1.0.0",
            author="Example Corp",
            tags=["example", "compliant"],
            license="Apache-2.0",
            allowed_tools=["http:get", "http:post"],
            category="api-integration",
        )
        assert skill.name == "compliant-skill"
        assert skill.license == "Apache-2.0"
        assert skill.allowed_tools == ["http:get", "http:post"]
        assert skill.category == "api-integration"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_skill_metadata_extraction")
class TestSkillMetadataExtraction:
    """Test suite for extracting runtime fields from nested metadata.

    Per agentskills.io spec, non-standard fields should be nested under
    metadata. The model_validator extracts them for backward compatibility.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_extract_version_category_author_from_metadata(self):
        """GIVEN metadata containing version, category, author
        WHEN creating a Skill
        THEN those fields should be promoted to top-level
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test skill",
            metadata={"version": "2.0.0", "category": "compliance", "author": "Acme"},
        )
        assert skill.version == "2.0.0"
        assert skill.category == "compliance"
        assert skill.author == "Acme"

    def test_top_level_fields_take_precedence_over_metadata(self):
        """GIVEN both top-level and metadata versions of the same field
        WHEN creating a Skill
        THEN top-level value should win
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            version="1.0.0",
            metadata={"version": "2.0.0"},
        )
        assert skill.version == "1.0.0"

    def test_extract_dependencies_from_metadata(self):
        """GIVEN metadata containing dependencies
        WHEN creating a Skill
        THEN dependencies should be promoted to top-level
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            metadata={"dependencies": ["httpx>=0.25.0", "pydantic>=2.0"]},
        )
        assert skill.dependencies == ["httpx>=0.25.0", "pydantic>=2.0"]

    def test_extract_sandbox_config_from_metadata(self):
        """GIVEN metadata containing sandbox_config dict
        WHEN creating a Skill
        THEN sandbox_config should be promoted to top-level
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            metadata={
                "sandbox_config": {"network": "none", "filesystem": "readonly"},
            },
        )
        # sandbox_config is promoted but not yet converted to SandboxConfig
        # (that's the loader's job). Model should accept dict or SandboxConfig.
        assert skill.sandbox_config is not None

    def test_extract_required_secrets_from_metadata(self):
        """GIVEN metadata containing required_secrets
        WHEN creating a Skill
        THEN required_secrets should be promoted to top-level
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            metadata={"required_secrets": ["DB_URL", "API_KEY"]},
        )
        assert skill.required_secrets == ["DB_URL", "API_KEY"]

    def test_extract_optional_secrets_from_metadata(self):
        """GIVEN metadata containing optional_secrets
        WHEN creating a Skill
        THEN optional_secrets should be promoted to top-level
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            metadata={"optional_secrets": ["REDIS_URL"]},
        )
        assert skill.optional_secrets == ["REDIS_URL"]

    def test_extract_compliance_frameworks_from_metadata(self):
        """GIVEN metadata containing compliance_frameworks
        WHEN creating a Skill with extra='ignore'
        THEN it should not error (compliance_frameworks is not a model field)
        """
        from mcp_server_langgraph.skills.models import Skill

        # compliance_frameworks is not a Skill field, so it should be ignored
        skill = Skill(
            name="test",
            description="Test",
            metadata={"compliance_frameworks": ["GDPR", "HIPAA"]},
        )
        assert skill.name == "test"

    def test_metadata_preserved_after_extraction(self):
        """GIVEN metadata with extractable fields
        WHEN creating a Skill
        THEN the metadata dict should still contain the original keys
        """
        from mcp_server_langgraph.skills.models import Skill

        skill = Skill(
            name="test",
            description="Test",
            metadata={
                "version": "1.0.0",
                "category": "devops",
                "author": "Test Author",
                "custom_key": "custom_value",
            },
        )
        assert skill.metadata["custom_key"] == "custom_value"
        assert skill.metadata["version"] == "1.0.0"
