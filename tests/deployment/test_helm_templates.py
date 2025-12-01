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

import gc
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = [pytest.mark.unit, pytest.mark.validation]
REPO_ROOT = Path(__file__).parent.parent.parent
CHART_PATH = REPO_ROOT / "deployments" / "helm" / "mcp-server-langgraph"


@pytest.fixture(scope="session")
def helm_dependencies_built():
    """Build Helm chart dependencies before running template tests.

    This fixture runs once per session and builds the Helm dependencies
    (redis, grafana, kube-prometheus-stack, etc.) required for helm template to work.

    Uses session scope with file locking to ensure only one pytest-xdist worker
    builds the dependencies, preventing race conditions.

    Cleanup: Removes any stale tmpcharts/ directory that may have been left
    from an interrupted previous run, which can cause helm dependency build
    to fail or produce inconsistent results.
    """
    import fcntl

    if not shutil.which("helm"):
        pytest.skip("helm CLI not installed")

    if not CHART_PATH.exists():
        pytest.skip("Helm chart directory does not exist")

    charts_dir = CHART_PATH / "charts"

    # Use file-based locking to prevent multiple xdist workers from racing
    # Lock file is in the chart path (part of the repo, gitignored)
    lock_file = CHART_PATH / ".helm_dependency_build.lock"

    with open(lock_file, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            # Check if charts are already built (another worker might have done it)
            if charts_dir.exists() and any(charts_dir.glob("*.tgz")):
                # Charts already present, no need to rebuild
                return True

            # Clean up any stale tmpcharts directory from interrupted previous runs
            tmpcharts_path = CHART_PATH / "tmpcharts"
            if tmpcharts_path.exists():
                shutil.rmtree(tmpcharts_path, ignore_errors=True)

            # Build dependencies (downloads redis, kube-prometheus-stack charts)
            result = subprocess.run(
                ["helm", "dependency", "build", str(CHART_PATH)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                timeout=180,  # Increased timeout for network downloads
            )

            if result.returncode != 0:
                pytest.skip(f"Failed to build Helm dependencies (may need network access):\n{result.stderr}")

            # Verify charts were actually downloaded
            if not charts_dir.exists() or not any(charts_dir.glob("*.tgz")):
                pytest.skip(
                    "Helm dependency build succeeded but charts directory is empty. "
                    "This may indicate a network issue or missing chart repositories."
                )

            return True
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


@pytest.mark.requires_helm
@pytest.mark.xdist_group(name="testhelmtemplaterendering")
class TestHelmTemplateRendering:
    """Test Helm chart template rendering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("helm")
    def test_helm_template_renders_without_errors(self, helm_dependencies_built):
        """Test that helm template command succeeds."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
        )

        assert result.returncode == 0, f"Helm template failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"

    @requires_tool("helm")
    def test_helm_template_produces_valid_yaml(self, helm_dependencies_built):
        """Test that rendered templates are valid YAML."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
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

    @requires_tool("helm")
    def test_helm_template_checksum_annotations_present(self, helm_dependencies_built):
        """Test that deployment has checksum annotations for config/secret changes."""
        result = subprocess.run(
            ["helm", "template", "test-release", str(CHART_PATH)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60
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


@pytest.mark.requires_helm
@pytest.mark.xdist_group(name="testhelmlint")
class TestHelmLint:
    """Test Helm chart lint passes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("helm")
    def test_helm_lint_passes(self):
        """Test that helm lint passes without warnings or errors."""
        result = subprocess.run(["helm", "lint", str(CHART_PATH)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60)

        assert result.returncode == 0, f"Helm lint failed:\n{result.stderr}\n{result.stdout}"

    @requires_tool("helm")
    def test_helm_lint_output_contains_success(self):
        """Test that helm lint output indicates success."""
        result = subprocess.run(["helm", "lint", str(CHART_PATH)], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60)

        assert result.returncode == 0, "Helm lint command failed"

        # Helm lint success messages
        output = result.stdout + result.stderr
        assert "linted" in output.lower() or "no failures" in output.lower(), (
            f"Helm lint output doesn't indicate success:\n{output}"
        )


@pytest.mark.xdist_group(name="testhelmdependencies")
class TestHelmDependencies:
    """Test Helm chart dependencies are available."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_helm_command_available(self):
        """Test that helm command is available in PATH."""
        result = subprocess.run(["which", "helm"], capture_output=True, text=True, timeout=60)

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


@pytest.mark.requires_helm
@pytest.mark.xdist_group(name="testhelmtemplatewithvalues")
class TestHelmTemplateWithValues:
    """Test Helm template rendering with different values."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("helm")
    def test_helm_template_with_custom_values(self, helm_dependencies_built):
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
                timeout=60,
            )

            assert result.returncode == 0, f"Helm template with custom values failed: {result.stderr}"
            assert len(result.stdout) > 0, "Helm template produced no output"

        finally:
            # Clean up
            if temp_values.exists():
                temp_values.unlink()

    @requires_tool("helm")
    def test_helm_template_with_staging_values(self, helm_dependencies_built):
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
            timeout=60,
        )

        assert result.returncode == 0, f"Helm template with staging values failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"

    @requires_tool("helm")
    def test_helm_template_with_production_values(self, helm_dependencies_built):
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
            timeout=60,
        )

        assert result.returncode == 0, f"Helm template with production values failed: {result.stderr}"
        assert len(result.stdout) > 0, "Helm template produced no output"
