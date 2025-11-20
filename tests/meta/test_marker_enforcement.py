"""
Meta-test to enforce pytest marker presence on all test files.

This test validates that all test files have appropriate pytest markers
to ensure they run in CI and are properly categorized.

RATIONALE (OpenAI Codex Finding #1):
- CI runs: pytest -n auto -m "unit and not llm"
- Tests without @pytest.mark.unit are INVISIBLE to CI
- 176 test files (57%) were unmarked, including critical guard-rail tests
- This meta-test prevents regression by enforcing marker requirements

VALIDATION CRITERIA:
- All test files must have at least one marker from: unit, integration, e2e
- Critical guard-rail tests must have both unit AND meta markers
- Files can opt-out via MARKER_EXEMPT_FILES list (with justification)

References:
- .github/workflows/ci.yaml:243 - CI test filter
- CLAUDE.md - Test marker conventions
- OpenAI Codex validation report (2025-11-15)
"""

import ast
import gc
from pathlib import Path

import pytest

# Test files that are intentionally exempt from marker requirements
# Each entry must have a documented reason
MARKER_EXEMPT_FILES: set[str] = {
    # Add exempt files here with justification comments
    # Example: "tests/examples/demo.py",  # Educational example, not executed in CI
    "tests/validation_lib/test_ids.py",  # Validation utility module, not a test file
}

# Critical guard-rail tests that must have both 'unit' AND 'meta' markers
CRITICAL_GUARD_RAIL_TESTS: set[str] = {
    "tests/test_gitignore_validation.py",
    "tests/test_documentation_integrity.py",
    "tests/test_workflow_security.py",
    "tests/test_mdx_validation.py",
    "tests/test_validate_mintlify_docs.py",
}

# Meta test classes that must have xdist_group markers (OpenAI Codex Finding #5)
# These classes perform repository-wide operations and need isolation
META_TEST_CLASSES_REQUIRING_XDIST_GROUP: set[tuple[str, str]] = {
    ("tests/meta/test_slash_commands.py", "TestCommandDocumentation"),
    ("tests/meta/test_claude_settings_schema.py", "TestSettingsLocalExclusion"),
    ("tests/meta/test_migration_checklists.py", "TestTypeSafetyChecklist"),
}


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="marker_enforcement")
class TestMarkerEnforcement:
    """Enforce pytest marker presence on all test files."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _get_all_test_files(self) -> list[Path]:
        """Get all Python test files in the tests/ directory."""
        tests_dir = Path(__file__).parent.parent  # tests/
        test_files = list(tests_dir.rglob("test_*.py"))
        test_files.extend(tests_dir.rglob("*_test.py"))
        return sorted(set(test_files))

    def _extract_markers_from_file(self, file_path: Path) -> set[str]:
        """
        Extract pytest markers from a test file.

        Returns set of marker names found in the file via:
        - pytestmark = pytest.mark.unit
        - pytestmark = [pytest.mark.unit, pytest.mark.integration]
        - @pytest.mark.unit decorators on classes/functions
        """
        markers = set()

        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            # If file has syntax errors, pytest won't collect it anyway
            return markers

        # Check for module-level pytestmark variable
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        # pytestmark = pytest.mark.unit
                        if isinstance(node.value, ast.Attribute):
                            if isinstance(node.value.value, ast.Attribute) and node.value.value.attr == "mark":
                                markers.add(node.value.attr)
                        # pytestmark = [pytest.mark.unit, pytest.mark.meta]
                        elif isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Attribute):
                                    if isinstance(elt.value, ast.Attribute) and elt.value.attr == "mark":
                                        markers.add(elt.attr)

            # Check for decorators on classes and functions
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    # @pytest.mark.unit
                    if isinstance(decorator, ast.Attribute):
                        if isinstance(decorator.value, ast.Attribute) and decorator.value.attr == "mark":
                            markers.add(decorator.attr)
                    # @pytest.mark.unit(...)
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if isinstance(decorator.func.value, ast.Attribute) and decorator.func.value.attr == "mark":
                                markers.add(decorator.func.attr)

        return markers

    def test_all_test_files_have_markers(self):
        """
        RED PHASE TEST: Validates all test files have appropriate markers.

        This test will FAIL initially, proving it works. After adding markers
        to all test files, it will pass (GREEN phase).

        EXPECTED MARKERS:
        - unit: Fast tests, no external dependencies
        - integration: Tests requiring infrastructure (Redis, Keycloak, etc.)
        - e2e: End-to-end tests with full stack
        - meta: Meta-tests validating test infrastructure
        """
        test_files = self._get_all_test_files()
        unmarked_files = []
        required_categories = {"unit", "integration", "e2e"}

        for test_file in test_files:
            # Skip exempt files
            relative_path = str(test_file.relative_to(Path.cwd()))
            if relative_path in MARKER_EXEMPT_FILES:
                continue

            # Skip conftest.py files (not test files)
            if test_file.name == "conftest.py":
                continue

            markers = self._extract_markers_from_file(test_file)

            # Check if file has at least one category marker
            if not any(marker in required_categories for marker in markers):
                unmarked_files.append(relative_path)

        assert not unmarked_files, (
            "Found {} test files without required markers.\n\n"
            "Files must have at least one marker from: {}\n\n"
            "Unmarked files:\n"
            + "\n".join(f"  - {f}" for f in unmarked_files[:20])
            + (f"\n  ... and {len(unmarked_files) - 20} more" if len(unmarked_files) > 20 else "")
            + "\n\n"
            "CI filter: pytest -n auto -m 'unit and not llm'\n"
            "Tests without markers are INVISIBLE to CI!\n\n"
            "Add markers using:\n"
            "  pytestmark = pytest.mark.unit  # Top of file\n"
            "  # or\n"
            "  pytestmark = [pytest.mark.unit, pytest.mark.meta]  # Multiple markers\n"
        ).format(len(unmarked_files), required_categories)

    def test_critical_guard_rail_tests_have_meta_marker(self):
        """
        Validates critical guard-rail tests have both 'unit' and 'meta' markers.

        Critical guard-rail tests prevent bad code from being committed:
        - gitignore validation
        - documentation integrity
        - workflow security
        - MDX validation
        - Mintlify docs validation

        These MUST run in CI to provide protection.
        """
        missing_meta = []

        for test_file_path in CRITICAL_GUARD_RAIL_TESTS:
            test_file = Path(test_file_path)

            if not test_file.exists():
                missing_meta.append(f"{test_file_path} (FILE NOT FOUND)")
                continue

            markers = self._extract_markers_from_file(test_file)

            # Must have BOTH unit and meta markers
            if "unit" not in markers or "meta" not in markers:
                missing_markers = []
                if "unit" not in markers:
                    missing_markers.append("unit")
                if "meta" not in markers:
                    missing_markers.append("meta")
                missing_meta.append(f"{test_file_path} (missing: {', '.join(missing_markers)})")

        assert not missing_meta, (
            "Critical guard-rail tests must have both 'unit' AND 'meta' markers.\n\n"
            "Files with missing markers:\n" + "\n".join(f"  - {f}" for f in missing_meta) + "\n\n"
            "Add markers using:\n"
            "  pytestmark = [pytest.mark.unit, pytest.mark.meta]\n"
        )

    def test_meta_test_classes_have_xdist_group_markers(self):
        """
        Validates meta test classes have xdist_group markers for isolation.

        Related: OpenAI Codex Finding #5

        Meta test classes that perform repository-wide operations (reading/writing
        configuration files, checking documentation, etc.) should have xdist_group
        markers to ensure they run in the same worker and don't cause state pollution.

        Even if they don't use AsyncMock, grouping is still required for:
        1. Coding standard compliance
        2. Predictable worker assignment
        3. Future-proofing if mocks are added later
        """
        violations = []

        for test_file_path, class_name in META_TEST_CLASSES_REQUIRING_XDIST_GROUP:
            test_file = Path(test_file_path)

            if not test_file.exists():
                violations.append(f"{test_file_path} (FILE NOT FOUND)")
                continue

            # Parse file and find the class
            try:
                with open(test_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(test_file))
            except SyntaxError:
                violations.append(f"{test_file_path}::{class_name} (SYNTAX ERROR)")
                continue

            # Find the class definition
            class_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    class_node = node
                    break

            if class_node is None:
                violations.append(f"{test_file_path}::{class_name} (CLASS NOT FOUND)")
                continue

            # Check for xdist_group marker in decorators
            has_xdist_group = False
            for decorator in class_node.decorator_list:
                # @pytest.mark.xdist_group(name="...")
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if (
                            isinstance(decorator.func.value, ast.Attribute)
                            and decorator.func.value.attr == "mark"
                            and decorator.func.attr == "xdist_group"
                        ):
                            has_xdist_group = True
                            break

            if not has_xdist_group:
                violations.append(f"{test_file_path}::{class_name}")

        assert not violations, (
            "Meta test classes must have @pytest.mark.xdist_group marker.\n\n"
            "Classes missing xdist_group:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
            "Add marker using:\n"
            "  @pytest.mark.xdist_group(name='meta_<descriptive_name>')\n"
            "  class TestClassName:\n"
            "      def teardown_method(self):\n"
            "          gc.collect()\n\n"
            "This ensures test isolation and prevents state pollution in parallel execution.\n"
            "See: tests/MEMORY_SAFETY_GUIDELINES.md for details."
        )

    def test_marker_enforcement_statistics(self):
        """
        Reports statistics on marker coverage (informational, always passes).

        Provides visibility into marker adoption across the test suite.
        """
        test_files = self._get_all_test_files()
        marker_stats = {
            "unit": 0,
            "integration": 0,
            "e2e": 0,
            "meta": 0,
            "unmarked": 0,
        }

        for test_file in test_files:
            if test_file.name == "conftest.py":
                continue

            markers = self._extract_markers_from_file(test_file)

            if "unit" in markers:
                marker_stats["unit"] += 1
            if "integration" in markers:
                marker_stats["integration"] += 1
            if "e2e" in markers:
                marker_stats["e2e"] += 1
            if "meta" in markers:
                marker_stats["meta"] += 1

            required_categories = {"unit", "integration", "e2e"}
            if not any(marker in required_categories for marker in markers):
                marker_stats["unmarked"] += 1

        total = len([f for f in test_files if f.name != "conftest.py"])
        coverage = ((total - marker_stats["unmarked"]) / total * 100) if total > 0 else 0

        print("\n" + "=" * 60)
        print("Test Marker Coverage Statistics")
        print("=" * 60)
        print(f"Total test files: {total}")
        print(f"Unit marked: {marker_stats['unit']}")
        print(f"Integration marked: {marker_stats['integration']}")
        print(f"E2E marked: {marker_stats['e2e']}")
        print(f"Meta marked: {marker_stats['meta']}")
        print(f"Unmarked: {marker_stats['unmarked']}")
        print(f"Coverage: {coverage:.1f}%")
        print("=" * 60 + "\n")

        # This test always passes - it's informational only
        assert True
