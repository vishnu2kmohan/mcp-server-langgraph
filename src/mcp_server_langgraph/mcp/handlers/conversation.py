"""
Conversation Tool Handler

Handles conversation retrieval and search operations.
Implements Anthropic best practices for search-focused tools.
"""

from typing import Any

from mcp.types import TextContent

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.core.constants import MESSAGE_PREVIEW_LENGTH
from mcp_server_langgraph.mcp.handlers.base import AbstractToolHandler
from mcp_server_langgraph.mcp.models import SearchConversationsInput
from mcp_server_langgraph.observability.telemetry import logger, tracer


class ConversationToolHandler(AbstractToolHandler):
    """
    Handler for conversation-related tool operations.

    Implements:
    - get_conversation: Retrieve conversation history
    - search_conversations: Search for conversations (vs list-all)
    """

    def __init__(
        self,
        auth: AuthMiddleware,
        agent_graph: Any,
    ) -> None:
        """Initialize conversation handler with dependencies."""
        super().__init__(auth, agent_graph)

    async def handle(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Handle conversation tool invocation.

        Dispatches to get or search based on arguments.
        """
        if "thread_id" in arguments and "query" not in arguments:
            return await self.handle_get_conversation(arguments, span, user_id)
        return await self.handle_search_conversations(arguments, span, user_id)

    async def handle_get_conversation(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """Retrieve conversation history from checkpointer."""
        with tracer.start_as_current_span("agent.get_conversation"):
            thread_id = arguments["thread_id"]
            conversation_resource = f"conversation:{thread_id}"

            # Authorize access
            can_view = await self.auth.authorize(user_id=user_id, relation="viewer", resource=conversation_resource)
            if not can_view:
                logger.warning(
                    "User cannot view conversation",
                    extra={"user_id": user_id, "thread_id": thread_id},
                )
                msg = f"Not authorized to view conversation {thread_id}"
                raise PermissionError(msg)

            # Retrieve conversation state
            try:
                graph = self.agent_graph
                if not hasattr(graph, "checkpointer") or graph.checkpointer is None:
                    logger.warning("Checkpointing not enabled")
                    return [
                        TextContent(
                            type="text",
                            text=f"Conversation history not available for thread {thread_id}. "
                            "Checkpointing is disabled. Enable it by setting ENABLE_CHECKPOINTING=true.",
                        )
                    ]

                config = {"configurable": {"thread_id": thread_id}}
                state_snapshot = await graph.aget_state(config)

                if not state_snapshot or not state_snapshot.values:
                    logger.info("No conversation history found", extra={"thread_id": thread_id})
                    return [
                        TextContent(
                            type="text",
                            text=f"No conversation history found for thread {thread_id}. "
                            "This thread may not exist or has no messages yet.",
                        )
                    ]

                messages = state_snapshot.values.get("messages", [])
                if not messages:
                    return [
                        TextContent(
                            type="text",
                            text=f"Thread {thread_id} exists but has no messages yet.",
                        )
                    ]

                # Format messages
                formatted_messages = self._format_messages(messages)
                response_text = (
                    f"Conversation history for thread {thread_id}\n"
                    f"Total messages: {len(messages)}\n"
                    f"User: {user_id}\n\n"
                    f"Messages:\n" + "\n".join(formatted_messages)
                )

                logger.info(
                    "Retrieved conversation history",
                    extra={"thread_id": thread_id, "message_count": len(messages), "user_id": user_id},
                )

                return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(
                    f"Failed to retrieve conversation: {e}",
                    extra={"thread_id": thread_id},
                    exc_info=True,
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Error retrieving conversation {thread_id}: {e!s}. "
                        "This may indicate a checkpointer issue or the conversation may not exist.",
                    )
                ]

    async def handle_search_conversations(
        self,
        arguments: dict[str, Any],
        span: Any,
        user_id: str,
    ) -> list[TextContent]:
        """
        Search conversations (replacing list-all approach).

        Implements Anthropic best practice for search-focused tools.
        """
        with tracer.start_as_current_span("agent.search_conversations"):
            try:
                search_input = SearchConversationsInput.model_validate(arguments)
            except Exception as e:
                logger.error(f"Invalid search input: {e}", extra={"arguments": arguments})
                msg = f"Invalid search input: {e}"
                raise ValueError(msg) from e

            query = search_input.query
            limit = search_input.limit

            span.set_attribute("search.query", query)
            span.set_attribute("search.limit", limit)

            all_conversations: list[str] = []
            filtered_conversations: list[str] = []

            # Try OpenFGA first, fall back to conversation store
            try:
                all_conversations = await self.auth.list_accessible_resources(
                    user_id=user_id, relation="viewer", resource_type="conversation"
                )

                if query:
                    normalized_query = query.lower().replace(" ", "_").replace("-", "_")
                    filtered_conversations = [
                        conv
                        for conv in all_conversations
                        if (
                            query.lower() in conv.lower()
                            or normalized_query in conv.lower().replace(" ", "_").replace("-", "_")
                        )
                    ]
                else:
                    filtered_conversations = all_conversations

            except Exception:
                logger.info("Using conversation store for search (OpenFGA unavailable)")
                filtered_conversations = await self._search_from_store(user_id, query, limit)

            limited_conversations = filtered_conversations[:limit]
            response_text = self._format_search_response(query, limited_conversations, len(filtered_conversations), limit)

            logger.info(
                "Searched conversations",
                extra={
                    "user_id": user_id,
                    "query": query,
                    "total_accessible": len(all_conversations),
                    "filtered_count": len(filtered_conversations),
                    "returned_count": len(limited_conversations),
                },
            )

            return [TextContent(type="text", text=response_text)]

    def _format_messages(self, messages: list[Any]) -> list[str]:
        """Format messages for display."""
        formatted = []
        for i, msg in enumerate(messages, 1):
            role = "unknown"
            content = str(msg)

            if hasattr(msg, "type"):
                role = msg.type
            elif hasattr(msg, "__class__"):
                role = msg.__class__.__name__.replace("Message", "").lower()

            if hasattr(msg, "content"):
                content = msg.content

            formatted.append(
                f"{i}. [{role}] {content[:MESSAGE_PREVIEW_LENGTH]}{'...' if len(content) > MESSAGE_PREVIEW_LENGTH else ''}"
            )
        return formatted

    async def _search_from_store(self, user_id: str, query: str, limit: int) -> list[str]:
        """Search conversations from the conversation store."""
        try:
            from mcp_server_langgraph.core.storage.conversation_store import get_conversation_store

            store = get_conversation_store()
            metadata_list = await store.search_conversations(user_id=user_id, query=query, limit=limit)
            return [f"conversation:{m.thread_id}" for m in metadata_list]
        except Exception as e:
            logger.warning(f"Conversation store also unavailable: {e}")
            return []

    def _format_search_response(
        self,
        query: str,
        conversations: list[str],
        total_filtered: int,
        limit: int,
    ) -> str:
        """Format search results for response."""
        if not conversations:
            return (
                f"No conversations found matching '{query}'. "
                f"Try a different search query or request access to more conversations."
            )

        response_lines = [
            (
                f"Found {len(conversations)} conversation(s) matching '{query}':"
                if query
                else f"Showing {len(conversations)} recent conversation(s):"
            )
        ]

        for i, conv_id in enumerate(conversations, 1):
            response_lines.append(f"{i}. {conv_id}")

        if total_filtered > limit:
            response_lines.append(
                f"\n[Showing {limit} of {total_filtered} results. Use a more specific query to narrow results.]"
            )

        return "\n".join(response_lines)
