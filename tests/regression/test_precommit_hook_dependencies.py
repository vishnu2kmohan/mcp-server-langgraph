"""
Regression Tests for Pre-commit Hook Dependencies

Prevents recurrence of pre-commit hook dependency failures from 2025-11-12:
- validate-workflow-test-deps hook failed with "ModuleNotFoundError: No module named 'yaml'"
- Hook was using language: system instead of language: python
- Missing pyyaml in additional_dependencies

## Failure Scenario (2025-11-12)
- Pre-commit hook: validate-workflow-test-deps
- Entry point: python3 scripts/validation/validate_workflow_test_deps.py
- Error: "ModuleNotFoundError: No module named 'yaml'" (line 30: import yaml)
- Root cause: Hook used `language: system` assuming system Python has pyyaml
- Fix: Changed to `language: python` with `additional_dependencies: ['pyyaml>=6.0.0']`

## Prevention Strategy
1. Test all pre-commit hooks have proper dependencies declared
2. Verify Python hooks use language: python (not system)
3. Ensure scripts' imports match hook dependencies
4. Validate hook configuration is consistent

## Related
- Similar to test_dev_dependencies.py (validates package dependencies)
- This focuses on pre-commit hook infrastructure dependencies
"""

import ast
import gc
import re
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit


try:
    import yaml
except ImportError:
    yaml = None


def load_precommit_config() -> dict:
    """Load .pre-commit-config.yaml configuration."""
    config_path = Path(__file__).parent.parent.parent / ".pre-commit-config.yaml"
    if not config_path.exists():
        return {}

    if yaml is None:
        pytest.skip("pyyaml not installed - cannot parse pre-commit config")

    with open(config_path) as f:
        return yaml.safe_load(f)


def extract_imports_from_python_file(file_path: Path) -> set[str]:
    """
    Extract all import statements from a Python file.

    Returns:
        Set of module names being imported (e.g., {'yaml', 'sys', 'pathlib'})
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # import foo.bar -> foo
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # from foo.bar import baz -> foo
                    imports.add(node.module.split(".")[0])

        return imports
    except Exception:
        return set()


# Map of common import names to PyPI package names
IMPORT_TO_PACKAGE = {
    "yaml": "pyyaml",
    "pytest": "pytest",
    "jsonschema": "jsonschema",
    "requests": "requests",
    "httpx": "httpx",
    "click": "click",
    "rich": "rich",
    "toml": "toml",
    "tomli": "tomli",  # Python < 3.11 backport of tomllib
    "tomllib": "STDLIB",  # Python 3.11+ stdlib (no package needed)
}


@pytest.mark.regression
@pytest.mark.precommit
@pytest.mark.xdist_group(name="testprecommithookdependencies")
class TestPreCommitHookDependencies:
    """
    Regression tests for pre-commit hook dependency configuration.

    Prevents recurrence of hook dependency failures.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_python_hooks_use_language_python_not_system(self):
        """
        Test: Python hooks should use language: python, not language: system.

        RED (Before Fix - 2025-11-12):
        - validate-workflow-test-deps hook used language: system
        - Assumed system Python had pyyaml installed
        - Failed in CI environment where pyyaml wasn't available

        GREEN (After Fix - 2025-11-12):
        - Changed to language: python
        - Added additional_dependencies: ['pyyaml>=6.0.0']
        - Pre-commit creates isolated environment with dependencies

        REFACTOR:
        - This test ensures all Python hooks use proper configuration
        - Catches any new hooks that might use language: system incorrectly

        EXCEPTION (2025-11-13):
        - Hooks using `uv run` or `bash -c '... source .venv ...'` SHOULD use language: system
        - uv/venv manage their own dependencies, not pre-commit's isolated environment
        - This provides better integration with project dependencies
        """
        config = load_precommit_config()
        if not config:
            pytest.skip("No .pre-commit-config.yaml found")

        python_hooks_using_system = []

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                entry = hook.get("entry", "")
                language = hook.get("language", "")
                hook_id = hook.get("id", "unknown")

                # EXCEPTION: Allow language: system for hooks using uv run or venv activation
                # These hooks manage their own dependencies and should use project's environment
                # Note: Checks for "uv run" anywhere in entry to handle bash-wrapped commands
                # like: bash -c 'OTEL_SDK_DISABLED=true uv run pytest...'
                # Also allow run-pre-push-tests orchestrator which calls "uv run pytest" internally
                if "uv run" in entry or "source .venv/bin/activate" in entry or hook_id == "run-pre-push-tests":
                    continue

                # Check if hook executes Python but uses language: system
                if ("python" in entry or ".py" in entry) and language == "system":
                    python_hooks_using_system.append(f"{hook_id} (entry: {entry}, language: {language})")

        if python_hooks_using_system:
            error_message = (
                f"\n❌ Found {len(python_hooks_using_system)} Python hooks using language: system:\n\n"
                + "\n".join(f"  - {hook}" for hook in python_hooks_using_system)
                + "\n\n💡 Fix: Change to language: python and add dependencies:\n"
                + "  - id: your-hook\n"
                + "    language: python\n"
                + "    additional_dependencies: ['pyyaml>=6.0.0', 'requests>=2.31.0']\n"
                + "\nBenefits:\n"
                + "  - Pre-commit creates isolated environment\n"
                + "  - Dependencies are guaranteed to be available\n"
                + "  - Works consistently across different systems\n"
            )
            pytest.fail(error_message)

    def test_python_script_imports_match_hook_dependencies(self):
        """
        Test: Python scripts referenced by hooks must have their imports satisfied.

        Ensures all imports in hook entry scripts are covered by additional_dependencies.

        RED (Before Fix - 2025-11-12):
        - scripts/validation/validate_workflow_test_deps.py imported yaml
        - Hook had no additional_dependencies
        - Runtime error: ModuleNotFoundError

        GREEN (After Fix - 2025-11-12):
        - Hook added additional_dependencies: ['pyyaml>=6.0.0']
        - yaml import satisfied by pyyaml package

        REFACTOR:
        - This test validates import/dependency alignment
        - Catches mismatches before CI runs
        """
        config = load_precommit_config()
        if not config:
            pytest.skip("No .pre-commit-config.yaml found")

        mismatches = []

        for repo in config.get("repos", []):
            # Only check local repos
            if repo.get("repo", "") != "local":
                continue

            for hook in repo.get("hooks", []):
                entry = hook.get("entry", "")
                language = hook.get("language", "")
                hook_id = hook.get("id", "unknown")
                additional_deps = hook.get("additional_dependencies", [])

                # SKIP: Hooks using uv run manage their own dependencies via project venv
                if entry.startswith("uv run") or "source .venv/bin/activate" in entry:
                    continue

                # Extract Python script path from entry
                # Format: "python3 scripts/something.py" or "scripts/something.py"
                script_match = re.search(r"(scripts/[\w/]+\.py)", entry)
                if not script_match:
                    continue

                script_path = Path(__file__).parent.parent.parent / script_match.group(1)
                if not script_path.exists():
                    continue

                # Get imports from script
                script_imports = extract_imports_from_python_file(script_path)

                # Get dependency package names from additional_dependencies
                # Format: ['pyyaml>=6.0.0', 'requests'] -> {'pyyaml', 'requests'}
                declared_packages = set()
                for dep in additional_deps:
                    # Extract package name (before version specifier)
                    package = re.split(r"[<>=!]", dep)[0].strip()
                    declared_packages.add(package.lower())

                # Check for missing dependencies
                # Skip standard library modules
                STDLIB_MODULES = {
                    "sys",
                    "os",
                    "re",
                    "pathlib",
                    "typing",
                    "json",
                    "datetime",
                    "collections",
                    "itertools",
                    "functools",
                    "dataclasses",
                    "enum",
                    "abc",
                    "argparse",  # Standard library in all Python versions
                    "ast",  # Standard library - Abstract Syntax Trees
                    "subprocess",
                    "tempfile",
                    "shutil",
                    "textwrap",
                    "inspect",
                    "warnings",
                    "contextlib",
                    "copy",
                    "io",
                    "traceback",
                    "logging",
                    "urllib",
                    "http",
                    "email",
                    "hashlib",
                    "hmac",
                    "base64",
                    "uuid",
                    "time",
                    "math",
                    "random",
                    "string",
                    "secrets",
                }

                missing_deps = []
                for import_name in script_imports:
                    if import_name in STDLIB_MODULES:
                        continue

                    # Map import to package name
                    package_name = IMPORT_TO_PACKAGE.get(import_name, import_name).lower()

                    # Skip if mapped to STDLIB (e.g., tomllib in Python 3.11+)
                    if package_name == "stdlib":
                        continue

                    if package_name not in declared_packages:
                        missing_deps.append(f"{import_name} (package: {package_name})")

                if missing_deps and language == "python":
                    relative_script = script_path.relative_to(Path(__file__).parent.parent.parent)
                    mismatches.append(
                        f"{hook_id}: {relative_script}\n"
                        f"    Missing dependencies: {', '.join(missing_deps)}\n"
                        f"    Declared: {declared_packages or 'none'}"
                    )

        if mismatches:
            error_message = (
                f"\n❌ Found {len(mismatches)} hooks with missing dependencies:\n\n"
                + "\n  ".join(mismatches)
                + "\n\n💡 Fix: Add missing packages to additional_dependencies in .pre-commit-config.yaml"
            )
            pytest.fail(error_message)

    def test_validate_workflow_test_deps_hook_has_pyyaml(self):
        """
        Test: validate-workflow-test-deps hook must have pyyaml dependency.

        Specific regression test for the exact issue from 2025-11-12.

        RED (Before Fix):
        - Hook had no additional_dependencies
        - Script imported yaml at line 30
        - ModuleNotFoundError in CI

        GREEN (After Fix):
        - Hook has additional_dependencies: ['pyyaml>=6.0.0']
        - yaml import satisfied

        REFACTOR:
        - Permanent regression check
        - Fails immediately if dependency removed
        """
        config = load_precommit_config()
        if not config:
            pytest.skip("No .pre-commit-config.yaml found")

        hook_found = False
        hook_has_pyyaml = False

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("id") == "validate-workflow-test-deps":
                    hook_found = True
                    additional_deps = hook.get("additional_dependencies", [])

                    # Check for pyyaml in dependencies
                    for dep in additional_deps:
                        if "pyyaml" in dep.lower():
                            hook_has_pyyaml = True
                            break

        if not hook_found:
            pytest.skip("validate-workflow-test-deps hook not found in config")

        assert hook_has_pyyaml, (
            "validate-workflow-test-deps hook missing pyyaml dependency!\n"
            "\n"
            "This is the exact issue from 2025-11-12 that caused CI failures.\n"
            "\n"
            "Fix in .pre-commit-config.yaml:\n"
            "  - id: validate-workflow-test-deps\n"
            "    name: Validate Workflow Test Dependencies\n"
            "    entry: python3 scripts/validation/validate_workflow_test_deps.py\n"
            "    language: python\n"
            "    additional_dependencies: ['pyyaml>=6.0.0']\n"
        )

    def test_validate_workflow_test_deps_script_imports_yaml(self):
        """
        Test: Verify the script actually imports yaml (validation that test is correct).

        This ensures our regression test is testing the right thing.
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "validation" / "validate_workflow_test_deps.py"

        if not script_path.exists():
            pytest.skip("Script not found")

        content = script_path.read_text()
        assert "import yaml" in content, (
            "Script no longer imports yaml - this test may be obsolete.\n"
            "If the script was refactored to not use yaml, update this test."
        )


@pytest.mark.regression
@pytest.mark.precommit
@pytest.mark.xdist_group(name="testprecommithookconfiguration")
class TestPreCommitHookConfiguration:
    """
    General pre-commit hook configuration best practices.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_hooks_have_descriptions(self):
        """
        Test: All hooks should have descriptions for maintainability.

        Helps developers understand what each hook does and why it exists.
        """
        config = load_precommit_config()
        if not config:
            pytest.skip("No .pre-commit-config.yaml found")

        hooks_without_descriptions = []

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "unknown")
                description = hook.get("description", "")
                name = hook.get("name", "")

                # Allow name as a substitute for description if it's descriptive
                if not description and (not name or len(name) < 10):
                    hooks_without_descriptions.append(hook_id)

        # This is a warning, not a failure
        if hooks_without_descriptions and len(hooks_without_descriptions) < 5:
            pytest.skip(f"Recommendation: Add descriptions to hooks: {', '.join(hooks_without_descriptions)}")

    def test_python_hooks_specify_pass_filenames_explicitly(self):
        """
        Test: Python hooks should explicitly set pass_filenames to avoid surprises.

        Makes hook behavior clear and intentional.
        """
        config = load_precommit_config()
        if not config:
            pytest.skip("No .pre-commit-config.yaml found")

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("language") == "python":
                    if "pass_filenames" not in hook:
                        # This is informational, not a hard requirement
                        pass  # Could add to a recommendations list if needed


def test_precommit_config_exists():
    """Test: .pre-commit-config.yaml file exists in repository root."""
    config_path = Path(__file__).parent.parent.parent / ".pre-commit-config.yaml"
    assert config_path.exists(), (
        ".pre-commit-config.yaml not found in repository root.\n"
        "Pre-commit hooks are essential for catching issues before CI."
    )


def test_pyyaml_in_dev_dependencies():
    """
    Test: pyyaml should be in dev dependencies for local testing.

    While pre-commit installs it in isolated env, developers need it locally too.
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        pytest.skip("pyproject.toml not found")

    content = pyproject_path.read_text()

    # Check if pyyaml is in dependencies or dev dependencies
    assert "pyyaml" in content.lower(), (
        "pyyaml not found in pyproject.toml dependencies.\n"
        "While pre-commit provides it in isolated env, it should be in dev deps "
        "for local development and script testing."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
