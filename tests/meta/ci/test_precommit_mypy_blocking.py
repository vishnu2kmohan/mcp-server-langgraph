"""
Test that pre-commit MyPy hooks are configured correctly

This test ensures MyPy runs during pre-push and blocks on errors,
maintaining local/CI parity.

Following TDD principles: Write test first, then fix pre-commit config

Regression prevention for validation audit finding:
- MyPy hooks set to 'manual' stage (non-blocking)
- Should be on 'pre-push' stage and fail on errors
"""

import gc
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="precommit_mypy_config")
class TestPreCommitMyPyConfiguration:
    """Test that pre-commit hooks have MyPy configured as blocking"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_mypy_hook_exists_in_precommit_config(self):
        """
        Test that .pre-commit-config.yaml contains MyPy hook.
        """
        config_path = Path(".pre-commit-config.yaml")
        assert config_path.exists(), ".pre-commit-config.yaml not found"

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Find MyPy hooks
        mypy_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower() or "mypy" in hook.get("name", "").lower():
                    mypy_hooks.append(hook)

        assert len(mypy_hooks) > 0, "No MyPy hooks found in .pre-commit-config.yaml"

    def test_mypy_hook_is_not_manual_stage(self):
        """
        Test that MyPy hooks are NOT set to 'manual' stage.

        RED Phase: Will FAIL because MyPy hooks have stages: [manual]

        GREEN Phase: After moving to pre-push stage, should PASS

        Manual stage means MyPy only runs when explicitly invoked,
        not during normal git operations. This creates local/CI parity gap.
        """
        config_path = Path(".pre-commit-config.yaml")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Find MyPy hooks and check their stages
        manual_mypy_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower() or "mypy" in hook.get("name", "").lower():
                    stages = hook.get("stages", [])
                    if "manual" in stages:
                        manual_mypy_hooks.append({"id": hook.get("id"), "name": hook.get("name"), "stages": stages})

        if manual_mypy_hooks:
            hook_details = "\n".join([f"  - {h['name']} (id: {h['id']}): stages={h['stages']}" for h in manual_mypy_hooks])
            pytest.fail(
                f"MyPy hooks set to 'manual' stage!\n"
                f"Found {len(manual_mypy_hooks)} manual MyPy hooks:\n{hook_details}\n\n"
                f"This creates local/CI parity gap:\n"
                f"- Local: MyPy only runs when manually invoked\n"
                f"- CI: MyPy runs automatically and blocks builds\n\n"
                f"Fix: Remove 'stages: [manual]' or change to 'stages: [pre-push]'\n"
                f"Location: .pre-commit-config.yaml, MyPy hook configuration"
            )

    def test_mypy_hook_configured_for_pre_push(self):
        """
        Test that at least one MyPy hook runs on pre-push stage.

        MyPy should run during pre-push to catch type errors before
        pushing to remote, matching CI behavior.
        """
        config_path = Path(".pre-commit-config.yaml")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Find MyPy hooks configured for pre-push
        pre_push_mypy_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower() or "mypy" in hook.get("name", "").lower():
                    stages = hook.get("stages", [])
                    # If no stages specified, it runs on all stages (including pre-push)
                    # If stages specified, check for pre-push
                    if not stages or "pre-push" in stages:
                        pre_push_mypy_hooks.append(hook.get("name", hook.get("id")))

        assert len(pre_push_mypy_hooks) > 0, (
            "No MyPy hooks configured for pre-push stage!\n"
            "MyPy should run during pre-push to maintain local/CI parity.\n"
            "Add: stages: [pre-push] to MyPy hook configuration"
        )

    def test_mypy_hook_files_pattern_includes_src(self):
        """
        Test that MyPy hooks target the src/ directory.

        Ensures MyPy runs on the actual source code, not just tests.
        The target can be specified via files pattern OR entry command.
        """
        config_path = Path(".pre-commit-config.yaml")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Find MyPy hooks and check files pattern OR entry command
        src_mypy_hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "mypy" in hook.get("id", "").lower() or "mypy" in hook.get("name", "").lower():
                    files_pattern = hook.get("files", "")
                    entry_cmd = hook.get("entry", "")

                    # Check if hook targets src/ via files pattern OR entry command
                    if (
                        "src" in files_pattern
                        or "mcp_server_langgraph" in files_pattern
                        or "src" in entry_cmd
                        or "mcp_server_langgraph" in entry_cmd
                    ):
                        src_mypy_hooks.append(hook.get("name", hook.get("id")))

        assert len(src_mypy_hooks) > 0, (
            "No MyPy hooks configured to check src/ directory!\n"
            "MyPy should validate source code type annotations.\n"
            "Add either:\n"
            "  - files: ^src/mcp_server_langgraph/ OR\n"
            "  - entry: uv run mypy src/mcp_server_langgraph"
        )

    def test_precommit_hook_validates_correctly(self):
        """
        Test that pre-commit config is valid YAML and can be loaded.

        This catches syntax errors in the configuration file.
        """
        config_path = Path(".pre-commit-config.yaml")

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            assert isinstance(config, dict), "Config should be a dictionary"
            assert "repos" in config, "Config should have 'repos' key"
            assert isinstance(config["repos"], list), "repos should be a list"

        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in .pre-commit-config.yaml: {e}")
        except Exception as e:
            pytest.fail(f"Error loading .pre-commit-config.yaml: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
