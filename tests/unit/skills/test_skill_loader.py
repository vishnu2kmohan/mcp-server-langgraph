"""
Unit tests for Skill Loader

Tests the SKILL.md YAML frontmatter parser per Anthropic's
Agent Skills specification.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc
import textwrap

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


@pytest.mark.unit
class TestSkillLoaderBasic:
    """Test suite for basic skill loading"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skill_loader_exists(self):
        """GIVEN the skills module
        WHEN importing SkillLoader
        THEN it should be available
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        assert loader is not None

    def test_load_from_string_parses_yaml_frontmatter(self):
        """GIVEN a SKILL.md content string
        WHEN loading from string
        THEN YAML frontmatter should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: web-research
        description: Research topics using web search
        dependencies:
          - beautifulsoup4>=4.12.0
          - httpx>=0.25.0
        ---

        # Web Research Skill

        Use this skill to research topics on the web.
        """)

        skill = loader.load_from_string(content)

        assert skill.name == "web-research"
        assert skill.description == "Research topics using web search"
        assert len(skill.dependencies) == 2

    def test_load_from_string_extracts_instructions(self):
        """GIVEN a SKILL.md with markdown content
        WHEN loading from string
        THEN markdown should become instructions
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: test-skill
        description: A test skill
        ---

        # Test Skill

        These are the instructions for Claude to follow.

        ## Guidelines
        - Be helpful
        - Be accurate
        """)

        skill = loader.load_from_string(content)

        assert "instructions for Claude" in skill.instructions
        assert "Guidelines" in skill.instructions

    def test_load_from_string_with_sandbox_config(self):
        """GIVEN a SKILL.md with sandbox configuration
        WHEN loading from string
        THEN sandbox config should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: web-skill
        description: Web skill
        sandbox_config:
          network: allowlist
          allowed_domains:
            - "*.google.com"
            - "*.wikipedia.org"
        ---

        # Web Skill
        """)

        skill = loader.load_from_string(content)

        assert skill.sandbox_config is not None
        assert skill.sandbox_config.network == "allowlist"
        assert len(skill.sandbox_config.allowed_domains) == 2


@pytest.mark.unit
class TestSkillLoaderSecrets:
    """Test suite for loading skill secret configurations"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_required_secrets(self):
        """GIVEN a SKILL.md with required secrets
        WHEN loading from string
        THEN required_secrets should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: db-skill
        description: Database skill
        required_secrets:
          - DATABASE_URL
          - API_KEY
        ---

        # Database Skill
        """)

        skill = loader.load_from_string(content)

        assert len(skill.required_secrets) == 2
        assert "DATABASE_URL" in skill.required_secrets

    def test_load_optional_secrets(self):
        """GIVEN a SKILL.md with optional secrets
        WHEN loading from string
        THEN optional_secrets should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: cache-skill
        description: Skill with caching
        optional_secrets:
          - REDIS_URL
        ---

        # Cache Skill
        """)

        skill = loader.load_from_string(content)

        assert len(skill.optional_secrets) == 1

    def test_load_secret_volumes(self):
        """GIVEN a SKILL.md with secret volumes
        WHEN loading from string
        THEN secret_volumes should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: tls-skill
        description: Skill with TLS
        secret_volumes:
          - type: tls
            mount_path: /secrets/tls
        ---

        # TLS Skill
        """)

        skill = loader.load_from_string(content)

        assert len(skill.secret_volumes) == 1
        assert skill.secret_volumes[0].type == "tls"


@pytest.mark.unit
class TestSkillLoaderExamples:
    """Test suite for loading skill examples"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_examples_from_frontmatter(self):
        """GIVEN a SKILL.md with examples in frontmatter
        WHEN loading from string
        THEN examples should be parsed
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: research-skill
        description: Research skill
        examples:
          - "Research quantum computing"
          - "Find recent AI developments"
        ---

        # Research Skill
        """)

        skill = loader.load_from_string(content)

        assert len(skill.examples) == 2
        assert "quantum computing" in skill.examples[0]


@pytest.mark.unit
class TestSkillLoaderFile:
    """Test suite for loading skills from files"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_from_path(self, tmp_path):
        """GIVEN a SKILL.md file on disk
        WHEN loading from path
        THEN skill should be loaded correctly
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create a temporary SKILL.md file
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent("""
        ---
        name: file-skill
        description: Skill loaded from file
        ---

        # File Skill

        Instructions here.
        """)
        )

        loader = SkillLoader()
        skill = loader.load_from_path(skill_file)

        assert skill.name == "file-skill"
        assert skill.description == "Skill loaded from file"

    def test_load_from_directory(self, tmp_path):
        """GIVEN a directory containing SKILL.md
        WHEN loading from directory
        THEN skill should be found and loaded
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create skill directory structure
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent("""
        ---
        name: dir-skill
        description: Skill from directory
        ---

        # Directory Skill
        """)
        )

        loader = SkillLoader()
        skill = loader.load_from_directory(skill_dir)

        assert skill.name == "dir-skill"


@pytest.mark.unit
class TestSkillLoaderErrors:
    """Test suite for skill loader error handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_invalid_yaml_raises_error(self):
        """GIVEN invalid YAML frontmatter
        WHEN loading from string
        THEN SkillParseError should be raised
        """
        from mcp_server_langgraph.skills.loader import SkillLoader, SkillParseError

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: invalid
        description: [unclosed bracket
        ---

        # Invalid
        """)

        with pytest.raises(SkillParseError):
            loader.load_from_string(content)

    def test_load_missing_required_field_raises_error(self):
        """GIVEN YAML missing required fields
        WHEN loading from string
        THEN SkillValidationError should be raised
        """
        from mcp_server_langgraph.skills.loader import SkillLoader, SkillValidationError

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: no-description
        ---

        # No Description
        """)

        with pytest.raises(SkillValidationError):
            loader.load_from_string(content)

    def test_load_nonexistent_file_raises_error(self, tmp_path):
        """GIVEN a path that doesn't exist
        WHEN loading from path
        THEN SkillNotFoundError should be raised
        """
        from mcp_server_langgraph.skills.loader import SkillLoader, SkillNotFoundError

        loader = SkillLoader()

        with pytest.raises(SkillNotFoundError):
            loader.load_from_path(tmp_path / "nonexistent" / "SKILL.md")


@pytest.mark.unit
class TestSkillLoaderDiscovery:
    """Test suite for skill discovery functionality (lines 183-197)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_discover_skills_nonexistent_path_returns_empty(self, tmp_path):
        """GIVEN a path that doesn't exist
        WHEN discovering skills
        THEN empty list should be returned
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        nonexistent_path = tmp_path / "does_not_exist"

        skills = loader.discover_skills(nonexistent_path)

        assert skills == []

    def test_discover_skills_finds_valid_skills(self, tmp_path):
        """GIVEN a directory with valid SKILL.md files
        WHEN discovering skills
        THEN all valid skills should be returned
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create skill 1
        skill1_dir = tmp_path / "skill-one"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            textwrap.dedent("""
        ---
        name: skill-one
        description: First skill
        ---

        # Skill One
        """)
        )

        # Create skill 2 (nested)
        skill2_dir = tmp_path / "category" / "skill-two"
        skill2_dir.mkdir(parents=True)
        (skill2_dir / "SKILL.md").write_text(
            textwrap.dedent("""
        ---
        name: skill-two
        description: Second skill
        ---

        # Skill Two
        """)
        )

        loader = SkillLoader()
        skills = loader.discover_skills(tmp_path)

        assert len(skills) == 2
        skill_names = [s.name for s in skills]
        assert "skill-one" in skill_names
        assert "skill-two" in skill_names

    def test_discover_skills_skips_invalid_skills(self, tmp_path):
        """GIVEN a directory with some invalid SKILL.md files
        WHEN discovering skills
        THEN invalid skills should be skipped without raising
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        # Create valid skill
        valid_dir = tmp_path / "valid-skill"
        valid_dir.mkdir()
        (valid_dir / "SKILL.md").write_text(
            textwrap.dedent("""
        ---
        name: valid-skill
        description: A valid skill
        ---

        # Valid Skill
        """)
        )

        # Create invalid skill (missing required description)
        invalid_dir = tmp_path / "invalid-skill"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text(
            textwrap.dedent("""
        ---
        name: invalid-skill
        ---

        # Invalid Skill
        """)
        )

        loader = SkillLoader()
        skills = loader.discover_skills(tmp_path)

        # Should only return the valid skill, skip the invalid one
        assert len(skills) == 1
        assert skills[0].name == "valid-skill"

    def test_discover_skills_empty_directory(self, tmp_path):
        """GIVEN an empty directory
        WHEN discovering skills
        THEN empty list should be returned
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        skills = loader.discover_skills(tmp_path)

        assert skills == []


@pytest.mark.unit
class TestSkillLoaderMetadataNesting:
    """Test suite for loading skills with runtime fields nested under metadata.

    Per agentskills.io spec, non-standard fields (dependencies, sandbox_config,
    required_secrets, optional_secrets) should be nested under metadata.
    The loader extracts them for backward compatibility with the Skill model.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_load_dependencies_from_metadata(self):
        """GIVEN a SKILL.md with dependencies nested under metadata
        WHEN loading from string
        THEN dependencies should be extracted and available on the skill
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: nested-deps
        description: Skill with nested dependencies
        metadata:
          version: "1.0.0"
          category: devops
          author: Test
          dependencies:
            - httpx>=0.25.0
            - pydantic>=2.0
        ---

        # Nested Deps Skill
        """)

        skill = loader.load_from_string(content)

        assert skill.dependencies == ["httpx>=0.25.0", "pydantic>=2.0"]
        assert skill.version == "1.0.0"
        assert skill.category == "devops"

    def test_load_sandbox_config_from_metadata(self):
        """GIVEN a SKILL.md with sandbox_config nested under metadata
        WHEN loading from string
        THEN sandbox_config should be extracted and converted to SandboxConfig
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: nested-sandbox
        description: Skill with nested sandbox config
        metadata:
          sandbox_config:
            network: allowlist
            allowed_domains:
              - "*.example.com"
        ---

        # Nested Sandbox Skill
        """)

        skill = loader.load_from_string(content)

        assert skill.sandbox_config is not None
        assert skill.sandbox_config.network == "allowlist"
        assert "*.example.com" in skill.sandbox_config.allowed_domains

    def test_load_secrets_from_metadata(self):
        """GIVEN a SKILL.md with secrets nested under metadata
        WHEN loading from string
        THEN secrets should be extracted and available on the skill
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: nested-secrets
        description: Skill with nested secrets
        metadata:
          required_secrets:
            - DB_URL
          optional_secrets:
            - REDIS_URL
            - CACHE_KEY
        ---

        # Nested Secrets Skill
        """)

        skill = loader.load_from_string(content)

        assert skill.required_secrets == ["DB_URL"]
        assert skill.optional_secrets == ["REDIS_URL", "CACHE_KEY"]

    def test_top_level_fields_override_metadata(self):
        """GIVEN a SKILL.md with dependencies at both top-level and metadata
        WHEN loading from string
        THEN top-level should take precedence
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: override-test
        description: Test precedence
        dependencies:
          - top-level-dep
        metadata:
          dependencies:
            - metadata-dep
        ---

        # Override Test
        """)

        skill = loader.load_from_string(content)

        assert skill.dependencies == ["top-level-dep"]

    def test_load_agentskills_io_compliant_skill(self):
        """GIVEN a fully spec-compliant SKILL.md with all fields under metadata
        WHEN loading from string
        THEN all fields should be correctly extracted
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: compliant-skill
        description: Fully spec-compliant skill
        allowed-tools:
          - Read
          - Glob
          - Grep
        compatibility: Requires pygments>=2.17.0. No network access needed.
        metadata:
          version: "1.0.0"
          category: devops
          author: Emergence AI
          dependencies:
            - pygments>=2.17.0
          sandbox_config:
            network: none
            filesystem: readonly
          optional_secrets:
            - GITHUB_TOKEN
        ---

        # Compliant Skill
        """)

        skill = loader.load_from_string(content)

        assert skill.name == "compliant-skill"
        assert skill.version == "1.0.0"
        assert skill.category == "devops"
        assert skill.author == "Emergence AI"
        assert skill.dependencies == ["pygments>=2.17.0"]
        assert skill.sandbox_config is not None
        assert skill.sandbox_config.network == "none"
        assert skill.optional_secrets == ["GITHUB_TOKEN"]
        assert skill.compatibility == "Requires pygments>=2.17.0. No network access needed."
        assert skill.allowed_tools == ["Read", "Glob", "Grep"]

    def test_load_allowed_tools_with_hyphen_key(self):
        """GIVEN a SKILL.md using allowed-tools (hyphenated, per Claude Code convention)
        WHEN loading from string
        THEN allowed_tools should be populated on the Skill model
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: tools-test
        description: Test allowed-tools normalization
        allowed-tools:
          - Bash(uv:*)
          - Read
          - Glob
        ---

        # Tools Test
        """)

        skill = loader.load_from_string(content)

        assert skill.allowed_tools == ["Bash(uv:*)", "Read", "Glob"]

    def test_load_allowed_tools_underscore_key_also_works(self):
        """GIVEN a SKILL.md using allowed_tools (underscored, Python convention)
        WHEN loading from string
        THEN allowed_tools should be populated
        """
        from mcp_server_langgraph.skills.loader import SkillLoader

        loader = SkillLoader()
        content = textwrap.dedent("""
        ---
        name: tools-test-underscore
        description: Test allowed_tools with underscore
        allowed_tools:
          - Read
          - Write
        ---

        # Tools Test Underscore
        """)

        skill = loader.load_from_string(content)

        assert skill.allowed_tools == ["Read", "Write"]
