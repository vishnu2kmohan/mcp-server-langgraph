/**
 * Context Graph API Contract Tests (ADR-0101)
 *
 * Verifies API schema matches backend for decision trace endpoints.
 * Reference: src/mcp_server_langgraph/api/v1/context_graph.py
 *
 * Uses raw fetch() to validate API contract without RTK Query transformation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

// =============================================================================
// MSW Handler Factory for Context Graph
// =============================================================================

/**
 * Create default handlers for context graph endpoints.
 */
function setupContextGraphHandlers() {
  server.use(
    // GET /api/v1/context-graph/traces/:id - Get specific trace
    http.get("/api/v1/context-graph/traces/:traceId", ({ params }) => {
      const { traceId } = params;
      return HttpResponse.json({
        trace_id: traceId,
        run_id: "run-123",
        session_id: "session-456",
        workflow_id: null,
        project_id: null,
        timestamp: "2026-01-08T10:00:00Z",
        decision_type: "routing",
        decision_stage: "action",
        chosen_action: "search_tool",
        confidence: 0.95,
        rationale: "User query matches search pattern",
        outcome: "success",
        requires_approval: false,
        approval_status: null,
      });
    }),

    // GET /api/v1/context-graph/sessions/:id/traces - Get traces for session
    http.get(
      "/api/v1/context-graph/sessions/:sessionId/traces",
      ({ request }) => {
        // Parse pagination params (validated but not used in mock response)
        const url = new URL(request.url);
        const _limit = parseInt(url.searchParams.get("limit") ?? "100", 10);
        const _offset = parseInt(url.searchParams.get("offset") ?? "0", 10);

        return HttpResponse.json([
          {
            trace_id: "trace-001",
            timestamp: "2026-01-08T10:00:00Z",
            decision_type: "routing",
            chosen_action: "search_tool",
            confidence: 0.95,
            outcome: "success",
          },
          {
            trace_id: "trace-002",
            timestamp: "2026-01-08T10:01:00Z",
            decision_type: "tool_selection",
            chosen_action: "web_search,file_read",
            confidence: 0.87,
            outcome: "success",
          },
        ]);
      },
    ),

    // POST /api/v1/context-graph/precedents/search - Search precedents
    http.post(
      "/api/v1/context-graph/precedents/search",
      async ({ request }) => {
        const body = (await request.json()) as {
          query: string;
          decision_type?: string;
          outcome?: string;
          limit?: number;
        };

        return HttpResponse.json([
          {
            trace: {
              trace_id: "trace-abc",
              run_id: "run-789",
              session_id: "session-xyz",
              timestamp: "2026-01-07T14:00:00Z",
              decision_type: body.decision_type ?? "routing",
              decision_stage: "action",
              chosen_action: "similar_tool",
              confidence: 0.92,
              rationale: "Similar query pattern detected",
              outcome: "success",
              requires_approval: false,
            },
            similarity_score: 0.89,
          },
        ]);
      },
    ),
  );
}

// =============================================================================
// Contract Tests
// =============================================================================

describe("Context Graph API Contract", () => {
  beforeEach(() => {
    setupContextGraphHandlers();
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  describe("GET /api/v1/context-graph/traces/:traceId", () => {
    it("should return decision trace with required fields", async () => {
      const response = await fetch("/api/v1/context-graph/traces/trace-123");
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data).toHaveProperty("trace_id", "trace-123");
      expect(data).toHaveProperty("decision_type");
      expect(data).toHaveProperty("chosen_action");
      expect(data).toHaveProperty("confidence");
      expect(data).toHaveProperty("rationale");
    });

    it("should include temporal fields", async () => {
      const response = await fetch("/api/v1/context-graph/traces/trace-123");
      const data = await response.json();

      expect(data).toHaveProperty("timestamp");
      expect(data).toHaveProperty("session_id");
      expect(data).toHaveProperty("run_id");
    });

    it("should include approval fields", async () => {
      const response = await fetch("/api/v1/context-graph/traces/trace-123");
      const data = await response.json();

      expect(data).toHaveProperty("requires_approval");
      expect(data).toHaveProperty("approval_status");
    });
  });

  describe("GET /api/v1/context-graph/sessions/:sessionId/traces", () => {
    it("should return array of trace summaries", async () => {
      const response = await fetch(
        "/api/v1/context-graph/sessions/session-456/traces",
      );
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it("should include summary fields for each trace", async () => {
      const response = await fetch(
        "/api/v1/context-graph/sessions/session-456/traces",
      );
      const data = await response.json();

      const trace = data[0];
      expect(trace).toHaveProperty("trace_id");
      expect(trace).toHaveProperty("timestamp");
      expect(trace).toHaveProperty("decision_type");
      expect(trace).toHaveProperty("chosen_action");
      expect(trace).toHaveProperty("confidence");
      expect(trace).toHaveProperty("outcome");
    });

    it("should support pagination parameters", async () => {
      const response = await fetch(
        "/api/v1/context-graph/sessions/session-456/traces?limit=10&offset=5",
      );
      expect(response.ok).toBe(true);
    });
  });

  describe("POST /api/v1/context-graph/precedents/search", () => {
    it("should return precedent search results", async () => {
      const response = await fetch("/api/v1/context-graph/precedents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "deploy to kubernetes" }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    });

    it("should include trace and similarity_score for each result", async () => {
      const response = await fetch("/api/v1/context-graph/precedents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "deploy to kubernetes" }),
      });
      const data = await response.json();

      const result = data[0];
      expect(result).toHaveProperty("trace");
      expect(result).toHaveProperty("similarity_score");
      expect(result.trace).toHaveProperty("trace_id");
      expect(result.trace).toHaveProperty("decision_type");
    });

    it("should support filtering by decision_type", async () => {
      const response = await fetch("/api/v1/context-graph/precedents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
          decision_type: "tool_selection",
        }),
      });
      expect(response.ok).toBe(true);
    });

    it("should support limit parameter", async () => {
      const response = await fetch("/api/v1/context-graph/precedents/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
          limit: 5,
        }),
      });
      expect(response.ok).toBe(true);
    });
  });
});

// =============================================================================
// Schema Validation Tests
// =============================================================================

describe("Context Graph Schema Validation", () => {
  beforeEach(() => {
    setupContextGraphHandlers();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  it("should validate decision_type enum values", async () => {
    const validTypes = [
      "routing",
      "tool_selection",
      "skill_selection",
      "model_selection",
      "response",
      "approval",
      "exception",
    ];

    const response = await fetch("/api/v1/context-graph/traces/trace-123");
    const data = await response.json();

    expect(validTypes).toContain(data.decision_type);
  });

  it("should validate confidence is between 0 and 1", async () => {
    const response = await fetch("/api/v1/context-graph/traces/trace-123");
    const data = await response.json();

    expect(data.confidence).toBeGreaterThanOrEqual(0);
    expect(data.confidence).toBeLessThanOrEqual(1);
  });

  it("should validate outcome enum values", async () => {
    const validOutcomes = ["success", "failure", "partial", "pending", null];

    const response = await fetch(
      "/api/v1/context-graph/sessions/session-456/traces",
    );
    const data = await response.json();

    for (const trace of data) {
      expect(validOutcomes).toContain(trace.outcome);
    }
  });
});
