"""
SCIM 2.0 Schema Validation

Implements SCIM 2.0 schema validation according to RFC 7643.
Validates User and Group resources against SCIM Core Schema and Enterprise Extension.

See ADR-0038 for SCIM implementation approach.

References:
- RFC 7643: SCIM Core Schema
- RFC 7644: SCIM Protocol
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# SCIM Schema URNs
SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"


class SCIMEmail(BaseModel):
    """SCIM email address"""
    value: str
    type: Optional[str] = "work"  # work, home, other
    primary: bool = False


class SCIMName(BaseModel):
    """SCIM user name"""
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


class SCIMPhoneNumber(BaseModel):
    """SCIM phone number"""
    value: str
    type: Optional[str] = "work"
    primary: bool = False


class SCIMAddress(BaseModel):
    """SCIM address"""
    formatted: Optional[str] = None
    streetAddress: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = "work"
    primary: bool = False


class SCIMGroupMembership(BaseModel):
    """SCIM group membership"""
    value: str  # Group ID
    ref: Optional[str] = Field(None, alias="$ref")
    display: Optional[str] = None
    type: Optional[str] = "direct"


class SCIMEnterpriseUser(BaseModel):
    """SCIM Enterprise User Extension (RFC 7643 Section 4.3)"""
    employeeNumber: Optional[str] = None
    costCenter: Optional[str] = None
    organization: Optional[str] = None
    division: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[Dict[str, str]] = None  # {value: manager_id, ref: url, displayName: name}


class SCIMUser(BaseModel):
    """
    SCIM 2.0 User Resource

    Core schema with optional Enterprise extension.
    """
    schemas: List[str] = Field(default=[SCIM_USER_SCHEMA])
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    nickName: Optional[str] = None
    profileUrl: Optional[str] = None
    title: Optional[str] = None
    userType: Optional[str] = None
    preferredLanguage: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    emails: List[SCIMEmail] = []
    phoneNumbers: List[SCIMPhoneNumber] = []
    addresses: List[SCIMAddress] = []
    groups: List[SCIMGroupMembership] = []

    # Meta
    meta: Optional[Dict[str, Any]] = None

    # Enterprise extension
    enterpriseUser: Optional[SCIMEnterpriseUser] = Field(
        None,
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )

    @field_validator("schemas")
    @classmethod
    def validate_schemas(cls, v: List[str]) -> List[str]:
        """Validate that required schemas are present"""
        if SCIM_USER_SCHEMA not in v:
            raise ValueError(f"Missing required schema: {SCIM_USER_SCHEMA}")
        return v

    @field_validator("emails")
    @classmethod
    def validate_primary_email(cls, v: List[SCIMEmail]) -> List[SCIMEmail]:
        """Ensure at most one primary email"""
        primary_count = sum(1 for email in v if email.primary)
        if primary_count > 1:
            raise ValueError("Only one email can be marked as primary")
        return v


class SCIMMember(BaseModel):
    """SCIM group member"""
    value: str  # User ID
    ref: Optional[str] = Field(None, alias="$ref")
    display: Optional[str] = None
    type: Optional[str] = "User"


class SCIMGroup(BaseModel):
    """SCIM 2.0 Group Resource"""
    schemas: List[str] = Field(default=[SCIM_GROUP_SCHEMA])
    id: Optional[str] = None
    displayName: str
    members: List[SCIMMember] = []
    meta: Optional[Dict[str, Any]] = None

    @field_validator("schemas")
    @classmethod
    def validate_schemas(cls, v: List[str]) -> List[str]:
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
    path: Optional[str] = None
    value: Any = None


class SCIMPatchRequest(BaseModel):
    """SCIM PATCH request"""
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:PatchOp"])
    Operations: List[SCIMPatchOperation]


class SCIMListResponse(BaseModel):
    """SCIM List Response"""
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: List[Any]  # Can be Users or Groups


class SCIMError(BaseModel):
    """SCIM Error Response"""
    schemas: List[str] = Field(default=["urn:ietf:params:scim:api:messages:2.0:Error"])
    status: int
    scimType: Optional[str] = None
    detail: Optional[str] = None


def validate_scim_user(data: Dict[str, Any]) -> SCIMUser:
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
        raise ValueError(f"Invalid SCIM user data: {str(e)}")


def validate_scim_group(data: Dict[str, Any]) -> SCIMGroup:
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
        raise ValueError(f"Invalid SCIM group data: {str(e)}")


def user_to_keycloak(scim_user: SCIMUser) -> Dict[str, Any]:
    """
    Convert SCIM user to Keycloak user representation

    Args:
        scim_user: SCIM user object

    Returns:
        Keycloak user representation
    """
    attributes: Dict[str, str] = {}
    keycloak_user: Dict[str, Any] = {
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


def keycloak_to_scim_user(keycloak_user: Dict[str, Any]) -> SCIMUser:
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

    return SCIMUser(
        schemas=schemas,
        id=keycloak_user["id"],
        userName=keycloak_user["username"],
        name=name,
        displayName=attributes.get("displayName"),
        title=attributes.get("title"),
        active=keycloak_user.get("enabled", True),
        emails=emails,
        externalId=attributes.get("externalId"),
        enterpriseUser=enterprise_user,
        meta={
            "resourceType": "User",
            "created": keycloak_user.get("createdTimestamp"),
            "lastModified": keycloak_user.get("createdTimestamp"),  # Keycloak doesn't track modification time
        },
    )
