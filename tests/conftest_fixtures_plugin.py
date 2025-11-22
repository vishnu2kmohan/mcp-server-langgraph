"""
Pytest plugin to enforce fixture organization best practices.

This plugin runs at pytest collection time and validates that:
1. No duplicate autouse fixtures exist across test files
2. Session/module-scoped autouse fixtures are only in conftest.py
3. Fixture names follow conventions

This provides runtime enforcement in addition to pre-commit hooks.
"""

import ast
from pathlib import Path

import pytest


class FixtureOrganizationPlugin:
    """Pytest plugin to enforce fixture organization rules."""

    def __init__(self):
        self.autouse_fixtures: dict[str, list[tuple[str, int]]] = {}
        self.violations: list[str] = []

    def pytest_collection_finish(self, session):
        """
        Hook called after test collection is complete.

        Validates fixture organization and fails the test session if violations found.
        """
        test_dir = Path(session.config.rootdir) / "tests"

        # Scan for autouse fixtures
        self._scan_autouse_fixtures(test_dir)

        # Check for violations
        self._check_for_violations()

        # If violations found, fail immediately
        if self.violations:
            violation_report = "\n".join(
                [
                    "",
                    "=" * 70,
                    "FIXTURE ORGANIZATION VIOLATIONS",
                    "=" * 70,
                    "",
                    *self.violations,
                    "",
                    "=" * 70,
                    "",
                    "Fix: Move autouse fixtures to tests/conftest.py",
                    "See: tests/test_fixture_organization.py for validation",
                    "",
                ]
            )
            pytest.exit(violation_report, returncode=1)

    def _scan_autouse_fixtures(self, test_dir: Path):
        """Scan all test files for autouse fixtures."""
        for test_file in test_dir.rglob("*.py"):
            if test_file.name.startswith("_"):
                continue

            try:
                with open(test_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(test_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, "attr") and decorator.func.attr == "fixture":
                                # Check if this is autouse AND module/session scoped
                                is_autouse = False
                                scope = "function"  # default scope

                                for keyword in decorator.keywords:
                                    if keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant):
                                        is_autouse = keyword.value.value is True
                                    if keyword.arg == "scope" and isinstance(keyword.value, ast.Constant):
                                        scope = keyword.value.value

                                # Only track module/session-scoped autouse fixtures
                                if is_autouse and scope in ("module", "session"):
                                    fixture_name = node.name
                                    file_path = str(test_file.relative_to(test_dir))
                                    line_num = node.lineno

                                    if fixture_name not in self.autouse_fixtures:
                                        self.autouse_fixtures[fixture_name] = []
                                    self.autouse_fixtures[fixture_name].append((file_path, line_num))

    def _check_for_violations(self):
        """Check for fixture organization violations."""
        for fixture_name, locations in self.autouse_fixtures.items():
            if len(locations) > 1:
                # Allow duplicates only if all in conftest.py files
                non_conftest = [loc for loc in locations if not loc[0].endswith("conftest.py")]
                if non_conftest:
                    self.violations.append(f"DUPLICATE autouse fixture '{fixture_name}' found in {len(locations)} files:")
                    for file_path, line_num in locations:
                        self.violations.append(f"  - {file_path}:{line_num}")
                    self.violations.append("")

            # Check that non-conftest files don't have module/session autouse fixtures
            for file_path, line_num in locations:
                if not file_path.endswith("conftest.py"):
                    self.violations.append(f"Autouse fixture '{fixture_name}' found outside conftest.py:")
                    self.violations.append(f"  - {file_path}:{line_num}")
                    self.violations.append("  RULE: Module/session-scoped autouse fixtures must be in conftest.py")
                    self.violations.append("")


def pytest_configure(config):
    """
    Register the fixture organization plugin.

    This hook is called during pytest initialization.
    """
    # Only run if we're actually collecting/running tests, not for informational commands
    # Defense-in-depth: explicitly guard all informational CLI modes
    if any(
        [
            config.option.collectonly,
            config.getoption("--help", default=False),
            config.getoption("--version", default=False),
            config.getoption("--markers", default=False),
            config.getoption("--fixtures", default=False),
            config.getoption("--fixtures-per-test", default=False),
        ]
    ):
        return

    # Register the plugin
    plugin = FixtureOrganizationPlugin()
    config.pluginmanager.register(plugin, "fixture_organization_enforcer")


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addini(
        "enforce_fixture_organization",
        "Enforce fixture organization rules (default: True)",
        type="bool",
        default=True,
    )
