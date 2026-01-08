"""Semantic Index Models for Tool and Skill Discovery.

Data models for indexing tools, skills, and memories in vector stores
to enable semantic search and progressive disclosure.

Usage:
    from mcp_server_langgraph.tools.semantic_index import (
        ToolIndexEntry,
        SkillIndexEntry,
        MemoryIndexEntry,
        ToolCategory,
        SkillCategory,
    )

    # Create a tool index entry
    entry = ToolIndexEntry(
        tool_id="tool-123",
        name="calculator",
        description="Perform calculations",
        category=ToolCategory.CALCULATOR,
    )

    # Create from LangChain tool
    entry = ToolIndexEntry.from_langchain_tool(lc_tool, category="math")

ADR Reference: Plan for semantic tool/skill discovery
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp_server_langgraph.core.scopes import CapabilityScope

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class ToolCategory(StrEnum):
    """Standard tool categories for organization and filtering."""

    CALCULATOR = "calculator"
    SEARCH = "search"
    FILESYSTEM = "filesystem"
    CODE_EXECUTION = "code_execution"
    WEB = "web"
    COMPUTER_USE = "computer_use"
    DATA = "data"
    COMMUNICATION = "communication"
    OTHER = "other"


class SkillCategory(StrEnum):
    """Standard skill categories for organization and filtering."""

    DEVELOPMENT = "development"
    ANALYSIS = "analysis"
    WRITING = "writing"
    RESEARCH = "research"
    DESIGN = "design"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class MemoryType(StrEnum):
    """Types of memory entries."""

    PREFERENCE = "preference"
    CONTEXT = "context"
    FACT = "fact"
    INSTRUCTION = "instruction"
    FEEDBACK = "feedback"


@dataclass
class ToolIndexEntry:
    """Indexed tool metadata for semantic search.

    Represents a tool in the semantic index with metadata for
    discovery, filtering, and progressive disclosure.

    Attributes:
        tool_id: Unique identifier for the tool
        name: Tool name (matches LangChain tool.name)
        description: Human-readable description for semantic matching
        category: Tool category for filtering
        embedding: Vector embedding for semantic search (optional)
        scope: CapabilityScope for hierarchical resolution
        tenant_id: Tenant ID for multi-tenant isolation
        parameters_summary: Compact parameter description
        token_estimate: Estimated tokens for full tool schema
    """

    tool_id: str
    name: str
    description: str
    category: str
    embedding: list[float] | None = None
    scope: CapabilityScope = CapabilityScope.SESSION
    tenant_id: str | None = None
    parameters_summary: str = ""
    token_estimate: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Qdrant payload.

        Returns:
            Dictionary representation without embedding (stored separately)
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "scope": str(self.scope.value),
            "tenant_id": self.tenant_id,
            "parameters_summary": self.parameters_summary,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_langchain_tool(
        cls,
        tool: BaseTool,
        category: str = ToolCategory.OTHER,
        scope: CapabilityScope = CapabilityScope.SESSION,
        tenant_id: str | None = None,
    ) -> ToolIndexEntry:
        """Create ToolIndexEntry from a LangChain tool.

        Args:
            tool: LangChain BaseTool instance
            category: Tool category
            scope: CapabilityScope for the tool
            tenant_id: Optional tenant ID

        Returns:
            ToolIndexEntry with metadata from the tool
        """
        # Generate parameters summary from schema if available
        params_summary = ""
        if hasattr(tool, "args_schema") and tool.args_schema is not None:
            try:
                schema = tool.args_schema.model_json_schema()
                props = schema.get("properties", {})
                params = [f"{k}: {v.get('type', 'any')}" for k, v in props.items()]
                params_summary = ", ".join(params)
            except Exception:
                pass

        return cls(
            tool_id=f"tool-{uuid4().hex[:12]}",
            name=tool.name,
            description=tool.description or "",
            category=category,
            scope=scope,
            tenant_id=tenant_id,
            parameters_summary=params_summary,
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on tool_id."""
        if not isinstance(other, ToolIndexEntry):
            return NotImplemented
        return self.tool_id == other.tool_id

    def __hash__(self) -> int:
        """Hash based on tool_id for use in sets."""
        return hash(self.tool_id)


@dataclass
class SkillIndexEntry:
    """Indexed skill metadata for semantic search.

    Represents a skill in the semantic index with metadata for
    discovery, filtering, and progressive disclosure.

    Attributes:
        skill_id: Unique identifier for the skill
        name: Skill name
        description: Human-readable description for semantic matching
        category: Skill category for filtering
        embedding: Vector embedding for semantic search (optional)
        scope: CapabilityScope for hierarchical resolution
        tenant_id: Tenant ID for multi-tenant isolation
        skill_file_path: Path to SKILL.md file
        summary: Short summary for progressive disclosure (~100 tokens)
        token_estimate: Estimated tokens for full skill instructions
        tools_needed: List of tools this skill uses
    """

    skill_id: str
    name: str
    description: str
    category: str
    embedding: list[float] | None = None
    scope: CapabilityScope = CapabilityScope.PROJECT
    tenant_id: str | None = None
    skill_file_path: str | None = None
    summary: str | None = None
    token_estimate: int = 0
    tools_needed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Qdrant payload.

        Returns:
            Dictionary representation without embedding (stored separately)
        """
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "scope": str(self.scope.value),
            "tenant_id": self.tenant_id,
            "skill_file_path": self.skill_file_path,
            "summary": self.summary,
            "token_estimate": self.token_estimate,
            "tools_needed": self.tools_needed,
        }

    def to_summary(self) -> str:
        """Generate compact summary for progressive disclosure.

        Returns:
            Compact string representation (~100 tokens)
        """
        summary_text = self.summary or self.description[:100]
        return f"{self.name}: {summary_text}"

    def __eq__(self, other: object) -> bool:
        """Check equality based on skill_id."""
        if not isinstance(other, SkillIndexEntry):
            return NotImplemented
        return self.skill_id == other.skill_id

    def __hash__(self) -> int:
        """Hash based on skill_id for use in sets."""
        return hash(self.skill_id)


@dataclass
class MemoryIndexEntry:
    """Indexed memory entry for semantic search.

    Represents a memory (preference, context, fact) in the semantic index
    for personalized context retrieval.

    Attributes:
        memory_id: Unique identifier for the memory
        content: Memory content text
        memory_type: Type of memory (preference, context, fact, etc.)
        embedding: Vector embedding for semantic search (optional)
        scope: CapabilityScope for resolution
        session_id: Associated session ID
        user_id: Associated user ID
        tenant_id: Tenant ID for multi-tenant isolation
        timestamp: Unix timestamp when memory was created
        importance_score: Relevance score (0.0-1.0)
    """

    memory_id: str
    content: str
    memory_type: str | MemoryType
    embedding: list[float] | None = None
    scope: CapabilityScope = CapabilityScope.SESSION
    session_id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    timestamp: int | None = None
    importance_score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Qdrant payload.

        Returns:
            Dictionary representation without embedding (stored separately)
        """
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": str(self.memory_type),
            "scope": str(self.scope.value),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp,
            "importance_score": self.importance_score,
        }

    def __eq__(self, other: object) -> bool:
        """Check equality based on memory_id."""
        if not isinstance(other, MemoryIndexEntry):
            return NotImplemented
        return self.memory_id == other.memory_id

    def __hash__(self) -> int:
        """Hash based on memory_id for use in sets."""
        return hash(self.memory_id)


__all__ = [
    "MemoryIndexEntry",
    "MemoryType",
    "SkillCategory",
    "SkillIndexEntry",
    "ToolCategory",
    "ToolIndexEntry",
]
