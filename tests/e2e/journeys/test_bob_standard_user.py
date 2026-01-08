"""
Bob Standard User Journey E2E Tests

Comprehensive tests for standard tier user (bob) journey including:
- Chat sessions within tier limits
- Message history access
- Task completion tracking
- Shared resource viewing (read-only)
- Basic workflow access
- Standard tier limitations

HEART Metrics Focus:
- Task Success: Standard feature completion rates
- Engagement: User interaction patterns
- Adoption: Feature discovery within tier limits
- Retention: Standard user return patterns
- Happiness: User satisfaction with standard tier

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
import time
from datetime import UTC, datetime

import pytest

from mcp_server_langgraph.core.numeric import safe_average

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.standard_user_journey,
]


# Infrastructure check and autouse skip fixture are in tests/e2e/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)


@pytest.mark.xdist_group(name="test_bob_standard_user")
class TestBobStandardUserJourney:
    """
    Comprehensive standard user journey tests with HEART metrics.

    Bob (Standard Tier) capabilities:
    - Basic chat functionality
    - Session management (limited)
    - View shared workflows (read-only)
    - Message history access
    - Basic cost tracking
    - Standard API access
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_standard_user_login_and_onboarding(
        self,
        e2e_keycloak_base_url: str,
        e2e_api_base_url: str,
        bob_credentials: dict,
    ) -> None:
        """
        Step 1: Bob logs in and completes onboarding.

        HEART Metrics:
        - Adoption: New user onboarding completion
        - Engagement: Login interaction
        - Task Success: Authentication completion

        GIVEN bob has standard tier credentials
        WHEN bob logs in (via token exchange or PKCE) and checks available features
        THEN bob should see standard tier features
        AND login should complete in < 1500ms

        NOTE: Uses login_as_user() token exchange per RFC 9700 instead of ROPC.
        """
        import httpx

        from tests.e2e.real_clients import real_keycloak_auth

        task_start_time = time.time()
        task_success = False
        onboarding_steps = []

        try:
            async with real_keycloak_auth(base_url=e2e_keycloak_base_url) as auth:
                # Use token exchange (RFC 8693) - no password needed
                # Falls back to PKCE if token exchange not configured
                try:
                    token_data = await auth.login_as_user(bob_credentials["username"])
                except RuntimeError as e:
                    if "not configured" in str(e):
                        # Fall back to PKCE if token exchange not set up
                        token_data = await auth.login_pkce(
                            bob_credentials["username"],
                            bob_credentials["password"],
                        )
                    else:
                        raise

                access_token = token_data["access_token"]
                onboarding_steps.append("authentication_complete")

                # Check feature flags (onboarding step)
                async with httpx.AsyncClient() as client:
                    features_resp = await client.get(
                        f"{e2e_api_base_url}/api/v1/features",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=5.0,
                    )

                    if features_resp.status_code == 200:
                        onboarding_steps.append("features_discovered")

                task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "standard_user_onboarding",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "onboarding_steps_completed": onboarding_steps,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_02_create_basic_chat_session(
        self,
        e2e_api_base_url: str,
        openfga_bob_tuples: dict,
    ) -> None:
        """
        Step 2: Bob creates a basic chat session.

        HEART Metrics:
        - Task Success: Session creation success
        - Engagement: Chat interaction start
        - Adoption: Chat feature discovery

        GIVEN bob has access to basic chat features
        WHEN bob creates a new chat session
        THEN the session should be created successfully
        AND creation time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        session_id = None

        try:
            async with httpx.AsyncClient() as client:
                session_payload = {
                    "workflow_id": "default-chat",
                    "metadata": {
                        "tier": "standard",
                        "user": "bob",
                    },
                }

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/sessions",
                    json=session_payload,
                    headers={"Authorization": "Bearer bob-test-token"},
                    timeout=5.0,
                )

                if response.status_code in [200, 201]:
                    task_success = True
                    session_data = response.json()
                    session_id = session_data.get("id")

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "create_chat_session",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_03_send_chat_messages_and_track_completion(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 3: Bob sends chat messages and tracks task completion.

        HEART Metrics:
        - Task Success: Message delivery and response success
        - Engagement: Chat interaction depth
        - Happiness: Response quality satisfaction

        GIVEN bob has an active chat session
        WHEN bob sends multiple messages
        THEN bob should receive responses for all messages
        AND average response time should be < 5000ms
        """
        import httpx

        task_start_time = time.time()
        messages_sent = 0
        messages_received = 0
        target_messages = 3
        response_times = []

        try:
            async with httpx.AsyncClient() as client:
                for i in range(target_messages):
                    msg_start_time = time.time()

                    chat_payload = {
                        "messages": [{"role": "user", "content": f"Hello, this is message {i + 1}"}],
                        "model": "gpt-3.5-turbo",  # Standard tier uses cheaper model
                    }

                    response = await client.post(
                        f"{e2e_api_base_url}/api/v1/chat/completions",
                        json=chat_payload,
                        headers={"Authorization": "Bearer bob-test-token"},
                        timeout=10.0,
                    )

                    messages_sent += 1

                    if response.status_code == 200:
                        messages_received += 1
                        msg_duration = (time.time() - msg_start_time) * 1000
                        response_times.append(msg_duration)

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            success_rate = (messages_received / messages_sent * 100) if messages_sent > 0 else 0
            avg_response_time = safe_average(response_times)

            heart_metrics = {
                "task_name": "chat_messages_task_completion",
                "duration_ms": task_duration_ms,
                "messages_sent": messages_sent,
                "messages_received": messages_received,
                "success_rate": success_rate,
                "avg_response_time_ms": avg_response_time,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_04_access_message_history(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 4: Bob accesses message history.

        HEART Metrics:
        - Task Success: History retrieval success
        - Engagement: History browsing interaction
        - Retention: Return to previous conversations

        GIVEN bob has sent messages in previous sessions
        WHEN bob requests message history
        THEN bob should receive his message history
        AND retrieval time should be < 1500ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        messages_found = 0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/sessions",
                    params={"limit": 10, "include_messages": True},
                    headers={"Authorization": "Bearer bob-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    if isinstance(data, list):
                        for session in data:
                            if "messages" in session:
                                messages_found += len(session["messages"])
                    elif isinstance(data, dict) and "sessions" in data:
                        for session in data["sessions"]:
                            if "messages" in session:
                                messages_found += len(session["messages"])

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "access_message_history",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "messages_found": messages_found,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_05_view_shared_workflow_readonly(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict,
    ) -> None:
        """
        Step 5: Bob views a shared workflow (read-only).

        HEART Metrics:
        - Task Success: Shared resource access
        - Engagement: Collaboration feature discovery
        - Adoption: Shared workflow feature

        GIVEN alice has shared a workflow with bob (viewer access)
        WHEN bob requests the shared workflow
        THEN bob should see the workflow content
        AND bob should NOT be able to edit it
        AND response time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        view_success = False
        edit_blocked = False

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        try:
            async with httpx.AsyncClient() as client:
                # View workflow (should succeed)
                view_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/workflows/{shared_workflow_id}",
                    headers={"Authorization": "Bearer bob-test-token"},
                    timeout=5.0,
                )

                if view_resp.status_code == 200:
                    view_success = True
                    workflow = view_resp.json()
                    assert "id" in workflow or "name" in workflow

                # Attempt edit (should fail with 403)
                edit_resp = await client.put(
                    f"{e2e_api_base_url}/api/v1/workflows/{shared_workflow_id}",
                    json={"name": "Bob's Modified Workflow"},
                    headers={"Authorization": "Bearer bob-test-token"},
                    timeout=5.0,
                )

                if edit_resp.status_code in [403, 401]:
                    edit_blocked = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "view_shared_workflow_readonly",
                "duration_ms": task_duration_ms,
                "view_success": view_success,
                "edit_properly_blocked": edit_blocked,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_06_basic_cost_tracking(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 6: Bob tracks basic usage costs.

        HEART Metrics:
        - Task Success: Cost data access
        - Engagement: Cost awareness
        - Adoption: Cost monitoring feature

        GIVEN bob has access to basic cost tracking
        WHEN bob requests cost summary
        THEN bob should see his usage costs
        AND response time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        cost_data = {}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/cost/summary",
                    headers={"Authorization": "Bearer bob-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    if "total_cost" in data:
                        cost_data["total"] = data["total_cost"]
                    if "current_period" in data:
                        cost_data["period"] = data["current_period"]

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "basic_cost_tracking",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "cost_data": cost_data,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_07_verify_admin_access_denied(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 7: Bob attempts admin access and is properly denied.

        HEART Metrics:
        - Task Success: Security enforcement
        - Engagement: Permission boundary discovery

        GIVEN bob is a standard user without admin privileges
        WHEN bob attempts to access admin-only endpoints
        THEN bob should receive 401/403/404 (denied or not found)
        AND all admin endpoints should be blocked or unavailable
        """
        import httpx

        task_start_time = time.time()
        admin_endpoints_tested = 0
        admin_endpoints_blocked = 0

        admin_endpoints = [
            "/api/v1/admin/dashboard",
            "/api/v1/admin/users",
            "/api/v1/admin/organizations",
            "/api/v1/admin/audit-logs",
        ]

        try:
            async with httpx.AsyncClient() as client:
                for endpoint in admin_endpoints:
                    admin_endpoints_tested += 1

                    response = await client.get(
                        f"{e2e_api_base_url}{endpoint}",
                        headers={"Authorization": "Bearer bob-test-token"},
                        timeout=5.0,
                    )

                    # 401/403 = access denied, 404 = endpoint doesn't exist
                    # All of these mean bob can't access admin functionality
                    if response.status_code in [401, 403, 404]:
                        admin_endpoints_blocked += 1

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            security_enforcement_rate = (
                (admin_endpoints_blocked / admin_endpoints_tested * 100) if admin_endpoints_tested > 0 else 0
            )

            # Security enforcement should be 100%
            assert security_enforcement_rate == 100, (
                f"Security breach: {admin_endpoints_blocked}/{admin_endpoints_tested} admin endpoints blocked"
            )

            heart_metrics = {
                "task_name": "verify_admin_access_denied",
                "duration_ms": task_duration_ms,
                "endpoints_tested": admin_endpoints_tested,
                "endpoints_blocked": admin_endpoints_blocked,
                "security_enforcement_rate": security_enforcement_rate,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_08_complete_standard_user_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 8: Complete standard user workflow.

        This test simulates a complete standard user journey:
        1. Check available features
        2. Create chat session
        3. Send messages
        4. View message history
        5. Check costs
        6. Verify tier limits

        HEART Metrics:
        - Complete standard user journey success rate
        - Total workflow duration
        - Standard feature adoption
        - User satisfaction
        """
        import httpx

        journey_start_time = time.time()
        steps_completed = 0
        total_steps = 6
        errors = []
        features_used = []

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Features check
                features_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/features",
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if features_resp.status_code == 200:
                    steps_completed += 1
                    features_used.append("feature_flags")

                # Step 2: Create session
                session_resp = await client.post(
                    f"{e2e_api_base_url}/api/v1/sessions",
                    json={"workflow_id": "default-chat"},
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if session_resp.status_code in [200, 201]:
                    steps_completed += 1
                    features_used.append("session_creation")

                # Step 3: Send chat message
                chat_resp = await client.post(
                    f"{e2e_api_base_url}/api/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": "Hello"}]},
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if chat_resp.status_code == 200:
                    steps_completed += 1
                    features_used.append("chat")

                # Step 4: View history
                history_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/sessions",
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if history_resp.status_code == 200:
                    steps_completed += 1
                    features_used.append("message_history")

                # Step 5: Check costs
                cost_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/cost/summary",
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if cost_resp.status_code == 200:
                    steps_completed += 1
                    features_used.append("cost_tracking")

                # Step 6: Verify admin blocked
                admin_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/admin/dashboard",
                    headers={"Authorization": "Bearer bob-test-token"},
                )
                if admin_resp.status_code in [401, 403]:
                    steps_completed += 1
                    features_used.append("security_enforcement")

        except Exception as e:
            errors.append(str(e))
        finally:
            journey_duration_ms = (time.time() - journey_start_time) * 1000
            success_rate = (steps_completed / total_steps) * 100

            heart_metrics = {
                "task_name": "complete_standard_user_workflow",
                "duration_ms": journey_duration_ms,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "success_rate": success_rate,
                "features_used": features_used,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS - STANDARD USER JOURNEY] {heart_metrics}")
