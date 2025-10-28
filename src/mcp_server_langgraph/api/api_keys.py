"""
API Key Management Endpoints

REST API for managing API keys including creation, listing, rotation, and revocation.
Also provides validation endpoint for Kong API key→JWT exchange.

See ADR-0034 for API key to JWT exchange pattern.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.api_keys import APIKeyManager
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.auth.keycloak import KeycloakClient
from mcp_server_langgraph.core.dependencies import (
    get_keycloak_client,
    get_api_key_manager,
)


router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["API Keys"],
)


# Request/Response Models


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""

    name: str = Field(..., description="Human-readable name for the API key")
    expires_days: int = Field(
        default=365, description="Days until expiration (default: 365)"
    )


class APIKeyResponse(BaseModel):
    """Response containing API key metadata"""

    key_id: str
    name: str
    created: str
    expires_at: str
    last_used: Optional[str] = None


class CreateAPIKeyResponse(APIKeyResponse):
    """Response when creating API key (includes the key itself)"""

    api_key: str = Field(..., description="API key (save securely, won't be shown again)")
    message: str = Field(
        default="API key created successfully. Save it securely - it will not be shown again."
    )


class RotateAPIKeyResponse(BaseModel):
    """Response when rotating API key"""

    key_id: str
    new_api_key: str = Field(..., description="New API key")
    message: str = Field(
        default="API key rotated successfully. Update your client configuration."
    )


class ValidateAPIKeyResponse(BaseModel):
    """Response when validating API key (for Kong plugin)"""

    access_token: str = Field(..., description="JWT access token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user_id: str
    username: str


# User-Facing API Endpoints


@router.post("/", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
):
    """
    Create a new API key for the current user

    Creates a cryptographically secure API key with bcrypt hashing.
    **Save the returned api_key securely** - it will not be shown again.

    Maximum 5 keys per user. Revoke an existing key before creating more.

    Example:
        ```json
        {
            "name": "Production API Key",
            "expires_days": 365
        }
        ```
    """
    try:
        result = await api_key_manager.create_api_key(
            user_id=current_user["user_id"],
            name=request.name,
            expires_days=request.expires_days,
        )

        return CreateAPIKeyResponse(
            key_id=result["key_id"],
            api_key=result["api_key"],
            name=result["name"],
            created=result.get("created", ""),
            expires_at=result["expires_at"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
):
    """
    List all API keys for the current user

    Returns metadata for all keys (name, created, expires, last_used).
    Does not include the actual API keys.
    """
    keys = await api_key_manager.list_api_keys(current_user["user_id"])

    return [
        APIKeyResponse(
            key_id=key["key_id"],
            name=key["name"],
            created=key["created"],
            expires_at=key["expires_at"],
            last_used=key.get("last_used"),
        )
        for key in keys
    ]


@router.post("/{key_id}/rotate", response_model=RotateAPIKeyResponse)
async def rotate_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
):
    """
    Rotate an API key

    Generates a new API key while keeping the same key_id.
    The old key is invalidated immediately.

    **Save the new_api_key securely** - update your client configuration.
    """
    try:
        result = await api_key_manager.rotate_api_key(
            user_id=current_user["user_id"],
            key_id=key_id,
        )

        return RotateAPIKeyResponse(
            key_id=result["key_id"],
            new_api_key=result["new_api_key"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
):
    """
    Revoke an API key

    Permanently deletes the API key. This action cannot be undone.
    Any clients using this key will immediately lose access.
    """
    await api_key_manager.revoke_api_key(
        user_id=current_user["user_id"],
        key_id=key_id,
    )

    return None


# Internal Endpoint for Kong Plugin


@router.post("/validate", response_model=ValidateAPIKeyResponse, include_in_schema=False)
async def validate_api_key(
    api_key: str = Header(None, alias="X-API-Key"),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
):
    """
    Validate API key and return JWT (internal endpoint for Kong plugin)

    This endpoint is called by the Kong API key→JWT exchange plugin.
    It validates the API key and issues a JWT for the associated user.

    **This endpoint is not intended for direct client use.**
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-API-Key header",
        )

    # Validate API key
    user_info = await api_key_manager.validate_and_get_user(api_key)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    # Issue JWT for this user
    try:
        # Exchange for JWT using Keycloak
        # This simulates a user login to get a JWT
        token_response = await keycloak.issue_token_for_user(user_info["user_id"])

        return ValidateAPIKeyResponse(
            access_token=token_response["access_token"],
            expires_in=token_response.get("expires_in", 900),  # Default 15 min
            user_id=user_info["user_id"],
            username=user_info["username"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to issue JWT: {str(e)}",
        )
