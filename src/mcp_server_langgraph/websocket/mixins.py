"""
WebSocket Mixins.

Provides reusable mixin classes for common WebSocket handler patterns:
- BroadcasterMixin: Standardized broadcaster integration with subscription state

Usage:
    class MyHandler(WebSocketBase, BroadcasterMixin):
        def __init__(self, broadcaster: Broadcaster, ...):
            super().__init__(...)
            self._broadcaster = broadcaster

        async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
            if message.type == "subscribe":
                # Simple subscribe
                await self.subscribe()
                # Or with custom arguments for filtering/context
                await self.subscribe(user_id=self.user_id)
                await self.subscribe(user_id=self.user_id, context_entity_id="ctx-123")
                await self.subscribe(filter_=my_filter)
                return self.create_subscribed_response(correlation_id=message.id)
            ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class Broadcaster(Protocol):
    """Protocol for broadcaster objects used with BroadcasterMixin.

    Broadcasters should accept websocket as the first argument and may
    accept additional keyword arguments for filtering or context.
    """

    async def subscribe(self, websocket: Any, **kwargs: Any) -> None:
        """Subscribe a websocket to receive broadcasts.

        Args:
            websocket: The WebSocket connection to subscribe.
            **kwargs: Additional arguments (user_id, filter_, context_entity_id, etc.)
        """
        ...

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe a websocket from broadcasts."""
        ...


class BroadcasterMixin:
    """
    Mixin for handlers that integrate with a broadcaster pattern.

    Provides standardized subscription state management and methods for
    subscribing/unsubscribing from a broadcaster. Reduces boilerplate in
    handlers that follow the common pattern of:
    - Storing subscription state
    - Calling broadcaster.subscribe/unsubscribe
    - Updating state accordingly

    Attributes expected on the class:
        _broadcaster: The broadcaster instance to integrate with
        _websocket: The WebSocket connection (from WebSocketBase)

    Usage:
        class AlertHandler(WebSocketBase, BroadcasterMixin):
            def __init__(self, config: WebSocketConfig, broadcaster: Broadcaster):
                super().__init__(config)
                self._broadcaster = broadcaster

            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                if message.type == "subscribe":
                    await self.subscribe()
                    return self.create_subscribed_response(correlation_id=message.id)
                elif message.type == "unsubscribe":
                    await self.unsubscribe()
                    return self.create_unsubscribed_response(correlation_id=message.id)
    """

    # Type hints for expected attributes from WebSocketBase
    _broadcaster: Any
    _websocket: WebSocket | None
    _subscribed: bool

    def __init__(self) -> None:
        """Initialize mixin - set default subscription state."""
        # Only set if not already set by another class in MRO
        if not hasattr(self, "_subscribed"):
            self._subscribed = False

    @property
    def subscribed(self) -> bool:
        """Get current subscription state."""
        return getattr(self, "_subscribed", False)

    @subscribed.setter
    def subscribed(self, value: bool) -> None:
        """Set subscription state."""
        self._subscribed = value

    async def subscribe(self, **kwargs: Any) -> None:
        """
        Subscribe to the broadcaster.

        Calls broadcaster.subscribe with the current websocket and any
        additional keyword arguments, then sets subscribed=True.
        Subclasses can override to add custom logic.

        Args:
            **kwargs: Additional arguments to pass to broadcaster.subscribe
                      (e.g., user_id, filter_, context_entity_id).

        Example:
            await self.subscribe(user_id="user-123")
            await self.subscribe(user_id="user-123", context_entity_id="ctx-456")
            await self.subscribe(filter_={"status": "OK"})
        """
        broadcaster = getattr(self, "_broadcaster", None)
        websocket = getattr(self, "_websocket", None)

        if broadcaster is None:
            logger.warning("subscribe() called but no broadcaster available")
            return

        await broadcaster.subscribe(websocket, **kwargs)
        self._subscribed = True

    async def unsubscribe(self) -> None:
        """
        Unsubscribe from the broadcaster.

        Only calls broadcaster.unsubscribe if currently subscribed.
        Sets subscribed=False after successful unsubscribe.
        Subclasses can override to add custom logic.
        """
        if not self._subscribed:
            return

        broadcaster = getattr(self, "_broadcaster", None)
        websocket = getattr(self, "_websocket", None)

        if broadcaster is None:
            logger.warning("unsubscribe() called but no broadcaster available")
            self._subscribed = False
            return

        await broadcaster.unsubscribe(websocket)
        self._subscribed = False
