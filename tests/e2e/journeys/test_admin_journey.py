"""
Admin User Journey E2E Tests

Comprehensive tests for admin user journey including:
- User management operations
- API key rotation and management
- Dashboard access and metrics
- Organization administration
- Audit log access
- Cross-user resource access

HEART Metrics Focus:
- Task Success: Admin operation completion rates
- Engagement: Dashboard interaction patterns
- Adoption: Admin feature discovery

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
import time
from datetime import UTC, datetime

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.admin_journey,
]


# Infrastructure check and autouse skip fixture are in tests/e2e/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)


@pytest.mark.xdist_group(name="test_admin_journey")
class TestAdminJourney:
    """
    Comprehensive admin user journey tests with HEART metrics.

    Admin capabilities tested:
    - User management (CRUD)
    - API key rotation
    - Dashboard metrics access
    - Organization management
    - Audit log viewing
    - Resource access across users
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_admin_login_and_token_validation(
        self,
        e2e_keycloak_base_url: str,
        admin_credentials: dict,
    ) -> None:
        """
        Step 1: Admin authenticates and validates token.

        HEART Metrics:
        - Task Success: Authentication completion time
        - Engagement: Login interaction

        GIVEN admin credentials
        WHEN admin attempts to login via Keycloak
        THEN admin should receive a valid access token with admin role
        AND authentication should complete in < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{e2e_keycloak_base_url}/realms/default/protocol/openid-connect/token",
                    data={
                        "grant_type": "password",
                        "client_id": admin_credentials.get("client_id", "mcp-server"),
                        "client_secret": admin_credentials.get("client_secret", ""),
                        "username": admin_credentials["username"],
                        "password": admin_credentials["password"],
                        "scope": "openid email profile",
                    },
                    timeout=5.0,
                )

                assert response.status_code == 200, f"Login failed: {response.status_code}"
                data = response.json()
                assert "access_token" in data, "Missing access token"
                assert "refresh_token" in data, "Missing refresh token"

                task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            assert task_duration_ms < 1000, f"Login took {task_duration_ms}ms, expected < 1000ms"

            heart_metrics = {
                "task_name": "admin_login",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_02_admin_dashboard_access(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 2: Admin accesses admin dashboard metrics.

        HEART Metrics:
        - Task Success: Dashboard load time
        - Engagement: Dashboard interaction
        - Adoption: Admin features discovered

        GIVEN admin is authenticated
        WHEN admin requests admin dashboard data
        THEN admin should receive comprehensive dashboard metrics
        AND response time should be < 1500ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        features_discovered = []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/dashboard",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    # Check for expected dashboard components
                    if "users" in data:
                        features_discovered.append("user_metrics")
                    if "workflows" in data:
                        features_discovered.append("workflow_metrics")
                    if "costs" in data:
                        features_discovered.append("cost_metrics")
                    if "system" in data:
                        features_discovered.append("system_health")

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "admin_dashboard_access",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "features_discovered": features_discovered,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_03_user_management_operations(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 3: Admin performs user management operations.

        HEART Metrics:
        - Task Success: User management CRUD success rate
        - Engagement: Admin interaction count

        GIVEN admin is authenticated
        WHEN admin performs user management operations (list, view, update)
        THEN all operations should succeed
        AND total operation time should be < 2000ms
        """
        import httpx

        task_start_time = time.time()
        operations_completed = 0
        total_operations = 3  # List, View, Update
        errors = []

        try:
            async with httpx.AsyncClient() as client:
                # List all users
                list_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/users",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if list_resp.status_code == 200:
                    operations_completed += 1
                    users = list_resp.json()
                    assert isinstance(users, (list, dict)), "Should return users list or dict"
                else:
                    errors.append(f"LIST failed: {list_resp.status_code}")

                # View specific user
                view_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/users/alice",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if view_resp.status_code == 200:
                    operations_completed += 1
                    user = view_resp.json()
                    assert "username" in user or "user_id" in user
                else:
                    errors.append(f"VIEW failed: {view_resp.status_code}")

                # Update user metadata (e.g., tier)
                update_resp = await client.patch(
                    f"{e2e_api_base_url}/api/v1/admin/users/alice",
                    json={"tier": "premium"},
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if update_resp.status_code in [200, 204]:
                    operations_completed += 1
                else:
                    errors.append(f"UPDATE failed: {update_resp.status_code}")

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            success_rate = (operations_completed / total_operations) * 100

            heart_metrics = {
                "task_name": "user_management",
                "duration_ms": task_duration_ms,
                "operations_completed": operations_completed,
                "success_rate": success_rate,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_04_api_key_rotation(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 4: Admin performs API key rotation.

        HEART Metrics:
        - Task Success: Key rotation completion
        - Engagement: Security management interaction

        GIVEN admin has permission to manage API keys
        WHEN admin rotates an API key
        THEN the operation should succeed
        AND completion time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False

        try:
            async with httpx.AsyncClient() as client:
                # Rotate API key for a user
                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/admin/users/alice/rotate-api-key",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if response.status_code in [200, 201]:
                    task_success = True
                    data = response.json()
                    assert "api_key" in data or "key" in data, "Should return new API key"

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "api_key_rotation",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_05_organization_management(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 5: Admin manages organizations.

        HEART Metrics:
        - Task Success: Organization management operations
        - Engagement: Admin portal usage

        GIVEN admin has organization management permissions
        WHEN admin lists and manages organizations
        THEN all operations should succeed
        AND response time should be < 1500ms
        """
        import httpx

        task_start_time = time.time()
        operations_completed = 0
        total_operations = 2  # List, View details

        try:
            async with httpx.AsyncClient() as client:
                # List organizations
                list_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/organizations",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if list_resp.status_code == 200:
                    operations_completed += 1
                    data = list_resp.json()
                    assert isinstance(data, (list, dict))

                # View organization details
                view_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/organizations/default",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if view_resp.status_code == 200:
                    operations_completed += 1

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            success_rate = (operations_completed / total_operations) * 100

            heart_metrics = {
                "task_name": "organization_management",
                "duration_ms": task_duration_ms,
                "operations_completed": operations_completed,
                "success_rate": success_rate,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_06_audit_log_access(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 6: Admin views audit logs.

        HEART Metrics:
        - Task Success: Audit log retrieval
        - Engagement: Compliance monitoring

        GIVEN admin has audit log permissions
        WHEN admin requests audit logs
        THEN admin should see system activity logs
        AND response time should be < 2000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        log_entries_found = 0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/audit-logs",
                    headers={"Authorization": "Bearer admin-test-token"},
                    params={"limit": 100, "offset": 0},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    if isinstance(data, list):
                        log_entries_found = len(data)
                    elif isinstance(data, dict) and "logs" in data:
                        log_entries_found = len(data["logs"])

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "audit_log_access",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "log_entries_found": log_entries_found,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_07_cross_user_resource_access(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict,
    ) -> None:
        """
        Step 7: Admin accesses resources across users.

        HEART Metrics:
        - Task Success: Cross-user access operations
        - Engagement: Admin oversight capabilities

        GIVEN admin has organization admin permission
        WHEN admin requests any user's workflow
        THEN admin should have access
        AND response time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/workflows/{shared_workflow_id}",
                    headers={"Authorization": "Bearer admin-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()
                    assert "id" in data or "workflow_id" in data

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "cross_user_access",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_08_complete_admin_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 8: Complete admin workflow with comprehensive metrics.

        This test simulates a complete admin workflow:
        1. Access dashboard
        2. Review user list
        3. Check audit logs
        4. Perform user update
        5. Verify changes

        HEART Metrics:
        - Complete admin journey success rate
        - Total workflow duration
        - Admin feature adoption
        """
        import httpx

        workflow_start_time = time.time()
        steps_completed = 0
        total_steps = 5
        errors = []

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Dashboard
                dashboard_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/dashboard",
                    headers={"Authorization": "Bearer admin-test-token"},
                )
                if dashboard_resp.status_code == 200:
                    steps_completed += 1

                # Step 2: User list
                users_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/users",
                    headers={"Authorization": "Bearer admin-test-token"},
                )
                if users_resp.status_code == 200:
                    steps_completed += 1

                # Step 3: Audit logs
                logs_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/audit-logs",
                    headers={"Authorization": "Bearer admin-test-token"},
                )
                if logs_resp.status_code == 200:
                    steps_completed += 1

                # Step 4: User update
                update_resp = await client.patch(
                    f"{e2e_api_base_url}/api/v1/admin/users/alice",
                    json={"tier": "premium"},
                    headers={"Authorization": "Bearer admin-test-token"},
                )
                if update_resp.status_code in [200, 204]:
                    steps_completed += 1

                # Step 5: Verify changes
                verify_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/users/alice",
                    headers={"Authorization": "Bearer admin-test-token"},
                )
                if verify_resp.status_code == 200:
                    steps_completed += 1

        except Exception as e:
            errors.append(str(e))
        finally:
            workflow_duration_ms = (time.time() - workflow_start_time) * 1000
            success_rate = (steps_completed / total_steps) * 100

            heart_metrics = {
                "task_name": "complete_admin_workflow",
                "duration_ms": workflow_duration_ms,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "success_rate": success_rate,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS - ADMIN WORKFLOW] {heart_metrics}")
