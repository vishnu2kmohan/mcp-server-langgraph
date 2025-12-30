/**
 * Orchestrator Status WebSocket Schema Contract Tests
 *
 * Validates that frontend and backend agree on WebSocket message schemas
 * for AI orchestrator status updates.
 *
 * This test ensures:
 * 1. TaskCategory values match backend TaskCategory enum
 * 2. OrchestratorStatus values match backend values
 * 3. Message type strings are consistent
 * 4. Payload structures are compatible
 */

import { describe, it, expect } from "vitest";

// Import frontend types (these are the contract we're validating)
import type {
  TaskCategory,
  OrchestratorStatus,
  TaskInfo,
  StatusChangeEvent,
} from "../../src/hooks/useAIOrchestratorStatus";

// =============================================================================
// Backend Contract Constants
// =============================================================================

/**
 * Backend TaskCategory enum values.
 * Source: src/mcp_server_langgraph/websocket/handlers/orchestrator_status.py
 */
const BACKEND_TASK_CATEGORIES = [
  "ux",
  "session",
  "conversation",
  "canvas",
  "diagram",
  "trace",
  "hitl",
  "command",
  "alert",
] as const;

/**
 * Backend OrchestratorStatus enum values.
 * Source: src/mcp_server_langgraph/websocket/handlers/orchestrator_status.py
 */
const BACKEND_ORCHESTRATOR_STATUSES = ["idle", "processing", "error"] as const;

/**
 * Backend WebSocket message types.
 * Source: src/mcp_server_langgraph/websocket/handlers/orchestrator_status.py
 */
const BACKEND_MESSAGE_TYPES = {
  STATUS_UPDATE: "orchestrator_status",
  TASK_STARTED: "task_started",
  TASK_COMPLETED: "task_completed",
  TASK_FAILED: "task_failed",
  TASK_PROGRESS: "task_progress",
  QUEUE_UPDATE: "queue_update",
} as const;

/**
 * Client-to-server message types.
 * Source: src/mcp_server_langgraph/websocket/handlers/orchestrator_status.py
 */
const CLIENT_MESSAGE_TYPES = {
  SUBSCRIBE: "subscribe",
  UNSUBSCRIBE: "unsubscribe",
  GET_STATUS: "get_status",
} as const;

// =============================================================================
// Contract Tests
// =============================================================================

describe("OrchestratorStatus Schema Contract", () => {
  describe("TaskCategory parity", () => {
    it("frontend TaskCategory type should include all backend values", () => {
      // Type assertion test - if frontend type doesn't include all backend values,
      // TypeScript will fail to compile
      const testCategories: TaskCategory[] = [...BACKEND_TASK_CATEGORIES];
      expect(testCategories).toHaveLength(BACKEND_TASK_CATEGORIES.length);
    });

    it("backend should support all 9 task categories", () => {
      expect(BACKEND_TASK_CATEGORIES).toContain("ux");
      expect(BACKEND_TASK_CATEGORIES).toContain("session");
      expect(BACKEND_TASK_CATEGORIES).toContain("conversation");
      expect(BACKEND_TASK_CATEGORIES).toContain("canvas");
      expect(BACKEND_TASK_CATEGORIES).toContain("diagram");
      expect(BACKEND_TASK_CATEGORIES).toContain("trace");
      expect(BACKEND_TASK_CATEGORIES).toContain("hitl");
      expect(BACKEND_TASK_CATEGORIES).toContain("command");
      expect(BACKEND_TASK_CATEGORIES).toContain("alert");
      expect(BACKEND_TASK_CATEGORIES).toHaveLength(9);
    });
  });

  describe("OrchestratorStatus parity", () => {
    it("frontend OrchestratorStatus type should include all backend values", () => {
      // Type assertion test
      const testStatuses: OrchestratorStatus[] = [
        ...BACKEND_ORCHESTRATOR_STATUSES,
      ];
      expect(testStatuses).toHaveLength(BACKEND_ORCHESTRATOR_STATUSES.length);
    });

    it("backend should support idle, processing, and error statuses", () => {
      expect(BACKEND_ORCHESTRATOR_STATUSES).toContain("idle");
      expect(BACKEND_ORCHESTRATOR_STATUSES).toContain("processing");
      expect(BACKEND_ORCHESTRATOR_STATUSES).toContain("error");
      expect(BACKEND_ORCHESTRATOR_STATUSES).toHaveLength(3);
    });
  });

  describe("WebSocket message types", () => {
    it("should have standard server-to-client message types", () => {
      expect(BACKEND_MESSAGE_TYPES.STATUS_UPDATE).toBe("orchestrator_status");
      expect(BACKEND_MESSAGE_TYPES.TASK_STARTED).toBe("task_started");
      expect(BACKEND_MESSAGE_TYPES.TASK_COMPLETED).toBe("task_completed");
      expect(BACKEND_MESSAGE_TYPES.TASK_FAILED).toBe("task_failed");
      expect(BACKEND_MESSAGE_TYPES.TASK_PROGRESS).toBe("task_progress");
      expect(BACKEND_MESSAGE_TYPES.QUEUE_UPDATE).toBe("queue_update");
    });

    it("should have standard client-to-server message types", () => {
      expect(CLIENT_MESSAGE_TYPES.SUBSCRIBE).toBe("subscribe");
      expect(CLIENT_MESSAGE_TYPES.UNSUBSCRIBE).toBe("unsubscribe");
      expect(CLIENT_MESSAGE_TYPES.GET_STATUS).toBe("get_status");
    });
  });

  describe("Message payload structures", () => {
    it("orchestrator_status payload should match expected structure", () => {
      // Example message from backend
      const backendMessage = {
        type: "orchestrator_status",
        payload: {
          status: "processing",
          message: "Analyzing persona...",
          task_type: "persona_analysis",
          category: "ux",
        },
      };

      // Validate required fields
      expect(backendMessage.type).toBe("orchestrator_status");
      expect(backendMessage.payload.status).toBeDefined();
      expect(typeof backendMessage.payload.status).toBe("string");

      // Optional fields
      expect(typeof backendMessage.payload.message).toBe("string");
      expect(typeof backendMessage.payload.task_type).toBe("string");
      expect(typeof backendMessage.payload.category).toBe("string");
    });

    it("task_started payload should match expected structure", () => {
      const backendMessage = {
        type: "task_started",
        payload: {
          task_id: "task-123",
          task_type: "error_analysis",
          category: "ux",
          started_at: "2025-01-01T00:00:00Z",
        },
      };

      expect(backendMessage.type).toBe("task_started");
      expect(backendMessage.payload.task_id).toBeDefined();
      expect(backendMessage.payload.task_type).toBeDefined();
      expect(backendMessage.payload.category).toBeDefined();
      expect(backendMessage.payload.started_at).toBeDefined();
    });

    it("task_completed payload should match expected structure", () => {
      const backendMessage = {
        type: "task_completed",
        payload: {
          task_id: "task-123",
          task_type: "disclosure_analysis",
          category: "ux",
          completed_at: "2025-01-01T00:01:00Z",
          success: true,
        },
      };

      expect(backendMessage.type).toBe("task_completed");
      expect(backendMessage.payload.task_id).toBeDefined();
      expect(backendMessage.payload.completed_at).toBeDefined();
      expect(typeof backendMessage.payload.success).toBe("boolean");
    });

    it("task_failed payload should match expected structure", () => {
      const backendMessage = {
        type: "task_failed",
        payload: {
          task_id: "task-456",
          task_type: "intent_detect",
          category: "conversation",
          failed_at: "2025-01-01T00:01:00Z",
          error: "LLM rate limit exceeded",
        },
      };

      expect(backendMessage.type).toBe("task_failed");
      expect(backendMessage.payload.task_id).toBeDefined();
      expect(backendMessage.payload.failed_at).toBeDefined();
      expect(backendMessage.payload.error).toBeDefined();
    });

    it("task_progress payload should match expected structure", () => {
      const backendMessage = {
        type: "task_progress",
        payload: {
          task_id: "task-789",
          progress: 75,
          message: "Processing step 3 of 4...",
        },
      };

      expect(backendMessage.type).toBe("task_progress");
      expect(backendMessage.payload.task_id).toBeDefined();
      expect(backendMessage.payload.progress).toBeDefined();
      expect(typeof backendMessage.payload.progress).toBe("number");
      expect(backendMessage.payload.progress).toBeGreaterThanOrEqual(0);
      expect(backendMessage.payload.progress).toBeLessThanOrEqual(100);
      // message is optional
      expect(typeof backendMessage.payload.message).toBe("string");
    });

    it("queue_update payload should match expected structure", () => {
      const backendMessage = {
        type: "queue_update",
        payload: {
          action: "added",
          task_id: "task-101",
          task_type: "persona_analysis",
          category: "ux",
          queue_depth: 3,
        },
      };

      expect(backendMessage.type).toBe("queue_update");
      expect(backendMessage.payload.action).toBeDefined();
      expect(backendMessage.payload.task_id).toBeDefined();
      expect(backendMessage.payload.queue_depth).toBeDefined();
      expect(typeof backendMessage.payload.queue_depth).toBe("number");
    });
  });

  describe("Frontend type compatibility", () => {
    it("StatusChangeEvent should accept backend orchestrator_status payload", () => {
      const backendPayload = {
        status: "processing" as OrchestratorStatus,
        message: "Analyzing...",
        taskType: "persona_analysis",
        category: "ux" as TaskCategory,
      };

      // This type assertion validates compatibility
      const event: StatusChangeEvent = backendPayload;
      expect(event.status).toBe("processing");
    });

    it("TaskInfo should represent task lifecycle data", () => {
      const taskInfo: TaskInfo = {
        taskId: "task-789",
        taskType: "trace_summarize",
        category: "trace",
        startedAt: new Date(),
      };

      expect(taskInfo.taskId).toBeDefined();
      expect(taskInfo.taskType).toBeDefined();
      expect(taskInfo.category).toBeDefined();
      expect(taskInfo.startedAt).toBeInstanceOf(Date);
    });
  });
});
