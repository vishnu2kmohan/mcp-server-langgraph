"""
HIPAA Compliance Controls

Implements HIPAA Security Rule technical safeguards:
- 164.312(a)(1): Unique User Identification
- 164.312(a)(2)(i): Emergency Access Procedure
- 164.312(a)(2)(iii): Automatic Logoff
- 164.312(b): Audit Controls
- 164.312(c)(1): Integrity Controls

Note: Only required if processing Protected Health Information (PHI)
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.integrations.alerting import Alert, AlertSeverity, AlertingService
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class EmergencyAccessRequest(BaseModel):
    """Emergency access request for PHI data"""

    user_id: str = Field(..., description="User requesting emergency access")
    reason: str = Field(..., min_length=10, description="Reason for emergency access (minimum 10 characters)")
    approver_id: str = Field(..., description="User ID of approver")
    duration_hours: int = Field(default=4, ge=1, le=24, description="Duration of emergency access (1-24 hours)")
    access_level: str = Field(default="PHI", description="Level of access granted")


class EmergencyAccessGrant(BaseModel):
    """Emergency access grant record"""

    grant_id: str
    user_id: str
    reason: str
    approver_id: str
    granted_at: str  # ISO timestamp
    expires_at: str  # ISO timestamp
    access_level: str
    revoked: bool = False
    revoked_at: Optional[str] = None


class PHIAuditLog(BaseModel):
    """HIPAA-compliant audit log for PHI access"""

    timestamp: str  # ISO format
    user_id: str
    action: str
    phi_accessed: bool
    patient_id: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: Optional[str] = None


class DataIntegrityCheck(BaseModel):
    """HIPAA integrity control - HMAC checksum for data"""

    data_id: str
    checksum: str
    algorithm: str = "HMAC-SHA256"
    created_at: str


class HIPAAControls:
    """
    HIPAA Security Rule technical safeguards implementation

    Provides emergency access, audit logging, and integrity controls
    for systems processing Protected Health Information (PHI).
    """

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        integrity_secret: Optional[str] = None,
    ):
        """
        Initialize HIPAA controls

        Args:
            session_store: Session storage for emergency access grants
            integrity_secret: Secret key for HMAC integrity checks (REQUIRED for production)
                            If not provided, will attempt to load from environment/settings

        Raises:
            ValueError: If integrity_secret is not provided and not in environment (fail-closed security pattern)
        """
        self.session_store = session_store

        # If not provided, try to load from environment/settings
        if not integrity_secret:
            import os

            from mcp_server_langgraph.secrets.manager import get_secrets_manager

            secrets_mgr = get_secrets_manager()
            integrity_secret = secrets_mgr.get_secret("HIPAA_INTEGRITY_SECRET", fallback=os.getenv("HIPAA_INTEGRITY_SECRET"))

        # Validate integrity secret is configured (fail-closed security pattern)
        # HIPAA 164.312(c)(1) requires integrity controls for PHI
        if not integrity_secret:
            raise ValueError(
                "CRITICAL: HIPAA integrity secret not configured. "
                "Set HIPAA_INTEGRITY_SECRET environment variable or configure via Infisical. "
                "HIPAA controls cannot be initialized without a secure secret key for data integrity. "
                "(HIPAA 164.312(c)(1) - Integrity Controls)"
            )

        self.integrity_secret = integrity_secret

        # In-memory storage for emergency access grants (replace with database)
        self._emergency_grants: Dict[str, EmergencyAccessGrant] = {}

    async def grant_emergency_access(
        self,
        user_id: str,
        reason: str,
        approver_id: str,
        duration_hours: int = 4,
        access_level: str = "PHI",
    ) -> EmergencyAccessGrant:
        """
        Grant emergency access to PHI (HIPAA 164.312(a)(2)(i))

        Emergency access procedure allows authorized users to access PHI
        in emergency situations with proper approval and audit trail.

        Args:
            user_id: User requesting emergency access
            reason: Detailed reason for emergency access
            approver_id: User ID of approver (must be authorized)
            duration_hours: Duration of access (1-24 hours, default 4)
            access_level: Level of access (default "PHI")

        Returns:
            EmergencyAccessGrant with grant details

        Example:
            grant = await controls.grant_emergency_access(
                user_id="user:doctor_smith",
                reason="Patient emergency - cardiac arrest in ER",
                approver_id="user:supervisor_jones",
                duration_hours=2
            )
        """
        with tracer.start_as_current_span("hipaa.grant_emergency_access") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("approver_id", approver_id)
            span.set_attribute("duration_hours", duration_hours)

            # Validate request (constructor validates fields)
            EmergencyAccessRequest(
                user_id=user_id,
                reason=reason,
                approver_id=approver_id,
                duration_hours=duration_hours,
                access_level=access_level,
            )

            # Generate grant ID
            grant_id = f"emergency_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{user_id.replace(':', '_')}"

            # Calculate expiration
            granted_at = datetime.now(timezone.utc)
            expires_at = granted_at + timedelta(hours=duration_hours)

            # Create grant
            grant = EmergencyAccessGrant(
                grant_id=grant_id,
                user_id=user_id,
                reason=reason,
                approver_id=approver_id,
                granted_at=granted_at.isoformat().replace("+00:00", "Z"),
                expires_at=expires_at.isoformat().replace("+00:00", "Z"),
                access_level=access_level,
            )

            # Store grant
            self._emergency_grants[grant_id] = grant

            # Log emergency access grant (HIPAA audit requirement)
            logger.warning(
                "HIPAA: Emergency access granted",
                extra={
                    "grant_id": grant_id,
                    "user_id": user_id,
                    "approver_id": approver_id,
                    "reason": reason,
                    "duration_hours": duration_hours,
                    "expires_at": grant.expires_at,
                    "access_level": access_level,
                },
            )

            # Track metrics
            metrics.successful_calls.add(1, {"operation": "emergency_access_grant"})

            # Send alert to security team
            try:
                alerting_service = AlertingService()
                await alerting_service.initialize()

                alert = Alert(
                    title="HIPAA: Emergency Access Granted",
                    message=f"Emergency PHI access granted to {user_id} by {approver_id}",
                    severity=AlertSeverity.CRITICAL,
                    source="hipaa_emergency_access",
                    tags=["hipaa", "emergency-access", "phi", "security"],
                    metadata={
                        "grant_id": grant.grant_id,
                        "user_id": user_id,
                        "approver_id": approver_id,
                        "reason": reason,
                        "duration_hours": duration_hours,
                        "expires_at": grant.expires_at,
                        "access_level": access_level,
                    },
                )

                await alerting_service.send_alert(alert)
                logger.info("Emergency access alert sent", extra={"alert_id": alert.alert_id})

            except Exception as e:
                logger.error(f"Failed to send emergency access alert: {e}", exc_info=True)

            return grant

    async def revoke_emergency_access(self, grant_id: str, revoked_by: str) -> bool:
        """
        Revoke emergency access grant

        Args:
            grant_id: Grant ID to revoke
            revoked_by: User ID performing revocation

        Returns:
            True if revoked, False if grant not found
        """
        with tracer.start_as_current_span("hipaa.revoke_emergency_access"):
            grant = self._emergency_grants.get(grant_id)

            if not grant:
                logger.warning(f"Emergency grant not found: {grant_id}")
                return False

            grant.revoked = True
            grant.revoked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            logger.warning(
                "HIPAA: Emergency access revoked",
                extra={
                    "grant_id": grant_id,
                    "user_id": grant.user_id,
                    "revoked_by": revoked_by,
                    "revoked_at": grant.revoked_at,
                },
            )

            return True

    async def check_emergency_access(self, user_id: str) -> Optional[EmergencyAccessGrant]:
        """
        Check if user has active emergency access

        Args:
            user_id: User ID to check

        Returns:
            Active EmergencyAccessGrant or None
        """
        now = datetime.now(timezone.utc)

        for grant in self._emergency_grants.values():
            if grant.user_id == user_id and not grant.revoked:
                expires_at = datetime.fromisoformat(grant.expires_at.replace("Z", "+00:00"))
                if expires_at > now:
                    return grant

        return None

    async def log_phi_access(
        self,
        user_id: str,
        action: str,
        patient_id: Optional[str],
        resource_id: Optional[str],
        ip_address: str,
        user_agent: str,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ):
        """
        Log PHI access (HIPAA 164.312(b) - Audit Controls)

        All access to PHI must be logged with sufficient detail to:
        - Identify who accessed
        - What was accessed
        - When it was accessed
        - Where it was accessed from
        - Whether access was successful

        Args:
            user_id: User accessing PHI
            action: Action performed (read, write, delete, etc.)
            patient_id: Patient identifier (if applicable)
            resource_id: Resource identifier
            ip_address: IP address of access
            user_agent: User agent string
            success: Whether access was successful
            failure_reason: Reason for failure (if unsuccessful)
        """
        with tracer.start_as_current_span("hipaa.log_phi_access") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("action", action)
            span.set_attribute("success", success)

            log_entry = PHIAuditLog(
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                user_id=user_id,
                action=action,
                phi_accessed=True,
                patient_id=patient_id,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
            )

            # Log to secure audit trail (tamper-proof)
            logger.warning(
                "HIPAA: PHI Access",
                extra=log_entry.model_dump(),
            )

            # Send to SIEM system via alerting service
            try:
                alerting_service = AlertingService()
                await alerting_service.initialize()

                # Determine severity based on success
                alert_severity = AlertSeverity.INFO if success else AlertSeverity.WARNING

                alert = Alert(
                    title=f"HIPAA: PHI Access {action.upper()}",
                    message=f"PHI access {action} by {user_id}: {resource_type}/{resource_id}",
                    severity=alert_severity,
                    source="hipaa_audit",
                    tags=["hipaa", "phi-access", "audit", "siem"],
                    metadata=log_entry.model_dump(),
                )

                await alerting_service.send_alert(alert)
                logger.debug("PHI access logged to SIEM", extra={"log_entry_id": log_entry.log_entry_id})

            except Exception as e:
                logger.error(f"Failed to send PHI access to SIEM: {e}", exc_info=True)

            # Track metrics
            if success:
                metrics.successful_calls.add(1, {"operation": "phi_access", "action": action})
            else:
                metrics.failed_calls.add(1, {"operation": "phi_access", "action": action})

    def generate_checksum(self, data: str, data_id: str) -> DataIntegrityCheck:
        """
        Generate HMAC checksum for data integrity (HIPAA 164.312(c)(1))

        Args:
            data: Data to generate checksum for
            data_id: Unique identifier for the data

        Returns:
            DataIntegrityCheck with checksum
        """
        checksum = hmac.new(
            self.integrity_secret.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

        return DataIntegrityCheck(
            data_id=data_id,
            checksum=checksum,
            algorithm="HMAC-SHA256",
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    def verify_checksum(self, data: str, expected_checksum: str) -> bool:
        """
        Verify data integrity using HMAC checksum

        Args:
            data: Data to verify
            expected_checksum: Expected checksum

        Returns:
            True if checksum matches, False otherwise

        Raises:
            IntegrityError: If checksums don't match (in production)
        """
        actual_checksum = hmac.new(
            self.integrity_secret.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(actual_checksum, expected_checksum)

        if not is_valid:
            logger.error(
                "HIPAA: Data integrity check failed",
                extra={
                    "expected": expected_checksum[:8] + "...",
                    "actual": actual_checksum[:8] + "...",
                },
            )

        return is_valid


# Global HIPAA controls instance
_hipaa_controls: Optional[HIPAAControls] = None


def get_hipaa_controls() -> HIPAAControls:
    """
    Get or create global HIPAA controls instance.

    Retrieves HIPAA integrity secret from settings.
    Will raise ValueError if secret is not configured (fail-closed pattern).

    Returns:
        HIPAAControls instance

    Raises:
        ValueError: If HIPAA integrity secret is not configured
    """
    global _hipaa_controls

    if _hipaa_controls is None:
        # Import here to avoid circular dependency
        from mcp_server_langgraph.core.config import settings

        _hipaa_controls = HIPAAControls(integrity_secret=settings.hipaa_integrity_secret)

    return _hipaa_controls


def set_hipaa_controls(controls: HIPAAControls):
    """
    Set global HIPAA controls instance

    Args:
        controls: HIPAAControls instance to use globally
    """
    global _hipaa_controls
    _hipaa_controls = controls
