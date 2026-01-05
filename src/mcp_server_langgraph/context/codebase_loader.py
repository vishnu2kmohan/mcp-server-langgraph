"""CodebaseProgressiveLoader for progressive codebase context loading.

Provides progressive loading of codebase context:
- Pattern-based file discovery
- Relevance scoring based on query
- Token-aware truncation to fit within limits
- Language detection for files

This enables efficient context management for code-related tasks.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodebaseFile:
    """A file from the codebase.

    Attributes:
        path: Path to the file
        content: Text content of the file
        language: Detected programming language
        relevance_score: Optional relevance score (0-1) based on query
    """

    path: Path
    content: str
    language: str
    relevance_score: float | None = None


@dataclass
class LoadedCodebase:
    """Result of progressive codebase loading.

    Attributes:
        files: List of codebase files
        total_tokens: Estimated total tokens in the context
        was_truncated: Whether files were truncated due to limits
        summary: Optional summary of the codebase
    """

    files: list[CodebaseFile]
    total_tokens: int
    was_truncated: bool
    summary: str | None = None


class CodebaseProgressiveLoader:
    """Progressively loads codebase context within token limits.

    Implements file discovery and relevance-based loading that:
    - Discovers files matching patterns
    - Scores files by relevance to a query
    - Truncates when over token/file limits
    - Detects programming languages

    Attributes:
        root_path: Root directory to search from
        max_files: Maximum number of files to load
        max_tokens: Maximum tokens allowed for the context
        patterns: File patterns to include
        exclude_patterns: File patterns to exclude
    """

    DEFAULT_MAX_FILES = 20
    DEFAULT_MAX_TOKENS = 8000
    CHARS_PER_TOKEN_ESTIMATE = 4  # Rough estimate: 4 chars per token

    DEFAULT_PATTERNS = [
        "**/*.py",
        "**/*.ts",
        "**/*.tsx",
        "**/*.js",
        "**/*.jsx",
        "**/*.go",
        "**/*.rs",
        "**/*.java",
        "**/*.cpp",
        "**/*.c",
        "**/*.h",
        "**/*.hpp",
    ]

    DEFAULT_EXCLUDE_PATTERNS = [
        "**/node_modules/**",
        "**/.git/**",
        "**/venv/**",
        "**/.venv/**",
        "**/dist/**",
        "**/build/**",
        "**/__pycache__/**",
        "**/*.pyc",
        "**/target/**",
    ]

    LANGUAGE_MAP = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".cs": "csharp",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
    }

    def __init__(
        self,
        root_path: Path | None = None,
        max_files: int | None = None,
        max_tokens: int | None = None,
        patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Initialize the CodebaseProgressiveLoader.

        Args:
            root_path: Root directory to search from (default: current directory)
            max_files: Maximum files to load (default: 20)
            max_tokens: Maximum tokens allowed (default: 8000)
            patterns: File patterns to include (default: common source files)
            exclude_patterns: File patterns to exclude
        """
        self._root_path = root_path or Path.cwd()
        self._max_files = max_files if max_files is not None else self.DEFAULT_MAX_FILES
        self._max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        self._patterns = patterns  # None means use defaults
        self._exclude_patterns = exclude_patterns if exclude_patterns is not None else self.DEFAULT_EXCLUDE_PATTERNS

    @property
    def root_path(self) -> Path:
        """Get the root path."""
        return self._root_path

    @property
    def max_files(self) -> int:
        """Get the maximum files limit."""
        return self._max_files

    @property
    def max_tokens(self) -> int:
        """Get the maximum tokens limit."""
        return self._max_tokens

    @property
    def default_patterns(self) -> list[str]:
        """Get the default file patterns."""
        return self.DEFAULT_PATTERNS.copy()

    @property
    def patterns(self) -> list[str]:
        """Get the configured file patterns."""
        return self._patterns or self.default_patterns

    @property
    def exclude_patterns(self) -> list[str]:
        """Get the exclude patterns."""
        return self._exclude_patterns

    def _detect_language(self, path: Path) -> str:
        """Detect the programming language from file extension.

        Args:
            path: Path to the file

        Returns:
            Language identifier string
        """
        suffix = path.suffix.lower()
        return self.LANGUAGE_MAP.get(suffix, "unknown")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: The text to estimate tokens for

        Returns:
            Estimated token count
        """
        return max(1, len(text) // self.CHARS_PER_TOKEN_ESTIMATE)

    def _discover_files(self) -> list[CodebaseFile]:
        """Discover files matching patterns in root_path.

        Returns:
            List of CodebaseFile objects
        """
        files: list[CodebaseFile] = []

        for pattern in self.patterns:
            for file_path in self._root_path.glob(pattern):
                if not file_path.is_file():
                    continue

                # Check exclude patterns
                relative = str(file_path.relative_to(self._root_path))
                excluded = False
                for exclude in self._exclude_patterns:
                    # Simple matching - check if any exclude pattern matches
                    exclude_pattern = exclude.replace("**", "*").replace("/*", "")
                    if exclude_pattern.strip("*") in relative:
                        excluded = True
                        break

                if excluded:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    language = self._detect_language(file_path)
                    files.append(
                        CodebaseFile(
                            path=file_path,
                            content=content,
                            language=language,
                        )
                    )
                except (OSError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue

        return files

    def _score_relevance(self, file: CodebaseFile, query: str) -> float:
        """Score a file's relevance to a query.

        Uses simple keyword matching. In production, this could use
        embeddings for semantic similarity.

        Args:
            file: The file to score
            query: The query to match against

        Returns:
            Relevance score (0-1)
        """
        if not query:
            return 0.5  # Neutral score when no query

        query_lower = query.lower()
        query_words = set(query_lower.split())

        score = 0.0

        # Check filename match
        filename_lower = file.path.name.lower()
        for word in query_words:
            if word in filename_lower:
                score += 0.3

        # Check path match
        path_lower = str(file.path).lower()
        for word in query_words:
            if word in path_lower:
                score += 0.2

        # Check content match
        content_lower = file.content.lower()
        for word in query_words:
            if word in content_lower:
                score += 0.1
                # Bonus for multiple occurrences
                count = content_lower.count(word)
                if count > 1:
                    score += min(0.1, count * 0.02)

        return min(1.0, score)

    async def load(
        self,
        query: str = "",
    ) -> LoadedCodebase:
        """Load codebase context progressively.

        Loads files matching patterns, scores by relevance,
        and truncates based on limits.

        Args:
            query: Query to use for relevance scoring

        Returns:
            LoadedCodebase with the loaded files and metadata
        """
        # Discover files
        discovered = self._discover_files()

        if not discovered:
            return LoadedCodebase(
                files=[],
                total_tokens=0,
                was_truncated=False,
            )

        # Score each file for relevance
        scored_files: list[CodebaseFile] = []
        for file in discovered:
            score = self._score_relevance(file, query)
            scored_file = CodebaseFile(
                path=file.path,
                content=file.content,
                language=file.language,
                relevance_score=score,
            )
            scored_files.append(scored_file)

        # Sort by relevance (highest first)
        scored_files.sort(
            key=lambda f: f.relevance_score if f.relevance_score is not None else 0,
            reverse=True,
        )

        # Apply limits
        selected_files: list[CodebaseFile] = []
        total_tokens = 0
        was_truncated = False

        for file in scored_files:
            # Check max files limit
            if len(selected_files) >= self._max_files:
                was_truncated = True
                break

            # Check token limit
            file_tokens = self._estimate_tokens(file.content)
            # Add overhead for path and metadata
            file_tokens += self._estimate_tokens(str(file.path)) + 10

            if total_tokens + file_tokens > self._max_tokens:
                was_truncated = True
                break

            selected_files.append(file)
            total_tokens += file_tokens

        return LoadedCodebase(
            files=selected_files,
            total_tokens=total_tokens,
            was_truncated=was_truncated,
        )
