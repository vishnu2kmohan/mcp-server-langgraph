# CLI Tool Guards Analysis - @requires_tool Decorator Audit

**Date**: 2025-11-16
**Context**: Codex Findings Remediation - Medium-Priority Infrastructure Work
**Status**: Analysis Complete - Implementation Recommendations Documented

---

## Executive Summary

Conducted comprehensive analysis of all test files using `subprocess.run()` to identify calls missing the `@requires_tool` decorator.

**Key Finding**: **59 subprocess calls** across **20 test files** are missing the `@requires_tool` decorator for graceful CLI tool absence handling.

**Impact**: Tests fail with cryptic error messages when CLI tools (kubectl, helm, docker, trivy, kustomize) are missing, instead of skipping with clear explanations.

**Recommendation**: Add `@requires_tool` decorator to all 59 identified test functions. Estimated effort: **2-3 hours** (systematic implementation).

---

## Analysis Results

### Summary by CLI Tool

| CLI Tool | Missing Guards | Percentage |
|----------|----------------|------------|
| **kustomize** | 20 | 34% |
| **kubectl** | 16 | 27% |
| **helm** | 11 | 19% |
| **docker** | 11 | 19% |
| **actionlint** | 1 | 2% |
| **Total** | **59** | **100%** |

---

## Affected Files (20 total)

### High Impact (4+ missing guards)

#### 1. `tests/deployment/test_helm_templates.py` (8 missing)
- Line 42: `test_helm_template_renders_without_errors()` → needs `@requires_tool("helm")`
- Line 51: `test_helm_template_produces_valid_yaml()` → needs `@requires_tool("helm")`
- Line 71: `test_helm_template_checksum_annotations_present()` → needs `@requires_tool("helm")`
- Line 117: `test_helm_lint_passes()` → needs `@requires_tool("helm")`
- Line 123: `test_helm_lint_output_contains_success()` → needs `@requires_tool("helm")`
- Line 196: `test_helm_template_with_custom_values()` → needs `@requires_tool("helm")`
- Line 226: `test_helm_template_with_staging_values()` → needs `@requires_tool("helm")`
- Line 251: `test_helm_template_with_production_values()` → needs `@requires_tool("helm")`

#### 2. `tests/integration/test_docker_image_assets.py` (7 missing)
- Line 191: `test_docker_test_image_contains_deployments_at_runtime()` → needs `@requires_tool("docker")`
- Line 212: `test_docker_test_image_contains_deployments_at_runtime()` (same function, multiple calls)
- Line 238: `test_docker_test_image_contains_deployments_at_runtime()` (same function, multiple calls)
- Line 259: `test_docker_test_image_contains_scripts_at_runtime()` → needs `@requires_tool("docker")`
- Line 280: `test_docker_test_image_contains_scripts_at_runtime()` (same function, multiple calls)
- Line 309: `test_docker_test_image_contains_scripts_at_runtime()` (same function, multiple calls)
- Line 332: `test_docker_test_image_contains_scripts_at_runtime()` (same function, multiple calls)

**Note**: Functions with multiple subprocess.run() calls only need **one** decorator at function level.

#### 3. `tests/deployment/test_kustomize_builds.py` (6 missing)
- Line 68: `test_overlay_builds_without_errors()` → needs `@requires_tool("kustomize")`
- Line 100: `test_built_manifests_are_valid_yaml()` → needs `@requires_tool("kustomize")`
- Line 136: `_build_overlay()` → needs `@requires_tool("kustomize")` (helper function)
- Line 238: `_build_overlay()` (same function, multiple calls)
- Line 360: `_build_base()` → needs `@requires_tool("kustomize")` (helper function)
- Line 474: `check_kustomize_installed()` → needs `@requires_tool("kustomize")` (helper function)

#### 4. `tests/deployment/test_dns_failover_verification.py` (4 missing)
- Line 215: `_validate_dns_test_pod_manifest()` → needs `@requires_tool("kubectl")`
- Line 303: `test_redis_session_service_uses_external_name()` → needs `@requires_tool("kubectl")`
- Line 338: `test_configmap_uses_dns_names()` → needs `@requires_tool("kubectl")`
- Line 447: `test_deployment_can_connect_to_services_via_dns()` → needs `@requires_tool("kubectl")`

#### 5. `tests/regression/test_pod_deployment_regression.py` (4 missing)
- Line 67: `build_kustomize()` → needs `@requires_tool("kubectl")` (fixture)
- Line 367: `test_kustomize_builds_successfully()` → needs `@requires_tool("kubectl")`
- Line 381: `test_manifests_pass_dry_run()` → needs `@requires_tool("kubectl")`
- Line 387: `test_manifests_pass_dry_run()` (same function, multiple calls)

#### 6. `tests/deployment/test_network_policies.py` (4 missing)
- Line 44: `staging_network_policies()` → needs `@requires_tool("kustomize")` (fixture)
- Line 57: `production_network_policies()` → needs `@requires_tool("kustomize")` (fixture)
- Line 202: `production_network_policies()` (same fixture, multiple calls)
- Line 312: `test_network_policy_coverage()` → needs `@requires_tool("kustomize")`

#### 7. `tests/deployment/test_service_accounts.py` (4 missing)
- Line 39: `base_resources()` → needs `@requires_tool("kustomize")` (fixture)
- Line 172: `staging_service_accounts()` → needs `@requires_tool("kustomize")` (fixture)
- Line 185: `production_service_accounts()` → needs `@requires_tool("kustomize")` (fixture)
- Line 285: `base_resources()` (same fixture, multiple calls)

#### 8. `tests/test_deployment_manifests.py` (4 missing)
- Line 215: `test_kustomize_overlay_builds()` → needs `@requires_tool("kustomize")`
- Line 248: `test_cloud_provider_overlay_builds()` → needs `@requires_tool("kustomize")`
- Line 330: `test_helm_chart_lints_successfully()` → needs `@requires_tool("helm")`
- Line 353: `test_helm_chart_renders_successfully()` → needs `@requires_tool("helm")`

---

### Medium Impact (2-3 missing guards)

#### 9. `tests/test_kubernetes_security.py` (3 missing)
- Line 189: `test_staging_overlay_has_imagepullpolicy_always()` → needs `@requires_tool("kubectl")`
- Line 308: `test_kubeconform_validates_manifests()` → needs `@requires_tool("kubectl")`
- Line 330: `test_kustomize_builds_successfully()` → needs `@requires_tool("kubectl")`

#### 10. `tests/integration/test_docker_health_checks.py` (3 missing)
- Line 34: `docker_compose_available()` → needs `@requires_tool("docker")` (fixture)
- Line 51: `docker_available()` → needs `@requires_tool("docker")` (fixture)
- Line 413: `test_health_check_command_availability()` → needs `@requires_tool("docker")`

#### 11. `tests/deployment/test_codex_findings_validation.py` (2 missing)
- Line 256: `test_no_unsubstituted_kustomize_variables()` → needs `@requires_tool("kustomize")`
- Line 516: `test_no_unused_secret_generators()` → needs `@requires_tool("kustomize")`

#### 12. `tests/deployment/test_configmap_secret_validation.py` (2 missing)
- Line 47: `get_kustomize_output()` → needs `@requires_tool("kustomize")` (fixture)
- Line 236: `get_kustomize_output()` (same fixture, multiple calls)

---

### Low Impact (1 missing guard)

- **tests/deployment/test_helm_configuration.py** (Line 87): `test_helm_chart_lints_successfully()`
- **tests/deployment/test_kustomize_build.py** (Line 45): `build_kustomize()` (fixture)
- **tests/deployment/test_placeholder_validation.py** (Line 46): `build_overlay()` (fixture)
- **tests/deployment/test_service_dependencies.py** (Line 38): `build_kustomize_manifests()` (fixture)
- **tests/meta/test_otel_security_context.py** (Line 352): `test_rendered_staging_manifest_has_otel_security_context()`
- **tests/meta/test_trivy_scans_rendered_manifests.py** (Line 155): `test_rendered_manifests_include_security_contexts()`
- **tests/test_test_utilities.py** (Line 180): `test_docker_compose_available_checks_functionality()`
- **tests/test_workflow_syntax.py** (Line 46): `test_workflow_syntax_valid()`

---

## Decorator Usage Pattern

### The `@requires_tool` Decorator (from tests/conftest.py:649)

```python
def requires_tool(tool_name, skip_reason=None):
    """
    Decorator to skip tests if a required CLI tool is not available.

    This decorator checks for tool availability at test runtime using shutil.which(),
    and skips the test with a clear message if the tool is not found.

    Args:
        tool_name: Name of the CLI tool to check (e.g., "kustomize", "kubectl")
        skip_reason: Optional custom skip message. If None, uses default message.

    Example:
        @requires_tool("kubectl")
        def test_kubectl_apply(self):
            subprocess.run(["kubectl", "apply", "-f", "file.yaml"])
    """
```

### How to Apply the Decorator

**Before** (cryptic error on missing tool):
```python
def test_helm_template_renders_without_errors(self):
    result = subprocess.run(
        ["helm", "template", "chart/"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

**After** (graceful skip with clear message):
```python
@requires_tool("helm")
def test_helm_template_renders_without_errors(self):
    result = subprocess.run(
        ["helm", "template", "chart/"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

**Output when tool missing**:
```
tests/deployment/test_helm_templates.py::test_helm_template_renders_without_errors
SKIPPED (helm not found in PATH. Install with: brew install helm)
```

---

## Implementation Recommendations

### Approach 1: Systematic File-by-File Implementation (Recommended)

**Pros**:
- Easy to review changes
- Can test incrementally
- Clear commit history

**Cons**:
- 20 files to modify
- Requires careful tracking

**Estimated Time**: 2-3 hours

**Process**:
1. Start with high-impact files (8 missing guards)
2. Add decorators to test functions and fixtures
3. Run affected tests to verify skip behavior
4. Commit in batches (e.g., "fix(tests/deployment): add @requires_tool to helm tests")

---

### Approach 2: Automated Script Implementation

**Pros**:
- Fast (could be automated)
- Consistent application

**Cons**:
- Requires AST manipulation script
- More complex to verify
- Risk of false positives

**Estimated Time**: 1-2 hours (script development + verification)

---

### Approach 3: Meta-Test Enforcement (Future-Proof)

**Long-term solution**: Create a meta-test that fails if subprocess.run() calls are found without @requires_tool.

**Example** (tests/meta/test_cli_tool_guards.py):
```python
def test_all_subprocess_calls_have_requires_tool_decorator():
    """
    Ensure all subprocess.run() calls using CLI tools have @requires_tool decorator.

    This prevents cryptic errors when CLI tools are missing in CI/CD or dev environments.
    """
    # Scan all test files for subprocess.run() with CLI tools
    # Assert all have @requires_tool decorator
    # Fail with clear message listing violations
```

**Benefit**: Prevents future regressions, enforces pattern for new tests.

---

## Benefits of Implementation

### 1. **Better Developer Experience**
- Clear skip messages instead of cryptic subprocess errors
- Developers know exactly which tool to install
- Reduces debugging time

### 2. **Cleaner CI/CD Output**
- Tests skip gracefully when tools unavailable
- Easier to see what's actually being tested
- No false failures due to missing tools

### 3. **Environment Flexibility**
- Tests adapt to available tooling
- Developers can run subset of tests without full toolchain
- Gradual CI/CD adoption of new tools

### 4. **Documentation Value**
- Decorator makes tool dependencies explicit
- Easy to see which tests need which tools
- Helps with onboarding new developers

---

## Example Error Improvements

### Before (Cryptic)
```
E   FileNotFoundError: [Errno 2] No such file or directory: 'kubectl'
E
E   During handling of the above exception, another exception occurred:
E
E   tests/deployment/test_dns_failover_verification.py:215: in _validate_dns_test_pod_manifest
E       result = subprocess.run(["kubectl", "apply", "--dry-run=client", "-f", "-"],
E   ...
```

### After (Clear)
```
tests/deployment/test_dns_failover_verification.py::test_redis_session_service_uses_external_name
SKIPPED (kubectl not found in PATH. Install with: brew install kubectl / apt-get install kubectl)

1 skipped in 0.01s
```

---

## Priority Ranking for Implementation

### Phase 1: High-Impact Files (First PR - 1 hour)
1. `tests/deployment/test_helm_templates.py` (8 guards)
2. `tests/integration/test_docker_image_assets.py` (7 guards)
3. `tests/deployment/test_kustomize_builds.py` (6 guards)

**Total**: 21 guards, 3 files

---

### Phase 2: Medium-Impact Files (Second PR - 1 hour)
4. `tests/deployment/test_dns_failover_verification.py` (4 guards)
5. `tests/regression/test_pod_deployment_regression.py` (4 guards)
6. `tests/deployment/test_network_policies.py` (4 guards)
7. `tests/deployment/test_service_accounts.py` (4 guards)
8. `tests/test_deployment_manifests.py` (4 guards)
9. `tests/test_kubernetes_security.py` (3 guards)
10. `tests/integration/test_docker_health_checks.py` (3 guards)
11. `tests/deployment/test_codex_findings_validation.py` (2 guards)
12. `tests/deployment/test_configmap_secret_validation.py` (2 guards)

**Total**: 30 guards, 9 files

---

### Phase 3: Low-Impact Files (Third PR - 30 minutes)
13-20. Remaining 8 files with 1 guard each

**Total**: 8 guards, 8 files

---

## Validation Strategy

### 1. Manual Testing (Per-File)
```bash
# Temporarily rename tool to simulate absence
sudo mv /usr/local/bin/kubectl /usr/local/bin/kubectl.bak

# Run affected tests
uv run pytest tests/deployment/test_dns_failover_verification.py -v

# Verify tests skip gracefully with clear message
# Expected: "SKIPPED (kubectl not found in PATH...)"

# Restore tool
sudo mv /usr/local/bin/kubectl.bak /usr/local/bin/kubectl
```

---

### 2. Meta-Test Validation
Create `tests/meta/test_cli_tool_guards_enforcement.py` to automatically verify all subprocess calls have decorators.

---

### 3. CI/CD Smoke Test
Run full test suite in environment with one tool missing to verify graceful degradation.

---

## Conclusion

**Analysis Complete**: 59 subprocess calls across 20 files identified as missing `@requires_tool` decorator.

**Key Insight**: This is a higher number than the original Codex estimate (21), indicating systematic application of this pattern was overlooked during initial test development.

**Recommendation**: Implement in 3 phases (high/medium/low impact) with **total estimated time of 2-3 hours**.

**Long-Term**: Add meta-test enforcement to prevent future regressions.

The Codex finding is **valid and actionable** - implementing these guards will significantly improve test quality and developer experience.

---

## Files Summary

**Total Test Files Analyzed**: 53
**Files with subprocess.run()**: 53
**Files with @requires_tool**: 5
**Files Missing Decorator**: 20
**Total Missing Guards**: 59

**Breakdown by Tool**:
- kustomize: 20 (34%)
- kubectl: 16 (27%)
- helm: 11 (19%)
- docker: 11 (19%)
- actionlint: 1 (2%)

---

**Report Generated**: 2025-11-16
**Engineer**: Claude (Anthropic)
**Session**: mcp-server-langgraph-session-20251116-171011
**Analysis Method**: AST-based static analysis with manual verification
**Analysis Script**: `/tmp/analyze_cli_tool_guards.py`
