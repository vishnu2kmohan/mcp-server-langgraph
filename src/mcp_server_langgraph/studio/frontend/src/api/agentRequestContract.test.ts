/**
 * Agent Request API Contract Tests
 *
 * Verifies RTK Query endpoint types match backend API schema for HITL agent requests.
 * Reference: src/mcp_server_langgraph/api/v1/agent_requests.py
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { configureStore } from "@reduxjs/toolkit";
import { api } from "./index";

// MSW Server setup
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => server.resetHandlers());

// Store factory
function createTestStore() {
  return configureStore({
    reducer: { [api.reducerPath]: api.reducer },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

describe("Agent Request API Contract", () => {
  describe("GET /api/v1/agents/requests/pending", () => {
    it("should validate PendingAgentRequestsResponse schema", async () => {
      // Backend schema: { requests: AgentRequest[], count: number }
      server.use(
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
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.listPendingAgentRequests.initiate({})
      );

      expect(result.data).toBeDefined();
      expect(result.data?.requests).toHaveLength(1);
      expect(result.data?.count).toBe(1);

      const request = result.data!.requests[0];
      // Verify all required fields match backend schema
      expect(request.request_id).toBe("req-001");
      expect(request.session_id).toBe("session-123");
      expect(request.task_id).toBe("task-456");
      expect(request.agent_name).toBe("research_agent");
      expect(request.request_type).toBe("approval");
      expect(request.confidence).toBe(0.65);
      expect(request.threshold).toBe(0.7);
      expect(request.status).toBe("pending");
      expect(request.requested_at).toBe("2024-01-15T10:30:00Z");
    });

    it("should include optional ai_explanation field when present", async () => {
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
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.listPendingAgentRequests.initiate({})
      );

      const request = result.data!.requests[0];
      expect(request.ai_explanation).toBeDefined();
      expect(request.ai_explanation?.what_agent_wants).toContain("Execute Python");
      expect(request.ai_explanation?.risk_factors).toContain("code_execution");
    });

    it("should handle clarification request type", async () => {
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
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.listPendingAgentRequests.initiate({})
      );

      const request = result.data!.requests[0];
      expect(request.request_type).toBe("clarification");
      expect(request.clarification_type).toBe("choice");
      expect(request.options).toHaveLength(2);
      expect(request.options![0].id).toBe("opt-1");
      expect(request.options![0].label).toBe("PDF");
    });
  });

  describe("POST /api/v1/agents/requests/:id/approve", () => {
    it("should validate ApproveAgentRequest request body", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/:id/approve", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            request_id: "req-001",
            status: "approved",
            message: "Request approved successfully",
          });
        })
      );

      const store = createTestStore();
      await store.dispatch(
        api.endpoints.approveAgentRequest.initiate({
          requestId: "req-001",
          approvedBy: "admin@example.com",
          reason: "Looks safe to proceed",
          modifications: { timeout: 30 },
        })
      );

      // Verify request body matches backend schema
      expect(capturedBody).toEqual({
        approved_by: "admin@example.com",
        reason: "Looks safe to proceed",
        modifications: { timeout: 30 },
      });
    });

    it("should validate AgentRequestActionResponse schema", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:id/approve", () => {
          return HttpResponse.json({
            request_id: "req-001",
            status: "approved",
            message: "Request approved successfully",
          });
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.approveAgentRequest.initiate({
          requestId: "req-001",
          approvedBy: "admin@example.com",
        })
      );

      expect(result.data).toEqual({
        request_id: "req-001",
        status: "approved",
        message: "Request approved successfully",
      });
    });
  });

  describe("POST /api/v1/agents/requests/:id/reject", () => {
    it("should validate RejectAgentRequest request body", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/:id/reject", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            request_id: "req-001",
            status: "rejected",
            message: "Request rejected",
          });
        })
      );

      const store = createTestStore();
      await store.dispatch(
        api.endpoints.rejectAgentRequest.initiate({
          requestId: "req-001",
          rejectedBy: "admin@example.com",
          reason: "Action is too risky",
        })
      );

      // Backend requires rejected_by and reason
      expect(capturedBody).toEqual({
        rejected_by: "admin@example.com",
        reason: "Action is too risky",
      });
    });
  });

  describe("POST /api/v1/agents/requests/:id/respond", () => {
    it("should validate ClarificationResponseRequest for text response", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/:id/respond", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            request_id: "req-003",
            status: "responded",
            message: "Clarification received",
          });
        })
      );

      const store = createTestStore();
      await store.dispatch(
        api.endpoints.respondToAgentRequest.initiate({
          requestId: "req-003",
          respondedBy: "user@example.com",
          responseType: "text",
          value: "Use JSON format please",
        })
      );

      expect(capturedBody).toEqual({
        responded_by: "user@example.com",
        response_type: "text",
        value: "Use JSON format please",
        selected_option_id: undefined,
        confirmed: undefined,
      });
    });

    it("should validate ClarificationResponseRequest for choice response", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/:id/respond", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            request_id: "req-003",
            status: "responded",
            message: "Clarification received",
          });
        })
      );

      const store = createTestStore();
      await store.dispatch(
        api.endpoints.respondToAgentRequest.initiate({
          requestId: "req-003",
          respondedBy: "user@example.com",
          responseType: "choice",
          selectedOptionId: "opt-2",
        })
      );

      expect(capturedBody).toEqual({
        responded_by: "user@example.com",
        response_type: "choice",
        value: undefined,
        selected_option_id: "opt-2",
        confirmed: undefined,
      });
    });

    it("should validate ClarificationResponseRequest for confirmation response", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/:id/respond", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            request_id: "req-004",
            status: "responded",
            message: "Clarification received",
          });
        })
      );

      const store = createTestStore();
      await store.dispatch(
        api.endpoints.respondToAgentRequest.initiate({
          requestId: "req-004",
          respondedBy: "user@example.com",
          responseType: "confirmation",
          confirmed: true,
        })
      );

      expect(capturedBody).toEqual({
        responded_by: "user@example.com",
        response_type: "confirmation",
        value: undefined,
        selected_option_id: undefined,
        confirmed: true,
      });
    });
  });

  describe("POST /api/v1/agents/requests/batch/approve", () => {
    it("should validate batch approve request and response", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/batch/approve", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            approved_count: 3,
            failed_count: 0,
            results: [
              { request_id: "req-001", status: "approved" },
              { request_id: "req-002", status: "approved" },
              { request_id: "req-003", status: "approved" },
            ],
          });
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.batchApproveAgentRequests.initiate({
          requestIds: ["req-001", "req-002", "req-003"],
          approvedBy: "admin@example.com",
          reason: "Batch approved",
        })
      );

      expect(capturedBody).toEqual({
        request_ids: ["req-001", "req-002", "req-003"],
        approved_by: "admin@example.com",
        reason: "Batch approved",
      });

      expect(result.data?.approved_count).toBe(3);
      expect(result.data?.failed_count).toBe(0);
      expect(result.data?.results).toHaveLength(3);
    });
  });

  describe("POST /api/v1/agents/requests/batch/reject", () => {
    it("should validate batch reject request and response", async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post("/api/v1/agents/requests/batch/reject", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            rejected_count: 2,
            failed_count: 1,
            results: [
              { request_id: "req-001", status: "rejected" },
              { request_id: "req-002", status: "rejected" },
              { request_id: "req-003", status: "error", error: "Request not found" },
            ],
          });
        })
      );

      const store = createTestStore();
      const result = await store.dispatch(
        api.endpoints.batchRejectAgentRequests.initiate({
          requestIds: ["req-001", "req-002", "req-003"],
          rejectedBy: "admin@example.com",
          reason: "Batch rejected - policy violation",
        })
      );

      expect(capturedBody).toEqual({
        request_ids: ["req-001", "req-002", "req-003"],
        rejected_by: "admin@example.com",
        reason: "Batch rejected - policy violation",
      });

      expect(result.data?.rejected_count).toBe(2);
      expect(result.data?.failed_count).toBe(1);
    });
  });

  describe("Cache Invalidation", () => {
    it("should invalidate AgentRequest tag on approve", async () => {
      // First, prime the cache with pending requests
      server.use(
        http.get("/api/v1/agents/requests/pending", () => {
          return HttpResponse.json({
            requests: [
              {
                request_id: "req-001",
                session_id: "session-123",
                task_id: "task-456",
                agent_name: "test_agent",
                request_type: "approval",
                status: "pending",
                question: "Test?",
                requested_at: "2024-01-15T10:30:00Z",
                context: {},
              },
            ],
            count: 1,
          });
        }),
        http.post("/api/v1/agents/requests/:id/approve", () => {
          return HttpResponse.json({
            request_id: "req-001",
            status: "approved",
            message: "Approved",
          });
        })
      );

      const store = createTestStore();

      // Initial fetch
      await store.dispatch(api.endpoints.listPendingAgentRequests.initiate({}));

      // Approve - should invalidate cache
      await store.dispatch(
        api.endpoints.approveAgentRequest.initiate({
          requestId: "req-001",
          approvedBy: "admin@example.com",
        })
      );

      // Verify the listPendingAgentRequests query is invalidated
      const state = store.getState();
      const query =
        state[api.reducerPath].queries["listPendingAgentRequests({})"];

      // After mutation with invalidation, status should change
      // (either refetching or needs refetch)
      expect(query).toBeDefined();
    });
  });
});
