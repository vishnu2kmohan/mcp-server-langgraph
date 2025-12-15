"""
Custom exceptions for the Unified Audit Logging Facility.

Provides specific exception types for audit-related errors:
- Configuration errors
- Integrity verification failures
- Retention policy violations
- Service errors

These exceptions support FedRAMP AU-5 requirements for
alerting personnel to audit processing failures.
"""

from typing import Any


class AuditError(Exception):
    """Base exception for all audit-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize audit error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuditConfigurationError(AuditError):
    """Raised when audit configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        """
        Initialize configuration error.

        Args:
            message: Error description.
            config_key: The configuration key that caused the error.
        """
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, details)
        self.config_key = config_key


class AuditIntegrityError(AuditError):
    """
    Raised when audit log integrity verification fails.

    This is a critical security event that should trigger
    immediate alerting per FedRAMP AU-9 requirements.
    """

    def __init__(
        self,
        message: str,
        sequence_number: int | None = None,
        expected_hash: str | None = None,
        actual_hash: str | None = None,
    ) -> None:
        """
        Initialize integrity error.

        Args:
            message: Error description.
            sequence_number: The sequence number where integrity failed.
            expected_hash: The expected hash value.
            actual_hash: The actual hash value found.
        """
        details = {
            "sequence_number": sequence_number,
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
        }
        super().__init__(message, details)
        self.sequence_number = sequence_number
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash


class AuditChainBrokenError(AuditIntegrityError):
    """Raised when the hash chain linkage is broken."""

    def __init__(
        self,
        message: str,
        position: int,
        expected_previous: str | None,
        actual_previous: str | None,
    ) -> None:
        """
        Initialize chain broken error.

        Args:
            message: Error description.
            position: Position in the chain where break occurred.
            expected_previous: Expected previous_hash value.
            actual_previous: Actual previous_hash value found.
        """
        super().__init__(
            message,
            sequence_number=position,
            expected_hash=expected_previous,
            actual_hash=actual_previous,
        )
        self.position = position


class AuditSequenceGapError(AuditIntegrityError):
    """Raised when a gap in sequence numbers is detected."""

    def __init__(
        self,
        message: str,
        expected_sequence: int,
        actual_sequence: int,
    ) -> None:
        """
        Initialize sequence gap error.

        Args:
            message: Error description.
            expected_sequence: The expected sequence number.
            actual_sequence: The actual sequence number found.
        """
        super().__init__(message, sequence_number=actual_sequence)
        self.expected_sequence = expected_sequence
        self.actual_sequence = actual_sequence
        self.details["expected_sequence"] = expected_sequence
        self.details["actual_sequence"] = actual_sequence


class AuditRetentionError(AuditError):
    """Raised when retention policy operations fail."""

    def __init__(
        self,
        message: str,
        regulation: str | None = None,
        operation: str | None = None,
    ) -> None:
        """
        Initialize retention error.

        Args:
            message: Error description.
            regulation: The regulation (GDPR, HIPAA, etc.) involved.
            operation: The operation that failed (delete, archive, etc.).
        """
        details = {
            "regulation": regulation,
            "operation": operation,
        }
        super().__init__(message, details)
        self.regulation = regulation
        self.operation = operation


class AuditServiceError(AuditError):
    """Raised when the audit service encounters an operational error."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize service error.

        Args:
            message: Error description.
            operation: The operation that failed.
            recoverable: Whether the error is recoverable.
        """
        details = {
            "operation": operation,
            "recoverable": recoverable,
        }
        super().__init__(message, details)
        self.operation = operation
        self.recoverable = recoverable


class AuditRepositoryError(AuditError):
    """Raised when audit repository operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        event_id: str | None = None,
    ) -> None:
        """
        Initialize repository error.

        Args:
            message: Error description.
            operation: The repository operation that failed.
            event_id: The event ID involved, if applicable.
        """
        details = {
            "operation": operation,
            "event_id": event_id,
        }
        super().__init__(message, details)
        self.operation = operation
        self.event_id = event_id


class AuditExportError(AuditError):
    """Raised when audit log export operations fail."""

    def __init__(
        self,
        message: str,
        format_type: str | None = None,
        event_count: int | None = None,
    ) -> None:
        """
        Initialize export error.

        Args:
            message: Error description.
            format_type: The export format (JSON, CSV, etc.).
            event_count: Number of events being exported.
        """
        details = {
            "format_type": format_type,
            "event_count": event_count,
        }
        super().__init__(message, details)
        self.format_type = format_type
        self.event_count = event_count


class AuditAlertError(AuditError):
    """Raised when audit alerting operations fail."""

    def __init__(
        self,
        message: str,
        alert_type: str | None = None,
        channel: str | None = None,
    ) -> None:
        """
        Initialize alert error.

        Args:
            message: Error description.
            alert_type: The type of alert that failed.
            channel: The notification channel that failed.
        """
        details = {
            "alert_type": alert_type,
            "channel": channel,
        }
        super().__init__(message, details)
        self.alert_type = alert_type
        self.channel = channel


class AuditAuthorizationError(AuditError):
    """Raised when audit access is denied."""

    def __init__(
        self,
        message: str,
        actor_id: str | None = None,
        resource: str | None = None,
        action: str | None = None,
    ) -> None:
        """
        Initialize authorization error.

        Args:
            message: Error description.
            actor_id: The actor who was denied access.
            resource: The resource being accessed.
            action: The action being attempted.
        """
        details = {
            "actor_id": actor_id,
            "resource": resource,
            "action": action,
        }
        super().__init__(message, details)
        self.actor_id = actor_id
        self.resource = resource
        self.action = action
