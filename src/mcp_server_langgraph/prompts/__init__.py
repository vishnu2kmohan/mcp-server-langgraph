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

from typing import Optional

from mcp_server_langgraph.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from mcp_server_langgraph.prompts.response_prompt import RESPONSE_SYSTEM_PROMPT
from mcp_server_langgraph.prompts.verification_prompt import VERIFICATION_SYSTEM_PROMPT

__all__ = [
    "ROUTER_SYSTEM_PROMPT",
    "RESPONSE_SYSTEM_PROMPT",
    "VERIFICATION_SYSTEM_PROMPT",
    "get_prompt",
]


def get_prompt(prompt_name: str, version: Optional[str] = None) -> str:
    """
    Get a prompt by name with optional versioning.

    Args:
        prompt_name: Name of the prompt ("router", "response", "verification")
        version: Optional version (default: latest)

    Returns:
        Prompt string

    Raises:
        ValueError: If prompt name is unknown
    """
    prompts = {
        "router": ROUTER_SYSTEM_PROMPT,
        "response": RESPONSE_SYSTEM_PROMPT,
        "verification": VERIFICATION_SYSTEM_PROMPT,
    }

    if prompt_name not in prompts:
        raise ValueError(f"Unknown prompt: {prompt_name}. Available: {list(prompts.keys())}")

    # TODO: Implement versioning when needed
    return prompts[prompt_name]
