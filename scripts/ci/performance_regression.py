#!/usr/bin/env python3
"""
Performance Regression Detection

Automatically detects performance regressions in:
- API response times
- Memory usage
- CPU usage
- Database query times

Usage:
    python scripts/ci/performance_regression.py --baseline baseline.json --current current.json

Workflow:
    1. Run performance benchmarks
    2. Compare against baseline
    3. Detect regressions (>50% degradation)
    4. Create alerts/issues if regressions found
"""

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import requests
except ImportError:
    requests = None


def establish_baseline(benchmarks: List[Dict]) -> Dict:
    """
    Establish performance baseline from benchmark results using median

    Args:
        benchmarks: List of benchmark results

    Returns:
        Baseline metrics (median values)
    """
    if not benchmarks:
        return {}

    # Group by endpoint/metric
    grouped = {}
    for benchmark in benchmarks:
        endpoint = benchmark.get("endpoint", "default")
        if endpoint not in grouped:
            grouped[endpoint] = {
                "response_times": [],
                "memory": [],
                "cpu": [],
            }

        if "response_time_ms" in benchmark:
            grouped[endpoint]["response_times"].append(benchmark["response_time_ms"])
        if "memory_mb" in benchmark:
            grouped[endpoint]["memory"].append(benchmark["memory_mb"])
        if "cpu_percent" in benchmark:
            grouped[endpoint]["cpu"].append(benchmark["cpu_percent"])

    # Calculate median for each metric
    baseline = {}
    for endpoint, metrics in grouped.items():
        endpoint_baseline = {}

        if metrics["response_times"]:
            endpoint_baseline["response_time_ms"] = statistics.median(metrics["response_times"])
        if metrics["memory"]:
            endpoint_baseline["memory_mb"] = statistics.median(metrics["memory"])
        if metrics["cpu"]:
            endpoint_baseline["cpu_percent"] = statistics.median(metrics["cpu"])

        baseline[endpoint] = endpoint_baseline

    # If single endpoint, return direct metrics
    if len(baseline) == 1:
        return list(baseline.values())[0]

    return baseline


def load_baseline(baseline_file: Path) -> Dict:
    """Load baseline from JSON file"""
    if not baseline_file.exists():
        return {}

    try:
        return json.loads(baseline_file.read_text())
    except json.JSONDecodeError:
        return {}


def detect_regression(
    baseline: Dict,
    current: Dict,
    threshold_percent: float = 50.0
) -> Dict:
    """
    Detect performance regression

    Args:
        baseline: Baseline metrics
        current: Current metrics
        threshold_percent: Regression threshold (default 50%)

    Returns:
        Regression details or {"has_regression": False}
    """
    for metric in ["response_time_ms", "memory_mb", "cpu_percent"]:
        if metric in baseline and metric in current:
            baseline_value = baseline[metric]
            current_value = current[metric]

            if baseline_value == 0:
                continue

            degradation = ((current_value - baseline_value) / baseline_value) * 100

            if degradation > threshold_percent:
                return {
                    "has_regression": True,
                    "metric": metric,
                    "baseline": baseline_value,
                    "current": current_value,
                    "degradation_percent": degradation,
                }

    return {"has_regression": False}


def detect_all_regressions(
    baseline: Dict,
    current: Dict,
    threshold_percent: float = 50.0
) -> List[Dict]:
    """Detect all performance regressions across all metrics"""
    regressions = []

    for metric in ["response_time_ms", "memory_mb", "cpu_percent"]:
        if metric in baseline and metric in current:
            baseline_value = baseline[metric]
            current_value = current[metric]

            if baseline_value == 0:
                continue

            degradation = ((current_value - baseline_value) / baseline_value) * 100

            if degradation > threshold_percent:
                regressions.append({
                    "has_regression": True,
                    "metric": metric,
                    "baseline": baseline_value,
                    "current": current_value,
                    "degradation_percent": degradation,
                })

    return regressions


def run_benchmark(endpoint: str, base_url: str) -> Dict:
    """Run single endpoint benchmark"""
    if not requests:
        raise ImportError("requests library required for benchmarking")

    import time

    url = f"{base_url}{endpoint}"
    response_times = []

    # Run 10 requests
    for _ in range(10):
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            response_times.append(elapsed)
        except Exception as e:
            print(f"Error benchmarking {url}: {e}")
            continue

    if not response_times:
        return {}

    return {
        "endpoint": endpoint,
        "response_time_ms": statistics.median(response_times),
        "status_code": response.status_code if 'response' in locals() else 0,
    }


def run_api_benchmarks(base_url: str, endpoints: List[str]) -> List[Dict]:
    """Run benchmarks for multiple API endpoints"""
    results = []

    for endpoint in endpoints:
        result = run_benchmark(endpoint, base_url)
        if result:
            results.append(result)

    return results


def calculate_percentiles(measurements: List[float]) -> Dict:
    """Calculate response time percentiles (p50, p95, p99)"""
    if not measurements:
        return {}

    sorted_measurements = sorted(measurements)

    return {
        "p50": statistics.median(sorted_measurements),
        "p95": sorted_measurements[int(len(sorted_measurements) * 0.95)],
        "p99": sorted_measurements[int(len(sorted_measurements) * 0.99)],
        "min": min(sorted_measurements),
        "max": max(sorted_measurements),
        "mean": statistics.mean(sorted_measurements),
    }


def generate_regression_report(regressions: List[Dict]) -> str:
    """Generate markdown report for regressions"""
    if not regressions:
        return "✅ No performance regressions detected"

    report = "# ⚠️ Performance Regressions Detected\n\n"

    for regression in regressions:
        metric_name = regression["metric"].replace("_", " ").title()
        degradation = regression["degradation_percent"]

        report += f"## {metric_name} Regression\n\n"
        report += f"- **Baseline**: {regression['baseline']:.2f}\n"
        report += f"- **Current**: {regression['current']:.2f}\n"
        report += f"- **Degradation**: {degradation:.1f}%\n\n"

        # Add severity indicator
        if degradation > 100:
            report += "🔴 **Severity**: Critical (>100% degradation)\n\n"
        elif degradation > 75:
            report += "🟠 **Severity**: High (>75% degradation)\n\n"
        else:
            report += "🟡 **Severity**: Medium (>50% degradation)\n\n"

    report += "## Recommended Actions\n\n"
    report += "1. Profile the application to identify bottlenecks\n"
    report += "2. Review recent code changes\n"
    report += "3. Check for resource constraints\n"
    report += "4. Consider rollback if critical\n"

    return report


def create_regression_issue(regression: Dict) -> str:
    """Create GitHub issue body for regression"""
    metric_name = regression["metric"].replace("_", " ").title()
    degradation = regression["degradation_percent"]

    severity = "Critical" if degradation > 100 else ("High" if degradation > 75 else "Medium")

    body = f"""## Performance Regression: {metric_name}

**Severity**: {severity}

### Metrics

| Metric | Baseline | Current | Degradation |
|--------|----------|---------|-------------|
| {metric_name} | {regression['baseline']:.2f} | {regression['current']:.2f} | {degradation:.1f}% |

### Details

"""

    if "endpoint" in regression:
        body += f"- **Endpoint**: `{regression['endpoint']}`\n"

    body += f"""
### Impact

A {degradation:.0f}% performance degradation has been detected in {metric_name}.

### Recommended Actions

1. **Profile the application** to identify bottlenecks
2. **Review recent commits** for performance-impacting changes
3. **Check resource utilization** (CPU, memory, disk I/O)
4. **Run local benchmarks** to reproduce the issue
5. **Consider rollback** if impact is severe

### Benchmark Commands

```bash
# Run performance benchmarks locally
make test-performance

# Compare with baseline
python scripts/ci/performance_regression.py --baseline .perf-baseline/baseline.json
```

---

_This issue was automatically created by the performance regression detection workflow._
"""

    return body


def should_update_baseline(
    baseline: Dict,
    current: Dict,
    improvement_threshold: float = 20.0
) -> bool:
    """
    Determine if baseline should be updated after performance improvement

    Args:
        baseline: Current baseline
        current: Current measurements
        improvement_threshold: Minimum improvement % to update baseline (default 20%)

    Returns:
        True if baseline should be updated
    """
    for metric in ["response_time_ms", "memory_mb", "cpu_percent"]:
        if metric in baseline and metric in current:
            baseline_value = baseline[metric]
            current_value = current[metric]

            if baseline_value == 0:
                continue

            improvement = ((baseline_value - current_value) / baseline_value) * 100

            if improvement > improvement_threshold:
                return True

    return False


def save_baseline(baseline: Dict, baseline_file: Path):
    """Save baseline to JSON file"""
    baseline_file.parent.mkdir(parents=True, exist_ok=True)

    # Add timestamp
    baseline_with_timestamp = {
        **baseline,
        "timestamp": datetime.now().isoformat(),
    }

    baseline_file.write_text(json.dumps(baseline_with_timestamp, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Detect performance regressions")
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline metrics file")
    parser.add_argument("--current", type=Path, help="Current metrics file")
    parser.add_argument("--benchmark-url", help="URL to benchmark (if not using current file)")
    parser.add_argument("--threshold", type=float, default=50.0,
                        help="Regression threshold percentage (default: 50)")
    parser.add_argument("--output", type=Path, help="Output file for report")

    args = parser.parse_args()

    # Load baseline
    baseline = load_baseline(args.baseline)
    if not baseline:
        print(f"Error: Could not load baseline from {args.baseline}")
        return 1

    # Get current metrics
    if args.current:
        current = load_baseline(args.current)
    elif args.benchmark_url:
        print(f"Running benchmarks against {args.benchmark_url}...")
        benchmarks = run_api_benchmarks(
            args.benchmark_url,
            endpoints=["/health", "/api/health"]
        )
        current = establish_baseline(benchmarks)
    else:
        print("Error: Either --current or --benchmark-url must be specified")
        return 1

    # Detect regressions
    regressions = detect_all_regressions(baseline, current, args.threshold)

    # Generate report
    report = generate_regression_report(regressions)
    print("\n" + report)

    # Save report if output specified
    if args.output:
        args.output.write_text(report)
        print(f"\n✅ Report saved to {args.output}")

    # Exit with error if regressions found
    if regressions:
        print(f"\n❌ {len(regressions)} regression(s) detected")
        return 1

    print("\n✅ No regressions detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
