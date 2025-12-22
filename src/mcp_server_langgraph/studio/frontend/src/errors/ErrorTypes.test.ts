/**
 * ErrorTypes Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the error type taxonomy for consistent error handling across
 * the application.
 */

import { describe, it, expect } from "vitest";
import {
  ClassifiedError,
  isRecoverable,
  getErrorCategory,
  createClassifiedError,
  isNetworkError,
  isAuthError,
  isValidationError,
  isServerError,
  isRateLimitError,
  ERROR_CATEGORIES,
  ERROR_CODES,
} from "./ErrorTypes";

describe("ErrorTypes", () => {
  describe("ERROR_CATEGORIES", () => {
    it("defines all 9 error categories", () => {
      expect(ERROR_CATEGORIES).toHaveLength(9);
      expect(ERROR_CATEGORIES).toContain("network");
      expect(ERROR_CATEGORIES).toContain("authentication");
      expect(ERROR_CATEGORIES).toContain("authorization");
      expect(ERROR_CATEGORIES).toContain("validation");
      expect(ERROR_CATEGORIES).toContain("server");
      expect(ERROR_CATEGORIES).toContain("client");
      expect(ERROR_CATEGORIES).toContain("timeout");
      expect(ERROR_CATEGORIES).toContain("quota");
      expect(ERROR_CATEGORIES).toContain("unknown");
    });
  });

  describe("ERROR_CODES", () => {
    it("maps common HTTP status codes to error categories", () => {
      expect(ERROR_CODES[400]).toBe("validation");
      expect(ERROR_CODES[401]).toBe("authentication");
      expect(ERROR_CODES[403]).toBe("authorization");
      expect(ERROR_CODES[404]).toBe("client");
      expect(ERROR_CODES[408]).toBe("timeout");
      expect(ERROR_CODES[429]).toBe("quota");
      expect(ERROR_CODES[500]).toBe("server");
      expect(ERROR_CODES[502]).toBe("server");
      expect(ERROR_CODES[503]).toBe("server");
      expect(ERROR_CODES[504]).toBe("timeout");
    });
  });

  describe("isRecoverable", () => {
    it("returns true for recoverable error categories", () => {
      expect(isRecoverable("network")).toBe(true);
      expect(isRecoverable("timeout")).toBe(true);
      expect(isRecoverable("quota")).toBe(true);
      expect(isRecoverable("server")).toBe(true);
    });

    it("returns false for non-recoverable error categories", () => {
      expect(isRecoverable("authorization")).toBe(false);
    });

    it("returns true for authentication (recoverable via re-auth)", () => {
      expect(isRecoverable("authentication")).toBe(true);
    });

    it("returns false for validation errors (requires input fix)", () => {
      expect(isRecoverable("validation")).toBe(false);
    });

    it("returns 'maybe' for client errors", () => {
      expect(isRecoverable("client")).toBe("maybe");
    });

    it("returns 'maybe' for unknown errors", () => {
      expect(isRecoverable("unknown")).toBe("maybe");
    });
  });

  describe("getErrorCategory", () => {
    it("returns correct category for HTTP status codes", () => {
      expect(getErrorCategory(401)).toBe("authentication");
      expect(getErrorCategory(403)).toBe("authorization");
      expect(getErrorCategory(500)).toBe("server");
      expect(getErrorCategory(429)).toBe("quota");
    });

    it("returns 'unknown' for unrecognized status codes", () => {
      expect(getErrorCategory(999)).toBe("unknown");
    });

    it("returns category from error code string", () => {
      expect(getErrorCategory("NETWORK_ERROR")).toBe("network");
      expect(getErrorCategory("AUTH_EXPIRED")).toBe("authentication");
      expect(getErrorCategory("PERMISSION_DENIED")).toBe("authorization");
      expect(getErrorCategory("INVALID_INPUT")).toBe("validation");
      expect(getErrorCategory("RATE_LIMITED")).toBe("quota");
      expect(getErrorCategory("CONNECTION_TIMEOUT")).toBe("timeout");
    });

    it("returns 'unknown' for unrecognized error codes", () => {
      expect(getErrorCategory("RANDOM_ERROR")).toBe("unknown");
    });
  });

  describe("createClassifiedError", () => {
    it("creates a ClassifiedError from Error object", () => {
      const error = new Error("Connection failed");
      const classified = createClassifiedError(error, "network");

      expect(classified.category).toBe("network");
      expect(classified.message).toBe("Connection failed");
      expect(classified.originalError).toBe(error);
      expect(classified.recoverable).toBe(true);
      expect(classified.timestamp).toBeDefined();
      expect(typeof classified.timestamp).toBe("number");
    });

    it("includes optional fields when provided", () => {
      const error = new Error("Session expired");
      const classified = createClassifiedError(error, "authentication", {
        code: "AUTH_001",
        statusCode: 401,
        traceId: "trace-123",
        context: { userId: "user-1" },
      });

      expect(classified.code).toBe("AUTH_001");
      expect(classified.statusCode).toBe(401);
      expect(classified.traceId).toBe("trace-123");
      expect(classified.context).toEqual({ userId: "user-1" });
    });

    it("auto-detects recoverability based on category", () => {
      expect(
        createClassifiedError(new Error("timeout"), "timeout").recoverable
      ).toBe(true);
      expect(
        createClassifiedError(new Error("forbidden"), "authorization").recoverable
      ).toBe(false);
    });

    it("allows overriding recoverable flag", () => {
      const error = createClassifiedError(new Error("test"), "authorization", {
        recoverable: true, // Override default false
      });
      expect(error.recoverable).toBe(true);
    });
  });

  describe("type guard functions", () => {
    const networkError = createClassifiedError(new Error("offline"), "network");
    const authError = createClassifiedError(new Error("expired"), "authentication");
    const authzError = createClassifiedError(new Error("denied"), "authorization");
    const validationError = createClassifiedError(new Error("invalid"), "validation");
    const serverError = createClassifiedError(new Error("crash"), "server");
    const quotaError = createClassifiedError(new Error("limited"), "quota");

    describe("isNetworkError", () => {
      it("returns true for network errors", () => {
        expect(isNetworkError(networkError)).toBe(true);
      });

      it("returns false for other error types", () => {
        expect(isNetworkError(authError)).toBe(false);
        expect(isNetworkError(serverError)).toBe(false);
      });
    });

    describe("isAuthError", () => {
      it("returns true for authentication errors", () => {
        expect(isAuthError(authError)).toBe(true);
      });

      it("returns true for authorization errors", () => {
        expect(isAuthError(authzError)).toBe(true);
      });

      it("returns false for other error types", () => {
        expect(isAuthError(networkError)).toBe(false);
      });
    });

    describe("isValidationError", () => {
      it("returns true for validation errors", () => {
        expect(isValidationError(validationError)).toBe(true);
      });

      it("returns false for other error types", () => {
        expect(isValidationError(serverError)).toBe(false);
      });
    });

    describe("isServerError", () => {
      it("returns true for server errors", () => {
        expect(isServerError(serverError)).toBe(true);
      });

      it("returns false for other error types", () => {
        expect(isServerError(networkError)).toBe(false);
      });
    });

    describe("isRateLimitError", () => {
      it("returns true for quota/rate limit errors", () => {
        expect(isRateLimitError(quotaError)).toBe(true);
      });

      it("returns false for other error types", () => {
        expect(isRateLimitError(serverError)).toBe(false);
      });
    });
  });

  describe("ClassifiedError interface", () => {
    it("includes all required fields", () => {
      const classified: ClassifiedError = {
        category: "network",
        message: "Connection failed",
        recoverable: true,
        timestamp: Date.now(),
        originalError: new Error("Connection failed"),
      };

      expect(classified.category).toBeDefined();
      expect(classified.message).toBeDefined();
      expect(classified.recoverable).toBeDefined();
      expect(classified.timestamp).toBeDefined();
      expect(classified.originalError).toBeDefined();
    });

    it("allows optional fields", () => {
      const classified: ClassifiedError = {
        category: "authentication",
        message: "Token expired",
        recoverable: true,
        timestamp: Date.now(),
        originalError: new Error("Token expired"),
        code: "AUTH_TOKEN_EXPIRED",
        statusCode: 401,
        traceId: "abc-123",
        context: { action: "api_call" },
        retryAfter: 5000,
        userMessage: "Your session has expired. Please log in again.",
      };

      expect(classified.code).toBe("AUTH_TOKEN_EXPIRED");
      expect(classified.statusCode).toBe(401);
      expect(classified.traceId).toBe("abc-123");
      expect(classified.context).toEqual({ action: "api_call" });
      expect(classified.retryAfter).toBe(5000);
      expect(classified.userMessage).toBe(
        "Your session has expired. Please log in again."
      );
    });
  });
});
