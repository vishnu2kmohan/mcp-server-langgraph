"""
Session Factory for Test Data Generation.

Provides factory functions for creating test session and message objects.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class SessionFactory:
    """Factory for creating test session objects."""

    @staticmethod
    def create(
        session_id: str | None = None,
        user_id: str = "alice",
        project_id: str | None = None,
        name: str = "Test Session",
        created_at: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a test session dictionary.

        Args:
            session_id: Session ID (auto-generated if not provided)
            user_id: Owner user ID
            project_id: Optional project ID
            name: Session name
            created_at: Creation timestamp

        Returns:
            Dictionary with session data
        """
        return {
            "id": session_id or str(uuid4()),
            "user_id": user_id,
            "project_id": project_id,
            "name": name,
            "created_at": created_at or datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }


class MessageFactory:
    """Factory for creating test message objects."""

    @staticmethod
    def human(content: str = "Hello, how can you help me?") -> HumanMessage:
        """Create a human message."""
        return HumanMessage(content=content)

    @staticmethod
    def ai(content: str = "I'm here to help!") -> AIMessage:
        """Create an AI message."""
        return AIMessage(content=content)

    @staticmethod
    def system(content: str = "You are a helpful assistant.") -> SystemMessage:
        """Create a system message."""
        return SystemMessage(content=content)

    @staticmethod
    def conversation(
        turns: int = 3,
        include_system: bool = True,
    ) -> list:
        """
        Create a test conversation with alternating human/AI messages.

        Args:
            turns: Number of human-AI turn pairs
            include_system: Whether to include a system message at the start

        Returns:
            List of messages forming a conversation
        """
        messages = []

        if include_system:
            messages.append(MessageFactory.system())

        for i in range(turns):
            messages.append(MessageFactory.human(f"Question {i + 1}"))
            messages.append(MessageFactory.ai(f"Answer {i + 1}"))

        return messages


class AgentStateFactory:
    """Factory for creating test agent state objects."""

    @staticmethod
    def create(
        messages: list | None = None,
        next_action: str = "respond",
        user_id: str = "alice",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a test agent state dictionary.

        Args:
            messages: List of messages (creates default if None)
            next_action: Next action for the agent
            user_id: User ID
            request_id: Request ID (auto-generated if not provided)

        Returns:
            Dictionary matching AgentState TypedDict
        """
        return {
            "messages": messages or [MessageFactory.human()],
            "next_action": next_action,
            "user_id": user_id,
            "request_id": request_id or f"test-{uuid4().hex[:8]}",
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": None,
            "user_request": None,
        }
