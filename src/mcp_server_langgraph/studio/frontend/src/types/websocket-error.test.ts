/**
 * WebSocket Error Types Tests
 *
 * TDD tests for unified WebSocket error types and factory utilities.
 */

import { describe, it, expect } from "vitest";
import {
  createWebSocketError,
  isRetryableError,
  getErrorCategory,
  WEBSOCKET_CLOSE_CODES,
  type HookWebSocketError,
  type HookErrorCode,
} from "./websocket-error";

describe("websocket-error types", () => {
  describe("createWebSocketError", () => {
    it("should create an error with required fields", () => {
      const error = createWebSocketError("missing_session_id", "Session ID is required");

      expect(error.code).toBe("missing_session_id");
      expect(error.message).toBe("Session ID is required");
      expect(error.retryable).toBe(false);
      expect(error.timestamp).toBeDefined();
    });

    it("should set retryable based on error code", () => {
      const networkError = createWebSocketError("network_error", "Connection lost");
      expect(networkError.retryable).toBe(true);

      const authError = createWebSocketError("token_expired", "Token expired");
      expect(authError.retryable).toBe(true);

      const invalidRequest = createWebSocketError("invalid_request", "Bad request");
      expect(invalidRequest.retryable).toBe(false);
    });

    it("should allow overriding retryable", () => {
      const error = createWebSocketError(
        "network_error",
        "Connection lost",
        { retryable: false }
      );

      expect(error.retryable).toBe(false);
    });

    it("should include optional context", () => {
      const error = createWebSocketError(
        "rate_limited",
        "Too many requests",
        {
          context: {
            retryAfter: 60,
            traceId: "trace-123",
          },
        }
      );

      expect(error.context?.retryAfter).toBe(60);
      expect(error.context?.traceId).toBe("trace-123");
    });

    it("should include optional details", () => {
      const error = createWebSocketError(
        "validation_error",
        "Invalid input",
        {
          details: {
            field: "session_id",
            expected: "string",
          },
        }
      );

      expect(error.details?.field).toBe("session_id");
    });
  });

  describe("isRetryableError", () => {
    it("should return true for network errors", () => {
      const error = createWebSocketError("network_error", "Connection lost");
      expect(isRetryableError(error)).toBe(true);
    });

    it("should return true for server errors", () => {
      const error = createWebSocketError("internal_error", "Server error");
      expect(isRetryableError(error)).toBe(true);
    });

    it("should return true for token expired", () => {
      const error = createWebSocketError("token_expired", "Token expired");
      expect(isRetryableError(error)).toBe(true);
    });

    it("should return false for validation errors", () => {
      const error = createWebSocketError("validation_error", "Invalid input");
      expect(isRetryableError(error)).toBe(false);
    });

    it("should return false for missing session ID", () => {
      const error = createWebSocketError("missing_session_id", "No session");
      expect(isRetryableError(error)).toBe(false);
    });

    it("should respect explicit retryable override", () => {
      const error = createWebSocketError("network_error", "Error", { retryable: false });
      expect(isRetryableError(error)).toBe(false);
    });
  });

  describe("getErrorCategory", () => {
    it("should categorize authentication errors", () => {
      expect(getErrorCategory("token_expired")).toBe("authentication");
      expect(getErrorCategory("unauthorized")).toBe("authentication");
    });

    it("should categorize network errors", () => {
      expect(getErrorCategory("network_error")).toBe("network");
      expect(getErrorCategory("connection_closed")).toBe("network");
    });

    it("should categorize server errors", () => {
      expect(getErrorCategory("internal_error")).toBe("server");
      expect(getErrorCategory("server_error")).toBe("server");
    });

    it("should categorize client errors", () => {
      expect(getErrorCategory("invalid_request")).toBe("client");
      expect(getErrorCategory("validation_error")).toBe("client");
      expect(getErrorCategory("missing_session_id")).toBe("client");
    });

    it("should categorize rate limiting", () => {
      expect(getErrorCategory("rate_limited")).toBe("quota");
    });
  });

  describe("WEBSOCKET_CLOSE_CODES", () => {
    it("should define standard close codes", () => {
      expect(WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE).toBe(1000);
      expect(WEBSOCKET_CLOSE_CODES.GOING_AWAY).toBe(1001);
      expect(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE).toBe(1006);
    });

    it("should define custom close codes", () => {
      expect(WEBSOCKET_CLOSE_CODES.TOKEN_EXPIRED).toBe(4010);
      expect(WEBSOCKET_CLOSE_CODES.PROTOCOL_VERSION_MISMATCH).toBe(4009);
    });
  });

  describe("HookWebSocketError type", () => {
    it("should allow all valid hook error codes", () => {
      const codes: HookErrorCode[] = [
        "missing_session_id",
        "network_error",
        "connection_closed",
        "token_expired",
        "unauthorized",
        "rate_limited",
        "internal_error",
        "invalid_request",
        "validation_error",
        "server_error",
        "not_found",
        "timeout",
      ];

      codes.forEach((code) => {
        const error: HookWebSocketError = {
          code,
          message: `Error: ${code}`,
          retryable: false,
          timestamp: Date.now(),
        };
        expect(error.code).toBe(code);
      });
    });
  });
});
