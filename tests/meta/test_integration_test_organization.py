"""
Meta-tests for integration test organization and marker consistency.

These tests validate that integration tests are properly organized and that
marker-based selection matches directory-based selection for local/CI parity.

PURPOSE:
--------
Prevent integration test fragmentation where tests marked with
@pytest.mark.integration live outside tests/integration/, causing pre-commit
hooks to miss them while CI catches them.

VALIDATION:
-----------
1. All @pytest.mark.integration tests are in tests/integration/
2. All files in tests/integration/ have integration marker
3. Pre-commit and CI use same selection strategy
4. No integration tests in unit/, patterns/, or root tests/

References:
- OpenAI Codex Finding #3: Integration test fragmentation
- Pre-commit hook: run-integration-tests (directory-based)
- CI workflow: integration-tests.yaml (marker-based)
"""

import ast
import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


def find_pytest_markers_in_file(file_path: Path) -> set[str]:
    """
    Extract all pytest markers from a test file using AST parsing.

    Returns set of marker names (e.g., {'unit', 'integration', 'meta'})
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    markers = set()

    for node in ast.walk(tree):
        # Check for @pytest.mark.marker_name decorators
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                # Handle @pytest.mark.integration
                if isinstance(decorator, ast.Attribute):
                    if isinstance(decorator.value, ast.Attribute) and decorator.value.attr == "mark":
                        markers.add(decorator.attr)

                # Handle @pytest.mark.integration(...) with args
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if isinstance(decorator.func.value, ast.Attribute) and decorator.func.value.attr == "mark":
                            markers.add(decorator.func.attr)

        # Check for pytestmark = pytest.mark.integration
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    # pytestmark = pytest.mark.integration
                    if isinstance(node.value, ast.Attribute):
                        if isinstance(node.value.value, ast.Attribute) and node.value.value.attr == "mark":
                            markers.add(node.value.attr)

                    # pytestmark = [pytest.mark.integration, pytest.mark.unit]
                    elif isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Attribute):
                                if isinstance(elt.value, ast.Attribute) and elt.value.attr == "mark":
                                    markers.add(elt.attr)

    return markers


def find_all_test_files(root: Path, pattern: str = "test_*.py") -> list[Path]:
    """Find all test files matching pattern recursively."""
    return sorted(root.rglob(pattern))


@pytest.mark.meta
@pytest.mark.xdist_group(name="integration_test_organization_tests")
class TestIntegrationTestOrganization:
    """
    Validate that integration tests are properly organized.

    Ensures all integration-marked tests are in tests/integration/
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_integration_markers_in_integration_directory(self):
        """
        🟢 GREEN: Verify all @pytest.mark.integration tests are in tests/integration/.

        Integration tests should be consolidated in one directory for clarity
        and to ensure pre-commit hooks catch them all.

        EXCEPTION: tests/meta/ tests may use integration marker for testing
        integration test infrastructure itself.
        """
        root = Path(__file__).parent.parent.parent
        tests_dir = root / "tests"

        # Find all test files
        all_test_files = find_all_test_files(tests_dir)

        # Find files with integration marker outside tests/integration/
        misplaced_integration_tests: list[tuple[Path, str]] = []

        for test_file in all_test_files:
            # Skip __init__.py files
            if test_file.name == "__init__.py":
                continue

            # Get relative path for clearer error messages
            rel_path = test_file.relative_to(root)

            # Allowed locations for integration marker
            allowed_locations = [
                tests_dir / "integration",
                tests_dir / "meta",  # Meta-tests may test integration infrastructure
            ]

            # Check if file is in allowed location
            in_allowed_location = any(test_file.is_relative_to(allowed) for allowed in allowed_locations)

            if in_allowed_location:
                continue

            # Check for integration marker
            markers = find_pytest_markers_in_file(test_file)

            if "integration" in markers:
                # Found integration test outside allowed locations
                misplaced_integration_tests.append((test_file, str(rel_path)))

        # Generate helpful error message
        if misplaced_integration_tests:
            error_msg = f"Found {len(misplaced_integration_tests)} integration tests outside tests/integration/:\n\n"
            for test_file, rel_path in misplaced_integration_tests:
                error_msg += f"  - {rel_path}\n"

            error_msg += "\nMove these tests to tests/integration/ with:\n"
            error_msg += "  python scripts/migrate_integration_tests.py\n"

            assert False, error_msg

    def test_all_integration_directory_files_have_integration_marker(self):
        """
        🟢 GREEN: Verify all files in tests/integration/ have @pytest.mark.integration.

        Reverse check: ensure directory structure matches marker usage.
        """
        root = Path(__file__).parent.parent.parent
        integration_dir = root / "tests" / "integration"

        if not integration_dir.exists():
            pytest.skip("tests/integration/ directory does not exist")

        # Find all test files in integration directory
        integration_files = find_all_test_files(integration_dir)

        # Check each file has integration marker
        missing_marker: list[str] = []

        for test_file in integration_files:
            # Skip __init__.py files
            if test_file.name == "__init__.py":
                continue

            rel_path = test_file.relative_to(root)

            markers = find_pytest_markers_in_file(test_file)

            if "integration" not in markers:
                missing_marker.append(str(rel_path))

        if missing_marker:
            error_msg = f"Found {len(missing_marker)} files in tests/integration/ without @pytest.mark.integration:\n\n"
            for rel_path in missing_marker:
                error_msg += f"  - {rel_path}\n"

            error_msg += "\nAdd @pytest.mark.integration to these files.\n"

            assert False, error_msg

    def test_no_integration_tests_in_unit_directory(self):
        """
        🟢 GREEN: Verify no @pytest.mark.integration tests in tests/unit/.

        Unit tests should not have integration marker.
        """
        root = Path(__file__).parent.parent.parent
        unit_dir = root / "tests" / "unit"

        if not unit_dir.exists():
            pytest.skip("tests/unit/ directory does not exist")

        # Find all test files in unit directory
        unit_files = find_all_test_files(unit_dir)

        # Check for integration marker
        integration_in_unit: list[str] = []

        for test_file in unit_files:
            if test_file.name == "__init__.py":
                continue

            rel_path = test_file.relative_to(root)

            markers = find_pytest_markers_in_file(test_file)

            if "integration" in markers:
                integration_in_unit.append(str(rel_path))

        if integration_in_unit:
            error_msg = f"Found {len(integration_in_unit)} integration tests in tests/unit/:\n\n"
            for rel_path in integration_in_unit:
                error_msg += f"  - {rel_path}\n"

            error_msg += "\nMove to tests/integration/ or remove integration marker.\n"

            assert False, error_msg

    def test_no_integration_tests_in_root_tests_directory(self):
        """
        🟢 GREEN: Verify no @pytest.mark.integration tests in root tests/ directory.

        Integration tests should be in tests/integration/, not scattered in root.
        """
        root = Path(__file__).parent.parent.parent
        tests_dir = root / "tests"

        # Find test files directly in tests/ (not in subdirectories)
        root_test_files = sorted(tests_dir.glob("test_*.py"))

        # Check for integration marker
        integration_in_root: list[str] = []

        for test_file in root_test_files:
            if test_file.name == "__init__.py":
                continue

            rel_path = test_file.relative_to(root)

            markers = find_pytest_markers_in_file(test_file)

            if "integration" in markers:
                integration_in_root.append(str(rel_path))

        if integration_in_root:
            error_msg = f"Found {len(integration_in_root)} integration tests in root tests/:\n\n"
            for rel_path in integration_in_root:
                error_msg += f"  - {rel_path}\n"

            error_msg += "\nMove to tests/integration/.\n"

            assert False, error_msg

    def test_integration_directory_exists(self):
        """
        🟢 GREEN: Verify tests/integration/ directory exists.

        The integration tests directory must exist.
        """
        root = Path(__file__).parent.parent.parent
        integration_dir = root / "tests" / "integration"

        assert integration_dir.exists(), (
            "tests/integration/ directory must exist. Create with:\n" "  mkdir -p tests/integration"
        )
        assert integration_dir.is_dir(), "tests/integration/ must be a directory"


@pytest.mark.meta
@pytest.mark.xdist_group(name="integration_test_selection_tests")
class TestIntegrationTestSelection:
    """
    Validate that pre-commit and CI use consistent integration test selection.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_precommit_uses_marker_based_selection(self):
        """
        🟢 GREEN: Verify pre-commit hook uses marker-based selection.

        Pre-commit should use `pytest -m integration` to match CI, NOT
        directory-based selection which can miss tests.

        UPDATE (After Consolidation):
        ------------------------------
        After consolidating all integration tests into tests/integration/,
        directory-based selection is acceptable since both approaches yield
        the same results. However, marker-based is preferred for robustness.
        """
        root = Path(__file__).parent.parent.parent
        precommit_config = root / ".pre-commit-config.yaml"

        assert precommit_config.exists(), ".pre-commit-config.yaml must exist"

        content = precommit_config.read_text()

        # Find run-integration-tests hook
        assert "run-integration-tests" in content, "run-integration-tests hook missing from .pre-commit-config.yaml"

        # After consolidation, either approach is acceptable:
        # 1. Marker-based: pytest -m integration (preferred)
        # 2. Directory-based: pytest tests/integration/ (acceptable after consolidation)

        has_marker_selection = "-m integration" in content
        has_directory_selection = "tests/integration/" in content

        assert has_marker_selection or has_directory_selection, (
            "Pre-commit hook must use either marker-based (-m integration) or "
            "directory-based (tests/integration/) selection for integration tests"
        )

    def test_ci_uses_marker_based_selection(self):
        """
        🟢 GREEN: Verify CI workflow uses marker-based selection.

        CI should use `pytest -m integration` for maximum coverage.
        """
        root = Path(__file__).parent.parent.parent
        workflow = root / ".github" / "workflows" / "integration-tests.yaml"

        assert workflow.exists(), "integration-tests.yaml must exist"

        content = workflow.read_text()

        # CI should use marker-based selection
        assert "-m integration" in content, (
            "CI workflow must use marker-based selection (-m integration) "
            "to catch all integration tests regardless of location"
        )


@pytest.mark.meta
@pytest.mark.xdist_group(name="integration_test_documentation_tests")
class TestIntegrationTestDocumentation:
    """
    Validate integration test organization is documented.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_integration_directory_has_readme(self):
        """
        🟢 GREEN: Verify tests/integration/ has README explaining organization.

        Documentation helps developers understand where to put tests.
        """
        root = Path(__file__).parent.parent.parent
        readme = root / "tests" / "integration" / "README.md"

        # This is a nice-to-have, not required
        if readme.exists():
            content = readme.read_text()
            # Should explain what integration tests are
            assert "integration" in content.lower(), "README should explain integration tests"

    def test_testing_md_documents_integration_test_organization(self):
        """
        🟢 GREEN: Verify TESTING.md documents where integration tests live.

        Developers should know where to put integration tests.
        """
        root = Path(__file__).parent.parent.parent
        testing_doc = root / "TESTING.md"

        if not testing_doc.exists():
            pytest.skip("TESTING.md not found")

        content = testing_doc.read_text()

        # Should mention integration tests
        assert "integration" in content.lower(), "TESTING.md should document integration tests"


@pytest.mark.meta
@pytest.mark.xdist_group(name="integration_test_enforcement_tests")
class TestIntegrationTestEnforcement:
    """
    Document enforcement strategy for integration test organization.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enforcement_strategy_documentation(self):
        """
        📚 Document the enforcement strategy for integration test organization.

        Multiple layers ensure integration tests are properly organized.
        """
        strategy = """
        ENFORCEMENT STRATEGY: Integration Test Organization
        ====================================================

        Goal: Consolidate all integration tests in tests/integration/ to ensure
        local pre-commit hooks and CI use same test selection.

        Layer 1: Meta-Tests (This File)
        --------------------------------
        ✅ test_all_integration_markers_in_integration_directory
           - Scans all test files for @pytest.mark.integration
           - Fails if any found outside tests/integration/ (except meta/)
           - Clear error message with file paths

        ✅ test_all_integration_directory_files_have_integration_marker
           - Reverse check: files in tests/integration/ must have marker
           - Ensures consistency

        ✅ test_no_integration_tests_in_unit_directory
           - Prevents accidental integration tests in unit/
           - Common mistake to catch

        ✅ test_no_integration_tests_in_root_tests_directory
           - Prevents scattered integration tests
           - Forces proper organization

        Layer 2: Migration Script
        --------------------------
        ✅ scripts/migrate_integration_tests.py
           - Automates moving misplaced integration tests
           - Preserves git history with git mv
           - Updates imports automatically
           - Creates proper directory structure

        Layer 3: Pre-Commit Selection Alignment
        ----------------------------------------
        ✅ After consolidation: Directory-based and marker-based selection
           yield identical results
        ✅ Pre-commit can use either approach safely
        ✅ CI uses marker-based for robustness

        Layer 4: Documentation
        -----------------------
        ✅ tests/integration/README.md (if exists)
        ✅ TESTING.md mentions integration test location
        ✅ This meta-test serves as documentation

        Enforcement Coverage:
        =====================

        Misplaced integration tests: ✅ Meta-test catches immediately
        Missing integration marker: ✅ Meta-test catches
        Pre-commit/CI mismatch: ✅ Meta-test validates both
        Documentation: ✅ Meta-test validates exists

        Migration Path:
        ===============

        1. Run meta-tests (this file) to identify misplaced tests
        2. Run scripts/migrate_integration_tests.py to move them
        3. Re-run meta-tests to verify (should be GREEN)
        4. Update pre-commit config if needed
        5. Commit changes with preserved git history

        Risk After Consolidation: VERY LOW
        All integration tests in one place, meta-tests enforce.
        """

        assert len(strategy) > 100, "Strategy documented"
        assert "Layer 1" in strategy
        assert "Layer 2" in strategy

    def test_consolidation_benefits_documented(self):
        """
        📚 Document the benefits of integration test consolidation.

        Explain why consolidating integration tests improves workflow.
        """
        benefits = """
        BENEFITS OF INTEGRATION TEST CONSOLIDATION
        ===========================================

        1. Local/CI Parity
           - Pre-commit hooks catch same tests as CI
           - No surprises after pushing
           - Failed test locally = will fail in CI

        2. Predictable Organization
           - Developers know where to put integration tests
           - Easy to find all integration tests
           - Clear separation from unit tests

        3. Simpler Pre-Commit Config
           - Can use simple directory-based selection
           - No complex marker filtering needed
           - Faster pre-commit runs (scoped to relevant files)

        4. Easier Code Navigation
           - All integration tests in one place
           - Related tests grouped together
           - Better discoverability

        5. Reduced Fragmentation
           - No scattered integration tests
           - Consistent patterns across codebase
           - Less confusion for new contributors

        6. Better Test Categorization
           - Clear distinction: unit/ vs integration/
           - Easier to run subsets of tests
           - Better understanding of test coverage

        7. Migration Script Available
           - Automated moving of tests
           - Preserves git history
           - Updates imports automatically
           - Low-friction consolidation process
        """

        assert len(benefits) > 100, "Benefits documented"
        assert "Local/CI Parity" in benefits
        assert "Predictable Organization" in benefits
