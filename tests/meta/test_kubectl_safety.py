"""
Meta-tests for Kubectl Safety

These tests validate that kubectl operations use dry-run mode to prevent
accidental modifications to real clusters.

Purpose: Prevent regression of Codex Finding #4 (DNS failover tests against real staging cluster)
"""

import ast
import gc
from pathlib import Path

import pytest


# Mark as unit+meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]


REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.meta
@pytest.mark.xdist_group(name="testkubectlsafetyenforcement")
class TestKubectlSafetyEnforcement:
    """
    Meta-tests that validate kubectl operations use --dry-run.

    RED: These tests will fail if kubectl apply/create/delete used without safety guards.
    GREEN: All kubectl operations are safe (dry-run or explicitly guarded).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_kubectl_operations_use_dry_run_or_guards(self):
        """
        Validate kubectl apply/create/delete operations use --dry-run or safety guards.

        This prevents regressions of Codex Finding #4:
        "Deployment DNS failover tests run real kubectl apply against staging-mcp-server-langgraph,
        risking live cluster drift from a local test run."

        RED: Fails if kubectl operations lack safety measures.
        GREEN: All kubectl operations are safe.
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            # Skip meta-tests
            if "meta" in str(test_file):
                continue

            with open(test_file) as f:
                source = f.read()

            # Check if file uses kubectl
            if "kubectl" not in source:
                continue

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        continue

                    func_source = ast.get_source_segment(source, node)
                    if not func_source:
                        continue

                    # Check for dangerous kubectl operations in actual code (not docstrings)
                    # Look for subprocess.run, os.system calls with kubectl
                    dangerous_operations = ["kubectl apply", "kubectl create", "kubectl delete", "kubectl patch"]

                    # Check for actual command execution patterns
                    has_subprocess_kubectl = "subprocess.run(" in func_source and "kubectl" in func_source
                    has_os_system_kubectl = "os.system(" in func_source and "kubectl" in func_source

                    if has_subprocess_kubectl or has_os_system_kubectl:
                        for operation in dangerous_operations:
                            # Look for the operation in command strings (between quotes)
                            # Match patterns like ["kubectl", "apply", ...] or "kubectl apply"
                            import re

                            # Pattern for list-style commands: ["kubectl", "apply"
                            list_pattern = rf'\["kubectl",\s*"{operation.split()[1]}"'
                            # Pattern for string commands: "kubectl apply" or 'kubectl apply'
                            string_pattern = rf'["\']kubectl\s+{operation.split()[1]}["\']'

                            has_operation = re.search(list_pattern, func_source) or re.search(string_pattern, func_source)

                            if has_operation:
                                # Check if it has safety guards
                                has_dry_run = "--dry-run" in func_source
                                has_skipif = "@pytest.mark.skipif" in func_source or "pytest.skip(" in func_source
                                has_env_check = (
                                    'os.getenv("ALLOW_REAL' in func_source or 'os.environ.get("ALLOW_REAL' in func_source
                                )

                                is_safe = has_dry_run or has_skipif or has_env_check

                                if not is_safe:
                                    violations.append(
                                        f"{test_file.name}::{node.name}\n"
                                        f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                        f"  Issue: Uses '{operation}' in subprocess call without safety guards\n"
                                        f"  Detected operation: {operation}\n"
                                        f"  Fix options:\n"
                                        f"    1. Add --dry-run=client flag: kubectl apply --dry-run=client\n"
                                        f"    2. Add @pytest.mark.skipif guard with environment check\n"
                                        f"    3. Add explicit environment variable check: if os.getenv('ALLOW_REAL_K8S_TESTS') != 'true': pytest.skip(...)"
                                    )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} kubectl operation(s) without safety guards:\n\n"
                f"{violation_report}\n\n"
                f"Kubectl operations MUST use --dry-run or explicit safety guards. "
                f"See Codex Finding #4 for examples."
            )

    def test_kubectl_tests_have_requires_kubectl_marker(self):
        """
        Validate tests using kubectl have @pytest.mark.requires_kubectl marker.

        This ensures kubectl tests can be skipped when kubectl is not available.

        RED: Fails if kubectl tests lack the marker.
        GREEN: All kubectl tests properly marked.
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            # Skip meta-tests
            if "meta" in str(test_file):
                continue

            with open(test_file) as f:
                source = f.read()

            # Check if file uses kubectl
            if "kubectl" not in source:
                continue

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
                        continue

                    func_or_class_source = ast.get_source_segment(source, node)
                    if not func_or_class_source:
                        continue

                    # Check if uses kubectl
                    if "kubectl" in func_or_class_source:
                        # Check for marker
                        has_marker = any(
                            (isinstance(dec, ast.Name) and dec.id == "pytest")
                            or (isinstance(dec, ast.Attribute) and dec.attr == "requires_kubectl")
                            for dec in node.decorator_list
                        )

                        # Also check for class-level marker
                        if not has_marker and isinstance(node, ast.FunctionDef):
                            # Check parent class
                            for parent in ast.walk(tree):
                                if isinstance(parent, ast.ClassDef):
                                    if any(child == node for child in ast.walk(parent)):
                                        has_marker = any(
                                            isinstance(dec, ast.Attribute) and dec.attr == "requires_kubectl"
                                            for dec in parent.decorator_list
                                        )
                                        break

                        if not has_marker:
                            violations.append(
                                f"{test_file.name}::{node.name}\n"
                                f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                f"  Issue: Uses kubectl but lacks @pytest.mark.requires_kubectl marker\n"
                                f"  Fix: Add marker to test or test class"
                            )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} kubectl test(s) without @pytest.mark.requires_kubectl:\n\n"
                f"{violation_report}\n\n"
                f"Tests using kubectl must be properly marked for conditional execution."
            )

    def test_kubectl_namespace_not_production(self):
        """
        Validate kubectl operations don't target production namespaces.

        RED: Fails if production namespaces detected.
        GREEN: All operations target safe namespaces.
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []
        production_namespaces = ["production", "prod", "default", "kube-system"]

        for test_file in test_files:
            # Skip meta-tests
            if "meta" in str(test_file):
                continue

            with open(test_file) as f:
                source = f.read()

            if "kubectl" not in source:
                continue

            for prod_ns in production_namespaces:
                # Check for direct namespace references
                if f"namespace={prod_ns}" in source or f"namespace: {prod_ns}" in source or f"-n {prod_ns}" in source:
                    # Skip if it's in a comment or string example
                    lines = source.split("\n")
                    for lineno, line in enumerate(lines, 1):
                        if f"namespace={prod_ns}" in line or f"namespace: {prod_ns}" in line or f"-n {prod_ns}" in line:
                            if not line.strip().startswith("#") and "--dry-run" not in line:
                                violations.append(
                                    f"{test_file.name}:{lineno}\n"
                                    f"  Location: {test_file.relative_to(REPO_ROOT)}:{lineno}\n"
                                    f"  Issue: References production namespace '{prod_ns}'\n"
                                    f"  Fix: Use test namespace or staging namespace with explicit guards"
                                )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} kubectl operation(s) targeting production namespaces:\n\n"
                f"{violation_report}\n\n"
                f"Tests must not target production namespaces without explicit dry-run mode."
            )


@pytest.mark.meta
@pytest.mark.xdist_group(name="testkubectltestnaming")
class TestKubectlTestNaming:
    """Validate kubectl test naming conventions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_kubectl_tests_describe_operation(self):
        """
        Kubectl tests should describe what they're validating.

        Good: test_deployment_manifest_valid_dry_run
        Bad: test_kubectl, test_apply
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            if "meta" in str(test_file):
                continue

            with open(test_file) as f:
                source = f.read()

            if "kubectl" not in source:
                continue

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        continue

                    func_source = ast.get_source_segment(source, node)
                    if not func_source or "kubectl" not in func_source:
                        continue

                    # Check name quality
                    name = node.name
                    low_quality_patterns = ["test_kubectl", "test_apply", "test_k8s"]

                    if name in low_quality_patterns:
                        violations.append(
                            f"{test_file.name}::{name}\n"
                            f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                            f"  Issue: Test name is too generic\n"
                            f"  Fix: Use descriptive name like test_<resource>_manifest_<operation>_<validation>"
                        )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} poorly named kubectl test(s):\n\n"
                f"{violation_report}\n\n"
                f"Kubectl tests should have descriptive names."
            )
