"""
Integration tests for Organizational Cost Attribution E2E.

Tests the full flow of cost recording and querying with organizational
hierarchy fields (organization_id, project_id, team_id).

These tests verify:
1. Cost records are stored with organizational fields
2. Cost queries filter correctly by organization
3. Cost aggregation works across organizational hierarchy
4. LiteLLM callback integration with organizational metadata
"""

import gc
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage
from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

pytestmark = [pytest.mark.integration, pytest.mark.cost]


@pytest.mark.xdist_group(name="cost_org_e2e")
class TestOrganizationalCostE2E:
    """End-to-end tests for organizational cost attribution."""

    def teardown_method(self) -> None:
        """Force GC and reset singletons."""
        from mcp_server_langgraph.api.v1.cost import reset_cost_service

        reset_cost_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_and_query_by_organization(self) -> None:
        """
        GIVEN cost records with different organization_ids
        WHEN querying by organization filter
        THEN only records for that organization are returned
        """
        storage = MemoryCostStorage()

        # Record costs for two organizations
        record_org_a = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="sess-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.01"),
            feature="chat",
            organization_id="organization:acme",
            project_id="project:backend",
            team_id="team:platform",
        )

        record_org_b = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:bob",
            session_id="sess-2",
            model="gpt-4",
            provider="openai",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            estimated_cost_usd=Decimal("0.02"),
            feature="chat",
            organization_id="organization:globex",
            project_id="project:frontend",
            team_id="team:ui",
        )

        await storage.store(record_org_a)
        await storage.store(record_org_b)

        # Query by organization
        records, _ = await storage.get_records(filters={"organization_id": "organization:acme"})

        assert len(records) == 1
        assert records[0].organization_id == "organization:acme"
        assert records[0].user_id == "user:alice"

    @pytest.mark.asyncio
    async def test_record_and_query_by_project(self) -> None:
        """
        GIVEN cost records with different project_ids
        WHEN querying by project filter
        THEN only records for that project are returned
        """
        storage = MemoryCostStorage()

        # Record costs for two projects
        for project, user in [("project:backend", "user:dev1"), ("project:frontend", "user:dev2")]:
            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=user,
                session_id=f"sess-{project}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=Decimal("0.01"),
                feature="chat",
                organization_id="organization:acme",
                project_id=project,
                team_id=None,
            )
            await storage.store(record)

        # Query by project
        records, _ = await storage.get_records(filters={"project_id": "project:backend"})

        assert len(records) == 1
        assert records[0].project_id == "project:backend"

    @pytest.mark.asyncio
    async def test_record_and_query_by_team(self) -> None:
        """
        GIVEN cost records with different team_ids
        WHEN querying by team filter
        THEN only records for that team are returned
        """
        storage = MemoryCostStorage()

        # Record costs for two teams
        for team, user in [("team:platform", "user:eng1"), ("team:data", "user:eng2")]:
            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=user,
                session_id=f"sess-{team}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=Decimal("0.01"),
                feature="chat",
                organization_id="organization:acme",
                project_id="project:backend",
                team_id=team,
            )
            await storage.store(record)

        # Query by team
        records, _ = await storage.get_records(filters={"team_id": "team:platform"})

        assert len(records) == 1
        assert records[0].team_id == "team:platform"

    @pytest.mark.asyncio
    async def test_cost_service_aggregation_by_organization(self) -> None:
        """
        GIVEN multiple cost records for different organizations
        WHEN calling get_cost_by_organization
        THEN costs are correctly aggregated per organization
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        storage = MemoryCostStorage()

        # Record multiple costs for organizations
        for i, org in enumerate(["organization:acme", "organization:acme", "organization:globex"]):
            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=f"user:{i}",
                session_id=f"sess-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=Decimal("10.00"),
                feature="chat",
                organization_id=org,
            )
            await storage.store(record)

        service = CostServiceImpl(storage=storage)
        result = await service.get_cost_by_organization()

        # Should have 2 organizations
        assert len(result) == 2

        # Find acme result
        acme_result = next((r for r in result if r["organization_id"] == "organization:acme"), None)
        assert acme_result is not None
        assert acme_result["request_count"] == 2
        assert acme_result["total_cost"] == 20.0

        # Find globex result
        globex_result = next((r for r in result if r["organization_id"] == "organization:globex"), None)
        assert globex_result is not None
        assert globex_result["request_count"] == 1
        assert globex_result["total_cost"] == 10.0

    @pytest.mark.asyncio
    async def test_cost_service_aggregation_by_project(self) -> None:
        """
        GIVEN multiple cost records for different projects within an organization
        WHEN calling get_cost_by_project with organization filter
        THEN costs are correctly aggregated per project
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        storage = MemoryCostStorage()

        # Record costs for different projects
        projects = ["project:backend", "project:backend", "project:frontend"]
        for i, proj in enumerate(projects):
            record = TokenUsage(
                timestamp=datetime.now(UTC),
                user_id=f"user:{i}",
                session_id=f"sess-{i}",
                model="gpt-4",
                provider="openai",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=Decimal("5.00"),
                feature="chat",
                organization_id="organization:acme",
                project_id=proj,
            )
            await storage.store(record)

        service = CostServiceImpl(storage=storage)
        result = await service.get_cost_by_project(organization_id="organization:acme")

        # Should have 2 projects
        assert len(result) == 2

        # Find backend result
        backend_result = next((r for r in result if r["project_id"] == "project:backend"), None)
        assert backend_result is not None
        assert backend_result["request_count"] == 2
        assert backend_result["total_cost"] == 10.0

    @pytest.mark.asyncio
    async def test_litellm_callback_records_org_metadata(self) -> None:
        """
        GIVEN a LiteLLM callback with organizational metadata
        WHEN the callback processes a success event
        THEN the cost is recorded with organizational fields
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        # Mock the cost collector
        mock_collector = AsyncMock(return_value=None)  # noqa: async-mock-config

        callback = CostTrackingCallback()

        # Simulate LiteLLM success event with org metadata
        kwargs = {
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "response_cost": 0.05,
            "litellm_params": {
                "metadata": {
                    "user_id": "user:alice",
                    "session_id": "sess-test",
                    "feature": "chat",
                    "organization_id": "organization:acme",
                    "project_id": "project:backend",
                    "team_id": "team:platform",
                }
            },
        }

        # Mock response object with usage
        response_obj = AsyncMock(return_value=None)  # noqa: async-mock-config
        response_obj.usage = AsyncMock(return_value=None)  # noqa: async-mock-config
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            await callback.async_log_success_event(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
            )

        # Verify org metadata was passed to record_usage
        mock_collector.record_usage.assert_called_once()
        call_kwargs = mock_collector.record_usage.call_args.kwargs
        assert call_kwargs["organization_id"] == "organization:acme"
        assert call_kwargs["project_id"] == "project:backend"
        assert call_kwargs["team_id"] == "team:platform"


@pytest.mark.xdist_group(name="cost_org_e2e")
class TestJWTOrganizationExtractionE2E:
    """End-to-end tests for JWT organization extraction."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_jwt_extracts_organization_from_groups(self) -> None:
        """
        GIVEN a JWT payload with Keycloak groups
        WHEN extracting user info
        THEN organization_id is correctly parsed
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "groups": ["/org/acme", "/team/platform"],
        }

        user_info = extract_user_from_jwt_payload(payload)

        assert user_info["organization_id"] == "organization:acme"

    def test_jwt_extracts_full_hierarchy_from_groups(self) -> None:
        """
        GIVEN a JWT payload with org/project/team groups
        WHEN extracting user info
        THEN all hierarchy fields are parsed
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user-123",
            "preferred_username": "bob",
            "email": "bob@acme.com",
            "groups": ["/org/acme", "/project/backend", "/team/platform"],
        }

        user_info = extract_user_from_jwt_payload(payload)

        assert user_info["organization_id"] == "organization:acme"
        assert user_info["project_id"] == "project:backend"
        assert user_info["team_id"] == "team:platform"

    def test_jwt_direct_claims_override_groups(self) -> None:
        """
        GIVEN a JWT payload with both direct claims and groups
        WHEN extracting user info
        THEN direct claims take precedence
        """
        from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload

        payload = {
            "sub": "user-123",
            "preferred_username": "carol",
            "email": "carol@acme.com",
            "organization_id": "organization:globex",  # Direct claim
            "groups": ["/org/acme"],  # Group claim (should be overridden)
        }

        user_info = extract_user_from_jwt_payload(payload)

        # Direct claim should take precedence
        assert user_info["organization_id"] == "organization:globex"


@pytest.mark.xdist_group(name="cost_allocation_tags_e2e")
class TestAllocationTagsE2E:
    """End-to-end tests for custom cost allocation tags."""

    def teardown_method(self) -> None:
        """Force GC and reset singletons."""
        from mcp_server_langgraph.api.v1.cost import reset_cost_service

        reset_cost_service()
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_with_allocation_tags(self) -> None:
        """
        GIVEN cost records with allocation tags
        WHEN storing the record
        THEN allocation tags are preserved
        """
        storage = MemoryCostStorage()

        record = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:alice",
            session_id="sess-alloc-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.01"),
            feature="chat",
            organization_id="organization:acme",
            allocation_tags={
                "environment": "production",
                "campaign": "launch-2025",
                "cost_center": "engineering",
            },
        )

        await storage.store(record)

        records, _ = await storage.get_records()
        assert len(records) == 1
        assert records[0].allocation_tags == {
            "environment": "production",
            "campaign": "launch-2025",
            "cost_center": "engineering",
        }

    @pytest.mark.asyncio
    async def test_allocation_tags_combined_with_org_hierarchy(self) -> None:
        """
        GIVEN cost records with both org hierarchy and allocation tags
        WHEN querying by organization
        THEN both organizational and tag data are returned
        """
        storage = MemoryCostStorage()

        # Record with both org hierarchy and custom tags
        record = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user:bob",
            session_id="sess-alloc-2",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            estimated_cost_usd=Decimal("0.02"),
            feature="summarization",
            organization_id="organization:globex",
            project_id="project:ml-pipeline",
            team_id="team:data-science",
            allocation_tags={
                "environment": "staging",
                "feature": "document-summary",
            },
        )

        await storage.store(record)

        # Query by organization
        records, _ = await storage.get_records(filters={"organization_id": "organization:globex"})

        assert len(records) == 1
        rec = records[0]
        # Org hierarchy preserved
        assert rec.organization_id == "organization:globex"
        assert rec.project_id == "project:ml-pipeline"
        assert rec.team_id == "team:data-science"
        # Custom tags preserved
        assert rec.allocation_tags["environment"] == "staging"
        assert rec.allocation_tags["feature"] == "document-summary"

    @pytest.mark.asyncio
    async def test_litellm_callback_records_allocation_tags(self) -> None:
        """
        GIVEN a LiteLLM callback with allocation_tags in metadata
        WHEN the callback processes a success event
        THEN the cost is recorded with allocation_tags
        """
        from mcp_server_langgraph.monitoring.litellm_cost_callback import (
            CostTrackingCallback,
        )

        mock_collector = AsyncMock(return_value=None)  # noqa: async-mock-config
        callback = CostTrackingCallback()

        kwargs = {
            "model": "gpt-4",
            "custom_llm_provider": "openai",
            "response_cost": 0.03,
            "litellm_params": {
                "metadata": {
                    "user_id": "user:carol",
                    "session_id": "sess-alloc-3",
                    "feature": "code-gen",
                    "organization_id": "organization:techcorp",
                    "allocation_tags": {
                        "environment": "development",
                        "experiment": "llm-benchmark-v2",
                    },
                }
            },
        }

        response_obj = AsyncMock(return_value=None)  # noqa: async-mock-config
        response_obj.usage = AsyncMock(return_value=None)  # noqa: async-mock-config
        response_obj.usage.prompt_tokens = 150
        response_obj.usage.completion_tokens = 75

        with patch(
            "mcp_server_langgraph.monitoring.cost_tracker.get_cost_collector",
            return_value=mock_collector,
        ):
            await callback.async_log_success_event(
                kwargs=kwargs,
                response_obj=response_obj,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
            )

        mock_collector.record_usage.assert_called_once()
        call_kwargs = mock_collector.record_usage.call_args.kwargs
        assert call_kwargs.get("allocation_tags") == {
            "environment": "development",
            "experiment": "llm-benchmark-v2",
        }


@pytest.mark.xdist_group(name="budget_crud_e2e")
class TestBudgetCRUDE2E:
    """End-to-end tests for budget CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC and reset budget storage."""
        from mcp_server_langgraph.monitoring.budget_storage import _reset_budget_storage

        _reset_budget_storage()
        gc.collect()

    @pytest.mark.asyncio
    async def test_budget_full_crud_lifecycle(self) -> None:
        """
        GIVEN an empty budget storage
        WHEN creating, reading, updating, and deleting a budget
        THEN all operations work correctly
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            MemoryBudgetStorage,
            get_budget_storage,
            _reset_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        # Reset to start fresh
        _reset_budget_storage()
        storage = get_budget_storage()
        assert isinstance(storage, MemoryBudgetStorage)

        # CREATE
        budget = Budget(
            entity_type="organization",
            entity_id="organization:test-org",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.0,
            name="Test Org Budget",
        )
        await storage.save_budget(budget)

        # READ
        retrieved = await storage.get_budget("organization", "organization:test-org")
        assert retrieved is not None
        assert retrieved.entity_id == "organization:test-org"
        assert retrieved.monthly_limit_usd == Decimal("1000.00")

        # LIST
        all_budgets = await storage.list_budgets()
        assert len(all_budgets) == 1

        # UPDATE
        budget.monthly_limit_usd = Decimal("2000.00")
        budget.name = "Updated Test Org Budget"
        await storage.save_budget(budget)

        updated = await storage.get_budget("organization", "organization:test-org")
        assert updated is not None
        assert updated.monthly_limit_usd == Decimal("2000.00")
        assert updated.name == "Updated Test Org Budget"

        # DELETE
        deleted = await storage.delete_budget("organization", "organization:test-org")
        assert deleted is True

        # Verify deleted
        gone = await storage.get_budget("organization", "organization:test-org")
        assert gone is None

    @pytest.mark.asyncio
    async def test_budget_list_filters_by_entity_type(self) -> None:
        """
        GIVEN budgets for different entity types
        WHEN listing with entity_type filter
        THEN only matching budgets are returned
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            get_budget_storage,
            _reset_budget_storage,
        )
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        _reset_budget_storage()
        storage = get_budget_storage()

        # Create budgets for different entity types
        entity_types = ["organization", "project", "team", "user"]
        for entity_type in entity_types:
            budget = Budget(
                entity_type=entity_type,
                entity_id=f"{entity_type}:test-{entity_type}",
                monthly_limit_usd=Decimal("500.00"),
            )
            await storage.save_budget(budget)

        # List all
        all_budgets = await storage.list_budgets()
        assert len(all_budgets) == 4

        # List by type
        org_budgets = await storage.list_budgets(entity_type="organization")
        assert len(org_budgets) == 1
        assert org_budgets[0].entity_type == "organization"

        user_budgets = await storage.list_budgets(entity_type="user")
        assert len(user_budgets) == 1
        assert user_budgets[0].entity_type == "user"

    @pytest.mark.asyncio
    async def test_budget_delete_nonexistent_returns_false(self) -> None:
        """
        GIVEN no budget exists for an entity
        WHEN deleting that budget
        THEN False is returned
        """
        from mcp_server_langgraph.monitoring.budget_storage import (
            get_budget_storage,
            _reset_budget_storage,
        )

        _reset_budget_storage()
        storage = get_budget_storage()

        deleted = await storage.delete_budget("organization", "organization:nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_budget_api_endpoints_integration(self) -> None:
        """
        GIVEN the cost router with budget endpoints
        WHEN using the full CRUD flow via HTTP
        THEN all operations work correctly
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from mcp_server_langgraph.api.v1.cost import cost_router
        from mcp_server_langgraph.monitoring.budget_storage import _reset_budget_storage

        _reset_budget_storage()

        app = FastAPI()
        app.include_router(cost_router, prefix="/api/v1")
        client = TestClient(app)

        # CREATE
        response = client.post(
            "/api/v1/cost/budgets",
            json={
                "entity_type": "project",
                "entity_id": "project:api-test",
                "monthly_limit_usd": "750.00",
                "warning_threshold": 0.75,
                "critical_threshold": 0.95,
                "name": "API Test Budget",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["entity_id"] == "project:api-test"
        assert data["monthly_limit_usd"] == "750.00"

        # LIST
        response = client.get("/api/v1/cost/budgets")
        assert response.status_code == 200
        data = response.json()
        assert len(data["budgets"]) == 1

        # UPDATE
        response = client.put(
            "/api/v1/cost/budgets/project/project:api-test",
            json={"monthly_limit_usd": "1500.00", "name": "Updated API Budget"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_limit_usd"] == "1500.00"
        assert data["name"] == "Updated API Budget"

        # DELETE
        response = client.delete("/api/v1/cost/budgets/project/project:api-test")
        assert response.status_code == 204

        # Verify deleted
        response = client.get("/api/v1/cost/budgets")
        assert response.status_code == 200
        data = response.json()
        assert len(data["budgets"]) == 0
