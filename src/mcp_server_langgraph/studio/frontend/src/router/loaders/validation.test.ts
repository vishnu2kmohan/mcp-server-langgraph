/**
 * Loader Validation Tests
 *
 * TDD tests for runtime validation of loader data.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import {
  validateSession,
  validateMessage,
  validateMessages,
  validateSessionsResponse,
  validateMessagesResponse,
} from "./validation";

describe("Loader Validation", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });
  describe("validateSession", () => {
    it("should validate a valid session", () => {
      const session = {
        id: "session-123",
        name: "Test Session",
        created_at: "2025-01-15T10:00:00Z",
        updated_at: "2025-01-15T11:00:00Z",
        status: "active",
      };

      const result = validateSession(session);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.id).toBe("session-123");
      }
    });

    it("should reject invalid session (missing id)", () => {
      const session = {
        name: "Test",
        created_at: "2025-01-15T10:00:00Z",
        updated_at: "2025-01-15T11:00:00Z",
      };

      const result = validateSession(session);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toContainEqual(
          expect.objectContaining({ field: "id" }),
        );
      }
    });

    it("should reject null value", () => {
      const result = validateSession(null);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toBe("Value is null or undefined");
      }
    });

    it("should reject undefined value", () => {
      const result = validateSession(undefined);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toBe("Value is null or undefined");
      }
    });

    it("should reject non-object value", () => {
      const result = validateSession("string");

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toContain("Expected object");
      }
    });

    it("should reject array value", () => {
      const result = validateSession([1, 2, 3]);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toContain("Expected object");
      }
    });

    it("should validate session with invalid name type", () => {
      const session = {
        id: "session-123",
        name: 123, // Invalid: should be string
        created_at: "2025-01-15T10:00:00Z",
        updated_at: "2025-01-15T11:00:00Z",
      };

      const result = validateSession(session);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toContainEqual(
          expect.objectContaining({ field: "name" }),
        );
      }
    });

    it("should validate session with invalid status type", () => {
      const session = {
        id: "session-123",
        created_at: "2025-01-15T10:00:00Z",
        updated_at: "2025-01-15T11:00:00Z",
        status: 123, // Invalid: should be string
      };

      const result = validateSession(session);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toContainEqual(
          expect.objectContaining({ field: "status" }),
        );
      }
    });
  });

  describe("validateMessage", () => {
    it("should validate a valid message (backend format: message_id, timestamp)", () => {
      const message = {
        message_id: "msg-1",
        role: "user",
        content: "Hello",
        timestamp: "2025-01-15T10:00:00Z",
      };

      const result = validateMessage(message);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.message_id).toBe("msg-1");
        expect(result.data.role).toBe("user");
      }
    });

    it("should reject message with invalid role", () => {
      const message = {
        message_id: "msg-1",
        role: "invalid",
        content: "Hello",
        timestamp: "2025-01-15T10:00:00Z",
      };

      const result = validateMessage(message);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toContainEqual(
          expect.objectContaining({ field: "role" }),
        );
      }
    });

    it("should reject message with missing content", () => {
      const message = {
        message_id: "msg-1",
        role: "user",
        timestamp: "2025-01-15T10:00:00Z",
      };

      const result = validateMessage(message);

      expect(result.success).toBe(false);
    });

    it("should reject non-object input", () => {
      const result = validateMessage("string");

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toBe("Expected object");
      }
    });

    it("should reject null input", () => {
      const result = validateMessage(null);

      expect(result.success).toBe(false);
    });

    it("should reject array input", () => {
      const result = validateMessage([1, 2, 3]);

      expect(result.success).toBe(false);
    });

    it("should reject message with missing timestamp", () => {
      const message = {
        message_id: "msg-1",
        role: "user",
        content: "Hello",
      };

      const result = validateMessage(message);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toContainEqual(
          expect.objectContaining({ field: "timestamp" }),
        );
      }
    });
  });

  describe("validateMessages", () => {
    it("should validate array of messages (backend format)", () => {
      const messages = [
        {
          message_id: "msg-1",
          role: "user",
          content: "Hi",
          timestamp: "2025-01-15T10:00:00Z",
        },
        {
          message_id: "msg-2",
          role: "assistant",
          content: "Hello",
          timestamp: "2025-01-15T10:01:00Z",
        },
      ];

      const result = validateMessages(messages);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toHaveLength(2);
      }
    });

    it("should return partial result with valid messages only", () => {
      const messages = [
        {
          message_id: "msg-1",
          role: "user",
          content: "Hi",
          timestamp: "2025-01-15T10:00:00Z",
        },
        { message_id: "msg-2", role: "invalid", content: "Bad" }, // Invalid - no timestamp
        {
          message_id: "msg-3",
          role: "assistant",
          content: "Hello",
          timestamp: "2025-01-15T10:01:00Z",
        },
      ];

      const result = validateMessages(messages);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toHaveLength(2);
        expect(result.warnings).toHaveLength(1);
      }
    });

    it("should reject non-array input", () => {
      const result = validateMessages({});

      expect(result.success).toBe(false);
    });
  });

  describe("validateSessionsResponse", () => {
    it("should validate API response with data array (CursorPaginatedResponse format)", () => {
      const response = {
        data: [
          {
            id: "s-1",
            name: "Session 1",
            created_at: "2025-01-15",
            updated_at: "2025-01-15",
          },
          {
            id: "s-2",
            name: "Session 2",
            created_at: "2025-01-15",
            updated_at: "2025-01-15",
          },
        ],
        pagination: {
          next_cursor: null,
          prev_cursor: null,
          has_next: false,
          has_prev: false,
          count: 2,
        },
      };

      const result = validateSessionsResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.data).toHaveLength(2);
      }
    });

    it("should handle empty data array", () => {
      const response = { data: [] };

      const result = validateSessionsResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.data).toHaveLength(0);
      }
    });

    it("should reject response without data field", () => {
      const response = { items: [] };

      const result = validateSessionsResponse(response);

      expect(result.success).toBe(false);
    });
  });

  describe("validateMessagesResponse", () => {
    it("should validate API response with items array (backend message format)", () => {
      const response = {
        items: [
          {
            message_id: "m-1",
            role: "user",
            content: "Hi",
            timestamp: "2025-01-15T10:00:00Z",
          },
        ],
      };

      const result = validateMessagesResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.items).toHaveLength(1);
      }
    });

    it("should reject non-object input", () => {
      const result = validateMessagesResponse("string");

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toBe("Expected object");
      }
    });

    it("should reject null input", () => {
      const result = validateMessagesResponse(null);

      expect(result.success).toBe(false);
    });

    it("should reject array input", () => {
      const result = validateMessagesResponse([1, 2, 3]);

      expect(result.success).toBe(false);
    });

    it("should reject response without items array", () => {
      const response = { data: [] };

      const result = validateMessagesResponse(response);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toContain("items");
      }
    });

    it("should reject response with non-array items", () => {
      const response = { items: "not-an-array" };

      const result = validateMessagesResponse(response);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].field).toBe("items");
      }
    });

    it("should handle empty items array", () => {
      const response = { items: [] };

      const result = validateMessagesResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.items).toHaveLength(0);
      }
    });

    it("should filter invalid messages and return warnings", () => {
      const response = {
        items: [
          {
            message_id: "m-1",
            role: "user",
            content: "Hi",
            timestamp: "2025-01-15T10:00:00Z",
          },
          { message_id: "m-2", role: "invalid", content: "Bad" }, // Invalid role and missing timestamp
        ],
      };

      const result = validateMessagesResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.items).toHaveLength(1);
        expect(result.warnings).toHaveLength(1);
      }
    });
  });

  describe("validateSessionsResponse - additional tests", () => {
    it("should reject non-object input", () => {
      const result = validateSessionsResponse("string");

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].message).toBe("Expected object");
      }
    });

    it("should reject null input", () => {
      const result = validateSessionsResponse(null);

      expect(result.success).toBe(false);
    });

    it("should reject response with non-array data", () => {
      const response = { data: "not-an-array" };

      const result = validateSessionsResponse(response);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors[0].field).toBe("data");
      }
    });

    it("should filter invalid sessions and return warnings", () => {
      const response = {
        data: [
          {
            id: "s-1",
            name: "Session 1",
            created_at: "2025-01-15",
            updated_at: "2025-01-15",
          },
          { name: "Invalid", created_at: "2025-01-15" }, // Missing id and updated_at
        ],
      };

      const result = validateSessionsResponse(response);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.data).toHaveLength(1);
        expect(result.warnings).toHaveLength(1);
      }
    });
  });
});
