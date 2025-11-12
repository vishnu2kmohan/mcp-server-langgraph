"""
Test Helm chart templates can be rendered successfully.

This module provides tests to catch Helm template errors early in development,
before they cause failures in CI/CD or production deployments.

TDD Approach:
1. Test that helm template renders without errors
2. Test that helm lint passes
3. Test that rendered manifests are valid YAML
4. Test checksum annotations are properly generated

Regression Prevention:
- Helm unittest plugin template resolution errors (Run #19311976718)
- Checksum template pattern issues with include (print $.Template.BasePath)
"""
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
CHART_PATH = REPO_ROOT / "deployments" / "helm" / "mcp-server-langgraph"


class TestHelmTemplateRendering:
    """Test Helm chart template rendering."""

    def test_helm_template_renders_without_errors(self):
        """Test that helm template command succeeds."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, f"Helm template failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"

    def test_helm_template_produces_valid_yaml(self):
        """Test that rendered templates are valid YAML."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, "Helm template command failed"

        # Parse all YAML documents
        documents = list(yaml.safe_load_all(result.stdout))
        assert len(documents) > 0, "No YAML documents found in rendered output"

        # Verify each document is valid
        for i, doc in enumerate(documents):
            if doc is None:  # Skip empty documents
                continue
            assert isinstance(doc, dict), f"Document {i} is not a valid YAML dict"
            assert "kind" in doc, f"Document {i} missing 'kind' field"
            assert "metadata" in doc, f"Document {i} missing 'metadata' field"

    def test_helm_template_checksum_annotations_present(self):
        """Test that deployment has checksum annotations for config/secret changes."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, "Helm template command failed"

        # Find Deployment manifest
        deployment = None
        for doc in yaml.safe_load_all(result.stdout):
            if doc and doc.get("kind") == "Deployment":
                deployment = doc
                break

        assert deployment is not None, "Deployment manifest not found in rendered output"

        # Verify checksum annotations exist
        annotations = deployment.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})

        assert "checksum/config" in annotations, "Missing checksum/config annotation"
        assert "checksum/secret" in annotations, "Missing checksum/secret annotation"

        # Verify checksums are not empty
        assert len(annotations["checksum/config"]) > 0, "checksum/config is empty"
        assert len(annotations["checksum/secret"]) > 0, "checksum/secret is empty"

        # Verify checksums look like sha256 (64 hex characters)
        config_checksum = annotations["checksum/config"]
        secret_checksum = annotations["checksum/secret"]

        assert len(config_checksum) == 64, f"checksum/config should be 64 chars, got {len(config_checksum)}"
        assert len(secret_checksum) == 64, f"checksum/secret should be 64 chars, got {len(secret_checksum)}"
        assert config_checksum.isalnum(), "checksum/config should be alphanumeric"
        assert secret_checksum.isalnum(), "checksum/secret should be alphanumeric"


class TestHelmLint:
    """Test Helm chart lint passes."""

    def test_helm_lint_passes(self):
        """Test that helm lint passes without warnings or errors."""
        result = subprocess.run(
            ["helm", "lint", str(CHART_PATH)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, f"Helm lint failed:\n{result.stderr}\n{result.stdout}"

    def test_helm_lint_output_contains_success(self):
        """Test that helm lint output indicates success."""
        result = subprocess.run(
            ["helm", "lint", str(CHART_PATH)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, "Helm lint command failed"

        # Helm lint success messages
        output = result.stdout + result.stderr
        assert "linted" in output.lower() or "no failures" in output.lower(), \
            f"Helm lint output doesn't indicate success:\n{output}"


class TestHelmDependencies:
    """Test Helm chart dependencies are available."""

    def test_helm_command_available(self):
        """Test that helm command is available in PATH."""
        result = subprocess.run(
            ["which", "helm"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("Helm not installed - skipping Helm tests")

    def test_chart_yaml_exists(self):
        """Test that Chart.yaml exists."""
        chart_yaml = CHART_PATH / "Chart.yaml"
        assert chart_yaml.exists(), f"Chart.yaml not found at {chart_yaml}"

    def test_values_yaml_exists(self):
        """Test that values.yaml exists."""
        values_yaml = CHART_PATH / "values.yaml"
        assert values_yaml.exists(), f"values.yaml not found at {values_yaml}"

    def test_templates_directory_exists(self):
        """Test that templates directory exists and contains files."""
        templates_dir = CHART_PATH / "templates"
        assert templates_dir.exists(), f"templates directory not found at {templates_dir}"
        assert templates_dir.is_dir(), f"{templates_dir} is not a directory"

        # Check for at least some template files
        template_files = list(templates_dir.glob("*.yaml"))
        template_files.extend(templates_dir.glob("*.tpl"))

        assert len(template_files) > 0, "No template files found in templates directory"


class TestHelmTemplateWithValues:
    """Test Helm template rendering with different values."""

    def test_helm_template_with_custom_values(self):
        """Test rendering with custom values doesn't fail."""
        # Create temporary values with some overrides
        custom_values = """
config:
  environment: "test"
  logLevel: "DEBUG"
replicaCount: 2
"""

        # Write to temp file
        temp_values = REPO_ROOT / "test-values.yaml"
        temp_values.write_text(custom_values)

        try:
            result = subprocess.run(
                [
                    "helm",
                    "template",
                    "test-release",
                    str(CHART_PATH),
                    "-f",
                    str(temp_values),
                ],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )

            assert result.returncode == 0, f"Helm template with custom values failed: {result.stderr}"
            assert len(result.stdout) > 0, "Helm template produced no output"

        finally:
            # Clean up
            if temp_values.exists():
                temp_values.unlink()

    def test_helm_template_with_staging_values(self):
        """Test rendering with staging values if available."""
        staging_values = CHART_PATH.parent / "values-staging.yaml"

        if not staging_values.exists():
            pytest.skip("Staging values file not found")

        result = subprocess.run(
            [
                "helm",
                "template",
                "staging-release",
                str(CHART_PATH),
                "-f",
                str(staging_values),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, f"Helm template with staging values failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"

    def test_helm_template_with_production_values(self):
        """Test rendering with production values if available."""
        production_values = CHART_PATH.parent / "values-production.yaml"

        if not production_values.exists():
            pytest.skip("Production values file not found")

        result = subprocess.run(
            [
                "helm",
                "template",
                "production-release",
                str(CHART_PATH),
                "-f",
                str(production_values),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, f"Helm template with production values failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"
