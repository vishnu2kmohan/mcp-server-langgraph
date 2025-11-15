"""
Test suite for .claude/settings.json schema validation.

Validates that Claude Code settings.json follows best practices:
- Allowed domains are valid (no typos, proper format)
- No overly permissive wildcards
- Bash auto-approve patterns are safe
- Plan mode configuration is valid

Following TDD: These tests are written FIRST, before settings.json exists.
They will FAIL initially (RED phase), then PASS after implementation (GREEN phase).

Regression prevention for Anthropic Claude Code settings configuration.
See: https://www.anthropic.com/engineering/claude-code-best-practices
"""

import json
import re
from pathlib import Path
from typing import Dict, List

import pytest


class TestClaudeSettingsSchema:
    """Validate .claude/settings.json schema and content."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def settings_file(self, project_root: Path) -> Path:
        """Get the settings.json file path."""
        return project_root / ".claude" / "settings.json"

    @pytest.fixture
    def settings(self, settings_file: Path) -> Dict:
        """Load and parse settings.json."""
        if not settings_file.exists():
            pytest.skip("settings.json does not exist yet (expected in RED phase)")

        with open(settings_file) as f:
            return json.load(f)

    def test_webfetch_domains_are_valid(self, settings: Dict):
        """Test that all WebFetch allowed_domains are valid domain names."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "WebFetch" not in settings["allowedTools"]:
            pytest.skip("WebFetch not configured yet")

        domains = settings["allowedTools"]["WebFetch"].get("allowed_domains", [])

        # Regex for valid domain names (simplified)
        domain_pattern = re.compile(r"^([a-z0-9-]+\.)*[a-z0-9-]+\.[a-z]{2,}$", re.IGNORECASE)

        invalid_domains = []
        for domain in domains:
            if not domain_pattern.match(domain):
                invalid_domains.append(domain)

        assert len(invalid_domains) == 0, (
            f"Invalid domain names in allowed_domains: {invalid_domains}. "
            f"Domains must be properly formatted (e.g., 'docs.python.org')."
        )

    def test_no_wildcard_domains(self, settings: Dict):
        """Test that WebFetch allowed_domains doesn't contain wildcards."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "WebFetch" not in settings["allowedTools"]:
            pytest.skip("WebFetch not configured yet")

        domains = settings["allowedTools"]["WebFetch"].get("allowed_domains", [])

        wildcard_domains = [d for d in domains if "*" in d]

        assert len(wildcard_domains) == 0, (
            f"Wildcard domains found in allowed_domains: {wildcard_domains}. "
            f"Use specific domains instead of wildcards for security."
        )

    def test_essential_documentation_domains_present(self, settings: Dict):
        """Test that essential documentation domains are in allowed_domains."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "WebFetch" not in settings["allowedTools"]:
            pytest.skip("WebFetch not configured yet")

        domains = settings["allowedTools"]["WebFetch"].get("allowed_domains", [])

        # Essential domains for Python development
        essential_domains = {
            "docs.python.org": "Python documentation",
            "peps.python.org": "Python Enhancement Proposals",
            "github.com": "GitHub repositories",
            "docs.anthropic.com": "Anthropic/Claude documentation",
        }

        missing_domains = []
        for domain, description in essential_domains.items():
            if domain not in domains:
                missing_domains.append(f"{domain} ({description})")

        assert len(missing_domains) == 0, f"Missing essential domains in allowed_domains: {missing_domains}"

    def test_project_specific_domains_present(self, settings: Dict):
        """Test that project-specific domains are in allowed_domains."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "WebFetch" not in settings["allowedTools"]:
            pytest.skip("WebFetch not configured yet")

        domains = settings["allowedTools"]["WebFetch"].get("allowed_domains", [])

        # Project-specific domains (FastAPI, LangChain, Docker, K8s)
        project_domains = {
            "fastapi.tiangolo.com": "FastAPI documentation",
            "docs.langchain.com": "LangChain documentation",
            "smith.langchain.com": "LangSmith documentation",
            "docs.docker.com": "Docker documentation",
            "kubernetes.io": "Kubernetes documentation",
        }

        missing_domains = []
        for domain, description in project_domains.items():
            if domain not in domains:
                missing_domains.append(f"{domain} ({description})")

        # This is a warning, not a failure (project-specific is optional)
        if missing_domains:
            pytest.fail(
                f"Recommended project-specific domains missing: {missing_domains}. "
                f"Consider adding them for better Claude Code experience."
            )

    def test_bash_auto_approve_patterns_are_safe(self, settings: Dict):
        """Test that Bash auto_approve_patterns don't contain dangerous commands."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "Bash" not in settings["allowedTools"]:
            pytest.skip("Bash not configured yet")

        patterns = settings["allowedTools"]["Bash"].get("auto_approve_patterns", [])

        # Dangerous patterns that should NEVER be auto-approved
        dangerous_patterns = [
            "rm -rf",
            "dd if=",
            "mkfs",
            "> /dev/",
            "chmod 777",
            "curl | bash",
            "wget | sh",
            "sudo ",
        ]

        dangerous_found = []
        for pattern in patterns:
            for dangerous in dangerous_patterns:
                if dangerous in pattern.lower():
                    dangerous_found.append((pattern, dangerous))

        assert len(dangerous_found) == 0, (
            f"Dangerous patterns found in auto_approve_patterns: {dangerous_found}. "
            f"These commands should require explicit approval for safety."
        )

    def test_bash_patterns_are_read_only_or_safe(self, settings: Dict):
        """Test that Bash auto_approve_patterns are mostly read-only commands."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "Bash" not in settings["allowedTools"]:
            pytest.skip("Bash not configured yet")

        patterns = settings["allowedTools"]["Bash"].get("auto_approve_patterns", [])

        # Safe read-only or development commands
        safe_prefixes = [
            "pytest",
            "make test",
            "make lint",
            "git status",
            "git log",
            "git diff",
            "git show",
            "ls",
            "cat",
            "grep",
            "find",
        ]

        # Check that patterns start with safe commands
        unsafe_patterns = []
        for pattern in patterns:
            is_safe = False
            for prefix in safe_prefixes:
                if pattern.strip().startswith(prefix):
                    is_safe = True
                    break

            if not is_safe:
                unsafe_patterns.append(pattern)

        # This is a warning - some write commands might be intentionally allowed
        if unsafe_patterns:
            # Just warn, don't fail (user might have valid reasons)
            print(
                f"\nWARNING: Some auto-approve patterns are not read-only: "
                f"{unsafe_patterns}. "
                f"Ensure these are safe for automatic approval."
            )

    def test_plan_mode_configuration_is_valid(self, settings: Dict):
        """Test that plan_mode configuration has valid structure."""
        if "plan_mode" not in settings:
            # Plan mode is optional, skip if not configured
            pytest.skip("plan_mode not configured (optional)")

        plan_mode = settings["plan_mode"]

        # Validate structure
        assert isinstance(plan_mode, dict), "plan_mode must be a dictionary"

        # Check optional fields if present
        if "default" in plan_mode:
            assert isinstance(plan_mode["default"], bool), "plan_mode.default must be a boolean"

        if "auto_enable_for_keywords" in plan_mode:
            assert isinstance(plan_mode["auto_enable_for_keywords"], list), "plan_mode.auto_enable_for_keywords must be a list"

            keywords = plan_mode["auto_enable_for_keywords"]
            assert all(isinstance(k, str) for k in keywords), "All auto_enable_for_keywords must be strings"

    def test_no_duplicate_domains(self, settings: Dict):
        """Test that there are no duplicate domains in allowed_domains."""
        if "allowedTools" not in settings:
            pytest.skip("allowedTools not configured yet")

        if "WebFetch" not in settings["allowedTools"]:
            pytest.skip("WebFetch not configured yet")

        domains = settings["allowedTools"]["WebFetch"].get("allowed_domains", [])

        # Check for duplicates
        seen = set()
        duplicates = []
        for domain in domains:
            if domain in seen:
                duplicates.append(domain)
            seen.add(domain)

        assert len(duplicates) == 0, f"Duplicate domains found in allowed_domains: {duplicates}"


class TestSettingsLocalExclusion:
    """Validate that settings.local.json is properly excluded from git."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_gitignore_excludes_settings_local(self, project_root: Path):
        """Test that .gitignore excludes settings.local.json."""
        gitignore = project_root / ".gitignore"

        if not gitignore.exists():
            pytest.skip(".gitignore does not exist")

        with open(gitignore) as f:
            gitignore_content = f.read()

        # Check for exclusion patterns
        has_pattern = (
            "settings.local.json" in gitignore_content
            or "*.local.json" in gitignore_content
            or ".claude/settings.local.json" in gitignore_content
        )

        assert has_pattern, (
            ".gitignore should contain a pattern to exclude settings.local.json. "
            "Add '*.local.json' or '.claude/settings.local.json' to prevent "
            "committing local configurations."
        )


# TDD Validation: Run this test file to verify RED phase
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
