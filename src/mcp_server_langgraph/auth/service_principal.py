"""
Service Principal Management

Manages service principal lifecycle including creation, user association,
permission inheritance, secret rotation, and OpenFGA synchronization.

Service principals enable machine-to-machine authentication with two modes:
1. Client Credentials (OAuth2) - Keycloak clients with service accounts
2. Service Account Users - Special user accounts marked as services

See ADR-0033 for architectural decisions.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from mcp_server_langgraph.auth.keycloak import KeycloakClient
from mcp_server_langgraph.auth.openfga import OpenFGAClient


@dataclass
class ServicePrincipal:
    """Service principal identity and configuration"""

    service_id: str  # e.g., "batch-etl-job"
    name: str
    description: str
    authentication_mode: str  # "client_credentials" or "service_account_user"
    associated_user_id: str | None = None  # e.g., "user:alice"
    owner_user_id: str | None = None  # e.g., "user:bob"
    inherit_permissions: bool = False
    enabled: bool = True
    created_at: str | None = None
    client_secret: str | None = None  # Only returned on creation/rotation


class ServicePrincipalManager:
    """Manage service principal lifecycle"""

    def __init__(self, keycloak_client: KeycloakClient, openfga_client: OpenFGAClient | None):
        """
        Initialize service principal manager

        Args:
            keycloak_client: Keycloak client for user/client management
            openfga_client: OpenFGA client for authorization tuples (None if disabled)
        """
        self.keycloak = keycloak_client
        self.openfga = openfga_client

    async def create_service_principal(
        self,
        service_id: str,
        name: str,
        description: str,
        authentication_mode: str = "client_credentials",
        associated_user_id: str | None = None,
        owner_user_id: str | None = None,
        inherit_permissions: bool = False,
    ) -> ServicePrincipal:
        """
        Create service principal in Keycloak and OpenFGA

        Args:
            service_id: Unique identifier for service (e.g., "batch-etl-job")
            name: Human-readable name
            description: Purpose/description
            authentication_mode: "client_credentials" or "service_account_user"
            associated_user_id: Optional user to act as (e.g., "user:alice")
            owner_user_id: User who owns this service principal
            inherit_permissions: Whether to inherit permissions from associated user

        Returns:
            ServicePrincipal with generated credentials

        Raises:
            ValueError: If authentication_mode is invalid
        """
        created_at = datetime.now(timezone.utc).isoformat()

        if authentication_mode == "client_credentials":
            client_secret = await self._create_client_credentials_service(
                service_id=service_id,
                name=name,
                description=description,
                associated_user_id=associated_user_id,
                owner_user_id=owner_user_id,
                inherit_permissions=inherit_permissions,
            )

        elif authentication_mode == "service_account_user":
            client_secret = await self._create_service_account_user(
                service_id=service_id,
                name=name,
                description=description,
                associated_user_id=associated_user_id,
                owner_user_id=owner_user_id,
                inherit_permissions=inherit_permissions,
            )

        else:
            raise ValueError(f"Invalid authentication mode: {authentication_mode}")

        # Sync to OpenFGA
        await self._sync_to_openfga(
            service_id=service_id,
            associated_user_id=associated_user_id,
            owner_user_id=owner_user_id,
            inherit_permissions=inherit_permissions,
        )

        return ServicePrincipal(
            service_id=service_id,
            name=name,
            description=description,
            authentication_mode=authentication_mode,
            associated_user_id=associated_user_id,
            owner_user_id=owner_user_id,
            inherit_permissions=inherit_permissions,
            enabled=True,
            created_at=created_at,
            client_secret=client_secret,
        )

    async def _create_client_credentials_service(
        self,
        service_id: str,
        name: str,
        description: str,
        associated_user_id: str | None,
        owner_user_id: str | None,
        inherit_permissions: bool,
    ) -> str:
        """Create Keycloak client with service account enabled"""
        # Generate secure client secret
        client_secret = secrets.token_urlsafe(32)

        client_config = {
            "clientId": service_id,
            "name": name,
            "description": description,
            "enabled": True,
            "serviceAccountsEnabled": True,  # Enable service accounts
            "standardFlowEnabled": False,  # No authorization code flow
            "directAccessGrantsEnabled": False,  # No ROPC
            "implicitFlowEnabled": False,  # No implicit flow
            "publicClient": False,  # Confidential client
            "clientAuthenticatorType": "client-secret",
            "secret": client_secret,
            "attributes": {
                "associatedUserId": associated_user_id or "",
                "inheritPermissions": str(inherit_permissions).lower(),
                "owner": owner_user_id or "",
                "purpose": description,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
        }

        await self.keycloak.create_client(client_config)
        return client_secret

    async def _create_service_account_user(
        self,
        service_id: str,
        name: str,
        description: str,
        associated_user_id: str | None,
        owner_user_id: str | None,
        inherit_permissions: bool,
    ) -> str:
        """Create Keycloak user marked as service account"""
        # Generate secure password
        password = secrets.token_urlsafe(32)

        user_config = {
            "username": f"svc_{service_id}",
            "enabled": True,
            "email": f"svc-{service_id}@example.com",
            "emailVerified": True,
            "attributes": {
                "serviceAccount": "true",  # Mark as service account
                "associatedUserId": associated_user_id or "",
                "inheritPermissions": str(inherit_permissions).lower(),
                "owner": owner_user_id or "",
                "purpose": description,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
            "credentials": [{"type": "password", "value": password, "temporary": False}],
            "realmRoles": ["service-principal"],
        }

        await self.keycloak.create_user(user_config)
        return password

    async def _sync_to_openfga(
        self,
        service_id: str,
        associated_user_id: str | None,
        owner_user_id: str | None,
        inherit_permissions: bool,
    ) -> None:
        """
        Sync service principal relationships to OpenFGA

        Gracefully handles disabled OpenFGA (when self.openfga is None).
        """
        # Guard: Skip OpenFGA sync if client is not available
        if self.openfga is None:
            return

        tuples = []

        # Permission inheritance via acts_as
        if inherit_permissions and associated_user_id:
            tuples.append(
                {
                    "user": f"service:{service_id}",
                    "relation": "acts_as",
                    "object": associated_user_id,
                }
            )

        # Ownership
        if owner_user_id:
            tuples.append(
                {
                    "user": owner_user_id,
                    "relation": "owner",
                    "object": f"service_principal:{service_id}",
                }
            )

        if tuples:
            await self.openfga.write_tuples(tuples)

    async def associate_with_user(
        self,
        service_id: str,
        user_id: str,
        inherit_permissions: bool = True,
    ) -> None:
        """
        Associate service principal with user for permission inheritance

        Args:
            service_id: Service principal identifier
            user_id: User to associate with (e.g., "user:alice")
            inherit_permissions: Whether to inherit user's permissions
        """
        # Update Keycloak attributes
        await self.keycloak.update_client_attributes(
            service_id,
            {
                "associatedUserId": user_id,
                "inheritPermissions": str(inherit_permissions).lower(),
            },
        )

        # Create OpenFGA tuple for permission inheritance
        if inherit_permissions and self.openfga is not None:
            await self.openfga.write_tuples(
                [
                    {
                        "user": f"service:{service_id}",
                        "relation": "acts_as",
                        "object": user_id,
                    }
                ]
            )

    async def rotate_secret(self, service_id: str) -> str:
        """
        Rotate service principal secret

        Args:
            service_id: Service principal identifier

        Returns:
            New client secret (store securely, won't be shown again)
        """
        new_secret = secrets.token_urlsafe(32)

        # Update in Keycloak
        await self.keycloak.update_client_secret(service_id, new_secret)

        return new_secret

    async def list_service_principals(self, owner_user_id: str | None = None) -> list[ServicePrincipal]:
        """
        List all service principals, optionally filtered by owner

        Args:
            owner_user_id: Optional filter by owner (e.g., "user:bob")

        Returns:
            List of ServicePrincipal objects
        """
        service_principals = []

        # Query Keycloak for clients with serviceAccountsEnabled
        clients = await self.keycloak.get_clients(query={"serviceAccountsEnabled": True})

        for client in clients:
            attrs = client.get("attributes", {})

            # Filter by owner if specified
            if owner_user_id and attrs.get("owner") != owner_user_id:
                continue

            service_principals.append(
                ServicePrincipal(
                    service_id=client["clientId"],
                    name=client.get("name", ""),
                    description=client.get("description", ""),
                    authentication_mode="client_credentials",
                    associated_user_id=attrs.get("associatedUserId") or None,
                    owner_user_id=attrs.get("owner") or None,
                    inherit_permissions=attrs.get("inheritPermissions") == "true",
                    enabled=client.get("enabled", True),
                    created_at=attrs.get("createdAt"),
                    client_secret=None,  # Never return secrets in list
                )
            )

        # Also query for service account users
        users = await self.keycloak.get_users(query={"serviceAccount": "true"})

        for user in users:
            attrs = user.get("attributes", {})

            # Filter by owner if specified
            if owner_user_id and attrs.get("owner") != owner_user_id:
                continue

            # Extract service_id from username (format: svc_<service_id>)
            username = user.get("username", "")
            service_id = username.replace("svc_", "") if username.startswith("svc_") else username

            service_principals.append(
                ServicePrincipal(
                    service_id=service_id,
                    name=user.get("firstName", "") or user.get("username", ""),
                    description=attrs.get("purpose", ""),
                    authentication_mode="service_account_user",
                    associated_user_id=attrs.get("associatedUserId") or None,
                    owner_user_id=attrs.get("owner") or None,
                    inherit_permissions=attrs.get("inheritPermissions") == "true",
                    enabled=user.get("enabled", True),
                    created_at=attrs.get("createdAt"),
                    client_secret=None,
                )
            )

        return service_principals

    async def get_service_principal(self, service_id: str) -> ServicePrincipal | None:
        """
        Get specific service principal by ID

        Args:
            service_id: Service principal identifier

        Returns:
            ServicePrincipal or None if not found
        """
        # Try to find as client first
        try:
            client = await self.keycloak.get_client(service_id)
            if client and client.get("serviceAccountsEnabled"):
                attrs = client.get("attributes", {})
                return ServicePrincipal(
                    service_id=client["clientId"],
                    name=client.get("name", ""),
                    description=client.get("description", ""),
                    authentication_mode="client_credentials",
                    associated_user_id=attrs.get("associatedUserId") or None,
                    owner_user_id=attrs.get("owner") or None,
                    inherit_permissions=attrs.get("inheritPermissions") == "true",
                    enabled=client.get("enabled", True),
                    created_at=attrs.get("createdAt"),
                )
        except Exception:
            pass

        # Try to find as service account user
        try:
            user = await self.keycloak.get_user_by_username(f"svc_{service_id}")
            if user:
                attrs = user.get("attributes", {})  # type: ignore[attr-defined]
                if attrs.get("serviceAccount") == "true":
                    return ServicePrincipal(
                        service_id=service_id,
                        name=user.get("firstName", "") or user.get("username", ""),  # type: ignore[attr-defined]
                        description=attrs.get("purpose", ""),
                        authentication_mode="service_account_user",
                        associated_user_id=attrs.get("associatedUserId") or None,
                        owner_user_id=attrs.get("owner") or None,
                        inherit_permissions=attrs.get("inheritPermissions") == "true",
                        enabled=user.get("enabled", True),  # type: ignore[attr-defined]
                        created_at=attrs.get("createdAt"),
                    )
        except Exception:
            pass

        return None

    async def delete_service_principal(self, service_id: str) -> None:
        """
        Delete service principal from Keycloak and OpenFGA

        Args:
            service_id: Service principal identifier
        """
        # Remove from Keycloak (try both client and user)
        try:
            await self.keycloak.delete_client(service_id)
        except Exception:
            try:
                await self.keycloak.delete_user(f"svc_{service_id}")
            except Exception:
                pass  # May not exist

        # Remove from OpenFGA (if available)
        if self.openfga is not None:
            await self.openfga.delete_tuples_for_object(f"service_principal:{service_id}")
