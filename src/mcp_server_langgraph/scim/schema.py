"""
SCIM 2.0 Schema Validation

Implements SCIM 2.0 schema validation according to RFC 7643.
Validates User and Group resources against SCIM Core Schema and Enterprise Extension.

See ADR-0038 for SCIM implementation approach.

References:
- RFC 7643: SCIM Core Schema
- RFC 7644: SCIM Protocol
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# SCIM Schema URNs
SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


class SCIMEmail(BaseModel):
    """SCIM email address"""

    value: str
    type: str | None = "work"  # work, home, other
    primary: bool = False


class SCIMName(BaseModel):
    """SCIM user name"""

    formatted: str | None = None
    familyName: str | None = None
    givenName: str | None = None
    middleName: str | None = None
    honorificPrefix: str | None = None
    honorificSuffix: str | None = None


class SCIMPhoneNumber(BaseModel):
    """SCIM phone number"""

    value: str
    type: str | None = "work"
    primary: bool = False


class SCIMAddress(BaseModel):
    """SCIM address"""

    formatted: str | None = None
    streetAddress: str | None = None
    locality: str | None = None
    region: str | None = None
    postalCode: str | None = None
    country: str | None = None
    type: str | None = "work"
    primary: bool = False


class SCIMGroupMembership(BaseModel):
    """SCIM group membership"""

    model_config = ConfigDict(
        populate_by_name=True,
        # Fix JSON schema to avoid $ref conflicts
        json_schema_extra=lambda schema, _model: schema.update(
            {"properties": {k if k != "$ref" else "ref": v for k, v in schema.get("properties", {}).items()}}
        ),
    )

    value: str  # Group ID
    # Use 'reference' as field name, serialize as '$ref' for SCIM compliance
    reference: str | None = Field(None, serialization_alias="$ref", validation_alias="$ref")
    display: str | None = None
    type: str | None = "direct"


class SCIMEnterpriseUser(BaseModel):
    """SCIM Enterprise User Extension (RFC 7643 Section 4.3)"""

    employeeNumber: str | None = None
    costCenter: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: dict[str, str] | None = None  # {value: manager_id, ref: url, displayName: name}


class SCIMUser(BaseModel):
    """
    SCIM 2.0 User Resource

    Core schema with optional Enterprise extension.
    """

    schemas: list[str] = Field(default=[SCIM_USER_SCHEMA])
    id: str | None = None
    externalId: str | None = None
    userName: str
    name: SCIMName | None = None
    displayName: str | None = None
    nickName: str | None = None
    profileUrl: str | None = None
    title: str | None = None
    userType: str | None = None
    preferredLanguage: str | None = None
    locale: str | None = None
    timezone: str | None = None
    active: bool = True
    password: str | None = None
    emails: list[SCIMEmail] = []
    phoneNumbers: list[SCIMPhoneNumber] = []
    addresses: list[SCIMAddress] = []
    groups: list[SCIMGroupMembership] = []

    # Meta
    meta: dict[str, Any] | None = None

    # Enterprise extension
    enterpriseUser: SCIMEnterpriseUser | None = Field(None, alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User")

    @field_validator("schemas")
    @classmethod
    def validate_schemas(cls, v: list[str]) -> list[str]:
        """Validate that required schemas are present"""
        if SCIM_USER_SCHEMA not in v:
            raise ValueError(f"Missing required schema: {SCIM_USER_SCHEMA}")
        return v

    @field_validator("emails")
    @classmethod
    def validate_primary_email(cls, v: list[SCIMEmail]) -> list[SCIMEmail]:
        """Ensure at most one primary email"""
        primary_count = sum(1 for email in v if email.primary)
        if primary_count > 1:
            raise ValueError("Only one email can be marked as primary")
        return v


class SCIMMember(BaseModel):
    """SCIM group member"""

    model_config = ConfigDict(
        populate_by_name=True,
        # Fix JSON schema to avoid $ref conflicts
        json_schema_extra=lambda schema, _model: schema.update(
            {"properties": {k if k != "$ref" else "ref": v for k, v in schema.get("properties", {}).items()}}
        ),
    )

    value: str  # User ID
    # Use 'reference' as field name, serialize as '$ref' for SCIM compliance
    reference: str | None = Field(None, serialization_alias="$ref", validation_alias="$ref")
    display: str | None = None
    type: str | None = "User"


class SCIMGroup(BaseModel):
    """SCIM 2.0 Group Resource"""

    schemas: list[str] = Field(default=[SCIM_GROUP_SCHEMA])
    id: str | None = None
    displayName: str
    members: list[SCIMMember] = []
    meta: dict[str, Any] | None = None

    @field_validator("schemas")
    @classmethod
    def validate_schemas(cls, v: list[str]) -> list[str]:
        """Validate that required schemas are present"""
        if SCIM_GROUP_SCHEMA not in v:
            raise ValueError(f"Missing required schema: {SCIM_GROUP_SCHEMA}")
        return v


class SCIMPatchOp(str, Enum):
    """SCIM PATCH operation types"""

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


class SCIMPatchOperation(BaseModel):
    """SCIM PATCH operation"""

    op: SCIMPatchOp
    path: str | None = None
    value: Any = None


class SCIMPatchRequest(BaseModel):
    """SCIM PATCH request"""

    schemas: list[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"])
    Operations: list[SCIMPatchOperation]


class SCIMListResponse(BaseModel):
    """SCIM List Response"""

    schemas: list[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: list[Any]  # Can be Users or Groups


class SCIMError(BaseModel):
    """SCIM Error Response"""

    schemas: list[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:Error"])
    status: int
    scimType: str | None = None
    detail: str | None = None


def validate_scim_user(data: dict[str, Any]) -> SCIMUser:
    """
    Validate SCIM user data

    Args:
        data: Raw user data

    Returns:
        Validated SCIMUser object

    Raises:
        ValueError: If validation fails
    """
    try:
        return SCIMUser(**data)
    except Exception as e:
        raise ValueError(f"Invalid SCIM user data: {str(e)}") from e


def validate_scim_group(data: dict[str, Any]) -> SCIMGroup:
    """
    Validate SCIM group data

    Args:
        data: Raw group data

    Returns:
        Validated SCIMGroup object

    Raises:
        ValueError: If validation fails
    """
    try:
        return SCIMGroup(**data)
    except Exception as e:
        raise ValueError(f"Invalid SCIM group data: {str(e)}") from e


def user_to_keycloak(scim_user: SCIMUser) -> dict[str, Any]:
    """
    Convert SCIM user to Keycloak user representation

    Args:
        scim_user: SCIM user object

    Returns:
        Keycloak user representation
    """
    attributes: dict[str, str] = {}
    keycloak_user: dict[str, Any] = {
        "username": scim_user.userName,
        "enabled": scim_user.active,
        "emailVerified": False,
        "attributes": attributes,
    }

    # Name
    if scim_user.name:
        if scim_user.name.givenName:
            keycloak_user["firstName"] = scim_user.name.givenName
        if scim_user.name.familyName:
            keycloak_user["lastName"] = scim_user.name.familyName

    # Email (use primary or first)
    if scim_user.emails:
        primary_email = next((e for e in scim_user.emails if e.primary), None)
        email = primary_email or scim_user.emails[0]
        keycloak_user["email"] = email.value
        keycloak_user["emailVerified"] = True

    # Optional attributes
    if scim_user.displayName:
        attributes["displayName"] = scim_user.displayName
    if scim_user.title:
        attributes["title"] = scim_user.title
    if scim_user.userType:
        attributes["userType"] = scim_user.userType

    # Enterprise extension
    if scim_user.enterpriseUser:
        ent = scim_user.enterpriseUser
        if ent.department:
            attributes["department"] = ent.department
        if ent.organization:
            attributes["organization"] = ent.organization
        if ent.employeeNumber:
            attributes["employeeNumber"] = ent.employeeNumber
        if ent.costCenter:
            attributes["costCenter"] = ent.costCenter

    # External ID
    if scim_user.externalId:
        attributes["externalId"] = scim_user.externalId

    return keycloak_user


def keycloak_to_scim_user(keycloak_user: dict[str, Any]) -> SCIMUser:
    """
    Convert Keycloak user to SCIM user representation

    Args:
        keycloak_user: Keycloak user object

    Returns:
        SCIM user object
    """
    attributes = keycloak_user.get("attributes", {})

    # Build name
    name = SCIMName(
        givenName=keycloak_user.get("firstName"),
        familyName=keycloak_user.get("lastName"),
    )

    # Build emails
    emails = []
    if keycloak_user.get("email"):
        emails.append(
            SCIMEmail(
                value=keycloak_user["email"],
                primary=True,
                type="work",
            )
        )

    # Build enterprise extension if attributes present
    enterprise_user = None
    if any(k in attributes for k in ["department", "organization", "employeeNumber"]):
        enterprise_user = SCIMEnterpriseUser(
            department=attributes.get("department"),
            organization=attributes.get("organization"),
            employeeNumber=attributes.get("employeeNumber"),
            costCenter=attributes.get("costCenter"),
        )

    schemas = [SCIM_USER_SCHEMA]
    if enterprise_user:
        schemas.append(SCIM_ENTERPRISE_USER_SCHEMA)

    user_dict = {
        "schemas": schemas,
        "id": keycloak_user["id"],
        "userName": keycloak_user["username"],
        "name": name,
        "displayName": attributes.get("displayName"),
        "title": attributes.get("title"),
        "active": keycloak_user.get("enabled", True),
        "emails": emails,
        "externalId": attributes.get("externalId"),
        "meta": {
            "resourceType": "User",
            "created": keycloak_user.get("createdTimestamp"),
            "lastModified": keycloak_user.get("createdTimestamp"),  # Keycloak doesn't track modification time
        },
    }

    if enterprise_user:
        user_dict["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"] = enterprise_user

    return SCIMUser(**user_dict)
