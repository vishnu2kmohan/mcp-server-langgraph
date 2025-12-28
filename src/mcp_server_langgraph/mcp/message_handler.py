"""
MCP Message Handler.

Provides the core MCP protocol message handling logic including:
- JSON-RPC 2.0 message routing
- MCP 2025-11-25 method handlers (initialize, tools/*, resources/*, prompts/*)
- Streaming and trace notification creation

This module is the canonical location for MCPMessageHandler and AuthenticatedMCPHandler.
For backward compatibility, these classes are re-exported from api.v1.mcp_websocket.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    pass

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

logger = logging.getLogger(__name__)


class MCPMessageHandler:
    """
    Handler for MCP protocol messages over WebSocket.

    Supports all MCP 2025-11-25 methods including:
    - initialize: Protocol handshake
    - tools/list, tools/call: Tool operations
    - resources/list, resources/read: Resource operations
    - prompts/list, prompts/get: Prompt operations
    - elicitation/*, sampling/*: Advanced features
    """

    def __init__(self) -> None:
        """Initialize the message handler."""
        self.protocol_version = "2025-11-25"
        self.server_info = {
            "name": "langgraph-agent",
            "version": "2.8.0",
            "description": "AI Agent with fine-grained authorization, LangGraph workflows, and multi-LLM support",
        }
        self.capabilities = {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False, "subscribe": True},
            "prompts": {"listChanged": False},
            "elicitation": {},
            "sampling": {},
            "logging": {},
            "streaming": {
                "supported": True,
                "textStreaming": True,
                "progressiveRendering": True,
                "chunkedResponses": True,
            },
        }

        # Standard tools available
        self._tools = [
            {
                "name": "langgraph-run",
                "description": "Execute the LangGraph agent with a query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to process",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional session ID for context",
                        },
                    },
                    "required": ["query"],
                },
            }
        ]

        # Standard prompts available
        self._prompts = [
            {
                "name": "code_review",
                "description": "Review code for issues and improvements",
                "arguments": [
                    {"name": "code", "required": True, "description": "Code to review"},
                    {"name": "language", "required": False, "description": "Programming language"},
                ],
            },
            {
                "name": "summarize_conversation",
                "description": "Summarize the current conversation",
                "arguments": [],
            },
            {
                "name": "debug_error",
                "description": "Help debug an error",
                "arguments": [
                    {"name": "error", "required": True, "description": "Error message"},
                    {"name": "context", "required": False, "description": "Additional context"},
                ],
            },
        ]

        # Standard resources available
        self._resources = [
            {
                "uri": "config://studio/default",
                "name": "Default Configuration",
                "mimeType": "application/json",
                "description": "Default studio configuration",
            }
        ]

    def handle_sync(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message synchronously.

        Used for simple methods that don't require async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params", {})

        # Handle methods
        if method == "initialize":
            return self._handle_initialize(message_id, params)
        else:
            # Unknown method
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    async def handle(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP message asynchronously.

        Supports all MCP methods including async operations.
        """
        # Validate JSON-RPC 2.0 structure
        if "method" not in message:
            return self._error_response(message.get("id"), INVALID_REQUEST, "Missing method field")

        method = str(message.get("method"))
        message_id = message.get("id")
        params = message.get("params", {})

        # Route to appropriate handler - sync handlers
        sync_handlers: dict[str, Callable[[Any, Any], dict[str, Any]]] = {
            "initialize": self._handle_initialize,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }

        # Async handlers
        if method == "tools/call":
            return await self._handle_tools_call(message_id, params)
        if method == "tools/list":
            return await self._handle_tools_list_async(message_id, params)

        # MCP 2025-11-25 Optional/Advanced Feature handlers
        if method == "sampling/createMessage":
            return await self._handle_sampling_create_message(message_id, params)
        if method == "elicitation/create":
            return await self._handle_elicitation_create(message_id, params)
        if method == "tasks/list":
            return await self._handle_tasks_list(message_id, params)
        if method == "tasks/get":
            return await self._handle_tasks_get(message_id, params)
        if method == "tasks/cancel":
            return await self._handle_tasks_cancel(message_id, params)
        if method == "tasks/result":
            return await self._handle_tasks_result(message_id, params)
        if method == "completion/complete":
            return await self._handle_completion_complete(message_id, params)
        if method == "logging/setLevel":
            return self._handle_logging_set_level(message_id, params)
        if method == "roots/list":
            return self._handle_roots_list(message_id, params)

        sync_handler = sync_handlers.get(method)
        if sync_handler:
            return sync_handler(message_id, params)
        else:
            return self._error_response(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def handle_parse_error(self) -> dict[str, Any]:
        """Return a parse error response for invalid JSON."""
        return self._error_response(None, PARSE_ERROR, "Parse error")

    def _error_response(self, message_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 error response."""
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": message_id, "error": error}

    def _success_response(self, message_id: Any, result: Any) -> dict[str, Any]:
        """Create a JSON-RPC 2.0 success response."""
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _handle_initialize(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return self._success_response(
            message_id,
            {
                "protocolVersion": self.protocol_version,
                "serverInfo": self.server_info,
                "capabilities": self.capabilities,
            },
        )

    async def _handle_tools_list_async(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/list request with built-in tools plus aggregated tools from external MCP servers."""
        tools: list[dict[str, Any]] = []

        # Get built-in tools from MCP server
        try:
            from mcp_server_langgraph.mcp.server_streamable import get_mcp_server

            mcp_server = get_mcp_server()
            builtin_tools = await mcp_server.list_tools_public()

            # Convert Tool objects to dict format expected by MCP protocol
            for tool in builtin_tools:
                tool_dict = tool.model_dump(mode="json")
                tools.append(
                    {
                        "name": tool_dict.get("name", ""),
                        "description": tool_dict.get("description") or "",
                        "inputSchema": tool_dict.get("inputSchema") or {},
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to get built-in tools, using static list: {e}")
            tools = list(self._tools)

        # Add aggregated tools from external MCP servers
        try:
            from mcp_server_langgraph.mcp.client.unified_registry import get_unified_registry

            registry = get_unified_registry()
            for tool in registry.get_tools():
                tools.append(
                    {
                        "name": tool.qualified_name,  # Use qualified name for disambiguation
                        "description": f"[{tool.server_name}] {tool.description}",
                        "inputSchema": tool.input_schema,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to get aggregated tools: {e}")

        return self._success_response(message_id, {"tools": tools})

    def _handle_tools_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/list request (sync fallback)."""
        return self._success_response(message_id, {"tools": self._tools})

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        try:
            result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool and return results.

        This is a placeholder that should be overridden or mocked in tests.
        In production, this integrates with the actual tool execution system.
        """
        # Default implementation returns a placeholder
        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    def _handle_resources_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/list request.

        Returns built-in resources plus aggregated resources from external MCP servers.
        """
        # Start with built-in resources
        all_resources = list(self._resources)

        # Add resources from external MCP servers via unified registry
        try:
            from mcp_server_langgraph.mcp.client.unified_registry import get_unified_registry

            registry = get_unified_registry()
            for resource in registry.get_resources():
                all_resources.append(
                    {
                        "uri": resource.qualified_name,  # Use qualified name as URI
                        "name": f"{resource.server_name}: {resource.name}",
                        "mimeType": resource.mime_type or "application/json",
                        "description": resource.description or f"Resource from {resource.server_name}",
                    }
                )
        except Exception as e:
            logger.warning("Failed to get aggregated resources: %s", e)

        return self._success_response(message_id, {"resources": all_resources})

    def _handle_resources_read(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        # Return placeholder content
        content = {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps({"config": "placeholder", "uri": uri}),
        }
        return self._success_response(message_id, {"contents": [content]})

    def _handle_prompts_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/list request.

        Returns built-in prompts plus aggregated prompts from external MCP servers.
        """
        # Start with built-in prompts
        all_prompts = list(self._prompts)

        # Add prompts from external MCP servers via unified registry
        try:
            from mcp_server_langgraph.mcp.client.unified_registry import get_unified_registry

            registry = get_unified_registry()
            for prompt in registry.get_prompts():
                all_prompts.append(
                    {
                        "name": prompt.qualified_name,  # Use qualified name
                        "description": prompt.description or f"Prompt from {prompt.server_name}",
                        "arguments": prompt.arguments,
                    }
                )
        except Exception as e:
            logger.warning("Failed to get aggregated prompts: %s", e)

        return self._success_response(message_id, {"prompts": all_prompts})

    def _handle_prompts_get(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        # Generate prompt messages based on name
        if prompt_name == "code_review":
            code = arguments.get("code", "")
            language = arguments.get("language", "unknown")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please review the following {language} code:\n\n```{language}\n{code}\n```",
                    },
                }
            ]
        elif prompt_name == "summarize_conversation":
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Please summarize the current conversation, highlighting key points and decisions.",
                    },
                }
            ]
        elif prompt_name == "debug_error":
            error = arguments.get("error", "")
            context = arguments.get("context", "")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please help debug this error:\n\nError: {error}\n\nContext: {context}",
                    },
                }
            ]
        else:
            return self._error_response(message_id, INVALID_PARAMS, f"Unknown prompt: {prompt_name}")

        return self._success_response(message_id, {"messages": messages})

    # =========================================================================
    # MCP 2025-11-25 Optional/Advanced Features
    # =========================================================================

    async def _handle_sampling_create_message(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle sampling/createMessage request.

        Creates a message using the LiteLLM Router for LLM sampling.
        Supports modelPreferences for model selection hints.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/sampling
        """
        messages = params.get("messages", [])
        max_tokens = params.get("maxTokens", 1024)
        model_preferences = params.get("modelPreferences", {})
        stop_sequences = params.get("stopSequences", [])
        temperature = params.get("temperature")
        system_prompt = params.get("systemPrompt")

        if not messages:
            return self._error_response(message_id, INVALID_PARAMS, "messages is required")

        try:
            # Use LiteLLM for sampling
            from litellm import acompletion

            # Convert MCP message format to LiteLLM format
            llm_messages = []
            if system_prompt:
                llm_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
                llm_messages.append({"role": role, "content": text})

            # Extract model hints from preferences
            model = "gpt-4o-mini"  # Default model
            hints = model_preferences.get("hints", [])
            if hints:
                # Use first hint as model name if available
                first_hint = hints[0]
                if isinstance(first_hint, dict) and "name" in first_hint:
                    model = first_hint["name"]

            # Build completion kwargs
            completion_kwargs: dict[str, Any] = {
                "model": model,
                "messages": llm_messages,
                "max_tokens": max_tokens,
            }
            if stop_sequences:
                completion_kwargs["stop"] = stop_sequences
            if temperature is not None:
                completion_kwargs["temperature"] = temperature

            response = await acompletion(**completion_kwargs)

            # Extract response content
            content = response.choices[0].message.content or ""
            stop_reason = response.choices[0].finish_reason or "end_turn"

            # Map finish_reason to MCP stopReason
            stop_reason_map = {
                "stop": "endTurn",
                "length": "maxTokens",
                "content_filter": "endTurn",
            }
            mcp_stop_reason = stop_reason_map.get(stop_reason, "endTurn")

            return self._success_response(
                message_id,
                {
                    "role": "assistant",
                    "content": {"type": "text", "text": content},
                    "model": model,
                    "stopReason": mcp_stop_reason,
                },
            )

        except ImportError:
            return self._error_response(
                message_id,
                INTERNAL_ERROR,
                "LiteLLM not available for sampling",
            )
        except Exception as e:
            logger.exception(f"Sampling error: {e}")
            return self._error_response(
                message_id,
                INTERNAL_ERROR,
                f"Sampling failed: {e}",
            )

    async def _handle_elicitation_create(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle elicitation/create request.

        Elicitation allows the server to request structured input from the user.
        This implementation returns a placeholder since actual user interaction
        requires frontend integration.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation
        """
        message_text = params.get("message", "")
        requested_schema = params.get("requestedSchema", {})

        if not message_text:
            return self._error_response(message_id, INVALID_PARAMS, "message is required")

        # For now, return a "declined" action since we can't interact with user
        # In production, this would integrate with the frontend to show a form
        logger.info(
            f"Elicitation requested: {message_text}",
            extra={"schema": requested_schema},
        )

        return self._success_response(
            message_id,
            {
                "action": "decline",
                "content": None,
            },
        )

    async def _handle_tasks_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tasks/list request.

        Lists all active tasks from the Orchestrator and MCP task registry.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/tasks
        """
        try:
            from mcp_server_langgraph.agents.base_orchestrator import get_orchestrator_registry

            tasks = []
            registry = get_orchestrator_registry()

            # Collect tasks from all registered orchestrators
            for name, orchestrator in registry.items():
                if hasattr(orchestrator, "list_tasks"):
                    orch_tasks = await orchestrator.list_tasks()
                    for task in orch_tasks:
                        tasks.append(
                            {
                                "id": task.get("id", ""),
                                "name": task.get("name", name),
                                "status": task.get("status", "pending"),
                                "progress": task.get("progress"),
                            }
                        )

            return self._success_response(message_id, {"tasks": tasks})

        except ImportError:
            # Orchestrator not available, return empty list
            return self._success_response(message_id, {"tasks": []})
        except Exception as e:
            logger.warning(f"Failed to list tasks: {e}")
            return self._success_response(message_id, {"tasks": []})

    async def _handle_tasks_get(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tasks/get request.

        Gets details about a specific task by ID.
        """
        task_id = params.get("taskId")
        if not task_id:
            return self._error_response(message_id, INVALID_PARAMS, "taskId is required")

        try:
            from mcp_server_langgraph.agents.base_orchestrator import get_orchestrator_registry

            registry = get_orchestrator_registry()

            # Search for task in all orchestrators
            for orchestrator in registry.values():
                if hasattr(orchestrator, "get_task"):
                    task = await orchestrator.get_task(task_id)
                    if task:
                        return self._success_response(
                            message_id,
                            {
                                "id": task.get("id", task_id),
                                "name": task.get("name", ""),
                                "status": task.get("status", "pending"),
                                "progress": task.get("progress"),
                                "result": task.get("result"),
                            },
                        )

            return self._error_response(message_id, INVALID_PARAMS, f"Task not found: {task_id}")

        except ImportError:
            return self._error_response(message_id, INVALID_PARAMS, f"Task not found: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to get task {task_id}: {e}")
            return self._error_response(message_id, INTERNAL_ERROR, f"Failed to get task: {e}")

    async def _handle_tasks_cancel(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tasks/cancel request.

        Cancels a running task by ID.
        """
        task_id = params.get("taskId")
        if not task_id:
            return self._error_response(message_id, INVALID_PARAMS, "taskId is required")

        try:
            from mcp_server_langgraph.agents.base_orchestrator import get_orchestrator_registry

            registry = get_orchestrator_registry()

            # Try to cancel in all orchestrators
            for orchestrator in registry.values():
                if hasattr(orchestrator, "cancel_task"):
                    cancelled = await orchestrator.cancel_task(task_id)
                    if cancelled:
                        return self._success_response(message_id, {"cancelled": True})

            # Task not found or couldn't be cancelled
            return self._success_response(message_id, {"cancelled": False})

        except ImportError:
            return self._success_response(message_id, {"cancelled": False})
        except Exception as e:
            logger.warning(f"Failed to cancel task {task_id}: {e}")
            return self._success_response(message_id, {"cancelled": False})

    async def _handle_tasks_result(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tasks/result request.

        Gets the result of a completed task.
        """
        task_id = params.get("taskId")
        if not task_id:
            return self._error_response(message_id, INVALID_PARAMS, "taskId is required")

        try:
            from mcp_server_langgraph.agents.base_orchestrator import get_orchestrator_registry

            registry = get_orchestrator_registry()

            # Search for task result in all orchestrators
            for orchestrator in registry.values():
                if hasattr(orchestrator, "get_task_result"):
                    result = await orchestrator.get_task_result(task_id)
                    if result is not None:
                        return self._success_response(
                            message_id,
                            {
                                "taskId": task_id,
                                "result": result,
                            },
                        )

            return self._error_response(message_id, INVALID_PARAMS, f"Task result not found: {task_id}")

        except ImportError:
            return self._error_response(message_id, INVALID_PARAMS, f"Task result not found: {task_id}")
        except Exception as e:
            logger.warning(f"Failed to get task result {task_id}: {e}")
            return self._error_response(message_id, INTERNAL_ERROR, f"Failed to get task result: {e}")

    async def _handle_completion_complete(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle completion/complete request.

        Provides autocompletion for prompt arguments and resource URIs.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/completion
        """
        ref = params.get("ref", {})
        argument = params.get("argument", {})

        ref_type = ref.get("type", "")
        argument_name = argument.get("name", "")
        argument_value = argument.get("value", "")

        completions: list[str] = []
        total = 0

        if ref_type == "ref/prompt":
            prompt_name = ref.get("name", "")
            # Provide completions for known prompt arguments
            if prompt_name == "code_review" and argument_name == "language":
                languages = [
                    "python",
                    "javascript",
                    "typescript",
                    "go",
                    "rust",
                    "java",
                    "c",
                    "cpp",
                    "csharp",
                    "ruby",
                    "php",
                ]
                completions = [lang for lang in languages if lang.startswith(argument_value.lower())]
                total = len(completions)

        elif ref_type == "ref/resource":
            uri_value = argument.get("value", "")
            # Provide completions for resource URIs
            if uri_value.startswith("config://"):
                available_configs = [
                    "config://studio/default",
                    "config://studio/theme",
                    "config://agent/settings",
                ]
                completions = [cfg for cfg in available_configs if cfg.startswith(uri_value)]
                total = len(completions)

        return self._success_response(
            message_id,
            {
                "completion": {
                    "values": completions[:10],  # Limit to 10 results
                    "hasMore": len(completions) > 10,
                    "total": total,
                }
            },
        )

    def _handle_logging_set_level(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle logging/setLevel request.

        Dynamically adjusts the logging level for the MCP server.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging
        """
        level = params.get("level", "").lower()

        # MCP logging levels map to Python logging levels
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "notice": logging.INFO,  # Python doesn't have NOTICE
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "alert": logging.CRITICAL,  # Map to CRITICAL
            "emergency": logging.CRITICAL,  # Map to CRITICAL
        }

        if level not in level_map:
            return self._error_response(
                message_id,
                INVALID_PARAMS,
                f"Invalid log level: {level}. Valid levels: {list(level_map.keys())}",
            )

        # Set the logging level for MCP-related loggers
        python_level = level_map[level]
        logging.getLogger("mcp_server_langgraph").setLevel(python_level)
        logging.getLogger("mcp_server_langgraph.mcp").setLevel(python_level)

        logger.info(f"Logging level set to: {level}")

        return self._success_response(message_id, {})

    def _handle_roots_list(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle roots/list request.

        Returns filesystem roots that the server can access.
        Integrates with sandbox workspace mapping for secure execution.

        Reference: https://modelcontextprotocol.io/specification/2025-11-25/client/roots
        """
        import os

        roots = []

        # Try to get workspace from sandbox context
        try:
            from mcp_server_langgraph.execution.sandbox_context import get_sandbox_context

            context = get_sandbox_context()
            if context and hasattr(context, "_working_directory"):
                working_dir = context._working_directory
                if working_dir:
                    roots.append(
                        {
                            "uri": f"file://{working_dir}",
                            "name": "Workspace",
                        }
                    )
        except ImportError:
            pass

        # Add default workspace if no sandbox context
        if not roots:
            # Use current working directory or configurable workspace
            workspace = os.getenv("MCP_WORKSPACE_ROOT", os.getcwd())
            roots.append(
                {
                    "uri": f"file://{workspace}",
                    "name": "Workspace",
                }
            )

        # Add config root for configuration resources
        roots.append(
            {
                "uri": "config://",
                "name": "Configuration",
            }
        )

        return self._success_response(message_id, {"roots": roots})

    # =========================================================================
    # Streaming Extensions ($/streaming/*)
    # =========================================================================

    def create_streaming_start_notification(self, stream_id: str, tool_call_id: int) -> dict[str, Any]:
        """Create a $/streaming/start notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/start",
            "params": {
                "streamId": stream_id,
                "toolCallId": tool_call_id,
            },
        }

    def create_streaming_chunk_notification(self, stream_id: str, content: dict[str, Any]) -> dict[str, Any]:
        """Create a $/streaming/chunk notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/chunk",
            "params": {
                "streamId": stream_id,
                "content": content,
            },
        }

    def create_streaming_end_notification(self, stream_id: str) -> dict[str, Any]:
        """Create a $/streaming/end notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/streaming/end",
            "params": {
                "streamId": stream_id,
            },
        }

    # =========================================================================
    # Trace Extensions ($/trace/*)
    # =========================================================================

    def create_trace_span_notification(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        start_time: str,
        end_time: str,
        status: str,
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/span notification with OpenTelemetry-compatible data."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/span",
            "params": {
                "traceId": trace_id,
                "spanId": span_id,
                "parentSpanId": parent_span_id,
                "name": name,
                "startTime": start_time,
                "endTime": end_time,
                "status": status,
                "attributes": attributes or {},
            },
        }

    def create_trace_event_notification(
        self,
        span_id: str,
        name: str,
        timestamp: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a $/trace/event notification."""
        return {
            "jsonrpc": "2.0",
            "method": "$/trace/event",
            "params": {
                "spanId": span_id,
                "name": name,
                "timestamp": timestamp,
                "attributes": attributes or {},
            },
        }


class AuthenticatedMCPHandler(MCPMessageHandler):
    """
    MCP message handler with user authentication context.

    Extends MCPMessageHandler with:
    - User ID and roles tracking
    - Authenticated tool execution
    - User context propagation to agent
    """

    def __init__(
        self,
        user_id: str,
        roles: list[str] | None = None,
        notification_callback: Callable[[dict[str, Any]], Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Initialize the authenticated handler.

        Args:
            user_id: The authenticated user's ID.
            roles: The user's roles for authorization.
            notification_callback: Optional async callback for sending notifications.
            session_id: Optional session ID for connection tracking and idle timeout prevention.
        """
        super().__init__()
        self.user_id = user_id
        self.roles = roles or []
        self.notification_callback = notification_callback
        self.session_id = session_id

    async def _handle_tools_call(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle tools/call request with streaming support.

        Overrides base method to check for _meta.streaming parameter
        and use StreamingToolCallHandler when streaming is requested.
        """
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return self._error_response(message_id, INVALID_PARAMS, "Missing or invalid tool name")
        arguments = params.get("arguments", {})

        # Check for streaming request
        meta = params.get("_meta", {})
        is_streaming_requested = meta.get("streaming", False)

        # Use streaming handler if:
        # 1. Streaming is globally enabled
        # 2. Client requested streaming
        # 3. We have a notification callback
        if is_streaming_requested and self.notification_callback is not None:
            # Import here to avoid circular dependency
            try:
                # Import from mcp/websocket package (fully migrated)
                from mcp_server_langgraph.mcp.websocket.streaming import (
                    StreamingToolCallHandler,
                    streaming_metrics_collector,
                )
                from mcp_server_langgraph.mcp.websocket.connection_manager import (
                    get_connection_manager,
                )
                from mcp_server_langgraph.mcp.websocket.config import (
                    is_streaming_enabled,
                    get_streaming_max_chunk_size,
                )
                from mcp_server_langgraph.mcp.websocket.rate_limiter import (
                    get_outbound_rate_limiter,
                )

                if is_streaming_enabled():
                    # Cast self to Any for StreamingToolCallHandler compatibility
                    # (message_handler.AuthenticatedMCPHandler implements same interface)
                    streaming_handler = StreamingToolCallHandler(
                        mcp_handler=self,  # type: ignore[arg-type]
                        send_notification=self.notification_callback,
                        metrics_collector=streaming_metrics_collector,
                        outbound_rate_limiter=get_outbound_rate_limiter(),
                        max_chunk_size=get_streaming_max_chunk_size(),
                        connection_manager=get_connection_manager(),
                        session_id=self.session_id,
                    )
                    streaming_result = await streaming_handler.handle_streaming_call(
                        message_id=message_id,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                    return self._success_response(message_id, streaming_result)
            except ImportError:
                logger.debug("Streaming components not available, falling back to non-streaming")

        # Fall back to non-streaming execution
        try:
            tool_result = await self.execute_tool(tool_name, arguments)
            return self._success_response(message_id, {"content": tool_result, "isError": False})
        except Exception as e:
            return self._success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute a tool with user context.

        Overrides the base method to integrate with the real agent and
        propagate user context for authorization.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            List of content items from the tool execution.
        """
        session_id = arguments.get("session_id")

        # Execute with the real agent
        return await self._execute_with_agent(
            tool_name=tool_name,
            arguments=arguments,
            user_id=self.user_id,
            session_id=session_id,
        )

    async def _execute_with_agent(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a tool via the LangGraph agent.

        This method integrates with MCPBridge for real tool execution.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            user_id: The user's ID for context.
            session_id: Optional session ID for context preservation.

        Returns:
            List of content items from the agent execution.
        """
        logger.info(
            f"Tool execution requested: {tool_name} by user {user_id}",
            extra={"tool_name": tool_name, "user_id": user_id, "session_id": session_id},
        )

        # Try to get MCPBridge for real tool execution
        try:
            from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, get_mcp_bridge

            bridge = get_mcp_bridge()

            if tool_name == "langgraph-run":
                query = arguments.get("query", "")

                # Use MCPBridge if available
                if bridge and bridge.is_configured:
                    try:
                        response = await bridge.send_chat_message(
                            session_id=session_id or "default",
                            message=query,
                            user_id=user_id,
                        )
                        return [
                            {
                                "type": "text",
                                "text": response.content,
                            }
                        ]
                    except ChatError as e:
                        logger.warning(
                            f"MCPBridge execution failed: {e}",
                            extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                        )
                        return [
                            {
                                "type": "text",
                                "text": f"Error executing query: {e}",
                            }
                        ]

                # Fallback when MCPBridge is not available
                logger.debug(
                    "MCPBridge not available, using placeholder response",
                    extra={"tool_name": tool_name, "user_id": user_id},
                )
                return [
                    {
                        "type": "text",
                        "text": f"[Agent] Processing query for user {user_id}: {query}",
                    }
                ]

            # For other tools, use MCPBridge.call_tool if available
            if bridge and bridge.is_configured:
                try:
                    result = await bridge.call_tool(tool_name, arguments)
                    return result.content
                except ChatError as e:
                    logger.warning(
                        f"MCPBridge tool call failed: {e}",
                        extra={"tool_name": tool_name, "user_id": user_id, "error": str(e)},
                    )
                    return [
                        {
                            "type": "text",
                            "text": f"Error executing tool: {e}",
                        }
                    ]
        except ImportError:
            logger.debug("MCPBridge not available, using fallback")

        return [{"type": "text", "text": f"Executed {tool_name} with {arguments}"}]

    async def execute_tool_streaming(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a tool with streaming response.

        Yields streaming chunks that can be sent as $/streaming/chunk notifications.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Yields:
            Content chunks from the streaming execution.
        """
        session_id = arguments.get("session_id")

        try:
            from mcp_server_langgraph.api.v1.mcp_bridge import ChatError, get_mcp_bridge

            bridge = get_mcp_bridge()

            if tool_name == "langgraph-run":
                query = arguments.get("query", "")

                # Use MCPBridge streaming if available
                if bridge and bridge.is_configured:
                    try:
                        async for chunk in bridge.stream_chat_message(
                            session_id=session_id or "default",
                            message=query,
                            user_id=self.user_id,
                        ):
                            yield {
                                "type": "text",
                                "text": chunk.content,
                                "is_final": chunk.is_final,
                            }
                        return
                    except ChatError as e:
                        logger.warning(
                            f"MCPBridge streaming failed: {e}",
                            extra={"tool_name": tool_name, "user_id": self.user_id},
                        )
                        yield {
                            "type": "text",
                            "text": f"Streaming error: {e}",
                            "is_final": True,
                        }
                        return

                # Fallback: yield single chunk
                yield {
                    "type": "text",
                    "text": f"[Agent] Processing query for user {self.user_id}: {query}",
                    "is_final": True,
                }
                return
        except ImportError:
            pass

        # For other tools, yield single result
        yield {
            "type": "text",
            "text": f"Executed {tool_name} with {arguments}",
            "is_final": True,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Error codes
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    # Handlers
    "MCPMessageHandler",
    "AuthenticatedMCPHandler",
]
