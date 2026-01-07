/**
 * API Contract Tests - Health, Metrics, Vector, and Core Endpoints
 *
 * Tests for: Health, HEART Metrics, Cost, Vector, Agent Config, Audit Log,
 * Pagination, and Session endpoints.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isHealthStatus,
  isHEARTAggregateMetrics,
  isCostSummary,
  isModelCostData,
  isCostHistoryPoint,
  isVectorCollection,
  isVectorSearchResult,
  isVectorTextUpsertResponse,
  isAgentConfig,
  isAuditLogEntry,
  isSession,
  isPaginatedResponse,
  isPagePaginatedResponse,
} from "./contract.validators.test-utils";

import type { WorkflowSummary, Project } from "../types/api";

// Helper validators for pagination tests
function isWorkflowSummary(obj: unknown): obj is WorkflowSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}

function isProject(obj: unknown): obj is Project {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// Health Endpoint Tests
// =============================================================================

describe("Health Endpoint", () => {
  it("should validate HealthStatus schema", () => {
    const validResponse = {
      status: "healthy",
      version: "1.0.0",
      uptime_seconds: 3600,
    };
    expect(isHealthStatus(validResponse)).toBe(true);
  });

  it("should reject invalid HealthStatus", () => {
    const invalidResponse = { status: "unknown" };
    expect(isHealthStatus(invalidResponse)).toBe(false);
  });

  it("should allow optional fields in HealthStatus", () => {
    const minimalResponse = { status: "healthy" };
    expect(isHealthStatus(minimalResponse)).toBe(true);
  });
});

// =============================================================================
// HEART Metrics Endpoint Tests
// =============================================================================

describe("HEART Metrics Endpoint", () => {
  it("should validate HEARTAggregateMetrics schema", () => {
    const validResponse = {
      period: "7d",
      nps_score_avg: 7.5,
      satisfaction_avg: 4.2,
      task_success_rate: 0.85,
      total_tasks_started: 100,
      total_tasks_completed: 85,
      avg_session_duration_ms: 300000,
      new_users_count: 50,
      avg_return_visits: 3.2,
    };
    expect(isHEARTAggregateMetrics(validResponse)).toBe(true);
  });

  it("should allow null values in HEART metrics", () => {
    const responseWithNulls = {
      period: "7d",
      nps_score_avg: null,
      satisfaction_avg: null,
      task_success_rate: null,
    };
    expect(isHEARTAggregateMetrics(responseWithNulls)).toBe(true);
  });
});

// =============================================================================
// Cost Endpoints Tests
// =============================================================================

describe("Cost Endpoints", () => {
  it("should validate CostSummary schema", () => {
    const validResponse = {
      total_cost: 125.5,
      total_tokens: 500000,
    };
    expect(isCostSummary(validResponse)).toBe(true);
  });

  it("should allow null total_tokens in CostSummary", () => {
    const responseWithNull = {
      total_cost: 125.5,
      total_tokens: null,
    };
    expect(isCostSummary(responseWithNull)).toBe(true);
  });

  it("should validate ModelCostData schema", () => {
    const validResponse = {
      model: "gpt-4",
      cost: 75.0,
      requests: 1000,
    };
    expect(isModelCostData(validResponse)).toBe(true);
  });

  it("should validate CostHistoryPoint schema", () => {
    const validResponse = {
      date: "2025-01-01",
      cost: 50.25,
    };
    expect(isCostHistoryPoint(validResponse)).toBe(true);
  });

  it("should validate array of CostHistoryPoint", () => {
    const validResponse = [
      { date: "2025-01-01", cost: 50.25 },
      { date: "2025-01-02", cost: 75.0 },
    ];
    expect(validResponse.every(isCostHistoryPoint)).toBe(true);
  });
});

// =============================================================================
// Vector Endpoints Tests
// =============================================================================

describe("Vector Endpoints", () => {
  it("should validate VectorCollection schema", () => {
    const validResponse = {
      name: "documents",
      vectors_count: 1000,
    };
    expect(isVectorCollection(validResponse)).toBe(true);
  });

  it("should validate VectorSearchResult schema", () => {
    const validResponse = {
      id: "point-123",
      score: 0.95,
      payload: { text: "Sample document" },
    };
    expect(isVectorSearchResult(validResponse)).toBe(true);
  });

  it("should validate VectorTextUpsertResponse schema", () => {
    const validResponse = {
      success: true,
      point_id: "point-456",
    };
    expect(isVectorTextUpsertResponse(validResponse)).toBe(true);
  });
});

// =============================================================================
// Agent Config Endpoint Tests
// =============================================================================

describe("Agent Config Endpoint", () => {
  it("should validate AgentConfig schema", () => {
    const validResponse = {
      model: "gpt-4",
      provider: "openai",
      temperature: 0.7,
      verification_enabled: true,
      tools: [{ name: "search", description: "Search the web" }],
    };
    expect(isAgentConfig(validResponse)).toBe(true);
  });

  it("should validate AgentConfig with empty tools", () => {
    const validResponse = {
      model: "claude-3",
      provider: "anthropic",
      temperature: 0.5,
      verification_enabled: false,
      tools: [],
    };
    expect(isAgentConfig(validResponse)).toBe(true);
  });
});

// =============================================================================
// Audit Log Endpoint Tests
// =============================================================================

describe("Audit Log Endpoint", () => {
  it("should validate AuditLogEntry schema", () => {
    const validResponse = {
      id: "log-123",
      timestamp: "2025-01-01T12:00:00Z",
      user_id: "user-456",
      action: "create",
      resource_type: "workflow",
      resource_id: "workflow-789",
    };
    expect(isAuditLogEntry(validResponse)).toBe(true);
  });
});

// =============================================================================
// Paginated Responses Tests
// =============================================================================

describe("Paginated Responses", () => {
  it("should validate cursor-based PaginatedResponse", () => {
    const validResponse = {
      items: [
        { id: "wf-1", name: "Workflow 1" },
        { id: "wf-2", name: "Workflow 2" },
      ],
      next_cursor: "cursor-abc",
      has_more: true,
    };
    expect(isPaginatedResponse(validResponse, isWorkflowSummary)).toBe(true);
  });

  it("should validate page-based PagePaginatedResponse", () => {
    const validResponse = {
      items: [
        { id: "proj-1", name: "Project 1" },
        { id: "proj-2", name: "Project 2" },
      ],
      total: 50,
      page: 1,
      per_page: 20,
      total_pages: 3,
    };
    expect(isPagePaginatedResponse(validResponse, isProject)).toBe(true);
  });

  it("should handle empty paginated response", () => {
    const emptyResponse = {
      items: [],
      next_cursor: null,
      has_more: false,
    };
    expect(isPaginatedResponse(emptyResponse, isWorkflowSummary)).toBe(true);
  });
});

// =============================================================================
// Session Endpoint Tests
// =============================================================================

describe("Session Endpoint", () => {
  it("should validate Session schema", () => {
    const validResponse = {
      session_id: "session-123",
      name: "Test Session",
      created_at: "2025-01-01T12:00:00Z",
    };
    expect(isSession(validResponse)).toBe(true);
  });
});
