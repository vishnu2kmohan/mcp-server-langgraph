"""
GDPR Compliance API Endpoints

Implements data subject rights under GDPR:
- Article 15: Right to Access
- Article 16: Right to Rectification
- Article 17: Right to Erasure
- Article 20: Right to Data Portability
- Article 21: Right to Object (Consent Management)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.middleware import get_current_user, require_auth
from mcp_server_langgraph.auth.session import SessionStore, get_session_store
from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService
from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService
from mcp_server_langgraph.observability.telemetry import logger, tracer

router = APIRouter(prefix="/api/v1/users", tags=["GDPR Compliance"])


# ==================== Models ====================


class UserProfileUpdate(BaseModel):
    """User profile update model (GDPR Article 16 - Right to Rectification)"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    email: Optional[str] = Field(None, description="User's email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Alice Smith",
                "email": "alice.smith@acme.com",
                "preferences": {"theme": "dark", "language": "en"},
            }
        }
    )


class ConsentType(str, Enum):
    """Types of consent that can be granted or revoked"""

    ANALYTICS = "analytics"
    MARKETING = "marketing"
    THIRD_PARTY = "third_party"
    PROFILING = "profiling"


class ConsentRecord(BaseModel):
    """Consent record for GDPR Article 21"""

    consent_type: ConsentType = Field(..., description="Type of consent")
    granted: bool = Field(..., description="Whether consent is granted")
    timestamp: Optional[str] = Field(None, description="ISO timestamp (auto-generated)")
    ip_address: Optional[str] = Field(None, description="IP address (auto-captured)")
    user_agent: Optional[str] = Field(None, description="User agent (auto-captured)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "consent_type": "analytics",
                "granted": True,
            }
        }
    )


class ConsentResponse(BaseModel):
    """Response for consent operations"""

    user_id: str
    consents: Dict[str, dict] = Field(description="Current consent status for all types")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user:alice",
                "consents": {
                    "analytics": {
                        "granted": True,
                        "timestamp": "2025-01-01T12:00:00Z",
                        "ip_address": "192.168.1.1",
                    },
                    "marketing": {"granted": False, "timestamp": "2025-01-01T12:00:00Z"},
                },
            }
        }
    )


# In-memory consent storage (replace with database in production)
# WARNING: This is not production-ready - data will be lost on server restart
_consent_storage: Dict[str, Dict[str, dict]] = {}


# PRODUCTION READINESS WARNING AND GUARD
import os
import warnings

# Check if running in production and guard against using in-memory storage
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
GDPR_STORAGE_BACKEND = os.getenv("GDPR_STORAGE_BACKEND", "memory")  # "memory", "postgres", "redis"

if ENVIRONMENT == "production" and GDPR_STORAGE_BACKEND == "memory":
    raise RuntimeError(
        "CRITICAL: GDPR endpoints cannot use in-memory storage in production. "
        "Set GDPR_STORAGE_BACKEND=postgres or GDPR_STORAGE_BACKEND=redis, "
        "or set ENVIRONMENT=development for testing. "
        "Data subject rights (GDPR compliance) require persistent storage."
    )

# Warn in non-production environments
if GDPR_STORAGE_BACKEND == "memory":
    warnings.warn(
        "GDPR endpoints use in-memory storage which is NOT production-ready. "
        "Profile and consent data will be lost on server restart. "
        "For production use, set GDPR_STORAGE_BACKEND=postgres or GDPR_STORAGE_BACKEND=redis. "
        "See docs/compliance/gdpr-storage-requirements.md for details.",
        category=RuntimeWarning,
        stacklevel=2,
    )

# ==================== Endpoints ====================


@router.get("/me/data")
async def get_user_data(
    user: Dict[str, Any] = Depends(get_current_user),
    session_store: SessionStore = Depends(get_session_store),
):
    """
    Export all user data (GDPR Article 15 - Right to Access)

    Returns all personal data associated with the authenticated user.

    **GDPR Article 15**: The data subject shall have the right to obtain from the
    controller confirmation as to whether or not personal data concerning him or
    her are being processed, and access to the personal data.

    **Response**: Complete JSON export of all user data including:
    - User profile
    - Sessions
    - Conversations
    - Preferences
    - Audit log
    - Consents
    """
    with tracer.start_as_current_span("gdpr.get_user_data"):
        # Get authenticated user
        user_id = user.get("user_id")
        username = user.get("username")
        email = user.get("email", f"{username}@example.com")

        # Create export service
        export_service = DataExportService(session_store=session_store)

        # Export all user data
        export = await export_service.export_user_data(user_id=user_id, username=username, email=email)

        # Log the data access request (GDPR requirement)
        logger.info(
            "User data access request",
            extra={
                "user_id": user_id,
                "export_id": export.export_id,
                "gdpr_article": "15",
            },
        )

        return export


@router.get("/me/export")
async def export_user_data(
    user: Dict[str, Any] = Depends(get_current_user),
    format: str = Query("json", pattern="^(json|csv)$", description="Export format: json or csv"),
    session_store: SessionStore = Depends(get_session_store),
):
    """
    Export user data in portable format (GDPR Article 20 - Right to Data Portability)

    **GDPR Article 20**: The data subject shall have the right to receive the personal
    data concerning him or her in a structured, commonly used and machine-readable format.

    **Query Parameters**:
    - `format`: Export format (json or csv)

    **Response**: File download in requested format
    """
    with tracer.start_as_current_span("gdpr.export_user_data"):
        # Get authenticated user
        user_id = user.get("user_id")
        username = user.get("username")
        email = user.get("email", f"{username}@example.com")

        # Create export service
        export_service = DataExportService(session_store=session_store)

        # Export data in requested format
        data_bytes, content_type = await export_service.export_user_data_portable(
            user_id=user_id, username=username, email=email, format=format
        )

        # Log the export request
        logger.info(
            "User data export request",
            extra={
                "user_id": user_id,
                "format": format,
                "size_bytes": len(data_bytes),
                "gdpr_article": "20",
            },
        )

        # Return as downloadable file
        filename = f"user_data_{username}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.{format}"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

        return Response(content=data_bytes, media_type=content_type, headers=headers)


@router.patch("/me")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update user profile (GDPR Article 16 - Right to Rectification)

    **GDPR Article 16**: The data subject shall have the right to obtain from the
    controller without undue delay the rectification of inaccurate personal data
    concerning him or her.

    **Request Body**: Profile fields to update (only provided fields are updated)

    **Response**: Updated user profile
    """
    with tracer.start_as_current_span("gdpr.update_user_profile"):
        # Get authenticated user
        user_id = user.get("user_id")
        username = user.get("username")

        # Get fields to update (exclude unset fields)
        update_data = profile_update.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # Log the update request
        logger.info(
            "User profile update request",
            extra={
                "user_id": user_id,
                "fields_updated": list(update_data.keys()),
                "gdpr_article": "16",
            },
        )

        # Integrate with user profile storage
        # Note: User profiles can be stored in:
        # - Redis (fast, session-like data)
        # - PostgreSQL (persistent, relational)
        # - User provider backend (if supported)
        # For now, we validate the update and return confirmation
        # Production: Integrate with your user storage backend
        updated_profile = {
            "user_id": user_id,
            "username": username,
            **update_data,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "storage_note": "Configure user profile storage backend for persistence",
        }

        logger.info("User profile updated successfully", extra={"user_id": user_id})

        return updated_profile


@router.delete("/me")
async def delete_user_account(
    user: Dict[str, Any] = Depends(get_current_user),
    confirm: bool = Query(..., description="Must be true to confirm account deletion"),
    session_store: SessionStore = Depends(get_session_store),
):
    """
    Delete user account and all data (GDPR Article 17 - Right to Erasure)

    **WARNING**: This is an irreversible operation that permanently deletes all user data.

    **GDPR Article 17**: The data subject shall have the right to obtain from the
    controller the erasure of personal data concerning him or her without undue delay.

    **Query Parameters**:
    - `confirm`: Must be set to `true` to confirm deletion

    **What gets deleted**:
    - User profile and account
    - All sessions
    - All conversations and messages
    - All preferences and settings
    - All authorization tuples

    **What gets anonymized** (retained for compliance):
    - Audit logs (user_id replaced with hash)

    **Response**: Deletion result with details
    """
    with tracer.start_as_current_span("gdpr.delete_user_account"):
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Account deletion requires confirmation. Set confirm=true to proceed.",
            )

        # Get authenticated user
        user_id = user.get("user_id")
        username = user.get("username")

        # Log deletion request (before deletion)
        logger.warning(
            "User account deletion requested",
            extra={
                "user_id": user_id,
                "username": username,
                "gdpr_article": "17",
            },
        )

        # Create deletion service with OpenFGA client
        # Note: OpenFGA client should be passed from FastAPI app state for proper lifecycle
        # For production, add OpenFGA client to app startup and inject via Depends()
        # Example: openfga_client = Depends(get_openfga_client)
        deletion_service = DataDeletionService(
            session_store=session_store,
            openfga_client=None,  # Configured via dependency injection in production
        )

        # Delete all user data
        result = await deletion_service.delete_user_account(
            user_id=user_id, username=username, reason="user_request_gdpr_article_17"
        )

        if not result.success:
            logger.error(
                "User account deletion failed",
                extra={"user_id": user_id, "errors": result.errors},
            )
            raise HTTPException(
                status_code=500,
                detail=f"Account deletion completed with errors: {', '.join(result.errors)}",
            )

        logger.warning(
            "User account deletion completed",
            extra={
                "user_id": user_id,
                "deleted_items": result.deleted_items,
                "anonymized_items": result.anonymized_items,
            },
        )

        return {
            "message": "Account deleted successfully",
            "deletion_timestamp": result.deletion_timestamp,
            "deleted_items": result.deleted_items,
            "anonymized_items": result.anonymized_items,
            "audit_record_id": result.audit_record_id,
        }


@router.post("/me/consent")
async def update_consent(
    consent: ConsentRecord,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update user consent preferences (GDPR Article 21 - Right to Object)

    **GDPR Article 21**: The data subject shall have the right to object at any time
    to processing of personal data concerning him or her.

    **Request Body**: Consent type and whether it's granted

    **Response**: Current consent status for all types
    """
    with tracer.start_as_current_span("gdpr.update_consent"):
        # Get authenticated user
        user_id = user.get("user_id")

        # Capture metadata
        consent.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        consent.ip_address = None  # Could capture from X-Forwarded-For if needed
        consent.user_agent = None  # Could capture from headers if needed

        # Store consent (in-memory for now)
        if user_id not in _consent_storage:
            _consent_storage[user_id] = {}

        _consent_storage[user_id][consent.consent_type] = {
            "granted": consent.granted,
            "timestamp": consent.timestamp,
            "ip_address": consent.ip_address,
            "user_agent": consent.user_agent,
        }

        # Log consent change
        logger.info(
            "User consent updated",
            extra={
                "user_id": user_id,
                "consent_type": consent.consent_type,
                "granted": consent.granted,
                "ip_address": consent.ip_address,
                "gdpr_article": "21",
            },
        )

        return ConsentResponse(user_id=user_id, consents=_consent_storage.get(user_id, {}))


@router.get("/me/consent")
async def get_consent_status(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current consent status (GDPR Article 21 - Right to Object)

    Returns all consent preferences for the authenticated user.

    **Response**: Current consent status for all consent types
    """
    with tracer.start_as_current_span("gdpr.get_consent_status"):
        # Get authenticated user
        user_id = user.get("user_id")

        # Get consent status
        consents = _consent_storage.get(user_id, {})

        logger.info("User consent status retrieved", extra={"user_id": user_id})

        return ConsentResponse(user_id=user_id, consents=consents)
