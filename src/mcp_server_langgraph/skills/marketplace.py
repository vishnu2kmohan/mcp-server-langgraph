"""
Skills Marketplace

Multi-marketplace integration for discovering and installing skills
from various sources including Anthropic's official skills repository.

Marketplaces:
- Anthropic (default): https://github.com/anthropics/skills
- Enterprise: Custom organizational skill repositories
- OCI: Container registry-based skill distribution

Usage:
    from mcp_server_langgraph.skills.marketplace import MarketplaceRegistry

    registry = MarketplaceRegistry()
    anthropic = registry.get("anthropic")
    skills = await client.list_skills(anthropic)
"""

from __future__ import annotations

import re
import time
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from mcp_server_langgraph.skills.metrics import record_marketplace_fetch


def parse_oci_uri(uri: str) -> dict[str, str] | None:
    """Parse an OCI registry URI into components.

    OCI URIs follow the format: oci://registry[:port]/namespace/repository

    Args:
        uri: OCI URI string

    Returns:
        Dictionary with registry, namespace, and repository, or None if invalid

    Examples:
        >>> parse_oci_uri("oci://ghcr.io/anthropics/skills")
        {"registry": "ghcr.io", "namespace": "anthropics", "repository": "skills"}

        >>> parse_oci_uri("oci://localhost:5000/org/repo")
        {"registry": "localhost:5000", "namespace": "org", "repository": "repo"}
    """
    # Pattern: oci://registry[:port]/namespace/repository
    match = re.match(r"^oci://([^/]+)/([^/]+)/([^/]+)/?$", uri)
    if not match:
        return None

    registry, namespace, repository = match.groups()
    return {
        "registry": registry,
        "namespace": namespace,
        "repository": repository,
    }


def parse_registry_uri(uri: str) -> dict[str, str] | None:
    """Parse a custom registry API URI.

    Registry URIs must use HTTPS and point to a REST API base URL.
    The API is expected to provide:
    - GET /skills - List all skills
    - GET /skills/{name} - Get skill details

    Args:
        uri: Registry API base URL (must be HTTPS)

    Returns:
        Dictionary with base_url (trailing slash stripped), or None if invalid

    Examples:
        >>> parse_registry_uri("https://skills.example.com/api/v1")
        {"base_url": "https://skills.example.com/api/v1"}

        >>> parse_registry_uri("https://registry.corp.com/skills/")
        {"base_url": "https://registry.corp.com/skills"}

        >>> parse_registry_uri("http://insecure.com/api")  # HTTP not allowed
        None
    """
    # Must be HTTPS
    if not uri.startswith("https://"):
        return None

    # Strip trailing slash for consistency
    base_url = uri.rstrip("/")

    # Validate it's a proper URL with host
    match = re.match(r"^https://[^/]+(/.*)?$", base_url)
    if not match:
        return None

    return {"base_url": base_url}


class MarketplaceConfig(BaseModel):
    """Configuration for a skill marketplace."""

    name: str = Field(description="Unique marketplace identifier")
    uri: str = Field(description="Marketplace URI (GitHub URL, OCI registry, etc.)")
    type: Literal["github", "oci", "registry"] = Field(description="Marketplace type")
    trusted: bool = Field(
        default=False,
        description="Whether skills from this marketplace are trusted",
    )
    auto_sync: bool = Field(
        default=False,
        description="Automatically sync skills from this marketplace",
    )
    requires_approval: bool = Field(
        default=True,
        description="Whether skills require admin approval before use",
    )


# Default Anthropic marketplace configuration
ANTHROPIC_MARKETPLACE = MarketplaceConfig(
    name="anthropic",
    uri="https://github.com/anthropics/skills",
    type="github",
    trusted=True,
    auto_sync=True,
    requires_approval=False,
)


class MarketplaceRegistry:
    """Registry for managing skill marketplaces.

    Provides registration, lookup, and management of multiple
    skill marketplaces with the Anthropic marketplace as default.
    """

    # Protected marketplace names that cannot be removed
    PROTECTED_MARKETPLACES = {"anthropic"}

    def __init__(self) -> None:
        """Initialize registry with default marketplaces."""
        self._marketplaces: dict[str, MarketplaceConfig] = {}
        # Register default Anthropic marketplace
        self._marketplaces["anthropic"] = ANTHROPIC_MARKETPLACE

    def get(self, name: str) -> MarketplaceConfig | None:
        """Get a marketplace by name.

        Args:
            name: Marketplace name

        Returns:
            MarketplaceConfig if found, None otherwise
        """
        return self._marketplaces.get(name)

    def register(self, config: MarketplaceConfig) -> None:
        """Register a new marketplace.

        Args:
            config: Marketplace configuration
        """
        self._marketplaces[config.name] = config

    def unregister(self, name: str) -> None:
        """Unregister a marketplace.

        Protected marketplaces (e.g., Anthropic) cannot be removed.

        Args:
            name: Marketplace name to remove
        """
        if name in self.PROTECTED_MARKETPLACES:
            return  # Cannot remove protected marketplaces
        self._marketplaces.pop(name, None)

    def list_all(self) -> list[MarketplaceConfig]:
        """List all registered marketplaces.

        Returns:
            List of all marketplace configurations
        """
        return list(self._marketplaces.values())

    def list_trusted(self) -> list[MarketplaceConfig]:
        """List only trusted marketplaces.

        Returns:
            List of trusted marketplace configurations
        """
        return [m for m in self._marketplaces.values() if m.trusted]


class MarketplaceClient:
    """Client for interacting with skill marketplaces.

    Provides methods to list, search, and fetch skills from
    configured marketplaces with local caching.
    """

    DEFAULT_CACHE_TTL = 3600  # 1 hour

    def __init__(self, cache_ttl_seconds: int = DEFAULT_CACHE_TTL) -> None:
        """Initialize marketplace client.

        Args:
            cache_ttl_seconds: Cache TTL for marketplace data
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    def _get_cache_key(self, marketplace: MarketplaceConfig) -> str:
        """Generate cache key for a marketplace.

        Args:
            marketplace: Marketplace configuration

        Returns:
            Cache key string
        """
        return f"{marketplace.name}:{marketplace.uri}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid.

        Args:
            cache_key: Cache key to check

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._cache:
            return False
        timestamp, _ = self._cache[cache_key]
        return (time.time() - timestamp) < self.cache_ttl_seconds

    async def list_skills(
        self,
        marketplace: MarketplaceConfig,
    ) -> list[dict[str, Any]]:
        """List available skills from a marketplace.

        Args:
            marketplace: Marketplace to query

        Returns:
            List of skill metadata dictionaries

        Note:
            Actual implementation depends on marketplace type (GitHub API, OCI, etc.)
        """
        cache_key = self._get_cache_key(marketplace)

        # Return cached data if valid
        if self._is_cache_valid(cache_key):
            _, skills = self._cache[cache_key]
            record_marketplace_fetch(
                marketplace_name=marketplace.name,
                operation="list_skills",
                success=True,
                cached=True,
            )
            return skills

        # Route to appropriate handler based on marketplace type
        handler_map = {
            "github": self._list_skills_github,
            "oci": self._list_skills_oci,
            "registry": self._list_skills_registry,
        }

        handler = handler_map.get(marketplace.type)
        if handler is None:
            # Unsupported type
            return []

        try:
            skills = await handler(marketplace)
            # Cache the results
            self._cache[cache_key] = (time.time(), skills)
            record_marketplace_fetch(
                marketplace_name=marketplace.name,
                operation="list_skills",
                success=True,
                cached=False,
            )
            return skills
        except Exception:
            record_marketplace_fetch(
                marketplace_name=marketplace.name,
                operation="list_skills",
                success=False,
                cached=False,
            )
            raise

    async def _list_skills_github(
        self,
        marketplace: MarketplaceConfig,
    ) -> list[dict[str, Any]]:
        """List skills from a GitHub repository.

        Args:
            marketplace: GitHub marketplace configuration

        Returns:
            List of skill metadata dictionaries
        """
        # Parse GitHub URL to get owner/repo
        # Expected format: https://github.com/{owner}/{repo}
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)", marketplace.uri)
        if not match:
            return []

        owner, repo = match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/skills"

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)

            if response.status_code != 200:
                return []

            contents = response.json()

            # Filter to only directories (skill folders)
            skills = [item for item in contents if item.get("type") == "dir"]

            return skills

    async def _list_skills_oci(
        self,
        marketplace: MarketplaceConfig,
    ) -> list[dict[str, Any]]:
        """List skills from an OCI registry.

        Uses the OCI Distribution API to list tags in the skills repository.
        Each tag corresponds to a skill name.

        Args:
            marketplace: OCI marketplace configuration

        Returns:
            List of skill metadata dictionaries
        """
        parsed = parse_oci_uri(marketplace.uri)
        if not parsed:
            return []

        registry = parsed["registry"]
        namespace = parsed["namespace"]
        repository = parsed["repository"]

        # OCI Distribution spec: GET /v2/{name}/tags/list
        tags_url = f"https://{registry}/v2/{namespace}/{repository}/tags/list"

        async with httpx.AsyncClient() as client:
            response = await client.get(tags_url)

            if response.status_code != 200:
                return []

            data = response.json()
            tags = data.get("tags", [])

            # Convert tags to skill metadata
            skills = [{"name": tag, "type": "oci"} for tag in tags]
            return skills

    async def _list_skills_registry(
        self,
        marketplace: MarketplaceConfig,
    ) -> list[dict[str, Any]]:
        """List skills from a custom registry API.

        Calls GET {base_url}/skills to retrieve skill list.

        Args:
            marketplace: Registry marketplace configuration

        Returns:
            List of skill metadata dictionaries
        """
        parsed = parse_registry_uri(marketplace.uri)
        if not parsed:
            return []

        base_url = parsed["base_url"]
        skills_url = f"{base_url}/skills"

        async with httpx.AsyncClient() as client:
            response = await client.get(skills_url)

            if response.status_code != 200:
                return []

            data = response.json()

            # Support both array response and {skills: [...]} wrapper
            skills = data if isinstance(data, list) else data.get("skills", [])

            # Ensure each skill has type marker
            for skill in skills:
                if "type" not in skill:
                    skill["type"] = "registry"

            return skills

    async def fetch_skill(
        self,
        marketplace: MarketplaceConfig,
        skill_name: str,
    ) -> dict[str, Any] | None:
        """Fetch a specific skill from a marketplace.

        Args:
            marketplace: Marketplace containing the skill
            skill_name: Name of skill to fetch

        Returns:
            Skill metadata if found, None otherwise
        """
        # Route to appropriate handler based on marketplace type
        handler_map = {
            "github": self._fetch_skill_github,
            "oci": self._fetch_skill_oci,
            "registry": self._fetch_skill_registry,
        }

        handler = handler_map.get(marketplace.type)
        if handler is None:
            # Unsupported type
            return None

        try:
            result = await handler(marketplace, skill_name)
            record_marketplace_fetch(
                marketplace_name=marketplace.name,
                operation="fetch_skill",
                success=result is not None,
                cached=False,
            )
            return result
        except Exception:
            record_marketplace_fetch(
                marketplace_name=marketplace.name,
                operation="fetch_skill",
                success=False,
                cached=False,
            )
            raise

    async def _fetch_skill_github(
        self,
        marketplace: MarketplaceConfig,
        skill_name: str,
    ) -> dict[str, Any] | None:
        """Fetch a skill from a GitHub repository.

        Args:
            marketplace: GitHub marketplace configuration
            skill_name: Name of skill to fetch

        Returns:
            Skill metadata if found, None otherwise
        """
        # Parse GitHub URL to get owner/repo
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)", marketplace.uri)
        if not match:
            return None

        owner, repo = match.groups()
        # Fetch raw SKILL.md content
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/skills/{skill_name}/SKILL.md"

        async with httpx.AsyncClient() as client:
            response = await client.get(raw_url)

            if response.status_code != 200:
                return None

            content = response.text

            # Parse YAML frontmatter
            return self._parse_skill_md(content, skill_name)

    async def _fetch_skill_oci(
        self,
        marketplace: MarketplaceConfig,
        skill_name: str,
    ) -> dict[str, Any] | None:
        """Fetch a skill from an OCI registry.

        Downloads the OCI manifest and config blob for the skill.

        Args:
            marketplace: OCI marketplace configuration
            skill_name: Name of skill to fetch (corresponds to tag)

        Returns:
            Skill metadata if found, None otherwise
        """
        parsed = parse_oci_uri(marketplace.uri)
        if not parsed:
            return None

        registry = parsed["registry"]
        namespace = parsed["namespace"]
        repository = parsed["repository"]

        # OCI Distribution spec: GET /v2/{name}/manifests/{reference}
        manifest_url = f"https://{registry}/v2/{namespace}/{repository}/manifests/{skill_name}"

        async with httpx.AsyncClient() as client:
            # Fetch the manifest
            manifest_response = await client.get(
                manifest_url,
                headers={
                    "Accept": "application/vnd.oci.image.manifest.v1+json",
                },
            )

            if manifest_response.status_code != 200:
                return None

            manifest = manifest_response.json()

            # Get the config blob which contains skill metadata
            config_info = manifest.get("config", {})
            config_digest = config_info.get("digest")

            if not config_digest:
                return {"name": skill_name}

            # Fetch the config blob
            blob_url = f"https://{registry}/v2/{namespace}/{repository}/blobs/{config_digest}"
            config_response = await client.get(blob_url)

            if config_response.status_code != 200:
                return {"name": skill_name}

            config: dict[str, Any] = config_response.json()
            config["name"] = skill_name
            return config

    async def _fetch_skill_registry(
        self,
        marketplace: MarketplaceConfig,
        skill_name: str,
    ) -> dict[str, Any] | None:
        """Fetch a skill from a custom registry API.

        Calls GET {base_url}/skills/{name} to retrieve skill details.

        Args:
            marketplace: Registry marketplace configuration
            skill_name: Name of skill to fetch

        Returns:
            Skill metadata if found, None otherwise
        """
        parsed = parse_registry_uri(marketplace.uri)
        if not parsed:
            return None

        base_url = parsed["base_url"]
        skill_url = f"{base_url}/skills/{skill_name}"

        async with httpx.AsyncClient() as client:
            response = await client.get(skill_url)

            if response.status_code != 200:
                return None

            skill: dict[str, Any] = response.json()

            # Ensure name is set
            if "name" not in skill:
                skill["name"] = skill_name

            # Ensure type marker
            if "type" not in skill:
                skill["type"] = "registry"

            return skill

    def _parse_skill_md(self, content: str, skill_name: str) -> dict[str, Any]:
        """Parse SKILL.md content to extract metadata.

        Args:
            content: SKILL.md file content
            skill_name: Skill name (used as fallback)

        Returns:
            Skill metadata dictionary
        """
        # Pattern to match YAML frontmatter
        frontmatter_pattern = re.compile(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$",
            re.DOTALL,
        )

        match = frontmatter_pattern.match(content.strip())
        if not match:
            return {"name": skill_name, "content": content}

        yaml_content = match.group(1)
        markdown_content = match.group(2).strip()

        # Simple YAML parsing for key: value pairs
        metadata: dict[str, Any] = {"name": skill_name}
        for line in yaml_content.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                metadata[key] = value

        metadata["instructions"] = markdown_content
        return metadata
