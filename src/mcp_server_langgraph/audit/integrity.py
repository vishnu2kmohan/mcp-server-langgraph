"""
Cryptographic integrity for audit logs (FedRAMP AU-9).

Provides tamper-evident audit logging through:
- HMAC-SHA256 hash computation for each event
- Hash chain linking (each event references previous hash)
- Sequential numbering for gap detection
- Chain verification utilities

This implementation supports FedRAMP AU-9 requirements for
protecting audit information from unauthorized modification.
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field

from mcp_server_langgraph.audit.models import UnifiedAuditEvent

logger = logging.getLogger(__name__)


def compute_event_hash(event: UnifiedAuditEvent, secret: str) -> str:
    """
    Compute HMAC-SHA256 hash for an audit event.

    The hash is computed over a canonical JSON representation
    of the event, excluding the event_hash field itself.

    Args:
        event: The audit event to hash.
        secret: The HMAC secret key.

    Returns:
        64-character hex string (256 bits).
    """
    # Create canonical representation (exclude event_hash to avoid self-reference)
    event_data = event.model_dump(
        mode="json",
        exclude={"event_hash"},
    )

    # Sort keys for deterministic serialization
    canonical_json = json.dumps(event_data, sort_keys=True, default=str)

    # Compute HMAC-SHA256
    hmac_obj = hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical_json.encode("utf-8"),
        digestmod=hashlib.sha256,
    )

    return hmac_obj.hexdigest()


class HashChainBuilder:
    """
    Builds a cryptographic hash chain for audit events.

    Each event is assigned:
    - sequence_number: Incrementing integer for ordering and gap detection
    - previous_hash: Hash of the previous event in the chain
    - event_hash: HMAC-SHA256 hash of this event (including previous_hash)

    Example:
        builder = HashChainBuilder(secret="your-secret-key")

        event1 = builder.add_to_chain(audit_event1)
        # event1.sequence_number = 1
        # event1.previous_hash = None
        # event1.event_hash = "abc123..."

        event2 = builder.add_to_chain(audit_event2)
        # event2.sequence_number = 2
        # event2.previous_hash = "abc123..."
        # event2.event_hash = "def456..."
    """

    def __init__(self, secret: str, start_sequence: int = 1) -> None:
        """
        Initialize hash chain builder.

        Args:
            secret: HMAC secret key for hash computation.
            start_sequence: Starting sequence number (default: 1).
        """
        self._secret = secret
        self._current_sequence = start_sequence
        self._last_hash: str | None = None

    def get_last_hash(self) -> str | None:
        """Get the hash of the last event in the chain."""
        return self._last_hash

    def get_next_sequence(self) -> int:
        """Get the next sequence number to be assigned."""
        return self._current_sequence

    def add_to_chain(self, event: UnifiedAuditEvent) -> UnifiedAuditEvent:
        """
        Add an event to the hash chain.

        Args:
            event: The audit event to add.

        Returns:
            New event with sequence_number, previous_hash, and event_hash set.
        """
        # Create new event with chain fields
        chained_event = event.model_copy(
            update={
                "sequence_number": self._current_sequence,
                "previous_hash": self._last_hash,
            }
        )

        # Compute hash (includes previous_hash)
        event_hash = compute_event_hash(chained_event, self._secret)

        # Update event with computed hash
        chained_event = chained_event.model_copy(update={"event_hash": event_hash})

        # Update chain state
        self._last_hash = event_hash
        self._current_sequence += 1

        return chained_event

    def add_event(self, event: UnifiedAuditEvent) -> UnifiedAuditEvent:
        """
        Add an event to the hash chain (alias for add_to_chain).

        Args:
            event: The audit event to add.

        Returns:
            New event with sequence_number, previous_hash, and event_hash set.
        """
        return self.add_to_chain(event)


@dataclass
class ChainVerificationResult:
    """Result of hash chain verification."""

    valid: bool
    """Whether the chain is valid (no tampering detected)."""

    events_verified: int
    """Number of events verified."""

    errors: list[str] = field(default_factory=list)
    """List of error messages if chain is invalid."""

    first_sequence: int | None = None
    """Sequence number of first event in verified range."""

    last_sequence: int | None = None
    """Sequence number of last event in verified range."""


def verify_chain(
    events: list[UnifiedAuditEvent],
    secret: str,
) -> ChainVerificationResult:
    """
    Verify the integrity of a hash chain.

    Checks:
    1. Each event's hash matches recomputed hash
    2. Each event's previous_hash matches prior event's event_hash
    3. Sequence numbers are consecutive (no gaps)

    Args:
        events: List of events to verify (must be in sequence order).
        secret: HMAC secret key used for hash computation.

    Returns:
        ChainVerificationResult with validity and any errors found.
    """
    if not events:
        return ChainVerificationResult(valid=True, events_verified=0)

    errors: list[str] = []
    last_hash: str | None = None
    last_sequence: int | None = None

    for i, event in enumerate(events):
        # Check sequence number continuity
        if last_sequence is not None:
            expected_sequence = last_sequence + 1
            if event.sequence_number != expected_sequence:
                errors.append(f"Sequence gap at position {i}: expected {expected_sequence}, got {event.sequence_number}")

        # Check previous_hash linkage
        if event.previous_hash != last_hash:
            if i == 0 and event.previous_hash is None:
                # First event should have None previous_hash
                pass
            else:
                errors.append(
                    f"Chain broken at position {i}: previous_hash mismatch. Expected {last_hash}, got {event.previous_hash}"
                )

        # Verify event hash
        # Create temporary event with same chain fields but without event_hash
        temp_event = event.model_copy(update={"event_hash": None})
        temp_event = temp_event.model_copy(
            update={
                "sequence_number": event.sequence_number,
                "previous_hash": event.previous_hash,
            }
        )
        expected_hash = compute_event_hash(temp_event, secret)

        if event.event_hash != expected_hash:
            errors.append(
                f"Hash mismatch at position {i} (sequence {event.sequence_number}): "
                f"stored hash does not match computed hash. Possible tampering."
            )

        # Update state for next iteration
        last_hash = event.event_hash
        last_sequence = event.sequence_number

    # Determine first and last sequence numbers
    first_seq = events[0].sequence_number if events else None
    last_seq = events[-1].sequence_number if events else None

    return ChainVerificationResult(
        valid=len(errors) == 0,
        events_verified=len(events),
        errors=errors,
        first_sequence=first_seq,
        last_sequence=last_seq,
    )
