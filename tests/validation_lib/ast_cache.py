"""
Shared caching and validation utilities for meta-tests.

This module provides:
1. Cached file reading and AST parsing for tests that need structural analysis
2. Fast regex-based checks for simple pattern detection (1000x faster than AST)

Performance Strategy:
- Use regex for presence detection ("does file contain X?") - 8ms for entire suite
- Use AST only for structural analysis ("is X used correctly?") - 10s for entire suite
- Cache both to avoid redundant I/O across multiple test methods

Usage:
    from tests.validation_lib.ast_cache import (
        cached_read_file,      # Cached file reading
        cached_parse_ast,      # Cached AST parsing (only when needed)
        has_pattern,           # Fast regex check
        has_xdist_group,       # Check for @pytest.mark.xdist_group
        has_pytest_marker,     # Check for any pytest marker
        has_fixture_decorator, # Check for @pytest.fixture
    )

Cache Management:
    - Cache is module-level and persists for the pytest session
    - Cache size is limited to 500 entries (sufficient for test suite)
    - Cache is automatically invalidated when pytest restarts

Note: This module addresses CI timeout issues identified in:
    - tests/meta/test_codex_regression_prevention.py (was timing out at 60s)
    - tests/meta/test_suite_validation.py (multiple full-suite scans)
    - tests/meta/test_pytest_xdist_enforcement.py (multiple full-suite scans)
"""

import ast
import re
from functools import lru_cache
from pathlib import Path

# =============================================================================
# CACHED FILE READING
# =============================================================================


@lru_cache(maxsize=500)
def cached_read_file(filepath: str) -> str:
    """
    Read file contents with caching.

    Args:
        filepath: Absolute or relative path to file (as string for hashability)

    Returns:
        File contents as string

    Raises:
        OSError: If file cannot be read
    """
    return Path(filepath).read_text()


# =============================================================================
# CACHED AST PARSING (use only when structural analysis is needed)
# =============================================================================


@lru_cache(maxsize=500)
def cached_parse_ast(filepath: str) -> tuple:
    """
    Parse Python file to AST with caching.

    USE SPARINGLY: Only for structural analysis like:
    - Checking function arguments (e.g., subprocess timeout values)
    - Control flow analysis (dead code detection)
    - Import order validation

    For simple presence checks, use has_pattern() instead (1000x faster).

    Args:
        filepath: Absolute or relative path to Python file (as string for hashability)

    Returns:
        Tuple of (ast.Module, str) on success - the AST tree and file content
        Tuple of (None, None) on parse error (SyntaxError, OSError)

    Note:
        Returns content alongside tree so callers can use ast.get_source_segment()
    """
    try:
        content = cached_read_file(filepath)
        tree = ast.parse(content, filename=filepath)
        return (tree, content)
    except (SyntaxError, OSError):
        return (None, None)


# =============================================================================
# FAST REGEX-BASED CHECKS (use for presence detection)
# =============================================================================

# Pre-compiled patterns for common checks (compiled once, reused)
_PATTERNS = {
    # Match both @pytest.mark.xdist_group and pytestmark = [...xdist_group...]
    "xdist_group": re.compile(r"pytest\.mark\.xdist_group\s*\("),
    "pytest_marker": re.compile(r"@pytest\.mark\.\w+"),
    "pytestmark": re.compile(r"^pytestmark\s*=", re.MULTILINE),
    "fixture": re.compile(r"@pytest\.fixture"),
    "subprocess_run": re.compile(r"subprocess\.run\s*\("),
    "pytest_skip": re.compile(r"pytest\.skip\s*\("),
    "pytest_xfail": re.compile(r"@pytest\.mark\.xfail"),
}


def has_pattern(filepath: str, pattern: str | re.Pattern) -> bool:
    """
    Fast check if file contains a regex pattern.

    This is ~1000x faster than AST parsing for simple presence detection.

    Args:
        filepath: Path to file (as string)
        pattern: Regex pattern string or compiled pattern

    Returns:
        True if pattern found, False otherwise
    """
    try:
        content = cached_read_file(filepath)
        if isinstance(pattern, str):
            return bool(re.search(pattern, content))
        return bool(pattern.search(content))
    except OSError:
        return False


def has_xdist_group(filepath: str) -> bool:
    """Check if file has @pytest.mark.xdist_group decorator."""
    return has_pattern(filepath, _PATTERNS["xdist_group"])


def has_pytest_marker(filepath: str) -> bool:
    """Check if file has any @pytest.mark.* decorator."""
    return has_pattern(filepath, _PATTERNS["pytest_marker"])


def has_pytestmark(filepath: str) -> bool:
    """Check if file has module-level pytestmark assignment."""
    return has_pattern(filepath, _PATTERNS["pytestmark"])


def has_fixture_decorator(filepath: str) -> bool:
    """Check if file has @pytest.fixture decorator."""
    return has_pattern(filepath, _PATTERNS["fixture"])


def has_subprocess_run(filepath: str) -> bool:
    """Check if file has subprocess.run() calls."""
    return has_pattern(filepath, _PATTERNS["subprocess_run"])


def find_pattern_lines(filepath: str, pattern: str | re.Pattern) -> list[tuple[int, str]]:
    """
    Find all lines matching a pattern with line numbers.

    Args:
        filepath: Path to file
        pattern: Regex pattern

    Returns:
        List of (line_number, line_content) tuples (1-indexed)
    """
    try:
        content = cached_read_file(filepath)
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        matches = []
        for i, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                matches.append((i, line))
        return matches
    except OSError:
        return []


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================


def clear_cache() -> None:
    """
    Clear all cached file contents and AST trees.

    Useful for testing or when files have changed during a test run.
    """
    cached_read_file.cache_clear()
    cached_parse_ast.cache_clear()


def cache_stats() -> dict:
    """
    Get cache statistics for debugging.

    Returns:
        Dictionary with 'read_file' and 'parse_ast' cache info
    """
    return {
        "read_file": cached_read_file.cache_info(),
        "parse_ast": cached_parse_ast.cache_info(),
    }
