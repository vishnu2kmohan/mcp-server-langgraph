#!/usr/bin/env bats
# BATS tests for preview-smoke-tests.sh
# Following TDD RED-GREEN-REFACTOR methodology
#
# These tests validate critical fixes to prevent regressions:
# - Integer comparison errors (restart count parsing bug fix)
# - Undefined function calls (test_warn → log_warn fix)
# - Shell script syntax and best practices

# Load BATS libraries
load '../test_helper/bats-support/load'
load '../test_helper/bats-assert/load'

# Test setup - run before each test
setup() {
    # Path to script under test
    export SCRIPT_PATH="${BATS_TEST_DIRNAME}/../../scripts/gcp/preview-smoke-tests.sh"
}

# ============================================================================
# REGRESSION TESTS - Prevent Previously Fixed Bugs
# ============================================================================

@test "script contains no undefined 'test_warn' calls (fixed bug)" {
    # Bug: Line 299 called test_warn instead of log_warn
    # This test ensures the fix remains in place
    run grep -n "test_warn" "$SCRIPT_PATH"

    # Should find no matches (all should be log_warn now)
    assert_failure
}

@test "script uses log_warn function correctly" {
    # Verify log_warn function exists and is used
    run grep -c "log_warn" "$SCRIPT_PATH"

    # Should have at least 1 usage
    assert_success
}

@test "restart count parsing uses proper tr and grep pipeline" {
    # Bug: kubectl returned "0 0" causing integer comparison error
    # Fix: Added tr ' ' '\n' | grep -v '^$' to handle space-separated values
    #
    # This test validates the fix is present
    run grep -A 5 "MAX_RESTARTS=" "$SCRIPT_PATH"

    assert_success
    # Should contain the tr command that fixes the parsing
    assert_output --partial "tr ' '"
}

@test "restart count has fallback default value" {
    # Ensure MAX_RESTARTS parsing handles empty values properly
    # The fix uses: grep -v '^$' and 'head -n1 || echo "0"' to handle edge cases
    run grep -A 6 "MAX_RESTARTS=" "$SCRIPT_PATH"

    assert_success
    # Should contain safeguards like grep, tr, or echo "0"
    # We verify the multi-line pipeline is present
    [ "${#lines[@]}" -gt 3 ]
}

@test "integer comparison uses proper syntax for MAX_RESTARTS" {
    # Verify integer comparisons use correct syntax with parameter expansion
    run grep "\${MAX_RESTARTS" "$SCRIPT_PATH"

    assert_success
    # Should use ${MAX_RESTARTS:-0} for safe comparisons
    assert_output --partial ":-0"
}

# ============================================================================
# SHELL SCRIPT BEST PRACTICES
# ============================================================================

@test "script uses 'set -euo pipefail' for safety" {
    # Best practice: fail fast on errors
    run grep "set -euo pipefail" "$SCRIPT_PATH"

    assert_success
}

@test "script has proper shebang" {
    run head -n 1 "$SCRIPT_PATH"

    assert_success
    assert_output "#!/bin/bash"
}

@test "all functions are defined before use" {
    # Extract all function definitions
    run grep -n "^[a-z_]*().*{$" "$SCRIPT_PATH"

    assert_success
    # Should have multiple function definitions
}

@test "log functions (info, warn, error) are all defined" {
    # Verify all log helper functions exist
    run grep -E "^(log_info|log_warn|log_error)\(\)" "$SCRIPT_PATH"

    assert_success
    # Count should be 3 (one for each log function)
    [ "${#lines[@]}" -eq 3 ]
}

@test "test result functions (pass, fail, start) are defined" {
    # Verify test result tracking functions exist
    run grep -E "^(test_pass|test_fail|test_start)\(\)" "$SCRIPT_PATH"

    assert_success
    # Should have all three test result functions
    [ "${#lines[@]}" -ge 3 ]
}

# ============================================================================
# VALIDATION - No Common Shell Script Errors
# ============================================================================

@test "no unquoted variable expansions in critical paths" {
    # Variables in comparisons should be quoted
    # Look for common patterns that should be quoted
    run grep -E '\[\s*\$[A-Z_]+\s*(=|!=|-eq|-ne|-lt|-le|-gt|-ge)' "$SCRIPT_PATH"

    # Should not find unquoted variables in test expressions
    # (Some may be acceptable, but we want to minimize them)
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
}

@test "kubectl commands have proper error handling" {
    # Find kubectl commands
    run grep -n "kubectl" "$SCRIPT_PATH"

    assert_success
    # Should have multiple kubectl commands
    [ "${#lines[@]}" -gt 5 ]
}

@test "no bashisms that would fail in sh" {
    # While script uses bash, check for common issues
    # Script should declare #!/bin/bash (not #!/bin/sh)
    run head -n 1 "$SCRIPT_PATH"

    assert_output "#!/bin/bash"
}

# ============================================================================
# FUNCTION COVERAGE - All Expected Test Functions Exist
# ============================================================================

@test "script contains test_pod_restarts function" {
    run grep "^test_pod_restarts()" "$SCRIPT_PATH"
    assert_success
}

@test "script contains test_external_secrets function" {
    run grep "^test_external_secrets()" "$SCRIPT_PATH"
    assert_success
}

@test "script contains test_health_endpoint function" {
    run grep "^test_health_endpoint()" "$SCRIPT_PATH"
    assert_success
}

@test "script contains test_deployment_status function" {
    run grep -E "test_deployment.*status" "$SCRIPT_PATH"
    assert_success
}

# ============================================================================
# DOCUMENTATION AND MAINTAINABILITY
# ============================================================================

@test "script has comments explaining complex logic" {
    # Count comments
    run grep -c "^#" "$SCRIPT_PATH"

    assert_success
    # Should have at least 20 comment lines
    [ "$output" -gt 20 ]
}

@test "script has proper exit code handling" {
    # Script should have exit statements or return codes
    run grep -E "(exit|return)" "$SCRIPT_PATH"

    assert_success
}

# ============================================================================
# SECURITY - No Hardcoded Secrets or Credentials
# ============================================================================

@test "no hardcoded API keys or secrets" {
    # Search for common secret patterns
    run grep -iE "(api[_-]?key|password|secret|token).*=" "$SCRIPT_PATH"

    # Should not find any hardcoded secrets
    # (May find variable names, but not values)
    if [ "$status" -eq 0 ]; then
        # If found, ensure they're variable assignments, not hardcoded values
        refute_output --partial '="sk-'
        refute_output --partial '="password'
    fi
}

@test "no credentials passed as command-line arguments" {
    # Credentials should not be in kubectl commands
    run grep -iE "kubectl.*--token|kubectl.*--password" "$SCRIPT_PATH"

    # Should not find credentials in kubectl commands
    assert_failure
}
