# Pre-Commit Hook Analysis & Optimization Opportunities

**Total pre-commit hooks**: 30 hooks
**Target runtime**: < 30 seconds (ideal for pre-commit)
**Current estimated runtime**: 20-40 seconds

## Category Breakdown

### File Formatting & Quality (9 hooks) ⚡ FAST
1. `trailing-whitespace` - Remove trailing whitespace
2. `end-of-file-fixer` - Ensure files end with newline
3. `check-yaml` - Validate YAML syntax
4. `check-added-large-files` - Block large files (>500KB)
5. `check-merge-conflict` - Detect merge conflict markers
6. `detect-private-key` - Prevent committing private keys
7. `check-json` - Validate JSON syntax
8. `check-toml` - Validate TOML syntax
9. `mixed-line-ending` - Normalize line endings

**Status**: ✅ Essential, fast (<5s total)
**Recommendation**: Keep as-is

---

### Code Formatting (3 hooks) ⚡ FAST-MODERATE
1. `black` - Python code formatting (auto-fix)
2. `isort` - Import sorting (auto-fix)
3. `flake8` - Linting (reporting only)

**Status**: ✅ Standard Python toolchain
**Runtime**: 5-10s depending on changed files
**Recommendation**: Keep as-is (essential for code quality)

**Potential optimization**:
```yaml
# Limit to only staged Python files (already done)
files: ^src/.*\.py$
pass_filenames: true
```

---

### Security Scanning (2 hooks) 🐌 MODERATE
1. `bandit` - Security vulnerability scanning
2. `gitleaks` - Secret detection

**Runtime**: 5-15s
**Status**: ⚠️ Moderate impact, but essential for security

**⚡ OPTIMIZATION OPPORTUNITY**:
- Both scan for security issues
- Could be slow on large codebases
- Consider: `files:` patterns to limit scope

**Current config**:
```yaml
# bandit - already optimized
args: [-ll, -x, tests, --skip, B608]  # Low/low severity, exclude tests

# gitleaks - scans all files
```

**Recommendation**:
- Keep both (security critical)
- Monitor runtime; if > 10s, consider moving to pre-push
- gitleaks is comprehensive but can be slow

---

### Dependency & Config Validation (2 hooks) ⚡ FAST
1. `uv-lock-check` - Validate uv.lock synchronized
2. `check-github-workflows` - GitHub Actions syntax

**Runtime**: 2-5s
**Status**: ✅ Fast and essential
**Recommendation**: Keep as-is

---

### Documentation Validation (3 hooks) ⚡ FAST
1. `validate-mdx-extensions` - Ensure .mdx not .md in docs/
2. `check-frontmatter-quotes` - Frontmatter quote style
3. `validate-adr-sync` - ADR synchronization (enhanced with case checking)

**Runtime**: 2-5s
**Status**: ✅ Fast validation
**Recommendation**: Keep as-is (recently enhanced!)

---

### Test Quality & Safety (6 hooks) ⚡ FAST-MODERATE
1. `check-test-sleep-duration` - Prevent excessive sleep()
2. `validate-pytest-markers` - Ensure markers registered
3. `check-test-memory-safety` - pytest-xdist OOM prevention
4. `check-async-mock-usage` - Prevent hanging tests
5. `validate-test-ids` - Prevent pytest-xdist ID pollution
6. `prevent-local-config-commits` - Block local config files

**Runtime**: 5-10s
**Status**: ✅ Fast validators, prevent critical bugs

**⚡ MINOR OPTIMIZATION**:
- All run on test file changes only (already optimized with `files:` patterns)
- Could potentially merge into single `validate-test-safety.py` script

**Recommendation**: Keep separate (each addresses distinct bug pattern)

---

### Infrastructure & Deployment (4 hooks) ⚡ FAST
1. `validate-github-workflows` - Workflow context usage
2. `shellcheck` - Bash script linting
3. `validate-keycloak-config` - Keycloak service config
4. `validate-docker-image-contents` - Dockerfile validation

**Runtime**: 3-8s
**Status**: ✅ Fast, focused validators
**Recommendation**: Keep as-is

---

### Terraform (1 hook) ⚡ FAST
1. `terraform_fmt` - Terraform formatting

**Runtime**: 1-3s
**Status**: ✅ Fast auto-formatter
**Recommendation**: Keep as-is

---

## Performance Analysis

### Current Runtime Breakdown

| Category | Hooks | Est. Time | Impact |
|----------|-------|-----------|--------|
| File Formatting | 9 | 2-5s | ⚡ Fast |
| Code Formatting | 3 | 5-10s | ⚡ Fast |
| Security | 2 | 5-15s | 🐌 Moderate |
| Dependencies | 2 | 2-5s | ⚡ Fast |
| Documentation | 3 | 2-5s | ⚡ Fast |
| Test Safety | 6 | 5-10s | ⚡ Fast |
| Infrastructure | 4 | 3-8s | ⚡ Fast |
| Terraform | 1 | 1-3s | ⚡ Fast |
| **TOTAL** | **30** | **25-60s** | ⚠️ Target: <30s |

---

## Identified Issues & Optimizations

### 🟡 MODERATE PRIORITY: Security Scan Performance

**Issue**: `gitleaks` and `bandit` can be slow on large commits

**Current behavior**:
- `gitleaks`: Scans all files for secrets (comprehensive but slow)
- `bandit`: Scans Python files for vulnerabilities (optimized with -ll)

**Optimization options**:

**Option 1**: Move `gitleaks` to pre-push
```yaml
# Pros: Faster pre-commit, still catches secrets before push
# Cons: Secrets in commits (but not pushed)
stages: [pre-push]
```

**Option 2**: Limit `gitleaks` scope
```yaml
# Scan only staged files, not full history
# (Check if gitleaks supports this)
```

**Recommendation**: **Monitor performance first**
- If pre-commit consistently > 30s, move `gitleaks` to pre-push
- Keep `bandit` in pre-commit (Python-specific, usually fast)

---

### 🟢 LOW PRIORITY: Test Validator Consolidation

**Current**: 6 separate test safety hooks
- `check-test-sleep-duration`
- `validate-pytest-markers`
- `check-test-memory-safety`
- `check-async-mock-usage`
- `validate-test-ids`
- `prevent-local-config-commits`

**Opportunity**: Merge into single `validate-test-safety.py`

**Pros**:
- Single script execution (faster startup)
- Unified error reporting
- Easier maintenance

**Cons**:
- Requires refactoring
- Loss of granular skip control (SKIP=specific-hook)

**Recommendation**: **Low priority**
- Current implementation is clean and fast
- Only consolidate if performance becomes issue

---

### ✅ ALREADY OPTIMIZED: File Patterns

Most hooks already use smart file patterns:

```yaml
# Good examples:
flake8:
  files: ^src/mcp_server_langgraph/.*\.py$  # Only source code

check-test-sleep-duration:
  files: ^tests/.*\.py$  # Only test files

validate-mdx-extensions:
  files: ^docs/.*\.(md|mdx)$  # Only documentation
```

**Status**: ✅ Well-optimized, no changes needed

---

## Comparison: Pre-Commit vs Pre-Push

| Aspect | Pre-Commit (30 hooks) | Pre-Push (45 hooks) |
|--------|----------------------|---------------------|
| **Target time** | < 30 seconds | < 10 minutes |
| **Actual time** | 25-60s | 8-12 min |
| **Focus** | Fast feedback | Comprehensive validation |
| **Optimization** | Minimize latency | Minimize redundancy |

---

## Optimization Recommendations

### Priority 1: Performance Monitoring

**Action**: Add timing to understand actual performance

```bash
# Manual timing test
time pre-commit run --all-files

# Per-hook timing
pre-commit run --verbose --all-files 2>&1 | grep -E "^\[|Passed|Failed"
```

**Decision points**:
- If total time < 30s → ✅ No changes needed
- If 30-60s → Consider moving gitleaks to pre-push
- If > 60s → Investigate slow hooks

---

### Priority 2: Conditional Optimizations

**If gitleaks is slow** (> 10s consistently):

```yaml
# Move to pre-push
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.28.0
  hooks:
    - id: gitleaks
      stages: [pre-push]  # ← Add this
      description: |
        Secret detection (moved to pre-push for performance)
```

**If bandit is slow** (> 10s):

```yaml
# Already optimized with:
args: [-ll, -x, tests, --skip, B608]

# Further optimization if needed:
args: [-ll, -x, tests, --skip, B608, -f, json]  # JSON output (faster)
```

---

### Priority 3: Developer Experience

**Quick commit workflow** (when hooks are slow):

```bash
# Skip hooks for WIP commits
git commit --no-verify -m "WIP: work in progress"

# Run hooks before final commit
pre-commit run --all-files
git commit --amend --no-edit
```

**Selective hook skipping**:

```bash
# Skip slow security scans for minor changes
SKIP=gitleaks,bandit git commit -m "docs: fix typo"
```

---

## Recommended Action Plan

### Phase 1: Measurement (Do this first!)

```bash
# 1. Time current pre-commit performance
time pre-commit run --all-files > /tmp/precommit-timing.txt 2>&1

# 2. Identify slowest hooks
grep -E "Passed|Failed" /tmp/precommit-timing.txt
```

### Phase 2: Conditional Optimization (Only if needed)

**If total time > 30s:**

1. Move `gitleaks` to pre-push (saves 5-10s)
   ```yaml
   - id: gitleaks
     stages: [pre-push]
   ```

2. Consider limiting `bandit` scope further
   ```yaml
   args: [-ll, -x, tests, --skip, B608, --recursive, src/]
   ```

### Phase 3: Documentation

Update `.githooks/README.md` with:
- Expected pre-commit runtime
- How to measure performance
- When to skip hooks

---

## Current Assessment

### ✅ Strengths

1. **Well-organized**: Clear categorization by purpose
2. **File patterns**: Smart use of `files:` to limit scope
3. **Fast validators**: Most hooks are <5s
4. **Essential checks**: No obvious redundancy

### ⚠️ Potential Concerns

1. **Security scans**: `gitleaks` + `bandit` could be slow on large commits
2. **Total runtime**: Upper bound (60s) exceeds ideal (<30s)
3. **No parallelization**: Hooks run sequentially

### 🎯 Optimization Potential

- **Low effort, high impact**: Move `gitleaks` to pre-push if slow
- **Medium effort, medium impact**: Consolidate test validators
- **High effort, unknown impact**: Parallel hook execution (framework limitation)

---

## Conclusion

**Overall Status**: ✅ **Well-optimized for a comprehensive test suite**

**Immediate action**: **Measure first, optimize later**

```bash
# Run this to get baseline performance
time pre-commit run --all-files

# If < 30s: ✅ No changes needed
# If 30-60s: Consider moving gitleaks to pre-push
# If > 60s: Investigate slow hooks individually
```

**Recommended optimization** (if needed):
1. Move `gitleaks` to pre-push (quick win, 5-10s savings)
2. Monitor bandit performance
3. Consider test validator consolidation (low priority)

---

**Next Steps**:
1. Measure actual performance on your machine
2. Review optimization recommendations
3. Decide if changes needed based on actual runtime
