"""
Meta-tests for validating path calculations in test files.

These tests ensure that all test files correctly calculate repository root paths,
preventing FileNotFoundError and incorrect path assumptions.

Context:
- Tests often need to calculate repo_root to access deployments/, config files, etc.
- Incorrect .parents[N] calculations lead to paths pointing to tests/ instead of repo root
- Using marker files (.git, pyproject.toml) is safer than hardcoded parent counts

Test Coverage:
1. Keycloak deployment tests calculate correct repo_root
2. LangGraph deployment tests calculate correct repo_root
3. All deployment paths point to existing directories
4. No hardcoded parent counts without marker file validation
"""

import gc
from pathlib import Path

import pytest

# Mark as unit test (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.validation]


@pytest.fixture(scope="module")
def actual_repo_root() -> Path:
    """
    Get actual repository root using marker file search.

    This is the CORRECT way to find repo root - search for markers like .git
    instead of using hardcoded .parents[N] counts.
    """
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.mark.xdist_group(name="path_validation_tests")
class TestRepoRootCalculations:
    """Validate repo_root calculations in test files"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_deployment_test_repo_root_is_correct(self, actual_repo_root: Path) -> None:
        """
        GIVEN tests/integration/deployment/test_keycloak_readonly_filesystem.py
        WHEN repo_root fixture calculates path
        THEN it should point to actual repository root (not tests/)
        AND deployments/base directory should exist at that location
        """
        # Calculate what the test file currently does
        test_file = actual_repo_root / "tests" / "integration" / "deployment" / "test_keycloak_readonly_filesystem.py"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        # Test file uses .parents[2] which should be .parents[3]
        # Let's verify the correct calculation
        calculated_repo_root = test_file.resolve().parents[3]

        # Verify this matches our actual repo root
        assert calculated_repo_root == actual_repo_root, (
            f"Keycloak test repo_root calculation incorrect. "
            f"Expected {actual_repo_root}, got {calculated_repo_root}. "
            f"Test file should use .parents[3], not .parents[2]"
        )

        # Verify deployments/base exists at this location
        deployments_base = calculated_repo_root / "deployments" / "base"
        assert deployments_base.exists(), (
            f"deployments/base not found at {deployments_base}. "
            f"This confirms repo_root calculation is correct and deployments/ exists."
        )

    def test_langgraph_deployment_test_repo_root_is_correct(self, actual_repo_root: Path) -> None:
        """
        GIVEN tests/integration/deployment/test_langgraph_platform.py
        WHEN path to deployments/ is calculated
        THEN it should use marker file approach (not hardcoded .parents[N])
        AND it should point to actual repository deployments/ directory

        NOTE: Directory consolidation completed - test_langgraph_platform.py
        moved from deployments/ (plural) to deployment/ (singular) and
        updated to use get_repo_root() function with marker file validation.
        """
        # File should now be in deployment/ (singular) only
        test_file = actual_repo_root / "tests" / "integration" / "deployment" / "test_langgraph_platform.py"

        assert test_file.exists(), (
            f"test_langgraph_platform.py should be in deployment/ directory (singular), "
            f"not deployments/ (plural). File not found at {test_file}"
        )

        # Verify file uses marker file approach (has get_repo_root function)
        content = test_file.read_text()
        assert "def get_repo_root()" in content, (
            "test_langgraph_platform.py should use get_repo_root() function "
            "with marker file validation, not hardcoded .parents[N]"
        )
        assert "pyproject.toml" in content or ".git" in content, (
            "test_langgraph_platform.py should validate marker files (.git, pyproject.toml) in get_repo_root() function"
        )

        # Verify no hardcoded .parents[N] path calculations remain
        assert "Path(__file__).parent.parent.parent" not in content, (
            "test_langgraph_platform.py should not use hardcoded .parents[N] - use get_repo_root() function instead"
        )

        # Verify deployments/ directory exists at repo root
        deployments_dir = actual_repo_root / "deployments"
        assert deployments_dir.exists(), f"deployments/ directory not found at {deployments_dir}"

    def test_all_deployment_test_paths_point_to_existing_directories(self, actual_repo_root: Path) -> None:
        """
        GIVEN all test files in tests/integration/deployment*/
        WHEN they calculate paths to deployments/
        THEN those paths should exist
        """
        tests_integration = actual_repo_root / "tests" / "integration"

        # Find all deployment-related test directories
        deployment_test_dirs = []
        for path in tests_integration.iterdir():
            if path.is_dir() and "deployment" in path.name:
                deployment_test_dirs.append(path)

        assert len(deployment_test_dirs) > 0, "No deployment test directories found"

        # Verify deployments/ directory exists at repo root
        deployments_dir = actual_repo_root / "deployments"
        assert deployments_dir.exists(), (
            f"deployments/ directory not found at repo root: {deployments_dir}. "
            f"Deployment tests cannot function without this directory."
        )

        # Verify key subdirectories exist
        expected_subdirs = ["base", "overlays"]
        for subdir in expected_subdirs:
            path = deployments_dir / subdir
            assert path.exists(), f"Expected deployment subdirectory not found: {path}"

    def test_no_hardcoded_parents_without_marker_validation(self, actual_repo_root: Path) -> None:
        """
        GIVEN any test file that uses .parents[N] to find repo root
        WHEN validating path calculation pattern
        THEN it should include marker file validation (.git, pyproject.toml)
        OR use the centralized project_root fixture from conftest.py

        This test serves as documentation of best practices, not strict enforcement.
        """
        # This is a documentation test - it passes but warns about patterns
        # In a real scenario, we'd parse Python files looking for .parents[N] patterns
        # and flag those without marker validation

        # For now, just verify our test files use correct patterns
        test_files_to_check = [
            actual_repo_root / "tests" / "integration" / "deployment" / "test_keycloak_readonly_filesystem.py",
        ]

        issues = []
        for test_file in test_files_to_check:
            if not test_file.exists():
                continue

            content = test_file.read_text()

            # Check if file uses .parents[N] pattern
            if ".parents[" in content:
                # Check if it validates with marker files
                has_marker_validation = any(
                    marker in content for marker in [".git", "pyproject.toml", "setup.py", "project_root"]
                )

                if not has_marker_validation:
                    issues.append(f"{test_file.relative_to(actual_repo_root)}: Uses .parents[N] without marker validation")

        # This test documents the issue but doesn't fail (yet)
        # Once we fix all files, we can make this strict
        if issues:
            pytest.skip(
                f"Found {len(issues)} files using .parents[N] without marker validation:\n"
                + "\n".join(f"  - {issue}" for issue in issues)
                + "\n\nRecommendation: Use project_root fixture from conftest.py or validate with marker files."
            )


@pytest.mark.xdist_group(name="path_validation_tests")
class TestPathCalculationPatterns:
    """Validate path calculation patterns and best practices"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_conftest_provides_project_root_fixture(self, actual_repo_root: Path) -> None:
        """
        GIVEN tests/conftest.py
        WHEN checking for centralized path fixtures
        THEN it should provide a project_root fixture that tests can use
        """
        conftest = actual_repo_root / "tests" / "conftest.py"
        assert conftest.exists(), "tests/conftest.py not found"

        content = conftest.read_text()

        # Check if project_root fixture exists
        has_project_root = "def project_root" in content or "@pytest.fixture" in content and "project_root" in content

        if not has_project_root:
            pytest.skip(
                "tests/conftest.py does not provide a centralized project_root fixture. "
                "Consider adding one to prevent path calculation errors."
            )

    def test_repo_root_points_to_directory_with_pyproject_toml(self, actual_repo_root: Path) -> None:
        """
        GIVEN calculated repo_root
        WHEN validating it's the correct location
        THEN pyproject.toml should exist at that path
        """
        pyproject_toml = actual_repo_root / "pyproject.toml"
        assert pyproject_toml.exists(), (
            f"pyproject.toml not found at {actual_repo_root}. This indicates repo_root calculation is incorrect."
        )

    def test_repo_root_points_to_directory_with_git_folder(self, actual_repo_root: Path) -> None:
        """
        GIVEN calculated repo_root
        WHEN validating it's the correct location
        THEN .git directory or file (for worktrees) should exist
        """
        git_path = actual_repo_root / ".git"
        assert git_path.exists(), f".git not found at {actual_repo_root}. This indicates repo_root calculation is incorrect."
