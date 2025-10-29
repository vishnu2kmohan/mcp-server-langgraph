"""
Service Principal API Endpoints

REST API for managing service principals including creation, listing,
secret rotation, and deletion.

See ADR-0033 for service principal design decisions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.service_principal import (
    ServicePrincipal,
    ServicePrincipalManager,
)
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.core.dependencies import (
    get_service_principal_manager,
)


router = APIRouter(
    prefix="/api/v1/service-principals",
    tags=["Service Principals"],
)


# Request/Response Models


class CreateServicePrincipalRequest(BaseModel):
    """Request to create a new service principal"""

    name: str = Field(..., description="Human-readable name for the service")
    description: str = Field(..., description="Purpose/description of the service")
    authentication_mode: str = Field(
        default="client_credentials",
        description="Authentication mode: 'client_credentials' or 'service_account_user'",
    )
    associated_user_id: Optional[str] = Field(
        None, description="User to act as for permission inheritance (e.g., 'user:alice')"
    )
    inherit_permissions: bool = Field(
        default=False, description="Whether to inherit permissions from associated user"
    )


class ServicePrincipalResponse(BaseModel):
    """Response containing service principal details"""

    service_id: str
    name: str
    description: str
    authentication_mode: str
    associated_user_id: Optional[str]
    owner_user_id: Optional[str]
    inherit_permissions: bool
    enabled: bool
    created_at: Optional[str]


class CreateServicePrincipalResponse(ServicePrincipalResponse):
    """Response when creating service principal (includes secret)"""

    client_secret: str = Field(
        ..., description="Client secret (save securely, won't be shown again)"
    )
    message: str = Field(
        default="Service principal created successfully. Save the client_secret securely."
    )


class RotateSecretResponse(BaseModel):
    """Response when rotating service principal secret"""

    service_id: str
    client_secret: str = Field(..., description="New client secret")
    message: str = Field(
        default="Secret rotated successfully. Update your service configuration."
    )


# API Endpoints


@router.post("/", response_model=CreateServicePrincipalResponse, status_code=status.HTTP_201_CREATED)
async def create_service_principal(
    request: CreateServicePrincipalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> CreateServicePrincipalResponse:
    """
    Create a new service principal

    Creates a service principal with the specified authentication mode.
    The calling user becomes the owner of the service principal.

    Returns the created service principal with credentials (client_secret).
    **Save the client_secret securely** - it will not be shown again.

    Example:
        ```json
        {
            "name": "Batch ETL Job",
            "description": "Nightly data processing",
            "authentication_mode": "client_credentials",
            "associated_user_id": "user:alice",
            "inherit_permissions": true
        }
        ```
    """
    # Validate authentication mode
    if request.authentication_mode not in ["client_credentials", "service_account_user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication_mode. Must be 'client_credentials' or 'service_account_user'",
        )

    # Generate service ID from name
    service_id = request.name.lower().replace(" ", "-").replace("_", "-")

    # Validate service ID doesn't already exist
    existing = await sp_manager.get_service_principal(service_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service principal with ID '{service_id}' already exists",
        )

    # Create service principal
    sp = await sp_manager.create_service_principal(
        service_id=service_id,
        name=request.name,
        description=request.description,
        authentication_mode=request.authentication_mode,
        associated_user_id=request.associated_user_id,
        owner_user_id=current_user["user_id"],
        inherit_permissions=request.inherit_permissions,
    )

    return CreateServicePrincipalResponse(
        service_id=sp.service_id,
        name=sp.name,
        description=sp.description,
        authentication_mode=sp.authentication_mode,
        associated_user_id=sp.associated_user_id,
        owner_user_id=sp.owner_user_id,
        inherit_permissions=sp.inherit_permissions,
        enabled=sp.enabled,
        created_at=sp.created_at,
        client_secret=sp.client_secret,
    )


@router.get("/", response_model=List[ServicePrincipalResponse])
async def list_service_principals(
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> List[ServicePrincipalResponse]:
    """
    List service principals owned by the current user

    Returns all service principals where the current user is the owner.
    Does not include client secrets.
    """
    sps = await sp_manager.list_service_principals(owner_user_id=current_user["user_id"])

    return [
        ServicePrincipalResponse(
            service_id=sp.service_id,
            name=sp.name,
            description=sp.description,
            authentication_mode=sp.authentication_mode,
            associated_user_id=sp.associated_user_id,
            owner_user_id=sp.owner_user_id,
            inherit_permissions=sp.inherit_permissions,
            enabled=sp.enabled,
            created_at=sp.created_at,
        )
        for sp in sps
    ]


@router.get("/{service_id}", response_model=ServicePrincipalResponse)
async def get_service_principal(
    service_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> ServicePrincipalResponse:
    """
    Get details of a specific service principal

    Returns service principal details if the current user is the owner.
    """
    sp = await sp_manager.get_service_principal(service_id)

    if not sp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service principal '{service_id}' not found",
        )

    # Verify ownership
    if sp.owner_user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this service principal",
        )

    return ServicePrincipalResponse(
        service_id=sp.service_id,
        name=sp.name,
        description=sp.description,
        authentication_mode=sp.authentication_mode,
        associated_user_id=sp.associated_user_id,
        owner_user_id=sp.owner_user_id,
        inherit_permissions=sp.inherit_permissions,
        enabled=sp.enabled,
        created_at=sp.created_at,
    )


@router.post("/{service_id}/rotate-secret", response_model=RotateSecretResponse)
async def rotate_service_principal_secret(
    service_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> RotateSecretResponse:
    """
    Rotate service principal secret

    Generates a new client secret for the service principal.
    The old secret will be invalidated immediately.

    **Save the new client_secret securely** - update your service configuration
    before the old secret expires.
    """
    # Get service principal
    sp = await sp_manager.get_service_principal(service_id)

    if not sp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service principal '{service_id}' not found",
        )

    # Verify ownership
    if sp.owner_user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to rotate this service principal's secret",
        )

    # Rotate secret
    new_secret = await sp_manager.rotate_secret(service_id)

    return RotateSecretResponse(
        service_id=service_id,
        client_secret=new_secret,
    )


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_principal(
    service_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> None:
    """
    Delete a service principal

    Permanently deletes the service principal from Keycloak and OpenFGA.
    This action cannot be undone.
    """
    # Get service principal
    sp = await sp_manager.get_service_principal(service_id)

    if not sp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service principal '{service_id}' not found",
        )

    # Verify ownership
    if sp.owner_user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this service principal",
        )

    # Delete service principal
    await sp_manager.delete_service_principal(service_id)

    return None


@router.post("/{service_id}/associate-user", response_model=ServicePrincipalResponse)
async def associate_service_principal_with_user(
    service_id: str,
    user_id: str,
    inherit_permissions: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user),
    sp_manager: ServicePrincipalManager = Depends(get_service_principal_manager),
) -> ServicePrincipalResponse:
    """
    Associate service principal with a user for permission inheritance

    Links a service principal to a user, optionally enabling permission inheritance.
    When inherit_permissions is true, the service principal can act on behalf of
    the user and inherit all their permissions.
    """
    # Get service principal
    sp = await sp_manager.get_service_principal(service_id)

    if not sp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service principal '{service_id}' not found",
        )

    # Verify ownership
    if sp.owner_user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this service principal",
        )

    # Associate with user
    await sp_manager.associate_with_user(
        service_id=service_id,
        user_id=user_id,
        inherit_permissions=inherit_permissions,
    )

    # Return updated service principal
    updated_sp = await sp_manager.get_service_principal(service_id)

    if not updated_sp:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated service principal",
        )

    return ServicePrincipalResponse(
        service_id=updated_sp.service_id,
        name=updated_sp.name,
        description=updated_sp.description,
        authentication_mode=updated_sp.authentication_mode,
        associated_user_id=updated_sp.associated_user_id,
        owner_user_id=updated_sp.owner_user_id,
        inherit_permissions=updated_sp.inherit_permissions,
        enabled=updated_sp.enabled,
        created_at=updated_sp.created_at,
    )
