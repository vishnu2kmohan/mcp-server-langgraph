"""ProgressiveSkillLoader for 4-stage skill loading.

Provides progressive skill loading with semantic relevance:
- Stage 1: Explicitly requested skills from router
- Stage 2: Default skills for the scope (tagged with 'default')
- Stage 3: Limit to max_skills with priority ordering
- Stage 4: On-demand loading via semantic search (future)

This implements the progressive disclosure pattern from ADR-0092,
optimizing token usage by loading only relevant skills.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.skills.models import Skill

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
    from mcp_server_langgraph.skills.search import SkillSearchTool


@dataclass
class LoadedSkills:
    """Result of progressive skill loading.

    Attributes:
        skills: List of loaded Skill objects
        stages_used: List of stage names that contributed skills
    """

    skills: list[Skill] = field(default_factory=list)
    stages_used: list[str] = field(default_factory=list)


class ProgressiveSkillLoader:
    """Loads skills progressively based on task relevance.

    Implements a 4-stage loading strategy:
    1. Explicitly requested skills (highest priority)
    2. Default scope skills (tagged with 'default')
    3. Semantically similar skills (future - requires vector search)
    4. On-demand loading via SkillSearchTool (future)

    Attributes:
        skill_registry: HierarchicalSkillRegistry for skill lookup
    """

    DEFAULT_MAX_SKILLS = 10
    DEFAULT_SEMANTIC_MIN_SCORE = 0.5

    def __init__(
        self,
        skill_registry: HierarchicalSkillRegistry | None = None,
        skill_search_tool: SkillSearchTool | None = None,
    ) -> None:
        """Initialize the ProgressiveSkillLoader.

        Args:
            skill_registry: Optional HierarchicalSkillRegistry for skill lookup
            skill_search_tool: Optional SkillSearchTool for semantic search (stages 3/4)
        """
        self._skill_registry = skill_registry
        self._skill_search_tool = skill_search_tool

    @property
    def skill_registry(self) -> HierarchicalSkillRegistry | None:
        """Get the skill registry."""
        return self._skill_registry

    @property
    def skill_search_tool(self) -> SkillSearchTool | None:
        """Get the skill search tool for semantic discovery."""
        return self._skill_search_tool

    async def load_for_task(
        self,
        task_description: str,
        scope: CapabilityScope,
        requested_skills: list[str] | None = None,
        include_defaults: bool = False,
        max_skills: int | None = None,
        enable_semantic: bool = False,
        semantic_min_score: float | None = None,
    ) -> list[Skill]:
        """Load skills progressively for a task.

        Implements 4-stage progressive loading:
        1. Load explicitly requested skills
        2. Load default skills for the scope
        3. Semantic search to fill remaining slots (when enabled)
        4. On-demand loading via semantic search (tracked in detailed mode)

        Args:
            task_description: Description of the task for relevance
            scope: CapabilityScope for skill resolution
            requested_skills: List of explicitly requested skill names
            include_defaults: Whether to include default scope skills
            max_skills: Maximum number of skills to return
            enable_semantic: Enable semantic search for stages 3/4
            semantic_min_score: Minimum score for semantic search results

        Returns:
            List of SkillSpec objects, ordered by priority
        """
        if self._skill_registry is None:
            return []

        loaded: list[Skill] = []
        seen_names: set[str] = set()
        max_count = max_skills if max_skills is not None else self.DEFAULT_MAX_SKILLS

        # Stage 1: Load explicitly requested skills (highest priority)
        if requested_skills:
            for skill_name in requested_skills:
                if len(loaded) >= max_count:
                    break
                if skill_name in seen_names:
                    continue

                skill = self._skill_registry.get_for_scope(skill_name, scope)
                if skill is not None:
                    loaded.append(skill)
                    seen_names.add(skill_name)

        # Stage 2: Load default skills (if requested)
        if include_defaults and len(loaded) < max_count:
            all_skills = self._skill_registry.list_for_scope(scope, include_parent_scopes=True)
            for skill in all_skills:
                if len(loaded) >= max_count:
                    break
                if skill.name in seen_names:
                    continue

                # Check if skill has 'default' tag
                if skill.tags and "default" in skill.tags:
                    loaded.append(skill)
                    seen_names.add(skill.name)

        # Stage 3: Semantic search to fill remaining slots
        if enable_semantic and self._skill_search_tool and len(loaded) < max_count:
            min_score = semantic_min_score if semantic_min_score is not None else self.DEFAULT_SEMANTIC_MIN_SCORE
            remaining_slots = max_count - len(loaded)

            search_results = await self._skill_search_tool.search(
                query=task_description,
                limit=remaining_slots,
                min_score=min_score,
            )

            for result in search_results:
                if len(loaded) >= max_count:
                    break
                if result.name in seen_names:
                    continue

                # Try to resolve the skill from registry
                skill = self._skill_registry.get_for_scope(result.name, scope)
                if skill is not None:
                    loaded.append(skill)
                    seen_names.add(result.name)

        return loaded

    async def load_for_task_detailed(
        self,
        task_description: str,
        scope: CapabilityScope,
        requested_skills: list[str] | None = None,
        include_defaults: bool = False,
        max_skills: int | None = None,
        enable_semantic: bool = False,
        semantic_min_score: float | None = None,
    ) -> LoadedSkills:
        """Load skills progressively with detailed stage tracking.

        Same as load_for_task but returns LoadedSkills with stage info.

        Args:
            task_description: Description of the task
            scope: CapabilityScope for skill resolution
            requested_skills: List of requested skill names
            include_defaults: Whether to include defaults
            max_skills: Maximum skills to return
            enable_semantic: Enable semantic search for stages 3/4
            semantic_min_score: Minimum score for semantic search results

        Returns:
            LoadedSkills with skills and stages used
        """
        if self._skill_registry is None:
            return LoadedSkills(skills=[], stages_used=[])

        loaded: list[Skill] = []
        seen_names: set[str] = set()
        stages_used: list[str] = []
        max_count = max_skills if max_skills is not None else self.DEFAULT_MAX_SKILLS

        # Stage 1: Load explicitly requested skills
        stage1_loaded = False
        if requested_skills:
            for skill_name in requested_skills:
                if len(loaded) >= max_count:
                    break
                if skill_name in seen_names:
                    continue

                skill = self._skill_registry.get_for_scope(skill_name, scope)
                if skill is not None:
                    loaded.append(skill)
                    seen_names.add(skill_name)
                    stage1_loaded = True

        if stage1_loaded:
            stages_used.append("stage1")

        # Stage 2: Load default skills
        stage2_loaded = False
        if include_defaults and len(loaded) < max_count:
            all_skills = self._skill_registry.list_for_scope(scope, include_parent_scopes=True)
            for skill in all_skills:
                if len(loaded) >= max_count:
                    break
                if skill.name in seen_names:
                    continue

                if skill.tags and "default" in skill.tags:
                    loaded.append(skill)
                    seen_names.add(skill.name)
                    stage2_loaded = True

        if stage2_loaded:
            stages_used.append("stage2")

        # Stage 3: Semantic search to fill remaining slots
        stage3_loaded = False
        if enable_semantic and self._skill_search_tool and len(loaded) < max_count:
            min_score = semantic_min_score if semantic_min_score is not None else self.DEFAULT_SEMANTIC_MIN_SCORE
            remaining_slots = max_count - len(loaded)

            search_results = await self._skill_search_tool.search(
                query=task_description,
                limit=remaining_slots,
                min_score=min_score,
            )

            for result in search_results:
                if len(loaded) >= max_count:
                    break
                if result.name in seen_names:
                    continue

                # Try to resolve the skill from registry
                skill = self._skill_registry.get_for_scope(result.name, scope)
                if skill is not None:
                    loaded.append(skill)
                    seen_names.add(result.name)
                    stage3_loaded = True

        if stage3_loaded:
            stages_used.append("stage3")

        return LoadedSkills(skills=loaded, stages_used=stages_used)
