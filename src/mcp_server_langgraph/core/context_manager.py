"""
Context Management for Agentic Workflows

Implements Anthropic's context engineering best practices:
- Compaction: Summarize conversation history when approaching limits
- Just-in-time loading: Load context dynamically as needed
- Token efficiency: Minimize context while maximizing signal

References:
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
"""

from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from mcp_server_langgraph.llm.factory import create_summarization_model
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import count_tokens


class CompactionResult(BaseModel):
    """Result of conversation compaction operation."""

    compacted_messages: list[BaseMessage] = Field(description="Compacted conversation messages")
    original_token_count: int = Field(description="Token count before compaction")
    compacted_token_count: int = Field(description="Token count after compaction")
    messages_summarized: int = Field(description="Number of messages summarized")
    compression_ratio: float = Field(ge=0.0, le=1.0, description="Compression achieved (1.0 = no compression)")


class ContextManager:
    """
    Manages conversation context following Anthropic's best practices.

    Key strategies:
    1. Compaction: Summarize old messages when approaching token limits
    2. Structured note-taking: Maintain persistent architectural decisions
    3. Progressive disclosure: Keep recent messages, summarize older ones

    Implementation follows "Long-Horizon Task Techniques" from Anthropic's guide.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        compaction_threshold: int = 8000,
        target_after_compaction: int = 4000,
        recent_message_count: int = 5,
        settings=None,
    ):
        """
        Initialize context manager.

        Args:
            compaction_threshold: Token count that triggers compaction (default: 8000)
            target_after_compaction: Target token count after compaction (default: 4000)
            recent_message_count: Number of recent messages to keep uncompacted (default: 5)
            settings: Application settings (if None, uses global settings)
        """
        self.compaction_threshold = compaction_threshold
        self.target_after_compaction = target_after_compaction
        self.recent_message_count = recent_message_count

        # Initialize dedicated summarization LLM (lighter/cheaper model)
        if settings is None:
            from mcp_server_langgraph.core.config import settings as global_settings

            settings = global_settings

        self.settings = settings
        self.llm = create_summarization_model(settings)
        logger.info(
            "ContextManager initialized",
            extra={
                "compaction_threshold": compaction_threshold,
                "target_after_compaction": target_after_compaction,
                "recent_message_count": recent_message_count,
                "model": settings.model_name,
            },
        )

    def needs_compaction(self, messages: list[BaseMessage]) -> bool:
        """
        Check if conversation needs compaction.

        Args:
            messages: Conversation messages

        Returns:
            True if token count exceeds threshold
        """
        # Use model-aware token counting
        model_name = self.settings.model_name
        total_tokens = sum(count_tokens(self._message_to_text(msg), model=model_name) for msg in messages)

        with tracer.start_as_current_span("context.check_compaction") as span:
            span.set_attribute("message.count", len(messages))
            span.set_attribute("token.count", total_tokens)
            span.set_attribute("needs.compaction", total_tokens > self.compaction_threshold)

            if total_tokens > self.compaction_threshold:
                logger.info(
                    "Compaction needed",
                    extra={
                        "total_tokens": total_tokens,
                        "threshold": self.compaction_threshold,
                        "message_count": len(messages),
                    },
                )
                return True

            return False

    async def compact_conversation(self, messages: list[BaseMessage], preserve_system: bool = True) -> CompactionResult:
        """
        Compact conversation by summarizing older messages.

        Strategy (Anthropic's "Compaction" technique):
        1. Keep system messages (architectural context)
        2. Keep recent N messages (working context)
        3. Summarize older messages (historical context)

        Args:
            messages: Full conversation history
            preserve_system: Keep system messages intact (default: True)

        Returns:
            CompactionResult with compacted messages and metrics
        """
        with tracer.start_as_current_span("context.compact") as span:
            # Use model-aware token counting
            model_name = self.settings.model_name
            original_tokens = sum(count_tokens(self._message_to_text(msg), model=model_name) for msg in messages)

            span.set_attribute("message.count.original", len(messages))
            span.set_attribute("token.count.original", original_tokens)

            # Separate messages by type
            system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)] if preserve_system else []
            other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

            # Keep recent messages
            recent_messages = other_messages[-self.recent_message_count :]
            older_messages = other_messages[: -self.recent_message_count]

            if not older_messages:
                # Nothing to compact
                logger.info("No older messages to compact")
                return CompactionResult(
                    compacted_messages=messages,
                    original_token_count=original_tokens,
                    compacted_token_count=original_tokens,
                    messages_summarized=0,
                    compression_ratio=1.0,
                )

            # Summarize older messages
            summary_text = await self._summarize_messages(older_messages)
            summary_message = SystemMessage(
                content=f"<conversation_summary>\n{summary_text}\n</conversation_summary>\n\n"
                f"[Previous {len(older_messages)} messages summarized to preserve context]"
            )

            # Reconstruct conversation: system + summary + recent
            compacted_messages = system_messages + [summary_message] + recent_messages

            compacted_tokens = sum(count_tokens(self._message_to_text(msg), model=model_name) for msg in compacted_messages)

            # Calculate compression ratio (clamped to max 1.0)
            # In rare cases, summary may be longer than original, so clamp to prevent validation errors
            compression_ratio = min(1.0, compacted_tokens / original_tokens) if original_tokens > 0 else 1.0

            span.set_attribute("message.count.compacted", len(compacted_messages))
            span.set_attribute("token.count.compacted", compacted_tokens)
            span.set_attribute("compression.ratio", compression_ratio)

            metrics.successful_calls.add(1, {"operation": "compact_conversation"})

            logger.info(
                "Conversation compacted",
                extra={
                    "original_messages": len(messages),
                    "compacted_messages": len(compacted_messages),
                    "original_tokens": original_tokens,
                    "compacted_tokens": compacted_tokens,
                    "compression_ratio": compression_ratio,
                    "messages_summarized": len(older_messages),
                },
            )

            return CompactionResult(
                compacted_messages=compacted_messages,
                original_token_count=original_tokens,
                compacted_token_count=compacted_tokens,
                messages_summarized=len(older_messages),
                compression_ratio=compression_ratio,
            )

    async def _summarize_messages(self, messages: list[BaseMessage]) -> str:
        """
        Summarize a sequence of messages preserving key information.

        Follows Anthropic's guidance:
        "Preserve architectural decisions and critical details
        while discarding redundant outputs"

        Args:
            messages: Messages to summarize

        Returns:
            Summary text preserving key information
        """
        with tracer.start_as_current_span("context.summarize"):
            # Format conversation for summarization
            conversation_text = "\n\n".join([f"{self._get_role_label(msg)}: {msg.content}" for msg in messages])

            # Summarization prompt using XML structure (Anthropic best practice)
            summarization_prompt = f"""<task>
Summarize the following conversation segment, preserving critical information.
</task>

<instructions>
Focus on:
1. Key decisions made
2. Important facts or data discovered
3. User preferences or requirements
4. Action items or next steps
5. Any errors or issues encountered

Omit:
- Redundant greetings or small talk
- Repetitive information
- Verbose explanations already acted upon
</instructions>

<conversation_to_summarize>
{conversation_text}
</conversation_to_summarize>

<output_format>
Provide a concise summary in 3-5 bullet points.
Focus on high-signal information that maintains conversation context.
</output_format>"""

            try:
                # BUGFIX: Wrap prompt in HumanMessage to avoid string-to-character-list iteration
                response = await self.llm.ainvoke([HumanMessage(content=summarization_prompt)])
                summary = response.content if hasattr(response, "content") else str(response)

                logger.info("Messages summarized", extra={"message_count": len(messages), "summary_length": len(summary)})

                return summary

            except Exception as e:
                logger.error(f"Summarization failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "summarize_messages"})

                # Fallback: Simple concatenation with truncation
                fallback_summary = f"Previous conversation ({len(messages)} messages): " + conversation_text[:500] + "..."
                return fallback_summary

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using LiteLLM model-aware counting.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return count_tokens(text, model=self.settings.model_name)

    def _message_to_text(self, message: BaseMessage) -> str:
        """Convert message to text for token counting."""
        if hasattr(message, "content"):
            return str(message.content)
        return str(message)

    def _get_role_label(self, message: BaseMessage) -> str:
        """Get role label for message formatting."""
        if isinstance(message, HumanMessage):
            return "User"
        elif isinstance(message, AIMessage):
            return "Assistant"
        elif isinstance(message, SystemMessage):
            return "System"
        else:
            return "Message"

    def extract_key_information(self, messages: list[BaseMessage]) -> dict[str, list[str]]:
        """
        Extract and categorize key information from conversation.

        Implements "Structured Note-Taking" pattern from Anthropic's guide.
        This is a rule-based fallback method.

        Args:
            messages: Conversation messages

        Returns:
            Dictionary with categorized key information
        """
        key_info = {  # type: ignore[var-annotated]
            "decisions": [],
            "requirements": [],
            "facts": [],
            "action_items": [],
            "issues": [],
            "preferences": [],
        }

        # Keyword-based extraction for all 6 categories
        # Expanded from 10 to ~35 keywords for better coverage
        for msg in messages:
            msg_content = msg.content if hasattr(msg, "content") else ""
            content = msg_content.lower() if isinstance(msg_content, str) else ""

            # Decisions (voting, choosing, selecting)
            if any(
                keyword in content
                for keyword in [
                    "decided",
                    "agreed",
                    "chose",
                    "selected",
                    "picked",
                    "opted",
                    "determined",
                    "concluded",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["decisions"].append(msg_content[:200])

            # Requirements (obligations, constraints)
            if any(
                keyword in content
                for keyword in [
                    "need",
                    "require",
                    "must",
                    "should",
                    "have to",
                    "necessary",
                    "essential",
                    "mandatory",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["requirements"].append(msg_content[:200])

            # Facts (statements of truth, data points)
            if any(
                keyword in content
                for keyword in [
                    " is ",
                    " are ",
                    " was ",
                    " were ",
                    "according to",
                    "version",
                    "default",
                    "by default",
                    "currently",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["facts"].append(msg_content[:200])

            # Action Items (tasks, TODOs)
            if any(
                keyword in content
                for keyword in [
                    "todo",
                    "to-do",
                    "please",
                    "need to",
                    "should",
                    "will",
                    "let's",
                    "we'll",
                    "add",
                    "fix",
                    "update",
                    "refactor",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["action_items"].append(msg_content[:200])

            # Issues (problems, bugs, errors)
            if any(
                keyword in content
                for keyword in [
                    "error",
                    "issue",
                    "problem",
                    "failed",
                    "bug",
                    "broken",
                    "crash",
                    "exception",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["issues"].append(msg_content[:200])

            # Preferences (likes, dislikes, choices)
            if any(
                keyword in content
                for keyword in [
                    "prefer",
                    "like",
                    "favorite",
                    "dislike",
                    "hate",
                    "love",
                    "enjoy",
                    "rather",
                ]
            ):
                if isinstance(msg_content, str):
                    key_info["preferences"].append(msg_content[:200])

        return key_info

    async def extract_key_information_llm(self, messages: list[BaseMessage]) -> dict[str, list[str]]:
        """
        Extract and categorize key information using LLM.

        Enhanced version of extract_key_information with LLM-based extraction.
        Implements Anthropic's "Structured Note-Taking" pattern with 6 categories.

        Args:
            messages: Conversation messages

        Returns:
            Dictionary with categorized key information
        """
        with tracer.start_as_current_span("context.extract_key_info_llm"):
            # Format conversation
            conversation_text = "\n\n".join([f"{self._get_role_label(msg)}: {msg.content}" for msg in messages])

            # Extraction prompt with XML structure (Anthropic best practice)
            extraction_prompt = f"""<task>
Extract and categorize key information from this conversation.
</task>

<categories>
1. **Decisions**: Choices made, agreements reached, directions chosen
2. **Requirements**: Needs, must-haves, constraints, specifications
3. **Facts**: Important factual information discovered or confirmed
4. **Action Items**: Tasks to do, next steps, follow-ups
5. **Issues**: Problems encountered, errors, blockers
6. **Preferences**: User preferences, settings, customizations
</categories>

<conversation>
{conversation_text}
</conversation>

<instructions>
For each category, list the key items found.
If a category has no items, write "None".
Be concise (1-2 sentences per item).
Focus on information that should be remembered long-term.
</instructions>

<output_format>
DECISIONS:
- [Decision 1]
- [Decision 2]

REQUIREMENTS:
- [Requirement 1]

FACTS:
- [Fact 1]

ACTION_ITEMS:
- [Item 1]

ISSUES:
- [Issue 1 or None]

PREFERENCES:
- [Preference 1 or None]
</output_format>"""

            try:
                # BUGFIX: Wrap prompt in HumanMessage to avoid string-to-character-list iteration
                response = await self.llm.ainvoke([HumanMessage(content=extraction_prompt)])
                response_content = response.content if hasattr(response, "content") else str(response)
                extraction_text = response_content if isinstance(response_content, str) else str(response_content)

                # Parse response
                key_info = self._parse_extraction_response(extraction_text)

                logger.info(
                    "Key information extracted with LLM",
                    extra={
                        "decisions": len(key_info.get("decisions", [])),
                        "requirements": len(key_info.get("requirements", [])),
                        "facts": len(key_info.get("facts", [])),
                        "action_items": len(key_info.get("action_items", [])),
                        "issues": len(key_info.get("issues", [])),
                        "preferences": len(key_info.get("preferences", [])),
                    },
                )

                metrics.successful_calls.add(1, {"operation": "extract_key_info_llm"})

                return key_info

            except Exception as e:
                logger.error(f"LLM-based extraction failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "extract_key_info_llm"})
                # Fallback to rule-based
                return self.extract_key_information(messages)

    def _parse_extraction_response(self, text: str) -> dict[str, list[str]]:
        """
        Parse LLM extraction response into structured dict.

        Args:
            text: LLM response text

        Returns:
            Dictionary with categorized information
        """
        categories = {  # type: ignore[var-annotated]
            "decisions": [],
            "requirements": [],
            "facts": [],
            "action_items": [],
            "issues": [],
            "preferences": [],
        }

        # Extract each section
        current_category = None

        for line in text.split("\n"):
            line = line.strip()

            # Check for category headers
            if line.upper().startswith("DECISIONS:"):
                current_category = "decisions"
            elif line.upper().startswith("REQUIREMENTS:"):
                current_category = "requirements"
            elif line.upper().startswith("FACTS:"):
                current_category = "facts"
            elif line.upper().startswith("ACTION_ITEMS:") or line.upper().startswith("ACTION ITEMS:"):
                current_category = "action_items"
            elif line.upper().startswith("ISSUES:"):
                current_category = "issues"
            elif line.upper().startswith("PREFERENCES:"):
                current_category = "preferences"
            # Check for bullet points
            elif line.startswith("-") and current_category:
                item = line[1:].strip()
                if item and item.lower() != "none":
                    categories[current_category].append(item)

        return categories


# Convenience functions for easy import
async def compact_if_needed(
    messages: list[BaseMessage], context_manager: Optional[ContextManager] = None
) -> list[BaseMessage]:
    """
    Compact conversation if needed, otherwise return unchanged.

    Args:
        messages: Conversation messages
        context_manager: ContextManager instance (creates new if None)

    Returns:
        Original or compacted messages
    """
    if context_manager is None:
        context_manager = ContextManager()

    if context_manager.needs_compaction(messages):
        result = await context_manager.compact_conversation(messages)
        return result.compacted_messages

    return messages
