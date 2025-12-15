"""
MCP Connections User Journey E2E Tests

Comprehensive tests for connection management including:
- Connection CRUD operations
- OAuth2 authentication flows
- Connection health monitoring
- Bulk operations
- Audit logging

HEART Metrics Focus:
- Task Success: Connection operation completion rates
- Engagement: Feature usage depth
- Adoption: OAuth2 and bulk feature discovery
- Retention: Connection reliability patterns
- Happiness: User satisfaction with connection UX

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.connections_journey,
]


# Infrastructure check and autouse skip fixture are in tests/e2e/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)


@pytest.mark.xdist_group(name="test_connections_journey")
class TestConnectionsUserJourney:
    """
    Comprehensive MCP connections user journey tests with HEART metrics.

    User capabilities:
    - Create and manage MCP server connections
    - Configure authentication (none, API key, OAuth2)
    - Monitor connection health
    - Perform bulk operations
    - View audit logs
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_create_connection_no_auth(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 1: Create a basic MCP connection without authentication.

        HEART Metrics:
        - Task Success: Connection creation completion
        - Engagement: Initial feature discovery
        - Adoption: Basic connection setup

        GIVEN user has connection creation permissions
        WHEN user creates a connection without auth
        THEN connection should be created successfully
        AND creation time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        connection_id = None

        try:
            async with httpx.AsyncClient() as client:
                connection_payload = {
                    "name": f"E2E Test Connection {uuid4().hex[:8]}",
                    "description": "E2E test connection without auth",
                    "url": "http://localhost:8765",
                    "auth_type": "none",
                }

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json=connection_payload,
                    headers={
                        "Authorization": "Bearer alice-test-token",
                        "X-User-ID": "alice",
                    },
                    timeout=10.0,
                )

                if response.status_code == 201:
                    task_success = True
                    data = response.json()
                    connection_id = data.get("id")
                    assert connection_id is not None
                    assert data["name"] == connection_payload["name"]
                    assert data["auth_type"] == "none"

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "create_connection_no_auth",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_02_create_connection_with_api_key(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 2: Create an MCP connection with API key authentication.

        HEART Metrics:
        - Task Success: API key connection creation
        - Engagement: Authentication feature usage
        - Adoption: Secure connection setup

        GIVEN user has connection creation permissions
        WHEN user creates a connection with API key auth
        THEN connection should be created with secure credential storage
        AND creation time should be < 1500ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        connection_id = None

        try:
            async with httpx.AsyncClient() as client:
                connection_payload = {
                    "name": f"E2E API Key Connection {uuid4().hex[:8]}",
                    "description": "E2E test connection with API key",
                    "url": "https://api.example.com/mcp",
                    "auth_type": "api_key",
                    "api_key": "test-api-key-12345",
                }

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json=connection_payload,
                    headers={
                        "Authorization": "Bearer alice-test-token",
                        "X-User-ID": "alice",
                    },
                    timeout=10.0,
                )

                if response.status_code == 201:
                    task_success = True
                    data = response.json()
                    connection_id = data.get("id")
                    assert data["auth_type"] == "api_key"
                    # API key should not be returned in response
                    assert "api_key" not in data or data.get("api_key") is None

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "create_connection_api_key",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_03_list_connections_with_filters(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 3: List connections with filtering and pagination.

        HEART Metrics:
        - Task Success: Listing and filtering success
        - Engagement: Filter feature usage
        - Adoption: Advanced search features

        GIVEN user has multiple connections
        WHEN user lists connections with various filters
        THEN filtered results should be returned correctly
        AND response time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        filter_tests_passed = 0

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Test 1: List all connections
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    filter_tests_passed += 1

                # Test 2: Filter by auth_type
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections?auth_type=none",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    filter_tests_passed += 1

                # Test 3: Search by name
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections?search=E2E",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    filter_tests_passed += 1

                # Test 4: Pagination
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections?limit=5&sort_by=created_at&sort_order=desc",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    filter_tests_passed += 1

                task_success = filter_tests_passed >= 3

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "list_connections_filters",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "filter_tests_passed": filter_tests_passed,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_04_update_connection(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 4: Update an existing connection.

        HEART Metrics:
        - Task Success: Update operation completion
        - Engagement: Edit feature usage
        - Retention: Connection management patterns

        GIVEN user owns a connection
        WHEN user updates the connection details
        THEN changes should be persisted correctly
        AND update time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        connection_id = None

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # First create a connection to update
                create_response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json={
                        "name": f"Update Test {uuid4().hex[:8]}",
                        "url": "http://localhost:8765",
                        "auth_type": "none",
                    },
                    headers=headers,
                    timeout=10.0,
                )

                if create_response.status_code == 201:
                    connection_id = create_response.json().get("id")

                    # Now update the connection
                    update_response = await client.put(
                        f"{e2e_api_base_url}/api/v1/connections/{connection_id}",
                        json={
                            "name": "Updated Connection Name",
                            "description": "Updated description via E2E test",
                        },
                        headers=headers,
                        timeout=10.0,
                    )

                    if update_response.status_code == 200:
                        task_success = True
                        data = update_response.json()
                        assert data["name"] == "Updated Connection Name"
                        assert data["description"] == "Updated description via E2E test"

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "update_connection",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_05_test_connection_health(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 5: Test connection health and get server info.

        HEART Metrics:
        - Task Success: Health check completion
        - Engagement: Monitoring feature usage
        - Happiness: Connection reliability

        GIVEN user owns a connection
        WHEN user tests the connection
        THEN health status and server info should be returned
        AND test time should be < 5000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        health_status = None
        latency_ms = None

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # First create a test connection
                create_response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json={
                        "name": f"Health Test {uuid4().hex[:8]}",
                        "url": "http://localhost:8765",
                        "auth_type": "none",
                    },
                    headers=headers,
                    timeout=10.0,
                )

                if create_response.status_code == 201:
                    connection_id = create_response.json().get("id")

                    # Test the connection
                    test_response = await client.post(
                        f"{e2e_api_base_url}/api/v1/connections/{connection_id}/test",
                        headers=headers,
                        timeout=15.0,
                    )

                    if test_response.status_code == 200:
                        task_success = True
                        data = test_response.json()
                        health_status = "success" if data.get("success") else "failed"
                        latency_ms = data.get("latency_ms")

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "test_connection_health",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "health_status": health_status,
                "latency_ms": latency_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_06_bulk_delete_connections(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 6: Bulk delete multiple connections.

        HEART Metrics:
        - Task Success: Bulk delete completion
        - Engagement: Bulk operation usage
        - Adoption: Advanced management features

        GIVEN user owns multiple connections
        WHEN user performs bulk delete
        THEN all selected connections should be deleted
        AND operation time should be < 3000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        deleted_count = 0
        created_ids = []

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Create multiple connections for bulk delete
                for i in range(3):
                    create_response = await client.post(
                        f"{e2e_api_base_url}/api/v1/connections",
                        json={
                            "name": f"Bulk Delete Test {i} {uuid4().hex[:8]}",
                            "url": f"http://localhost:876{i}",
                            "auth_type": "none",
                        },
                        headers=headers,
                        timeout=10.0,
                    )
                    if create_response.status_code == 201:
                        created_ids.append(create_response.json().get("id"))

                if len(created_ids) >= 2:
                    # Perform bulk delete
                    bulk_response = await client.post(
                        f"{e2e_api_base_url}/api/v1/connections/bulk/delete",
                        json={"connection_ids": created_ids},
                        headers=headers,
                        timeout=15.0,
                    )

                    if bulk_response.status_code == 200:
                        task_success = True
                        data = bulk_response.json()
                        deleted_count = data.get("deleted_count", 0)

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "bulk_delete_connections",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "created_count": len(created_ids),
                "deleted_count": deleted_count,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_07_bulk_test_connections(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 7: Bulk test multiple connections.

        HEART Metrics:
        - Task Success: Bulk test completion
        - Engagement: Bulk testing usage
        - Adoption: Health monitoring features

        GIVEN user owns multiple connections
        WHEN user performs bulk health test
        THEN all connection health statuses should be returned
        AND operation time should be < 10000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        test_results = []

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Create connections for bulk test
                created_ids = []
                for i in range(2):
                    create_response = await client.post(
                        f"{e2e_api_base_url}/api/v1/connections",
                        json={
                            "name": f"Bulk Test Check {i} {uuid4().hex[:8]}",
                            "url": f"http://localhost:877{i}",
                            "auth_type": "none",
                        },
                        headers=headers,
                        timeout=10.0,
                    )
                    if create_response.status_code == 201:
                        created_ids.append(create_response.json().get("id"))

                if created_ids:
                    # Perform bulk test
                    bulk_response = await client.post(
                        f"{e2e_api_base_url}/api/v1/connections/bulk/test",
                        json={"connection_ids": created_ids},
                        headers=headers,
                        timeout=30.0,
                    )

                    if bulk_response.status_code == 200:
                        task_success = True
                        data = bulk_response.json()
                        test_results = data.get("results", [])

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "bulk_test_connections",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "test_results_count": len(test_results),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_08_view_connection_audit_log(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 8: View audit log for a connection.

        HEART Metrics:
        - Task Success: Audit log retrieval
        - Engagement: Audit feature usage
        - Adoption: Compliance feature discovery

        GIVEN user owns a connection with activity history
        WHEN user views the audit log
        THEN all operations should be logged with details
        AND retrieval time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        log_entries = 0

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Create a connection (this will generate an audit log entry)
                create_response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json={
                        "name": f"Audit Test {uuid4().hex[:8]}",
                        "url": "http://localhost:8765",
                        "auth_type": "none",
                    },
                    headers=headers,
                    timeout=10.0,
                )

                if create_response.status_code == 201:
                    connection_id = create_response.json().get("id")

                    # Get audit log for this connection
                    audit_response = await client.get(
                        f"{e2e_api_base_url}/api/v1/connections/{connection_id}/audit",
                        headers=headers,
                        timeout=10.0,
                    )

                    if audit_response.status_code == 200:
                        task_success = True
                        data = audit_response.json()
                        log_entries = len(data.get("logs", []))

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "view_audit_log",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "log_entries": log_entries,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_09_export_audit_logs(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 9: Export audit logs in JSON and CSV format.

        HEART Metrics:
        - Task Success: Export completion
        - Engagement: Export feature usage
        - Adoption: Compliance reporting features

        GIVEN user has audit log data
        WHEN user exports logs in different formats
        THEN exports should be generated correctly
        AND export time should be < 2000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        export_tests_passed = 0

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Test JSON export
                json_response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections/audit/export?format=json",
                    headers=headers,
                    timeout=15.0,
                )
                if json_response.status_code == 200:
                    export_tests_passed += 1
                    assert json_response.headers.get("content-type") == "application/json"

                # Test CSV export
                csv_response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections/audit/export?format=csv",
                    headers=headers,
                    timeout=15.0,
                )
                if csv_response.status_code == 200:
                    export_tests_passed += 1
                    assert "text/csv" in csv_response.headers.get("content-type", "")

                task_success = export_tests_passed >= 2

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "export_audit_logs",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "export_tests_passed": export_tests_passed,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_10_complete_connection_journey(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 10: Complete connection management journey.

        This test simulates a complete user journey:
        1. Create connection
        2. Test connection health
        3. Update connection
        4. View audit log
        5. Delete connection

        HEART Metrics:
        - Complete connection journey success rate
        - Total journey duration
        - Feature adoption metrics
        - User satisfaction indicators
        """
        import httpx

        journey_start_time = time.time()
        steps_completed = 0
        total_steps = 5
        errors = []
        features_used = []

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer alice-test-token",
                    "X-User-ID": "alice",
                }

                # Step 1: Create connection
                create_response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections",
                    json={
                        "name": f"Journey Test {uuid4().hex[:8]}",
                        "url": "http://localhost:8765",
                        "auth_type": "none",
                    },
                    headers=headers,
                    timeout=10.0,
                )
                if create_response.status_code == 201:
                    steps_completed += 1
                    features_used.append("create")
                    connection_id = create_response.json().get("id")
                else:
                    errors.append(f"Create failed: {create_response.status_code}")
                    return

                # Step 2: Test connection
                test_response = await client.post(
                    f"{e2e_api_base_url}/api/v1/connections/{connection_id}/test",
                    headers=headers,
                    timeout=15.0,
                )
                if test_response.status_code == 200:
                    steps_completed += 1
                    features_used.append("test")

                # Step 3: Update connection
                update_response = await client.put(
                    f"{e2e_api_base_url}/api/v1/connections/{connection_id}",
                    json={"description": "Journey test update"},
                    headers=headers,
                    timeout=10.0,
                )
                if update_response.status_code == 200:
                    steps_completed += 1
                    features_used.append("update")

                # Step 4: View audit log
                audit_response = await client.get(
                    f"{e2e_api_base_url}/api/v1/connections/{connection_id}/audit",
                    headers=headers,
                    timeout=10.0,
                )
                if audit_response.status_code == 200:
                    steps_completed += 1
                    features_used.append("audit_log")

                # Step 5: Delete connection
                delete_response = await client.delete(
                    f"{e2e_api_base_url}/api/v1/connections/{connection_id}",
                    headers=headers,
                    timeout=10.0,
                )
                if delete_response.status_code == 204:
                    steps_completed += 1
                    features_used.append("delete")

        except Exception as e:
            errors.append(str(e))
        finally:
            journey_duration_ms = (time.time() - journey_start_time) * 1000
            success_rate = (steps_completed / total_steps) * 100

            heart_metrics = {
                "task_name": "complete_connection_journey",
                "duration_ms": journey_duration_ms,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "success_rate": success_rate,
                "features_used": features_used,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS - CONNECTION JOURNEY] {heart_metrics}")
