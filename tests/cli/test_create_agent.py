"""
Tests for create_agent CLI command.

Tests the agent file generation and scaffolding functionality.
Target Coverage: 80%+ (line and branch)

Tests cover:
- Agent file generation with valid inputs
- Template selection (basic, research, customer-support)
- Test file creation
- Template substitution
- Error handling (ValueError, FileExistsError)
- Edge cases
"""

import gc

import pytest

from mcp_server_langgraph.cli.create_agent import AGENT_TEMPLATES, generate_agent

pytestmark = pytest.mark.unit

# ==============================================================================
# Test generate_agent Function
# ==============================================================================


@pytest.mark.cli
@pytest.mark.xdist_group(name="testgenerateagent")
class TestGenerateAgent:
    """Test agent file generation functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_generate_agent_creates_agent_file(self, tmp_path, monkeypatch):
        """Test generate_agent creates agent file in correct location."""
        monkeypatch.chdir(tmp_path)

        generate_agent("my_agent", template="basic")

        agent_file = tmp_path / "src" / "agents" / "my_agent_agent.py"
        assert agent_file.exists()

    def test_generate_agent_creates_test_file(self, tmp_path, monkeypatch):
        """Test generate_agent creates test file."""
        monkeypatch.chdir(tmp_path)

        generate_agent("test_agent", template="basic")

        test_file = tmp_path / "tests" / "agents" / "test_test_agent_agent.py"
        assert test_file.exists()

    def test_generate_agent_basic_template(self, tmp_path, monkeypatch):
        """Test agent generation with basic template."""
        monkeypatch.chdir(tmp_path)

        generate_agent("simple", template="basic")

        agent_file = tmp_path / "src" / "agents" / "simple_agent.py"
        content = agent_file.read_text()

        # Verify basic template components
        assert "class SimpleState(TypedDict):" in content
        assert "def process_query(state: SimpleState)" in content
        assert "simple_agent = graph.compile()" in content

    def test_generate_agent_research_template(self, tmp_path, monkeypatch):
        """Test agent generation with research template."""
        monkeypatch.chdir(tmp_path)

        generate_agent("researcher", template="research")

        agent_file = tmp_path / "src" / "agents" / "researcher_agent.py"
        content = agent_file.read_text()

        # Verify research template components
        assert "class ResearchState(TypedDict):" in content
        assert "def search(state: ResearchState)" in content
        assert "def summarize(state: ResearchState)" in content
        assert "research_agent = graph.compile()" in content

    def test_generate_agent_customer_support_template(self, tmp_path, monkeypatch):
        """Test agent generation with customer-support template."""
        monkeypatch.chdir(tmp_path)

        generate_agent("support", template="customer-support")

        agent_file = tmp_path / "src" / "agents" / "support_agent.py"
        content = agent_file.read_text()

        # Verify customer-support template components
        assert "class SupportState(TypedDict):" in content
        assert "def classify_intent(state: SupportState)" in content
        assert "def handle_faq(state: SupportState)" in content
        assert "def escalate(state: SupportState)" in content
        assert "support_agent = graph.compile()" in content

    def test_generate_agent_invalid_template_raises_error(self, tmp_path, monkeypatch):
        """Test generate_agent raises ValueError for invalid template."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            generate_agent("bad_agent", template="invalid_template")

        assert "Invalid template" in str(exc_info.value)
        assert "invalid_template" in str(exc_info.value)

    def test_generate_agent_raises_error_if_file_exists(self, tmp_path, monkeypatch):
        """Test generate_agent raises FileExistsError if agent file already exists."""
        monkeypatch.chdir(tmp_path)

        # Create agent first time
        generate_agent("duplicate", template="basic")

        # Try to create again - should raise error
        with pytest.raises(FileExistsError) as exc_info:
            generate_agent("duplicate", template="basic")

        assert "already exists" in str(exc_info.value)
        assert "duplicate_agent.py" in str(exc_info.value)

    def test_generate_agent_with_underscores_in_name(self, tmp_path, monkeypatch):
        """Test agent generation with snake_case name."""
        monkeypatch.chdir(tmp_path)

        generate_agent("data_analyzer", template="basic")

        agent_file = tmp_path / "src" / "agents" / "data_analyzer_agent.py"
        content = agent_file.read_text()

        # Verify class name is PascalCase
        assert "class DataAnalyzerState(TypedDict):" in content

    def test_generate_agent_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test generate_agent creates src/agents directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Ensure directory doesn't exist initially
        agents_dir = tmp_path / "src" / "agents"
        assert not agents_dir.exists()

        generate_agent("first_agent", template="basic")

        # Directory should now exist
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_generate_agent_creates_test_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test generate_agent creates tests/agents directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Ensure directory doesn't exist initially
        tests_dir = tmp_path / "tests" / "agents"
        assert not tests_dir.exists()

        generate_agent("new_agent", template="basic")

        # Directory should now exist
        assert tests_dir.exists()
        assert tests_dir.is_dir()

    def test_generate_agent_test_file_content(self, tmp_path, monkeypatch):
        """Test generated test file has correct structure."""
        monkeypatch.chdir(tmp_path)

        generate_agent("testable", template="basic")

        test_file = tmp_path / "tests" / "agents" / "test_testable_agent.py"
        content = test_file.read_text()

        # Verify test structure
        assert "import pytest" in content
        assert "from src.agents.testable_agent import testable_agent" in content
        assert "def test_testable_agent_basic():" in content
        assert "@pytest.mark.asyncio" in content
        assert "async def test_testable_agent_async():" in content

    def test_generate_agent_default_template_is_basic(self, tmp_path, monkeypatch):
        """Test generate_agent uses 'basic' template by default."""
        monkeypatch.chdir(tmp_path)

        # Call without template parameter
        generate_agent("default_template")

        agent_file = tmp_path / "src" / "agents" / "default_template_agent.py"
        content = agent_file.read_text()

        # Should use basic template
        assert "def process_query" in content

    def test_generate_agent_tools_parameter_accepted(self, tmp_path, monkeypatch):
        """Test generate_agent accepts tools parameter without error."""
        monkeypatch.chdir(tmp_path)

        # Should not raise error even though tools not used yet
        generate_agent("tool_agent", template="basic", tools=["search", "calculator"])

        agent_file = tmp_path / "src" / "agents" / "tool_agent_agent.py"
        assert agent_file.exists()

    def test_generate_agent_single_word_name(self, tmp_path, monkeypatch):
        """Test agent generation with single word name."""
        monkeypatch.chdir(tmp_path)

        generate_agent("helper", template="basic")

        agent_file = tmp_path / "src" / "agents" / "helper_agent.py"
        content = agent_file.read_text()

        # Single word should still be capitalized for class name
        assert "class HelperState(TypedDict):" in content

    def test_generate_agent_multiple_words_with_underscores(self, tmp_path, monkeypatch):
        """Test agent generation with multiple underscored words."""
        monkeypatch.chdir(tmp_path)

        generate_agent("advanced_research_agent", template="basic")

        agent_file = tmp_path / "src" / "agents" / "advanced_research_agent_agent.py"
        content = agent_file.read_text()

        # Verify PascalCase class name
        assert "class AdvancedResearchAgentState(TypedDict):" in content

    def test_generate_agent_file_is_valid_python(self, tmp_path, monkeypatch):
        """Test generated agent file is syntactically valid Python."""
        monkeypatch.chdir(tmp_path)

        generate_agent("syntax_check", template="basic")

        agent_file = tmp_path / "src" / "agents" / "syntax_check_agent.py"

        # Try to compile the file (will raise SyntaxError if invalid)
        content = agent_file.read_text()
        compile(content, str(agent_file), "exec")

    def test_generate_agent_test_file_is_valid_python(self, tmp_path, monkeypatch):
        """Test generated test file is syntactically valid Python."""
        monkeypatch.chdir(tmp_path)

        generate_agent("test_syntax", template="basic")

        test_file = tmp_path / "tests" / "agents" / "test_test_syntax_agent.py"

        # Try to compile the file (will raise SyntaxError if invalid)
        content = test_file.read_text()
        compile(content, str(test_file), "exec")


# ==============================================================================
# Test Agent Templates
# ==============================================================================


@pytest.mark.cli
@pytest.mark.xdist_group(name="testagenttemplates")
class TestAgentTemplates:
    """Test agent template structures."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_templates_dict_exists(self):
        """Test AGENT_TEMPLATES dictionary exists and has templates."""
        assert isinstance(AGENT_TEMPLATES, dict)
        assert len(AGENT_TEMPLATES) > 0

    def test_agent_templates_has_basic(self):
        """Test basic template exists."""
        assert "basic" in AGENT_TEMPLATES
        assert AGENT_TEMPLATES["basic"] is not None

    def test_agent_templates_has_research(self):
        """Test research template exists."""
        assert "research" in AGENT_TEMPLATES
        assert AGENT_TEMPLATES["research"] is not None

    def test_agent_templates_has_customer_support(self):
        """Test customer-support template exists."""
        assert "customer-support" in AGENT_TEMPLATES
        assert AGENT_TEMPLATES["customer-support"] is not None

    def test_basic_template_contains_required_placeholders(self):
        """Test basic template contains required placeholder variables."""
        basic_template = AGENT_TEMPLATES["basic"]

        required_placeholders = [
            "{agent_name}",
            "{class_name}",
        ]

        for placeholder in required_placeholders:
            assert placeholder in basic_template, f"Missing placeholder: {placeholder}"

    def test_research_template_has_search_and_summarize(self):
        """Test research template has search and summarize nodes."""
        research_template = AGENT_TEMPLATES["research"]

        assert "def search(" in research_template
        assert "def summarize(" in research_template
        assert "ResearchState" in research_template

    def test_customer_support_template_has_classification(self):
        """Test customer-support template has intent classification."""
        support_template = AGENT_TEMPLATES["customer-support"]

        assert "def classify_intent(" in support_template
        assert "def handle_faq(" in support_template
        assert "def escalate(" in support_template
        assert "SupportState" in support_template

    def test_basic_template_can_be_formatted(self):
        """Test basic template can be formatted with sample values."""
        basic_template = AGENT_TEMPLATES["basic"]

        formatted = basic_template.format(
            agent_name="test_agent",
            class_name="TestAgent",
        )

        # Verify no placeholders remain
        assert "{agent_name}" not in formatted
        assert "{class_name}" not in formatted
        assert "test_agent" in formatted
        assert "TestAgent" in formatted

    def test_all_templates_use_langgraph(self):
        """Test all templates import LangGraph."""
        for template_name, template_content in AGENT_TEMPLATES.items():
            assert "from langgraph.graph import StateGraph" in template_content, f"{template_name} missing LangGraph import"

    def test_all_templates_have_typed_dict(self):
        """Test all templates use TypedDict for state."""
        for template_name, template_content in AGENT_TEMPLATES.items():
            assert "TypedDict" in template_content, f"{template_name} missing TypedDict"

    def test_all_templates_compile_graph(self):
        """Test all templates compile the graph."""
        for template_name, template_content in AGENT_TEMPLATES.items():
            assert ".compile()" in template_content, f"{template_name} doesn't compile graph"


# ==============================================================================
# Edge Cases and Error Scenarios
# ==============================================================================


@pytest.mark.cli
@pytest.mark.xdist_group(name="testgenerateagentedgecases")
class TestGenerateAgentEdgeCases:
    """Test edge cases and error scenarios for generate_agent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_generate_agent_with_numbers_in_name(self, tmp_path, monkeypatch):
        """Test agent generation with numbers in name."""
        monkeypatch.chdir(tmp_path)

        generate_agent("agent_v2", template="basic")

        agent_file = tmp_path / "src" / "agents" / "agent_v2_agent.py"
        assert agent_file.exists()

        content = agent_file.read_text()
        assert "class AgentV2State" in content

    def test_generate_agent_very_long_name(self, tmp_path, monkeypatch):
        """Test agent generation with very long name."""
        monkeypatch.chdir(tmp_path)

        long_name = "very_long_agent_name_with_many_words_for_testing"
        generate_agent(long_name, template="basic")

        agent_file = tmp_path / "src" / "agents" / f"{long_name}_agent.py"
        assert agent_file.exists()

    def test_generate_agent_preserves_directory_structure(self, tmp_path, monkeypatch):
        """Test generate_agent doesn't interfere with existing files."""
        monkeypatch.chdir(tmp_path)

        # Create first agent
        generate_agent("agent_one", template="basic")

        # Create another unrelated file
        (tmp_path / "src" / "agents" / "manual_file.py").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "agents" / "manual_file.py").write_text("# Manual file")

        # Create second agent
        generate_agent("agent_two", template="research")

        # Verify all files exist
        assert (tmp_path / "src" / "agents" / "agent_one_agent.py").exists()
        assert (tmp_path / "src" / "agents" / "agent_two_agent.py").exists()
        assert (tmp_path / "src" / "agents" / "manual_file.py").exists()
        assert (tmp_path / "src" / "agents" / "manual_file.py").read_text() == "# Manual file"

    def test_generate_agent_test_imports_correct_module(self, tmp_path, monkeypatch):
        """Test test file imports from correct module path."""
        monkeypatch.chdir(tmp_path)

        generate_agent("import_test", template="basic")

        test_file = tmp_path / "tests" / "agents" / "test_import_test_agent.py"
        content = test_file.read_text()

        # Verify correct import path
        assert "from src.agents.import_test_agent import import_test_agent" in content

    @pytest.mark.parametrize("template", ["basic", "research", "customer-support"])
    def test_generate_agent_all_templates_work(self, tmp_path, monkeypatch, template):
        """Test all agent templates can be generated without errors."""
        monkeypatch.chdir(tmp_path)

        agent_name = f"test_{template.replace('-', '_')}"
        generate_agent(agent_name, template=template)

        agent_file = tmp_path / "src" / "agents" / f"{agent_name}_agent.py"
        assert agent_file.exists()

        # Verify file is valid Python
        content = agent_file.read_text()
        compile(content, str(agent_file), "exec")

    def test_generate_agent_tools_parameter_none(self, tmp_path, monkeypatch):
        """Test generate_agent works with tools=None (default)."""
        monkeypatch.chdir(tmp_path)

        generate_agent("no_tools", template="basic", tools=None)

        agent_file = tmp_path / "src" / "agents" / "no_tools_agent.py"
        assert agent_file.exists()

    def test_generate_agent_tools_parameter_empty_list(self, tmp_path, monkeypatch):
        """Test generate_agent works with empty tools list."""
        monkeypatch.chdir(tmp_path)

        generate_agent("empty_tools", template="basic", tools=[])

        agent_file = tmp_path / "src" / "agents" / "empty_tools_agent.py"
        assert agent_file.exists()

    def test_generate_agent_multiple_agents_different_templates(self, tmp_path, monkeypatch):
        """Test generating multiple agents with different templates."""
        monkeypatch.chdir(tmp_path)

        generate_agent("basic_agent", template="basic")
        generate_agent("research_agent", template="research")
        generate_agent("support_agent", template="customer-support")

        # All should exist
        assert (tmp_path / "src" / "agents" / "basic_agent_agent.py").exists()
        assert (tmp_path / "src" / "agents" / "research_agent_agent.py").exists()
        assert (tmp_path / "src" / "agents" / "support_agent_agent.py").exists()

    def test_generate_agent_error_doesnt_create_partial_files(self, tmp_path, monkeypatch):
        """Test that validation errors don't create partial files."""
        monkeypatch.chdir(tmp_path)

        # Try to create with invalid template
        with pytest.raises(ValueError):
            generate_agent("bad_agent", template="nonexistent")

        # No agent file should be created
        agent_file = tmp_path / "src" / "agents" / "bad_agent_agent.py"
        assert not agent_file.exists()

    def test_generate_agent_case_sensitive_template_validation(self, tmp_path, monkeypatch):
        """Test template validation is case-sensitive."""
        monkeypatch.chdir(tmp_path)

        # "Basic" (capitalized) should fail, only "basic" is valid
        with pytest.raises(ValueError):
            generate_agent("caps_test", template="Basic")

    def test_generate_agent_preserves_agent_name_in_test(self, tmp_path, monkeypatch):
        """Test agent name is correctly used in test file."""
        monkeypatch.chdir(tmp_path)

        generate_agent("my_special_agent", template="basic")

        test_file = tmp_path / "tests" / "agents" / "test_my_special_agent_agent.py"
        content = test_file.read_text()

        # Agent name should appear in imports and tests
        assert "my_special_agent_agent" in content
        assert "test_my_special_agent_agent_basic" in content

    def test_generate_agent_research_template_structure(self, tmp_path, monkeypatch):
        """Test research template has correct graph structure."""
        monkeypatch.chdir(tmp_path)

        generate_agent("researcher", template="research")

        agent_file = tmp_path / "src" / "agents" / "researcher_agent.py"
        content = agent_file.read_text()

        # Verify graph edges
        assert 'graph.add_edge("search", "summarize")' in content
        assert 'graph.set_entry_point("search")' in content
        assert 'graph.set_finish_point("summarize")' in content

    def test_generate_agent_support_template_has_routing(self, tmp_path, monkeypatch):
        """Test customer-support template has conditional routing."""
        monkeypatch.chdir(tmp_path)

        generate_agent("supporter", template="customer-support")

        agent_file = tmp_path / "src" / "agents" / "supporter_agent.py"
        content = agent_file.read_text()

        # Verify routing logic
        assert "def route(state: SupportState) -> str:" in content
        assert "graph.add_conditional_edges" in content
