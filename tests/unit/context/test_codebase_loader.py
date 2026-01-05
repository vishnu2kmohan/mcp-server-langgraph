"""Tests for CodebaseProgressiveLoader.

TDD: These tests define the contract for progressive loading
of codebase context using file pattern matching and relevance scoring.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="codebase_loader_basic")
class TestCodebaseProgressiveLoaderBasic:
    """Tests for CodebaseProgressiveLoader basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_codebase_loader_exists(self) -> None:
        """Test CodebaseProgressiveLoader class exists."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        assert CodebaseProgressiveLoader is not None

    def test_codebase_loader_has_load_method(self) -> None:
        """Test CodebaseProgressiveLoader has load method."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert hasattr(loader, "load")

    def test_codebase_loader_accepts_root_path(self) -> None:
        """Test CodebaseProgressiveLoader accepts root_path parameter."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp/test"))

        assert loader.root_path == Path("/tmp/test")

    def test_codebase_loader_accepts_max_files(self) -> None:
        """Test CodebaseProgressiveLoader accepts max_files parameter."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(max_files=50)

        assert loader.max_files == 50

    def test_codebase_loader_accepts_max_tokens(self) -> None:
        """Test CodebaseProgressiveLoader accepts max_tokens parameter."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(max_tokens=4000)

        assert loader.max_tokens == 4000


@pytest.mark.unit
@pytest.mark.xdist_group(name="codebase_file")
class TestCodebaseFile:
    """Tests for CodebaseFile dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_codebase_file_exists(self) -> None:
        """Test CodebaseFile dataclass exists."""
        from mcp_server_langgraph.context.codebase_loader import CodebaseFile

        assert CodebaseFile is not None

    def test_codebase_file_has_path(self) -> None:
        """Test CodebaseFile has path field."""
        from mcp_server_langgraph.context.codebase_loader import CodebaseFile

        file = CodebaseFile(
            path=Path("/test/file.py"),
            content="# test",
            language="python",
        )

        assert file.path == Path("/test/file.py")

    def test_codebase_file_has_content(self) -> None:
        """Test CodebaseFile has content field."""
        from mcp_server_langgraph.context.codebase_loader import CodebaseFile

        file = CodebaseFile(
            path=Path("/test/file.py"),
            content="def hello(): pass",
            language="python",
        )

        assert file.content == "def hello(): pass"

    def test_codebase_file_has_language(self) -> None:
        """Test CodebaseFile has language field."""
        from mcp_server_langgraph.context.codebase_loader import CodebaseFile

        file = CodebaseFile(
            path=Path("/test/file.py"),
            content="# test",
            language="python",
        )

        assert file.language == "python"

    def test_codebase_file_has_optional_relevance_score(self) -> None:
        """Test CodebaseFile has optional relevance_score field."""
        from mcp_server_langgraph.context.codebase_loader import CodebaseFile

        file = CodebaseFile(
            path=Path("/test/file.py"),
            content="# test",
            language="python",
            relevance_score=0.85,
        )

        assert file.relevance_score == 0.85


@pytest.mark.unit
@pytest.mark.xdist_group(name="loaded_codebase")
class TestLoadedCodebase:
    """Tests for LoadedCodebase dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loaded_codebase_exists(self) -> None:
        """Test LoadedCodebase dataclass exists."""
        from mcp_server_langgraph.context.codebase_loader import LoadedCodebase

        assert LoadedCodebase is not None

    def test_loaded_codebase_has_files(self) -> None:
        """Test LoadedCodebase has files field."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseFile,
            LoadedCodebase,
        )

        file = CodebaseFile(
            path=Path("/test/file.py"),
            content="# test",
            language="python",
        )
        context = LoadedCodebase(
            files=[file],
            total_tokens=100,
            was_truncated=False,
        )

        assert len(context.files) == 1
        assert context.files[0] is file

    def test_loaded_codebase_has_total_tokens(self) -> None:
        """Test LoadedCodebase has total_tokens field."""
        from mcp_server_langgraph.context.codebase_loader import LoadedCodebase

        context = LoadedCodebase(
            files=[],
            total_tokens=500,
            was_truncated=False,
        )

        assert context.total_tokens == 500

    def test_loaded_codebase_has_was_truncated(self) -> None:
        """Test LoadedCodebase has was_truncated field."""
        from mcp_server_langgraph.context.codebase_loader import LoadedCodebase

        context = LoadedCodebase(
            files=[],
            total_tokens=500,
            was_truncated=True,
        )

        assert context.was_truncated is True

    def test_loaded_codebase_has_optional_summary(self) -> None:
        """Test LoadedCodebase has optional summary field."""
        from mcp_server_langgraph.context.codebase_loader import LoadedCodebase

        context = LoadedCodebase(
            files=[],
            total_tokens=500,
            was_truncated=True,
            summary="This codebase contains the agent implementation.",
        )

        assert context.summary == "This codebase contains the agent implementation."


@pytest.mark.unit
@pytest.mark.xdist_group(name="codebase_loader_patterns")
class TestCodebaseProgressiveLoaderPatterns:
    """Tests for CodebaseProgressiveLoader pattern matching."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_patterns_include_python(self) -> None:
        """Test default patterns include Python files."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert "**/*.py" in loader.default_patterns

    def test_default_patterns_include_typescript(self) -> None:
        """Test default patterns include TypeScript files."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert "**/*.ts" in loader.default_patterns or "**/*.tsx" in loader.default_patterns

    def test_exclude_patterns_default(self) -> None:
        """Test exclude patterns have sensible defaults."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        # Should exclude common non-source directories
        assert any("node_modules" in p for p in loader.exclude_patterns)
        assert any(".git" in p for p in loader.exclude_patterns)

    def test_custom_patterns_override_default(self) -> None:
        """Test custom patterns can be provided."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        custom = ["**/*.rs", "**/*.go"]
        loader = CodebaseProgressiveLoader(patterns=custom)

        assert loader.patterns == custom


@pytest.mark.unit
@pytest.mark.xdist_group(name="codebase_loader_load")
class TestCodebaseProgressiveLoaderLoad:
    """Tests for CodebaseProgressiveLoader.load() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_returns_loaded_codebase(self) -> None:
        """Test load() returns LoadedCodebase."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
            LoadedCodebase,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp"))

        # Mock filesystem operations
        with patch.object(loader, "_discover_files", return_value=[]):
            result = await loader.load(query="Find auth files")

        assert isinstance(result, LoadedCodebase)

    @pytest.mark.asyncio
    async def test_load_uses_query_for_relevance(self) -> None:
        """Test load() uses query to score file relevance."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseFile,
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp"))

        test_files = [
            CodebaseFile(
                path=Path("/tmp/auth.py"),
                content="def authenticate(): pass",
                language="python",
            ),
            CodebaseFile(
                path=Path("/tmp/utils.py"),
                content="def format_string(): pass",
                language="python",
            ),
        ]

        with patch.object(loader, "_discover_files", return_value=test_files):
            with patch.object(loader, "_score_relevance", side_effect=[0.9, 0.2]) as mock_score:
                await loader.load(query="authentication")

        # Should have called score_relevance for each file
        assert mock_score.call_count == 2

    @pytest.mark.asyncio
    async def test_load_respects_max_files(self) -> None:
        """Test load() respects max_files limit."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseFile,
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp"), max_files=2)

        # Create many test files
        test_files = [
            CodebaseFile(
                path=Path(f"/tmp/file{i}.py"),
                content=f"# file {i}",
                language="python",
            )
            for i in range(10)
        ]

        with patch.object(loader, "_discover_files", return_value=test_files):
            with patch.object(loader, "_score_relevance", return_value=0.5):
                result = await loader.load(query="test")

        assert len(result.files) <= 2

    @pytest.mark.asyncio
    async def test_load_respects_max_tokens(self) -> None:
        """Test load() respects max_tokens limit."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseFile,
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp"), max_tokens=100)

        # Create files with known content size
        test_files = [
            CodebaseFile(
                path=Path(f"/tmp/file{i}.py"),
                content="x" * 200,  # Each file is 200 chars
                language="python",
            )
            for i in range(5)
        ]

        with patch.object(loader, "_discover_files", return_value=test_files):
            with patch.object(loader, "_score_relevance", return_value=0.5):
                result = await loader.load(query="test")

        # Should truncate based on token limit
        assert result.was_truncated is True

    @pytest.mark.asyncio
    async def test_load_sorts_by_relevance(self) -> None:
        """Test load() returns files sorted by relevance (highest first)."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseFile,
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader(root_path=Path("/tmp"), max_files=10)

        test_files = [
            CodebaseFile(
                path=Path("/tmp/low.py"),
                content="# low relevance",
                language="python",
            ),
            CodebaseFile(
                path=Path("/tmp/high.py"),
                content="# high relevance",
                language="python",
            ),
            CodebaseFile(
                path=Path("/tmp/medium.py"),
                content="# medium relevance",
                language="python",
            ),
        ]

        def mock_score(file: CodebaseFile, query: str) -> float:
            if "high" in file.path.name:
                return 0.9
            elif "medium" in file.path.name:
                return 0.5
            return 0.1

        with patch.object(loader, "_discover_files", return_value=test_files):
            with patch.object(loader, "_score_relevance", side_effect=mock_score):
                result = await loader.load(query="test")

        # Files should be sorted by relevance (high first)
        if len(result.files) >= 2:
            assert result.files[0].relevance_score >= result.files[1].relevance_score


@pytest.mark.unit
@pytest.mark.xdist_group(name="codebase_loader_language")
class TestCodebaseProgressiveLoaderLanguage:
    """Tests for language detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detect_language_python(self) -> None:
        """Test language detection for Python files."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert loader._detect_language(Path("test.py")) == "python"

    def test_detect_language_typescript(self) -> None:
        """Test language detection for TypeScript files."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert loader._detect_language(Path("test.ts")) == "typescript"
        assert loader._detect_language(Path("test.tsx")) == "typescript"

    def test_detect_language_javascript(self) -> None:
        """Test language detection for JavaScript files."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert loader._detect_language(Path("test.js")) == "javascript"
        assert loader._detect_language(Path("test.jsx")) == "javascript"

    def test_detect_language_unknown(self) -> None:
        """Test language detection returns unknown for unrecognized extensions."""
        from mcp_server_langgraph.context.codebase_loader import (
            CodebaseProgressiveLoader,
        )

        loader = CodebaseProgressiveLoader()

        assert loader._detect_language(Path("test.xyz")) == "unknown"
