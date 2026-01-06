"""
Contract tests for Grafana dashboard provisioning.

These tests validate that the Grafana dashboard configuration is correct
and will be auto-provisioned when the test environment starts.

Following TDD RED-GREEN-REFACTOR cycle to prevent:
- Empty provisioning config files that break dashboard loading
- Shadowing of provisioning config by directory mounts
- Missing dashboard categories (AI, Resilience, WebSocket)

Reference: Grafana provisioning issue where empty dashboards.yml in
dashboards/ directory shadowed the real provisioning config.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def repo_root() -> Path:
    """Get repository root directory (shared across all tests in module)."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return Path(result.stdout.strip())


def test_dashboards_yml_provisioning_config_not_empty(repo_root: Path):
    """
    Verify that the main dashboards.yml provisioning config is not empty.

    The dashboards.yml file at monitoring/grafana/dashboards.yml contains
    the Grafana dashboard provisioning configuration. If empty, no dashboards
    will be auto-provisioned.
    """
    dashboards_yml = repo_root / "monitoring" / "grafana" / "dashboards.yml"

    assert dashboards_yml.exists(), (
        f"Dashboard provisioning config not found: {dashboards_yml}\n"
        "\n"
        "Expected file: monitoring/grafana/dashboards.yml\n"
        "This file configures Grafana to auto-provision dashboards from disk."
    )

    # Check file is not empty
    file_size = dashboards_yml.stat().st_size
    assert file_size > 0, (
        f"Dashboard provisioning config is empty (0 bytes): {dashboards_yml}\n"
        "\n"
        "This will cause Grafana to not load any dashboards.\n"
        "Fix: Add valid YAML provisioning configuration."
    )

    # Verify it's valid YAML
    with open(dashboards_yml) as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Dashboard provisioning config is not valid YAML: {e}")
            return

    assert config is not None, "Dashboard provisioning config is empty (null YAML)"
    assert "providers" in config, (
        "Dashboard provisioning config missing 'providers' key.\n"
        "\n"
        "Expected structure:\n"
        "apiVersion: 1\n"
        "providers:\n"
        "  - name: 'Dashboards'\n"
        "    ..."
    )


def test_no_shadowing_dashboards_yml_in_dashboards_directory(repo_root: Path):
    """
    Verify that there is NO dashboards.yml file inside the dashboards/ directory.

    Docker Compose mounts:
    1. ./monitoring/grafana/dashboards.yml -> /etc/grafana/provisioning/dashboards/dashboards.yml
    2. ./monitoring/grafana/dashboards/ -> /etc/grafana/provisioning/dashboards/

    If dashboards.yml exists inside the dashboards/ directory, it SHADOWS
    the real provisioning config from mount #1, causing dashboards to not load.

    This was the root cause of missing AI, Resilience, and WebSocket dashboards.
    """
    shadowing_file = repo_root / "monitoring" / "grafana" / "dashboards" / "dashboards.yml"

    assert not shadowing_file.exists(), (
        f"Found rogue dashboards.yml that shadows provisioning config: {shadowing_file}\n"
        "\n"
        "This file will shadow the real provisioning config due to Docker volume mount order.\n"
        "\n"
        "Docker mounts in docker-compose.test.yml:\n"
        "  1. dashboards.yml -> /etc/grafana/provisioning/dashboards/dashboards.yml (REAL config)\n"
        "  2. dashboards/    -> /etc/grafana/provisioning/dashboards/ (SHADOWS above!)\n"
        "\n"
        "Fix: Delete monitoring/grafana/dashboards/dashboards.yml"
    )


def test_dashboard_folders_exist_and_contain_dashboards(repo_root: Path):
    """
    Verify that all expected dashboard category folders exist and contain JSON files.

    The Grafana provisioning config uses foldersFromFilesStructure: true,
    which creates Grafana folders matching the filesystem directories.
    """
    dashboards_dir = repo_root / "monitoring" / "grafana" / "dashboards"

    expected_folders = {
        "Overview": ["langgraph-agent.json"],
        "Application": [
            "ai-ux-metrics.json",
            "llm-performance.json",
            "websocket-telemetry.json",
        ],
        "Auth": ["authentication.json", "openfga.json", "keycloak.json", "security.json"],
        "Infrastructure": ["resilience-patterns.json", "lgtm-stack.json", "postgresql.json"],
        "Compliance": ["sla-monitoring.json", "soc2-compliance.json"],
    }

    for folder_name, expected_dashboards in expected_folders.items():
        folder_path = dashboards_dir / folder_name

        assert folder_path.exists(), (
            f"Dashboard folder not found: {folder_path}\n"
            "\n"
            f"Expected folder: {folder_name}/\n"
            f"Expected dashboards: {expected_dashboards}"
        )

        assert folder_path.is_dir(), f"Expected directory, got file: {folder_path}"

        # Check each expected dashboard exists
        for dashboard_name in expected_dashboards:
            dashboard_path = folder_path / dashboard_name
            assert dashboard_path.exists(), (
                f"Dashboard not found: {dashboard_path}\n\nExpected dashboard: {folder_name}/{dashboard_name}"
            )


def test_ai_dashboards_exist_in_application_folder(repo_root: Path):
    """
    Verify that AI-related dashboards exist in the Application folder.

    These dashboards are for monitoring AI/LLM features:
    - ai-ux-metrics.json: AI UX metrics (HEART metrics, suggestions)
    - ai-recommendation-quality.json: AI recommendation quality
    - studio-ai-intelligence.json: Studio AI intelligence features
    """
    app_folder = repo_root / "monitoring" / "grafana" / "dashboards" / "Application"

    ai_dashboards = [
        "ai-ux-metrics.json",
        "ai-recommendation-quality.json",
        "studio-ai-intelligence.json",
    ]

    missing = []
    for dashboard in ai_dashboards:
        if not (app_folder / dashboard).exists():
            missing.append(dashboard)

    assert len(missing) == 0, (
        f"Missing AI dashboards in Application folder: {missing}\n"
        "\n"
        f"Expected in: {app_folder}\n"
        "\n"
        "These dashboards provide AI/LLM monitoring capabilities."
    )


def test_websocket_dashboard_exists(repo_root: Path):
    """
    Verify that WebSocket telemetry dashboard exists.

    This dashboard monitors WebSocket connections, messages, and health.
    """
    websocket_dashboard = repo_root / "monitoring" / "grafana" / "dashboards" / "Application" / "websocket-telemetry.json"

    assert websocket_dashboard.exists(), (
        f"WebSocket dashboard not found: {websocket_dashboard}\n\nThis dashboard provides WebSocket connection monitoring."
    )


def test_resilience_dashboard_exists(repo_root: Path):
    """
    Verify that Resilience patterns dashboard exists.

    This dashboard monitors circuit breakers, retries, bulkheads, and rate limiters.
    """
    resilience_dashboard = repo_root / "monitoring" / "grafana" / "dashboards" / "Infrastructure" / "resilience-patterns.json"

    assert resilience_dashboard.exists(), (
        f"Resilience dashboard not found: {resilience_dashboard}\n"
        "\n"
        "This dashboard provides circuit breaker and resilience pattern monitoring."
    )


def test_all_dashboard_files_are_valid_json(repo_root: Path):
    """
    Verify that all dashboard JSON files are valid JSON.

    Invalid JSON files will cause Grafana provisioning to fail silently.
    """
    import json

    dashboards_dir = repo_root / "monitoring" / "grafana" / "dashboards"

    invalid_files = []
    for json_file in dashboards_dir.rglob("*.json"):
        try:
            with open(json_file) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            invalid_files.append((str(json_file.relative_to(dashboards_dir)), str(e)))

    assert len(invalid_files) == 0, "Invalid JSON in dashboard files:\n" + "\n".join(
        f"  - {path}: {error}" for path, error in invalid_files
    )


def test_dashboard_files_have_required_fields(repo_root: Path):
    """
    Verify that all dashboard JSON files have required Grafana fields.

    Each dashboard must have:
    - title: Dashboard title
    - uid: Unique identifier for URL routing
    """
    import json

    dashboards_dir = repo_root / "monitoring" / "grafana" / "dashboards"

    issues = []
    for json_file in dashboards_dir.rglob("*.json"):
        with open(json_file) as f:
            try:
                dashboard = json.load(f)
            except json.JSONDecodeError:
                continue  # Covered by test_all_dashboard_files_are_valid_json

        rel_path = str(json_file.relative_to(dashboards_dir))

        if "title" not in dashboard:
            issues.append(f"{rel_path}: missing 'title' field")

        if "uid" not in dashboard:
            issues.append(f"{rel_path}: missing 'uid' field")

    assert len(issues) == 0, "Dashboard validation issues:\n" + "\n".join(f"  - {issue}" for issue in issues)
