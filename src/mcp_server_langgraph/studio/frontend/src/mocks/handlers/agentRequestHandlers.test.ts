/**
 * Agent Request Handlers Tests
 *
 * TDD tests for Agent HITL API MSW handlers.
 * Validates that handlers return proper data structures.
 */
import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import {
  agentRequestHandlers,
  mockPendingApprovals,
  mockPendingClarifications,
  createMockApprovalRequest,
  createMockClarificationRequest,
} from "./agentRequestHandlers";

const server = setupServer(...agentRequestHandlers);

describe("agentRequestHandlers", () => {
  beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });
  afterAll(() => server.close());

  describe("GET /api/v1/agents/requests/pending", () => {
    it("should return pending approvals and clarifications", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("approvals");
      expect(data).toHaveProperty("clarifications");
      expect(Array.isArray(data.approvals)).toBe(true);
      expect(Array.isArray(data.clarifications)).toBe(true);
    });

    it("should return proper approval structure", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");
      const data = await response.json();

      // Check first approval has required fields
      if (data.approvals.length > 0) {
        const approval = data.approvals[0];
        expect(approval).toMatchObject({
          request_id: expect.any(String),
          session_id: expect.any(String),
          task_id: expect.any(String),
          agent_name: expect.any(String),
          confidence: expect.any(Number),
          threshold: expect.any(Number),
          proposed_action: expect.any(String),
          trigger_reason: expect.any(String),
          requested_at: expect.any(String),
        });
      }
    });

    it("should return proper clarification structure", async () => {
      const response = await fetch("/api/v1/agents/requests/pending");
      const data = await response.json();

      // Check first clarification has required fields
      if (data.clarifications.length > 0) {
        const clarification = data.clarifications[0];
        expect(clarification).toMatchObject({
          request_id: expect.any(String),
          session_id: expect.any(String),
          task_id: expect.any(String),
          agent_name: expect.any(String),
          clarification_type: expect.any(String),
          question: expect.any(String),
          required: expect.any(Boolean),
          requested_at: expect.any(String),
        });
      }
    });

    it("should filter by request_type=approval", async () => {
      const response = await fetch(
        "/api/v1/agents/requests/pending?request_type=approval",
      );
      const data = await response.json();

      expect(data.approvals.length).toBeGreaterThan(0);
      expect(data.clarifications).toHaveLength(0);
    });

    it("should filter by request_type=clarification", async () => {
      const response = await fetch(
        "/api/v1/agents/requests/pending?request_type=clarification",
      );
      const data = await response.json();

      expect(data.approvals).toHaveLength(0);
      expect(data.clarifications.length).toBeGreaterThan(0);
    });
  });

  describe("GET /api/v1/agents/requests/:id", () => {
    it("should return approval request by ID", async () => {
      const requestId = mockPendingApprovals[0].request_id;
      const response = await fetch(`/api/v1/agents/requests/${requestId}`);

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.request_id).toBe(requestId);
      expect(data.type).toBe("approval");
      expect(data.status).toBe("pending");
    });

    it("should return clarification request by ID", async () => {
      const requestId = mockPendingClarifications[0].request_id;
      const response = await fetch(`/api/v1/agents/requests/${requestId}`);

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.request_id).toBe(requestId);
      expect(data.type).toBe("clarification");
      expect(data.status).toBe("pending");
    });

    it("should return 404 for unknown request ID", async () => {
      const response = await fetch("/api/v1/agents/requests/unknown-id-123");

      expect(response.status).toBe(404);
      const data = await response.json();
      expect(data.error).toBe("Request not found");
    });
  });

  describe("POST /api/v1/agents/requests/:id/approve", () => {
    it("should approve a request successfully", async () => {
      const requestId = mockPendingApprovals[0].request_id;
      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            approved_by: "admin",
            reason: "Looks good",
          }),
        },
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.request_id).toBe(requestId);
      expect(data.action).toBe("approved");
      expect(data.approved_by).toBe("admin");
      expect(data.reason).toBe("Looks good");
      expect(data.timestamp).toBeDefined();
    });

    it("should include modifications in response", async () => {
      const requestId = mockPendingApprovals[0].request_id;
      const modifications = { output_path: "/new/path" };

      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            approved_by: "admin",
            modifications,
          }),
        },
      );

      const data = await response.json();
      expect(data.modifications).toEqual(modifications);
    });

    it("should return 404 for unknown request ID", async () => {
      const response = await fetch(
        "/api/v1/agents/requests/unknown-id/approve",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved_by: "admin" }),
        },
      );

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/agents/requests/:id/reject", () => {
    it("should reject a request successfully", async () => {
      const requestId = mockPendingApprovals[0].request_id;
      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rejected_by: "admin",
            reason: "Not appropriate",
          }),
        },
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.request_id).toBe(requestId);
      expect(data.action).toBe("rejected");
      expect(data.rejected_by).toBe("admin");
      expect(data.reason).toBe("Not appropriate");
    });

    it("should return 404 for unknown request ID", async () => {
      const response = await fetch(
        "/api/v1/agents/requests/unknown-id/reject",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rejected_by: "admin" }),
        },
      );

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/agents/requests/:id/respond", () => {
    it("should respond to choice clarification", async () => {
      const requestId = mockPendingClarifications[0].request_id;
      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/respond`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            response_type: "choice",
            selected_option: "PDF",
          }),
        },
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.request_id).toBe(requestId);
      expect(data.action).toBe("responded");
      expect(data.response_type).toBe("choice");
      expect(data.response_value).toBe("PDF");
    });

    it("should respond to text clarification", async () => {
      const requestId = mockPendingClarifications[0].request_id;
      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/respond`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            response_type: "text",
            text_response: "Use custom format XYZ",
          }),
        },
      );

      const data = await response.json();
      expect(data.response_type).toBe("text");
      expect(data.response_value).toBe("Use custom format XYZ");
    });

    it("should respond to confirm clarification", async () => {
      const requestId = mockPendingClarifications[0].request_id;
      const response = await fetch(
        `/api/v1/agents/requests/${requestId}/respond`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            response_type: "confirm",
            confirmed: true,
          }),
        },
      );

      const data = await response.json();
      expect(data.response_type).toBe("confirm");
      expect(data.response_value).toBe("true");
    });

    it("should return 404 for unknown request ID", async () => {
      const response = await fetch(
        "/api/v1/agents/requests/unknown-id/respond",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            response_type: "choice",
            selected_option: "PDF",
          }),
        },
      );

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/agents/requests/batch/approve", () => {
    it("should batch approve multiple requests", async () => {
      const requestIds = mockPendingApprovals.map((a) => a.request_id);
      const response = await fetch("/api/v1/agents/requests/batch/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_ids: requestIds,
          approved_by: "admin",
          reason: "Batch approved",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.processed).toBe(requestIds.length);
      expect(data.failed).toBe(0);
      expect(data.results).toHaveLength(requestIds.length);
      expect(data.results.every((r: { success: boolean }) => r.success)).toBe(
        true,
      );
    });

    it("should handle mixed valid/invalid request IDs", async () => {
      const requestIds = [mockPendingApprovals[0].request_id, "invalid-id"];
      const response = await fetch("/api/v1/agents/requests/batch/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_ids: requestIds,
          approved_by: "admin",
        }),
      });

      const data = await response.json();

      expect(data.success).toBe(false); // Not all succeeded
      expect(data.processed).toBe(1);
      expect(data.failed).toBe(1);
      expect(data.results.some((r: { success: boolean }) => !r.success)).toBe(
        true,
      );
    });
  });

  describe("POST /api/v1/agents/requests/batch/reject", () => {
    it("should batch reject multiple requests", async () => {
      const requestIds = mockPendingApprovals.map((a) => a.request_id);
      const response = await fetch("/api/v1/agents/requests/batch/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_ids: requestIds,
          rejected_by: "admin",
          reason: "Batch rejected for safety",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.processed).toBe(requestIds.length);
      expect(data.failed).toBe(0);
    });
  });

  describe("Mock Data Factories", () => {
    it("createMockApprovalRequest creates valid approval", () => {
      const approval = createMockApprovalRequest();

      expect(approval.request_id).toBeDefined();
      expect(approval.confidence).toBeDefined();
      expect(approval.threshold).toBeDefined();
      expect(approval.proposed_action).toBeDefined();
    });

    it("createMockApprovalRequest applies overrides", () => {
      const approval = createMockApprovalRequest({
        agent_name: "CustomAgent",
        confidence: 0.99,
      });

      expect(approval.agent_name).toBe("CustomAgent");
      expect(approval.confidence).toBe(0.99);
    });

    it("createMockClarificationRequest creates valid clarification", () => {
      const clarification = createMockClarificationRequest();

      expect(clarification.request_id).toBeDefined();
      expect(clarification.question).toBeDefined();
      expect(clarification.clarification_type).toBeDefined();
    });

    it("createMockClarificationRequest applies overrides", () => {
      const clarification = createMockClarificationRequest({
        question: "Custom question?",
        options: ["A", "B"],
      });

      expect(clarification.question).toBe("Custom question?");
      expect(clarification.options).toEqual(["A", "B"]);
    });
  });
});
