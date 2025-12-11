#!/usr/bin/env python3
"""
Grafana Dashboard Audit Script

Validates that all dashboard panels are correctly configured and receiving metrics.

Usage:
    uv run python scripts/validation/audit_grafana_dashboards.py
"""

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

# Configuration
MIMIR_URL = "http://localhost:19009/prometheus"
DASHBOARDS_DIR = Path("monitoring/grafana/dashboards")


def query_mimir(promql: str) -> dict[str, Any]:
    """Query Mimir and return results."""
    encoded_query = urllib.parse.quote(promql)
    url = f"{MIMIR_URL}/api/v1/query?query={encoded_query}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310 # noqa: S310
            return json.loads(response.read().decode())  # type: ignore[no-any-return]
    except Exception as e:
        return {"status": "error", "error": str(e)}


def extract_queries_from_panel(panel: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract PromQL queries from a panel."""
    queries = []
    panel_title = panel.get("title", "Untitled")

    # Skip row panels
    if panel.get("type") == "row":
        return queries

    # Extract from targets
    for target in panel.get("targets", []):
        expr = target.get("expr", "")
        if expr:
            queries.append((panel_title, expr))

    return queries


def extract_queries_from_dashboard(dashboard: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract all PromQL queries from a dashboard."""
    queries = []

    for panel in dashboard.get("panels", []):
        queries.extend(extract_queries_from_panel(panel))

        # Handle nested panels in rows
        for nested in panel.get("panels", []):
            queries.extend(extract_queries_from_panel(nested))

    return queries


def validate_datasource_uids(dashboard: dict[str, Any]) -> list[str]:
    """Check all panel datasources use 'mimir' UID."""
    issues = []

    def check_panel(panel: dict[str, Any], path: str) -> None:
        # Check panel datasource
        ds = panel.get("datasource", {})
        if isinstance(ds, dict):
            uid = ds.get("uid", "")
            ds_type = ds.get("type", "")
            # Allow grafana built-in datasources
            if uid and uid not in ("mimir", "-- Grafana --") and ds_type != "grafana":
                issues.append(f"{path}: wrong datasource UID '{uid}' (expected 'mimir')")

        # Check target datasources
        for i, target in enumerate(panel.get("targets", [])):
            target_ds = target.get("datasource", {})
            if isinstance(target_ds, dict):
                uid = target_ds.get("uid", "")
                if uid and uid not in ("mimir", "-- Grafana --"):
                    issues.append(f"{path} target {i}: wrong datasource UID '{uid}'")

    for panel in dashboard.get("panels", []):
        panel_title = panel.get("title", "Untitled")
        check_panel(panel, panel_title)

        for nested in panel.get("panels", []):
            nested_title = nested.get("title", "Untitled")
            check_panel(nested, f"{panel_title}/{nested_title}")

    return issues


def extract_job_labels(expr: str) -> list[str]:
    """Extract job labels from PromQL expression."""
    # Pattern: job="value" or job=~"value"
    pattern = r'job[=~]+"([^"]+)"'
    matches = re.findall(pattern, expr)
    return matches


def audit_dashboard(filepath: Path) -> dict[str, Any]:
    """Audit a single dashboard file."""
    with open(filepath) as f:
        dashboard = json.load(f)

    results: dict[str, Any] = {
        "file": filepath.name,
        "title": dashboard.get("title", "Unknown"),
        "uid": dashboard.get("uid", "Unknown"),
        "issues": [],
        "panels_with_data": 0,
        "panels_without_data": 0,
        "total_panels": 0,
        "queries": [],
    }

    # Check datasource UIDs
    ds_issues = validate_datasource_uids(dashboard)
    results["issues"].extend(ds_issues)

    # Extract and test queries
    queries = extract_queries_from_dashboard(dashboard)
    results["total_panels"] = len(queries)

    available_jobs = set()
    try:
        job_response = query_mimir("up")
        if job_response.get("status") == "success":
            for result in job_response.get("data", {}).get("result", []):
                job = result.get("metric", {}).get("job", "")
                if job:
                    available_jobs.add(job)
    except Exception:
        pass

    for panel_title, expr in queries:
        query_result = {
            "panel": panel_title,
            "expr": expr[:100] + "..." if len(expr) > 100 else expr,
            "has_data": False,
            "job_labels": [],
        }

        # Extract job labels
        jobs = extract_job_labels(expr)
        query_result["job_labels"] = jobs

        # Check if job exists in Mimir
        for job in jobs:
            # Skip regex patterns (contain |, .*, or other regex chars)
            is_regex = "|" in job or ".*" in job or ".+" in job
            if is_regex:
                # For regex patterns, check if any available job matches
                try:
                    pattern = re.compile(f"^({job})$")
                    if not any(pattern.match(j) for j in available_jobs):
                        results["issues"].append(f"Panel '{panel_title}': job regex '{job}' matches no jobs in Mimir")
                except re.error:
                    pass  # Invalid regex, skip check
            elif job not in available_jobs:
                results["issues"].append(f"Panel '{panel_title}': job '{job}' not found in Mimir")

        # Test the query
        response = query_mimir(expr)
        if response.get("status") == "success":
            data = response.get("data", {})
            result_data = data.get("result", [])
            if result_data:
                query_result["has_data"] = True
                results["panels_with_data"] += 1
            else:
                results["panels_without_data"] += 1
        else:
            error = response.get("error", "Unknown error")
            if "parse error" in error.lower():
                results["issues"].append(f"Panel '{panel_title}': PromQL parse error - {error[:100]}")
            results["panels_without_data"] += 1

        results["queries"].append(query_result)

    return results


def main() -> int:
    """Main entry point."""
    print("=" * 80)
    print("GRAFANA DASHBOARD AUDIT REPORT")
    print("=" * 80)
    print()

    if not DASHBOARDS_DIR.exists():
        print(f"ERROR: Dashboards directory not found: {DASHBOARDS_DIR}")
        return 1

    # Get all dashboard JSON files
    dashboard_files = sorted(DASHBOARDS_DIR.glob("*.json"))
    print(f"Found {len(dashboard_files)} dashboard files\n")

    all_results = []
    total_issues = 0
    total_panels_with_data = 0
    total_panels_without_data = 0

    for filepath in dashboard_files:
        print(f"Auditing: {filepath.name}...", end=" ", flush=True)
        results = audit_dashboard(filepath)
        all_results.append(results)

        issue_count = len(results["issues"])
        total_issues += issue_count
        total_panels_with_data += results["panels_with_data"]
        total_panels_without_data += results["panels_without_data"]

        status = "PASS" if issue_count == 0 else f"FAIL ({issue_count} issues)"
        data_status = f"{results['panels_with_data']}/{results['total_panels']} panels with data"
        print(f"{status} - {data_status}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total dashboards: {len(dashboard_files)}")
    print(f"Total issues: {total_issues}")
    print(f"Panels with data: {total_panels_with_data}")
    print(f"Panels without data: {total_panels_without_data}")
    print()

    # Print detailed issues
    if total_issues > 0:
        print("=" * 80)
        print("ISSUES BY DASHBOARD")
        print("=" * 80)
        for results in all_results:
            if results["issues"]:
                print(f"\n{results['file']} ({results['title']}):")
                for issue in results["issues"]:
                    print(f"  - {issue}")

    # Print panels without data
    print()
    print("=" * 80)
    print("PANELS WITHOUT DATA")
    print("=" * 80)
    for results in all_results:
        panels_without = [q for q in results["queries"] if not q["has_data"]]
        if panels_without:
            print(f"\n{results['file']}:")
            for query in panels_without[:5]:  # Limit to first 5
                print(f"  - {query['panel']}: {query['expr']}")
            if len(panels_without) > 5:
                print(f"  ... and {len(panels_without) - 5} more")

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
