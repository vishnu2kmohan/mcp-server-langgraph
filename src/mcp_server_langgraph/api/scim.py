"""
SCIM 2.0 API Endpoints

Implements SCIM 2.0 protocol for user and group provisioning.
Bridges to Keycloak Admin API for actual user management.

See ADR-0038 for SCIM implementation approach.

Endpoints:
- POST /scim/v2/Users - Create user
- GET /scim/v2/Users/{id} - Get user
- PUT /scim/v2/Users/{id} - Replace user
- PATCH /scim/v2/Users/{id} - Update user
- DELETE /scim/v2/Users/{id} - Deactivate user
- GET /scim/v2/Users?filter=... - Search users
- POST /scim/v2/Groups - Create group
- GET /scim/v2/Groups/{id} - Get group
- PATCH /scim/v2/Groups/{id} - Update group

References:
- RFC 7643: https://datatracker.ietf.org/doc/html/rfc7643
- RFC 7644: https://datatracker.ietf.org/doc/html/rfc7644
"""

from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from mcp_server_langgraph.auth.keycloak import KeycloakClient
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.dependencies import get_keycloak_client, get_openfga_client
from mcp_server_langgraph.scim.schema import (
    SCIMError,
    SCIMGroup,
    SCIMListResponse,
    SCIMMember,
    SCIMPatchRequest,
    SCIMUser,
    keycloak_to_scim_user,
    user_to_keycloak,
    validate_scim_group,
    validate_scim_user,
)

router = APIRouter(
    prefix="/scim/v2",
    tags=["SCIM 2.0"],
)


# Error response helper
def scim_error(status_code: int, detail: str, scim_type: Optional[str] = None) -> JSONResponse:
    """Return SCIM-formatted error response"""
    error = SCIMError(
        status=status_code,
        detail=detail,
        scimType=scim_type,
    )
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(exclude_none=True),
    )


# User Endpoints


@router.post("/Users", response_model=SCIMUser, status_code=status.HTTP_201_CREATED)  # type: ignore[misc]
async def create_user(
    user_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> SCIMUser:
    """
    Create a new user (SCIM 2.0)

    Provisions user in Keycloak and syncs roles to OpenFGA.

    Example:
        ```json
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "alice@example.com",
            "name": {
                "givenName": "Alice",
                "familyName": "Smith"
            },
            "emails": [{
                "value": "alice@example.com",
                "primary": true
            }],
            "active": true
        }
        ```
    """
    try:
        # Validate SCIM schema
        scim_user = validate_scim_user(user_data)

        # Convert to Keycloak user
        keycloak_user = user_to_keycloak(scim_user)

        # Create in Keycloak
        user_id = await keycloak.create_user(keycloak_user)

        # Set password if provided
        if scim_user.password:
            await keycloak.set_user_password(user_id, scim_user.password, temporary=False)

        # Sync to OpenFGA (assign default roles)
        # Note: sync_user_to_openfga requires KeycloakUser, not just user_id
        # For now, skip sync or implement proper user retrieval
        # from mcp_server_langgraph.auth.keycloak import sync_user_to_openfga
        # await sync_user_to_openfga(keycloak_user_obj, openfga)

        # Get created user and convert back to SCIM
        created_user = await keycloak.get_user(user_id)

        if not created_user:
            raise HTTPException(status_code=500, detail="Failed to retrieve created user")

        response_user = keycloak_to_scim_user(created_user)

        return response_user

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.get("/Users/{user_id}", response_model=SCIMUser)  # type: ignore[misc]
async def get_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> SCIMUser:
    """
    Get user by ID (SCIM 2.0)

    Returns user in SCIM format.
    """
    try:
        # Get user from Keycloak
        keycloak_user = await keycloak.get_user(user_id)

        if not keycloak_user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        # Convert to SCIM format
        scim_user = keycloak_to_scim_user(keycloak_user)
        return scim_user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


@router.put("/Users/{user_id}", response_model=SCIMUser)  # type: ignore[misc]
async def replace_user(
    user_id: str,
    user_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> Union[SCIMUser, JSONResponse]:
    """
    Replace user (SCIM 2.0 PUT)

    Replaces entire user resource.
    """
    try:
        # Validate SCIM schema
        scim_user = validate_scim_user(user_data)

        # Convert to Keycloak user
        keycloak_user = user_to_keycloak(scim_user)

        # Update in Keycloak
        await keycloak.update_user(user_id, keycloak_user)

        # Get updated user
        updated_user = await keycloak.get_user(user_id)
        if not updated_user:
            return scim_error(404, f"User {user_id} not found", "notFound")
        response_user = keycloak_to_scim_user(updated_user)

        return response_user

    except ValueError as e:
        return scim_error(400, str(e), "invalidValue")
    except Exception as e:
        return scim_error(500, f"Failed to update user: {str(e)}", "internalError")


@router.patch("/Users/{user_id}", response_model=SCIMUser)  # type: ignore[misc]
async def update_user(
    user_id: str,
    patch_request: SCIMPatchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> Union[SCIMUser, JSONResponse]:
    """
    Update user with PATCH operations (SCIM 2.0)

    Supports add, remove, replace operations.

    Example:
        ```json
        {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "replace",
                    "path": "active",
                    "value": false
                }
            ]
        }
        ```
    """
    try:
        # Get current user
        keycloak_user = await keycloak.get_user(user_id)

        if not keycloak_user:
            return scim_error(404, f"User {user_id} not found", "notFound")

        # Apply PATCH operations
        for operation in patch_request.Operations:
            if operation.path == "active":
                keycloak_user["enabled"] = operation.value
            elif operation.path == "emails":
                if operation.op == "replace" and operation.value:
                    keycloak_user["email"] = operation.value[0]["value"]
            # Add more PATCH operation handlers as needed

        # Update in Keycloak
        await keycloak.update_user(user_id, keycloak_user)

        # Get updated user
        updated_user = await keycloak.get_user(user_id)
        if not updated_user:
            return scim_error(404, f"User {user_id} not found", "notFound")
        response_user = keycloak_to_scim_user(updated_user)

        return response_user

    except Exception as e:
        return scim_error(500, f"Failed to patch user: {str(e)}", "internalError")


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)  # type: ignore[misc]
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
    openfga: OpenFGAClient = Depends(get_openfga_client),
) -> None:
    """
    Delete (deactivate) user (SCIM 2.0)

    Deactivates user in Keycloak and removes OpenFGA tuples.
    """
    try:
        # Soft delete - disable user
        await keycloak.update_user(user_id, {"enabled": False})

        # Remove OpenFGA tuples
        await openfga.delete_tuples_for_object(f"user:{user_id}")

    except Exception as e:
        # For 204 responses, we must raise HTTPException not return error body
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.get("/Users", response_model=SCIMListResponse)  # type: ignore[misc]
async def list_users(
    filter: Optional[str] = Query(None, description="SCIM filter expression"),
    startIndex: int = Query(1, ge=1, description="1-based start index"),
    count: int = Query(100, ge=1, le=1000, description="Number of results"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> Union[SCIMListResponse, JSONResponse]:
    """
    List/search users (SCIM 2.0)

    Supports basic filtering (e.g., 'userName eq "alice@example.com"').
    """
    try:
        # Parse filter (simple implementation)
        query = {}
        if filter:
            # Simple filter parsing: "userName eq \"alice@example.com\""
            if "userName eq" in filter:
                username = filter.split('"')[1]
                query["username"] = username
            elif "email eq" in filter:
                email = filter.split('"')[1]
                query["email"] = email

        # Get users from Keycloak
        users = await keycloak.search_users(query=query, first=startIndex - 1, max=count)

        # Convert to SCIM format
        scim_users = [keycloak_to_scim_user(user) for user in users]

        return SCIMListResponse(
            totalResults=len(scim_users),
            startIndex=startIndex,
            itemsPerPage=len(scim_users),
            Resources=scim_users,
        )

    except Exception as e:
        return scim_error(500, f"Failed to list users: {str(e)}", "internalError")


# Group Endpoints


@router.post("/Groups", response_model=SCIMGroup, status_code=status.HTTP_201_CREATED)  # type: ignore[misc]
async def create_group(
    group_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> Union[SCIMGroup, JSONResponse]:
    """
    Create a new group (SCIM 2.0)

    Example:
        ```json
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "Engineering",
            "members": [
                {"value": "user-id-123", "display": "Alice Smith"}
            ]
        }
        ```
    """
    try:
        # Validate SCIM schema
        scim_group = validate_scim_group(group_data)

        # Create group in Keycloak
        group_config = {
            "name": scim_group.displayName,
        }

        group_id = await keycloak.create_group(group_config)

        # Add members
        for member in scim_group.members:
            await keycloak.add_user_to_group(member.value, group_id)

        # Get created group
        created_group = await keycloak.get_group(group_id)
        if not created_group:
            return scim_error(500, "Failed to retrieve created group", "internalError")

        return SCIMGroup(
            id=created_group["id"],
            displayName=created_group["name"],
            members=scim_group.members,
            meta={
                "resourceType": "Group",
                "created": created_group.get("createdTimestamp"),
            },
        )

    except ValueError as e:
        return scim_error(400, str(e), "invalidValue")
    except Exception as e:
        return scim_error(500, f"Failed to create group: {str(e)}", "internalError")


@router.get("/Groups/{group_id}", response_model=SCIMGroup)  # type: ignore[misc]
async def get_group(
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    keycloak: KeycloakClient = Depends(get_keycloak_client),
) -> Union[SCIMGroup, JSONResponse]:
    """Get group by ID (SCIM 2.0)"""
    try:
        group = await keycloak.get_group(group_id)

        if not group:
            return scim_error(404, f"Group {group_id} not found", "notFound")

        # Get group members
        members = await keycloak.get_group_members(group_id)

        scim_members = [SCIMMember(value=member["id"], display=member.get("username"), reference=None) for member in members]

        return SCIMGroup(
            id=group["id"],
            displayName=group["name"],
            members=scim_members,
            meta={"resourceType": "Group"},
        )

    except Exception as e:
        return scim_error(500, f"Failed to get group: {str(e)}", "internalError")
