#!/usr/bin/env python3
"""
Tests for YAML syntax validation across the project.

Following TDD principles:
1. RED: These tests verify all YAML files parse correctly
2. GREEN: Fix YAML syntax errors
3. REFACTOR: Add pre-commit hooks to prevent regressions
"""

import gc
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testprecommitconfigsyntax")
class TestPreCommitConfigSyntax:
    """Test pre-commit configuration files have valid YAML syntax."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pre_commit_requirements_check_valid_yaml(self):
        """
        Test that .pre-commit-config-requirements-check.yaml is valid YAML.

        This test will initially FAIL because the multiline bash script on line 20
        uses single quotes in a plain scalar, which causes parsing issues.

        After fix, should use block scalar syntax (|) for multiline content.
        """
        config_file = Path(__file__).parent.parent / ".pre-commit-config-requirements-check.yaml"

        assert config_file.exists(), f"Config file not found: {config_file}"

        # This should not raise yaml.YAMLError
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)

            assert config is not None, "YAML config should not be empty"
            assert isinstance(config, list), "Pre-commit config should be a list of repos"

            # Verify the structure
            assert len(config) > 0, "Config should have at least one repo"

            # Check first repo is 'local'
            first_repo = config[0]
            assert first_repo.get("repo") == "local", "First repo should be 'local'"

            # Check hooks exist
            hooks = first_repo.get("hooks", [])
            assert len(hooks) > 0, "Should have at least one hook"

            # Check first hook has required fields
            first_hook = hooks[0]
            assert "id" in first_hook, "Hook should have 'id' field"
            assert "name" in first_hook, "Hook should have 'name' field"
            assert "entry" in first_hook, "Hook should have 'entry' field"
            assert "language" in first_hook, "Hook should have 'language' field"

            # Verify entry is a string (not a malformed multiline)
            entry = first_hook.get("entry")
            assert isinstance(entry, str), "Entry should be a string"
            assert len(entry) > 0, "Entry should not be empty"

        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing error in {config_file}: {e}")

    def test_all_workflow_yaml_files_valid(self):
        """Test that all GitHub workflow YAML files are valid."""
        workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"

        if not workflows_dir.exists():
            pytest.skip("Workflows directory not found")

        yaml_files = list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))
        assert len(yaml_files) > 0, "Should have at least one workflow file"

        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    content = yaml.safe_load(f)

                assert content is not None, f"Workflow {yaml_file.name} should not be empty"

            except yaml.YAMLError as e:
                pytest.fail(f"YAML parsing error in {yaml_file}: {e}")

    def test_block_scalars_used_for_multiline_scripts(self):
        """
        Test that multiline scripts in pre-commit config are properly parsed.

        After using block scalar syntax (|), multiline bash scripts should parse
        correctly as strings with embedded newlines.
        """
        config_file = Path(__file__).parent.parent / ".pre-commit-config-requirements-check.yaml"

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # For each hook, verify entry is a valid string (proves block scalar worked)
        for repo in config:
            if repo.get("repo") == "local":
                for hook in repo.get("hooks", []):
                    entry = hook.get("entry", "")

                    # Entry should be a non-empty string
                    assert isinstance(entry, str), f"Hook '{hook.get('id')}' entry should be a string"
                    assert len(entry) > 0, f"Hook '{hook.get('id')}' entry should not be empty"

                    # If entry is multiline, verify it has actual newline characters
                    # This proves the block scalar (|) syntax worked correctly
                    if hook.get("id") == "check-unauthorized-requirements-files":
                        assert "\n" in entry, "Multiline entry should contain newline characters"


@pytest.mark.xdist_group(name="testkubernetesyamlsyntax")
class TestKubernetesYAMLSyntax:
    """Test Kubernetes manifest YAML files have valid syntax."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_helm_templates_directory_exists(self):
        """Verify Helm templates directory exists."""
        templates_dir = Path(__file__).parent.parent / "deployments" / "helm" / "mcp-server-langgraph" / "templates"

        if templates_dir.exists():
            yaml_files = list(templates_dir.glob("*.yaml"))
            # Note: Helm templates use Go templating, so they may not parse as valid YAML
            # This test just verifies the directory structure
            assert len(yaml_files) > 0, "Should have at least one template file"

    def test_kustomize_overlays_valid_yaml(self):
        """Test that Kustomize overlay files are valid YAML."""
        overlays_dir = Path(__file__).parent.parent / "deployments" / "overlays"

        if not overlays_dir.exists():
            pytest.skip("Overlays directory not found")

        # Find all kustomization.yaml files
        kustomization_files = list(overlays_dir.rglob("kustomization.yaml"))

        if not kustomization_files:
            pytest.skip("No kustomization.yaml files found")

        for kust_file in kustomization_files:
            try:
                with open(kust_file) as f:
                    content = yaml.safe_load(f)

                assert content is not None, f"{kust_file} should not be empty"
                assert isinstance(content, dict), f"{kust_file} should be a YAML dict"

            except yaml.YAMLError as e:
                pytest.fail(f"YAML parsing error in {kust_file}: {e}")


@pytest.mark.xdist_group(name="testyamlfileencoding")
class TestYAMLFileEncoding:
    """Test YAML files use correct encoding and no BOM."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_yaml_files_utf8_no_bom(self):
        """Test that YAML files are UTF-8 without BOM."""
        project_root = Path(__file__).parent.parent

        yaml_files = (
            list(project_root.glob("*.yaml"))
            + list(project_root.glob("*.yml"))
            + list((project_root / ".github" / "workflows").glob("*.yaml"))
            + list((project_root / ".github" / "workflows").glob("*.yml"))
        )

        for yaml_file in yaml_files:
            if yaml_file.exists() and yaml_file.is_file():
                with open(yaml_file, "rb") as f:
                    first_bytes = f.read(3)
                    # Check for UTF-8 BOM (EF BB BF)
                    assert first_bytes != b"\xef\xbb\xbf", f"{yaml_file} should not have UTF-8 BOM"


@pytest.mark.xdist_group(name="testyamlindentation")
class TestYAMLIndentation:
    """Test YAML files follow consistent indentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_yaml_uses_2_space_indentation(self):
        """Test that YAML files use 2-space indentation (not tabs)."""
        config_file = Path(__file__).parent.parent / ".pre-commit-config-requirements-check.yaml"

        with open(config_file) as f:
            content = f.read()

        # Check no tabs are used for indentation
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if line.startswith("\t"):
                pytest.fail(f"Line {i} starts with tab instead of spaces: {line[:20]}")


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "yaml: tests for YAML syntax validation")
    config.addinivalue_line("markers", "integration: integration tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
