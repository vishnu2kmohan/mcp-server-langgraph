"""
Test suite for scripts/validators/codeblock_validator_v2.py

Tests the improved code block validator to ensure it:
1. Correctly detects programming languages with high confidence
2. Distinguishes comment-only blocks from code with comments
3. Identifies environment variables, tree structures, and output
4. Uses proper state machine for fence tracking
5. Provides accurate validation and fixing capabilities
"""

import gc
import importlib

# Import the module under test
import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import scripts.validators.codeblock_validator_v2

importlib.reload(scripts.validators.codeblock_validator_v2)  # Force reload to get latest changes
from scripts.validators.codeblock_validator_v2 import BlockType, CodeBlock, CodeBlockValidator, SmartLanguageDetector

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorBash:
    """Test suite for SmartLanguageDetector bash detection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Bash Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_bash_with_shell_commands(self):
        """Test detecting bash from common shell commands."""
        content = dedent(
            """
            git clone https://github.com/user/repo.git
            cd repo
            npm install
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_detect_bash_with_command_options(self):
        """Test detecting bash from commands with flags."""
        content = dedent(
            """
            docker run --rm -p 8080:8080 myimage
            kubectl apply -f deployment.yaml
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_detect_bash_with_shell_operators(self):
        """Test detecting bash from shell operators."""
        content = dedent(
            """
            npm install && npm run build
            docker build -t myimage . || exit 1
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_detect_bash_with_shebang(self):
        """Test detecting bash from shebang."""
        content = dedent(
            """
            #!/bin/bash
            echo "Hello, world!"
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_detect_bash_script_execution(self):
        """Test detecting bash script execution like the false positive example."""
        content = "./deployments/service-mesh/anthos/setup-anthos-service-mesh.sh PROJECT_ID"

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_bash_with_pipe_operators(self):
        """Test detecting bash with pipes."""
        content = dedent(
            """
            cat file.txt | grep pattern | wc -l
            docker ps | grep running
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.BASH_SCRIPT


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorPython:
    """Test suite for SmartLanguageDetector Python detection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Python Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_python_with_imports(self):
        """Test detecting Python from import statements."""
        content = dedent(
            """
            from langgraph.graph import StateGraph
            import asyncio
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_detect_python_with_function_definition(self):
        """Test detecting Python from function definition."""
        content = dedent(
            """
            def hello_world():
                print("Hello, world!")
                return True
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_detect_python_with_class_definition(self):
        """Test detecting Python from class definition."""
        content = dedent(
            """
            class MyClass:
                def __init__(self):
                    self.value = 42
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_detect_python_with_async_await(self):
        """Test detecting Python from async/await syntax."""
        content = dedent(
            """
            import asyncio

            try:
                result = await asyncio.wait_for(
                    client.call_tool(name, arguments),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print("Tool execution timed out")
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_detect_python_with_comments_and_code(self):
        """Test that code with comments is still detected as Python, not comment-only."""
        content = dedent(
            """
            from langgraph.graph import StateGraph

            graph = StateGraph(AgentState)

            # Add agent nodes
            graph.add_node("research", research_agent)
            graph.add_node("write", write_agent)

            # Define flow
            graph.add_edge("research", "write")
            graph.set_entry_point("research")

            # Compile with persistence
            app = graph.compile(checkpointer=checkpointer)
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # This is the key test - should detect as Python, not comment-only
        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_detect_python_with_decorators(self):
        """Test detecting Python from decorators."""
        content = dedent(
            """
            @pytest.fixture
            def test_data():
                return {"key": "value"}
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PYTHON_CODE


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorCommentOnly:
    """Test suite for detecting comment-only blocks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Comment-Only Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_comment_only_bash_style(self):
        """Test detecting comment-only blocks with bash-style comments."""
        content = dedent(
            """
            # This is a comment
            # Another comment
            # More comments
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.COMMENT_ONLY

    @pytest.mark.asyncio
    async def test_detect_comment_only_with_list_items(self):
        """Test detecting markdown lists in comments as comment-only."""
        content = dedent(
            """
            ## Required
            - Python 3.12+
            - Docker & Docker Compose
            - Git

            ## Recommended
            - uv (Python package manager)
            - Pre-commit
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.COMMENT_ONLY

    @pytest.mark.asyncio
    async def test_not_comment_only_with_actual_code(self):
        """Test that blocks with comments AND code are not comment-only."""
        content = dedent(
            """
            # Install dependencies
            npm install

            # Start server
            npm start
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as bash, not comment-only
        assert detected == BlockType.BASH_SCRIPT


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorEnvVars:
    """Test suite for detecting environment variable blocks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Environment Variables Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_env_vars_only(self):
        """Test detecting environment variable only blocks."""
        content = dedent(
            """
            GOOGLE_API_KEY=your-api-key-here
            OPENFGA_STORE_ID=01HXXXXXXXXXXXXXXXXXX
            OPENFGA_MODEL_ID=01HYYYYYYYYYYYYYYYY
            JWT_SECRET_KEY=your-secret-key
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.ENV_VARS

    @pytest.mark.asyncio
    async def test_env_vars_with_comments(self):
        """Test env vars with comment lines."""
        content = dedent(
            """
            # Get free API key from https://aistudio.google.com/apikey
            GOOGLE_API_KEY=your-api-key-here

            # From previous step
            OPENFGA_STORE_ID=01HXXXXXXXXXXXXXXXXXX
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should still be env vars (comments are allowed)
        assert detected == BlockType.ENV_VARS

    @pytest.mark.asyncio
    async def test_env_vars_mixed_with_export_is_bash(self):
        """Test that env vars with export statements are bash, not env."""
        content = dedent(
            """
            export DATABASE_URL=postgresql://localhost/db
            export API_KEY=secret
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should be bash because of export
        assert detected == BlockType.BASH_SCRIPT


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorTreeStructure:
    """Test suite for detecting directory tree structures."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Tree Structure Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_tree_structure(self):
        """Test detecting directory tree output."""
        content = dedent(
            """
            tests/
            ├── unit/
            │   ├── test_auth.py
            │   ├── test_agent.py
            │   └── test_llm.py
            │
            ├── integration/
            │   ├── test_api.py
            │   └── test_database.py
            └── conftest.py
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.TREE_STRUCTURE


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorCommandOutput:
    """Test suite for detecting command output."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Command Output Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_error_output(self):
        """Test detecting error messages as output."""
        content = dedent(
            """
            Error: Module not found
            Traceback (most recent call last):
              File "app.py", line 10, in <module>
                import missing_module
            ModuleNotFoundError: No module named 'missing_module'
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.COMMAND_OUTPUT

    @pytest.mark.asyncio
    async def test_detect_http_response(self):
        """Test detecting HTTP responses as output."""
        content = dedent(
            """
            HTTP/1.1 200 OK
            Content-Type: application/json
            Content-Length: 42

            {"status": "success"}
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.COMMAND_OUTPUT

    @pytest.mark.asyncio
    async def test_detect_log_output(self):
        """Test detecting log entries as output."""
        content = dedent(
            """
            2025-01-15 10:30:45 INFO Starting application
            2025-01-15 10:30:46 DEBUG Loading configuration
            2025-01-15 10:30:47 INFO Server listening on port 8080
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.COMMAND_OUTPUT


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorDataFormats:
    """Test suite for detecting data formats (JSON, YAML, XML)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # JSON Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_json_object(self):
        """Test detecting JSON objects."""
        content = dedent(
            """
            {
              "id": "alice",
              "username": "alice",
              "email": "alice@example.com",
              "roles": ["user", "admin"]
            }
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.JSON_DATA

    @pytest.mark.asyncio
    async def test_detect_json_array(self):
        """Test detecting JSON arrays."""
        content = dedent(
            """
            [
              {"id": 1, "name": "Alice"},
              {"id": 2, "name": "Bob"}
            ]
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.JSON_DATA

    # ========================================================================
    # YAML Detection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_yaml_kubernetes(self):
        """Test detecting Kubernetes YAML."""
        content = dedent(
            """
            apiVersion: v1
            kind: Service
            metadata:
              name: my-service
            spec:
              selector:
                app: my-app
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.YAML_CONFIG

    @pytest.mark.asyncio
    async def test_detect_yaml_config(self):
        """Test detecting general YAML config."""
        content = dedent(
            """
            database:
              host: localhost
              port: 5432
            logging:
              level: DEBUG
              format: json
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # May be YAML or plain text depending on indicators
        assert detected in [BlockType.YAML_CONFIG, BlockType.PLAIN_TEXT]

    # ========================================================================
    # Other Formats
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_dockerfile(self):
        """Test detecting Dockerfile syntax."""
        content = dedent(
            """
            FROM python:3.11-slim
            WORKDIR /app
            COPY requirements.txt .
            RUN pip install -r requirements.txt
            CMD ["python", "app.py"]
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.DOCKERFILE

    @pytest.mark.asyncio
    async def test_detect_sql(self):
        """Test detecting SQL queries."""
        content = dedent(
            """
            SELECT u.username, u.email, COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.user_id
            WHERE u.active = true
            GROUP BY u.id
            ORDER BY post_count DESC;
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.SQL_QUERY


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorEmptyAndPlain:
    """Test suite for empty blocks and plain text."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Empty and Plain Text Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_detect_empty_block(self):
        """Test detecting empty blocks."""
        content = ""

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.EMPTY

    @pytest.mark.asyncio
    async def test_detect_whitespace_only_as_empty(self):
        """Test that whitespace-only blocks are empty."""
        content = "   \n  \n   "

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.EMPTY

    @pytest.mark.asyncio
    async def test_detect_plain_text(self):
        """Test detecting plain text prose."""
        content = dedent(
            """
            This is just plain text.
            No special formatting or code.
            Just regular prose.
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        assert detected == BlockType.PLAIN_TEXT


@pytest.mark.xdist_group(name="scripts_validation")
class TestCodeBlockValidatorStateMachine:
    """Test suite for CodeBlockValidator state machine."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # State Machine Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_parse_code_blocks_correctly(self):
        """Test that code blocks are parsed correctly with state machine."""
        content = dedent(
            """
            # Documentation

            ```python
            def hello():
                pass
            ```

            More text.

            ```bash
            echo "test"
            ```
        """
        ).strip()

        validator = CodeBlockValidator()
        blocks = validator._parse_code_blocks(content)

        assert len(blocks) == 2
        assert blocks[0].language_tag == "python"
        assert blocks[0].has_language_tag is True
        assert blocks[1].language_tag == "bash"
        assert blocks[1].has_language_tag is True

    @pytest.mark.asyncio
    async def test_parse_blocks_without_language_tags(self):
        """Test parsing blocks without language tags."""
        content = dedent(
            """
            ```
            some content
            ```
        """
        ).strip()

        validator = CodeBlockValidator()
        blocks = validator._parse_code_blocks(content)

        assert len(blocks) == 1
        assert blocks[0].has_language_tag is False
        assert blocks[0].language_tag is None

    @pytest.mark.asyncio
    async def test_opening_fence_detection(self):
        """Test that opening fences are correctly identified."""
        content = dedent(
            """
            ```python
            code
            ```
        """
        ).strip()

        validator = CodeBlockValidator()
        blocks = validator._parse_code_blocks(content)

        assert blocks[0].start_line == 1
        assert blocks[0].opening_fence == "```python"

    @pytest.mark.asyncio
    async def test_closing_fence_never_has_tag(self):
        """Test that closing fence language is not stored (from opening fence)."""
        content = dedent(
            """
            ```python
            code
            ```
        """
        ).strip()

        validator = CodeBlockValidator()
        blocks = validator._parse_code_blocks(content)

        # Language tag comes from opening fence, closing fence should be bare
        assert blocks[0].language_tag == "python"
        assert blocks[0].closing_fence == "```"


@pytest.mark.xdist_group(name="scripts_validation")
class TestCodeBlockValidatorCompatibleTags:
    """Test suite for compatible tag validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Compatible Tags Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_env_vars_accept_bash_tag(self):
        """Test that env var blocks can be tagged as bash."""
        block = CodeBlock(
            start_line=1,
            end_line=3,
            opening_fence="```bash",
            closing_fence="```",
            content="API_KEY=secret\nDB_URL=postgres://localhost",
            has_language_tag=True,
            language_tag="bash",
            detected_type=BlockType.ENV_VARS,
        )

        validator = CodeBlockValidator()
        issue = validator._validate_block(block)

        # Should be valid (bash is compatible with env vars)
        assert issue is None

    @pytest.mark.asyncio
    async def test_env_vars_accept_env_tag(self):
        """Test that env var blocks can be tagged as env."""
        block = CodeBlock(
            start_line=1,
            end_line=3,
            opening_fence="```env",
            closing_fence="```",
            content="API_KEY=secret\nDB_URL=postgres://localhost",
            has_language_tag=True,
            language_tag="env",
            detected_type=BlockType.ENV_VARS,
        )

        validator = CodeBlockValidator()
        issue = validator._validate_block(block)

        # Should be valid
        assert issue is None

    @pytest.mark.asyncio
    async def test_comment_only_accepts_text_or_bash(self):
        """Test that comment-only blocks accept text or bash tags."""
        for tag in ["text", "bash"]:
            block = CodeBlock(
                start_line=1,
                end_line=3,
                opening_fence=f"```{tag}",
                closing_fence="```",
                content="# Comment 1\n# Comment 2",
                has_language_tag=True,
                language_tag=tag,
                detected_type=BlockType.COMMENT_ONLY,
            )

            validator = CodeBlockValidator()
            issue = validator._validate_block(block)

            # Should be valid
            assert issue is None, f"Tag '{tag}' should be valid for comment-only blocks"


@pytest.mark.xdist_group(name="scripts_validation")
class TestCodeBlockValidatorIntegration:
    """Integration tests for CodeBlockValidator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Integration Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_file_with_no_issues(self, tmp_path):
        """Test validating a file with correctly tagged blocks."""
        test_file = tmp_path / "correct.md"
        test_file.write_text(
            dedent(
                """
            ```python
            def hello():
                print("world")
            ```

            ```bash
            echo "test"
            ```
        """
            ).strip()
        )

        validator = CodeBlockValidator(fix=False, dry_run=False)
        result = validator.validate_file(test_file)

        assert result is True  # Valid
        assert validator.stats["blocks_untagged"] == 0

    @pytest.mark.asyncio
    async def test_validate_file_with_untagged_block(self, tmp_path):
        """Test validating a file with untagged block."""
        test_file = tmp_path / "untagged.md"
        test_file.write_text(
            dedent(
                """
            ```
            git clone repo
            ```
        """
            ).strip()
        )

        validator = CodeBlockValidator(fix=False, dry_run=False)
        result = validator.validate_file(test_file)

        assert result is False  # Has issues
        assert validator.stats["blocks_untagged"] == 1

    @pytest.mark.asyncio
    async def test_fix_mode_dry_run(self, tmp_path):
        """Test fix mode with dry run."""
        test_file = tmp_path / "fix_test.md"
        original_content = dedent(
            """
            ```
            echo "test"
            ```
        """
        ).strip()
        test_file.write_text(original_content)

        validator = CodeBlockValidator(fix=True, dry_run=True)
        validator.validate_file(test_file)

        # File should not be modified in dry run
        assert test_file.read_text() == original_content

        # But stats should show what would be fixed
        assert validator.stats["blocks_fixed"] == 0  # Dry run doesn't count as fixed

    @pytest.mark.asyncio
    async def test_fix_mode_applies_changes(self, tmp_path):
        """Test fix mode actually modifies files."""
        test_file = tmp_path / "fix_test.md"
        test_file.write_text(
            dedent(
                """
            ```
            echo "test"
            ```
        """
            ).strip()
        )

        validator = CodeBlockValidator(fix=True, dry_run=False)
        validator.validate_file(test_file)

        # File should be modified
        fixed_content = test_file.read_text()
        assert "```bash" in fixed_content  # Language tag added
        assert validator.stats["blocks_fixed"] == 1


@pytest.mark.xdist_group(name="scripts_validation")
class TestCodeBlockValidatorRegressions:
    """Regression tests for known issues and false positives."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Regression Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_regression_bash_script_execution_not_flagged(self):
        """Regression: ./script.sh should be detected as bash, not text."""
        content = "./deployments/service-mesh/anthos/setup-anthos-service-mesh.sh PROJECT_ID"

        detected = SmartLanguageDetector.detect(content)

        # Should detect as bash
        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_regression_python_with_comments_not_flagged(self):
        """Regression: Python code with comments should not be flagged as 'non-code'."""
        content = dedent(
            """
            from langgraph.graph import StateGraph

            # Add agent nodes
            graph.add_node("research", research_agent)

            # Define flow
            graph.add_edge("research", "write")
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as Python, not comment-only
        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_regression_async_python_not_flagged(self):
        """Regression: Async Python code should be detected as Python."""
        content = dedent(
            """
            import asyncio

            try:
                result = await asyncio.wait_for(
                    client.call_tool(name, arguments),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print("Tool execution timed out")
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as Python
        assert detected == BlockType.PYTHON_CODE

    @pytest.mark.asyncio
    async def test_regression_shell_commands_with_multiple_lines(self):
        """Regression: Multiple shell commands should be bash."""
        content = dedent(
            """
            kubectl label namespace production istio-injection=enabled
            kubectl rollout restart deployment -n production
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as bash
        assert detected == BlockType.BASH_SCRIPT


@pytest.mark.xdist_group(name="scripts_validation")
class TestSmartLanguageDetectorEdgeCases:
    """Edge case regression tests for false positive patterns."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Heredoc Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_bash_with_python_heredoc_detected_as_bash(self):
        """Bash script with embedded Python heredoc should be detected as bash, not Python."""
        content = dedent(
            """
            # Decode JWT to inspect claims
            echo "YOUR_JWT_TOKEN" | base64 -d | jq .

            # Check token expiration
            python3 <<EOF
            import jwt
# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit
            token = "YOUR_JWT_TOKEN"
            decoded = jwt.decode(token, options={"verify_signature": False})
            print(f"Expires: {decoded.get('exp')}")
            print(f"Issued: {decoded.get('iat')}")
            EOF
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as bash (heredoc pattern), not Python
        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_bash_with_cat_heredoc_detected_as_bash(self):
        """Bash script using cat heredoc should be detected as bash."""
        content = dedent(
            """
            cat <<EOF > config.yaml
            database:
              host: localhost
              port: 5432
            EOF
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should detect as bash
        assert detected == BlockType.BASH_SCRIPT

    @pytest.mark.asyncio
    async def test_bash_with_heredoc_eof_variations(self):
        """Test various heredoc EOF patterns."""
        patterns = [
            "python3 <<EOF\nimport sys\nEOF",
            "python3 <<'EOF'\nimport sys\nEOF",
            "python3 <<-EOF\nimport sys\nEOF",
            "cat <<EOF\ndata\nEOF",
        ]

        for content in patterns:
            detected = SmartLanguageDetector.detect(content)
            assert detected == BlockType.BASH_SCRIPT, f"Failed for: {content}"

    # ========================================================================
    # YAML with Inline Comments
    # ========================================================================

    @pytest.mark.asyncio
    async def test_yaml_with_inline_comments_detected_as_yaml(self):
        """YAML with inline comments should be detected as YAML, not comment-only."""
        content = dedent(
            """
            ---
            title: "Page Title"
            sidebarTitle: "Short Title"  # optional, for sidebar
            description: "SEO-friendly description"
            icon: "lucide-icon-name"  # See ICON_GUIDE.md
            ---
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should NOT be detected as comment-only
        assert detected != BlockType.COMMENT_ONLY

    @pytest.mark.asyncio
    async def test_config_with_inline_comments_not_comment_only(self):
        """Config files with inline comments should not be flagged as comment-only."""
        # YAML example
        yaml_content = dedent(
            """
            apiVersion: v1  # Kubernetes API version
            kind: Service  # Resource type
            metadata:
              name: my-service  # Service name
        """
        ).strip()

        detected = SmartLanguageDetector.detect(yaml_content)
        assert detected != BlockType.COMMENT_ONLY

        # HCL example
        hcl_content = dedent(
            """
            resource "google_project" "project" {
              name       = "my-project"  # Project name
              project_id = "my-id"       # Must be globally unique
            }
        """
        ).strip()

        detected = SmartLanguageDetector.detect(hcl_content)
        assert detected != BlockType.COMMENT_ONLY

    @pytest.mark.asyncio
    async def test_pure_comments_still_detected_as_comment_only(self):
        """Pure comment blocks should still be detected as comment-only."""
        content = dedent(
            """
            # This is just a comment
            # Another comment
            # No actual code here
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should be comment-only
        assert detected == BlockType.COMMENT_ONLY

    # ========================================================================
    # Mixed Content Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_mermaid_with_comments_detected_as_mermaid(self):
        """Mermaid diagrams with comment syntax should not be flagged as comment-only."""
        content = dedent(
            """
            graph LR
                A[Start] --> B[Process]
                %% This is a mermaid comment
                B --> C[End]
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should NOT be comment-only (though we don't have MERMAID type, so plain text is ok)
        assert detected != BlockType.COMMENT_ONLY

    @pytest.mark.asyncio
    async def test_http_requests_with_comments_not_comment_only(self):
        """HTTP request examples with comments should not be comment-only."""
        content = dedent(
            """
            GET /api/users HTTP/1.1
            Host: api.example.com
            # Authorization header
            Authorization: Bearer token123
        """
        ).strip()

        detected = SmartLanguageDetector.detect(content)

        # Should NOT be comment-only
        assert detected != BlockType.COMMENT_ONLY
