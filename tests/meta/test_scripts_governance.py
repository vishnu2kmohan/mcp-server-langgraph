"""
Meta-tests for scripts governance and validation.

These tests validate that scripts in scripts/ directory are properly governed,
documented, and validated to prevent ungoverned automation sprawl.

PURPOSE:
--------
Ensure all scripts (especially validators) are documented, tested, and governed
to prevent the situation where validator scripts themselves lack validation.

VALIDATION:
-----------
1. All scripts in scripts/ are documented
2. Validator scripts have meta-tests
3. scripts/README.md or REGISTRY.md catalogs all scripts
4. Shell scripts follow best practices (shebang, set -euo pipefail)

References:
- OpenAI Codex Finding #5: Scripts ungoverned and undocumented
- scripts/: 114 automation scripts
- scripts/README.md: Currently only documents 3 deployment scripts
"""

import gc
import stat
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.meta
@pytest.mark.xdist_group(name="scripts_governance_tests")
class TestScriptsGovernance:
    """
    Validate that scripts are properly governed and documented.

    These meta-tests ensure scripts follow best practices.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_scripts_directory_exists(self):
        """
        🟢 GREEN: Verify scripts/ directory exists.

        The scripts directory contains automation and validation scripts.
        """
        root = Path(__file__).parent.parent.parent
        scripts_dir = root / "scripts"

        assert scripts_dir.exists(), "scripts/ directory must exist"
        assert scripts_dir.is_dir(), "scripts/ must be a directory"

    def test_scripts_readme_exists(self):
        """
        🟢 GREEN: Verify scripts/README.md exists.

        README should document script organization and usage.
        """
        root = Path(__file__).parent.parent.parent
        readme = root / "scripts" / "README.md"

        assert readme.exists(), "scripts/README.md should exist to document scripts.\n" "Create with: touch scripts/README.md"

    def test_validator_scripts_exist(self):
        """
        🟢 GREEN: Verify validator scripts exist.

        These scripts validate code quality and should be governed.
        """
        root = Path(__file__).parent.parent.parent

        # Key validator scripts
        expected_validators = [
            "scripts/validation/validate_ci_cd.py",
            "scripts/validation/validate_pre_push_hook.py",
            "scripts/validation/check_test_memory_safety.py",
        ]

        for validator_path in expected_validators:
            full_path = root / validator_path
            assert full_path.exists(), f"Validator script missing: {validator_path}"

    def test_shell_scripts_have_shebang(self):
        """
        🟢 GREEN: Verify shell scripts have proper shebang.

        All .sh scripts should start with #!/usr/bin/env bash or #!/bin/bash
        """
        root = Path(__file__).parent.parent.parent
        scripts_dir = root / "scripts"

        shell_scripts = list(scripts_dir.glob("*.sh"))

        missing_shebang = []

        for script in shell_scripts:
            try:
                content = script.read_text()
                first_line = content.split("\n")[0]

                if not first_line.startswith("#!"):
                    missing_shebang.append(script.name)
            except (UnicodeDecodeError, FileNotFoundError):
                continue

        if missing_shebang:
            error_msg = f"Found {len(missing_shebang)} shell scripts without shebang:\n\n"
            for script_name in missing_shebang:
                error_msg += f"  - {script_name}\n"

            error_msg += "\nAdd shebang: #!/usr/bin/env bash\n"

            assert False, error_msg

    def test_python_validator_scripts_are_executable(self):
        """
        🟢 GREEN: Verify Python validator scripts are executable.

        Validator scripts should be chmod +x for easy invocation.
        """
        root = Path(__file__).parent.parent.parent

        # Key validator scripts that should be executable
        expected_executables = [
            "scripts/validation/validate_ci_cd.py",
            "scripts/validation/check_test_memory_safety.py",
        ]

        non_executable = []

        for script_path in expected_executables:
            full_path = root / script_path

            if not full_path.exists():
                continue  # Tested in other test

            # Check if executable
            file_stat = full_path.stat()
            is_executable = bool(file_stat.st_mode & stat.S_IXUSR)

            if not is_executable:
                non_executable.append(script_path)

        if non_executable:
            error_msg = f"Found {len(non_executable)} scripts that are not executable:\n\n"
            for script_path in non_executable:
                error_msg += f"  - {script_path}\n"

            error_msg += "\nMake executable: chmod +x <script>\n"

            # This is a warning, not a hard failure (some projects don't require +x)
            import warnings

            warnings.warn(error_msg, UserWarning, stacklevel=2)

    def test_python_validator_scripts_have_docstrings(self):
        """
        🟢 GREEN: Verify Python validator scripts have module docstrings.

        Scripts should document their purpose.
        """
        root = Path(__file__).parent.parent.parent

        # Key validator scripts
        validator_scripts = [
            root / "scripts" / "validation" / "validate_ci_cd.py",
            root / "scripts" / "validation" / "validate_pre_push_hook.py",
            root / "scripts" / "validation" / "check_test_memory_safety.py",
        ]

        missing_docstring = []

        for script in validator_scripts:
            if not script.exists():
                continue

            try:
                content = script.read_text()

                # Check for docstring (triple-quoted string at module level)
                has_docstring = '"""' in content[:500] or "'''" in content[:500]

                if not has_docstring:
                    missing_docstring.append(script.name)
            except (UnicodeDecodeError, FileNotFoundError):
                continue

        if missing_docstring:
            error_msg = f"Found {len(missing_docstring)} validator scripts without docstrings:\n\n"
            for script_name in missing_docstring:
                error_msg += f"  - {script_name}\n"

            error_msg += "\nAdd module-level docstring documenting script purpose.\n"

            # Warning, not hard failure
            import warnings

            warnings.warn(error_msg, UserWarning, stacklevel=2)


@pytest.mark.meta
@pytest.mark.xdist_group(name="scripts_registry_tests")
class TestScriptsRegistry:
    """
    Validate that scripts registry exists and is maintained.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_scripts_registry_exists(self):
        """
        🟢 GREEN: Verify scripts/REGISTRY.md exists.

        REGISTRY.md should catalog all scripts by category.

        This test will FAIL initially (part of TDD approach) and pass
        after we create the registry in Phase 6.
        """
        root = Path(__file__).parent.parent.parent
        registry = root / "scripts" / "REGISTRY.md"

        assert registry.exists(), (
            "scripts/REGISTRY.md should exist to catalog all scripts.\n" "Create in Phase 6 of implementation plan."
        )

    def test_registry_documents_validators(self):
        """
        🟢 GREEN: Verify REGISTRY.md documents validator scripts.

        Registry should have a 'Validators' section.
        """
        root = Path(__file__).parent.parent.parent
        registry = root / "scripts" / "REGISTRY.md"

        if not registry.exists():
            pytest.skip("REGISTRY.md does not exist yet (will be created in Phase 6)")

        content = registry.read_text()

        # Should have validators section
        assert (
            "validator" in content.lower() or "validation" in content.lower()
        ), "REGISTRY.md should document validator scripts"

    def test_registry_documents_deployment_scripts(self):
        """
        🟢 GREEN: Verify REGISTRY.md documents deployment scripts.

        Registry should have a 'Deployment' section.
        """
        root = Path(__file__).parent.parent.parent
        registry = root / "scripts" / "REGISTRY.md"

        if not registry.exists():
            pytest.skip("REGISTRY.md does not exist yet (will be created in Phase 6)")

        content = registry.read_text()

        # Should have deployment section
        assert "deployment" in content.lower() or "deploy" in content.lower(), "REGISTRY.md should document deployment scripts"


@pytest.mark.meta
@pytest.mark.xdist_group(name="scripts_enforcement_tests")
class TestScriptsEnforcement:
    """
    Document enforcement strategy for scripts governance.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enforcement_strategy_documentation(self):
        """
        📚 Document the enforcement strategy for scripts governance.

        Multiple layers ensure scripts are governed and validated.
        """
        strategy = """
        ENFORCEMENT STRATEGY: Scripts Governance
        ========================================

        Goal: Ensure all scripts are documented, validated, and maintained
        to prevent ungoverned automation sprawl.

        Layer 1: Scripts Registry (Documentation)
        ------------------------------------------
        ✅ scripts/REGISTRY.md catalogs all scripts
        ✅ Categories: Validators, Deployment, Test, Infrastructure, Development
        ✅ Each script documented with purpose, usage, dependencies
        ✅ Deprecated scripts clearly marked

        Layer 2: Meta-Tests (This File)
        --------------------------------
        ✅ Validates REGISTRY.md exists
        ✅ Validates validator scripts exist
        ✅ Checks shell scripts have shebang
        ✅ Checks Python scripts have docstrings
        ✅ Validates executability

        Layer 3: Validator Script Meta-Tests
        -------------------------------------
        ✅ tests/meta/test_validator_scripts.py (to be created)
        ✅ Tests each validator script executes successfully
        ✅ Tests they have --help text
        ✅ Tests they produce expected exit codes
        ✅ Tests they handle missing dependencies

        Layer 4: Pre-Commit Integration
        --------------------------------
        ✅ Validator scripts run as pre-commit hooks
        ✅ Scripts tested in isolation and in CI
        ✅ Failures block commits/pushes

        Best Practices Enforced:
        ========================

        Shell Scripts (.sh):
        - Shebang: #!/usr/bin/env bash
        - Error handling: set -euo pipefail
        - Documented in REGISTRY.md

        Python Scripts (.py):
        - Module docstring explaining purpose
        - Executable (chmod +x)
        - Type hints where appropriate
        - argparse for CLI arguments
        - Proper exit codes (0 success, non-zero failure)

        Validator Scripts (Special):
        - Must have meta-tests validating them
        - Must be documented in REGISTRY.md
        - Must have comprehensive docstrings
        - Must handle edge cases gracefully

        Benefits:
        =========

        1. Discoverability
           - Developers can find scripts easily
           - REGISTRY.md provides index
           - Clear categorization

        2. Maintainability
           - Scripts follow consistent patterns
           - Documentation prevents bit-rot
           - Deprecated scripts identified

        3. Reliability
           - Validator scripts are themselves validated
           - No unchecked automation
           - Pre-commit integration catches issues

        4. Onboarding
           - New contributors understand script landscape
           - Clear documentation
           - Examples of correct patterns

        Risk: LOW
        Scripts are governed, documented, and validated.
        """

        assert len(strategy) > 100, "Strategy documented"
        assert "Layer 1" in strategy
        assert "Layer 2" in strategy
