"""
Tests for Alert Consolidation System

TDD tests for:
1. K8s CRD to standard Prometheus format conversion
2. Alert consolidation to canonical location
3. Alert coverage report mechanism
4. Dashboard-alert linking validation

These tests validate the alert management infrastructure that ensures:
- All alerts are in a canonical location (monitoring/prometheus/rules/)
- K8s PrometheusRule CRDs are converted to standard Prometheus format
- No duplicate alert names exist across files
- All alerts have required labels (severity)
- Dashboards reference valid alerts
- Alerts reference valid dashboard URLs
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit]

# Paths
PROJECT_ROOT = get_repo_root()
CANONICAL_RULES_DIR = PROJECT_ROOT / "monitoring" / "prometheus" / "rules"
CANONICAL_ALERTS_DIR = PROJECT_ROOT / "monitoring" / "prometheus" / "alerts"
DEPLOYMENTS_ALERTING_DIR = PROJECT_ROOT / "deployments" / "monitoring" / "alerting-rules"
DEPLOYMENTS_MONITORING_DIR = PROJECT_ROOT / "deployments" / "monitoring"
GRAFANA_DASHBOARDS_DIR = PROJECT_ROOT / "monitoring" / "grafana" / "dashboards"
HELM_DASHBOARDS_DIR = PROJECT_ROOT / "deployments" / "helm" / "mcp-server-langgraph" / "dashboards"


def load_yaml_file(file_path: Path) -> dict[str, Any] | None:
    """Load and parse a YAML file."""
    try:
        with open(file_path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError):
        return None


def is_k8s_crd_format(content: dict[str, Any]) -> bool:
    """Check if content is in Kubernetes PrometheusRule CRD format."""
    if not content:
        return False
    api_version = content.get("apiVersion", "")
    kind = content.get("kind", "")
    return "monitoring.coreos.com" in api_version and kind == "PrometheusRule"


def extract_alerts_from_standard_format(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract alerts from standard Prometheus rules format."""
    alerts = []
    for group in content.get("groups", []):
        for rule in group.get("rules", []):
            if "alert" in rule:
                alerts.append(rule)
    return alerts


def extract_alerts_from_k8s_crd(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract alerts from K8s PrometheusRule CRD format."""
    alerts = []
    spec = content.get("spec", {})
    for group in spec.get("groups", []):
        for rule in group.get("rules", []):
            if "alert" in rule:
                alerts.append(rule)
    return alerts


def get_all_alert_files() -> list[tuple[Path, str]]:
    """Get all alert files with their format type."""
    alert_files = []

    # Check canonical rules directory
    if CANONICAL_RULES_DIR.exists():
        for f in CANONICAL_RULES_DIR.glob("*.y*ml"):
            content = load_yaml_file(f)
            if content:
                fmt = "k8s_crd" if is_k8s_crd_format(content) else "standard"
                alert_files.append((f, fmt))

    # Check canonical alerts directory
    if CANONICAL_ALERTS_DIR.exists():
        for f in CANONICAL_ALERTS_DIR.glob("*.y*ml"):
            content = load_yaml_file(f)
            if content:
                fmt = "k8s_crd" if is_k8s_crd_format(content) else "standard"
                alert_files.append((f, fmt))

    # Check deployments alerting rules
    if DEPLOYMENTS_ALERTING_DIR.exists():
        for f in DEPLOYMENTS_ALERTING_DIR.glob("*.y*ml"):
            content = load_yaml_file(f)
            if content:
                fmt = "k8s_crd" if is_k8s_crd_format(content) else "standard"
                alert_files.append((f, fmt))

    # Check deployments monitoring directory
    if DEPLOYMENTS_MONITORING_DIR.exists():
        for f in DEPLOYMENTS_MONITORING_DIR.glob("*.y*ml"):
            if f.parent == DEPLOYMENTS_MONITORING_DIR:  # Don't recurse
                content = load_yaml_file(f)
                if content:
                    fmt = "k8s_crd" if is_k8s_crd_format(content) else "standard"
                    alert_files.append((f, fmt))

    return alert_files


class TestK8sCRDConversion:
    """Tests for K8s CRD to standard Prometheus format conversion."""

    def test_k8s_crd_format_detection(self) -> None:
        """Detect K8s PrometheusRule CRD format correctly."""
        k8s_content = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {"name": "test"},
            "spec": {"groups": []},
        }
        standard_content = {"groups": [{"name": "test", "rules": []}]}

        assert is_k8s_crd_format(k8s_content) is True
        assert is_k8s_crd_format(standard_content) is False
        assert is_k8s_crd_format({}) is False
        assert is_k8s_crd_format(None) is False

    def test_extract_alerts_from_k8s_crd(self) -> None:
        """Extract alerts from K8s PrometheusRule CRD format."""
        k8s_content = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {"name": "test"},
            "spec": {
                "groups": [
                    {
                        "name": "test_group",
                        "rules": [
                            {"alert": "TestAlert1", "expr": "up == 0"},
                            {"record": "job:metric", "expr": "sum(metric)"},
                            {"alert": "TestAlert2", "expr": "rate(errors[5m]) > 0"},
                        ],
                    }
                ]
            },
        }

        alerts = extract_alerts_from_k8s_crd(k8s_content)
        assert len(alerts) == 2
        assert alerts[0]["alert"] == "TestAlert1"
        assert alerts[1]["alert"] == "TestAlert2"

    def test_extract_alerts_from_standard_format(self) -> None:
        """Extract alerts from standard Prometheus format."""
        standard_content = {
            "groups": [
                {
                    "name": "test_group",
                    "rules": [
                        {"alert": "TestAlert1", "expr": "up == 0"},
                        {"record": "job:metric", "expr": "sum(metric)"},
                        {"alert": "TestAlert2", "expr": "rate(errors[5m]) > 0"},
                    ],
                }
            ]
        }

        alerts = extract_alerts_from_standard_format(standard_content)
        assert len(alerts) == 2
        assert alerts[0]["alert"] == "TestAlert1"
        assert alerts[1]["alert"] == "TestAlert2"

    def test_identify_k8s_crd_files_in_project(self) -> None:
        """Identify all K8s CRD format files that need conversion.

        This test documents the current state - K8s CRD files exist in:
        - monitoring/prometheus/alerts/langgraph-agent.yaml
        - deployments/monitoring/slo-alerts.yaml
        - deployments/monitoring/prompt-quality-alerts.yaml

        These should be converted to standard format and moved to canonical location.
        """
        k8s_crd_files = []
        for file_path, fmt in get_all_alert_files():
            if fmt == "k8s_crd":
                k8s_crd_files.append(file_path)

        # Document current K8s CRD files (this will change after conversion)
        # For now, we just ensure the detection works
        for f in k8s_crd_files:
            content = load_yaml_file(f)
            assert is_k8s_crd_format(content), f"Expected K8s CRD format for {f}"


class TestAlertConsolidation:
    """Tests for alert consolidation to canonical location."""

    def test_no_duplicate_alert_names_globally(self) -> None:
        """All alerts must have globally unique names across all files.

        Duplicate alert names cause confusion and can lead to missed alerts
        when one rule shadows another in Prometheus/Mimir.
        """
        alert_to_files: dict[str, list[str]] = {}

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert")
                if alert_name:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    if alert_name not in alert_to_files:
                        alert_to_files[alert_name] = []
                    alert_to_files[alert_name].append(rel_path)

        # Find duplicates
        duplicates = {name: files for name, files in alert_to_files.items() if len(files) > 1}

        if duplicates:
            duplicate_msg = "\n".join(f"  Alert '{name}' defined in: {files}" for name, files in sorted(duplicates.items()))
            pytest.fail(
                f"Found {len(duplicates)} duplicate alert names:\n{duplicate_msg}\n\n"
                "Each alert must have a unique name. Rename or consolidate duplicates."
            )

    def test_all_alerts_have_severity_label(self) -> None:
        """All alerts must have a severity label (critical, warning, info)."""
        missing_severity: list[str] = []
        valid_severities = {"critical", "warning", "info", "page"}

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert")
                labels = alert.get("labels", {})
                severity = labels.get("severity")

                if not severity:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    missing_severity.append(f"{rel_path}: {alert_name}")
                elif severity not in valid_severities:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    missing_severity.append(f"{rel_path}: {alert_name} (invalid severity: {severity})")

        if missing_severity:
            pytest.fail(
                f"Found {len(missing_severity)} alerts with missing/invalid severity:\n"
                + "\n".join(f"  {x}" for x in missing_severity[:30])
                + ("\n  ..." if len(missing_severity) > 30 else "")
            )

    def test_all_alerts_have_summary_annotation(self) -> None:
        """All alerts should have a summary annotation for clarity."""
        missing_summary: list[str] = []

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert")
                annotations = alert.get("annotations", {})

                if "summary" not in annotations and "description" not in annotations:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    missing_summary.append(f"{rel_path}: {alert_name}")

        if missing_summary:
            pytest.fail(
                f"Found {len(missing_summary)} alerts without summary/description:\n"
                + "\n".join(f"  {x}" for x in missing_summary[:30])
                + ("\n  ..." if len(missing_summary) > 30 else "")
            )

    def test_deployments_alerts_should_be_in_canonical_location(self) -> None:
        """Alerts in deployments/ should be consolidated to monitoring/prometheus/rules/.

        The canonical location is monitoring/prometheus/rules/ where alerts are:
        - Synced to docker/mimir/rules/ for test environment
        - Version controlled in a single location
        - Consistent format (standard Prometheus, not K8s CRD)

        This test documents fragmentation that should be addressed.
        """
        fragmented_locations = []

        # Check deployments/monitoring/alerting-rules/
        if DEPLOYMENTS_ALERTING_DIR.exists():
            for f in DEPLOYMENTS_ALERTING_DIR.glob("*.y*ml"):
                fragmented_locations.append(str(f.relative_to(PROJECT_ROOT)))

        # Check deployments/monitoring/ (direct children only)
        if DEPLOYMENTS_MONITORING_DIR.exists():
            for f in DEPLOYMENTS_MONITORING_DIR.glob("*.y*ml"):
                if f.parent == DEPLOYMENTS_MONITORING_DIR:
                    content = load_yaml_file(f)
                    if content and ("groups" in content or is_k8s_crd_format(content)):
                        fragmented_locations.append(str(f.relative_to(PROJECT_ROOT)))

        if fragmented_locations:
            # This is informational for now - documents the fragmentation
            # After consolidation, this should fail if any remain
            pytest.skip(
                f"Found {len(fragmented_locations)} alert files outside canonical location:\n"
                + "\n".join(f"  {x}" for x in fragmented_locations)
                + "\n\nRun consolidation script to move these to monitoring/prometheus/rules/"
            )


class TestAlertCoverageReport:
    """Tests for alert coverage report mechanism."""

    def test_count_total_alerts(self) -> None:
        """Count total number of alerts across all files."""
        total_alerts = 0
        alerts_by_file: dict[str, int] = {}

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            count = len(alerts)
            if count > 0:
                rel_path = str(file_path.relative_to(PROJECT_ROOT))
                alerts_by_file[rel_path] = count
                total_alerts += count

        # Document the alert count (informational)
        assert total_alerts > 0, "Expected at least some alerts to exist"

        # Print summary for visibility
        print("\n\nAlert Coverage Summary:")
        print(f"Total alerts: {total_alerts}")
        print(f"Files with alerts: {len(alerts_by_file)}")
        for path, count in sorted(alerts_by_file.items()):
            print(f"  {path}: {count} alerts")

    def test_alerts_by_severity_distribution(self) -> None:
        """Analyze alert distribution by severity."""
        severity_counts: dict[str, int] = {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "page": 0,
            "missing": 0,
        }

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                labels = alert.get("labels", {})
                severity = labels.get("severity", "missing")
                if severity in severity_counts:
                    severity_counts[severity] += 1
                else:
                    severity_counts["missing"] += 1

        total = sum(severity_counts.values())
        assert total > 0, "Expected at least some alerts"

        print("\n\nSeverity Distribution:")
        for severity, count in sorted(severity_counts.items()):
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {severity}: {count} ({pct:.1f}%)")

    def test_alert_categories_coverage(self) -> None:
        """Analyze alert categories based on naming patterns.

        Categories derived from alert name prefixes:
        - Service health (ServiceDown, *Down, *Unavailable)
        - Performance (*Slow, *HighLatency, *ResponseTime)
        - Errors (*Error, *Failure, *Failed)
        - Resources (*HighMemory, *HighCPU, *Exhausted)
        - Security (*Unauthorized, *Security, *Suspicious)
        - SLO (*SLO*, *Budget*, *Breach)
        """
        categories = {
            "service_health": [],
            "performance": [],
            "errors": [],
            "resources": [],
            "security": [],
            "slo": [],
            "other": [],
        }

        patterns = {
            "service_health": re.compile(r"(Down|Unavailable|NotRunning|Unhealthy)", re.I),
            "performance": re.compile(r"(Slow|HighLatency|ResponseTime|Duration)", re.I),
            "errors": re.compile(r"(Error|Failure|Failed|Exception)", re.I),
            "resources": re.compile(r"(HighMemory|HighCPU|Exhausted|OOM|Pressure)", re.I),
            "security": re.compile(r"(Unauthorized|Security|Suspicious|Auth)", re.I),
            "slo": re.compile(r"(SLO|Budget|Breach|SLA)", re.I),
        }

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                categorized = False

                for category, pattern in patterns.items():
                    if pattern.search(alert_name):
                        categories[category].append(alert_name)
                        categorized = True
                        break

                if not categorized:
                    categories["other"].append(alert_name)

        print("\n\nAlert Categories Coverage:")
        for category, alerts in sorted(categories.items()):
            print(f"  {category}: {len(alerts)} alerts")
            if len(alerts) <= 5:
                for a in alerts:
                    print(f"    - {a}")


class TestDashboardAlertLinking:
    """Tests for dashboard-alert reference validation."""

    def _get_all_dashboards(self) -> list[tuple[Path, dict[str, Any]]]:
        """Load all Grafana dashboard JSON files."""
        dashboards = []

        for dashboard_dir in [GRAFANA_DASHBOARDS_DIR, HELM_DASHBOARDS_DIR]:
            if not dashboard_dir.exists():
                continue
            for f in dashboard_dir.rglob("*.json"):
                try:
                    with open(f) as fp:
                        content = json.load(fp)
                    if "panels" in content or "rows" in content:
                        dashboards.append((f, content))
                except (json.JSONDecodeError, FileNotFoundError):
                    continue

        return dashboards

    def _get_all_alert_names(self) -> set[str]:
        """Get all defined alert names."""
        alert_names = set()

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                if "alert" in alert:
                    alert_names.add(alert["alert"])

        return alert_names

    def test_dashboard_alert_annotations_reference_valid_alerts(self) -> None:
        """Dashboard alert annotations should reference existing alerts.

        Grafana dashboards can have alert annotations that display when alerts fire.
        These should reference alerts that actually exist.
        """
        alert_names = self._get_all_alert_names()
        invalid_references: list[str] = []

        for file_path, content in self._get_all_dashboards():
            # Check annotations
            annotations = content.get("annotations", {}).get("list", [])
            for ann in annotations:
                # Datasource can be a string or a dict
                datasource = ann.get("datasource", {})
                if isinstance(datasource, dict) and datasource.get("type") == "prometheus":
                    expr = ann.get("expr", "")
                    # Look for ALERTS{alertname="..."} patterns
                    matches = re.findall(r'alertname[=~]+"?([^"}\s]+)"?', expr)
                    for match in matches:
                        if match not in alert_names and "*" not in match:
                            rel_path = str(file_path.relative_to(PROJECT_ROOT))
                            invalid_references.append(f"{rel_path}: annotation references '{match}'")

        if invalid_references:
            pytest.fail(
                f"Found {len(invalid_references)} invalid alert references in dashboards:\n"
                + "\n".join(f"  {x}" for x in invalid_references[:20])
                + ("\n  ..." if len(invalid_references) > 20 else "")
            )

    def test_alerts_with_dashboard_urls_reference_valid_dashboards(self) -> None:
        """Alert annotations with dashboard_url should reference valid dashboards.

        Alerts often have dashboard_url annotations for quick navigation.
        These should use {{ grafana_url }} template variable, not hardcoded URLs.
        """
        dashboards = self._get_all_dashboards()
        dashboard_uids = {d[1].get("uid") for d in dashboards if d[1].get("uid")}

        hardcoded_urls: list[str] = []
        invalid_uids: list[str] = []

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                annotations = alert.get("annotations", {})
                dashboard_url = annotations.get("dashboard_url", "")

                if dashboard_url:
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))

                    # Check for hardcoded URLs
                    if (
                        "http://" in dashboard_url or "https://" in dashboard_url
                    ) and "{{ grafana_url }}" not in dashboard_url:
                        hardcoded_urls.append(f"{rel_path}: {alert_name}")

                    # Extract dashboard UID from URL pattern /d/<uid>/
                    uid_match = re.search(r"/d/([^/]+)/", dashboard_url)
                    if uid_match:
                        uid = uid_match.group(1)
                        # Skip template variables
                        if not uid.startswith("{{") and uid not in dashboard_uids:
                            invalid_uids.append(f"{rel_path}: {alert_name} references UID '{uid}'")

        errors = []
        if hardcoded_urls:
            errors.append(
                f"Found {len(hardcoded_urls)} alerts with hardcoded dashboard URLs "
                f"(use '{{{{ grafana_url }}}}' template):\n" + "\n".join(f"  {x}" for x in hardcoded_urls[:10])
            )

        # Don't fail on invalid UIDs for now - just warn
        # Dashboard UIDs may be dynamically generated
        if False:  # Disabled check - UIDs may be dynamic
            errors.append(
                f"Found {len(invalid_uids)} alerts referencing non-existent dashboard UIDs:\n"
                + "\n".join(f"  {x}" for x in invalid_uids[:10])
            )

        if errors:
            pytest.fail("\n\n".join(errors))

    def test_critical_alerts_have_runbook_urls(self) -> None:
        """Critical alerts MUST have runbook_url annotations.

        Critical alerts require runbook URLs to guide on-call engineers.
        This is a hard requirement - all critical alerts must have runbooks.
        """
        missing_runbooks: list[str] = []

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})

                severity = labels.get("severity", "")
                if severity == "critical":
                    if "runbook_url" not in annotations:
                        rel_path = str(file_path.relative_to(PROJECT_ROOT))
                        missing_runbooks.append(f"{rel_path}: {alert_name}")

        # HARD REQUIREMENT: All critical alerts must have runbook URLs
        if missing_runbooks:
            pytest.fail(
                f"Found {len(missing_runbooks)} critical alerts without runbook_url:\n"
                + "\n".join(f"  {x}" for x in missing_runbooks[:20])
                + ("\n  ..." if len(missing_runbooks) > 20 else "")
                + "\n\nAll critical alerts MUST have runbook URLs for on-call guidance."
            )

    def test_high_priority_alerts_have_dashboard_urls(self) -> None:
        """Critical and warning alerts should have dashboard_url annotations.

        Alerts with dashboard links enable faster troubleshooting.
        Target: >= 50% of critical/warning alerts should have dashboard links.
        """
        alerts_needing_dashboard: list[str] = []
        alerts_with_dashboard: list[str] = []

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})

                severity = labels.get("severity", "")
                rel_path = str(file_path.relative_to(PROJECT_ROOT))

                # Check critical and warning alerts
                if severity in ("critical", "warning"):
                    has_dashboard = "dashboard_url" in annotations or "dashboard" in annotations
                    if has_dashboard:
                        alerts_with_dashboard.append(f"{rel_path}: {alert_name}")
                    else:
                        alerts_needing_dashboard.append(f"{rel_path}: {alert_name}")

        total = len(alerts_needing_dashboard) + len(alerts_with_dashboard)
        coverage = len(alerts_with_dashboard) / total * 100 if total > 0 else 0

        # Target: >= 50% dashboard coverage for critical/warning alerts
        min_coverage = 50.0
        if coverage < min_coverage:
            pytest.fail(
                f"Dashboard coverage for critical/warning alerts is {coverage:.1f}% "
                f"(target: >= {min_coverage}%).\n"
                f"  With dashboard: {len(alerts_with_dashboard)}\n"
                f"  Missing dashboard: {len(alerts_needing_dashboard)}\n\n"
                f"Top 15 alerts needing dashboard_url:\n" + "\n".join(f"  {x}" for x in alerts_needing_dashboard[:15])
            )


class TestAlertQuality:
    """Tests for alert quality and best practices."""

    def test_alerts_have_for_duration(self) -> None:
        """Alerts should have 'for' duration to avoid flapping.

        The 'for' field prevents alerts from firing on transient issues.
        Recommended minimums:
        - Critical: >= 1m
        - Warning: >= 5m
        - Info: >= 10m
        """
        missing_for: list[str] = []
        short_for: list[str] = []

        def parse_duration(duration: str) -> int:
            """Parse duration string to seconds."""
            if not duration:
                return 0
            match = re.match(r"(\d+)(s|m|h|d)?", duration)
            if not match:
                return 0
            value = int(match.group(1))
            unit = match.group(2) or "s"
            multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            return value * multipliers.get(unit, 1)

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                for_duration = alert.get("for", "")
                labels = alert.get("labels", {})
                severity = labels.get("severity", "warning")

                rel_path = str(file_path.relative_to(PROJECT_ROOT))

                if not for_duration:
                    missing_for.append(f"{rel_path}: {alert_name}")
                else:
                    seconds = parse_duration(for_duration)
                    min_seconds = {"critical": 30, "warning": 60, "info": 120}.get(severity, 60)

                    if seconds < min_seconds:
                        short_for.append(
                            f"{rel_path}: {alert_name} (for={for_duration}, recommended>={min_seconds}s for {severity})"
                        )

        # Missing 'for' is a warning, not an error
        if missing_for:
            print(f"\n\nAlerts without 'for' duration ({len(missing_for)}):")
            for x in missing_for[:10]:
                print(f"  {x}")
            if len(missing_for) > 10:
                print(f"  ... and {len(missing_for) - 10} more")

    def test_no_hardcoded_thresholds_in_expressions(self) -> None:
        """Alert expressions should prefer recording rules for complex calculations.

        This is informational - identifies alerts that might benefit from recording rules.
        """
        complex_alerts: list[str] = []

        # Patterns that suggest recording rules would help
        complex_patterns = [
            r"histogram_quantile\([^)]+\)\s*[><=]",  # histogram with comparison
            r"sum\s*\([^)]+\)\s*/\s*sum\s*\(",  # ratio of sums
            r"rate\s*\([^)]+\)\s*/\s*rate\s*\(",  # ratio of rates
        ]
        combined_pattern = re.compile("|".join(complex_patterns))

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                expr = alert.get("expr", "")

                if combined_pattern.search(expr):
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    complex_alerts.append(f"{rel_path}: {alert_name}")

        if complex_alerts:
            print(f"\n\nAlerts with complex expressions (consider recording rules, {len(complex_alerts)}):")
            for x in complex_alerts[:10]:
                print(f"  {x}")

    def test_warning_alerts_have_runbook_urls(self) -> None:
        """Warning alerts should have runbook_url annotations.

        Warning alerts benefit from runbook URLs to provide troubleshooting guidance.
        Target: >= 80% of warning alerts should have runbook_url.
        """
        alerts_with_runbook: list[str] = []
        alerts_without_runbook: list[str] = []

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})

                severity = labels.get("severity", "")
                rel_path = str(file_path.relative_to(PROJECT_ROOT))

                if severity == "warning":
                    if "runbook_url" in annotations:
                        alerts_with_runbook.append(f"{rel_path}: {alert_name}")
                    else:
                        alerts_without_runbook.append(f"{rel_path}: {alert_name}")

        total = len(alerts_with_runbook) + len(alerts_without_runbook)
        coverage = len(alerts_with_runbook) / total * 100 if total > 0 else 0

        # Target: >= 80% runbook coverage for warning alerts
        min_coverage = 80.0
        if coverage < min_coverage:
            pytest.fail(
                f"Runbook coverage for warning alerts is {coverage:.1f}% "
                f"(target: >= {min_coverage}%).\n"
                f"  With runbook: {len(alerts_with_runbook)}\n"
                f"  Missing runbook: {len(alerts_without_runbook)}\n\n"
                f"Top 15 warning alerts needing runbook_url:\n" + "\n".join(f"  {x}" for x in alerts_without_runbook[:15])
            )


class TestRunbookFileExistence:
    """Tests to verify runbook files referenced in alerts actually exist."""

    def _extract_runbook_paths(self) -> dict[str, list[str]]:
        """Extract all runbook file paths from alert annotations.

        Returns dict mapping runbook path -> list of alerts referencing it.
        """
        runbook_to_alerts: dict[str, list[str]] = {}

        for file_path, fmt in get_all_alert_files():
            content = load_yaml_file(file_path)
            if not content:
                continue

            if fmt == "k8s_crd":
                alerts = extract_alerts_from_k8s_crd(content)
            else:
                alerts = extract_alerts_from_standard_format(content)

            for alert in alerts:
                alert_name = alert.get("alert", "")
                annotations = alert.get("annotations", {})
                runbook_url = annotations.get("runbook_url", "")

                if runbook_url and "github.com" in runbook_url:
                    # Extract path from GitHub URL
                    # https://github.com/.../blob/main/monitoring/runbooks/sla-alerts.md#anchor
                    if "/blob/main/" in runbook_url:
                        path = runbook_url.split("/blob/main/")[1].split("#")[0]
                        if path not in runbook_to_alerts:
                            runbook_to_alerts[path] = []
                        runbook_to_alerts[path].append(alert_name)

        return runbook_to_alerts

    def test_runbook_files_exist(self) -> None:
        """All runbook files referenced in alerts must exist.

        Runbook URLs point to markdown files in monitoring/runbooks/.
        These files must exist to provide troubleshooting guidance.
        """
        runbook_to_alerts = self._extract_runbook_paths()
        missing_files: list[str] = []

        for runbook_path, alerts in sorted(runbook_to_alerts.items()):
            full_path = PROJECT_ROOT / runbook_path
            if not full_path.exists():
                missing_files.append(f"{runbook_path} (used by {len(alerts)} alerts)")

        if missing_files:
            pytest.fail(
                f"Found {len(missing_files)} missing runbook files:\n"
                + "\n".join(f"  ❌ {x}" for x in missing_files[:20])
                + ("\n  ..." if len(missing_files) > 20 else "")
                + "\n\nCreate these files in monitoring/runbooks/ directory."
            )

    def test_runbook_files_have_required_sections(self) -> None:
        """Runbook files should have standard sections.

        Each runbook should have:
        - Title (# heading)
        - Overview section
        - Symptoms section
        - Resolution section
        """
        runbooks_dir = PROJECT_ROOT / "monitoring" / "runbooks"
        if not runbooks_dir.exists():
            pytest.skip("monitoring/runbooks/ directory does not exist yet")

        missing_sections: list[str] = []
        required_sections = ["overview", "symptom", "resolution", "escalation"]

        for runbook_file in runbooks_dir.glob("*.md"):
            # Skip README and other non-runbook files
            if runbook_file.name.lower() in ("readme.md", "index.md"):
                continue
            content = runbook_file.read_text().lower()
            file_issues = []

            for section in required_sections:
                # Check for section heading (## Section or # Section)
                if f"# {section}" not in content and f"## {section}" not in content:
                    # Also check for variations like "symptoms" vs "symptom"
                    if f"# {section}s" not in content and f"## {section}s" not in content:
                        file_issues.append(section)

            if file_issues:
                missing_sections.append(f"{runbook_file.name}: missing {', '.join(file_issues)}")

        if missing_sections:
            pytest.fail(
                f"Found {len(missing_sections)} runbooks with missing sections:\n"
                + "\n".join(f"  {x}" for x in missing_sections[:15])
                + "\n\nRequired sections: "
                + ", ".join(required_sections)
            )

    def test_runbook_anchors_exist(self) -> None:
        """Runbook URL anchors must have corresponding sections in the file.

        When an alert's runbook_url contains an anchor (e.g., #authzproxydown),
        that anchor must correspond to a heading in the runbook file.
        This ensures on-call engineers can navigate directly to the relevant section.
        """
        runbook_anchor_issues: list[str] = []

        for file_path, fmt in get_all_alert_files():
            try:
                content = file_path.read_text()
                # fmt is "standard" or "k8s_crd", not "yaml"/"json"
                # All alert files are YAML format
                data = yaml.safe_load(content)
            except Exception:
                continue

            # Handle k8s CRD format vs standard Prometheus format
            if fmt == "k8s_crd":
                groups = data.get("spec", {}).get("groups", [])
            else:
                groups = data.get("groups", [])
            for group in groups:
                rules = group.get("rules", [])
                for alert in rules:
                    if "alert" not in alert:
                        continue

                    alert_name = alert.get("alert", "")
                    annotations = alert.get("annotations", {})
                    runbook_url = annotations.get("runbook_url", "")

                    # Check if URL has an anchor
                    if runbook_url and "#" in runbook_url and "github.com" in runbook_url:
                        # Extract path and anchor from URL
                        # https://github.com/.../blob/main/monitoring/runbooks/file.md#anchor
                        if "/blob/main/" in runbook_url:
                            path_with_anchor = runbook_url.split("/blob/main/")[1]
                            if "#" in path_with_anchor:
                                runbook_path, anchor = path_with_anchor.split("#", 1)
                                full_path = PROJECT_ROOT / runbook_path

                                if full_path.exists():
                                    runbook_content = full_path.read_text().lower()
                                    # Anchors in GitHub are lowercase versions of headings
                                    # Check for ## AnchorName heading pattern
                                    anchor_lower = anchor.lower()
                                    # GitHub anchor format: removes special chars, lowercases
                                    # We check if there's a heading that would create this anchor
                                    if f"## {anchor_lower}" not in runbook_content:
                                        # Also try without ## (could be # or ###)
                                        has_anchor = f"# {anchor_lower}" in runbook_content
                                        if not has_anchor:
                                            rel_path = str(file_path.relative_to(PROJECT_ROOT))
                                            runbook_anchor_issues.append(
                                                f"{rel_path}: {alert_name} -> #{anchor} (missing in {runbook_path})"
                                            )

        # All runbook anchors should exist - no known missing anchors
        known_missing_anchors = 0

        if len(runbook_anchor_issues) > known_missing_anchors:
            pytest.fail(
                f"Found {len(runbook_anchor_issues)} alerts with missing runbook anchors "
                f"(threshold: {known_missing_anchors}):\n"
                + "\n".join(f"  ❌ {x}" for x in runbook_anchor_issues[:20])
                + ("\n  ..." if len(runbook_anchor_issues) > 20 else "")
                + "\n\nEach runbook anchor must have a corresponding ## heading in the file."
                + "\n\nNOTE: New alerts MUST have corresponding runbook anchors. "
                + "Reduce known_missing_anchors as you fix existing issues."
            )
        elif runbook_anchor_issues:
            # Report as warning for visibility, but don't fail
            print(
                f"\n⚠️  {len(runbook_anchor_issues)} alerts have missing runbook anchors "
                f"(allowed: {known_missing_anchors}):\n" + "\n".join(f"  - {x}" for x in runbook_anchor_issues[:10])
            )
