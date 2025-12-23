/**
 * Agent Request API Contract Tests
 *
 * Verifies API schema matches backend for HITL agent requests.
 * Reference: src/mcp_server_langgraph/api/v1/agent_requests.py
 *
 * Uses raw fetch() to validate API contract without RTK Query transformation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

// =============================================================================
// MSW Handler Factory for Agent Requests
// =============================================================================

/**
 * Create default handlers for agent request endpoints.
 * Uses server.use() to add handlers to the global MSW server.
 */
function setupAgentRequestHandlers() {
  server.use(
    // GET /api/v1/agents/requests/pending
    http.get("/api/v1/agents/requests/pending", () => {
      return HttpResponse.json({
        requests: [
          {
            request_id: "req-001",
            session_id: "session-123",
            task_id: "task-456",
            agent_name: "research_agent",
            request_type: "approval",
            confidence: 0.65,
            threshold: 0.7,
            question: "Should I execute this search?",
            proposed_action: "web_search('AI ethics')",
            trigger_reason: "low_confidence",
            placeholder: null,
            clarification_type: null,
            options: null,
            status: "pending",
            requested_at: "2024-01-15T10:30:00Z",
            responded_at: null,
            responded_by: null,
            context: { domain: "research" },
            ai_explanation: null,
          },
        ],
        count: 1,
      });
    }),

    // NOTE: Batch handlers MUST come before :id handlers to avoid path conflicts
    // POST /api/v1/agents/requests/batch/approve
    http.post("/api/v1/agents/requests/batch/approve", async ({ request }) => {
      const body = (await request.json()) as {
        request_ids: string[];
        approved_by: string;
        reason?: string;
      };

      // Simulate processing each request
      const results = body.request_ids.map((requestId) => ({
        request_id: requestId,
        success: true,
      }));

      return HttpResponse.json({
        success: true,
        processed: body.request_ids.length,
        failed: 0,
        results,
      });
    }),

    // POST /api/v1/agents/requests/batch/reject
    http.post("/api/v1/agents/requests/batch/reject", async ({ request }) => {
      const body = (await request.json()) as {
        request_ids: string[];
        rejected_by: string;
        reason?: string;
      };

      // Simulate processing each request
      const results = body.request_ids.map((requestId) => ({
        request_id: requestId,
        success: true,
      }));

      return HttpResponse.json({
        success: true,
        processed: body.request_ids.length,
        failed: 0,
        results,
      });
    }),

    // POST /api/v1/agents/requests/:id/approve
    http.post(
      "/api/v1/agents/requests/:id/approve",
      async ({ request, params }) => {
        const body = await request.json();
        return HttpResponse.json({
          request_id: params.id as string,
          status: "approved",
          message: `Request approved by ${(body as { approved_by: string }).approved_by}`,
        });
      },
    ),

    // POST /api/v1/agents/requests/:id/reject
    http.post(
      "/api/v1/agents/requests/:id/reject",
      async ({ request, params }) => {
        const body = await request.json();
        return HttpResponse.json({
          request_id: params.id as string,
          status: "rejected",
          message: `Request rejected: ${(body as { reason: string }).reason}`,
        });
      },
    ),

    // POST /api/v1/agents/requests/:id/respond
    http.post("/api/v1/agents/requests/:id/respond", async ({ params }) => {
      return HttpResponse.json({
        request_id: params.id as string,
        status: "responded",
        message: "Clarification received",
      });
    }),
  );
}

// Set up handlers before each test, reset after
beforeEach(() => {
  setupAgentRequestHandlers();
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

// =============================================================================
// Schema Type Definitions (matching backend Pydantic models)
// =============================================================================

interface AgentRequest {
  request_id: string;
  session_id: string;
  task_id: string;
  agent_name: string;
  request_type: "approval" | "clarification";
  confidence: number | null;
  threshold: number | null;
  question: string;
  proposed_action: string | null;
  trigger_reason: string | null;
  placeholder: string | null;
  clarification_type: string | null;
  options: Array<{ id: string; label: string; description?: string }> | null;
  status: "pending" | "approved" | "rejected" | "responded" | "timeout";
  requested_at: string;
  responded_at: string | null;
  responded_by: string | null;
  context: Record<string, unknown>;
  ai_explanation: AIExplanation | null;
}

interface AIExplanation {
  what_agent_wants: string;
  why_needs_approval: string;
  risk_factors: string[];
  confidence_score: number;
  recommendation: string;
}

interface PendingAgentRequestsResponse {
  requests: AgentRequest[];
  count: number;
}

interface AgentRequestActionResponse {
  request_id: string;
  status: string;
  message: string;
}

interface BatchActionResponse {
  success: boolean;
  processed: number;
  failed: number;
  results: Array<{ request_id: string; success: boolean; error?: string }>;
}

// =============================================================================
// Contract Tests
// =============================================================================

describe("Agent Request API Contract", () => {
  describe("GET /api/v1/agents/requests/pending", () => {
    it("should validate PendingAgentRequestsResponse schema", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");
      expect(response.ok).toBe(true);

      const data: PendingAgentRequestsResponse = await response.json();

      // Validate response structure
      expect(data).toHaveProperty("requests");
      expect(data).toHaveProperty("count");
      expect(Array.isArray(data.requests)).toBe(true);
      expect(typeof data.count).toBe("number");
    });

    it("should return AgentRequest objects with required fields", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");
      const data: PendingAgentRequestsResponse = await response.json();

      expect(data.requests.length).toBeGreaterThan(0);

      const request = data.requests[0];
      // Required fields
      expect(typeof request.request_id).toBe("string");
      expect(typeof request.session_id).toBe("string");
      expect(typeof request.task_id).toBe("string");
      expect(typeof request.agent_name).toBe("string");
      expect(["approval", "clarification"]).toContain(request.request_type);
      expect(typeof request.question).toBe("string");
      expect([
        "pending",
        "approved",
        "rejected",
        "responded",
        "timeout",
      ]).toContain(request.status);
      expect(typeof request.requested_at).toBe("string");
      expect(typeof request.context).toBe("object");
    });

    it("should include optional fields when present", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");
      const data: PendingAgentRequestsResponse = await response.json();

      const request = data.requests[0];

      // Optional fields for approval type
      if (request.request_type === "approval") {
        expect(request.confidence).toBeDefined();
        expect(request.threshold).toBeDefined();
        expect(typeof request.confidence).toBe("number");
        expect(typeof request.threshold).toBe("number");
      }
    });
  });

  describe("GET /api/v1/agents/requests/pending with ai_explanation", () => {
    it("should include ai_explanation when present", async () => {
      // Override handler for this test
      server.use(
        http.get("/api/v1/agents/requests/pending", () => {
          return HttpResponse.json({
            requests: [
              {
                request_id: "req-002",
                session_id: "session-456",
                task_id: "task-789",
                agent_name: "code_agent",
                request_type: "approval",
                confidence: 0.55,
                threshold: 0.7,
                question: "Execute this code?",
                proposed_action: "run_code('python')",
                trigger_reason: "destructive_action",
                status: "pending",
                requested_at: "2024-01-15T11:00:00Z",
                context: {},
                ai_explanation: {
                  what_agent_wants: "Execute Python code that modifies files",
                  why_needs_approval: "Potentially destructive file operation",
                  risk_factors: ["file_modification", "code_execution"],
                  confidence_score: 0.55,
                  recommendation: "approve_with_caution",
                },
              },
            ],
            count: 1,
          });
        }),
      );

      const response = await fetch("/api/v1/agents/requests/pending");
      const data: PendingAgentRequestsResponse = await response.json();

      const request = data.requests[0];
      expect(request.ai_explanation).toBeDefined();
      expect(request.ai_explanation?.what_agent_wants).toContain(
        "Execute Python",
      );
      expect(request.ai_explanation?.risk_factors).toContain("code_execution");
      expect(request.ai_explanation?.recommendation).toBe(
        "approve_with_caution",
      );
    });
  });

  describe("GET /api/v1/agents/requests/pending with clarification type", () => {
    it("should handle clarification request type with options", async () => {
      server.use(
        http.get("/api/v1/agents/requests/pending", () => {
          return HttpResponse.json({
            requests: [
              {
                request_id: "req-003",
                session_id: "session-789",
                task_id: "task-012",
                agent_name: "assistant_agent",
                request_type: "clarification",
                confidence: null,
                threshold: null,
                question: "Which format would you prefer?",
                proposed_action: null,
                trigger_reason: null,
                placeholder: "Enter your preference",
                clarification_type: "choice",
                options: [
                  { id: "opt-1", label: "PDF", description: "PDF format" },
                  { id: "opt-2", label: "CSV", description: "CSV format" },
                ],
                status: "pending",
                requested_at: "2024-01-15T12:00:00Z",
                responded_at: null,
                responded_by: null,
                context: {},
                ai_explanation: null,
              },
            ],
            count: 1,
          });
        }),
      );

      const response = await fetch("/api/v1/agents/requests/pending");
      const data: PendingAgentRequestsResponse = await response.json();

      const request = data.requests[0];
      expect(request.request_type).toBe("clarification");
      expect(request.clarification_type).toBe("choice");
      expect(request.options).toHaveLength(2);
      expect(request.options?.[0].id).toBe("opt-1");
      expect(request.options?.[0].label).toBe("PDF");
    });
  });

  describe("POST /api/v1/agents/requests/:id/approve", () => {
    it("should accept ApproveAgentRequest body and return ActionResponse", async () => {
      const response = await fetch("/api/v1/agents/requests/req-001/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved_by: "admin@example.com",
          reason: "Looks safe to proceed",
          modifications: { timeout: 30 },
        }),
      });

      expect(response.ok).toBe(true);
      const data: AgentRequestActionResponse = await response.json();

      expect(data.request_id).toBe("req-001");
      expect(data.status).toBe("approved");
      expect(typeof data.message).toBe("string");
    });
  });

  describe("POST /api/v1/agents/requests/:id/reject", () => {
    it("should accept RejectAgentRequest body and return ActionResponse", async () => {
      const response = await fetch("/api/v1/agents/requests/req-001/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rejected_by: "admin@example.com",
          reason: "Action is too risky",
        }),
      });

      expect(response.ok).toBe(true);
      const data: AgentRequestActionResponse = await response.json();

      expect(data.request_id).toBe("req-001");
      expect(data.status).toBe("rejected");
      expect(data.message).toContain("too risky");
    });
  });

  describe("POST /api/v1/agents/requests/:id/respond", () => {
    it("should accept text response", async () => {
      const response = await fetch("/api/v1/agents/requests/req-003/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          responded_by: "user@example.com",
          response_type: "text",
          value: "Use JSON format please",
        }),
      });

      expect(response.ok).toBe(true);
      const data: AgentRequestActionResponse = await response.json();

      expect(data.request_id).toBe("req-003");
      expect(data.status).toBe("responded");
    });

    it("should accept choice response", async () => {
      const response = await fetch("/api/v1/agents/requests/req-003/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          responded_by: "user@example.com",
          response_type: "choice",
          selected_option_id: "opt-2",
        }),
      });

      expect(response.ok).toBe(true);
      const data: AgentRequestActionResponse = await response.json();

      expect(data.status).toBe("responded");
    });

    it("should accept confirmation response", async () => {
      const response = await fetch("/api/v1/agents/requests/req-004/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          responded_by: "user@example.com",
          response_type: "confirmation",
          confirmed: true,
        }),
      });

      expect(response.ok).toBe(true);
    });
  });

  describe("POST /api/v1/agents/requests/batch/approve", () => {
    it("should validate batch approve request and response", async () => {
      const response = await fetch("/api/v1/agents/requests/batch/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_ids: ["approval-1", "approval-2"], // Use mock pending approval IDs
          approved_by: "admin@example.com",
          reason: "Batch approved",
        }),
      });

      expect(response.ok).toBe(true);
      const data: BatchActionResponse = await response.json();

      // Validate BatchAgentRequestResponse schema
      expect(typeof data.success).toBe("boolean");
      expect(typeof data.processed).toBe("number");
      expect(typeof data.failed).toBe("number");
      expect(Array.isArray(data.results)).toBe(true);

      // Each result should have request_id and success
      for (const result of data.results) {
        expect(typeof result.request_id).toBe("string");
        expect(typeof result.success).toBe("boolean");
      }
    });
  });

  describe("POST /api/v1/agents/requests/batch/reject", () => {
    it("should validate batch reject request and response", async () => {
      const response = await fetch("/api/v1/agents/requests/batch/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_ids: ["approval-1", "approval-2"],
          rejected_by: "admin@example.com",
          reason: "Batch rejected - policy violation",
        }),
      });

      expect(response.ok).toBe(true);
      const data: BatchActionResponse = await response.json();

      // Validate BatchAgentRequestResponse schema
      expect(typeof data.success).toBe("boolean");
      expect(typeof data.processed).toBe("number");
      expect(typeof data.failed).toBe("number");
      expect(Array.isArray(data.results)).toBe(true);
    });
  });
});
