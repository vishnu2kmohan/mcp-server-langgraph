"""
Tests for scripts/convert-k8s-crd-alerts.py

TDD tests for K8s PrometheusRule CRD to standard Prometheus format conversion.

The conversion script should:
1. Read K8s CRD format files
2. Extract the spec.groups section
3. Write as standard Prometheus rules YAML
4. Preserve alert definitions, labels, and annotations
5. Add header comments for traceability
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit]

# Paths
PROJECT_ROOT = get_repo_root()
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "convert-k8s-crd-alerts.py"


class TestK8sCRDConversionScript:
    """Tests for the K8s CRD conversion script."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> dict[str, Path]:
        """Create a temporary project structure for testing."""
        source_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        source_dir.mkdir(parents=True)
        dest_dir.mkdir(parents=True)
        return {"source": source_dir, "dest": dest_dir}

    def _create_k8s_crd_file(self, folder: Path, name: str) -> Path:
        """Create a test K8s CRD format file."""
        content = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": name,
                "namespace": "monitoring",
            },
            "spec": {
                "groups": [
                    {
                        "name": f"{name}_group",
                        "interval": "30s",
                        "rules": [
                            {
                                "alert": f"{name}Alert1",
                                "expr": 'up{job="test"} == 0',
                                "for": "5m",
                                "labels": {"severity": "critical"},
                                "annotations": {"summary": "Test alert 1"},
                            },
                            {
                                "alert": f"{name}Alert2",
                                "expr": "rate(errors[5m]) > 0.1",
                                "for": "10m",
                                "labels": {"severity": "warning"},
                                "annotations": {"summary": "Test alert 2"},
                            },
                        ],
                    }
                ]
            },
        }
        filepath = folder / f"{name}.yaml"
        with open(filepath, "w") as f:
            yaml.dump(content, f, default_flow_style=False)
        return filepath

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_help_flag_shows_usage(self) -> None:
        """--help flag should show usage information."""
        result = subprocess.run(
            ["python", str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_convert_single_file(self, temp_project: dict[str, Path]) -> None:
        """Convert a single K8s CRD file to standard format."""
        source_file = self._create_k8s_crd_file(temp_project["source"], "test-alerts")
        dest_file = temp_project["dest"] / "test-alerts.yaml"

        result = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                str(source_file),
                "--output",
                str(dest_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Conversion failed: {result.stderr}"
        assert dest_file.exists()

        # Verify output format
        with open(dest_file) as f:
            content = yaml.safe_load(f)

        assert "groups" in content
        assert "apiVersion" not in content
        assert "kind" not in content
        assert len(content["groups"]) == 1
        assert len(content["groups"][0]["rules"]) == 2

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_preserves_alert_definitions(self, temp_project: dict[str, Path]) -> None:
        """Converted file preserves all alert definitions."""
        source_file = self._create_k8s_crd_file(temp_project["source"], "preserve-test")
        dest_file = temp_project["dest"] / "preserve-test.yaml"

        subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                str(source_file),
                "--output",
                str(dest_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        with open(source_file) as f:
            source_content = yaml.safe_load(f)
        with open(dest_file) as f:
            dest_content = yaml.safe_load(f)

        # Get alerts from both files
        source_alerts = source_content["spec"]["groups"][0]["rules"]
        dest_alerts = dest_content["groups"][0]["rules"]

        assert len(dest_alerts) == len(source_alerts)
        for src, dst in zip(source_alerts, dest_alerts, strict=True):
            assert src["alert"] == dst["alert"]
            assert src["expr"] == dst["expr"]
            assert src["labels"] == dst["labels"]
            assert src["annotations"] == dst["annotations"]

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_dry_run_mode(self, temp_project: dict[str, Path]) -> None:
        """--dry-run shows what would be done without writing."""
        source_file = self._create_k8s_crd_file(temp_project["source"], "dry-run-test")
        dest_file = temp_project["dest"] / "dry-run-test.yaml"

        result = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                str(source_file),
                "--output",
                str(dest_file),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert not dest_file.exists()  # File should not be created in dry-run

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_convert_directory_with_multiple_files_succeeds(self, temp_project: dict[str, Path]) -> None:
        """Convert all K8s CRD files in a directory."""
        self._create_k8s_crd_file(temp_project["source"], "alerts-1")
        self._create_k8s_crd_file(temp_project["source"], "alerts-2")

        result = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--source-dir",
                str(temp_project["source"]),
                "--output-dir",
                str(temp_project["dest"]),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert (temp_project["dest"] / "alerts-1.yaml").exists()
        assert (temp_project["dest"] / "alerts-2.yaml").exists()

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_skips_non_crd_files(self, temp_project: dict[str, Path]) -> None:
        """Skip files that are not K8s PrometheusRule CRDs."""
        # Create K8s CRD file
        self._create_k8s_crd_file(temp_project["source"], "crd-alerts")

        # Create standard format file
        standard_content = {"groups": [{"name": "test", "rules": []}]}
        standard_file = temp_project["source"] / "standard-alerts.yaml"
        with open(standard_file, "w") as f:
            yaml.dump(standard_content, f)

        result = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "--source-dir",
                str(temp_project["source"]),
                "--output-dir",
                str(temp_project["dest"]),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # CRD file should be converted
        assert (temp_project["dest"] / "crd-alerts.yaml").exists()
        # Standard file should be skipped (or copied as-is based on implementation)

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Conversion script not yet created (TDD - RED phase)",
    )
    def test_adds_header_comment(self, temp_project: dict[str, Path]) -> None:
        """Converted file includes header comment for traceability."""
        source_file = self._create_k8s_crd_file(temp_project["source"], "header-test")
        dest_file = temp_project["dest"] / "header-test.yaml"

        subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                str(source_file),
                "--output",
                str(dest_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        with open(dest_file) as f:
            content = f.read()

        # Check for header comment
        assert "# Converted from K8s PrometheusRule CRD" in content or "# Source:" in content
