#!/usr/bin/env python3
"""
Hook Performance Profiling Script

Measures execution time of all pre-commit hooks to identify candidates
for moving from commit stage to pre-push stage.

Usage:
    python scripts/profiling/profile_hooks.py --scenario typical --iterations 10
    python scripts/profiling/profile_hooks.py --all-scenarios --format json
    python scripts/profiling/profile_hooks.py --hook-id ruff-format --iterations 50

Performance Target:
- Commit stage: <2 seconds (fast feedback for developers)
- Pre-push stage: 8-12 minutes (comprehensive validation before push)
"""

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


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

    def _load_hooks(self) -> list[dict[str, Any]]:
        """Load hook configurations from .pre-commit-config.yaml."""
        if not self.config_path.exists():
            print(f"Error: {self.config_path} not found", file=sys.stderr)
            sys.exit(1)

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_data = {
                    "id": hook.get("id"),
                    "name": hook.get("name", hook.get("id")),
                    "stages": hook.get("stages", ["commit"]),
                    "repo": repo.get("repo"),
                }
                hooks.append(hook_data)

        return hooks

    def profile_hook(self, hook_id: str, iterations: int = 10) -> HookPerformance:
        """Profile a single hook."""
        # Find hook info
        hook_info = None
        for hook in self.hooks:
            if hook["id"] == hook_id:
                hook_info = hook
                break

        if not hook_info:
            print(f"Error: Hook '{hook_id}' not found in config", file=sys.stderr)
            sys.exit(1)

        print(f"Profiling {hook_id} ({iterations} iterations)...", file=sys.stderr)

        timings = []
        for i in range(iterations):
            start = time.perf_counter()

            # Run hook via pre-commit
            subprocess.run(
                ["pre-commit", "run", hook_id, "--all-files"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            timings.append(elapsed_ms)

            # Progress indicator
            if (i + 1) % 5 == 0:
                print(f"  {i + 1}/{iterations} complete...", file=sys.stderr)

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

        # Determine primary stage
        stages = hook_info["stages"]
        if "push" in stages or "pre-push" in stages:
            stage = "push"
        elif "manual" in stages:
            stage = "manual"
        else:
            stage = "commit"

        return HookPerformance(
            hook_id=hook_id,
            hook_name=hook_info["name"],
            stage=stage,
            iterations=iterations,
            mean_ms=mean,
            median_ms=median,
            p90_ms=p90,
            p95_ms=p95,
            p99_ms=p99,
            min_ms=min_val,
            max_ms=max_val,
            stddev_ms=stddev,
            category=category,
        )

    def profile_all(self, iterations: int = 10) -> list[HookPerformance]:
        """Profile all hooks."""
        results = []
        total = len(self.hooks)

        print(f"\n🔍 Profiling {total} hooks ({iterations} iterations each)...\n", file=sys.stderr)

        for idx, hook in enumerate(self.hooks, 1):
            print(f"[{idx}/{total}] {hook['id']}", file=sys.stderr)
            try:
                perf = self.profile_hook(hook["id"], iterations)
                results.append(perf)
                print(f"  ✓ {perf.mean_ms:.0f}ms (p90: {perf.p90_ms:.0f}ms) - {perf.category}\n", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("  ⚠️  Timeout (>5min) - skipping\n", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Error: {e}\n", file=sys.stderr)

        return results

    def export_json(self, results: list[HookPerformance], output_path: Path):
        """Export results to JSON."""
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_hooks": len(results),
            "summary": {
                "fast": len([r for r in results if r.category == "fast"]),
                "medium": len([r for r in results if r.category == "medium"]),
                "heavy": len([r for r in results if r.category == "heavy"]),
            },
            "hooks": [asdict(r) for r in results],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✓ JSON report: {output_path}", file=sys.stderr)

    def export_csv(self, results: list[HookPerformance], output_path: Path):
        """Export results to CSV."""
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "hook_id",
                    "hook_name",
                    "stage",
                    "category",
                    "iterations",
                    "mean_ms",
                    "median_ms",
                    "p90_ms",
                    "p95_ms",
                    "p99_ms",
                    "min_ms",
                    "max_ms",
                    "stddev_ms",
                ],
            )
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))

        print(f"✓ CSV report: {output_path}", file=sys.stderr)

    def export_markdown(self, results: list[HookPerformance], output_path: Path):
        """Export results to Markdown table."""
        # Group by category
        fast = [r for r in results if r.category == "fast"]
        medium = [r for r in results if r.category == "medium"]
        heavy = [r for r in results if r.category == "heavy"]

        with open(output_path, "w") as f:
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

        print(f"✓ Markdown report: {output_path}", file=sys.stderr)

    def _write_table(self, f, results: list[HookPerformance]):
        """Write results as Markdown table."""
        f.write("| Hook ID | Stage | Mean | p90 | p95 | Category |\n")
        f.write("|---------|-------|------|-----|-----|----------|\n")
        for r in results:
            f.write(
                f"| `{r.hook_id}` | {r.stage} | {r.mean_ms:.0f}ms | {r.p90_ms:.0f}ms | {r.p95_ms:.0f}ms | {r.category} |\n"
            )

    @staticmethod
    def _percentile(data: list[float], p: float) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]


def main():
    parser = argparse.ArgumentParser(description="Profile pre-commit hooks to measure execution time")
    parser.add_argument("--hook-id", help="Profile specific hook by ID")
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per hook (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown", "all"],
        default="all",
        help="Output format",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs-internal/profiling"),
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Ensure we're in repo root
    if not Path(".pre-commit-config.yaml").exists():
        print("Error: Must run from repository root", file=sys.stderr)
        sys.exit(1)

    profiler = HookProfiler()

    if args.hook_id:
        # Profile single hook
        result = profiler.profile_hook(args.hook_id, args.iterations)
        print(f"\n📊 Results for {args.hook_id}:")
        print(f"  Mean: {result.mean_ms:.0f}ms")
        print(f"  p90: {result.p90_ms:.0f}ms")
        print(f"  p95: {result.p95_ms:.0f}ms")
        print(f"  Category: {result.category}")
    else:
        # Profile all hooks
        results = profiler.profile_all(args.iterations)

        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Export results
        if args.format in ("json", "all"):
            profiler.export_json(results, args.output_dir / "hooks_performance.json")

        if args.format in ("csv", "all"):
            profiler.export_csv(results, args.output_dir / "hooks_performance.csv")

        if args.format in ("markdown", "all"):
            profiler.export_markdown(results, args.output_dir / "hooks_performance.md")

        print(f"\n✅ Profiling complete! ({len(results)} hooks)")


if __name__ == "__main__":
    main()
# Test comment
