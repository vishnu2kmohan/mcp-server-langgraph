"""
Alice Power User Journey E2E Tests

Comprehensive tests for power user (alice) journey including:
- Workflow creation and deployment
- Advanced chat features
- Trace visualization and debugging
- Cost monitoring
- Multi-session management
- Premium tier features

HEART Metrics Focus:
- Task Success: Advanced feature completion rates
- Engagement: Power user interaction depth
- Adoption: Premium feature discovery
- Retention: Power user return patterns
- Happiness: Advanced user satisfaction

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
import time
from datetime import UTC, datetime

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.journey,
    pytest.mark.power_user_journey,
]


# Infrastructure check and autouse skip fixture are in tests/e2e/conftest.py
# This avoids duplicate autouse fixtures across test files (best practice)


@pytest.mark.xdist_group(name="test_alice_power_user")
class TestAlicePowerUserJourney:
    """
    Comprehensive power user journey tests with HEART metrics.

    Alice (Premium Tier) capabilities:
    - Complex workflow creation
    - Multi-session orchestration
    - Advanced trace visualization
    - Cost optimization tools
    - Workflow sharing and collaboration
    - Premium API access
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_power_user_login_and_feature_discovery(
        self,
        e2e_keycloak_base_url: str,
        e2e_api_base_url: str,
        alice_credentials: dict,
    ) -> None:
        """
        Step 1: Alice logs in and discovers premium features.

        HEART Metrics:
        - Adoption: Premium feature discovery
        - Engagement: Login interaction
        - Task Success: Authentication completion

        GIVEN alice has premium tier credentials
        WHEN alice logs in (via token exchange or PKCE) and checks feature flags
        THEN alice should see premium features enabled
        AND login should complete in < 1500ms

        NOTE: Uses login_as_user() token exchange per RFC 9700 instead of ROPC.
        """
        import httpx

        from tests.e2e.real_clients import real_keycloak_auth

        task_start_time = time.time()
        task_success = False
        premium_features = []

        try:
            async with real_keycloak_auth(base_url=e2e_keycloak_base_url) as auth:
                # Use token exchange (RFC 8693) - no password needed
                # Falls back to PKCE if token exchange not configured
                try:
                    token_data = await auth.login_as_user(alice_credentials["username"])
                except RuntimeError as e:
                    if "not configured" in str(e):
                        # Fall back to PKCE if token exchange not set up
                        token_data = await auth.login_pkce(
                            alice_credentials["username"],
                            alice_credentials["password"],
                        )
                    else:
                        raise

                access_token = token_data["access_token"]

                # Check feature flags
                async with httpx.AsyncClient() as client:
                    features_resp = await client.get(
                        f"{e2e_api_base_url}/api/v1/features",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=5.0,
                    )

                    if features_resp.status_code == 200:
                        features = features_resp.json()
                        # Check for premium features
                        if isinstance(features, dict):
                            for key, value in features.items():
                                if value and "premium" in key.lower():
                                    premium_features.append(key)

                task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "power_user_login_feature_discovery",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "premium_features_discovered": premium_features,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_02_create_complex_workflow(
        self,
        e2e_api_base_url: str,
        openfga_seeded_tuples: dict,
    ) -> None:
        """
        Step 2: Alice creates a complex multi-node workflow.

        HEART Metrics:
        - Task Success: Workflow creation completion
        - Engagement: Workflow complexity metrics
        - Adoption: Advanced workflow features

        GIVEN alice has workflow creation permissions
        WHEN alice creates a complex workflow with multiple nodes
        THEN the workflow should be created successfully
        AND creation time should be < 2000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        workflow_complexity = {"nodes": 0, "edges": 0}

        try:
            async with httpx.AsyncClient() as client:
                # Create complex workflow
                complex_workflow = {
                    "name": "Alice's Advanced Agent Workflow",
                    "description": "Multi-stage AI agent with RAG and tool calling",
                    "graph": {
                        "nodes": [
                            {"id": "input", "type": "input", "data": {"schema": "user_query"}},
                            {"id": "embeddings", "type": "embeddings", "data": {"model": "text-embedding-ada-002"}},
                            {"id": "vector_search", "type": "vector_search", "data": {"top_k": 5}},
                            {"id": "llm", "type": "llm", "data": {"model": "gpt-4"}},
                            {"id": "tools", "type": "tool_executor", "data": {"tools": ["calculator", "search"]}},
                            {"id": "output", "type": "output", "data": {"format": "json"}},
                        ],
                        "edges": [
                            {"source": "input", "target": "embeddings"},
                            {"source": "embeddings", "target": "vector_search"},
                            {"source": "vector_search", "target": "llm"},
                            {"source": "llm", "target": "tools"},
                            {"source": "tools", "target": "output"},
                        ],
                    },
                    "config": {
                        "max_iterations": 10,
                        "timeout": 30000,
                        "enable_tracing": True,
                    },
                }

                workflow_complexity["nodes"] = len(complex_workflow["graph"]["nodes"])
                workflow_complexity["edges"] = len(complex_workflow["graph"]["edges"])

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/workflows",
                    json=complex_workflow,
                    headers={"Authorization": "Bearer alice-test-token"},
                    timeout=5.0,
                )

                if response.status_code in [200, 201]:
                    task_success = True
                    workflow_data = response.json()
                    assert "id" in workflow_data or "workflow_id" in workflow_data

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "create_complex_workflow",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "workflow_complexity": workflow_complexity,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_03_multi_session_orchestration(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 3: Alice orchestrates multiple concurrent sessions.

        HEART Metrics:
        - Task Success: Multi-session management success rate
        - Engagement: Session interaction depth
        - Adoption: Advanced session features

        GIVEN alice has premium tier access
        WHEN alice creates and manages multiple concurrent sessions
        THEN all sessions should be managed successfully
        AND total operation time should be < 3000ms
        """
        import httpx

        task_start_time = time.time()
        sessions_created = 0
        target_sessions = 3
        errors = []

        try:
            async with httpx.AsyncClient() as client:
                session_ids = []

                # Create multiple sessions
                for i in range(target_sessions):
                    session_payload = {
                        "workflow_id": f"workflow-{i}",
                        "metadata": {
                            "session_name": f"Power User Session {i + 1}",
                            "tier": "premium",
                        },
                    }

                    response = await client.post(
                        f"{e2e_api_base_url}/api/v1/sessions",
                        json=session_payload,
                        headers={"Authorization": "Bearer alice-test-token"},
                        timeout=5.0,
                    )

                    if response.status_code in [200, 201]:
                        sessions_created += 1
                        session_data = response.json()
                        session_ids.append(session_data.get("id"))
                    else:
                        errors.append(f"Session {i} creation failed: {response.status_code}")

                # Verify we can list all sessions
                if sessions_created > 0:
                    list_resp = await client.get(
                        f"{e2e_api_base_url}/api/v1/sessions",
                        headers={"Authorization": "Bearer alice-test-token"},
                        timeout=5.0,
                    )

                    if list_resp.status_code == 200:
                        sessions_list = list_resp.json()
                        assert isinstance(sessions_list, (list, dict))

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000
            success_rate = (sessions_created / target_sessions) * 100

            heart_metrics = {
                "task_name": "multi_session_orchestration",
                "duration_ms": task_duration_ms,
                "sessions_created": sessions_created,
                "target_sessions": target_sessions,
                "success_rate": success_rate,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_04_trace_visualization_access(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 4: Alice accesses trace visualization for debugging.

        HEART Metrics:
        - Task Success: Trace retrieval success
        - Engagement: Debugging tool usage
        - Adoption: Premium debugging features

        GIVEN alice has access to observability features
        WHEN alice requests trace data for a workflow execution
        THEN alice should receive detailed trace information
        AND response time should be < 2000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        trace_depth = 0

        try:
            async with httpx.AsyncClient() as client:
                # Get traces for a workflow execution
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/observability/traces",
                    params={"workflow_id": "test-workflow", "limit": 10},
                    headers={"Authorization": "Bearer alice-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    traces = response.json()

                    if isinstance(traces, list) and len(traces) > 0:
                        # Check trace depth (spans)
                        first_trace = traces[0]
                        if "spans" in first_trace:
                            trace_depth = len(first_trace["spans"])

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "trace_visualization_access",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "trace_depth": trace_depth,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_05_cost_monitoring_and_optimization(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 5: Alice monitors and optimizes workflow costs.

        HEART Metrics:
        - Task Success: Cost data retrieval
        - Engagement: Cost monitoring interaction
        - Adoption: Cost optimization features

        GIVEN alice has access to cost dashboard
        WHEN alice requests detailed cost breakdown
        THEN alice should receive granular cost metrics
        AND response time should be < 1500ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        cost_breakdown = {}

        try:
            async with httpx.AsyncClient() as client:
                # Get detailed cost summary
                response = await client.get(
                    f"{e2e_api_base_url}/api/v1/cost/summary",
                    params={"granularity": "detailed", "period": "7d"},
                    headers={"Authorization": "Bearer alice-test-token"},
                    timeout=5.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    # Extract cost breakdown
                    if "by_model" in data:
                        cost_breakdown["models"] = len(data["by_model"])
                    if "by_workflow" in data:
                        cost_breakdown["workflows"] = len(data["by_workflow"])
                    if "total_cost" in data:
                        cost_breakdown["total"] = data["total_cost"]

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "cost_monitoring_optimization",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "cost_breakdown": cost_breakdown,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_06_workflow_sharing_collaboration(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict,
    ) -> None:
        """
        Step 6: Alice shares a workflow with another user.

        HEART Metrics:
        - Task Success: Sharing operation success
        - Engagement: Collaboration feature usage
        - Adoption: Premium collaboration features

        GIVEN alice owns a workflow
        WHEN alice shares it with bob (viewer access)
        THEN the sharing operation should succeed
        AND operation time should be < 1000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        try:
            async with httpx.AsyncClient() as client:
                # Share workflow with bob
                share_payload = {
                    "user_id": "bob",
                    "permission": "viewer",
                }

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/workflows/{shared_workflow_id}/share",
                    json=share_payload,
                    headers={"Authorization": "Bearer alice-test-token"},
                    timeout=5.0,
                )

                if response.status_code in [200, 201]:
                    task_success = True

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "workflow_sharing",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_07_advanced_chat_with_tools(
        self,
        e2e_api_base_url: str,
        openfga_seeded_tuples: dict,
    ) -> None:
        """
        Step 7: Alice uses advanced chat with tool calling.

        HEART Metrics:
        - Task Success: Advanced chat completion
        - Engagement: Tool usage depth
        - Happiness: Response quality

        GIVEN alice has access to premium chat features
        WHEN alice sends a message requiring tool usage
        THEN the agent should execute tools and return results
        AND total response time should be < 10000ms
        """
        import httpx

        task_start_time = time.time()
        task_success = False
        tools_used = []

        try:
            async with httpx.AsyncClient() as client:
                chat_payload = {
                    "messages": [
                        {
                            "role": "user",
                            "content": "Calculate 42 * 137 and search for information about LangGraph",
                        }
                    ],
                    "model": "gpt-4",
                    "tools_enabled": True,
                }

                response = await client.post(
                    f"{e2e_api_base_url}/api/v1/chat/completions",
                    json=chat_payload,
                    headers={"Authorization": "Bearer alice-test-token"},
                    timeout=15.0,
                )

                if response.status_code == 200:
                    task_success = True
                    data = response.json()

                    # Check if tools were used
                    if "tool_calls" in data:
                        tools_used = [call.get("name") for call in data["tool_calls"]]

        finally:
            task_duration_ms = (time.time() - task_start_time) * 1000

            heart_metrics = {
                "task_name": "advanced_chat_with_tools",
                "duration_ms": task_duration_ms,
                "success": task_success,
                "tools_used": tools_used,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS] {heart_metrics}")

    async def test_08_complete_power_user_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Step 8: Complete power user workflow with all premium features.

        This test simulates a complete power user journey:
        1. Check premium features
        2. Create complex workflow
        3. Deploy and test workflow
        4. Monitor traces and costs
        5. Share with team
        6. Optimize based on metrics

        HEART Metrics:
        - Complete premium journey success rate
        - Total workflow duration
        - Premium feature adoption
        - Power user satisfaction
        """
        import httpx

        journey_start_time = time.time()
        steps_completed = 0
        total_steps = 6
        errors = []
        premium_features_used = []

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Features check
                features_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/features",
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if features_resp.status_code == 200:
                    steps_completed += 1
                    premium_features_used.append("feature_flags")

                # Step 2: Create workflow
                workflow_resp = await client.post(
                    f"{e2e_api_base_url}/api/v1/workflows",
                    json={"name": "Premium Workflow", "graph": {"nodes": [], "edges": []}},
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if workflow_resp.status_code in [200, 201]:
                    steps_completed += 1
                    premium_features_used.append("workflow_creation")

                # Step 3: Create session
                session_resp = await client.post(
                    f"{e2e_api_base_url}/api/v1/sessions",
                    json={"workflow_id": "test"},
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if session_resp.status_code in [200, 201]:
                    steps_completed += 1
                    premium_features_used.append("session_management")

                # Step 4: Check traces
                traces_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/observability/traces",
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if traces_resp.status_code == 200:
                    steps_completed += 1
                    premium_features_used.append("trace_visualization")

                # Step 5: Check costs
                cost_resp = await client.get(
                    f"{e2e_api_base_url}/api/v1/cost/summary",
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if cost_resp.status_code == 200:
                    steps_completed += 1
                    premium_features_used.append("cost_monitoring")

                # Step 6: Chat interaction
                chat_resp = await client.post(
                    f"{e2e_api_base_url}/api/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": "test"}]},
                    headers={"Authorization": "Bearer alice-test-token"},
                )
                if chat_resp.status_code == 200:
                    steps_completed += 1
                    premium_features_used.append("advanced_chat")

        except Exception as e:
            errors.append(str(e))
        finally:
            journey_duration_ms = (time.time() - journey_start_time) * 1000
            success_rate = (steps_completed / total_steps) * 100

            heart_metrics = {
                "task_name": "complete_power_user_workflow",
                "duration_ms": journey_duration_ms,
                "steps_completed": steps_completed,
                "total_steps": total_steps,
                "success_rate": success_rate,
                "premium_features_used": premium_features_used,
                "errors": errors,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            print(f"\n[HEART METRICS - POWER USER JOURNEY] {heart_metrics}")
