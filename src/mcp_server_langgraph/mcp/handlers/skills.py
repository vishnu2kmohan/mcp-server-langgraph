"""
Skills MCP Tool Handler

Handles skills/list, skills/get, skills/search, skills/execute operations.

Provides MCP interface to the skills system for agent capabilities.

Semantic Search (ADR-0092/ADR-0099):
When enable_semantic_skill_search=True and SkillSearchTool is available,
skill search uses vector-based semantic similarity instead of string matching.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.skills import Skill, SkillDiscovery, SkillExecutor, SkillRegistry

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.search import SkillSearchTool

logger = logging.getLogger(__name__)


class SkillsToolHandler(AbstractToolHandler):
    """Handler for skills-related MCP operations.

    Provides:
    - skills/list: List available skills (progressive disclosure)
    - skills/get: Get full skill details
    - skills/search: Search skills by query
    - skills/execute: Execute a skill (feature-gated)
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
        skill_registry: SkillRegistry | None = None,
        skill_discovery: SkillDiscovery | None = None,
        skill_executor: SkillExecutor | None = None,
        skill_search_tool: SkillSearchTool | None = None,
    ) -> None:
        """Initialize skills handler.

        Args:
            auth: Authentication middleware
            agent_graph: LangGraph agent instance
            skill_registry: Optional skill registry (creates default if None)
            skill_discovery: Optional skill discovery (creates default if None)
            skill_executor: Optional skill executor (creates default if None)
            skill_search_tool: Optional semantic search tool for vector-based search
        """
        super().__init__(auth, agent_graph)
        self.skill_registry = skill_registry or SkillRegistry()
        self.skill_discovery = skill_discovery or SkillDiscovery(registry=self.skill_registry)
        self.skill_executor = skill_executor or SkillExecutor()
        self.skill_search_tool = skill_search_tool
        self._test_skills: dict[str, Skill] = {}

    def register_skill_for_test(
        self,
        name: str,
        description: str,
        category: str = "general",
        instructions: str = "",
        **kwargs: Any,
    ) -> None:
        """Register a skill for testing purposes.

        Args:
            name: Skill name
            description: Skill description
            category: Skill category
            instructions: Skill instructions
            **kwargs: Additional skill fields
        """
        skill = Skill(
            name=name,
            description=description,
            instructions=instructions or f"Instructions for {name}",
            **kwargs,
        )
        self.skill_registry.register(skill)
        self._test_skills[name] = skill

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Route to appropriate handler based on operation.

        This is called for the main "skills" tool - suboperations
        are handled by specific methods.
        """
        operation = arguments.get("operation", "list")

        if operation == "list":
            return await self.handle_list_skills(arguments, span, user_id)
        elif operation == "get":
            return await self.handle_get_skill(arguments, span, user_id)
        elif operation == "search":
            return await self.handle_search_skills(arguments, span, user_id)
        elif operation == "execute":
            return await self.handle_execute_skill(arguments, span, user_id)
        else:
            return [TextContent(type="text", text=f"Unknown operation: {operation}")]

    async def handle_list_skills(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """List available skills with progressive disclosure.

        Args:
            arguments: May contain 'category' filter
            span: Tracing span
            user_id: User ID

        Returns:
            List of skill summaries (not full details)
        """
        category = arguments.get("category")

        # Use discovery for progressive disclosure (summaries only)
        summaries = self.skill_discovery.get_skill_summaries()

        # Filter by category if specified
        if category:
            summaries = [s for s in summaries if s.get("category") == category]

        return [
            TextContent(
                type="text",
                text=json.dumps({"skills": summaries}, indent=2),
            )
        ]

    async def handle_get_skill(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Get full details for a specific skill.

        Args:
            arguments: Must contain 'name'
            span: Tracing span
            user_id: User ID

        Returns:
            Full skill details including instructions
        """
        name = arguments.get("name", "")

        skill = self.skill_discovery.get_skill(name)
        if skill is None:
            return [
                TextContent(
                    type="text",
                    text=f"Skill not found: {name}",
                )
            ]

        # Return full details including instructions
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "version": skill.version,
                        "instructions": skill.instructions,
                        "tags": skill.tags,
                        "required_secrets": skill.required_secrets,
                    },
                    indent=2,
                ),
            )
        ]

    async def handle_search_skills(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Search skills by query.

        Uses semantic vector search when enable_semantic_skill_search=True
        and SkillSearchTool is available, otherwise falls back to string matching.

        Args:
            arguments: Must contain 'query', optional 'limit' and 'min_score'
            span: Tracing span
            user_id: User ID

        Returns:
            List of matching skill summaries
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        min_score = arguments.get("min_score", 0.0)

        summaries = []

        # Try semantic search if enabled and available
        if feature_flags.enable_semantic_skill_search and self.skill_search_tool is not None:
            try:
                semantic_results = await self.skill_search_tool.search(
                    query,
                    limit=limit,
                    min_score=min_score,
                )
                summaries = [
                    {
                        "name": r.name,
                        "description": r.description,
                        "tags": r.tags or [],
                        "score": r.score,
                    }
                    for r in semantic_results
                ]
                logger.debug(
                    "Semantic skill search completed",
                    extra={"query": query, "results": len(summaries)},
                )
            except Exception as e:
                # Fall back to string search on error
                logger.warning(
                    f"Semantic skill search failed, falling back to string search: {e}",
                    extra={"query": query, "error": str(e)},
                )
                summaries = []

        # Fall back to string-based search if semantic search not used or failed
        if not summaries:
            results = self.skill_discovery.search(query)
            summaries = [
                {
                    "name": s.name if isinstance(s, Skill) else s.get("name", ""),
                    "description": s.description if isinstance(s, Skill) else s.get("description", ""),
                    "tags": s.tags if isinstance(s, Skill) else s.get("tags", []),
                }
                for s in results
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps({"results": summaries, "count": len(summaries)}, indent=2),
            )
        ]

    async def handle_execute_skill(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Execute a skill.

        Args:
            arguments: Must contain 'name', optional 'args'
            span: Tracing span
            user_id: User ID

        Returns:
            Execution result
        """
        # Check feature flag
        if not feature_flags.enable_skills_system:
            return [
                TextContent(
                    type="text",
                    text="Skills system is disabled. Enable with FF_ENABLE_SKILLS_SYSTEM=true",
                )
            ]

        name = arguments.get("name", "")
        # Note: skill_args will be used when sandbox execution is implemented
        # skill_args = arguments.get("args", {})

        skill = self.skill_registry.get(name)
        if skill is None:
            return [
                TextContent(
                    type="text",
                    text=f"Skill not found: {name}",
                )
            ]

        # Validate secrets if required
        available_secrets = arguments.get("secrets", {})
        validation = self.skill_executor.validate_secrets(skill, available_secrets)
        if not validation.is_valid:
            return [
                TextContent(
                    type="text",
                    text=f"Missing required secrets: {', '.join(validation.missing_secrets)}",
                )
            ]

        # Execute skill (placeholder - actual execution would use sandbox)
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "skill": name,
                        "status": "executed",
                        "message": f"Skill '{name}' executed successfully",
                    },
                    indent=2,
                ),
            )
        ]
