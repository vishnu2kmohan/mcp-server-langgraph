"""STUDIO.md parser for YAML frontmatter + Markdown body.

Parses STUDIO.md configuration files with the following format:

    ---
    name: Project Name
    tools:
      enabled:
        - file_reader
        - web_search
    skills:
      enabled:
        - summarize
    ---
    # Instructions

    Markdown content here...

The parser extracts:
1. YAML frontmatter between --- delimiters → StudioConfig fields
2. Markdown body after frontmatter → instructions field

Usage:
    from mcp_server_langgraph.studio.config.parser import StudioParser

    parser = StudioParser()
    config = parser.parse(content)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from pydantic import ValidationError

from mcp_server_langgraph.studio.config.models import (
    StudioConfig,
    StudioCostConfig,
    StudioMemoryConfig,
    StudioModelsConfig,
    StudioRule,
    StudioSkillsConfig,
    StudioToolsConfig,
)


class StudioParseError(Exception):
    """Exception raised when STUDIO.md parsing fails.

    Attributes:
        message: Error description
        line: Optional line number where error occurred
        details: Optional additional details
    """

    def __init__(
        self,
        message: str,
        line: int | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize parse error.

        Args:
            message: Error description
            line: Optional line number
            details: Optional additional details
        """
        self.message = message
        self.line = line
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message."""
        parts = [self.message]
        if self.line is not None:
            parts.append(f"at line {self.line}")
        if self.details:
            parts.append(f"({self.details})")
        return " ".join(parts)


# Regex pattern for YAML frontmatter
FRONTMATTER_PATTERN = re.compile(
    r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)",
    re.DOTALL,
)


class StudioParser:
    """Parser for STUDIO.md configuration files.

    Parses STUDIO.md files with YAML frontmatter and Markdown body.
    The YAML section contains configuration options, while the
    Markdown body becomes the instructions field.
    """

    def parse(self, content: str) -> StudioConfig:
        """Parse STUDIO.md content into StudioConfig.

        Args:
            content: Raw STUDIO.md file content

        Returns:
            Parsed StudioConfig object

        Raises:
            StudioParseError: If parsing fails
        """
        # Extract frontmatter and body
        frontmatter, body = self._extract_sections(content)

        # Parse YAML frontmatter
        yaml_data = self._parse_yaml(frontmatter)

        # Build config from YAML data
        config = self._build_config(yaml_data, body)

        return config

    def _extract_sections(self, content: str) -> tuple[str, str]:
        """Extract YAML frontmatter and Markdown body.

        Args:
            content: Raw file content

        Returns:
            Tuple of (frontmatter, body)

        Raises:
            StudioParseError: If frontmatter not found
        """
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            raise StudioParseError(
                "Missing YAML frontmatter",
                details="File must start with --- delimited YAML section",
            )

        frontmatter = match.group(1)
        body = match.group(2).strip() if match.group(2) else ""

        return frontmatter, body

    def _parse_yaml(self, frontmatter: str) -> dict[str, Any]:
        """Parse YAML frontmatter into dict.

        Args:
            frontmatter: YAML content

        Returns:
            Parsed dict

        Raises:
            StudioParseError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(frontmatter)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise StudioParseError(
                    "Invalid YAML structure",
                    details="Frontmatter must be a YAML mapping",
                )
            return data
        except yaml.YAMLError as e:
            raise StudioParseError(
                "Invalid YAML syntax",
                details=str(e),
            ) from e

    def _build_config(
        self,
        yaml_data: dict[str, Any],
        body: str,
    ) -> StudioConfig:
        """Build StudioConfig from parsed data.

        Args:
            yaml_data: Parsed YAML dict
            body: Markdown body content

        Returns:
            StudioConfig object

        Raises:
            StudioParseError: If validation fails
        """
        # Check required name field
        if "name" not in yaml_data:
            raise StudioParseError(
                "Missing required field",
                details="'name' field is required in frontmatter",
            )

        # Build nested config objects
        config_data: dict[str, Any] = {
            "name": yaml_data["name"],
        }

        # Optional top-level fields
        if "description" in yaml_data:
            config_data["description"] = yaml_data["description"]
        if "version" in yaml_data:
            config_data["version"] = yaml_data["version"]

        # Tools section
        if "tools" in yaml_data and isinstance(yaml_data["tools"], dict):
            config_data["tools"] = StudioToolsConfig(**yaml_data["tools"])

        # Skills section
        if "skills" in yaml_data and isinstance(yaml_data["skills"], dict):
            config_data["skills"] = StudioSkillsConfig(**yaml_data["skills"])

        # Memory section
        if "memory" in yaml_data and isinstance(yaml_data["memory"], dict):
            config_data["memory"] = StudioMemoryConfig(**yaml_data["memory"])

        # Cost section
        if "cost" in yaml_data and isinstance(yaml_data["cost"], dict):
            config_data["cost"] = StudioCostConfig(**yaml_data["cost"])

        # Models section
        if "models" in yaml_data and isinstance(yaml_data["models"], dict):
            config_data["models"] = StudioModelsConfig(**yaml_data["models"])

        # Rules section
        if "rules" in yaml_data and isinstance(yaml_data["rules"], list):
            config_data["rules"] = [StudioRule(**r) for r in yaml_data["rules"] if isinstance(r, dict)]

        # Instructions from markdown body
        if body:
            config_data["instructions"] = body

        # Build final config
        try:
            return StudioConfig(**config_data)
        except ValidationError as e:
            raise StudioParseError(
                "Validation failed",
                details=str(e),
            ) from e
