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
            tool_id="tool-123",
            name="calculator",
            description="Perform mathematical calculations",
            category="math",
        )

        assert entry.tool_id == "tool-123"
        assert entry.name == "calculator"
        assert entry.description == "Perform mathematical calculations"
        assert entry.category == "math"

    def test_tool_index_entry_creation_full(self) -> None:
        """ToolIndexEntry should support all optional fields."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="tool-456",
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
            tool_id="tool-789",
            name="read_file",
            description="Read file contents",
            category="filesystem",
        )

        assert entry.scope == CapabilityScope.SESSION

    def test_tool_index_entry_default_embedding_is_none(self) -> None:
        """ToolIndexEntry should default embedding to None."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="tool-001",
            name="test_tool",
            description="Test tool",
            category="test",
        )

        assert entry.embedding is None

    def test_tool_index_entry_to_dict(self) -> None:
        """ToolIndexEntry should be convertible to dict for Qdrant payload."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry = ToolIndexEntry(
            tool_id="tool-dict",
            name="dict_tool",
            description="Dict test tool",
            category="test",
            token_estimate=100,
        )

        entry_dict = entry.to_dict()

        assert isinstance(entry_dict, dict)
        assert entry_dict["tool_id"] == "tool-dict"
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

        entry = ToolIndexEntry.from_langchain_tool(lc_tool, category="test")

        assert entry.name == "sample_tool"
        assert entry.description == "A sample tool for testing"
        assert entry.category == "test"
        assert entry.tool_id.startswith("tool-")

    def test_tool_index_entry_equality(self) -> None:
        """ToolIndexEntry with same tool_id should be equal."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry1 = ToolIndexEntry(
            tool_id="tool-eq",
            name="eq_tool",
            description="Equality test",
            category="test",
        )
        entry2 = ToolIndexEntry(
            tool_id="tool-eq",
            name="eq_tool",
            description="Equality test",
            category="test",
        )

        assert entry1 == entry2

    def test_tool_index_entry_hash_for_set(self) -> None:
        """ToolIndexEntry should be hashable for use in sets."""
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        entry1 = ToolIndexEntry(
            tool_id="tool-hash1",
            name="hash_tool_1",
            description="Hash test 1",
            category="test",
        )
        entry2 = ToolIndexEntry(
            tool_id="tool-hash2",
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
