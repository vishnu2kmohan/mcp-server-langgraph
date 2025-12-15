"""
Audit decorators for service-level auditing.

Provides decorators for auditing function calls:
- @audit_action: General purpose audit decorator
- @audit_ai_operation: AI operation auditing (EU AI Act)
- @audit_data_access: Data access auditing (HIPAA, GDPR)

These decorators complement the HTTP middleware by providing
fine-grained auditing at the service/function level.
"""

import functools
import inspect
import logging
from typing import Any, Callable, Literal, ParamSpec, TypeVar, cast
from uuid import uuid4

from mcp_server_langgraph.audit.models import (
    AIOperationDetails,
    AuditActor,
    AuditContext,
    AuditEventCategory,
    AuditEventType,
    UnifiedAuditEvent,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# Outcome literal type for audit events
OutcomeType = Literal["success", "failure", "denied", "error"]


def audit_action(
    category: AuditEventCategory,
    event_type: AuditEventType,
    resource_type: str,
    resource_id_param: str | None = None,
    regulations: list[str] | None = None,
    audit_service: Any | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to audit any action with category and event type.

    Args:
        category: The audit event category.
        event_type: The specific event type.
        resource_type: Type of resource being acted upon.
        resource_id_param: Name of parameter containing resource ID.
        regulations: List of applicable regulations (GDPR, HIPAA, etc.)
        audit_service: Service for persisting audit events.

    Returns:
        Decorated function that logs audit events.

    Example:
        @audit_action(
            category=AuditEventCategory.DATA_MODIFICATION,
            event_type=AuditEventType.DATA_CREATE,
            resource_type="workflow",
            resource_id_param="workflow_id",
            regulations=["SOC2"],
        )
        async def create_workflow(workflow_id: str) -> dict:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Extract resource_id from parameters if specified
            resource_id = "unknown"
            if resource_id_param:
                # Try kwargs first
                if resource_id_param in kwargs:
                    resource_id = str(kwargs[resource_id_param])
                else:
                    # Try positional args using function signature
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if resource_id_param in params:
                        idx = params.index(resource_id_param)
                        if idx < len(args):
                            resource_id = str(args[idx])

            # Create actor (system for decorator-based auditing)
            actor = AuditActor(
                actor_id="system",
                actor_type="system",
            )

            # Create context
            context = AuditContext(
                request_id=str(uuid4()),
            )

            # Execute the function
            outcome: OutcomeType = "success"
            error_details: dict[str, Any] = {}

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                return cast(T, result)
            except Exception as e:
                outcome = "error"
                error_details = {"error": str(e), "error_type": type(e).__name__}
                raise
            finally:
                # Create and log audit event
                try:
                    event = UnifiedAuditEvent(
                        category=category,
                        event_type=event_type,
                        actor=actor,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=f"{func.__module__}.{func.__name__}",
                        outcome=outcome,
                        context=context,
                        details=error_details,
                        regulation_tags=regulations or [],
                    )

                    logger.debug(
                        "Function audited",
                        extra={"audit_event": event.model_dump()},
                    )

                    if audit_service:
                        try:
                            await audit_service.log_event(event)
                        except Exception as audit_error:
                            logger.exception(
                                "Audit logging failed",
                                extra={"error": str(audit_error)},
                            )
                except Exception as audit_error:
                    logger.exception(
                        "Failed to create audit event",
                        extra={"error": str(audit_error)},
                    )

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # For sync functions, we can't await
            # Just call and log synchronously
            resource_id = "unknown"
            if resource_id_param:
                if resource_id_param in kwargs:
                    resource_id = str(kwargs[resource_id_param])

            actor = AuditActor(actor_id="system", actor_type="system")
            context = AuditContext(request_id=str(uuid4()))

            outcome: OutcomeType = "success"
            error_details: dict[str, Any] = {}

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                outcome = "error"
                error_details = {"error": str(e)}
                raise
            finally:
                try:
                    event = UnifiedAuditEvent(
                        category=category,
                        event_type=event_type,
                        actor=actor,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=f"{func.__module__}.{func.__name__}",
                        outcome=outcome,
                        context=context,
                        details=error_details,
                        regulation_tags=regulations or [],
                    )
                    logger.debug("Function audited", extra={"audit_event": event.model_dump()})
                except Exception as audit_error:
                    logger.exception("Failed to create audit event", extra={"error": str(audit_error)})

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def audit_ai_operation(
    model_id: str,
    provider: str,
    decision_type: str | None = None,
    audit_service: Any | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to audit AI operations (EU AI Act Articles 12, 19, 72).

    Args:
        model_id: The AI model identifier.
        provider: The AI provider (openai, anthropic, etc.)
        decision_type: Type of AI decision (generation, classification, etc.)
        audit_service: Service for persisting audit events.

    Returns:
        Decorated function that logs AI operation audit events.

    Example:
        @audit_ai_operation(
            model_id="gpt-4o",
            provider="openai",
            decision_type="generation",
        )
        async def generate_text(prompt: str) -> str:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            actor = AuditActor(actor_id="system", actor_type="system")
            context = AuditContext(request_id=str(uuid4()))

            outcome: OutcomeType = "success"
            error_details: dict[str, Any] = {}

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                return cast(T, result)
            except Exception as e:
                outcome = "error"
                error_details = {"error": str(e), "error_type": type(e).__name__}
                raise
            finally:
                try:
                    ai_details = AIOperationDetails(
                        model_id=model_id,
                        provider=provider,
                        decision_type=decision_type,
                    )

                    event = UnifiedAuditEvent(
                        category=AuditEventCategory.AI_OPERATION,
                        event_type=AuditEventType.AI_INVOKE,
                        actor=actor,
                        resource_type="ai_model",
                        resource_id=model_id,
                        action=f"{func.__module__}.{func.__name__}",
                        outcome=outcome,
                        context=context,
                        details=error_details,
                        ai_operation=ai_details,
                        regulation_tags=["EU_AI_ACT"],
                    )

                    logger.debug(
                        "AI operation audited",
                        extra={"audit_event": event.model_dump()},
                    )

                    if audit_service:
                        try:
                            await audit_service.log_event(event)
                        except Exception as audit_error:
                            logger.exception(
                                "Audit logging failed",
                                extra={"error": str(audit_error)},
                            )
                except Exception as audit_error:
                    logger.exception(
                        "Failed to create AI audit event",
                        extra={"error": str(audit_error)},
                    )

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]

        # For sync functions
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                logger.debug("AI operation audited (sync)")

        return sync_wrapper

    return decorator


def audit_data_access(
    resource_type: str,
    sensitivity: str = "normal",
    regulations: list[str] | None = None,
    audit_service: Any | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to audit data access operations (HIPAA, GDPR).

    Args:
        resource_type: Type of data resource being accessed.
        sensitivity: Data sensitivity level (normal, high, phi).
        regulations: List of applicable regulations.
        audit_service: Service for persisting audit events.

    Returns:
        Decorated function that logs data access audit events.

    Example:
        @audit_data_access(
            resource_type="patient_record",
            sensitivity="phi",
            regulations=["HIPAA"],
        )
        async def read_patient_record(record_id: str) -> dict:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            actor = AuditActor(actor_id="system", actor_type="system")
            context = AuditContext(request_id=str(uuid4()))

            # Get first positional arg as resource_id if available
            resource_id = "unknown"
            if args:
                resource_id = str(args[0])
            elif kwargs:
                first_key = list(kwargs.keys())[0]
                resource_id = str(kwargs[first_key])

            outcome: OutcomeType = "success"
            error_details: dict[str, Any] = {"sensitivity": sensitivity}

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                return cast(T, result)
            except Exception as e:
                outcome = "error"
                error_details["error"] = str(e)
                raise
            finally:
                try:
                    event = UnifiedAuditEvent(
                        category=AuditEventCategory.DATA_ACCESS,
                        event_type=AuditEventType.DATA_READ,
                        actor=actor,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=f"{func.__module__}.{func.__name__}",
                        outcome=outcome,
                        context=context,
                        details=error_details,
                        regulation_tags=regulations or [],
                    )

                    logger.debug(
                        "Data access audited",
                        extra={"audit_event": event.model_dump()},
                    )

                    if audit_service:
                        try:
                            await audit_service.log_event(event)
                        except Exception as audit_error:
                            logger.exception(
                                "Audit logging failed",
                                extra={"error": str(audit_error)},
                            )
                except Exception as audit_error:
                    logger.exception(
                        "Failed to create data access audit event",
                        extra={"error": str(audit_error)},
                    )

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                logger.debug("Data access audited (sync)")

        return sync_wrapper

    return decorator
