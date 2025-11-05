"""
Unit tests for code execution tools

Tests execute_python tool with mocked sandbox.
Following TDD best practices - these tests should FAIL until implementation is complete.
"""

import pytest
from unittest.mock import MagicMock, patch

# This import will fail initially - that's expected in TDD!
try:
    from mcp_server_langgraph.tools.code_execution_tools import execute_python
    from mcp_server_langgraph.execution import ExecutionResult
except ImportError:
    pytest.skip("Code execution tools not implemented yet", allow_module_level=True)


@pytest.mark.unit
class TestExecutePythonTool:
    """Test execute_python tool"""

    @pytest.fixture
    def mock_sandbox(self):
        """Create mock sandbox"""
        sandbox = MagicMock()
        sandbox.execute.return_value = ExecutionResult(
            success=True,
            stdout="Hello, World!\n",
            stderr="",
            exit_code=0,
            execution_time=0.5,
        )
        return sandbox

    def test_tool_has_correct_metadata(self):
        """Test tool has name and description"""
        assert execute_python.name == "execute_python"
        assert execute_python.description is not None
        assert len(execute_python.description) > 10

    def test_tool_schema_has_code_parameter(self):
        """Test tool schema includes code parameter"""
        schema = execute_python.args_schema.model_json_schema()
        assert "code" in str(schema)

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_simple_code_execution(self, mock_get_sandbox, mock_settings, mock_sandbox):
        """Test executing simple code"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math"]
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": "print('Hello, World!')"})

        assert "Hello, World!" in result
        assert "success" in result.lower() or "Hello" in result

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_code_validation_before_execution(self, mock_get_sandbox, mock_settings, mock_sandbox):
        """Test that code is validated before execution"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math"]
        mock_get_sandbox.return_value = mock_sandbox

        # Dangerous code should be rejected before hitting sandbox
        result = execute_python.invoke({"code": "import os; os.system('ls')"})

        # Should fail validation
        assert "not allowed" in result.lower() or "blocked" in result.lower() or "invalid" in result.lower() or "validation failed" in result.lower()

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_empty_code_rejection(self, mock_get_sandbox, mock_settings, mock_sandbox):
        """Test that empty code is rejected"""
        mock_settings.enable_code_execution = True
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": ""})

        assert "empty" in result.lower() or "invalid" in result.lower()

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_execution_error_handling(self, mock_get_sandbox, mock_settings):
        """Test handling of execution errors"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math"]

        mock_sandbox = MagicMock()
        mock_sandbox.execute.return_value = ExecutionResult(
            success=False,
            stdout="",
            stderr="NameError: name 'undefined_var' is not defined",
            exit_code=1,
            execution_time=0.1,
        )
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": "print(undefined_var)"})

        assert "error" in result.lower() or "NameError" in result

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_timeout_handling(self, mock_get_sandbox, mock_settings):
        """Test handling of timeout"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math", "time"]  # Add 'time'

        mock_sandbox = MagicMock()
        mock_sandbox.execute.return_value = ExecutionResult(
            success=False,
            stdout="",
            stderr="Execution timed out after 30s",
            exit_code=124,
            execution_time=30.0,
            timed_out=True,
        )
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": "import time; time.sleep(100)"})

        assert "timeout" in result.lower() or "timed out" in result.lower()

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_output_truncation(self, mock_get_sandbox, mock_settings):
        """Test that long output is truncated"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math"]

        mock_sandbox = MagicMock()
        # Create very long output
        long_output = "x" * 100000
        mock_sandbox.execute.return_value = ExecutionResult(
            success=True,
            stdout=long_output,
            stderr="",
            exit_code=0,
            execution_time=0.5,
        )
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": "print('x' * 100000)"})

        # Output should be truncated (less than 100000 chars)
        assert len(result) < 100000 or "truncated" in result.lower()

    @patch("mcp_server_langgraph.tools.code_execution_tools.settings")
    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_custom_timeout(self, mock_get_sandbox, mock_settings, mock_sandbox):
        """Test executing with custom timeout"""
        mock_settings.enable_code_execution = True
        mock_settings.code_execution_allowed_imports = ["json", "math"]
        mock_get_sandbox.return_value = mock_sandbox

        result = execute_python.invoke({"code": "print('test')", "timeout": 60})

        # Should execute successfully
        mock_get_sandbox.assert_called_once()

    def test_tool_disabled_by_default(self):
        """Test that tool respects configuration flag"""
        # When execution is disabled, tool should return error
        with patch("mcp_server_langgraph.tools.code_execution_tools._is_execution_enabled") as mock_enabled:
            mock_enabled.return_value = False

            result = execute_python.invoke({"code": "print('test')"})

            assert "disabled" in result.lower() or "not enabled" in result.lower()


@pytest.mark.unit
class TestCodeExecutionToolIntegration:
    """Test integration with other components"""

    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_uses_configuration_settings(self, mock_get_sandbox):
        """Test that tool uses settings from config"""
        mock_sandbox = MagicMock()
        mock_sandbox.execute.return_value = ExecutionResult(
            success=True,
            stdout="{}",  # Actual JSON output
            stderr="",
            exit_code=0,
            execution_time=0.1,
        )
        mock_get_sandbox.return_value = mock_sandbox

        # Mock settings
        with patch("mcp_server_langgraph.tools.code_execution_tools.settings") as mock_settings:
            mock_settings.enable_code_execution = True
            mock_settings.code_execution_backend = "docker-engine"
            mock_settings.code_execution_allowed_imports = ["json", "math"]

            result = execute_python.invoke({"code": "import json\nprint(json.dumps({}))"})

            # Should see the output and success message
            assert "{}" in result or "success" in result.lower()

    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_backend_selection_docker(self, mock_get_sandbox):
        """Test Docker backend selection"""
        mock_sandbox = MagicMock()
        mock_sandbox.execute.return_value = ExecutionResult(
            success=True, stdout="test", stderr="", exit_code=0, execution_time=0.1
        )
        mock_get_sandbox.return_value = mock_sandbox

        with patch("mcp_server_langgraph.tools.code_execution_tools.settings") as mock_settings:
            mock_settings.enable_code_execution = True
            mock_settings.code_execution_backend = "docker-engine"

            result = execute_python.invoke({"code": "print('test')"})

            # Should use Docker sandbox
            mock_get_sandbox.assert_called_once()

    @patch("mcp_server_langgraph.tools.code_execution_tools._get_sandbox")
    def test_backend_selection_kubernetes(self, mock_get_sandbox):
        """Test Kubernetes backend selection"""
        mock_sandbox = MagicMock()
        mock_sandbox.execute.return_value = ExecutionResult(
            success=True, stdout="test", stderr="", exit_code=0, execution_time=0.1
        )
        mock_get_sandbox.return_value = mock_sandbox

        with patch("mcp_server_langgraph.tools.code_execution_tools.settings") as mock_settings:
            mock_settings.enable_code_execution = True
            mock_settings.code_execution_backend = "kubernetes"

            result = execute_python.invoke({"code": "print('test')"})

            # Should use Kubernetes sandbox
            mock_get_sandbox.assert_called_once()
