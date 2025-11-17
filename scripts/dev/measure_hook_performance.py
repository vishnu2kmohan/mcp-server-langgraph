#!/usr/bin/env python3
"""
Measure and report pre-commit and pre-push hook performance.

This script helps monitor hook execution times to ensure:
- Pre-commit hooks remain fast (< 30 seconds target)
- Pre-push hooks are comprehensive but efficient (< 10 minutes target)
- Identify slow hooks that need optimization

Usage:
    # Measure pre-commit hook performance
    python scripts/measure_hook_performance.py --stage commit

    # Measure pre-push hook performance
    python scripts/measure_hook_performance.py --stage push

    # Measure both stages
    python scripts/measure_hook_performance.py --stage all

    # Run with profiling (detailed timing)
    python scripts/measure_hook_performance.py --stage commit --profile
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class HookResult:
    """Result of running a single hook."""

    hook_id: str
    duration: float
    passed: bool
    output: str


@dataclass
class StageResult:
    """Result of running all hooks in a stage."""

    stage: str
    total_duration: float
    hook_results: List[HookResult]
    passed: bool


def get_repo_root() -> Path:
    """Get repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def measure_pre_commit_hooks(stage: str, profile: bool = False) -> StageResult:
    """
    Measure pre-commit hook performance.

    Args:
        stage: "commit" or "push"
        profile: Whether to measure individual hook timing

    Returns:
        StageResult with timing information
    """
    hook_results = []
    start_time = time.time()

    if stage == "commit":
        hook_stage = "commit"
        print(f"🔍 Measuring pre-commit hook performance (commit stage)...")
    else:
        hook_stage = "push"
        print(f"🔍 Measuring pre-commit hook performance (push stage)...")

    # Run pre-commit hooks
    cmd = ["pre-commit", "run", "--all-files"]
    if stage == "push":
        cmd.extend(["--hook-stage", "push"])

    if profile:
        cmd.append("--verbose")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1200,  # 20 minute timeout
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        passed = False
        output = "TIMEOUT: Pre-commit hooks exceeded 20 minute limit"

    total_duration = time.time() - start_time

    # Create a single result for all hooks combined
    hook_results.append(
        HookResult(
            hook_id=f"pre-commit-{stage}-stage",
            duration=total_duration,
            passed=passed,
            output=output,
        )
    )

    return StageResult(
        stage=hook_stage,
        total_duration=total_duration,
        hook_results=hook_results,
        passed=passed,
    )


def measure_pre_push_phases() -> StageResult:
    """
    Measure pre-push hook phases.

    Returns:
        StageResult with timing for each phase
    """
    print("🔍 Measuring pre-push hook phases...")
    hook_results = []
    start_time = time.time()

    # Phase 1: Lockfile & Workflow Validation
    phase1_start = time.time()
    try:
        subprocess.run(["uv", "lock", "--check"], capture_output=True, check=True, timeout=60)
        phase1_passed = True
        phase1_output = "Lockfile validation passed"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        phase1_passed = False
        phase1_output = f"Lockfile validation failed: {e}"
    phase1_duration = time.time() - phase1_start
    hook_results.append(
        HookResult(
            hook_id="phase1-lockfile-validation",
            duration=phase1_duration,
            passed=phase1_passed,
            output=phase1_output,
        )
    )

    # Phase 2: Type Checking (MyPy)
    phase2_start = time.time()
    try:
        result = subprocess.run(
            ["uv", "run", "mypy", "src/mcp_server_langgraph", "--no-error-summary"],
            capture_output=True,
            timeout=180,
        )
        phase2_passed = result.returncode == 0
        phase2_output = f"MyPy: {result.stdout.decode('utf-8', errors='ignore')[:200]}"
    except subprocess.TimeoutExpired:
        phase2_passed = False
        phase2_output = "MyPy timeout"
    phase2_duration = time.time() - phase2_start
    hook_results.append(
        HookResult(
            hook_id="phase2-mypy-type-checking",
            duration=phase2_duration,
            passed=phase2_passed,
            output=phase2_output,
        )
    )

    # Phase 3: Test Suite
    phase3_start = time.time()
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-m", "unit", "-x", "--tb=short"],
            capture_output=True,
            timeout=300,
        )
        phase3_passed = result.returncode == 0
        phase3_output = f"Unit tests: {'PASSED' if phase3_passed else 'FAILED'}"
    except subprocess.TimeoutExpired:
        phase3_passed = False
        phase3_output = "Unit tests timeout"
    phase3_duration = time.time() - phase3_start
    hook_results.append(
        HookResult(
            hook_id="phase3-unit-tests",
            duration=phase3_duration,
            passed=phase3_passed,
            output=phase3_output,
        )
    )

    # Phase 4: Pre-commit hooks (push stage)
    phase4_start = time.time()
    try:
        result = subprocess.run(
            ["pre-commit", "run", "--all-files", "--hook-stage", "push"],
            capture_output=True,
            timeout=600,
        )
        phase4_passed = result.returncode == 0
        phase4_output = f"Pre-commit (push): {'PASSED' if phase4_passed else 'FAILED'}"
    except subprocess.TimeoutExpired:
        phase4_passed = False
        phase4_output = "Pre-commit (push) timeout"
    phase4_duration = time.time() - phase4_start
    hook_results.append(
        HookResult(
            hook_id="phase4-precommit-push",
            duration=phase4_duration,
            passed=phase4_passed,
            output=phase4_output,
        )
    )

    total_duration = time.time() - start_time
    overall_passed = all(r.passed for r in hook_results)

    return StageResult(
        stage="pre-push-phases",
        total_duration=total_duration,
        hook_results=hook_results,
        passed=overall_passed,
    )


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def print_results(stage_result: StageResult) -> None:
    """Print performance results."""
    print("\n" + "=" * 80)
    print(f"📊 {stage_result.stage.upper()} STAGE PERFORMANCE REPORT")
    print("=" * 80)

    # Overall status
    status_emoji = "✅" if stage_result.passed else "❌"
    print(f"\n{status_emoji} Overall Status: {'PASSED' if stage_result.passed else 'FAILED'}")
    print(f"⏱️  Total Duration: {format_duration(stage_result.total_duration)}")

    # Targets
    if "commit" in stage_result.stage.lower():
        target = 30
        target_status = "✅" if stage_result.total_duration < target else "⚠️"
        print(f"{target_status} Target: < {target}s")
    elif "push" in stage_result.stage.lower():
        target = 600  # 10 minutes
        target_status = "✅" if stage_result.total_duration < target else "⚠️"
        print(f"{target_status} Target: < {target // 60}m")

    # Individual hooks/phases
    if len(stage_result.hook_results) > 1:
        print(f"\n📋 Individual Phase Timings:")
        print("-" * 80)
        for hook in sorted(stage_result.hook_results, key=lambda x: x.duration, reverse=True):
            status = "✅" if hook.passed else "❌"
            duration_str = format_duration(hook.duration)
            percentage = (hook.duration / stage_result.total_duration * 100) if stage_result.total_duration > 0 else 0
            print(f"{status} {hook.hook_id:40s} {duration_str:>10s} ({percentage:5.1f}%)")

    # Recommendations
    print(f"\n💡 Recommendations:")
    print("-" * 80)

    if "commit" in stage_result.stage.lower():
        if stage_result.total_duration > 30:
            print("⚠️  Pre-commit hooks exceed 30s target")
            print("   Consider moving slow validators to pre-push stage")
        elif stage_result.total_duration > 15:
            print("⚠️  Pre-commit hooks approaching 30s target")
            print("   Monitor for further increases")
        else:
            print("✅ Pre-commit hooks are fast and responsive")

    elif "push" in stage_result.stage.lower():
        if stage_result.total_duration > 600:
            print("⚠️  Pre-push validation exceeds 10 minute target")
            print("   Consider optimizing slow phases or running in parallel")
        elif stage_result.total_duration > 480:
            print("⚠️  Pre-push validation approaching 10 minute target")
            print("   Monitor for further increases")
        else:
            print("✅ Pre-push validation is comprehensive and efficient")

        # Identify slow phases
        slow_phases = [h for h in stage_result.hook_results if h.duration > 60]
        if slow_phases:
            print(f"\n   Slow phases (> 1 minute):")
            for phase in slow_phases:
                print(f"   - {phase.hook_id}: {format_duration(phase.duration)}")

    print("\n" + "=" * 80)


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Measure pre-commit and pre-push hook performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--stage",
        choices=["commit", "push", "all"],
        default="commit",
        help="Which stage to measure (default: commit)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable detailed profiling (verbose output)",
    )

    args = parser.parse_args()

    try:
        # Ensure we're in a git repository
        repo_root = get_repo_root()
        print(f"📁 Repository: {repo_root}")

        if args.stage in ["commit", "all"]:
            commit_result = measure_pre_commit_hooks("commit", profile=args.profile)
            print_results(commit_result)

        if args.stage in ["push", "all"]:
            if args.stage == "all":
                print("\n")  # Spacing between reports

            # Measure pre-push phases
            push_result = measure_pre_push_phases()
            print_results(push_result)

        return 0

    except Exception as e:
        print(f"❌ Error measuring hook performance: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
