#!/usr/bin/env python3
"""
Alert Coverage Report Generator

Analyzes Prometheus/Mimir alert rules and generates a comprehensive
coverage report showing:
- Total alerts by category and severity
- Dashboard-alert linking status
- Critical paths without alerts
- Runbook coverage for critical alerts

Usage:
    python scripts/alert-coverage-report.py [OPTIONS]

Options:
    --format FORMAT   Output format: text, json, markdown (default: text)
    --output FILE     Write report to file (default: stdout)
    --verbose         Show detailed output
    --help            Show this help message

Examples:
    # Generate text report
    python scripts/alert-coverage-report.py

    # Generate markdown report for documentation
    python scripts/alert-coverage-report.py --format markdown --output ALERT_COVERAGE.md

    # Generate JSON report for CI integration
    python scripts/alert-coverage-report.py --format json --output alert-coverage.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Alert:
    """Represents a Prometheus alert."""

    name: str
    expr: str
    severity: str
    category: str
    file_path: str
    has_runbook: bool
    has_dashboard_link: bool
    for_duration: str | None


@dataclass
class CoverageReport:
    """Alert coverage report data."""

    total_alerts: int = 0
    alerts_by_severity: dict[str, int] = field(default_factory=dict)
    alerts_by_category: dict[str, int] = field(default_factory=dict)
    alerts_by_file: dict[str, int] = field(default_factory=dict)
    critical_without_runbook: list[str] = field(default_factory=list)
    alerts_without_dashboard: list[str] = field(default_factory=list)
    alerts_without_for: list[str] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)


# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CANONICAL_RULES_DIR = PROJECT_ROOT / "monitoring" / "prometheus" / "rules"
MIMIR_RULES_DIR = PROJECT_ROOT / "docker" / "mimir" / "rules"


# Category patterns
CATEGORY_PATTERNS = {
    "service_health": re.compile(r"(Down|Unavailable|NotRunning|Unhealthy)", re.I),
    "performance": re.compile(r"(Slow|HighLatency|ResponseTime|Duration)", re.I),
    "errors": re.compile(r"(Error|Failure|Failed|Exception)", re.I),
    "resources": re.compile(r"(HighMemory|HighCPU|Exhausted|OOM|Pressure)", re.I),
    "security": re.compile(r"(Unauthorized|Security|Suspicious|Auth)", re.I),
    "slo": re.compile(r"(SLO|Budget|Breach|SLA)", re.I),
    "streaming": re.compile(r"(Stream|TTFC|WebSocket|Realtime)", re.I),
    "cost": re.compile(r"(Cost|Token|Usage|Spending)", re.I),
    "hitl": re.compile(r"(HITL|Intervention|Human)", re.I),
    "resilience": re.compile(r"(Circuit|Retry|Timeout|Bulkhead|Fallback)", re.I),
}


def load_yaml_file(file_path: Path) -> dict[str, Any] | None:
    """Load and parse a YAML file."""
    try:
        with open(file_path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError):
        return None


def is_k8s_crd_format(content: dict[str, Any]) -> bool:
    """Check if content is in Kubernetes PrometheusRule CRD format."""
    if not content or not isinstance(content, dict):
        return False
    api_version = content.get("apiVersion", "")
    kind = content.get("kind", "")
    return "monitoring.coreos.com" in api_version and kind == "PrometheusRule"


def extract_alerts(content: dict[str, Any], file_path: Path) -> list[Alert]:
    """Extract alerts from rule file."""
    alerts = []

    if is_k8s_crd_format(content):
        groups = content.get("spec", {}).get("groups", [])
    else:
        groups = content.get("groups", [])

    for group in groups:
        for rule in group.get("rules", []):
            if "alert" not in rule:
                continue  # Recording rule

            alert_name = rule.get("alert")
            labels = rule.get("labels", {})
            annotations = rule.get("annotations", {})

            # Determine category
            category = "other"
            for cat_name, pattern in CATEGORY_PATTERNS.items():
                if pattern.search(alert_name):
                    category = cat_name
                    break

            alert = Alert(
                name=alert_name,
                expr=rule.get("expr", ""),
                severity=labels.get("severity", "unknown"),
                category=category,
                file_path=str(file_path.relative_to(PROJECT_ROOT)),
                has_runbook="runbook_url" in annotations,
                has_dashboard_link="dashboard_url" in annotations or "dashboard" in annotations,
                for_duration=rule.get("for"),
            )
            alerts.append(alert)

    return alerts


def generate_report(rules_dir: Path) -> CoverageReport:
    """Generate coverage report for all alerts in a directory."""
    report = CoverageReport()

    if not rules_dir.exists():
        return report

    for rule_file in rules_dir.glob("*.y*ml"):
        content = load_yaml_file(rule_file)
        if not content:
            continue

        alerts = extract_alerts(content, rule_file)

        for alert in alerts:
            report.total_alerts += 1
            report.alerts.append(alert)

            # By severity
            if alert.severity not in report.alerts_by_severity:
                report.alerts_by_severity[alert.severity] = 0
            report.alerts_by_severity[alert.severity] += 1

            # By category
            if alert.category not in report.alerts_by_category:
                report.alerts_by_category[alert.category] = 0
            report.alerts_by_category[alert.category] += 1

            # By file
            if alert.file_path not in report.alerts_by_file:
                report.alerts_by_file[alert.file_path] = 0
            report.alerts_by_file[alert.file_path] += 1

            # Track issues
            if alert.severity == "critical" and not alert.has_runbook:
                report.critical_without_runbook.append(f"{alert.file_path}: {alert.name}")

            if not alert.has_dashboard_link:
                report.alerts_without_dashboard.append(f"{alert.file_path}: {alert.name}")

            if not alert.for_duration:
                report.alerts_without_for.append(f"{alert.file_path}: {alert.name}")

    return report


def format_text_report(report: CoverageReport) -> str:
    """Format report as plain text."""
    lines = []
    lines.append("=" * 60)
    lines.append("ALERT COVERAGE REPORT")
    lines.append("=" * 60)
    lines.append(f"\nTotal Alerts: {report.total_alerts}")

    lines.append("\n--- Alerts by Severity ---")
    for severity, count in sorted(report.alerts_by_severity.items()):
        pct = (count / report.total_alerts * 100) if report.total_alerts > 0 else 0
        lines.append(f"  {severity}: {count} ({pct:.1f}%)")

    lines.append("\n--- Alerts by Category ---")
    for category, count in sorted(report.alerts_by_category.items()):
        pct = (count / report.total_alerts * 100) if report.total_alerts > 0 else 0
        lines.append(f"  {category}: {count} ({pct:.1f}%)")

    lines.append("\n--- Alerts by File ---")
    for file_path, count in sorted(report.alerts_by_file.items()):
        lines.append(f"  {file_path}: {count}")

    # Issues section
    if report.critical_without_runbook:
        lines.append(f"\n--- Critical Alerts Without Runbook ({len(report.critical_without_runbook)}) ---")
        for alert in report.critical_without_runbook[:10]:
            lines.append(f"  ⚠️  {alert}")
        if len(report.critical_without_runbook) > 10:
            lines.append(f"  ... and {len(report.critical_without_runbook) - 10} more")

    runbook_coverage = report.total_alerts - len(report.alerts_without_for)
    dashboard_coverage = report.total_alerts - len(report.alerts_without_dashboard)

    lines.append("\n--- Coverage Metrics ---")
    lines.append(
        f"  Runbook URL Coverage: {runbook_coverage}/{report.total_alerts} "
        f"({runbook_coverage / report.total_alerts * 100:.1f}%)"
        if report.total_alerts
        else "  N/A"
    )
    lines.append(
        f"  Dashboard Link Coverage: {dashboard_coverage}/{report.total_alerts} "
        f"({dashboard_coverage / report.total_alerts * 100:.1f}%)"
        if report.total_alerts
        else "  N/A"
    )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def format_markdown_report(report: CoverageReport) -> str:
    """Format report as markdown."""
    lines = []
    lines.append("# Alert Coverage Report\n")
    lines.append(f"**Total Alerts:** {report.total_alerts}\n")

    lines.append("## Severity Distribution\n")
    lines.append("| Severity | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    for severity, count in sorted(report.alerts_by_severity.items()):
        pct = (count / report.total_alerts * 100) if report.total_alerts > 0 else 0
        lines.append(f"| {severity} | {count} | {pct:.1f}% |")

    lines.append("\n## Category Distribution\n")
    lines.append("| Category | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    for category, count in sorted(report.alerts_by_category.items()):
        pct = (count / report.total_alerts * 100) if report.total_alerts > 0 else 0
        lines.append(f"| {category} | {count} | {pct:.1f}% |")

    lines.append("\n## Alerts by File\n")
    lines.append("| File | Count |")
    lines.append("|------|-------|")
    for file_path, count in sorted(report.alerts_by_file.items()):
        lines.append(f"| `{file_path}` | {count} |")

    if report.critical_without_runbook:
        lines.append(f"\n## ⚠️ Critical Alerts Without Runbook ({len(report.critical_without_runbook)})\n")
        for alert in report.critical_without_runbook[:20]:
            lines.append(f"- `{alert}`")
        if len(report.critical_without_runbook) > 20:
            lines.append(f"- *... and {len(report.critical_without_runbook) - 20} more*")

    return "\n".join(lines)


def format_json_report(report: CoverageReport) -> str:
    """Format report as JSON."""
    data = {
        "total_alerts": report.total_alerts,
        "alerts_by_severity": report.alerts_by_severity,
        "alerts_by_category": report.alerts_by_category,
        "alerts_by_file": report.alerts_by_file,
        "issues": {
            "critical_without_runbook": report.critical_without_runbook,
            "alerts_without_dashboard": len(report.alerts_without_dashboard),
            "alerts_without_for": len(report.alerts_without_for),
        },
    }
    return json.dumps(data, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate alert coverage report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write report to file (default: stdout)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    # Generate report from canonical rules directory
    report = generate_report(CANONICAL_RULES_DIR)

    # Format report
    if args.format == "text":
        output = format_text_report(report)
    elif args.format == "markdown":
        output = format_markdown_report(report)
    elif args.format == "json":
        output = format_json_report(report)
    else:
        output = format_text_report(report)

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
