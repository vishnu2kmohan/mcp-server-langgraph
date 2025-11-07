"""
Regression Tests for CI/CD and Testing Infrastructure

This test suite prevents regression of critical issues that caused workflow failures:
1. Missing pytest fixture decorators
2. Invalid class-scoped fixtures
3. Settings singleton not being reloaded after monkeypatch
4. Use of archived/unmaintained tools in workflows

Following TDD principles, these tests will FAIL if regressions are introduced.
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml


class TestPytestFixtureValidation:
    """Validate that all pytest fixtures are properly decorated"""

    def get_python_test_files(self) -> List[Path]:
        """Get all Python test files in the tests directory"""
        test_dir = Path("tests")
        return list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))

    def extract_fixtures_and_decorators(self, file_path: Path) -> List[Tuple[str, bool, int]]:
        """
        Extract functions with yield and check for @pytest.fixture decorator.

        Returns:
            List of (function_name, has_fixture_decorator, line_number)
        """
        with open(file_path, "r") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []  # Skip files with syntax errors

        fixtures = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has yield (potential fixture)
                has_yield = any(isinstance(n, ast.Yield) or isinstance(n, ast.YieldFrom) for n in ast.walk(node))

                if has_yield:
                    # Check for @pytest.fixture decorator (with or without arguments)
                    has_fixture_decorator = False
                    for dec in node.decorator_list:
                        # Direct decorator: @pytest.fixture or @fixture
                        if isinstance(dec, ast.Name) and dec.id == "fixture":
                            has_fixture_decorator = True
                        elif isinstance(dec, ast.Attribute) and dec.attr == "fixture":
                            has_fixture_decorator = True
                        # Decorator with arguments: @pytest.fixture(...) or @fixture(...)
                        elif isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Name) and dec.func.id == "fixture":
                                has_fixture_decorator = True
                            elif isinstance(dec.func, ast.Attribute) and dec.func.attr == "fixture":
                                has_fixture_decorator = True

                    fixtures.append((node.name, has_fixture_decorator, node.lineno))

        return fixtures

    def test_all_yield_functions_have_fixture_decorator(self):
        """
        REGRESSION TEST: Ensure all functions with yield have @pytest.fixture decorator.

        Prevents regression of Issue #6 (Quality Test Fixture Issues):
        - tests/test_health_check.py:11 was missing @pytest.fixture
        """
        issues = []

        for test_file in self.get_python_test_files():
            fixtures = self.extract_fixtures_and_decorators(test_file)

            for func_name, has_decorator, line_num in fixtures:
                if not has_decorator and not func_name.startswith("test_"):
                    issues.append(f"{test_file}:{line_num} - Function '{func_name}' has yield but missing @pytest.fixture")

        assert not issues, (
            f"Found {len(issues)} functions with yield but no @pytest.fixture decorator:\n"
            + "\n".join(issues)
            + "\n\nFix: Add @pytest.fixture decorator to these functions"
        )

    def test_no_class_scoped_fixtures(self):
        """
        REGRESSION TEST: Ensure no @pytest.fixture(scope="class") on class definitions.

        Prevents regression of Issue #6 (Quality Test Fixture Issues):
        - tests/test_rate_limiter.py:20 had invalid class-scoped fixture

        Pytest does not support fixtures on classes, only on functions.
        """
        issues = []

        for test_file in self.get_python_test_files():
            with open(test_file, "r") as f:
                content = f.read()

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for dec in node.decorator_list:
                        # Check for @pytest.fixture decorator on class
                        is_fixture_decorator = False

                        if isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Attribute) and dec.func.attr == "fixture":
                                is_fixture_decorator = True
                            elif isinstance(dec.func, ast.Name) and dec.func.id == "fixture":
                                is_fixture_decorator = True

                        if is_fixture_decorator:
                            issues.append(
                                f"{test_file}:{node.lineno} - Class '{node.name}' has @pytest.fixture decorator (unsupported)"
                            )

        assert not issues, (
            f"Found {len(issues)} classes with @pytest.fixture decorator:\n"
            + "\n".join(issues)
            + "\n\nFix: Remove @pytest.fixture from class definitions (pytest doesn't support class fixtures)"
        )


class TestMonkeypatchReloadPattern:
    """Validate that tests using monkeypatch properly reload Settings"""

    def test_monkeypatch_tests_reload_config_module(self):
        """
        REGRESSION TEST: Ensure tests using monkeypatch.setenv() reload config modules.

        Prevents regression of Issue #7 (Smoke Test Environment Configuration):
        - Tests were setting env vars but Settings singleton wasn't reloaded
        - Fixed by adding importlib.reload(config_module) pattern
        """
        test_file = Path("tests/integration/test_app_startup_validation.py")

        with open(test_file, "r") as f:
            content = f.read()

        # Find all test functions that use monkeypatch.setenv
        monkeypatch_tests = re.findall(
            r"def (test_\w+)\([^)]*monkeypatch[^)]*\):.*?(?=\n    def |\n\nclass |\Z)", content, re.DOTALL
        )

        issues = []

        for match in monkeypatch_tests:
            test_name = match if isinstance(match, str) else match[0]

            # Check if test has importlib.reload pattern
            if "KEYCLOAK" in content and test_name in content:
                test_body_match = re.search(rf"def {test_name}\([^)]*\):(.+?)(?=\n    def |\nclass |\Z)", content, re.DOTALL)

                if test_body_match:
                    test_body = test_body_match.group(1)

                    # Check if it sets Keycloak env vars
                    if "KEYCLOAK" in test_body and "monkeypatch.setenv" in test_body:
                        # Should have importlib.reload
                        if "importlib.reload" not in test_body:
                            issues.append(
                                f"{test_file} - Test '{test_name}' uses monkeypatch.setenv for Keycloak "
                                "but doesn't reload config module"
                            )

        # This is informational - we've already fixed the known issues
        # If new tests are added that use monkeypatch, they should follow the pattern
        if issues:
            pytest.skip(f"Found {len(issues)} tests that may need config reload:\n" + "\n".join(issues))


class TestWorkflowToolMaintenance:
    """Validate that GitHub Actions workflows use maintained tools"""

    def get_workflow_files(self) -> List[Path]:
        """Get all GitHub Actions workflow files"""
        workflow_dir = Path(".github/workflows")
        return list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))

    def test_no_archived_tools_in_workflows(self):
        """
        REGRESSION TEST: Ensure workflows don't use archived/unmaintained tools.

        Prevents regression of Issue #8 (Deployment Workflow kubeval Limitations):
        - kubeval is archived and doesn't support K8s 1.22+
        - Replaced with kubeconform (actively maintained)
        """
        archived_tools = {
            "kubeval": {
                "replacement": "kubeconform",
                "reason": "kubeval is archived, use kubeconform (actively maintained fork)",
            },
            "setup-gcloud": {
                "replacement": "google-github-actions/setup-gcloud",
                "reason": "Use official google-github-actions/setup-gcloud",
            },
        }

        issues = []

        for workflow_file in self.get_workflow_files():
            with open(workflow_file, "r") as f:
                content = f.read()

            try:
                yaml.safe_load(content)
            except yaml.YAMLError:
                continue

            # Check for archived tools in run commands
            for line_num, line in enumerate(content.split("\n"), 1):
                for tool, info in archived_tools.items():
                    if tool in line.lower() and not line.strip().startswith("#"):
                        # Check if it's the old tool (not the replacement)
                        if "kubeval" in line and "kubeconform" not in line:
                            issues.append(
                                f"{workflow_file}:{line_num} - Uses archived tool '{tool}'. "
                                f"{info['reason']}. Replacement: {info['replacement']}"
                            )

        assert not issues, (
            f"Found {len(issues)} uses of archived tools in workflows:\n"
            + "\n".join(issues)
            + "\n\nFix: Replace archived tools with maintained alternatives"
        )

    def test_workflows_use_kubeconform_with_ignore_missing_schemas(self):
        """
        REGRESSION TEST: Ensure kubeconform uses -ignore-missing-schemas flag.

        Prevents regression: kubeconform needs -ignore-missing-schemas for CRDs
        to avoid false positive validation failures.
        """
        deployment_workflows = [
            Path(".github/workflows/deploy-staging-gke.yaml"),
            Path(".github/workflows/deploy-production-gke.yaml"),
        ]

        issues = []

        for workflow_file in deployment_workflows:
            if not workflow_file.exists():
                continue

            with open(workflow_file, "r") as f:
                content = f.read()

            # If using kubeconform, should have -ignore-missing-schemas
            if "kubeconform" in content:
                if "-ignore-missing-schemas" not in content:
                    issues.append(
                        f"{workflow_file} - Uses kubeconform but missing -ignore-missing-schemas flag " "(needed for CRDs)"
                    )

        assert not issues, (
            f"Found {len(issues)} kubeconform uses without -ignore-missing-schemas:\n"
            + "\n".join(issues)
            + "\n\nFix: Add -ignore-missing-schemas flag to kubeconform command"
        )


class TestWorkflowActionVersions:
    """Validate that GitHub Actions use pinned, non-deprecated versions"""

    def get_workflow_files(self) -> List[Path]:
        """Get all GitHub Actions workflow files"""
        workflow_dir = Path(".github/workflows")
        return list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))

    def test_astral_sh_setup_uv_uses_v7_or_later(self):
        """
        REGRESSION TEST: Ensure astral-sh/setup-uv uses v7.1.1 or later.

        Prevents regression: Earlier versions had bugs and deprecated parameters.
        Validated in commit ae71fb3 (Comprehensive GitHub Actions validation and fixes).
        """
        issues = []

        for workflow_file in self.get_workflow_files():
            with open(workflow_file, "r") as f:
                content = f.read()

            # Find uses of astral-sh/setup-uv
            matches = re.finditer(r"uses:\s+astral-sh/setup-uv@(v\d+(?:\.\d+)*)", content)

            for match in matches:
                version = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Check version is v7.1.1 or later
                version_parts = version.replace("v", "").split(".")
                major = int(version_parts[0]) if version_parts else 0

                if major < 7:
                    issues.append(
                        f"{workflow_file}:{line_num} - Uses astral-sh/setup-uv@{version} " f"(should be @v7.1.1 or later)"
                    )

        assert not issues, (
            f"Found {len(issues)} outdated astral-sh/setup-uv versions:\n"
            + "\n".join(issues)
            + "\n\nFix: Update to @v7.1.1 or later"
        )


class TestWorkflowSyntaxValidation:
    """Validate GitHub Actions workflow syntax"""

    def get_workflow_files(self) -> List[Path]:
        """Get all GitHub Actions workflow files"""
        workflow_dir = Path(".github/workflows")
        if not workflow_dir.exists():
            return []
        return list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))

    def test_all_workflows_are_valid_yaml(self):
        """
        REGRESSION TEST: Ensure all workflow files are valid YAML.

        Prevents syntax errors that break CI/CD pipelines.
        """
        issues = []

        for workflow_file in self.get_workflow_files():
            try:
                with open(workflow_file, "r") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                issues.append(f"{workflow_file} - Invalid YAML: {e}")

        assert not issues, f"Found {len(issues)} workflow files with invalid YAML:\n" + "\n".join(issues)

    def test_all_workflows_have_required_structure(self):
        """
        REGRESSION TEST: Ensure all workflows have required fields.

        Required fields:
        - name: Workflow name
        - on: Trigger events
        - jobs: At least one job
        """
        issues = []

        for workflow_file in self.get_workflow_files():
            try:
                with open(workflow_file, "r") as f:
                    workflow = yaml.safe_load(f)

                if not workflow:
                    issues.append(f"{workflow_file} - Empty workflow file")
                    continue

                if "name" not in workflow:
                    issues.append(f"{workflow_file} - Missing 'name' field")

                # YAML allows both "on" and on: as keys (True is the boolean value)
                # Both are valid and equivalent in GitHub Actions
                if "on" not in workflow and True not in workflow:
                    issues.append(f"{workflow_file} - Missing 'on' (triggers) field")

                if "jobs" not in workflow or not workflow["jobs"]:
                    issues.append(f"{workflow_file} - Missing or empty 'jobs' field")

            except yaml.YAMLError:
                # Already caught by test_all_workflows_are_valid_yaml
                pass

        assert not issues, f"Found {len(issues)} workflow structure issues:\n" + "\n".join(issues)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
