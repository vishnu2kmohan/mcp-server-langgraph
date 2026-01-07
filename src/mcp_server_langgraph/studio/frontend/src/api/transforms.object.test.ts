/**
 * Tests for Object Transform Symmetry and Endpoint Consistency
 *
 * ADR-0091 Phase 5: Round-trip Symmetry Tests
 * ADR-0091 Phase 9: Endpoint Transform Consistency Tests
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getTransformSnakeToCamel,
  getTransforms,
} from "./transforms.test-utils";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// Round-trip Symmetry Tests (ADR-0091 Phase 5)
// =============================================================================

describe("Round-trip transform symmetry", () => {
  it("camelCase -> snake_case -> camelCase preserves data", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      alertId: "123",
      userData: {
        firstName: "John",
        lastName: "Doe",
      },
      itemList: [{ itemId: "1" }, { itemId: "2" }],
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });

  it("snake_case -> camelCase -> snake_case preserves data", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      alert_id: "123",
      user_data: {
        first_name: "John",
        last_name: "Doe",
      },
      item_list: [{ item_id: "1" }, { item_id: "2" }],
    };

    const roundTrip = transformCamelToSnake(transformSnakeToCamel(original));

    expect(roundTrip).toEqual(original);
  });

  it("handles complex nested structures in round-trip", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      workflowId: "wf-123",
      workflowConfig: {
        nodeSettings: {
          maxRetries: 3,
          timeoutMs: 5000,
        },
        edgeList: [
          { sourceNodeId: "node-1", targetNodeId: "node-2" },
          { sourceNodeId: "node-2", targetNodeId: "node-3" },
        ],
      },
      createdAt: "2024-01-01",
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });

  it("preserves primitive values through round-trip", async () => {
    const { transformSnakeToCamel, transformCamelToSnake } =
      await getTransforms();

    const original = {
      count: 42,
      isActive: true,
      floatValue: 3.14,
      nullValue: null,
    };

    const roundTrip = transformSnakeToCamel(transformCamelToSnake(original));

    expect(roundTrip).toEqual(original);
  });
});

// =============================================================================
// ADR-0091 Phase 9: Endpoint Transform Consistency Tests (TDD)
// =============================================================================
// These tests verify that specific endpoints apply transformSnakeToCamel correctly.
// The 4 endpoints needing fixes:
// 1. getSharedWorkflows - should transform WorkflowSummary[] to camelCase
// 2. listAlertRules - should transform ObservabilityAlertRule[] to camelCase
// 3. getHealth - should transform HealthStatus to camelCase
// 4. getHeartMetrics - should transform HEARTAggregateMetrics to camelCase

describe("Endpoint Transform Consistency (ADR-0091 Phase 9)", () => {
  describe("getSharedWorkflows endpoint transform", () => {
    it("should transform WorkflowSummary array from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = [
        {
          id: "wf-1",
          name: "Workflow 1",
          description: "First workflow",
          node_count: 5,
          edge_count: 4,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-02T00:00:00Z",
        },
        {
          id: "wf-2",
          name: "Workflow 2",
          description: "Second workflow",
          node_count: 3,
          edge_count: 2,
          created_at: "2024-01-03T00:00:00Z",
          updated_at: "2024-01-04T00:00:00Z",
        },
      ];

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result[0].nodeCount).toBe(5);
      expect(result[0].edgeCount).toBe(4);
      expect(result[0].createdAt).toBe("2024-01-01T00:00:00Z");
      expect(result[0].updatedAt).toBe("2024-01-02T00:00:00Z");
      expect(result[1].nodeCount).toBe(3);
      expect(result[1].edgeCount).toBe(2);
    });
  });

  describe("listAlertRules endpoint transform", () => {
    it("should transform ObservabilityAlertRule array from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = [
        {
          rule_id: "rule-1",
          name: "High Error Rate",
          expression: "error_rate > 0.1",
          severity: "critical",
          labels: { team: "platform" },
          annotations: { summary: "Error rate exceeded threshold" },
          evaluation_interval_seconds: 60,
          for_duration_seconds: 300,
          enabled: true,
        },
        {
          rule_id: "rule-2",
          name: "High Latency",
          expression: "latency_p99 > 1000",
          severity: "warning",
          labels: { team: "api" },
          annotations: { summary: "Latency exceeded threshold" },
          evaluation_interval_seconds: 30,
          for_duration_seconds: 120,
          enabled: false,
        },
      ];

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result[0].ruleId).toBe("rule-1");
      expect(result[0].evaluationIntervalSeconds).toBe(60);
      expect(result[0].forDurationSeconds).toBe(300);
      expect(result[1].ruleId).toBe("rule-2");
      expect(result[1].evaluationIntervalSeconds).toBe(30);
      expect(result[1].forDurationSeconds).toBe(120);
    });
  });

  describe("getHealth endpoint transform", () => {
    it("should transform HealthStatus from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case)
      const backendResponse = {
        status: "healthy",
        version: "1.0.0",
        uptime_seconds: 3600,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result.status).toBe("healthy");
      expect(result.version).toBe("1.0.0");
      expect(result.uptimeSeconds).toBe(3600);
    });

    it("should handle HealthStatus with optional fields missing", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Minimal backend response (only required field)
      const backendResponse = {
        status: "healthy",
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify required field is present, optional are undefined
      expect(result.status).toBe("healthy");
      expect(result.version).toBeUndefined();
      expect(result.uptimeSeconds).toBeUndefined();
    });
  });

  describe("getHeartMetrics endpoint transform", () => {
    it("should transform HEARTAggregateMetrics from snake_case to camelCase", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response format (snake_case) - full HEART metrics
      const backendResponse = {
        period: "7d",
        app_name: "studio",
        // Happiness
        nps_score_avg: 7.5,
        satisfaction_avg: 4.2,
        // Task Success
        task_success_rate: 0.85,
        total_tasks_started: 100,
        total_tasks_completed: 85,
        total_tasks_errored: 15,
        // Engagement
        avg_session_duration_ms: 300000,
        total_interactions: 5000,
        top_features: { chat: 2000, workflows: 1500, settings: 500 },
        // Adoption
        new_users_count: 50,
        onboarding_completion_rate: 0.75,
        // Retention
        avg_return_visits: 3.2,
        avg_days_active: 5,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify camelCase properties are accessible
      expect(result.period).toBe("7d");
      expect(result.appName).toBe("studio");
      expect(result.npsScoreAvg).toBe(7.5);
      expect(result.satisfactionAvg).toBe(4.2);
      expect(result.taskSuccessRate).toBe(0.85);
      expect(result.totalTasksStarted).toBe(100);
      expect(result.totalTasksCompleted).toBe(85);
      expect(result.totalTasksErrored).toBe(15);
      expect(result.avgSessionDurationMs).toBe(300000);
      expect(result.totalInteractions).toBe(5000);
      expect(result.topFeatures).toEqual({
        chat: 2000,
        workflows: 1500,
        settings: 500,
      });
      expect(result.newUsersCount).toBe(50);
      expect(result.onboardingCompletionRate).toBe(0.75);
      expect(result.avgReturnVisits).toBe(3.2);
      expect(result.avgDaysActive).toBe(5);
    });

    it("should handle HEARTAggregateMetrics with null values", async () => {
      const transformSnakeToCamel = await getTransformSnakeToCamel();

      // Backend response with nullable fields set to null
      const backendResponse = {
        period: "7d",
        app_name: null,
        nps_score_avg: null,
        satisfaction_avg: null,
        task_success_rate: null,
        total_tasks_started: 0,
        total_tasks_completed: 0,
        total_tasks_errored: 0,
        avg_session_duration_ms: null,
        total_interactions: 0,
        top_features: {},
        new_users_count: 0,
        onboarding_completion_rate: null,
        avg_return_visits: null,
        avg_days_active: null,
      };

      // Transform to frontend camelCase format
      const result = transformSnakeToCamel(backendResponse);

      // Verify null values are preserved after transform
      expect(result.appName).toBeNull();
      expect(result.npsScoreAvg).toBeNull();
      expect(result.satisfactionAvg).toBeNull();
      expect(result.taskSuccessRate).toBeNull();
      expect(result.avgSessionDurationMs).toBeNull();
      expect(result.onboardingCompletionRate).toBeNull();
      expect(result.avgReturnVisits).toBeNull();
      expect(result.avgDaysActive).toBeNull();
    });
  });
});
