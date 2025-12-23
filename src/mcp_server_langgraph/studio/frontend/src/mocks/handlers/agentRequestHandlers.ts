/**
 * Agent Request Handlers
 *
 * MSW handlers for Agent HITL (Human-in-the-Loop) API endpoints.
 * These define the API contracts for agent approval and clarification workflows.
 *
 * Endpoints:
 * - GET /api/v1/agents/requests/pending - List pending HITL requests
 * - GET /api/v1/agents/requests/:id - Get request details
 * - POST /api/v1/agents/requests/:id/approve - Approve request
 * - POST /api/v1/agents/requests/:id/reject - Reject request
 * - POST /api/v1/agents/requests/:id/respond - Respond to clarification
 * - POST /api/v1/agents/requests/batch/approve - Batch approve requests
 * - POST /api/v1/agents/requests/batch/reject - Batch reject requests
 */

import { http, HttpResponse, delay } from "msw";
import type {
  AgentRequestStatus,
  PendingAgentRequestsResponse,
  AgentRequestActionResponse,
  BatchAgentRequestResponse,
} from "../../types/api";
import type {
  ApprovalRequiredPayload,
  ClarificationRequiredPayload,
} from "../../types/hitl";

// =============================================================================
// Mock Data Factories
// =============================================================================

/**
 * Create a mock approval request
 */
export const createMockApprovalRequest = (
  overrides: Partial<ApprovalRequiredPayload> = {}
): ApprovalRequiredPayload => ({
  request_id: `req-${crypto.randomUUID().slice(0, 8)}`,
  session_id: "session-1",
  task_id: "task-1",
  agent_name: "TestAgent",
  confidence: 0.7,
  threshold: 0.8,
  proposed_action: "Delete file: /tmp/test.txt",
  trigger_reason: "Low confidence score",
  context: {
    file_path: "/tmp/test.txt",
    operation: "delete",
  },
  requested_at: new Date().toISOString(),
  ...overrides,
});

/**
 * Create a mock clarification request
 */
export const createMockClarificationRequest = (
  overrides: Partial<ClarificationRequiredPayload> = {}
): ClarificationRequiredPayload => ({
  request_id: `req-${crypto.randomUUID().slice(0, 8)}`,
  session_id: "session-1",
  task_id: "task-2",
  agent_name: "TestAgent",
  clarification_type: "choice",
  question: "Which file format should I use?",
  options: [
    { id: "json", label: "JSON", description: "JavaScript Object Notation" },
    { id: "yaml", label: "YAML", description: "YAML Ain't Markup Language" },
    { id: "xml", label: "XML", description: "Extensible Markup Language" },
  ],
  placeholder: "Select a format",
  required: true,
  context: {
    current_step: "export",
    available_formats: ["JSON", "YAML", "XML"],
  },
  requested_at: new Date().toISOString(),
  ...overrides,
});

// =============================================================================
// Default Mock Data
// =============================================================================

export const mockPendingApprovals: ApprovalRequiredPayload[] = [
  createMockApprovalRequest({
    request_id: "req-approve-1",
    agent_name: "FileManager",
    proposed_action: "Delete temporary files",
    confidence: 0.65,
    threshold: 0.8,
  }),
  createMockApprovalRequest({
    request_id: "req-approve-2",
    agent_name: "DatabaseAgent",
    proposed_action: "Execute migration script",
    confidence: 0.75,
    threshold: 0.9,
  }),
];

export const mockPendingClarifications: ClarificationRequiredPayload[] = [
  createMockClarificationRequest({
    request_id: "req-clarify-1",
    agent_name: "ReportGenerator",
    question: "Which report format do you prefer?",
    options: [
      { id: "pdf", label: "PDF", description: "Portable Document Format" },
      { id: "excel", label: "Excel", description: "Microsoft Excel format" },
      { id: "csv", label: "CSV", description: "Comma Separated Values" },
    ],
  }),
];

export const mockPendingRequestsResponse: PendingAgentRequestsResponse = {
  approvals: mockPendingApprovals,
  clarifications: mockPendingClarifications,
  total_count: mockPendingApprovals.length + mockPendingClarifications.length,
};

// =============================================================================
// Handlers
// =============================================================================

export const agentRequestHandlers = [
  /**
   * GET /api/v1/agents/requests/pending - List pending HITL requests
   */
  http.get("/api/v1/agents/requests/pending", async ({ request }) => {
    await delay(50); // Simulate network delay

    const url = new URL(request.url);
    const sessionId = url.searchParams.get("session_id");
    const status = url.searchParams.get("status") as AgentRequestStatus | null;
    const requestType = url.searchParams.get("request_type");

    let approvals = [...mockPendingApprovals];
    let clarifications = [...mockPendingClarifications];

    // Filter by session_id if provided
    if (sessionId) {
      approvals = approvals.filter((a) => a.session_id === sessionId);
      clarifications = clarifications.filter((c) => c.session_id === sessionId);
    }

    // Filter by request_type if provided
    if (requestType === "approval") {
      clarifications = [];
    } else if (requestType === "clarification") {
      approvals = [];
    }

    return HttpResponse.json({
      approvals,
      clarifications,
      total_count: approvals.length + clarifications.length,
    } satisfies PendingAgentRequestsResponse);
  }),

  /**
   * POST /api/v1/agents/requests/batch/approve - Batch approve requests
   * NOTE: Batch handlers MUST come before :requestId handlers to avoid path conflicts
   */
  http.post("/api/v1/agents/requests/batch/approve", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as {
      request_ids: string[];
      approved_by: string;
      reason?: string;
    };

    const results: Array<{
      request_id: string;
      success: boolean;
      error?: string;
    }> = [];

    for (const requestId of body.request_ids) {
      const found = mockPendingApprovals.find((a) => a.request_id === requestId);
      if (found) {
        results.push({ request_id: requestId, success: true });
      } else {
        results.push({
          request_id: requestId,
          success: false,
          error: "Request not found",
        });
      }
    }

    const processed = results.filter((r) => r.success).length;
    const failed = results.filter((r) => !r.success).length;

    return HttpResponse.json({
      success: failed === 0,
      processed,
      failed,
      results,
    } satisfies BatchAgentRequestResponse);
  }),

  /**
   * POST /api/v1/agents/requests/batch/reject - Batch reject requests
   * NOTE: Batch handlers MUST come before :requestId handlers to avoid path conflicts
   */
  http.post("/api/v1/agents/requests/batch/reject", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as {
      request_ids: string[];
      rejected_by: string;
      reason?: string;
    };

    const results: Array<{
      request_id: string;
      success: boolean;
      error?: string;
    }> = [];

    for (const requestId of body.request_ids) {
      const found = mockPendingApprovals.find((a) => a.request_id === requestId);
      if (found) {
        results.push({ request_id: requestId, success: true });
      } else {
        results.push({
          request_id: requestId,
          success: false,
          error: "Request not found",
        });
      }
    }

    const processed = results.filter((r) => r.success).length;
    const failed = results.filter((r) => !r.success).length;

    return HttpResponse.json({
      success: failed === 0,
      processed,
      failed,
      results,
    } satisfies BatchAgentRequestResponse);
  }),

  /**
   * GET /api/v1/agents/requests/:id - Get request details
   */
  http.get("/api/v1/agents/requests/:requestId", async ({ params }) => {
    await delay(50);

    const { requestId } = params;

    // Check approvals first
    const approval = mockPendingApprovals.find((a) => a.request_id === requestId);
    if (approval) {
      return HttpResponse.json({
        ...approval,
        type: "approval",
        status: "pending",
      });
    }

    // Check clarifications
    const clarification = mockPendingClarifications.find(
      (c) => c.request_id === requestId
    );
    if (clarification) {
      return HttpResponse.json({
        ...clarification,
        type: "clarification",
        status: "pending",
      });
    }

    // Not found
    return HttpResponse.json(
      { error: "Request not found", request_id: requestId },
      { status: 404 }
    );
  }),

  /**
   * POST /api/v1/agents/requests/:id/approve - Approve request
   */
  http.post("/api/v1/agents/requests/:requestId/approve", async ({ params, request }) => {
    await delay(50);

    const { requestId } = params;
    const body = (await request.json()) as {
      approved_by: string;
      reason?: string;
      modifications?: Record<string, unknown>;
    };

    // Find the request
    const approval = mockPendingApprovals.find((a) => a.request_id === requestId);
    if (!approval) {
      return HttpResponse.json(
        { error: "Request not found", request_id: requestId },
        { status: 404 }
      );
    }

    // Return success response
    return HttpResponse.json({
      success: true,
      request_id: requestId as string,
      status: "approved",
      message: body.reason ?? `Approved by ${body.approved_by}`,
    } satisfies AgentRequestActionResponse);
  }),

  /**
   * POST /api/v1/agents/requests/:id/reject - Reject request
   */
  http.post("/api/v1/agents/requests/:requestId/reject", async ({ params, request }) => {
    await delay(50);

    const { requestId } = params;
    const body = (await request.json()) as {
      rejected_by: string;
      reason?: string;
    };

    // Find the request
    const approval = mockPendingApprovals.find((a) => a.request_id === requestId);
    if (!approval) {
      return HttpResponse.json(
        { error: "Request not found", request_id: requestId },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      success: true,
      request_id: requestId as string,
      status: "rejected",
      message: body.reason ?? `Rejected by ${body.rejected_by}`,
    } satisfies AgentRequestActionResponse);
  }),

  /**
   * POST /api/v1/agents/requests/:id/respond - Respond to clarification
   */
  http.post("/api/v1/agents/requests/:requestId/respond", async ({ params, request }) => {
    await delay(50);

    const { requestId } = params;
    const body = (await request.json()) as {
      response_type: "choice" | "text" | "confirm";
      selected_option?: string;
      text_response?: string;
      confirmed?: boolean;
    };

    // Find the clarification request
    const clarification = mockPendingClarifications.find(
      (c) => c.request_id === requestId
    );
    if (!clarification) {
      return HttpResponse.json(
        { error: "Request not found", request_id: requestId },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      success: true,
      request_id: requestId as string,
      status: "responded",
      message: `Responded with ${body.response_type}: ${body.selected_option ?? body.text_response ?? String(body.confirmed)}`,
    } satisfies AgentRequestActionResponse);
  }),
];

export default agentRequestHandlers;
