"""
Skill Loader

Parses SKILL.md files with YAML frontmatter per Anthropic's
Agent Skills specification.

SKILL.md Format:
    ---
    name: web-research
    description: Research topics using web search
    dependencies:
      - beautifulsoup4>=4.12.0
    sandbox_config:
      network: allowlist
      allowed_domains:
        - "*.google.com"
    ---

    # Web Research Skill

    [Instructions for Claude to follow]

Usage:
    from mcp_server_langgraph.skills.loader import SkillLoader

    loader = SkillLoader()
    skill = loader.load_from_path("/path/to/SKILL.md")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from mcp_server_langgraph.skills.models import SandboxConfig, SecretVolume, Skill


class SkillError(Exception):
    """Base exception for skill-related errors."""

    pass


class SkillNotFoundError(SkillError):
    """Raised when a skill file cannot be found."""

    pass


class SkillParseError(SkillError):
    """Raised when SKILL.md YAML parsing fails."""

    pass


class SkillValidationError(SkillError):
    """Raised when skill data fails validation."""

    pass


# Pattern to match YAML frontmatter
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL,
)


class SkillLoader:
    """Loads skills from SKILL.md files."""

    def load_from_string(self, content: str) -> Skill:
        """Load a skill from SKILL.md content string.

        Args:
            content: SKILL.md file content

        Returns:
            Parsed Skill object

        Raises:
            SkillParseError: If YAML parsing fails
            SkillValidationError: If validation fails
        """
        content = content.strip()

        # Parse frontmatter
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            raise SkillParseError("No YAML frontmatter found in SKILL.md")

        yaml_content = match.group(1)
        markdown_content = match.group(2).strip()

        # Parse YAML
        try:
            data: dict[str, Any] = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            raise SkillParseError(f"Invalid YAML frontmatter: {e}") from e

        # Add markdown as instructions
        data["instructions"] = markdown_content

        # Normalize allowed-tools (YAML/Claude Code convention) to allowed_tools (Python field)
        if "allowed-tools" in data and "allowed_tools" not in data:
            data["allowed_tools"] = data.pop("allowed-tools")

        # Extract runtime fields from nested metadata (agentskills.io spec compliance)
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            for key in (
                "dependencies",
                "sandbox_config",
                "required_secrets",
                "optional_secrets",
                "secret_volumes",
            ):
                if key not in data and key in metadata:
                    data[key] = metadata[key]

        # Convert sandbox_config dict to SandboxConfig object
        if "sandbox_config" in data and isinstance(data["sandbox_config"], dict):
            data["sandbox_config"] = SandboxConfig(**data["sandbox_config"])

        # Convert secret_volumes list to SecretVolume objects
        if "secret_volumes" in data and isinstance(data["secret_volumes"], list):
            data["secret_volumes"] = [SecretVolume(**v) if isinstance(v, dict) else v for v in data["secret_volumes"]]

        # Validate and create Skill
        try:
            skill = Skill(**data)
        except ValidationError as e:
            raise SkillValidationError(f"Skill validation failed: {e}") from e

        return skill

    def load_from_path(self, path: Path | str) -> Skill:
        """Load a skill from a SKILL.md file path.

        Args:
            path: Path to SKILL.md file

        Returns:
            Parsed Skill object

        Raises:
            SkillNotFoundError: If file doesn't exist
            SkillParseError: If parsing fails
            SkillValidationError: If validation fails
        """
        path = Path(path)

        if not path.exists():
            raise SkillNotFoundError(f"Skill file not found: {path}")

        content = path.read_text(encoding="utf-8")
        return self.load_from_string(content)

    def load_from_directory(self, directory: Path | str) -> Skill:
        """Load a skill from a directory containing SKILL.md.

        Args:
            directory: Directory containing SKILL.md

        Returns:
            Parsed Skill object with path set to the directory

        Raises:
            SkillNotFoundError: If SKILL.md not found in directory
        """
        directory = Path(directory)
        skill_path = directory / "SKILL.md"

        if not skill_path.exists():
            raise SkillNotFoundError(f"No SKILL.md found in: {directory}")

        skill = self.load_from_path(skill_path)
        # Set the path to the skill directory
        skill.path = directory
        return skill

    def discover_skills(self, base_path: Path | str) -> list[Skill]:
        """Discover all skills in a directory tree.

        Searches for SKILL.md files in subdirectories.

        Args:
            base_path: Base directory to search

        Returns:
            List of discovered skills
        """
        base_path = Path(base_path)
        skills: list[Skill] = []

        if not base_path.exists():
            return skills

        for skill_file in base_path.rglob("SKILL.md"):
            try:
                skill = self.load_from_path(skill_file)
                skills.append(skill)
            except SkillError:
                # Skip invalid skills during discovery
                pass

        return skills
