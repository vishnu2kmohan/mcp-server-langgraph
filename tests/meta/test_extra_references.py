"""Meta-test: Validate all --extra references match pyproject.toml optional-dependencies.

This test prevents the "partial migration" issue where an extra is removed from
pyproject.toml but references remain in Docker, Makefile, scripts, or documentation.

Created: 2025-11-28 in response to PR #121 CI failures where:
- builder extra was removed from pyproject.toml
- But --extra builder references remained in Dockerfile, Makefile, docs
- CI failed with: "Extra `builder` is not defined in the project's `optional-dependencies`"

This test catches such issues locally before they reach CI.
"""

from __future__ import annotations

import gc
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Module-level pytest marker
pytestmark = pytest.mark.meta

if TYPE_CHECKING:
    from collections.abc import Set

# Files to scan for --extra references
SCAN_PATTERNS = [
    "docker/Dockerfile*",
    "Makefile",
    ".github/workflows/*.yaml",
    ".github/workflows/*.yml",
    "scripts/**/*.sh",
    "scripts/**/*.py",
]

# Files to exclude (historical docs, templates, etc.)
EXCLUDE_PATTERNS = [
    "docs-internal/*",  # Historical reports
    ".github/WORKFLOW_AUDIT_COMPLETION_REPORT.md",  # Historical audit
]


@pytest.mark.meta
@pytest.mark.validation
@pytest.mark.xdist_group(name="test_extra_references")
class TestExtraReferences:
    """Validate that all --extra X references correspond to actual extras in pyproject.toml."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root path."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def valid_extras(self, repo_root: Path) -> Set[str]:
        """Parse pyproject.toml and return all valid optional-dependencies names."""
        import tomllib  # Python 3.11+ stdlib

        pyproject_path = repo_root / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Get all optional-dependencies keys
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        return set(optional_deps.keys())

    def _extract_extra_references(self, content: str) -> list[tuple[str, int]]:
        """Extract all --extra X references from file content.

        Returns list of (extra_name, line_number) tuples.
        """
        references = []
        # Match --extra followed by a word (the extra name)
        pattern = r"--extra\s+([a-zA-Z0-9_-]+)"

        for i, line in enumerate(content.split("\n"), start=1):
            # Skip comments (shell, yaml, python)
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for match in re.finditer(pattern, line):
                extra_name = match.group(1)
                references.append((extra_name, i))

        return references

    def _should_scan_file(self, path: Path) -> bool:
        """Check if file should be scanned (not in exclude patterns)."""
        for exclude in EXCLUDE_PATTERNS:
            if path.match(exclude):
                return False
        return True

    def test_dockerfile_extras_exist(self, repo_root: Path, valid_extras: Set[str]):
        """Verify all --extra X references in Dockerfiles correspond to valid extras."""
        docker_dir = repo_root / "docker"
        if not docker_dir.exists():
            pytest.skip("No docker directory found")

        invalid_refs = []

        for dockerfile in docker_dir.glob("Dockerfile*"):
            if not self._should_scan_file(dockerfile):
                continue

            content = dockerfile.read_text()
            refs = self._extract_extra_references(content)

            for extra_name, line_num in refs:
                if extra_name not in valid_extras:
                    invalid_refs.append(
                        f"  {dockerfile.relative_to(repo_root)}:{line_num}: --extra {extra_name} (not in pyproject.toml)"
                    )

        assert not invalid_refs, (
            "Found --extra references to non-existent extras:\n"
            + "\n".join(invalid_refs)
            + f"\n\nValid extras in pyproject.toml: {sorted(valid_extras)}"
        )

    def test_makefile_extras_exist(self, repo_root: Path, valid_extras: Set[str]):
        """Verify all --extra X references in Makefile correspond to valid extras."""
        makefile = repo_root / "Makefile"
        if not makefile.exists():
            pytest.skip("No Makefile found")

        content = makefile.read_text()
        refs = self._extract_extra_references(content)
        invalid_refs = []

        for extra_name, line_num in refs:
            if extra_name not in valid_extras:
                invalid_refs.append(f"  Makefile:{line_num}: --extra {extra_name}")

        assert not invalid_refs, (
            "Found --extra references to non-existent extras in Makefile:\n"
            + "\n".join(invalid_refs)
            + f"\n\nValid extras in pyproject.toml: {sorted(valid_extras)}"
        )

    def test_workflow_extras_exist(self, repo_root: Path, valid_extras: Set[str]):
        """Verify all --extra X references in GitHub workflows correspond to valid extras."""
        workflows_dir = repo_root / ".github" / "workflows"
        if not workflows_dir.exists():
            pytest.skip("No .github/workflows directory found")

        invalid_refs = []

        for workflow in workflows_dir.glob("*.yaml"):
            if not self._should_scan_file(workflow):
                continue

            content = workflow.read_text()
            refs = self._extract_extra_references(content)

            for extra_name, line_num in refs:
                if extra_name not in valid_extras:
                    invalid_refs.append(f"  {workflow.relative_to(repo_root)}:{line_num}: --extra {extra_name}")

        for workflow in workflows_dir.glob("*.yml"):
            if not self._should_scan_file(workflow):
                continue

            content = workflow.read_text()
            refs = self._extract_extra_references(content)

            for extra_name, line_num in refs:
                if extra_name not in valid_extras:
                    invalid_refs.append(f"  {workflow.relative_to(repo_root)}:{line_num}: --extra {extra_name}")

        assert not invalid_refs, (
            "Found --extra references to non-existent extras in workflows:\n"
            + "\n".join(invalid_refs)
            + f"\n\nValid extras in pyproject.toml: {sorted(valid_extras)}"
        )

    def test_scripts_extras_exist(self, repo_root: Path, valid_extras: Set[str]):
        """Verify all --extra X references in scripts correspond to valid extras."""
        scripts_dir = repo_root / "scripts"
        if not scripts_dir.exists():
            pytest.skip("No scripts directory found")

        invalid_refs = []

        for script in scripts_dir.glob("**/*.sh"):
            if not self._should_scan_file(script):
                continue

            content = script.read_text()
            refs = self._extract_extra_references(content)

            for extra_name, line_num in refs:
                if extra_name not in valid_extras:
                    invalid_refs.append(f"  {script.relative_to(repo_root)}:{line_num}: --extra {extra_name}")

        for script in scripts_dir.glob("**/*.py"):
            if not self._should_scan_file(script):
                continue

            content = script.read_text()
            refs = self._extract_extra_references(content)

            for extra_name, line_num in refs:
                if extra_name not in valid_extras:
                    invalid_refs.append(f"  {script.relative_to(repo_root)}:{line_num}: --extra {extra_name}")

        assert not invalid_refs, (
            "Found --extra references to non-existent extras in scripts:\n"
            + "\n".join(invalid_refs)
            + f"\n\nValid extras in pyproject.toml: {sorted(valid_extras)}"
        )

    def test_valid_extras_discovery(self, valid_extras: Set[str]):
        """Verify we can discover valid extras from pyproject.toml."""
        # Should have at least these common extras
        expected_extras = {"dev", "cli", "secrets"}

        missing = expected_extras - valid_extras
        assert not missing, f"Expected extras not found in pyproject.toml: {missing}\nFound extras: {sorted(valid_extras)}"

        # builder should NOT be in valid extras anymore
        assert "builder" not in valid_extras, (
            "builder extra should have been removed from pyproject.toml.\n"
            "This extra was removed 2025-11-28 as dependencies were merged into dev."
        )
