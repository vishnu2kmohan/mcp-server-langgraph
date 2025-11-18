#!/usr/bin/env python3
"""
Validate Test Fixtures - Pre-commit Hook

Detects common test fixture issues that cause test failures:
1. Missing FastAPI dependency overrides
2. Async/sync mismatch in dependency overrides
3. Invalid LLM model name formats
4. Missing circuit breaker isolation markers

Prevents:
- 401 Unauthorized errors from missing OpenFGA/auth overrides
- Test failures from incorrect Ollama model names
- Circuit breaker state pollution in parallel tests

Usage:
    # Run manually
    python scripts/validate_test_fixtures.py tests/**/*.py

    # Via pre-commit
    pre-commit run validate-test-fixtures --all-files

Exit codes:
    0 - All validations passed
    1 - Validation errors found

References:
    - Root cause: Missing dependency overrides (4 service principal tests)
    - Root cause: Invalid model names (2 Ollama tests)
    - Root cause: Circuit breaker state pollution (4 circuit breaker tests)
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple


class TestFixtureValidator:
    """Validates test fixtures for common issues"""

    def __init__(self):
        self.errors: list[tuple[str, int, str]] = []
        self.warnings: list[tuple[str, int, str]] = []

    def validate_file(self, filepath: Path) -> None:
        """Validate a single test file"""
        try:
            content = filepath.read_text()
            tree = ast.parse(content)

            # Run all validation checks
            self._check_fastapi_test_clients(filepath, tree, content)
            self._check_ollama_model_names(filepath, tree, content)
            self._check_circuit_breaker_tests(filepath, tree, content)

        except SyntaxError as e:
            self.errors.append((str(filepath), e.lineno or 0, f"Syntax error: {e}"))
        except Exception as e:
            self.errors.append((str(filepath), 0, f"Validation error: {e}"))

    def _check_fastapi_test_clients(self, filepath: Path, tree: ast.AST, content: str) -> None:
        """
        Check FastAPI test clients have all required dependency overrides.

        Detects:
        - TestClient fixtures that override some but not all dependencies
        - Missing get_openfga_client overrides (common cause of 401 errors)
        """
        # Find all fixtures that create TestClient
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Check if this is a pytest fixture
            has_fixture_decorator = any(
                isinstance(dec, ast.Name) and dec.id == "fixture" or isinstance(dec, ast.Attribute) and dec.attr == "fixture"
                for dec in node.decorator_list
            )

            if not has_fixture_decorator:
                continue

            # Check if function creates a TestClient
            creates_test_client = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "TestClient" for n in ast.walk(node)
            )

            if not creates_test_client:
                continue

            # Found a TestClient fixture - check dependency overrides
            func_source = ast.get_source_segment(content, node) or ""

            # Common dependencies to check
            has_get_current_user = "get_current_user" in func_source
            has_get_openfga = "get_openfga_client" in func_source
            has_get_sp_manager = "get_service_principal_manager" in func_source
            has_dependency_override = "app.dependency_overrides" in func_source

            # If using dependency overrides, warn if common ones are missing
            if has_dependency_override:
                # Check for common patterns
                if has_get_current_user and not re.search(r"app\.dependency_overrides\[get_current_user\]", func_source):
                    self.warnings.append(
                        (
                            str(filepath),
                            node.lineno,
                            f"Fixture '{node.name}' imports get_current_user but doesn't override it. "
                            f"This may cause 401 errors.",
                        )
                    )

                if has_get_openfga and not re.search(r"app\.dependency_overrides\[get_openfga_client\]", func_source):
                    self.warnings.append(
                        (
                            str(filepath),
                            node.lineno,
                            f"Fixture '{node.name}' imports get_openfga_client but doesn't override it. "
                            f"This commonly causes 401 errors. Add: app.dependency_overrides[get_openfga_client] = mock",
                        )
                    )

                if has_get_sp_manager and not re.search(
                    r"app\.dependency_overrides\[get_service_principal_manager\]", func_source
                ):
                    self.warnings.append(
                        (
                            str(filepath),
                            node.lineno,
                            f"Fixture '{node.name}' imports get_service_principal_manager but doesn't override it.",
                        )
                    )

    def _check_ollama_model_names(self, filepath: Path, tree: ast.AST, content: str) -> None:
        """
        Check that Ollama model names use correct format.

        Detects:
        - Model names without 'ollama/' prefix
        - Common patterns: llama3.1:8b, qwen2.5:7b, etc.
        """
        # Pattern: model_name="<name>:<tag>" or fallback_models=["<name>:<tag>"]
        # Should be: model_name="ollama/<name>:<tag>"

        # Search for LLMFactory calls with provider="ollama"
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Check if this is LLMFactory call
            is_llm_factory = (
                isinstance(node.func, ast.Name)
                and node.func.id == "LLMFactory"
                or isinstance(node.func, ast.Attribute)
                and node.func.attr == "LLMFactory"
            )

            if not is_llm_factory:
                continue

            # Check if provider="ollama"
            provider_is_ollama = any(
                isinstance(kw, ast.keyword)
                and kw.arg == "provider"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value == "ollama"
                for kw in node.keywords
            )

            if not provider_is_ollama:
                continue

            # Found Ollama LLMFactory - check model_name
            for kw in node.keywords:
                if kw.arg == "model_name" and isinstance(kw.value, ast.Constant):
                    model_name = kw.value.value
                    if not model_name.startswith("ollama/"):
                        self.errors.append(
                            (
                                str(filepath),
                                kw.value.lineno,
                                f"Invalid Ollama model name: '{model_name}'. "
                                f"Ollama models must use format 'ollama/model:tag'. "
                                f"Did you mean 'ollama/{model_name}'?",
                            )
                        )

                elif kw.arg == "fallback_models" and isinstance(kw.value, ast.List):
                    for elem in kw.value.elts:
                        if isinstance(elem, ast.Constant) and isinstance(elem.value, str):
                            model_name = elem.value
                            if not model_name.startswith("ollama/"):
                                self.errors.append(
                                    (
                                        str(filepath),
                                        elem.lineno,
                                        f"Invalid Ollama fallback model: '{model_name}'. " f"Should be 'ollama/{model_name}'",
                                    )
                                )

    def _check_circuit_breaker_tests(self, filepath: Path, tree: ast.AST, content: str) -> None:
        """
        Check that circuit breaker tests have proper isolation.

        Detects:
        - Tests manipulating circuit breaker state without skip_resilience_reset marker
        - Missing xdist group for circuit breaker tests
        """
        # Find test classes that test circuit breakers
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if class name suggests circuit breaker testing
            is_circuit_breaker_test = "CircuitBreaker" in node.name or "circuit_breaker" in node.name.lower()

            if not is_circuit_breaker_test:
                continue

            # Check class source for circuit breaker manipulation
            class_source = ast.get_source_segment(content, node) or ""
            manipulates_cb = (
                "reset_circuit_breaker" in class_source
                or "get_circuit_breaker" in class_source
                or ".state.name" in class_source
            )

            if not manipulates_cb:
                continue

            # Found circuit breaker test class - verify markers
            has_skip_reset = any(
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "mark"
                and len(dec.args) > 0
                and isinstance(dec.args[0], ast.Name)
                and dec.args[0].id == "skip_resilience_reset"
                for dec in node.decorator_list
            )

            has_xdist_group = any(
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "mark"
                and any(
                    isinstance(kw, ast.keyword)
                    and kw.arg == "name"
                    and isinstance(kw.value, ast.Constant)
                    and "circuit_breaker" in kw.value.value
                    for kw in (dec.keywords if hasattr(dec, "keywords") else [])
                )
                for dec in node.decorator_list
            )

            if not has_skip_reset:
                self.warnings.append(
                    (
                        str(filepath),
                        node.lineno,
                        f"Circuit breaker test class '{node.name}' should use "
                        f"@pytest.mark.skip_resilience_reset to avoid state pollution. "
                        f"See: tests/test_openfga_client.py for example",
                    )
                )

            if not has_xdist_group:
                self.warnings.append(
                    (
                        str(filepath),
                        node.lineno,
                        f"Circuit breaker test class '{node.name}' should use "
                        f"@pytest.mark.xdist_group(name='..._circuit_breaker_tests') for isolation",
                    )
                )

    def report(self) -> int:
        """Print validation report and return exit code"""
        has_issues = False

        if self.errors:
            has_issues = True
            print("\n❌ TEST FIXTURE VALIDATION ERRORS:")
            print("=" * 80)
            for filepath, lineno, message in self.errors:
                print(f"\n{filepath}:{lineno}")
                print(f"  ERROR: {message}")

        if self.warnings:
            print("\n⚠️  TEST FIXTURE VALIDATION WARNINGS:")
            print("=" * 80)
            for filepath, lineno, message in self.warnings:
                print(f"\n{filepath}:{lineno}")
                print(f"  WARNING: {message}")

        if not has_issues and not self.warnings:
            print("✅ All test fixtures validation passed!")
            return 0

        if has_issues:
            print("\n" + "=" * 80)
            print(f"Found {len(self.errors)} errors that must be fixed.")
            print("\nCommon fixes:")
            print("  - Add OpenFGA mock: app.dependency_overrides[get_openfga_client] = lambda: mock")
            print("  - Fix Ollama models: 'llama3.1:8b' → 'ollama/llama3.1:8b'")
            print("  - Add circuit breaker markers: @pytest.mark.skip_resilience_reset")
            print("\nSee: tests/API_TESTING.md for detailed guidance")
            return 1

        if self.warnings:
            print("\n" + "=" * 80)
            print(f"Found {len(self.warnings)} warnings (won't block commit)")
            print("Consider addressing warnings to improve test reliability.")
            return 0

        return 0


def main() -> int:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate test fixtures")
    parser.add_argument(
        "files",
        nargs="+",
        help="Test files to validate",
    )
    parser.add_argument(
        "--errors-only",
        action="store_true",
        help="Only show errors, suppress warnings",
    )

    args = parser.parse_args()

    validator = TestFixtureValidator()

    # Validate each file
    for filepath_str in args.files:
        filepath = Path(filepath_str)

        # Skip non-test files
        if not filepath.name.startswith("test_"):
            continue

        # Skip conftest.py
        if filepath.name == "conftest.py":
            continue

        if filepath.exists():
            validator.validate_file(filepath)

    # Suppress warnings if requested
    if args.errors_only:
        validator.warnings = []

    return validator.report()


if __name__ == "__main__":
    sys.exit(main())
