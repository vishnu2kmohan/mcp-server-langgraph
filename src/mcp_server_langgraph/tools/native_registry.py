"""
Native tool definitions with builtin name mapping.

This module defines the mapping between native LLM provider tools
and their equivalent builtin tools for fallback scenarios.

NATIVE TOOL TYPES:
- Anthropic web_search_20250305: Web search via Anthropic's native tool
- Anthropic code_execution_20250825: Remote sandbox code execution
- Google googleSearch: Google's grounded search

NAMING CONVENTIONS:
- Native tools use provider's naming (code_execution, web_search)
- Builtin tools use our naming (execute_python, web_search)
- BUILTIN_TO_NATIVE maps our names to native names for lookup
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeToolDef:
    """Definition of a native LLM provider tool.

    Attributes:
        name: Simple name (e.g., "web_search", "code_execution")
        provider: Provider name (e.g., "anthropic", "google")
        provider_type: Provider's type identifier for the API
        description: Human-readable description
        fallback_builtin: Builtin tool name to fall back to if native unavailable
    """

    name: str
    provider: str
    provider_type: str
    description: str
    fallback_builtin: str | None


# Map (name, provider) → NativeToolDef
# Note: name is the native tool name, fallback_builtin is the builtin equivalent
NATIVE_TOOLS: dict[tuple[str, str], NativeToolDef] = {
    ("web_search", "anthropic"): NativeToolDef(
        name="web_search",
        provider="anthropic",
        provider_type="web_search_20250305",
        description="Search the web using Anthropic's native tool",
        fallback_builtin="web_search",
    ),
    ("web_search", "google"): NativeToolDef(
        name="web_search",
        provider="google",
        provider_type="googleSearch",
        description="Search using Google's grounded search",
        fallback_builtin="web_search",
    ),
    # code_execution maps to execute_python builtin
    ("code_execution", "anthropic"): NativeToolDef(
        name="code_execution",
        provider="anthropic",
        provider_type="code_execution_20250825",
        description="Execute code in Anthropic's remote sandbox",
        fallback_builtin="execute_python",
    ),
}


# Reverse mapping: builtin name → native name
# Used when looking up native equivalents for builtin tools
BUILTIN_TO_NATIVE: dict[str, str] = {
    "execute_python": "code_execution",
}


def get_native_for_builtin(builtin_name: str, provider: str) -> NativeToolDef | None:
    """Get native tool that can replace a builtin.

    This function handles the mapping between builtin tool names and
    their native equivalents. For example, "execute_python" builtin
    maps to "code_execution" native tool on Anthropic.

    Args:
        builtin_name: The builtin tool name (e.g., "execute_python", "web_search")
        provider: The provider name (e.g., "anthropic", "google")

    Returns:
        NativeToolDef if a native equivalent exists, None otherwise
    """
    # First check if there's a name mapping (e.g., execute_python → code_execution)
    native_name = BUILTIN_TO_NATIVE.get(builtin_name, builtin_name)

    # Look up the native tool by (name, provider)
    return NATIVE_TOOLS.get((native_name, provider))
