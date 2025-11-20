"""
Test suite to validate that GKE Autopilot configurations don't use deprecated labels.

These tests ensure Kubernetes manifests for GKE Autopilot use compatible labels
and don't include deprecated or incompatible node pool labels.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (deprecated labels exist)
- GREEN: After removing deprecated labels, tests should PASS
- REFACTOR: Improve validation logic as needed
"""

import gc
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
# Define project root relative to test file
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"


@pytest.mark.xdist_group(name="testgkeautopilotlabels")
class TestGKEAutopilotLabels:
    """Test that GKE Autopilot overlays don't use deprecated labels."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # Labels that are deprecated or incompatible with GKE Autopilot
    DEPRECATED_LABELS = {
        "cloud.google.com/gke-nodepool": "Deprecated for GKE Autopilot - node pools are managed automatically",
    }

    def _find_gke_kustomization_files(self):
        """Find kustomization.yaml files in GKE overlay directories."""
        gke_dirs = [
            DEPLOYMENTS_DIR / "kubernetes" / "overlays" / "gcp",
            DEPLOYMENTS_DIR / "overlays" / "production-gke",
        ]

        kustomization_files = []
        for gke_dir in gke_dirs:
            if gke_dir.exists():
                kustomization_files.extend(list(gke_dir.glob("kustomization.yaml")))

        return kustomization_files

    def _load_yaml_file(self, file_path: Path):
        """Load YAML file and return parsed content."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            pytest.fail(f"Error loading YAML file {file_path}: {e}")

    def test_gke_autopilot_no_deprecated_nodepool_label(self):
        """
        Test that GKE Autopilot overlays don't use deprecated nodepool labels.

        RED: Should FAIL - GCP overlay uses cloud.google.com/gke-nodepool label
        GREEN: Should PASS - after removing deprecated label
        """
        kustomization_files = self._find_gke_kustomization_files()

        if not kustomization_files:
            pytest.skip("No GKE kustomization files found")

        violations = []

        for kustomize_file in kustomization_files:
            config = self._load_yaml_file(kustomize_file)

            if not isinstance(config, dict):
                continue

            # Check commonLabels
            common_labels = config.get("commonLabels", {})

            for deprecated_label, reason in self.DEPRECATED_LABELS.items():
                if deprecated_label in common_labels:
                    violations.append(
                        {
                            "file": str(kustomize_file.relative_to(PROJECT_ROOT)),
                            "label": deprecated_label,
                            "value": common_labels[deprecated_label],
                            "reason": reason,
                        }
                    )

            # Check labels in patches
            patches = config.get("patches", [])
            for patch in patches:
                if not isinstance(patch, dict):
                    continue

                patch_content = yaml.dump(patch)
                for deprecated_label, reason in self.DEPRECATED_LABELS.items():
                    if deprecated_label in patch_content:
                        violations.append(
                            {
                                "file": str(kustomize_file.relative_to(PROJECT_ROOT)),
                                "label": deprecated_label,
                                "location": "patches",
                                "reason": reason,
                            }
                        )

        if violations:
            error_msg = "\n\nDeprecated label violations in GKE configurations:\n"
            for v in violations:
                error_msg += f"\n  {v['file']}"
                error_msg += f"\n    Label: {v['label']}"
                if "value" in v:
                    error_msg += f"\n    Value: {v['value']}"
                error_msg += f"\n    Reason: {v['reason']}\n"

            pytest.fail(error_msg)

    def test_gke_autopilot_recommended_labels(self):
        """
        Test that GKE Autopilot overlays use recommended labels.

        This is informational - helps ensure proper labeling practices.
        """
        kustomization_files = self._find_gke_kustomization_files()

        if not kustomization_files:
            pytest.skip("No GKE kustomization files found")

        # Recommended labels for GKE
        recommended_labels = [
            "app.kubernetes.io/name",
            "app.kubernetes.io/instance",
            "app.kubernetes.io/version",
            "app.kubernetes.io/component",
        ]

        # This is informational only - we don't fail if missing
        for kustomize_file in kustomization_files:
            config = self._load_yaml_file(kustomize_file)
            common_labels = config.get("commonLabels", {})

            found_labels = [label for label in recommended_labels if label in common_labels]

            if not found_labels:
                print(
                    f"\nINFO: {kustomize_file.relative_to(PROJECT_ROOT)} - "
                    f"Consider adding recommended labels: {recommended_labels}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
