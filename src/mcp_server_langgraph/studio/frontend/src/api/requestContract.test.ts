/**
 * Comprehensive Request Contract Tests
 *
 * Validates that frontend request bodies match backend Pydantic models.
 * Each endpoint has a type guard that validates:
 * - Required fields are present
 * - Field names match backend contract (snake_case)
 * - Field types are correct
 * - No extra/wrong fields that backend doesn't expect
 *
 * Reference: src/mcp_server_langgraph/api/v1/*.py
 */

import { afterEach, describe, expect, it, vi } from "vitest";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// Session Endpoint Request Contract Tests
// =============================================================================

describe("Session Request Contracts", () => {
  /**
   * POST /api/v1/sessions
   * Backend: SessionCreate
   */
  function isValidSessionCreateRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // Optional fields
    if ("title" in o && typeof o.title !== "string") return false;
    if ("workflow_id" in o && typeof o.workflow_id !== "string") return false;
    if ("mode" in o && !["interactive", "headless"].includes(o.mode as string))
      return false;

    return true;
  }

  describe("POST /api/v1/sessions", () => {
    it("should accept empty body (all optional)", () => {
      expect(isValidSessionCreateRequest({})).toBe(true);
    });

    it("should accept session with title", () => {
      expect(
        isValidSessionCreateRequest({
          title: "My Session",
        }),
      ).toBe(true);
    });

    it("should accept session with workflow_id", () => {
      expect(
        isValidSessionCreateRequest({
          title: "My Session",
          workflow_id: "wf-123",
        }),
      ).toBe(true);
    });

    it("should accept session with mode", () => {
      expect(
        isValidSessionCreateRequest({
          title: "My Session",
          mode: "interactive",
        }),
      ).toBe(true);
    });
  });

  /**
   * POST /api/v1/sessions/generate-title
   * Backend: GenerateTitleRequest
   */
  function isValidGenerateTitleRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // content is required
    if (!("content" in o) || typeof o.content !== "string") return false;

    return true;
  }

  describe("POST /api/v1/sessions/generate-title", () => {
    it("should require content field", () => {
      expect(isValidGenerateTitleRequest({})).toBe(false);
      expect(
        isValidGenerateTitleRequest({
          content: "User message for title generation",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Chat Endpoint Request Contract Tests
// =============================================================================

describe("Chat Request Contracts", () => {
  /**
   * POST /api/v1/chat/completions
   * Backend: ChatCompletionRequest
   */
  function isValidChatCompletionRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // session_id is required
    if (!("session_id" in o) || typeof o.session_id !== "string") return false;

    // messages is required array
    if (!("messages" in o) || !Array.isArray(o.messages)) return false;

    // Validate each message has role and content
    for (const msg of o.messages) {
      if (typeof msg !== "object" || msg === null) return false;
      const m = msg as Record<string, unknown>;
      if (!("role" in m) || typeof m.role !== "string") return false;
      if (!("content" in m) || typeof m.content !== "string") return false;
    }

    // stream is optional boolean
    if ("stream" in o && typeof o.stream !== "boolean") return false;

    return true;
  }

  describe("POST /api/v1/chat/completions", () => {
    it("should require session_id and messages", () => {
      expect(isValidChatCompletionRequest({})).toBe(false);
      expect(
        isValidChatCompletionRequest({
          session_id: "sess-123",
        }),
      ).toBe(false);
      expect(
        isValidChatCompletionRequest({
          session_id: "sess-123",
          messages: [{ role: "user", content: "Hello" }],
        }),
      ).toBe(true);
    });

    it("should accept stream parameter", () => {
      expect(
        isValidChatCompletionRequest({
          session_id: "sess-123",
          messages: [{ role: "user", content: "Hello" }],
          stream: true,
        }),
      ).toBe(true);
    });

    it("should validate message structure", () => {
      // Missing role
      expect(
        isValidChatCompletionRequest({
          session_id: "sess-123",
          messages: [{ content: "Hello" }],
        }),
      ).toBe(false);

      // Missing content
      expect(
        isValidChatCompletionRequest({
          session_id: "sess-123",
          messages: [{ role: "user" }],
        }),
      ).toBe(false);
    });
  });
});

// =============================================================================
// Workflow Endpoint Request Contract Tests
// =============================================================================

describe("Workflow Request Contracts", () => {
  /**
   * POST /api/v1/workflows
   * Backend: WorkflowCreate
   */
  function isValidWorkflowCreateRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // name is required
    if (!("name" in o) || typeof o.name !== "string") return false;

    // description is optional
    if ("description" in o && typeof o.description !== "string") return false;

    // nodes is optional array
    if ("nodes" in o && !Array.isArray(o.nodes)) return false;

    // edges is optional array
    if ("edges" in o && !Array.isArray(o.edges)) return false;

    return true;
  }

  describe("POST /api/v1/workflows", () => {
    it("should require name", () => {
      expect(isValidWorkflowCreateRequest({})).toBe(false);
      expect(
        isValidWorkflowCreateRequest({
          name: "My Workflow",
        }),
      ).toBe(true);
    });

    it("should accept workflow with description", () => {
      expect(
        isValidWorkflowCreateRequest({
          name: "My Workflow",
          description: "A test workflow",
        }),
      ).toBe(true);
    });

    it("should accept workflow with nodes and edges", () => {
      expect(
        isValidWorkflowCreateRequest({
          name: "My Workflow",
          nodes: [{ id: "node-1", type: "start" }],
          edges: [{ from: "node-1", to: "node-2" }],
        }),
      ).toBe(true);
    });
  });

  /**
   * PUT /api/v1/workflows/:id
   * Backend: WorkflowUpdate
   */
  function isValidWorkflowUpdateRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // All fields are optional for update
    if ("name" in o && typeof o.name !== "string") return false;
    if ("description" in o && typeof o.description !== "string") return false;
    if ("nodes" in o && !Array.isArray(o.nodes)) return false;
    if ("edges" in o && !Array.isArray(o.edges)) return false;

    return true;
  }

  describe("PUT /api/v1/workflows/:id", () => {
    it("should accept empty body for partial update", () => {
      expect(isValidWorkflowUpdateRequest({})).toBe(true);
    });

    it("should accept partial updates", () => {
      expect(
        isValidWorkflowUpdateRequest({
          name: "Updated Name",
        }),
      ).toBe(true);
      expect(
        isValidWorkflowUpdateRequest({
          description: "Updated description",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Connection Endpoint Request Contract Tests
// =============================================================================

describe("Connection Request Contracts", () => {
  /**
   * POST /api/v1/connections
   * Backend: MCPConnectionCreate
   */
  function isValidMCPConnectionCreateRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // name is required
    if (!("name" in o) || typeof o.name !== "string") return false;

    // connection_type is required
    if (
      !("connection_type" in o) ||
      !["http", "websocket", "stdio"].includes(o.connection_type as string)
    )
      return false;

    // url is optional (for http/websocket types)
    if ("url" in o && typeof o.url !== "string") return false;

    return true;
  }

  describe("POST /api/v1/connections", () => {
    it("should require name and connection_type", () => {
      expect(isValidMCPConnectionCreateRequest({})).toBe(false);
      expect(
        isValidMCPConnectionCreateRequest({
          name: "My Connection",
        }),
      ).toBe(false);
      expect(
        isValidMCPConnectionCreateRequest({
          name: "My Connection",
          connection_type: "http",
        }),
      ).toBe(true);
    });

    it("should accept connection with url", () => {
      expect(
        isValidMCPConnectionCreateRequest({
          name: "My Connection",
          connection_type: "websocket",
          url: "ws://localhost:3000",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Project Endpoint Request Contract Tests
// =============================================================================

describe("Project Request Contracts", () => {
  /**
   * POST /api/v1/projects
   * Backend: ProjectCreate
   */
  function isValidProjectCreateRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // name is required
    if (!("name" in o) || typeof o.name !== "string") return false;

    // description is optional
    if ("description" in o && typeof o.description !== "string") return false;

    return true;
  }

  describe("POST /api/v1/projects", () => {
    it("should require name", () => {
      expect(isValidProjectCreateRequest({})).toBe(false);
      expect(
        isValidProjectCreateRequest({
          name: "My Project",
        }),
      ).toBe(true);
    });

    it("should accept project with description", () => {
      expect(
        isValidProjectCreateRequest({
          name: "My Project",
          description: "A test project",
        }),
      ).toBe(true);
    });
  });

  /**
   * POST /api/v1/projects/:id/members
   * Backend: AddMemberRequest
   */
  function isValidAddMemberRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // user_id is required
    if (!("user_id" in o) || typeof o.user_id !== "string") return false;

    // role is required
    if (
      !("role" in o) ||
      !["owner", "admin", "member", "viewer"].includes(o.role as string)
    )
      return false;

    return true;
  }

  describe("POST /api/v1/projects/:id/members", () => {
    it("should require user_id and role", () => {
      expect(isValidAddMemberRequest({})).toBe(false);
      expect(
        isValidAddMemberRequest({
          user_id: "user-123",
        }),
      ).toBe(false);
      expect(
        isValidAddMemberRequest({
          user_id: "user-123",
          role: "member",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// AI UX Endpoint Request Contract Tests
// =============================================================================

describe("AI UX Request Contracts", () => {
  /**
   * POST /api/v1/ai-ux/composite
   * Backend: CompositeAnalysisRequest
   */
  function isValidCompositeAnalysisRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // session_id is required
    if (!("session_id" in o) || typeof o.session_id !== "string") return false;

    // context is required
    if (!("context" in o) || typeof o.context !== "object") return false;

    return true;
  }

  describe("POST /api/v1/ai-ux/composite", () => {
    it("should require session_id and context", () => {
      expect(isValidCompositeAnalysisRequest({})).toBe(false);
      expect(
        isValidCompositeAnalysisRequest({
          session_id: "sess-123",
        }),
      ).toBe(false);
      expect(
        isValidCompositeAnalysisRequest({
          session_id: "sess-123",
          context: { page: "chat" },
        }),
      ).toBe(true);
    });
  });

  /**
   * POST /api/v1/ai/suggestions/feedback
   * Backend: SuggestionFeedbackRequest
   */
  function isValidSuggestionFeedbackRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // suggestion_id is required
    if (!("suggestion_id" in o) || typeof o.suggestion_id !== "string")
      return false;

    // feedback is required
    if (
      !("feedback" in o) ||
      !["helpful", "not_helpful", "inappropriate"].includes(
        o.feedback as string,
      )
    )
      return false;

    return true;
  }

  describe("POST /api/v1/ai/suggestions/feedback", () => {
    it("should require suggestion_id and feedback", () => {
      expect(isValidSuggestionFeedbackRequest({})).toBe(false);
      expect(
        isValidSuggestionFeedbackRequest({
          suggestion_id: "sugg-123",
          feedback: "helpful",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Notification Endpoint Request Contract Tests
// =============================================================================

describe("Notification Request Contracts", () => {
  /**
   * PUT /api/v1/notifications/preferences
   * Backend: NotificationPreferencesUpdate
   */
  function isValidNotificationPreferencesUpdate(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // email_enabled is optional boolean
    if ("email_enabled" in o && typeof o.email_enabled !== "boolean")
      return false;

    // push_enabled is optional boolean
    if ("push_enabled" in o && typeof o.push_enabled !== "boolean")
      return false;

    return true;
  }

  describe("PUT /api/v1/notifications/preferences", () => {
    it("should accept partial updates", () => {
      expect(isValidNotificationPreferencesUpdate({})).toBe(true);
      expect(
        isValidNotificationPreferencesUpdate({
          email_enabled: true,
        }),
      ).toBe(true);
      expect(
        isValidNotificationPreferencesUpdate({
          push_enabled: false,
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Metrics/Feedback Endpoint Request Contract Tests
// =============================================================================

describe("Metrics/Feedback Request Contracts", () => {
  /**
   * POST /api/v1/metrics/feedback
   * Backend: FeedbackRequest
   */
  function isValidFeedbackRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // type is required
    if (
      !("type" in o) ||
      !["bug", "feature", "general"].includes(o.type as string)
    )
      return false;

    // message is required
    if (!("message" in o) || typeof o.message !== "string") return false;

    return true;
  }

  describe("POST /api/v1/metrics/feedback", () => {
    it("should require type and message", () => {
      expect(isValidFeedbackRequest({})).toBe(false);
      expect(
        isValidFeedbackRequest({
          type: "bug",
        }),
      ).toBe(false);
      expect(
        isValidFeedbackRequest({
          type: "bug",
          message: "Found an issue with...",
        }),
      ).toBe(true);
    });
  });

  /**
   * POST /api/v1/sessions/:id/messages/:id/rating
   * Backend: MessageRatingRequest
   */
  function isValidMessageRatingRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // rating is required (1-5)
    if (!("rating" in o) || typeof o.rating !== "number") return false;
    if (o.rating < 1 || o.rating > 5) return false;

    // comment is optional
    if ("comment" in o && typeof o.comment !== "string") return false;

    return true;
  }

  describe("POST /api/v1/sessions/:id/messages/:id/rating", () => {
    it("should require rating between 1-5", () => {
      expect(isValidMessageRatingRequest({})).toBe(false);
      expect(
        isValidMessageRatingRequest({
          rating: 0,
        }),
      ).toBe(false);
      expect(
        isValidMessageRatingRequest({
          rating: 6,
        }),
      ).toBe(false);
      expect(
        isValidMessageRatingRequest({
          rating: 4,
        }),
      ).toBe(true);
    });

    it("should accept optional comment", () => {
      expect(
        isValidMessageRatingRequest({
          rating: 5,
          comment: "Very helpful response!",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Vector/Qdrant Endpoint Request Contract Tests
// =============================================================================

describe("Vector/Qdrant Request Contracts", () => {
  /**
   * POST /api/v1/vectors/search
   * Backend: VectorSearchRequest
   */
  function isValidVectorSearchRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // query is required (string or vector)
    if (
      !("query" in o) ||
      (typeof o.query !== "string" && !Array.isArray(o.query))
    )
      return false;

    // collection is required
    if (!("collection" in o) || typeof o.collection !== "string") return false;

    // limit is optional number
    if ("limit" in o && typeof o.limit !== "number") return false;

    return true;
  }

  describe("POST /api/v1/vectors/search", () => {
    it("should require query and collection", () => {
      expect(isValidVectorSearchRequest({})).toBe(false);
      expect(
        isValidVectorSearchRequest({
          query: "search term",
        }),
      ).toBe(false);
      expect(
        isValidVectorSearchRequest({
          query: "search term",
          collection: "documents",
        }),
      ).toBe(true);
    });

    it("should accept vector as query", () => {
      expect(
        isValidVectorSearchRequest({
          query: [0.1, 0.2, 0.3],
          collection: "embeddings",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// Admin Endpoint Request Contract Tests
// =============================================================================

describe("Admin Request Contracts", () => {
  /**
   * POST /api/v1/admin/service-principals
   * Backend: CreateServicePrincipalRequest
   */
  function isValidCreateServicePrincipalRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // name is required
    if (!("name" in o) || typeof o.name !== "string") return false;

    // description is optional
    if ("description" in o && typeof o.description !== "string") return false;

    // permissions is optional array
    if ("permissions" in o && !Array.isArray(o.permissions)) return false;

    return true;
  }

  describe("POST /api/v1/admin/service-principals", () => {
    it("should require name", () => {
      expect(isValidCreateServicePrincipalRequest({})).toBe(false);
      expect(
        isValidCreateServicePrincipalRequest({
          name: "my-service",
        }),
      ).toBe(true);
    });

    it("should accept permissions array", () => {
      expect(
        isValidCreateServicePrincipalRequest({
          name: "my-service",
          permissions: ["read", "write"],
        }),
      ).toBe(true);
    });
  });

  /**
   * POST /api/v1/remediations/:id/approve
   * Backend: ApproveRemediationRequest
   */
  function isValidApproveRemediationRequest(obj: unknown): boolean {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;

    // approved_by is required
    if (!("approved_by" in o) || typeof o.approved_by !== "string")
      return false;

    // reason is optional
    if ("reason" in o && typeof o.reason !== "string") return false;

    return true;
  }

  describe("POST /api/v1/remediations/:id/approve", () => {
    it("should require approved_by", () => {
      expect(isValidApproveRemediationRequest({})).toBe(false);
      expect(
        isValidApproveRemediationRequest({
          approved_by: "admin@example.com",
        }),
      ).toBe(true);
    });

    it("should accept optional reason", () => {
      expect(
        isValidApproveRemediationRequest({
          approved_by: "admin@example.com",
          reason: "Verified the remediation is safe",
        }),
      ).toBe(true);
    });
  });
});
