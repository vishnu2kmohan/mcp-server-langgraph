"""
Centralized Prompt Management with XML Structure

Implements Anthropic's prompt engineering best practices:
- XML tags for structural clarity
- Right altitude principle (balanced specificity/flexibility)
- Minimalism with sufficiency
- Clear sectioning (<role>, <task>, <instructions>, <output_format>)

References:
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
"""

from mcp_server_langgraph.core.prompts.response_prompt import RESPONSE_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.verification_prompt import VERIFICATION_SYSTEM_PROMPT

__all__ = [
    "ROUTER_SYSTEM_PROMPT",
    "RESPONSE_SYSTEM_PROMPT",
    "VERIFICATION_SYSTEM_PROMPT",
    "get_prompt",
    "get_prompt_version",
    "list_prompt_versions",
]

# Prompt version registry
# Format: {prompt_name: {version: prompt_string}}
_PROMPT_VERSIONS: dict[str, dict[str, str]] = {
    "router": {
        "v1": ROUTER_SYSTEM_PROMPT,
        "latest": ROUTER_SYSTEM_PROMPT,
    },
    "response": {
        "v1": RESPONSE_SYSTEM_PROMPT,
        "latest": RESPONSE_SYSTEM_PROMPT,
    },
    "verification": {
        "v1": VERIFICATION_SYSTEM_PROMPT,
        "latest": VERIFICATION_SYSTEM_PROMPT,
    },
}

# Current version metadata
_PROMPT_METADATA: dict[str, dict[str, str]] = {
    "router": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "response": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "verification": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
}


def get_prompt(prompt_name: str, version: str | None = None) -> str:
    """
    Get a prompt by name with optional versioning.

    Args:
        prompt_name: Name of the prompt ("router", "response", "verification")
        version: Optional version string (default: "latest")

    Returns:
        Prompt string

    Raises:
        ValueError: If prompt name or version is unknown

    Examples:
        >>> get_prompt("router")  # Gets latest version
        >>> get_prompt("router", "v1")  # Gets specific version
        >>> get_prompt("verification", "latest")  # Explicitly latest
    """
    if prompt_name not in _PROMPT_VERSIONS:
        available = list(_PROMPT_VERSIONS.keys())
        raise ValueError(f"Unknown prompt: {prompt_name}. Available: {available}")

    version = version or "latest"
    prompt_versions = _PROMPT_VERSIONS[prompt_name]

    if version not in prompt_versions:
        available_versions = list(prompt_versions.keys())
        raise ValueError(f"Unknown version '{version}' for prompt '{prompt_name}'. Available: {available_versions}")

    return prompt_versions[version]


def get_prompt_version(prompt_name: str) -> str:
    """
    Get current version number for a prompt.

    Args:
        prompt_name: Name of the prompt

    Returns:
        Version string (e.g., "v1")

    Raises:
        ValueError: If prompt name is unknown
    """
    if prompt_name not in _PROMPT_METADATA:
        raise ValueError(f"Unknown prompt: {prompt_name}")

    return _PROMPT_METADATA[prompt_name]["current_version"]


def list_prompt_versions(prompt_name: str) -> list[str]:
    """
    List all available versions for a prompt.

    Args:
        prompt_name: Name of the prompt

    Returns:
        List of version strings

    Raises:
        ValueError: If prompt name is unknown
    """
    if prompt_name not in _PROMPT_VERSIONS:
        raise ValueError(f"Unknown prompt: {prompt_name}")

    return list(_PROMPT_VERSIONS[prompt_name].keys())
