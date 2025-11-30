# Phase 2: Hook Rebalancing - Implementation Plan

**Priority**: 🔥 **HIGHEST IMPACT**
**Objective**: Achieve <2s commits by moving heavy hooks to pre-push stage
**Expected Impact**: 87% faster commits (8-15s → <2s)
**Estimated Effort**: 4 hours
**Tasks**: 5

---

## Executive Summary

Move heavy validation hooks from commit stage to pre-push stage to achieve sub-2-second commits while maintaining comprehensive validation at push time. This dramatically improves developer experience by enabling frequent, fast commits without sacrificing code quality.

### Success Metrics

**Before (Current State)**:
- **Commit time**: 8-15s (90th percentile)
- **Pre-push time**: 8-12 min
- **Hook distribution**: ~40 commit, ~40 pre-push, ~2 manual
- **Developer experience**: Slow commits discourage frequent commits

**After (Target State)**:
- **Commit time**: <2s (90th percentile) ✨ **87% improvement**
- **Pre-push time**: <5 min (still comprehensive)
- **Hook distribution**: ~30 commit, ~50 pre-push
- **Developer experience**: Fast commits enable TDD workflow

---

## Phase 2.1: Create Hook Performance Profiling Script

### Objective
Create a robust profiling script to measure execution time of all 82 pre-commit hooks.

### Deliverable
`scripts/profiling/profile_hooks.py` (estimated 200-250 lines)

### Implementation

#### Script Requirements

1. **Hook Execution**:
   - Run each hook in isolation
   - Measure wall clock time (not CPU time)
   - Run multiple iterations (10 iterations per hook)
   - Calculate mean, median, p90, p95, p99
   - Capture stderr/stdout for debugging

2. **Test Scenarios**:
   - **Empty change**: No files modified
   - **Single file change**: One file modified
   - **Typical change**: 3-5 files modified
   - **Large change**: 10+ files modified

3. **Output Formats**:
   - **JSON**: Machine-readable for automation
   - **CSV**: Easy import to spreadsheets
   - **Markdown table**: Human-readable report

#### Script Structure

```python
#!/usr/bin/env python3
"""
Hook Performance Profiling Script

Measures execution time of all pre-commit hooks to identify candidates
for moving from commit stage to pre-push stage.

Usage:
    python scripts/profiling/profile_hooks.py --scenario typical --iterations 10
    python scripts/profiling/profile_hooks.py --all-scenarios --format json
    python scripts/profiling/profile_hooks.py --hook-id ruff-format --iterations 50
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class HookPerformance:
    """Performance metrics for a single hook."""
    hook_id: str
    hook_name: str
    stage: str  # commit, push, manual
    iterations: int
    mean_ms: float
    median_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    stddev_ms: float
    category: str  # fast (<500ms), medium (500ms-2s), heavy (>2s)


class HookProfiler:
    """Profile pre-commit hooks to measure execution time."""

    def __init__(self, config_path: Path = Path(".pre-commit-config.yaml")):
        self.config_path = config_path
        self.hooks = self._load_hooks()

    def _load_hooks(self) -> List[Dict]:
        """Load hook configurations from .pre-commit-config.yaml."""
        # Implementation: Parse YAML and extract hook configurations
        pass

    def profile_hook(self, hook_id: str, iterations: int = 10) -> HookPerformance:
        """Profile a single hook."""
        timings = []

        for i in range(iterations):
            start = time.perf_counter()

            # Run hook via pre-commit
            result = subprocess.run(
                ["pre-commit", "run", hook_id, "--all-files"],
                capture_output=True,
                text=True
            )

            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            timings.append(elapsed_ms)

        # Calculate statistics
        mean = statistics.mean(timings)
        median = statistics.median(timings)
        p90 = self._percentile(timings, 0.90)
        p95 = self._percentile(timings, 0.95)
        p99 = self._percentile(timings, 0.99)
        min_val = min(timings)
        max_val = max(timings)
        stddev = statistics.stdev(timings) if len(timings) > 1 else 0.0

        # Categorize by speed
        if mean < 500:
            category = "fast"
        elif mean < 2000:
            category = "medium"
        else:
            category = "heavy"

        hook_info = self._get_hook_info(hook_id)

        return HookPerformance(
            hook_id=hook_id,
            hook_name=hook_info["name"],
            stage=hook_info["stage"],
            iterations=iterations,
            mean_ms=mean,
            median_ms=median,
            p90_ms=p90,
            p95_ms=p95,
            p99_ms=p99,
            min_ms=min_val,
            max_ms=max_val,
            stddev_ms=stddev,
            category=category
        )

    def profile_all(self, iterations: int = 10) -> List[HookPerformance]:
        """Profile all hooks."""
        results = []
        total = len(self.hooks)

        for idx, hook in enumerate(self.hooks, 1):
            print(f"Profiling {idx}/{total}: {hook['id']}...", file=sys.stderr)
            perf = self.profile_hook(hook['id'], iterations)
            results.append(perf)

        return results

    def export_json(self, results: List[HookPerformance], output_path: Path):
        """Export results to JSON."""
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_hooks": len(results),
            "hooks": [asdict(r) for r in results]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def export_csv(self, results: List[HookPerformance], output_path: Path):
        """Export results to CSV."""
        import csv

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'hook_id', 'hook_name', 'stage', 'category',
                'mean_ms', 'median_ms', 'p90_ms', 'p95_ms', 'p99_ms',
                'min_ms', 'max_ms', 'stddev_ms'
            ])
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))

    def export_markdown(self, results: List[HookPerformance], output_path: Path):
        """Export results to Markdown table."""
        # Group by category
        fast = [r for r in results if r.category == "fast"]
        medium = [r for r in results if r.category == "medium"]
        heavy = [r for r in results if r.category == "heavy"]

        with open(output_path, 'w') as f:
            f.write("# Hook Performance Profile\n\n")
            f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Hooks**: {len(results)}\n\n")

            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Fast hooks (<500ms)**: {len(fast)} hooks\n")
            f.write(f"- **Medium hooks (500ms-2s)**: {len(medium)} hooks\n")
            f.write(f"- **Heavy hooks (>2s)**: {len(heavy)} hooks\n\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            if heavy:
                f.write(f"### Move {len(heavy)} Heavy Hooks to Pre-push\n\n")
                f.write("These hooks significantly slow down commits:\n\n")
                self._write_table(f, heavy)

            if medium:
                f.write(f"\n### Review {len(medium)} Medium Hooks\n\n")
                f.write("Consider moving pytest-based hooks to pre-push:\n\n")
                self._write_table(f, medium)

            # All hooks table
            f.write("\n## All Hooks (sorted by p90)\n\n")
            sorted_results = sorted(results, key=lambda r: r.p90_ms, reverse=True)
            self._write_table(f, sorted_results)

    def _write_table(self, f, results: List[HookPerformance]):
        """Write results as Markdown table."""
        f.write("| Hook ID | Stage | Mean | p90 | p95 | Category |\n")
        f.write("|---------|-------|------|-----|-----|----------|\n")
        for r in results:
            f.write(f"| `{r.hook_id}` | {r.stage} | {r.mean_ms:.0f}ms | "
                   f"{r.p90_ms:.0f}ms | {r.p95_ms:.0f}ms | {r.category} |\n")

    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _get_hook_info(self, hook_id: str) -> Dict:
        """Get hook metadata."""
        # Implementation: Extract from config
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Profile pre-commit hooks to measure execution time"
    )
    parser.add_argument(
        "--hook-id",
        help="Profile specific hook by ID"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per hook (default: 10)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown", "all"],
        default="all",
        help="Output format"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs-internal/profiling"),
        help="Output directory for reports"
    )

    args = parser.parse_args()

    profiler = HookProfiler()

    if args.hook_id:
        result = profiler.profile_hook(args.hook_id, args.iterations)
        print(f"\nResults for {args.hook_id}:")
        print(f"  Mean: {result.mean_ms:.0f}ms")
        print(f"  p90: {result.p90_ms:.0f}ms")
        print(f"  p95: {result.p95_ms:.0f}ms")
        print(f"  Category: {result.category}")
    else:
        results = profiler.profile_all(args.iterations)

        args.output_dir.mkdir(parents=True, exist_ok=True)

        if args.format in ("json", "all"):
            profiler.export_json(results, args.output_dir / "hooks_performance.json")
            print(f"✓ JSON report: {args.output_dir / 'hooks_performance.json'}")

        if args.format in ("csv", "all"):
            profiler.export_csv(results, args.output_dir / "hooks_performance.csv")
            print(f"✓ CSV report: {args.output_dir / 'hooks_performance.csv'}")

        if args.format in ("markdown", "all"):
            profiler.export_markdown(results, args.output_dir / "hooks_performance.md")
            print(f"✓ Markdown report: {args.output_dir / 'hooks_performance.md'}")


if __name__ == "__main__":
    main()
```

#### Testing Requirements

Create `tests/meta/test_hook_profiler.py` with comprehensive tests:

1. `test_profile_single_hook_measures_time()`
2. `test_profile_hook_calculates_statistics_correctly()`
3. `test_categorize_hooks_by_speed()`
4. `test_export_json_format()`
5. `test_export_csv_format()`
6. `test_export_markdown_format()`
7. `test_handle_hook_failure_gracefully()`

---

## Phase 2.2: Profile All 82 Hooks

### Objective
Run profiling script on all hooks to establish baseline performance metrics.

### Execution

```bash
# Profile all hooks with 10 iterations each
python scripts/profiling/profile_hooks.py --iterations 10 --format all

# Output will be in docs-internal/profiling/:
# - hooks_performance.json
# - hooks_performance.csv
# - hooks_performance.md (human-readable report with recommendations)
```

### Expected Baseline Results

Based on manual testing and Codex Audit findings:

#### Fast Hooks (<500ms) - Keep on Commit
- `check-yaml` (~50ms)
- `check-json` (~40ms)
- `check-toml` (~45ms)
- `end-of-file-fixer` (~30ms)
- `trailing-whitespace` (~35ms)
- `check-merge-conflicts` (~25ms)
- `detect-private-key` (~60ms)
- `ruff-format` (~200ms)
- `ruff-check` (~250ms)
- Total: ~35-40 hooks

#### Medium Hooks (500ms-2s) - Review Case-by-Case
- `mypy` (~800ms, non-blocking)
- `shellcheck` (~600ms)
- `actionlint` (~700ms)
- Light pytest hooks (~500-1000ms)
- Total: ~10-15 hooks

#### Heavy Hooks (>2s) - Move to Pre-push
- `prevent-local-config-commits` (5-8s, runs pytest)
- Heavy pytest validators (2-5s each)
- Security scanners running on all files (2-4s)
- Total: ~5-10 hooks

---

## Phase 2.3: Move Heavy Hooks to Pre-push

### Objective
Migrate identified heavy hooks from commit stage to pre-push stage.

### Implementation Steps

#### 1. Update .pre-commit-config.yaml

For each heavy hook, change `stages: [commit]` to `stages: [push]`:

```yaml
# BEFORE
- id: prevent-local-config-commits
  name: Prevent commits with local config
  entry: python scripts/validation/check_local_config.py
  language: system
  pass_filenames: false
  stages: [commit]  # ❌ Runs on every commit (5-8s)

# AFTER
- id: prevent-local-config-commits
  name: Prevent commits with local config
  entry: python scripts/validation/check_local_config.py
  language: system
  pass_filenames: false
  stages: [push]  # ✅ Runs on push only
```

#### 2. Priority Candidates for Moving to Pre-push

**High Priority** (definitely move):
1. `prevent-local-config-commits` (5-8s) - Runs pytest, heaviest hook
2. Any hook running `pytest` with `--all-files`
3. Security scanners with `--all-files` that take >2s

**Medium Priority** (consider moving):
1. Hooks running on all files (not just changed files)
2. Hooks with >1s execution time
3. Pytest-based validators

**Keep on Commit** (fast, essential):
1. All formatters (ruff-format, prettier)
2. Fast linters (ruff-check)
3. Fast validators (<500ms)
4. Security checks that are fast (<500ms)

#### 3. Validation After Changes

```bash
# Test commit speed (should be <2s)
time git commit -m "test: measure commit speed"

# Test pre-push (should still be comprehensive, <5 min)
time git push --dry-run

# Profile again to verify improvements
python scripts/profiling/profile_hooks.py --format markdown
```

---

## Phase 2.4: Validate Cloud-Native Tooling

### Objective
Ensure cloud-native CLI tools (gcloud, kubectl, helm, trivy) follow consistent fail-open patterns.

### Tools to Validate

1. **gcloud** (Google Cloud CLI)
2. **kubectl** (Kubernetes)
3. **helm** (Helm charts)
4. **trivy** (Container security scanning)

### Validation Checklist

For each tool, verify:

#### 1. Availability Check Pattern

✅ **Correct pattern** (fail-open):
```bash
if ! command -v gcloud &> /dev/null; then
    echo "⚠️ gcloud not found, skipping GCP validation"
    exit 0  # ✅ Graceful degradation
fi
```

❌ **Incorrect pattern** (fail-closed):
```bash
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud required but not found"
    exit 1  # ❌ Blocks workflow
fi
```

#### 2. Wrapper Script Pattern

All cloud tools should be wrapped for consistent behavior:

**File**: `scripts/wrappers/gcloud_wrapper.sh`
```bash
#!/bin/bash
# GCloud Wrapper - Fail-open if CLI unavailable

if ! command -v gcloud &> /dev/null; then
    echo "⚠️ gcloud not available, skipping validation" >&2
    exit 0
fi

# Run gcloud command
gcloud "$@"
```

#### 3. Documentation Requirements

For each tool, document in `docs-internal/CLI_TOOL_REQUIREMENTS.md`:

```markdown
## GCloud CLI

**Required for**: GCP deployment validation
**Installation**: `curl https://sdk.cloud.google.com | bash`
**Validation hook**: `validate-gcp-configs`
**Behavior if missing**: Gracefully skips GCP validation
**Local development**: Optional
**CI/CD**: Required

### Verification

```bash
gcloud --version
gcloud auth list
```
```

### Implementation

Create validation script: `scripts/validation/validate_cli_tools.py`

```python
#!/usr/bin/env python3
"""Validate cloud-native CLI tools follow fail-open patterns."""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict


def check_tool_availability(tool: str) -> bool:
    """Check if CLI tool is available."""
    try:
        subprocess.run(
            [tool, "--version"],
            capture_output=True,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def validate_wrapper_script(wrapper_path: Path) -> Dict:
    """Validate wrapper script follows fail-open pattern."""
    content = wrapper_path.read_text()

    checks = {
        "has_availability_check": 'command -v' in content,
        "fails_open": 'exit 0' in content and '⚠️' in content,
        "has_error_message": 'echo' in content and 'skipping' in content.lower()
    }

    return {
        "path": str(wrapper_path),
        "valid": all(checks.values()),
        "checks": checks
    }


def main():
    tools = {
        "gcloud": "scripts/wrappers/gcloud_wrapper.sh",
        "kubectl": "scripts/wrappers/kubectl_wrapper.sh",
        "helm": "scripts/wrappers/helm_wrapper.sh",
        "trivy": "scripts/wrappers/trivy_wrapper.sh"
    }

    print("🔍 Validating Cloud-Native CLI Tools\n")

    all_valid = True

    for tool, wrapper_path in tools.items():
        available = check_tool_availability(tool)
        wrapper_exists = Path(wrapper_path).exists()

        print(f"Tool: {tool}")
        print(f"  Available: {'✓' if available else '✗'}")
        print(f"  Wrapper: {'✓' if wrapper_exists else '✗'}")

        if wrapper_exists:
            validation = validate_wrapper_script(Path(wrapper_path))
            print(f"  Fail-open pattern: {'✓' if validation['valid'] else '✗'}")

            if not validation['valid']:
                all_valid = False
                print(f"  Issues:")
                for check, passed in validation['checks'].items():
                    if not passed:
                        print(f"    - {check}: ✗")
        else:
            all_valid = False

        print()

    if all_valid:
        print("✅ All cloud-native tools properly configured")
        sys.exit(0)
    else:
        print("❌ Some tools need configuration updates")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Phase 2.5: Validate Commit Stage Performance

### Objective
Verify commit stage achieves <2s target after hook rebalancing.

### Validation Script

**File**: `scripts/validation/measure_commit_performance.py`

```python
#!/usr/bin/env python3
"""Measure commit stage performance to verify <2s target."""

import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import List


def create_test_commit(iteration: int) -> float:
    """Create a test commit and measure time."""
    # Create a temporary file change
    test_file = Path(f".commit_perf_test_{iteration}.txt")
    test_file.write_text(f"Test commit {iteration}\n")

    # Add file
    subprocess.run(["git", "add", str(test_file)], check=True)

    # Measure commit time
    start = time.perf_counter()
    subprocess.run(
        ["git", "commit", "-m", f"test: performance measurement {iteration}"],
        check=True,
        capture_output=True
    )
    end = time.perf_counter()

    # Clean up
    subprocess.run(["git", "reset", "--soft", "HEAD~1"], check=True)
    test_file.unlink()

    return (end - start)


def main():
    iterations = 10
    timings: List[float] = []

    print(f"📊 Measuring commit performance ({iterations} iterations)...\n")

    for i in range(1, iterations + 1):
        elapsed = create_test_commit(i)
        timings.append(elapsed)
        print(f"  Iteration {i}: {elapsed:.2f}s")

    # Calculate statistics
    mean = statistics.mean(timings)
    median = statistics.median(timings)
    p90 = statistics.quantiles(timings, n=10)[8]  # 90th percentile
    p95 = statistics.quantiles(timings, n=20)[18]  # 95th percentile

    print("\n📈 Results:")
    print(f"  Mean: {mean:.2f}s")
    print(f"  Median: {median:.2f}s")
    print(f"  p90: {p90:.2f}s")
    print(f"  p95: {p95:.2f}s")

    # Check against target
    target = 2.0
    if p90 < target:
        print(f"\n✅ SUCCESS: p90 ({p90:.2f}s) < target ({target:.0f}s)")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: p90 ({p90:.2f}s) >= target ({target:.0f}s)")
        print("\nRecommendations:")
        print("  - Profile hooks again to identify remaining slow hooks")
        print("  - Consider moving more hooks to pre-push stage")
        print("  - Check for newly added hooks")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Validation Steps

```bash
# 1. Measure commit performance
python scripts/validation/measure_commit_performance.py

# Expected output:
# 📊 Measuring commit performance (10 iterations)...
#   Iteration 1: 1.45s
#   Iteration 2: 1.52s
#   ...
# 📈 Results:
#   Mean: 1.48s
#   Median: 1.47s
#   p90: 1.65s
#   p95: 1.78s
# ✅ SUCCESS: p90 (1.65s) < target (2s)

# 2. Verify pre-push still comprehensive
time make validate-pre-push

# Expected: 4-5 minutes (comprehensive validation)

# 3. Document results
python scripts/validation/measure_commit_performance.py > docs-internal/commit_performance_after.txt
```

---

## Risk Mitigation

### Risk 1: Breaking Existing Workflows

**Mitigation**:
1. Create feature branch for hook rebalancing
2. Test thoroughly before merging to main
3. Document all changes in commit messages
4. Create rollback plan (revert commit)

### Risk 2: Missing Critical Validation

**Mitigation**:
1. Only move hooks that are >2s
2. Keep all security checks <500ms on commit
3. Verify pre-push runs all moved hooks
4. Test with real-world scenarios

### Risk 3: Developer Confusion

**Mitigation**:
1. Clear commit messages explaining changes
2. Update TESTING.md with new hook organization
3. Add banner message when hooks are skipped on commit
4. Document in .claude/memory/pre-commit-hooks-catalog.md

---

## Testing Plan

### Unit Tests

Create `tests/meta/test_hook_rebalancing.py`:

```python
def test_commit_hooks_are_fast():
    """Verify all commit-stage hooks are <500ms."""
    profiler = HookProfiler()
    commit_hooks = [h for h in profiler.hooks if h.stage == "commit"]

    for hook in commit_hooks:
        perf = profiler.profile_hook(hook.id, iterations=5)
        assert perf.mean_ms < 500, (
            f"Hook {hook.id} is too slow for commit stage: "
            f"{perf.mean_ms:.0f}ms > 500ms"
        )


def test_pre_push_hooks_are_comprehensive():
    """Verify pre-push hooks cover all validation."""
    profiler = HookProfiler()
    push_hooks = [h for h in profiler.hooks if h.stage == "push"]

    # Should have moved hooks
    assert len(push_hooks) >= 45, f"Expected >= 45 push hooks, got {len(push_hooks)}"

    # Should include heavy validators
    hook_ids = [h.id for h in push_hooks]
    assert "prevent-local-config-commits" in hook_ids
    assert any("pytest" in h_id for h_id in hook_ids)


def test_commit_stage_meets_performance_target():
    """Verify commit stage achieves <2s target."""
    # Run actual commit and measure
    elapsed = measure_commit_time()
    assert elapsed < 2.0, f"Commit took {elapsed:.2f}s > 2s target"
```

### Integration Tests

```bash
# Test complete workflow
git checkout -b test-hook-rebalancing

# Make a change
echo "test" >> test_file.txt

# Measure commit (should be <2s)
time git commit -am "test: verify fast commits"

# Measure push (should be comprehensive, <5 min)
time git push --set-upstream origin test-hook-rebalancing

# Clean up
git checkout main
git branch -D test-hook-rebalancing
```

---

## Documentation Updates

### 1. TESTING.md

```markdown
## Git Hooks Performance

This project uses a **two-stage hook validation strategy** optimized for developer productivity:

### Pre-commit Hooks (Fast - <2s)
Auto-runs on `git commit` for changed files only.

**Performance**: <2s (90th percentile)
**What runs**:
- Fast formatters (Ruff format/check)
- Light validators (YAML, JSON, TOML)
- Quick security checks (<500ms)

**Philosophy**: Keep commits fast to enable TDD workflow

### Pre-push Hooks (Comprehensive - 4-5 min)
Auto-runs on `git push` for all files.

**Performance**: 4-5 minutes
**What runs**:
- Complete test suite (unit, smoke, integration)
- Heavy validators (pytest-based)
- Comprehensive security scans
- Infrastructure validation

**Philosophy**: Comprehensive validation before code review
```

### 2. .claude/memory/pre-commit-hooks-catalog.md

Update with new hook organization showing which hooks run on commit vs push.

---

## Success Criteria

- [ ] Hook profiling script created and tested
- [ ] All 82 hooks profiled with baseline metrics
- [ ] Heavy hooks (>2s) moved to pre-push stage
- [ ] Cloud-native tooling validated (fail-open pattern)
- [ ] Commit stage achieves <2s target (p90)
- [ ] Pre-push stage remains comprehensive (<5 min)
- [ ] Documentation updated
- [ ] Tests pass
- [ ] Changes committed and pushed

---

## Appendix: Hook Categories

### Fast Hooks (<500ms) - Keep on Commit

**File Validators**:
- check-yaml
- check-json
- check-toml
- check-xml
- check-added-large-files
- check-merge-conflicts
- end-of-file-fixer
- trailing-whitespace
- mixed-line-ending

**Security (Fast)**:
- detect-private-key
- detect-aws-credentials
- check-secrets

**Formatters**:
- ruff-format
- prettier

**Linters**:
- ruff-check
- shellcheck (if fast)
- actionlint (if fast)

### Medium Hooks (500ms-2s) - Review Case-by-Case

**Type Checking**:
- mypy (warning-only, non-blocking)

**Validators**:
- shellcheck (if medium)
- actionlint (if medium)
- Light pytest hooks

### Heavy Hooks (>2s) - Move to Pre-push

**Pytest-based Validators**:
- prevent-local-config-commits (5-8s)
- Heavy pytest validators

**Security (Comprehensive)**:
- bandit (all files)
- trivy (container scanning)

**Infrastructure**:
- Deployment validators
- Helm/Kustomize validation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Status**: Ready for Implementation
