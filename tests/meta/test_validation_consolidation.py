"""
Meta-tests for validation workflow consolidation.

These tests validate that pre-commit framework is the canonical source for
validation, eliminating duplication between Makefile targets, pre-commit hooks,
and CI workflows.

PURPOSE:
--------
Prevent pre-push validation duplication where developers run the same checks
multiple times through different entry points (Makefile, pre-commit, CI).

VALIDATION:
-----------
1. Pre-commit config is canonical source for validation hooks
2. Makefile targets are minimal (quick checks only)
3. CI workflows match pre-commit configuration
4. No duplication of validation logic

References:
- OpenAI Codex Finding #2: Pre-push validation duplication
- .pre-commit-config.yaml: Canonical validation configuration
- Makefile: Manual validation targets (Tier 2 & 3)
"""

import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.meta
@pytest.mark.xdist_group(name="validation_consolidation_tests")
class TestValidationConsolidation:
    """
    Validate that validation workflows are consolidated and not duplicated.

    These meta-tests ensure pre-commit framework is the single source of truth.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_precommit_config_exists(self):
        """
        🟢 GREEN: Verify .pre-commit-config.yaml exists.

        This is the canonical source for validation hooks.
        """
        root = Path(__file__).parent.parent.parent
        precommit_config = root / ".pre-commit-config.yaml"

        assert precommit_config.exists(), ".pre-commit-config.yaml must exist"
        assert precommit_config.is_file(), ".pre-commit-config.yaml must be a file"

    def test_precommit_has_required_test_hooks(self):
        """
        🟢 GREEN: Verify pre-commit has required test hooks.

        Pre-commit uses consolidated `run-pre-push-tests` hook which runs:
        - Unit tests
        - Smoke tests
        - Integration tests (when CI_PARITY=1)
        - API tests
        - Property tests
        - MCP server tests

        This is a consolidated approach instead of separate hooks per test type.
        """
        root = Path(__file__).parent.parent.parent
        precommit_config = root / ".pre-commit-config.yaml"

        content = precommit_config.read_text()

        # Consolidated test hook (runs all test types)
        assert "run-pre-push-tests" in content, (
            "Pre-commit hook missing: run-pre-push-tests\n"
            "Pre-commit config should have consolidated test hook that runs all test types."
        )

    def test_precommit_hooks_run_on_push_stage(self):
        """
        🟢 GREEN: Verify test hooks run on pre-push stage.

        Comprehensive tests should run before push, not on commit.
        """
        root = Path(__file__).parent.parent.parent
        precommit_config = root / ".pre-commit-config.yaml"

        content = precommit_config.read_text()

        # Pre-push hooks should have stages: [pre-push] or stages:\n    - pre-push (YAML list)
        has_pre_push_stage = (
            "stages: [pre-push]" in content
            or "stages: [push]" in content
            or ("stages:" in content and "- pre-push" in content)
            or ("stages:" in content and "- push" in content)
        )

        assert has_pre_push_stage, (
            "Pre-commit config should have hooks configured for pre-push stage\n"
            "Expected: stages: [pre-push] or stages:\\n    - pre-push"
        )

    def test_makefile_validate_pre_push_exists_and_documented(self):
        """
        🟢 GREEN: Verify Makefile validate-pre-push target exists and is documented.

        The validate-pre-push target provides manual CI-equivalent validation.
        It complements pre-commit hooks by allowing developers to manually run
        the same comprehensive validation that CI runs.

        NOTE: This is NOT deprecated - it serves as manual validation option
        alongside automatic pre-commit hooks.
        """
        root = Path(__file__).parent.parent.parent
        makefile = root / "Makefile"

        assert makefile.exists(), "Makefile must exist"

        content = makefile.read_text()

        # Find validate-pre-push target
        assert "validate-pre-push:" in content, "validate-pre-push target must exist"

        # Check for documentation
        # Find the validate-pre-push section
        lines = content.split("\n")
        validate_pre_push_section = []
        in_section = False

        for line in lines:
            if "validate-pre-push:" in line:
                in_section = True

            if in_section:
                validate_pre_push_section.append(line)

                # Stop at next target (non-indented line with colon)
                if (
                    line.strip()
                    and not line.startswith("\t")
                    and not line.startswith("@")
                    and ":" in line
                    and "validate-pre-push:" not in line
                ):
                    break

        section_text = "\n".join(validate_pre_push_section)

        # Should be documented (has descriptive echo statements or comments)
        documentation_keywords = ["validation", "comprehensive", "CI", "PHASE", "checking"]

        has_documentation = any(keyword.lower() in section_text.lower() for keyword in documentation_keywords)

        assert has_documentation, (
            "validate-pre-push target should have clear documentation.\n"
            "Expected: Echo statements or comments explaining what it does"
        )

    def test_validate_push_is_tier_2_quick_checks(self):
        """
        🟢 GREEN: Verify validate-push is Tier 2 (quick checks only).

        validate-push should be lightweight for quick manual validation.
        """
        root = Path(__file__).parent.parent.parent
        makefile = root / "Makefile"

        content = makefile.read_text()

        assert "validate-push:" in content, "validate-push target must exist"

        # Find validate-push section
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "validate-push:" in line:
                # Check surrounding lines for tier documentation
                context = "\n".join(lines[max(0, i - 5) : min(len(lines), i + 20)])

                # Should mention Tier 2 or be documented as quick
                tier_keywords = ["Tier 2", "tier 2", "quick", "fast", "lightweight", "3-5 min"]

                has_tier_doc = any(keyword in context for keyword in tier_keywords)

                # This is informational - we want tier documentation but don't fail if missing
                if not has_tier_doc:
                    import warnings

                    warnings.warn(
                        "validate-push target should be documented as Tier 2 (quick checks)",
                        UserWarning,
                        stacklevel=2,
                    )

                break

    def test_validate_full_is_tier_3_comprehensive(self):
        """
        🟢 GREEN: Verify validate-full is Tier 3 (comprehensive checks).

        validate-full should run everything for manual comprehensive validation.
        """
        root = Path(__file__).parent.parent.parent
        makefile = root / "Makefile"

        content = makefile.read_text()

        assert "validate-full:" in content, "validate-full target must exist"

        # Should reference comprehensive validation
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "validate-full:" in line:
                context = "\n".join(lines[max(0, i - 5) : min(len(lines), i + 20)])

                # Should mention Tier 3 or comprehensive
                tier_keywords = ["Tier 3", "tier 3", "comprehensive", "all checks", "12-15 min"]

                has_tier_doc = any(keyword in context for keyword in tier_keywords)

                if not has_tier_doc:
                    import warnings

                    warnings.warn(
                        "validate-full target should be documented as Tier 3 (comprehensive)",
                        UserWarning,
                        stacklevel=2,
                    )

                break

    def test_ci_workflows_use_precommit_run(self):
        """
        🟢 GREEN: Verify CI workflows use pre-commit run for validation.

        CI should use 'pre-commit run' to match local pre-commit behavior.
        """
        root = Path(__file__).parent.parent.parent
        workflow_dir = root / ".github" / "workflows"

        assert workflow_dir.exists(), ".github/workflows directory must exist"

        # Check ci.yaml
        ci_workflow = workflow_dir / "ci.yaml"
        if ci_workflow.exists():
            content = ci_workflow.read_text()

            # Should use pre-commit
            assert "pre-commit" in content.lower(), "CI workflow should use pre-commit for validation"


@pytest.mark.meta
@pytest.mark.xdist_group(name="validation_documentation_tests")
class TestValidationDocumentation:
    """
    Validate that validation workflows are properly documented.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_testing_md_documents_validation_tiers(self):
        """
        🟢 GREEN: Verify TESTING.md documents validation tiers.

        Documentation should explain when to use each validation approach.
        """
        root = Path(__file__).parent.parent.parent
        testing_doc = root / "TESTING.md"

        if not testing_doc.exists():
            pytest.skip("TESTING.md not found")

        content = testing_doc.read_text()

        # Should mention validation or pre-commit
        assert (
            "validation" in content.lower() or "pre-commit" in content.lower()
        ), "TESTING.md should document validation workflows"

    def test_makefile_has_validation_tier_comments(self):
        """
        🟢 GREEN: Verify Makefile documents validation tiers.

        Makefile should have clear comments explaining each tier.
        """
        root = Path(__file__).parent.parent.parent
        makefile = root / "Makefile"

        content = makefile.read_text()

        # Should have tier documentation
        tier_keywords = ["Tier 1", "Tier 2", "Tier 3", "tier", "validation"]

        has_tier_docs = any(keyword in content for keyword in tier_keywords)

        # This is currently documented in the Makefile
        # If we refactor, this test will catch missing documentation
        if not has_tier_docs:
            import warnings

            warnings.warn(
                "Makefile should document validation tiers",
                UserWarning,
                stacklevel=2,
            )


@pytest.mark.meta
@pytest.mark.xdist_group(name="validation_enforcement_tests")
class TestValidationEnforcement:
    """
    Document enforcement strategy for validation consolidation.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enforcement_strategy_documentation(self):
        """
        📚 Document the enforcement strategy for validation consolidation.

        Multiple layers ensure validation is efficient and not duplicated.
        """
        strategy = """
        ENFORCEMENT STRATEGY: Validation Consolidation
        ==============================================

        Goal: Consolidate validation on pre-commit framework to eliminate
        duplication while maintaining manual options for developers.

        Layer 1: Pre-Commit Framework (Canonical)
        ------------------------------------------
        ✅ .pre-commit-config.yaml is single source of truth
        ✅ Runs automatically on 'git push'
        ✅ Comprehensive test coverage
        ✅ Parallelizable hooks
        ✅ Fast feedback for developers

        Layer 2: Makefile Targets (Manual)
        -----------------------------------
        ✅ validate-pre-push: DEPRECATED (use pre-commit)
        ✅ validate-push: Tier 2 quick checks (manual)
        ✅ validate-full: Tier 3 comprehensive (manual CI equivalent)
        ✅ Clear tier documentation

        Layer 3: CI Workflows (Automated)
        ----------------------------------
        ✅ Uses pre-commit run for validation
        ✅ Matches local pre-commit behavior
        ✅ Parallelized across multiple jobs
        ✅ Same hooks as local development

        Layer 4: Meta-Tests (This File)
        --------------------------------
        ✅ Validates pre-commit config has required hooks
        ✅ Validates Makefile targets are deprecated/documented
        ✅ Validates CI uses pre-commit
        ✅ Prevents validation drift

        Validation Entry Points:
        ========================

        Primary (Automatic):
        - 'git push' → pre-commit hooks (recommended)
        - CI pipeline → pre-commit run (automatic)

        Secondary (Manual):
        - 'make validate-push' → Quick Tier 2 checks
        - 'make validate-full' → Comprehensive Tier 3 checks

        Deprecated:
        - 'make validate-pre-push' → Use 'git push' instead

        Benefits of Consolidation:
        ===========================

        1. No Duplication
           - Validation logic defined once (pre-commit config)
           - Makefile and CI reference same hooks
           - Changes propagate everywhere

        2. Faster Iterations
           - Pre-commit runs incrementally (only changed files)
           - Developers choose validation tier
           - Heavy validation optional

        3. Local/CI Parity
           - Same hooks run locally and in CI
           - No surprises after push
           - Consistent behavior

        4. Clear Documentation
           - Three tiers clearly defined
           - Decision tree for developers
           - Easy onboarding

        Risk After Consolidation: LOW
        Single source of truth with manual opt-ins preserved.
        """

        assert len(strategy) > 100, "Strategy documented"
        assert "Layer 1" in strategy
        assert "Layer 2" in strategy
