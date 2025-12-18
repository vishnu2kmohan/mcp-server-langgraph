"""
MCP Server Input Models

Pydantic models for tool input validation.
Follows Anthropic best practices for tool schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatInput(BaseModel):
    """
    Input schema for agent_chat tool.

    Follows Anthropic best practices:
    - Unambiguous parameter names (user_id not username, message not query)
    - Response format control for token efficiency
    - Clear field descriptions
    """

    message: str = Field(
        description="The user message to send to the agent",
        min_length=1,
        max_length=10000,
    )
    token: str = Field(
        description=(
            "JWT authentication token. Obtain via /auth/login endpoint (HTTP) "
            "or external authentication service. Required for all tool calls."
        )
    )
    user_id: str = Field(
        description=(
            "User identifier for authentication and authorization. "
            "Accepts both plain usernames ('alice') and OpenFGA-prefixed IDs ('user:alice'). "
            "The system will normalize both formats automatically."
        )
    )
    thread_id: str | None = Field(
        default=None,
        description="Optional thread ID for conversation continuity (e.g., 'conv_123')",
    )
    response_format: Literal["concise", "detailed"] = Field(
        default="concise",
        description=(
            "Response verbosity level. "
            "'concise' returns ~500 tokens (faster, less context). "
            "'detailed' returns ~2000 tokens (comprehensive, more context)."
        ),
    )

    # Backward compatibility - DEPRECATED
    username: str | None = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED: Use 'user_id' instead. Maintained for backward compatibility.",
    )

    @property
    def effective_user_id(self) -> str:
        """Get effective user ID, prioritizing user_id over deprecated username."""
        return self.user_id if hasattr(self, "user_id") and self.user_id else (self.username or "")


class SearchConversationsInput(BaseModel):
    """Input schema for conversation_search tool."""

    query: str = Field(
        description="Search query to filter conversations. Empty string returns recent conversations.",
        min_length=0,
        max_length=500,
    )
    token: str = Field(
        description=(
            "JWT authentication token. Obtain via /auth/login endpoint (HTTP) "
            "or external authentication service. Required for all tool calls."
        )
    )
    user_id: str = Field(
        description="User identifier for authentication and authorization",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of conversations to return (1-50)",
    )

    # Backward compatibility - DEPRECATED
    username: str | None = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED: Use 'user_id' instead. Maintained for backward compatibility.",
    )

    @property
    def effective_user_id(self) -> str:
        """Get effective user ID, prioritizing user_id over deprecated username."""
        return self.user_id if hasattr(self, "user_id") and self.user_id else (self.username or "")


class GetConversationInput(BaseModel):
    """Input schema for conversation_get tool."""

    thread_id: str = Field(
        description="Thread ID of the conversation to retrieve",
    )
    token: str = Field(
        description="JWT authentication token",
    )
    user_id: str = Field(
        description="User identifier for authentication and authorization",
    )
    max_messages: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of messages to return",
    )
    include_metadata: bool = Field(
        default=False,
        description="Include message metadata in response",
    )


class ExecutePythonInput(BaseModel):
    """Input schema for execute_python tool."""

    code: str = Field(
        description="Python code to execute in sandboxed environment",
        min_length=1,
        max_length=50000,
    )
    token: str = Field(
        description="JWT authentication token",
    )
    user_id: str = Field(
        description="User identifier for authentication and authorization",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Execution timeout in seconds",
    )


class SearchToolsInput(BaseModel):
    """Input schema for search_tools tool."""

    query: str = Field(
        description="Search query for finding tools by name or description",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of tools to return",
    )
