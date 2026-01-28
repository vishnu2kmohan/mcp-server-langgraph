"""
Tests for Semantic Index Models.

TDD tests for ToolIndexEntry and SkillIndexEntry models used
for semantic search of tools and skills.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in tools/semantic_index.py will make them pass.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_models")
class TestToolIndexEntry:
    """Tests for ToolIndexEntry model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_index_entry_creation_minimal(self) -> None:
        """ToolIndexEntry should be created with minimal required fields."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="builtin:calculator",
            name="calculator",
            description="Perform mathematical calculations",
            category="math",
        )

        assert entry.tool_id == "builtin:calculator"
        assert entry.name == "calculator"
        assert entry.description == "Perform mathematical calculations"
        assert entry.category == "math"

    def test_tool_index_entry_creation_full(self) -> None:
        """ToolIndexEntry should support all optional fields."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="builtin:web_search",
            name="web_search",
            description="Search the web for information",
            category="search",
            embedding=[0.1, 0.2, 0.3, 0.4],
            scope=CapabilityScope.PROJECT,
            tenant_id="tenant-abc",
            parameters_summary="query: str, limit: int = 10",
            token_estimate=150,
        )

        assert entry.embedding == [0.1, 0.2, 0.3, 0.4]
        assert entry.scope == CapabilityScope.PROJECT
        assert entry.tenant_id == "tenant-abc"
        assert entry.parameters_summary == "query: str, limit: int = 10"
        assert entry.token_estimate == 150

    def test_tool_index_entry_default_scope_is_session(self) -> None:
        """ToolIndexEntry should default to SESSION scope."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="builtin:read_file",
            name="read_file",
            description="Read file contents",
            category="filesystem",
        )

        assert entry.scope == CapabilityScope.SESSION

    def test_tool_index_entry_default_embedding_is_none(self) -> None:
        """ToolIndexEntry should default embedding to None."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="builtin:test_tool",
            name="test_tool",
            description="Test tool",
            category="test",
        )

        assert entry.embedding is None

    def test_tool_index_entry_to_dict(self) -> None:
        """ToolIndexEntry should be convertible to dict for Qdrant payload."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="builtin:dict_tool",
            name="dict_tool",
            description="Dict test tool",
            category="test",
            token_estimate=100,
        )

        entry_dict = entry.to_dict()

        assert isinstance(entry_dict, dict)
        assert entry_dict["tool_id"] == "builtin:dict_tool"
        assert entry_dict["name"] == "dict_tool"
        assert entry_dict["description"] == "Dict test tool"
        assert entry_dict["category"] == "test"
        assert entry_dict["token_estimate"] == 100

    def test_tool_index_entry_from_langchain_tool(self) -> None:
        """ToolIndexEntry should be creatable from a LangChain StructuredTool."""
        from langchain_core.tools import StructuredTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        def sample_func(x: int) -> int:
            """Sample function for testing."""
            return x * 2

        lc_tool = StructuredTool.from_function(
            func=sample_func,
            name="sample_tool",
            description="A sample tool for testing",
        )

        # v26: tool_id is REQUIRED
        entry = ToolIndexEntry.from_langchain_tool(lc_tool, category="test", tool_id="builtin:sample_tool")

        assert entry.name == "sample_tool"
        assert entry.description == "A sample tool for testing"
        assert entry.category == "test"
        assert entry.tool_id == "builtin:sample_tool"

    def test_tool_index_entry_equality(self) -> None:
        """ToolIndexEntry with same tool_id should be equal."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry1 = ToolIndexEntry(
            tool_id="builtin:eq_tool",
            name="eq_tool",
            description="Equality test",
            category="test",
        )
        entry2 = ToolIndexEntry(
            tool_id="builtin:eq_tool",
            name="eq_tool",
            description="Equality test",
            category="test",
        )

        assert entry1 == entry2

    def test_tool_index_entry_hash_for_set(self) -> None:
        """ToolIndexEntry should be hashable for use in sets."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry1 = ToolIndexEntry(
            tool_id="builtin:hash_tool_1",
            name="hash_tool_1",
            description="Hash test 1",
            category="test",
        )
        entry2 = ToolIndexEntry(
            tool_id="builtin:hash_tool_2",
            name="hash_tool_2",
            description="Hash test 2",
            category="test",
        )

        tool_set = {entry1, entry2}
        assert len(tool_set) == 2


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_models")
class TestSkillIndexEntry:
    """Tests for SkillIndexEntry model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skill_index_entry_creation_minimal(self) -> None:
        """SkillIndexEntry should be created with minimal required fields."""
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-123",
            name="code_review",
            description="Review code for quality and best practices",
            category="development",
        )

        assert entry.skill_id == "skill-123"
        assert entry.name == "code_review"
        assert entry.description == "Review code for quality and best practices"
        assert entry.category == "development"

    def test_skill_index_entry_creation_full(self) -> None:
        """SkillIndexEntry should support all optional fields."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-456",
            name="data_analysis",
            description="Analyze data and generate insights",
            category="analytics",
            embedding=[0.5, 0.6, 0.7, 0.8],
            scope=CapabilityScope.ORGANIZATION,
            tenant_id="tenant-xyz",
            skill_file_path="/path/to/SKILL.md",
            summary="Analyzes data using statistical methods",
            token_estimate=500,
            tools_needed=["calculator", "chart_generator"],
        )

        assert entry.embedding == [0.5, 0.6, 0.7, 0.8]
        assert entry.scope == CapabilityScope.ORGANIZATION
        assert entry.tenant_id == "tenant-xyz"
        assert entry.skill_file_path == "/path/to/SKILL.md"
        assert entry.summary == "Analyzes data using statistical methods"
        assert entry.token_estimate == 500
        assert entry.tools_needed == ["calculator", "chart_generator"]

    def test_skill_index_entry_default_scope_is_project(self) -> None:
        """SkillIndexEntry should default to PROJECT scope."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-default",
            name="default_skill",
            description="Test skill",
            category="test",
        )

        assert entry.scope == CapabilityScope.PROJECT

    def test_skill_index_entry_default_tools_needed_is_empty(self) -> None:
        """SkillIndexEntry should default tools_needed to empty list."""
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-no-tools",
            name="no_tools_skill",
            description="Skill without tools",
            category="test",
        )

        assert entry.tools_needed == []

    def test_skill_index_entry_to_dict(self) -> None:
        """SkillIndexEntry should be convertible to dict for Qdrant payload."""
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-dict",
            name="dict_skill",
            description="Dict test skill",
            category="test",
            tools_needed=["tool1", "tool2"],
        )

        entry_dict = entry.to_dict()

        assert isinstance(entry_dict, dict)
        assert entry_dict["skill_id"] == "skill-dict"
        assert entry_dict["name"] == "dict_skill"
        assert entry_dict["tools_needed"] == ["tool1", "tool2"]

    def test_skill_index_entry_to_summary(self) -> None:
        """SkillIndexEntry should generate a compact summary for progressive disclosure."""
        from mcp_server_langgraph.tools.semantic_index import SkillIndexEntry

        entry = SkillIndexEntry(
            skill_id="skill-summary",
            name="summary_skill",
            description="A skill that demonstrates summary generation for progressive disclosure",
            category="test",
            summary="Short summary",
        )

        summary = entry.to_summary()

        # Summary should be compact (for progressive disclosure ~100 tokens)
        assert len(summary) < 500  # Characters, not tokens
        assert "summary_skill" in summary
        assert "Short summary" in summary


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_models")
class TestMemoryIndexEntry:
    """Tests for MemoryIndexEntry model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_index_entry_creation(self) -> None:
        """MemoryIndexEntry should be created with required fields."""
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry

        entry = MemoryIndexEntry(
            memory_id="mem-123",
            content="User prefers dark mode and Python over JavaScript",
            memory_type="preference",
        )

        assert entry.memory_id == "mem-123"
        assert entry.content == "User prefers dark mode and Python over JavaScript"
        assert entry.memory_type == "preference"

    def test_memory_index_entry_full(self) -> None:
        """MemoryIndexEntry should support all optional fields."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry

        entry = MemoryIndexEntry(
            memory_id="mem-456",
            content="Important context about the project",
            memory_type="context",
            embedding=[0.9, 0.8, 0.7],
            scope=CapabilityScope.SESSION,
            session_id="session-abc",
            user_id="user-xyz",
            tenant_id="tenant-123",
            timestamp=1704067200,
            importance_score=0.85,
        )

        assert entry.memory_type == "context"
        assert entry.session_id == "session-abc"
        assert entry.user_id == "user-xyz"
        assert entry.importance_score == 0.85

    def test_memory_index_entry_types(self) -> None:
        """MemoryIndexEntry should support different memory types."""
        from mcp_server_langgraph.tools.semantic_index import MemoryIndexEntry, MemoryType

        # Preference memory
        pref = MemoryIndexEntry(
            memory_id="mem-pref",
            content="Prefers concise responses",
            memory_type=MemoryType.PREFERENCE,
        )
        assert pref.memory_type == "preference"

        # Context memory
        ctx = MemoryIndexEntry(
            memory_id="mem-ctx",
            content="Working on authentication module",
            memory_type=MemoryType.CONTEXT,
        )
        assert ctx.memory_type == "context"

        # Fact memory
        fact = MemoryIndexEntry(
            memory_id="mem-fact",
            content="API key stored in environment variable",
            memory_type=MemoryType.FACT,
        )
        assert fact.memory_type == "fact"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_models")
class TestIndexEntryCategories:
    """Tests for tool and skill category constants."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_categories_defined(self) -> None:
        """Standard tool categories should be defined."""
        from mcp_server_langgraph.tools.semantic_index import ToolCategory

        # Verify key categories exist
        assert ToolCategory.CALCULATOR == "calculator"
        assert ToolCategory.SEARCH == "search"
        assert ToolCategory.FILESYSTEM == "filesystem"
        assert ToolCategory.CODE_EXECUTION == "code_execution"
        assert ToolCategory.WEB == "web"
        assert ToolCategory.COMPUTER_USE == "computer_use"

    def test_skill_categories_defined(self) -> None:
        """Standard skill categories should be defined."""
        from mcp_server_langgraph.tools.semantic_index import SkillCategory

        # Verify key categories exist
        assert SkillCategory.DEVELOPMENT == "development"
        assert SkillCategory.ANALYSIS == "analysis"
        assert SkillCategory.WRITING == "writing"
        assert SkillCategory.RESEARCH == "research"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_validation")
class TestToolIndexEntryValidation:
    """Tests for ToolIndexEntry tool_id format validation (v26).

    Single regex pattern: ^(builtin|mcp):.+$
    - __post_init__: Raises ValueError (fail-fast for new tools)
    - from_payload(): Returns None silently (wrapper logs summary)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "valid_id",
        [
            "builtin:web_search",
            "builtin:calculator",
            "builtin:a",  # Minimal valid
            "mcp:github:create_issue",
            "mcp:server:tool",
            "mcp:server:nested:tool",  # MCP can have multiple colons
        ],
    )
    def test_post_init_accepts_valid_formats(self, valid_id: str) -> None:
        """__post_init__ accepts valid builtin: and mcp: formats."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Should not raise
        entry = ToolIndexEntry(
            tool_id=valid_id,
            name="test",
            description="Test",
            category="test",
        )
        assert entry.tool_id == valid_id

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "tool:web_search",  # Old format (wrong prefix)
            "tool-abc123",  # Old UUID format
            "native:code_exec",  # Native format (not valid - never existed)
            "invalid:calculator",  # Wrong prefix
            "web_search",  # No prefix
            "builtin:",  # Empty name
            ":web_search",  # Empty prefix
            # Empty string is tested separately in test_post_init_rejects_empty_tool_id
            "  ",  # Whitespace
            "builtin",  # No colon
            "mcp",  # No colon
        ],
    )
    def test_post_init_rejects_invalid_formats(self, invalid_id: str) -> None:
        """__post_init__ raises ValueError for invalid tool_id formats."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        with pytest.raises(ValueError, match="Invalid tool_id format"):
            ToolIndexEntry(
                tool_id=invalid_id,
                name="test",
                description="Test",
                category="test",
            )

    def test_post_init_rejects_empty_tool_id(self) -> None:
        """__post_init__ raises ValueError for empty tool_id."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        with pytest.raises(ValueError, match="tool_id is required"):
            ToolIndexEntry(
                tool_id="",
                name="test",
                description="Test",
                category="test",
            )


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_validation")
class TestToolIndexEntryFromLangchainTool:
    """Tests for ToolIndexEntry.from_langchain_tool() factory method (v26).

    tool_id is REQUIRED - raises ValueError if None or invalid format.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_from_langchain_tool_with_valid_tool_id(self) -> None:
        """from_langchain_tool() accepts valid tool_id."""
        from unittest.mock import MagicMock

        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "calculator"
        mock_tool.description = "Math operations"
        mock_tool.args_schema = None

        entry = ToolIndexEntry.from_langchain_tool(mock_tool, tool_id="builtin:calculator")

        assert entry.tool_id == "builtin:calculator"
        assert entry.name == "calculator"
        assert entry.description == "Math operations"

    def test_from_langchain_tool_with_mcp_tool_id(self) -> None:
        """from_langchain_tool() accepts MCP tool_id format."""
        from unittest.mock import MagicMock

        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "create_issue"
        mock_tool.description = "Create a GitHub issue"
        mock_tool.args_schema = None

        entry = ToolIndexEntry.from_langchain_tool(mock_tool, tool_id="mcp:github:create_issue")

        assert entry.tool_id == "mcp:github:create_issue"

    def test_from_langchain_tool_raises_valueerror_when_tool_id_none(self) -> None:
        """from_langchain_tool() raises ValueError when tool_id is None."""
        from unittest.mock import MagicMock

        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "test"
        mock_tool.description = "Test"
        mock_tool.args_schema = None

        with pytest.raises(ValueError, match="tool_id is required"):
            ToolIndexEntry.from_langchain_tool(mock_tool, tool_id=None)

    def test_from_langchain_tool_raises_valueerror_for_invalid_format(self) -> None:
        """from_langchain_tool() raises ValueError for invalid format via __post_init__."""
        from unittest.mock import MagicMock

        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "test"
        mock_tool.description = "Test"
        mock_tool.args_schema = None

        with pytest.raises(ValueError, match="Invalid tool_id format"):
            ToolIndexEntry.from_langchain_tool(mock_tool, tool_id="invalid:format")

    def test_from_langchain_tool_extracts_parameters_summary(self) -> None:
        """from_langchain_tool() extracts parameters from args_schema."""
        from unittest.mock import MagicMock

        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.name = "calculator"
        mock_tool.description = "Math operations"

        # Mock args_schema with model_json_schema
        mock_schema = MagicMock()
        mock_schema.model_json_schema.return_value = {
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            }
        }
        mock_tool.args_schema = mock_schema

        entry = ToolIndexEntry.from_langchain_tool(mock_tool, tool_id="builtin:calculator")

        assert "a: integer" in entry.parameters_summary
        assert "b: integer" in entry.parameters_summary


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_validation")
class TestToolIndexEntryFromPayload:
    """Tests for ToolIndexEntry.from_payload() factory method (v26).

    Returns None silently for invalid/legacy data (wrapper handles logging).
    ONLY builtin: and mcp: formats are valid (no native:).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_from_payload_returns_entry_for_valid_builtin(self) -> None:
        """Valid builtin: payload returns ToolIndexEntry."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {
            "tool_id": "builtin:calculator",
            "name": "calculator",
            "description": "Math operations",
            "category": "math",
        }
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is not None
        assert entry.tool_id == "builtin:calculator"
        assert entry.name == "calculator"

    def test_from_payload_returns_entry_for_valid_mcp(self) -> None:
        """Valid mcp: payload returns ToolIndexEntry."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {
            "tool_id": "mcp:github:create_issue",
            "name": "create_issue",
            "description": "Create a GitHub issue",
            "category": "dev",
        }
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is not None
        assert entry.tool_id == "mcp:github:create_issue"

    def test_from_payload_rejects_native_prefix(self) -> None:
        """native: prefix is rejected - format never existed."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {
            "tool_id": "native:code_execution",
            "name": "code",
            "description": "Execute code",
            "category": "execution",
        }
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is None  # Rejected silently

    def test_from_payload_returns_none_for_missing_tool_id(self) -> None:
        """Missing tool_id returns None (silent skip)."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {"name": "calculator", "description": "Math"}
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is None

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "tool:web_search",  # Old format
            "tool-abc123",  # Old UUID format
            "native:code_exec",  # Native rejected (format never existed)
            "",  # Empty string
            "invalid:format",  # Wrong prefix
        ],
    )
    def test_from_payload_skips_invalid_formats(self, invalid_id: str) -> None:
        """Invalid/legacy formats are silently skipped."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {"tool_id": invalid_id, "name": "test", "description": "test"}
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is None

    def test_from_payload_preserves_embedding(self) -> None:
        """from_payload() preserves embedding from argument."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {
            "tool_id": "builtin:calculator",
            "name": "calculator",
            "description": "Math operations",
            "category": "math",
        }
        embedding = [0.1, 0.2, 0.3]
        entry = ToolIndexEntry.from_payload(payload, embedding=embedding)

        assert entry is not None
        assert entry.embedding == [0.1, 0.2, 0.3]

    def test_from_payload_handles_all_optional_fields(self) -> None:
        """from_payload() handles all optional fields correctly."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        payload = {
            "tool_id": "builtin:web_search",
            "name": "web_search",
            "description": "Search the web",
            "category": "search",
            "scope": "project",
            "tenant_id": "tenant-123",
            "parameters_summary": "query: str",
            "token_estimate": 100,
        }
        entry = ToolIndexEntry.from_payload(payload)

        assert entry is not None
        assert entry.scope == CapabilityScope.PROJECT
        assert entry.tenant_id == "tenant-123"
        assert entry.parameters_summary == "query: str"
        assert entry.token_estimate == 100


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_validation")
class TestReconstructToolsFromPayloads:
    """Tests for reconstruct_tools_from_payloads() shared wrapper (v26).

    Required in production. Handles summary logging for skipped entries.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_reconstruct_returns_valid_entries(self) -> None:
        """Wrapper returns valid ToolIndexEntry objects."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        results = [
            MagicMock(
                payload={"tool_id": "builtin:calc", "name": "calc", "description": "d", "category": "c"},
                vector=None,
            ),
            MagicMock(
                payload={"tool_id": "mcp:gh:issue", "name": "issue", "description": "d", "category": "c"},
                vector=[0.1, 0.2],
            ),
        ]
        mock_logger = MagicMock()

        entries = reconstruct_tools_from_payloads(results, mock_logger)

        assert len(entries) == 2
        assert entries[0].tool_id == "builtin:calc"
        assert entries[1].tool_id == "mcp:gh:issue"
        assert entries[1].embedding == [0.1, 0.2]
        mock_logger.warning.assert_not_called()

    def test_reconstruct_skips_invalid_entries(self) -> None:
        """Wrapper skips entries with invalid tool_id."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        results = [
            MagicMock(
                payload={"tool_id": "builtin:valid", "name": "v", "description": "d", "category": "c"},
                vector=None,
            ),
            MagicMock(
                payload={"tool_id": "tool-legacy", "name": "l", "description": "d", "category": "c"},
                vector=None,
            ),  # Invalid
            MagicMock(
                payload={"tool_id": "native:skip", "name": "s", "description": "d", "category": "c"},
                vector=None,
            ),  # Invalid
        ]
        mock_logger = MagicMock()

        entries = reconstruct_tools_from_payloads(results, mock_logger)

        assert len(entries) == 1
        assert entries[0].tool_id == "builtin:valid"

    def test_reconstruct_logs_summary_warning(self) -> None:
        """Wrapper logs single summary warning for skipped entries."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        results = [
            MagicMock(
                payload={"tool_id": "builtin:valid", "name": "v", "description": "d", "category": "c"},
                vector=None,
            ),
            MagicMock(
                payload={"tool_id": "tool-legacy", "name": "l", "description": "d", "category": "c"},
                vector=None,
            ),  # Invalid
            MagicMock(
                payload={"tool_id": "native:skip", "name": "s", "description": "d", "category": "c"},
                vector=None,
            ),  # Invalid
        ]
        mock_logger = MagicMock()

        reconstruct_tools_from_payloads(results, mock_logger)

        mock_logger.warning.assert_called_once_with("Skipped 2 invalid/legacy entries during search")

    def test_reconstruct_no_warning_when_all_valid(self) -> None:
        """Wrapper does not log warning when all entries are valid."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        results = [
            MagicMock(
                payload={"tool_id": "builtin:one", "name": "o", "description": "d", "category": "c"},
                vector=None,
            ),
            MagicMock(
                payload={"tool_id": "mcp:two:t", "name": "t", "description": "d", "category": "c"},
                vector=None,
            ),
        ]
        mock_logger = MagicMock()

        reconstruct_tools_from_payloads(results, mock_logger)

        mock_logger.warning.assert_not_called()

    def test_reconstruct_handles_empty_results(self) -> None:
        """Wrapper handles empty results list."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        mock_logger = MagicMock()
        entries = reconstruct_tools_from_payloads([], mock_logger)

        assert entries == []
        mock_logger.warning.assert_not_called()

    def test_reconstruct_handles_none_payload(self) -> None:
        """Wrapper handles result with None payload."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.tools.semantic_index import (
            reconstruct_tools_from_payloads,
        )

        results = [
            MagicMock(payload=None, vector=None),
            MagicMock(
                payload={"tool_id": "builtin:valid", "name": "v", "description": "d", "category": "c"},
                vector=None,
            ),
        ]
        mock_logger = MagicMock()

        entries = reconstruct_tools_from_payloads(results, mock_logger)

        assert len(entries) == 1
        mock_logger.warning.assert_called_once_with("Skipped 1 invalid/legacy entries during search")
