"""
Skill Data Models

Pydantic models for skills per Anthropic's Agent Skills specification.
Skills are loaded from SKILL.md files with YAML frontmatter.

Usage:
    from mcp_server_langgraph.skills.models import Skill, SandboxConfig

    skill = Skill(
        name="web-research",
        description="Research topics using web search",
        dependencies=["httpx>=0.25.0"],
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SecretVolume(BaseModel):
    """Configuration for volume-mounted secrets.

    Supports K8s secret types like TLS certificates and SSH keys
    that need to be mounted as files rather than environment variables.
    """

    type: str = Field(
        description="Secret type (tls, ssh-auth, etc.)",
    )
    mount_path: str = Field(
        description="Path to mount the secret volume",
    )


class SandboxConfig(BaseModel):
    """Sandbox configuration for skill execution.

    Controls network access and resource limits for skill scripts.
    """

    network: Literal["none", "allowlist", "unrestricted"] = Field(
        default="none",
        description="Network access mode",
    )
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Allowed domains when network=allowlist",
    )
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time in seconds",
    )
    memory_mb: int = Field(
        default=256,
        description="Maximum memory in MB",
    )


class Skill(BaseModel):
    """A skill that extends agent capabilities.

    Skills are loaded from SKILL.md files with YAML frontmatter
    per Anthropic's Agent Skills specification.
    """

    # Required fields
    name: str = Field(
        description="Unique skill identifier (kebab-case)",
    )
    description: str = Field(
        description="Short description of the skill",
    )

    # Optional fields
    version: str = Field(
        default="1.0.0",
        description="Semantic version of the skill",
    )
    author: str = Field(
        default="",
        description="Skill author or organization",
    )
    source: str = Field(
        default="local",
        description="Marketplace source URL or 'local'",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and search",
    )

    # AgentSkills.io compliance fields (Appendix B)
    license: str = Field(
        default="",
        description="License identifier (e.g., MIT, Apache-2.0)",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Pre-approved tools this skill can use (e.g., filesystem:read_file)",
    )
    category: str = Field(
        default="",
        description="Skill category (e.g., research, api-integration, automation)",
    )

    # Instructions and examples
    instructions: str = Field(
        default="",
        description="Markdown instructions for Claude",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example usage prompts",
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list,
        description="Python package dependencies (pip format)",
    )

    # Sandbox configuration
    sandbox_config: SandboxConfig | None = Field(
        default=None,
        description="Sandbox execution configuration",
    )

    # Secret configuration
    required_secrets: list[str] = Field(
        default_factory=list,
        description="Required environment variable secrets",
    )
    optional_secrets: list[str] = Field(
        default_factory=list,
        description="Optional environment variable secrets",
    )
    secret_volumes: list[SecretVolume] = Field(
        default_factory=list,
        description="Volume-mounted secrets (TLS, SSH)",
    )

    # Scripts bundled with the skill
    scripts: list[str] = Field(
        default_factory=list,
        description="Bundled Python scripts for deterministic operations",
    )

    # AgentSkills.io spec: metadata (arbitrary key-value pairs)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata key-value pairs per agentskills.io spec",
    )

    # AgentSkills.io spec: compatibility (human-readable requirements)
    compatibility: str = Field(
        default="",
        description="Human-readable compatibility requirements string",
    )

    # Filesystem path (set by loader)
    path: Path | None = Field(
        default=None,
        description="Path to skill directory on filesystem",
    )

    model_config = ConfigDict(
        extra="ignore",  # Ignore unknown fields in YAML
        arbitrary_types_allowed=True,  # Allow Path type
    )

    @model_validator(mode="before")
    @classmethod
    def extract_from_metadata(cls, data: Any) -> Any:
        """Extract recognized fields from metadata for backward compatibility.

        Supports both flat YAML (legacy) and nested metadata (agentskills.io spec).
        Top-level fields take precedence over metadata values.
        """
        if not isinstance(data, dict):
            return data
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            return data
        extractable = (
            "version",
            "category",
            "author",
            "dependencies",
            "sandbox_config",
            "required_secrets",
            "optional_secrets",
            "secret_volumes",
        )
        for key in extractable:
            if key not in data and key in metadata:
                data[key] = metadata[key]
        return data
