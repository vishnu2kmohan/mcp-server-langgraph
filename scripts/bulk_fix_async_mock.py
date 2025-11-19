#!/usr/bin/env python3
"""
Bulk fix script for AsyncMock configuration violations.

This script automatically transforms unconfigured AsyncMock() instances to use
the configured_async_mock() helper factory.

Strategy:
    1. Parse Python source files using AST
    2. Detect AsyncMock() calls without explicit return_value/side_effect
    3. Replace with configured_async_mock(return_value=None)
    4. Add import statement if not present
    5. Preserve formatting and comments where possible

Usage:
    python scripts/bulk_fix_async_mock.py tests/test_example.py
    python scripts/bulk_fix_async_mock.py tests/**/*.py  # Bulk fix

Safety:
    - Creates .backup files before modifying
    - Uses black for formatting after transformation
    - Validates syntax before writing
    - Dry-run mode available: --dry-run

Author: Claude Code (Sonnet 4.5)
Created: 2025-11-15
"""

import argparse
import ast
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class AsyncMockTransformer(ast.NodeTransformer):
    """
    AST transformer that replaces unconfigured AsyncMock() with configured helpers.

    Transformations:
        AsyncMock() → configured_async_mock(return_value=None)
        AsyncMock(spec=Foo) → configured_async_mock(return_value=None, spec=Foo)
        AsyncMock(spec_set=Bar) → configured_async_mock(return_value=None, spec_set=Bar)

    Does NOT transform:
        AsyncMock(return_value=X) - already configured
        AsyncMock(side_effect=Y) - already configured
    """

    def __init__(self):
        self.transformations = 0
        self.needs_import = False

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Visit function call nodes and transform AsyncMock calls."""
        self.generic_visit(node)

        # Check if this is an AsyncMock() call
        if not self._is_async_mock_call(node):
            return node

        # Check if already configured (has return_value or side_effect)
        if self._is_already_configured(node):
            return node

        # Transform to configured_async_mock()
        return self._transform_to_configured(node)

    def _is_async_mock_call(self, node: ast.Call) -> bool:
        """Check if node is an AsyncMock() call."""
        if isinstance(node.func, ast.Name):
            return node.func.id == "AsyncMock"
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "AsyncMock"
        return False

    def _is_already_configured(self, node: ast.Call) -> bool:
        """Check if AsyncMock is already configured with return_value or side_effect."""
        return any(keyword.arg in ("return_value", "side_effect") for keyword in node.keywords)

    def _transform_to_configured(self, node: ast.Call) -> ast.Call:
        """Transform AsyncMock() to configured_async_mock(return_value=None)."""
        self.transformations += 1
        self.needs_import = True

        # Create new call to configured_async_mock
        new_call = ast.Call(
            func=ast.Name(id="configured_async_mock", ctx=ast.Load()), args=node.args.copy(), keywords=node.keywords.copy()
        )

        # Add return_value=None as first keyword argument
        return_value_kwarg = ast.keyword(arg="return_value", value=ast.Constant(value=None))
        new_call.keywords.insert(0, return_value_kwarg)

        # Copy location info for better error messages
        ast.copy_location(new_call, node)
        ast.copy_location(new_call.func, node.func)

        return new_call


def add_import_statement(source: str) -> str:
    """
    Add import statement for configured_async_mock if not present.

    Insertion strategy:
        1. After existing unittest.mock imports
        2. After all imports (end of import block)
        3. At top of file if no imports

    Args:
        source: Python source code

    Returns:
        Modified source with import added
    """
    lines = source.split("\n")
    import_line = "from tests.helpers.async_mock_helpers import configured_async_mock"

    # Check if import already exists
    if any(import_line in line for line in lines):
        return source

    # Find insertion point
    insertion_idx = 0
    last_import_idx = -1
    mock_import_idx = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = idx
            if "unittest.mock" in stripped or "mock" in stripped:
                mock_import_idx = idx

    # Insertion strategy
    if mock_import_idx >= 0:
        # Insert after unittest.mock imports
        insertion_idx = mock_import_idx + 1
    elif last_import_idx >= 0:
        # Insert after last import
        insertion_idx = last_import_idx + 1
    else:
        # Insert at top (after docstring if present)
        insertion_idx = 0
        if lines and (lines[0].startswith('"""') or lines[0].startswith("'''")):
            # Skip docstring
            for idx in range(1, len(lines)):
                if '"""' in lines[idx] or "'''" in lines[idx]:
                    insertion_idx = idx + 1
                    break

    # Insert import
    lines.insert(insertion_idx, import_line)

    return "\n".join(lines)


def transform_file(file_path: Path, dry_run: bool = False) -> tuple[int, bool]:
    """
    Transform a single Python file to use configured AsyncMock helpers.

    Args:
        file_path: Path to Python file
        dry_run: If True, don't write changes

    Returns:
        Tuple of (transformations_count, success)
    """
    logger.info(f"Processing {file_path}")

    # Read source
    try:
        source = file_path.read_text()
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return 0, False

    # Parse AST
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.error(f"Syntax error in {file_path}: {e}")
        return 0, False

    # Transform
    transformer = AsyncMockTransformer()
    new_tree = transformer.visit(tree)

    if transformer.transformations == 0:
        logger.info(f"  No transformations needed for {file_path}")
        return 0, True

    # Generate new source
    try:
        import astor

        new_source = astor.to_source(new_tree)
    except ImportError:
        logger.warning("astor not installed, using ast.unparse (Python 3.9+)")
        new_source = ast.unparse(new_tree)

    # Add import if needed
    if transformer.needs_import:
        new_source = add_import_statement(new_source)

    # Format with black
    try:
        result = subprocess.run(
            ["uv", "run", "black", "--quiet", "-"], input=new_source.encode(), capture_output=True, check=True
        )
        new_source = result.stdout.decode()
    except subprocess.CalledProcessError:
        logger.warning(f"  Black formatting failed for {file_path}, using unformatted")
    except FileNotFoundError:
        logger.warning("  Black not found, skipping formatting")

    # Validate syntax of new source
    try:
        ast.parse(new_source)
    except SyntaxError as e:
        logger.error(f"  Generated invalid syntax for {file_path}: {e}")
        return 0, False

    if dry_run:
        logger.info(f"  [DRY RUN] Would transform {transformer.transformations} AsyncMock calls in {file_path}")
        return transformer.transformations, True

    # Backup original
    backup_path = file_path.with_suffix(file_path.suffix + ".backup")
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        logger.error(f"  Failed to create backup for {file_path}: {e}")
        return 0, False

    # Write transformed source
    try:
        file_path.write_text(new_source)
        logger.info(f"  ✅ Transformed {transformer.transformations} AsyncMock calls in {file_path}")
        logger.info(f"  📁 Backup saved to {backup_path}")
        return transformer.transformations, True
    except Exception as e:
        logger.error(f"  Failed to write {file_path}: {e}")
        # Restore from backup
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"  Restored from backup")
        except:
            pass
        return 0, False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bulk fix AsyncMock configuration violations")
    parser.add_argument("files", nargs="+", type=Path, help="Python test files to transform")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate files
    files = []
    for file_path in args.files:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            continue
        if not file_path.is_file():
            logger.error(f"Not a file: {file_path}")
            continue
        if file_path.suffix != ".py":
            logger.warning(f"Not a Python file: {file_path}")
            continue
        files.append(file_path)

    if not files:
        logger.error("No valid Python files to process")
        return 1

    # Transform files
    total_transformations = 0
    successful = 0
    failed = 0

    for file_path in files:
        count, success = transform_file(file_path, dry_run=args.dry_run)
        total_transformations += count
        if success:
            successful += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("TRANSFORMATION SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(files)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"Total AsyncMock transformations: {total_transformations}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files were modified")
    else:
        print("\n✅ Transformations complete!")
        print("💡 Next steps:")
        print("  1. Run tests: uv run pytest")
        print("  2. Verify: uv run python scripts/check_async_mock_configuration.py")
        print("  3. Review changes: git diff")
        print("  4. Remove backups: find tests -name '*.backup' -delete")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
