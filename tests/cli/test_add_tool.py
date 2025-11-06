"""
Tests for add_tool CLI command.

Tests the tool file generation and scaffolding functionality.
Target Coverage: 80%+ (line and branch)

Tests cover:
- Tool file generation with valid inputs
- Test file creation
- Template substitution (class names, function names)
- Error handling (FileExistsError)
- Edge cases (special characters, empty inputs)
"""

from pathlib import Path

import pytest

from mcp_server_langgraph.cli.add_tool import TOOL_TEMPLATE, generate_tool

# ==============================================================================
# Test generate_tool Function
# ==============================================================================


@pytest.mark.unit
class TestGenerateTool:
    """Test tool file generation functionality."""

    def test_generate_tool_creates_tool_file(self, tmp_path, monkeypatch):
        """Test generate_tool creates tool file in correct location."""
        # Change to tmp_path so src/tools is created there
        monkeypatch.chdir(tmp_path)

        generate_tool("example_tool", "An example tool for testing")

        tool_file = tmp_path / "src" / "tools" / "example_tool_tool.py"
        assert tool_file.exists()

    def test_generate_tool_creates_test_file(self, tmp_path, monkeypatch):
        """Test generate_tool creates test file."""
        monkeypatch.chdir(tmp_path)

        generate_tool("test_tool", "A test tool")

        test_file = tmp_path / "tests" / "tools" / "test_test_tool_tool.py"
        assert test_file.exists()

    def test_generate_tool_with_underscores_in_name(self, tmp_path, monkeypatch):
        """Test tool generation with snake_case name."""
        monkeypatch.chdir(tmp_path)

        generate_tool("web_scraper_tool", "Scrapes web pages")

        tool_file = tmp_path / "src" / "tools" / "web_scraper_tool_tool.py"
        assert tool_file.exists()

        content = tool_file.read_text()

        # Verify class name is PascalCase
        assert "class WebScraperToolInput" in content
        assert "class WebScraperToolOutput" in content

        # Verify function name is snake_case
        assert "def web_scraper_tool(" in content

    def test_generate_tool_with_hyphens_in_name(self, tmp_path, monkeypatch):
        """Test tool generation converts hyphens to underscores in function names."""
        monkeypatch.chdir(tmp_path)

        generate_tool("api-client", "API client tool")

        tool_file = tmp_path / "src" / "tools" / "api-client_tool.py"
        content = tool_file.read_text()

        # Function name should use underscores, not hyphens
        assert "def api_client(" in content

    def test_generate_tool_template_substitution(self, tmp_path, monkeypatch):
        """Test template correctly substitutes all placeholders."""
        monkeypatch.chdir(tmp_path)

        generate_tool("calculator", "Performs mathematical calculations")

        tool_file = tmp_path / "src" / "tools" / "calculator_tool.py"
        content = tool_file.read_text()

        # Verify all substitutions
        assert "class CalculatorInput(BaseModel):" in content
        assert "class CalculatorOutput(BaseModel):" in content
        assert "def calculator(input_data: CalculatorInput) -> CalculatorOutput:" in content
        assert '"name": "calculator"' in content
        assert '"description": "Performs mathematical calculations"' in content

    def test_generate_tool_includes_pydantic_models(self, tmp_path, monkeypatch):
        """Test generated tool includes Pydantic model definitions."""
        monkeypatch.chdir(tmp_path)

        generate_tool("validator", "Validates data")

        tool_file = tmp_path / "src" / "tools" / "validator_tool.py"
        content = tool_file.read_text()

        # Verify Pydantic imports and models
        assert "from pydantic import BaseModel, Field" in content
        assert "ValidatorInput(BaseModel)" in content
        assert "ValidatorOutput(BaseModel)" in content

    def test_generate_tool_includes_metadata(self, tmp_path, monkeypatch):
        """Test generated tool includes MCP metadata."""
        monkeypatch.chdir(tmp_path)

        generate_tool("fetcher", "Fetches data from APIs")

        tool_file = tmp_path / "src" / "tools" / "fetcher_tool.py"
        content = tool_file.read_text()

        # Verify metadata section
        assert "TOOL_METADATA =" in content
        assert '"name": "fetcher"' in content
        assert '"description": "Fetches data from APIs"' in content
        assert "input_schema" in content
        assert "output_schema" in content

    def test_generate_tool_raises_error_if_file_exists(self, tmp_path, monkeypatch):
        """Test generate_tool raises FileExistsError if tool file already exists."""
        monkeypatch.chdir(tmp_path)

        # Create tool first time
        generate_tool("duplicate_tool", "First generation")

        # Try to create again - should raise error
        with pytest.raises(FileExistsError) as exc_info:
            generate_tool("duplicate_tool", "Second generation")

        assert "already exists" in str(exc_info.value)
        assert "duplicate_tool_tool.py" in str(exc_info.value)

    def test_generate_tool_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test generate_tool creates src/tools directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Ensure directory doesn't exist initially
        tools_dir = tmp_path / "src" / "tools"
        assert not tools_dir.exists()

        generate_tool("first_tool", "First tool created")

        # Directory should now exist
        assert tools_dir.exists()
        assert tools_dir.is_dir()

    def test_generate_tool_creates_test_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test generate_tool creates tests/tools directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        # Ensure directory doesn't exist initially
        tests_dir = tmp_path / "tests" / "tools"
        assert not tests_dir.exists()

        generate_tool("new_tool", "New tool with tests")

        # Directory should now exist
        assert tests_dir.exists()
        assert tests_dir.is_dir()

    def test_generate_tool_test_file_content(self, tmp_path, monkeypatch):
        """Test generated test file has correct structure."""
        monkeypatch.chdir(tmp_path)

        generate_tool("processor", "Processes data")

        test_file = tmp_path / "tests" / "tools" / "test_processor_tool.py"
        content = test_file.read_text()

        # Verify test structure
        assert "import pytest" in content
        assert "from src.tools.processor_tool import" in content
        assert "processor" in content
        assert "ProcessorInput" in content
        assert "ProcessorOutput" in content
        assert "def test_processor_success():" in content
        assert "def test_processor_with_empty_input():" in content
        assert "@pytest.mark.parametrize" in content

    def test_generate_tool_single_word_name(self, tmp_path, monkeypatch):
        """Test tool generation with single word name."""
        monkeypatch.chdir(tmp_path)

        generate_tool("logger", "Logs messages")

        tool_file = tmp_path / "src" / "tools" / "logger_tool.py"
        content = tool_file.read_text()

        # Single word should still be capitalized for class name
        assert "class LoggerInput" in content
        assert "class LoggerOutput" in content
        assert "def logger(" in content

    def test_generate_tool_multiple_words_with_underscores(self, tmp_path, monkeypatch):
        """Test tool generation with multiple underscored words."""
        monkeypatch.chdir(tmp_path)

        generate_tool("advanced_data_processor", "Processes advanced data")

        tool_file = tmp_path / "src" / "tools" / "advanced_data_processor_tool.py"
        content = tool_file.read_text()

        # Verify PascalCase class name
        assert "class AdvancedDataProcessorInput" in content
        assert "class AdvancedDataProcessorOutput" in content

        # Verify snake_case function name
        assert "def advanced_data_processor(" in content

    def test_generate_tool_description_preserved(self, tmp_path, monkeypatch):
        """Test tool description is preserved in generated files."""
        monkeypatch.chdir(tmp_path)

        description = "A complex tool with special characters: @#$%"
        generate_tool("special_tool", description)

        tool_file = tmp_path / "src" / "tools" / "special_tool_tool.py"
        content = tool_file.read_text()

        # Description should be in both docstring and metadata
        assert description in content

    def test_generate_tool_file_is_valid_python(self, tmp_path, monkeypatch):
        """Test generated tool file is syntactically valid Python."""
        monkeypatch.chdir(tmp_path)

        generate_tool("syntax_check", "Tool to check syntax")

        tool_file = tmp_path / "src" / "tools" / "syntax_check_tool.py"

        # Try to compile the file (will raise SyntaxError if invalid)
        content = tool_file.read_text()
        compile(content, str(tool_file), "exec")

    def test_generate_tool_test_file_is_valid_python(self, tmp_path, monkeypatch):
        """Test generated test file is syntactically valid Python."""
        monkeypatch.chdir(tmp_path)

        generate_tool("test_syntax", "Test syntax check")

        test_file = tmp_path / "tests" / "tools" / "test_test_syntax_tool.py"

        # Try to compile the file (will raise SyntaxError if invalid)
        content = test_file.read_text()
        compile(content, str(test_file), "exec")


# ==============================================================================
# Test Tool Template
# ==============================================================================


@pytest.mark.unit
class TestToolTemplate:
    """Test the tool template structure."""

    def test_tool_template_contains_required_placeholders(self):
        """Test TOOL_TEMPLATE contains all required placeholder variables."""
        required_placeholders = [
            "{name}",
            "{description}",
            "{class_name}",
            "{function_name}",
        ]

        for placeholder in required_placeholders:
            assert placeholder in TOOL_TEMPLATE, f"Missing placeholder: {placeholder}"

    def test_tool_template_has_input_output_models(self):
        """Test template includes Pydantic input/output models."""
        assert "class {class_name}Input(BaseModel):" in TOOL_TEMPLATE
        assert "class {class_name}Output(BaseModel):" in TOOL_TEMPLATE

    def test_tool_template_has_function_definition(self):
        """Test template includes function definition."""
        assert "def {function_name}(input_data: {class_name}Input) -> {class_name}Output:" in TOOL_TEMPLATE

    def test_tool_template_has_metadata(self):
        """Test template includes metadata for MCP registration."""
        assert "TOOL_METADATA =" in TOOL_TEMPLATE
        assert '"name": "{name}"' in TOOL_TEMPLATE
        assert '"description": "{description}"' in TOOL_TEMPLATE

    def test_tool_template_has_error_handling(self):
        """Test template includes error handling in function."""
        assert "try:" in TOOL_TEMPLATE
        assert "except Exception as e:" in TOOL_TEMPLATE

    def test_tool_template_can_be_formatted(self):
        """Test template can be formatted with sample values."""
        formatted = TOOL_TEMPLATE.format(
            name="test_tool",
            description="Test description",
            class_name="TestTool",
            function_name="test_tool",
        )

        # Verify template placeholders were replaced
        assert "{name}" not in formatted
        assert "{description}" not in formatted
        assert "{class_name}" not in formatted
        assert "{function_name}" not in formatted

        # Verify substituted values are present
        assert "test_tool" in formatted
        assert "Test description" in formatted


# ==============================================================================
# Edge Cases and Error Scenarios
# ==============================================================================


@pytest.mark.unit
class TestGenerateToolEdgeCases:
    """Test edge cases and error scenarios for generate_tool."""

    def test_generate_tool_with_numbers_in_name(self, tmp_path, monkeypatch):
        """Test tool generation with numbers in name."""
        monkeypatch.chdir(tmp_path)

        generate_tool("parser_v2", "Version 2 parser")

        tool_file = tmp_path / "src" / "tools" / "parser_v2_tool.py"
        assert tool_file.exists()

        content = tool_file.read_text()
        assert "class ParserV2Input" in content

    def test_generate_tool_preserves_tool_metadata_structure(self, tmp_path, monkeypatch):
        """Test metadata structure is valid Python dict."""
        monkeypatch.chdir(tmp_path)

        generate_tool("metadata_test", "Testing metadata")

        tool_file = tmp_path / "src" / "tools" / "metadata_test_tool.py"
        content = tool_file.read_text()

        # Metadata should be valid Python
        assert "TOOL_METADATA = {" in content
        assert "model_json_schema()" in content

    def test_generate_tool_test_imports_correct_module(self, tmp_path, monkeypatch):
        """Test test file imports from correct module path."""
        monkeypatch.chdir(tmp_path)

        generate_tool("import_test", "Test imports")

        test_file = tmp_path / "tests" / "tools" / "test_import_test_tool.py"
        content = test_file.read_text()

        # Verify correct import path
        assert "from src.tools.import_test_tool import" in content

    def test_generate_tool_empty_description(self, tmp_path, monkeypatch):
        """Test tool generation with empty description."""
        monkeypatch.chdir(tmp_path)

        generate_tool("no_desc", "")

        tool_file = tmp_path / "src" / "tools" / "no_desc_tool.py"
        content = tool_file.read_text()

        # Empty description should still work
        assert '"description": ""' in content

    def test_generate_tool_very_long_name(self, tmp_path, monkeypatch):
        """Test tool generation with very long name."""
        monkeypatch.chdir(tmp_path)

        long_name = "very_long_tool_name_with_many_words_for_testing_purposes"
        generate_tool(long_name, "Long name test")

        tool_file = tmp_path / "src" / "tools" / f"{long_name}_tool.py"
        assert tool_file.exists()

    def test_generate_tool_preserves_directory_structure(self, tmp_path, monkeypatch):
        """Test generate_tool doesn't interfere with existing files."""
        monkeypatch.chdir(tmp_path)

        # Create first tool
        generate_tool("tool_one", "First tool")

        # Create another unrelated file
        (tmp_path / "src" / "tools" / "manual_file.py").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "tools" / "manual_file.py").write_text("# Manual file")

        # Create second tool
        generate_tool("tool_two", "Second tool")

        # Verify all files exist
        assert (tmp_path / "src" / "tools" / "tool_one_tool.py").exists()
        assert (tmp_path / "src" / "tools" / "tool_two_tool.py").exists()
        assert (tmp_path / "src" / "tools" / "manual_file.py").exists()
        assert (tmp_path / "src" / "tools" / "manual_file.py").read_text() == "# Manual file"
