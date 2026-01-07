"""
Worker Agent Implementation

Concrete BaseAgent implementation that uses LLMFactory for LLM invocation
and ThinkingBudgetManager for extended thinking support.

ADR-0092: Supports capability provider injection for hierarchical tool/skill
resolution. When a capability_provider is set, tools are resolved from the
request and bound to the LLM invocation.

Usage:
    from mcp_server_langgraph.agents.worker_agent import WorkerAgent
    from mcp_server_langgraph.llm.factory import get_llm_factory

    agent = WorkerAgent(llm_factory=get_llm_factory())
    request = AgentRequest(message="Hello, how are you?")
    result = await agent.run(request)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.agents.base_agent import (
    AgentRequest,
    AgentResult,
    BaseAgent,
)
from mcp_server_langgraph.capabilities.provider import (
    CapabilityProvider,
    ResolvedCapabilities,
    SkillSpec,
    ToolSpec,
)
from mcp_server_langgraph.core.scopes import CapabilityScope

if TYPE_CHECKING:
    from mcp_server_langgraph.agents.thinking_budget import ThinkingBudgetManager


class WorkerAgent(BaseAgent):
    """Worker agent that uses LLMFactory for LLM calls.

    This is the primary agent implementation for executing individual
    LLM invocations within orchestration patterns.

    ADR-0092: Supports hierarchical capability resolution when a
    capability_provider is injected. Tools and skills are resolved
    based on the request's scope and merge strategy.

    Attributes:
        llm_factory: Factory for creating LLM completions
        thinking_budget_manager: Optional manager for thinking budget mapping
        model_id: Optional model ID override (uses factory default if None)
        capability_provider: Optional provider for tool/skill resolution
    """

    def __init__(
        self,
        llm_factory: Any,
        thinking_budget_manager: ThinkingBudgetManager | None = None,
        model_id: str | None = None,
        capability_provider: CapabilityProvider | None = None,
    ) -> None:
        """Initialize WorkerAgent.

        Args:
            llm_factory: LLMFactory instance for creating completions
            thinking_budget_manager: Optional ThinkingBudgetManager for
                mapping thinking budget levels to provider params
            model_id: Optional model ID override. If not provided,
                uses the factory's default model.
            capability_provider: Optional CapabilityProvider for resolving
                tools and skills from hierarchical scope. If not provided,
                tool binding is disabled (legacy mode).
        """
        self.llm_factory = llm_factory
        self.thinking_budget_manager = thinking_budget_manager
        self.model_id = model_id
        self.capability_provider = capability_provider

    async def run(
        self,
        request: AgentRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentResult:
        """Execute agent with cancellation support.

        Args:
            request: The AgentRequest with message and configuration
            cancel_event: Optional asyncio.Event for cancellation

        Returns:
            AgentResult with content, success status, and model info
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Check for cancellation before starting
        if cancel_event and cancel_event.is_set():
            return AgentResult(
                content="",
                success=False,
                error="Cancelled before execution",
            )

        try:
            # Resolve capabilities if provider is set (ADR-0092)
            resolved_capabilities = None
            if self.capability_provider is not None:
                resolved_capabilities = await self._resolve_capabilities(request)

            # Build LangChain messages
            langchain_messages: list[SystemMessage | HumanMessage] = []

            # Inject memory context as SystemMessage if available
            if resolved_capabilities and resolved_capabilities.memory:
                memory = resolved_capabilities.memory
                memory_parts = []

                # Add relevant memories
                if memory.relevant_memories:
                    for mem in memory.relevant_memories:
                        memory_parts.append(str(mem))

                # Add working memory summary
                if memory.working_memory:
                    for key, value in memory.working_memory.items():
                        memory_parts.append(f"{key}: {value}")

                if memory_parts:
                    memory_content = "\n".join(memory_parts)
                    langchain_messages.append(SystemMessage(content=f"Context from memory:\n{memory_content}"))

            # Add user message
            langchain_messages.append(HumanMessage(content=request.message))

            # Build kwargs for ainvoke
            kwargs: dict[str, Any] = {}

            # Add resolved tools if available
            if resolved_capabilities and resolved_capabilities.tools:
                # Convert ToolSpec to LangChain tools
                langchain_tools = []
                for tool_spec in resolved_capabilities.tools:
                    if tool_spec.callable is not None:
                        # Create a structured tool from callable
                        from langchain_core.tools import StructuredTool

                        langchain_tool = StructuredTool.from_function(
                            func=tool_spec.callable,
                            name=tool_spec.name,
                            description=tool_spec.description,
                        )
                        langchain_tools.append(langchain_tool)

                if langchain_tools:
                    kwargs["tools"] = langchain_tools

            # Add model override if specified
            if self.model_id:
                kwargs["model"] = self.model_id

            # Add max tokens if specified
            if request.max_tokens:
                kwargs["max_tokens"] = request.max_tokens

            # Handle thinking budget if manager available and budget requested
            thinking_content = None
            thinking_tokens = 0
            if self.thinking_budget_manager and request.thinking_budget != "none" and self.model_id is not None:
                # Map thinking budget to provider-specific params
                # Convert string level to ThinkingLevel enum
                thinking_level = self.thinking_budget_manager.level_from_string(request.thinking_budget)
                thinking_params = self.thinking_budget_manager.get_params(
                    model=self.model_id,
                    level=thinking_level,
                )
                kwargs.update(thinking_params)

            # Execute LLM call with timeout using ainvoke (returns AIMessage)
            response = await asyncio.wait_for(
                self.llm_factory.ainvoke(langchain_messages, **kwargs),
                timeout=request.timeout_seconds,
            )

            # Extract response content from AIMessage
            content = response.content or ""

            # Extract model info from response metadata if available
            model_used = self.model_id or ""
            if hasattr(response, "response_metadata") and response.response_metadata:
                model_used = response.response_metadata.get("model", model_used)

            # Extract thinking content if available (from additional_kwargs or response_metadata)
            if hasattr(response, "additional_kwargs") and response.additional_kwargs:
                thinking_content = response.additional_kwargs.get("thinking")
                thinking_tokens = response.additional_kwargs.get("thinking_tokens", 0)

            return AgentResult(
                content=content,
                success=True,
                model_used=model_used,
                thinking_content=thinking_content,
                thinking_tokens=thinking_tokens,
            )

        except TimeoutError:
            return AgentResult(
                content="",
                success=False,
                error=f"Timeout after {request.timeout_seconds} seconds",
            )
        except asyncio.CancelledError:
            return AgentResult(
                content="",
                success=False,
                error="Cancelled during execution",
            )
        except Exception as e:
            return AgentResult(
                content="",
                success=False,
                error=str(e),
                model_used=self.model_id or "",
            )

    async def _resolve_tools(self, request: AgentRequest) -> list[ToolSpec]:
        """Resolve tools from request using capability provider.

        Applies merge strategy to combine router-selected tools with
        user-selected tools.

        Args:
            request: AgentRequest containing tool selections and merge strategy

        Returns:
            List of resolved ToolSpec objects
        """
        if self.capability_provider is None:
            return []

        # Determine the scope to use (default to TASK if not specified)
        scope = request.scope if request.scope is not None else CapabilityScope.TASK

        # Determine which tool names to request based on merge strategy
        router_tools = set(request.tools or [])
        user_tools = set(request.user_tool_selection or [])

        if request.merge_strategy == "user_only":
            tool_names = list(user_tools) if user_tools else []
        elif request.merge_strategy == "router_only":
            tool_names = list(router_tools) if router_tools else []
        elif request.merge_strategy == "intersection":
            tool_names = list(router_tools & user_tools) if router_tools and user_tools else []
        else:  # "union" (default)
            tool_names = list(router_tools | user_tools)

        if not tool_names:
            return []

        # Get tools from capability provider
        return await self.capability_provider.get_tools(scope, tool_names)

    async def _resolve_capabilities(self, request: AgentRequest) -> ResolvedCapabilities:
        """Resolve all capabilities (tools, skills, memory) from request.

        Args:
            request: AgentRequest with capability specifications

        Returns:
            ResolvedCapabilities with resolved tools, skills, and memory
        """
        if self.capability_provider is None:
            return ResolvedCapabilities(
                tools=[],
                skills=[],
                memory=None,
                scope=request.scope,
            )

        # Determine the scope to use
        scope = request.scope if request.scope is not None else CapabilityScope.TASK

        # Resolve tools with merge strategy
        tools = await self._resolve_tools(request)

        # Resolve skills similarly
        router_skills = set(request.skills or [])
        user_skills = set(request.user_skill_selection or [])

        if request.merge_strategy == "user_only":
            skill_names = list(user_skills) if user_skills else []
        elif request.merge_strategy == "router_only":
            skill_names = list(router_skills) if router_skills else []
        elif request.merge_strategy == "intersection":
            skill_names = list(router_skills & user_skills) if router_skills and user_skills else []
        else:  # "union" (default)
            skill_names = list(router_skills | user_skills)

        skills: list[SkillSpec] = []
        if skill_names:
            skills = await self.capability_provider.get_skills(scope, skill_names)

        # Get memory context
        memory = await self.capability_provider.get_memory(scope, request.message)

        return ResolvedCapabilities(
            tools=tools,
            skills=skills,
            memory=memory,
            scope=scope,
        )
