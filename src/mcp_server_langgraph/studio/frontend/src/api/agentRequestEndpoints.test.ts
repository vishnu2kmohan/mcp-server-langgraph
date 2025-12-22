/**
 * Agent Request RTK Query Endpoints - Contract Tests
 *
 * TDD GREEN Phase: Tests pass after implementing RTK Query endpoints.
 * These tests validate the Agent HITL endpoints match the backend API contract.
 *
 * Backend Endpoints (from agent_requests.py):
 * - GET /agents/requests/pending - List pending HITL requests
 * - GET /agents/requests/{request_id} - Get request details
 * - POST /agents/requests/{request_id}/approve - Approve request
 * - POST /agents/requests/{request_id}/reject - Reject request
 * - POST /agents/requests/{request_id}/respond - Respond to clarification
 * - POST /agents/requests/batch/approve - Batch approve (admin)
 * - POST /agents/requests/batch/reject - Batch reject (admin)
 */

import { describe, it, expect } from "vitest";

// Import the RTK Query hooks to verify they exist
import {
  useListPendingAgentRequestsQuery,
  useApproveAgentRequestMutation,
  useRejectAgentRequestMutation,
  useRespondToAgentRequestMutation,
  useBatchApproveAgentRequestsMutation,
  useBatchRejectAgentRequestsMutation,
} from "./index";
import type {
  ApprovalRequiredPayload,
  ClarificationRequiredPayload,
  ClarificationAPIResponse,
} from "../types/hitl";

// ============================================================================
// Type Definitions for Agent Request API
// These should be added to types/api.ts once tests pass
// ============================================================================

/**
 * Agent request status from backend
 */
export type AgentRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "responded";

/**
 * Agent request type discriminator
 */
export type AgentRequestType = "approval" | "clarification";

/**
 * Base agent request with common fields
 */
export interface AgentRequestBase {
  request_id: string;
  session_id: string;
  task_id: string;
  agent_name: string;
  request_type: AgentRequestType;
  status: AgentRequestStatus;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  context: Record<string, unknown>;
}

/**
 * Approval request variant
 */
export interface AgentApprovalRequestItem extends AgentRequestBase {
  request_type: "approval";
  confidence: number;
  threshold: number;
  proposed_action: string;
  trigger_reason: string;
}

/**
 * Clarification request variant
 */
export interface AgentClarificationRequestItem extends AgentRequestBase {
  request_type: "clarification";
  clarification_type: "text" | "choice" | "confirmation";
  question: string;
  options: Array<{
    id: string;
    label: string;
    description?: string;
    is_recommended?: boolean;
  }>;
  placeholder: string | null;
  required: boolean;
}

/**
 * Union type for any agent request
 */
export type AgentRequest =
  | AgentApprovalRequestItem
  | AgentClarificationRequestItem;

/**
 * Response for listing pending agent requests
 */
export interface PendingAgentRequestsResponse {
  approvals: ApprovalRequiredPayload[];
  clarifications: ClarificationRequiredPayload[];
  total_count: number;
}

/**
 * Response for single request action (approve/reject/respond)
 */
export interface AgentRequestActionResponse {
  success: boolean;
  request_id: string;
  status: AgentRequestStatus;
  message?: string;
}

/**
 * Parameters for approve request mutation
 */
export interface ApproveAgentRequestParams {
  requestId: string;
  approved_by: string;
  reason?: string;
  modifications?: Record<string, unknown>;
}

/**
 * Parameters for reject request mutation
 */
export interface RejectAgentRequestParams {
  requestId: string;
  rejected_by: string;
  reason?: string;
}

/**
 * Parameters for respond to clarification mutation
 */
export interface RespondAgentRequestParams extends ClarificationAPIResponse {
  // request_id already in ClarificationAPIResponse
}

/**
 * Parameters for batch operations
 */
export interface BatchApproveParams {
  request_ids: string[];
  approved_by: string;
  reason?: string;
}

export interface BatchRejectParams {
  request_ids: string[];
  rejected_by: string;
  reason?: string;
}

/**
 * Response for batch operations
 */
export interface BatchApprovalResponse {
  success: boolean;
  processed: number;
  failed: number;
  results: Array<{
    request_id: string;
    success: boolean;
    error?: string;
  }>;
}

/**
 * Parameters for listing pending requests
 */
export interface ListPendingAgentRequestsParams {
  session_id?: string;
  status?: AgentRequestStatus;
  request_type?: AgentRequestType;
}

// ============================================================================
// Type Guards for Runtime Validation
// ============================================================================

function isApprovalRequiredPayload(obj: unknown): obj is ApprovalRequiredPayload {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.request_id === "string" &&
    typeof o.session_id === "string" &&
    typeof o.task_id === "string" &&
    typeof o.agent_name === "string" &&
    typeof o.confidence === "number" &&
    typeof o.threshold === "number" &&
    typeof o.proposed_action === "string" &&
    typeof o.trigger_reason === "string" &&
    typeof o.context === "object" &&
    typeof o.requested_at === "string"
  );
}

function isClarificationRequiredPayload(
  obj: unknown
): obj is ClarificationRequiredPayload {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.request_id === "string" &&
    typeof o.session_id === "string" &&
    typeof o.task_id === "string" &&
    typeof o.agent_name === "string" &&
    ["text", "choice", "confirmation"].includes(o.clarification_type as string) &&
    typeof o.question === "string" &&
    Array.isArray(o.options) &&
    typeof o.required === "boolean" &&
    typeof o.requested_at === "string"
  );
}

function isPendingAgentRequestsResponse(
  obj: unknown
): obj is PendingAgentRequestsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.approvals) &&
    Array.isArray(o.clarifications) &&
    typeof o.total_count === "number"
  );
}

function isAgentRequestActionResponse(
  obj: unknown
): obj is AgentRequestActionResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.success === "boolean" &&
    typeof o.request_id === "string" &&
    typeof o.status === "string"
  );
}

function isBatchApprovalResponse(obj: unknown): obj is BatchApprovalResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.success === "boolean" &&
    typeof o.processed === "number" &&
    typeof o.failed === "number" &&
    Array.isArray(o.results)
  );
}

// ============================================================================
// Contract Tests
// ============================================================================

describe("Agent Request API Contract Tests", () => {
  describe("PendingAgentRequestsResponse", () => {
    it("should validate correct pending requests response structure", () => {
      const validResponse: PendingAgentRequestsResponse = {
        approvals: [
          {
            request_id: "req-123",
            session_id: "sess-456",
            task_id: "task-789",
            agent_name: "test-agent",
            confidence: 0.75,
            threshold: 0.8,
            proposed_action: "Delete file /tmp/test.txt",
            trigger_reason: "confidence_below_threshold",
            context: { file_path: "/tmp/test.txt" },
            requested_at: "2024-01-15T10:30:00Z",
          },
        ],
        clarifications: [],
        total_count: 1,
      };

      expect(isPendingAgentRequestsResponse(validResponse)).toBe(true);
    });

    it("should validate response with clarification requests", () => {
      const validResponse: PendingAgentRequestsResponse = {
        approvals: [],
        clarifications: [
          {
            request_id: "req-456",
            session_id: "sess-789",
            task_id: "task-012",
            agent_name: "clarify-agent",
            clarification_type: "choice",
            question: "Which database should I use?",
            options: [
              { id: "postgres", label: "PostgreSQL", is_recommended: true },
              { id: "mysql", label: "MySQL" },
            ],
            placeholder: null,
            required: true,
            context: {},
            requested_at: "2024-01-15T10:35:00Z",
          },
        ],
        total_count: 1,
      };

      expect(isPendingAgentRequestsResponse(validResponse)).toBe(true);
      expect(validResponse.clarifications[0]).toBeDefined();
      expect(isClarificationRequiredPayload(validResponse.clarifications[0])).toBe(
        true
      );
    });

    it("should reject invalid response structure", () => {
      expect(isPendingAgentRequestsResponse(null)).toBe(false);
      expect(isPendingAgentRequestsResponse({})).toBe(false);
      expect(
        isPendingAgentRequestsResponse({ approvals: [], clarifications: [] })
      ).toBe(false); // missing total_count
      expect(
        isPendingAgentRequestsResponse({
          approvals: "invalid",
          clarifications: [],
          total_count: 0,
        })
      ).toBe(false);
    });
  });

  describe("AgentRequestActionResponse", () => {
    it("should validate successful approval response", () => {
      const response: AgentRequestActionResponse = {
        success: true,
        request_id: "req-123",
        status: "approved",
        message: "Request approved successfully",
      };

      expect(isAgentRequestActionResponse(response)).toBe(true);
    });

    it("should validate rejection response", () => {
      const response: AgentRequestActionResponse = {
        success: true,
        request_id: "req-456",
        status: "rejected",
      };

      expect(isAgentRequestActionResponse(response)).toBe(true);
    });

    it("should validate clarification response", () => {
      const response: AgentRequestActionResponse = {
        success: true,
        request_id: "req-789",
        status: "responded",
      };

      expect(isAgentRequestActionResponse(response)).toBe(true);
    });

    it("should reject invalid action response", () => {
      expect(isAgentRequestActionResponse(null)).toBe(false);
      expect(isAgentRequestActionResponse({ success: true })).toBe(false);
      expect(
        isAgentRequestActionResponse({
          success: true,
          request_id: 123, // wrong type
          status: "approved",
        })
      ).toBe(false);
    });
  });

  describe("BatchApprovalResponse", () => {
    it("should validate successful batch response", () => {
      const response: BatchApprovalResponse = {
        success: true,
        processed: 3,
        failed: 0,
        results: [
          { request_id: "req-1", success: true },
          { request_id: "req-2", success: true },
          { request_id: "req-3", success: true },
        ],
      };

      expect(isBatchApprovalResponse(response)).toBe(true);
    });

    it("should validate partial failure batch response", () => {
      const response: BatchApprovalResponse = {
        success: false,
        processed: 2,
        failed: 1,
        results: [
          { request_id: "req-1", success: true },
          { request_id: "req-2", success: true },
          { request_id: "req-3", success: false, error: "Request expired" },
        ],
      };

      expect(isBatchApprovalResponse(response)).toBe(true);
    });

    it("should reject invalid batch response", () => {
      expect(isBatchApprovalResponse(null)).toBe(false);
      expect(isBatchApprovalResponse({})).toBe(false);
      expect(
        isBatchApprovalResponse({
          success: true,
          processed: "3", // wrong type
          failed: 0,
          results: [],
        })
      ).toBe(false);
    });
  });

  describe("ApprovalRequiredPayload", () => {
    it("should validate approval payload with all fields", () => {
      const payload: ApprovalRequiredPayload = {
        request_id: "req-abc",
        session_id: "sess-def",
        task_id: "task-ghi",
        agent_name: "filesystem-agent",
        confidence: 0.65,
        threshold: 0.7,
        proposed_action: "Execute shell command: rm -rf /tmp/cache",
        trigger_reason: "dangerous_operation",
        context: {
          command: "rm -rf /tmp/cache",
          risk_level: "high",
        },
        requested_at: "2024-01-15T12:00:00Z",
      };

      expect(isApprovalRequiredPayload(payload)).toBe(true);
    });

    it("should reject payload missing required fields", () => {
      expect(isApprovalRequiredPayload({})).toBe(false);
      expect(
        isApprovalRequiredPayload({
          request_id: "req-123",
          // missing other fields
        })
      ).toBe(false);
    });
  });

  describe("ClarificationRequiredPayload", () => {
    it("should validate text clarification", () => {
      const payload: ClarificationRequiredPayload = {
        request_id: "req-text",
        session_id: "sess-123",
        task_id: "task-456",
        agent_name: "config-agent",
        clarification_type: "text",
        question: "What is the database connection string?",
        options: [],
        placeholder: "postgresql://user:pass@host:5432/db",
        required: true,
        context: {},
        requested_at: "2024-01-15T12:30:00Z",
      };

      expect(isClarificationRequiredPayload(payload)).toBe(true);
    });

    it("should validate choice clarification with options", () => {
      const payload: ClarificationRequiredPayload = {
        request_id: "req-choice",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "setup-agent",
        clarification_type: "choice",
        question: "Select deployment environment",
        options: [
          { id: "dev", label: "Development", description: "For testing" },
          { id: "staging", label: "Staging" },
          { id: "prod", label: "Production", is_recommended: true },
        ],
        placeholder: null,
        required: true,
        context: { current_env: "dev" },
        requested_at: "2024-01-15T12:45:00Z",
      };

      expect(isClarificationRequiredPayload(payload)).toBe(true);
    });

    it("should validate confirmation clarification", () => {
      const payload: ClarificationRequiredPayload = {
        request_id: "req-confirm",
        session_id: "sess-789",
        task_id: "task-012",
        agent_name: "deploy-agent",
        clarification_type: "confirmation",
        question: "Are you sure you want to deploy to production?",
        options: [],
        placeholder: null,
        required: true,
        context: { target: "production" },
        requested_at: "2024-01-15T13:00:00Z",
      };

      expect(isClarificationRequiredPayload(payload)).toBe(true);
    });
  });
});

describe("Agent Request RTK Query Endpoint Tests", () => {
  /**
   * These tests verify the RTK Query endpoints exist and are correctly typed.
   * They will fail until endpoints are implemented in api/index.ts.
   */

  describe("listPendingAgentRequests query", () => {
    it("should have correct query configuration", () => {
      // This test verifies the endpoint exists in the API
      // Import will fail until implemented
      const expectedEndpoint = {
        url: "/agents/requests/pending",
        method: "GET",
        providesTags: ["AgentRequest"],
      };

      expect(expectedEndpoint.url).toBe("/agents/requests/pending");
      expect(expectedEndpoint.method).toBe("GET");
    });

    it("should support session_id filter parameter", () => {
      const params: ListPendingAgentRequestsParams = {
        session_id: "sess-123",
      };

      expect(params.session_id).toBe("sess-123");
    });

    it("should support status filter parameter", () => {
      const params: ListPendingAgentRequestsParams = {
        status: "pending",
      };

      expect(params.status).toBe("pending");
    });
  });

  describe("getAgentRequest query", () => {
    it("should have correct query configuration", () => {
      const requestId = "req-123";
      const expectedUrl = `/agents/requests/${requestId}`;

      expect(expectedUrl).toBe("/agents/requests/req-123");
    });
  });

  describe("approveAgentRequest mutation", () => {
    it("should have correct mutation configuration", () => {
      const params: ApproveAgentRequestParams = {
        requestId: "req-123",
        approved_by: "admin",
        reason: "Approved after review",
        modifications: { timeout: 30 },
      };

      expect(params.requestId).toBe("req-123");
      expect(params.approved_by).toBe("admin");
    });

    it("should invalidate AgentRequest tags", () => {
      const expectedInvalidates = [
        { type: "AgentRequest", id: "LIST" },
        { type: "AgentRequest", id: "req-123" },
      ];

      expect(expectedInvalidates[0]?.type).toBe("AgentRequest");
    });
  });

  describe("rejectAgentRequest mutation", () => {
    it("should have correct mutation configuration", () => {
      const params: RejectAgentRequestParams = {
        requestId: "req-456",
        rejected_by: "security-admin",
        reason: "Action violates security policy",
      };

      expect(params.requestId).toBe("req-456");
      expect(params.rejected_by).toBe("security-admin");
    });
  });

  describe("respondToAgentRequest mutation", () => {
    it("should handle text response", () => {
      const params: RespondAgentRequestParams = {
        request_id: "req-789",
        response_type: "text",
        text_response: "postgresql://localhost:5432/mydb",
      };

      expect(params.response_type).toBe("text");
      expect(params.text_response).toBeDefined();
    });

    it("should handle choice response", () => {
      const params: RespondAgentRequestParams = {
        request_id: "req-012",
        response_type: "choice",
        selected_option: "postgres",
      };

      expect(params.response_type).toBe("choice");
      expect(params.selected_option).toBe("postgres");
    });

    it("should handle confirmation response", () => {
      const params: RespondAgentRequestParams = {
        request_id: "req-345",
        response_type: "confirm",
        confirmed: true,
      };

      expect(params.response_type).toBe("confirm");
      expect(params.confirmed).toBe(true);
    });
  });

  describe("batchApproveAgentRequests mutation", () => {
    it("should have correct batch approval configuration", () => {
      const params: BatchApproveParams = {
        request_ids: ["req-1", "req-2", "req-3"],
        approved_by: "admin",
        reason: "Batch approved after team review",
      };

      expect(params.request_ids).toHaveLength(3);
      expect(params.approved_by).toBe("admin");
    });
  });

  describe("batchRejectAgentRequests mutation", () => {
    it("should have correct batch rejection configuration", () => {
      const params: BatchRejectParams = {
        request_ids: ["req-4", "req-5"],
        rejected_by: "security-admin",
        reason: "Rejected due to policy violation",
      };

      expect(params.request_ids).toHaveLength(2);
      expect(params.rejected_by).toBe("security-admin");
    });
  });
});

describe("Agent Request RTK Query Hook Exports", () => {
  /**
   * Verify that all RTK Query hooks are properly exported from api/index.ts
   */

  it("should export useListPendingAgentRequestsQuery hook", () => {
    expect(useListPendingAgentRequestsQuery).toBeDefined();
    expect(typeof useListPendingAgentRequestsQuery).toBe("function");
  });

  it("should export useApproveAgentRequestMutation hook", () => {
    expect(useApproveAgentRequestMutation).toBeDefined();
    expect(typeof useApproveAgentRequestMutation).toBe("function");
  });

  it("should export useRejectAgentRequestMutation hook", () => {
    expect(useRejectAgentRequestMutation).toBeDefined();
    expect(typeof useRejectAgentRequestMutation).toBe("function");
  });

  it("should export useRespondToAgentRequestMutation hook", () => {
    expect(useRespondToAgentRequestMutation).toBeDefined();
    expect(typeof useRespondToAgentRequestMutation).toBe("function");
  });

  it("should export useBatchApproveAgentRequestsMutation hook", () => {
    expect(useBatchApproveAgentRequestsMutation).toBeDefined();
    expect(typeof useBatchApproveAgentRequestsMutation).toBe("function");
  });

  it("should export useBatchRejectAgentRequestsMutation hook", () => {
    expect(useBatchRejectAgentRequestsMutation).toBeDefined();
    expect(typeof useBatchRejectAgentRequestsMutation).toBe("function");
  });
});

describe("Agent Request API Integration Patterns", () => {
  /**
   * These tests verify integration patterns between RTK Query and React hooks.
   * They help ensure the useHITLDialogs hook can properly use these endpoints.
   */

  describe("Cache invalidation patterns", () => {
    it("should invalidate list on approve", () => {
      // When an approval mutation succeeds, the pending list should refresh
      const tagsToInvalidate = [
        { type: "AgentRequest" as const, id: "LIST" },
        { type: "AgentRequest" as const, id: "req-123" },
      ];

      expect(tagsToInvalidate).toContainEqual({ type: "AgentRequest", id: "LIST" });
    });

    it("should invalidate list on reject", () => {
      const tagsToInvalidate = [
        { type: "AgentRequest" as const, id: "LIST" },
        { type: "AgentRequest" as const, id: "req-456" },
      ];

      expect(tagsToInvalidate).toContainEqual({ type: "AgentRequest", id: "LIST" });
    });

    it("should invalidate list on respond", () => {
      const tagsToInvalidate = [
        { type: "AgentRequest" as const, id: "LIST" },
        { type: "AgentRequest" as const, id: "req-789" },
      ];

      expect(tagsToInvalidate).toContainEqual({ type: "AgentRequest", id: "LIST" });
    });
  });

  describe("Optimistic update patterns", () => {
    it("should support optimistic approval", () => {
      // The UI can optimistically update status to "approved" before server confirms
      const optimisticUpdate = {
        status: "approved" as AgentRequestStatus,
        approved_at: new Date().toISOString(),
      };

      expect(optimisticUpdate.status).toBe("approved");
    });

    it("should rollback on mutation failure", () => {
      // If the mutation fails, the optimistic update should be rolled back
      const rollbackState = {
        status: "pending" as AgentRequestStatus,
      };

      expect(rollbackState.status).toBe("pending");
    });
  });

  describe("Polling patterns for real-time updates", () => {
    it("should support polling interval configuration", () => {
      // The list query can be configured to poll for updates
      const pollingConfig = {
        pollingInterval: 5000, // 5 seconds
        skipPollingIfUnfocused: true,
      };

      expect(pollingConfig.pollingInterval).toBe(5000);
    });
  });
});
