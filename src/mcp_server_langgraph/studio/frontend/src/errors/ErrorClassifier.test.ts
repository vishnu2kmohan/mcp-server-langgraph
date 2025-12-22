/**
 * ErrorClassifier Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the error classification logic that analyzes errors and
 * categorizes them for appropriate handling.
 */

import { describe, it, expect } from "vitest";
import {
  classifyError,
  classifyFetchError,
  classifyAxiosError,
  classifyWebSocketError,
} from "./ErrorClassifier";

describe("ErrorClassifier", () => {
  describe("classifyError", () => {
    describe("from Error objects", () => {
      it("classifies TypeError as client error", () => {
        const error = new TypeError("Cannot read property 'x' of undefined");
        const classified = classifyError(error);

        expect(classified.category).toBe("client");
        expect(classified.message).toBe("Cannot read property 'x' of undefined");
        expect(classified.recoverable).toBe("maybe");
      });

      it("classifies NetworkError as network error", () => {
        const error = new Error("NetworkError: Failed to fetch");
        const classified = classifyError(error);

        expect(classified.category).toBe("network");
        expect(classified.recoverable).toBe(true);
      });

      it("classifies timeout errors from message", () => {
        const error = new Error("Request timed out");
        const classified = classifyError(error);

        expect(classified.category).toBe("timeout");
        expect(classified.recoverable).toBe(true);
      });

      it("classifies CORS errors as network errors", () => {
        const error = new Error("CORS policy blocked the request");
        const classified = classifyError(error);

        expect(classified.category).toBe("network");
      });

      it("classifies unknown errors appropriately", () => {
        const error = new Error("Something unexpected happened");
        const classified = classifyError(error);

        expect(classified.category).toBe("unknown");
        expect(classified.recoverable).toBe("maybe");
      });
    });

    describe("from status codes", () => {
      it("classifies 400 as validation error", () => {
        const error = new Error("Bad Request");
        const classified = classifyError(error, { statusCode: 400 });

        expect(classified.category).toBe("validation");
        expect(classified.statusCode).toBe(400);
        expect(classified.recoverable).toBe(false);
      });

      it("classifies 401 as authentication error", () => {
        const error = new Error("Unauthorized");
        const classified = classifyError(error, { statusCode: 401 });

        expect(classified.category).toBe("authentication");
        expect(classified.recoverable).toBe(true);
      });

      it("classifies 403 as authorization error", () => {
        const error = new Error("Forbidden");
        const classified = classifyError(error, { statusCode: 403 });

        expect(classified.category).toBe("authorization");
        expect(classified.recoverable).toBe(false);
      });

      it("classifies 404 as client error", () => {
        const error = new Error("Not Found");
        const classified = classifyError(error, { statusCode: 404 });

        expect(classified.category).toBe("client");
      });

      it("classifies 429 as quota/rate limit error", () => {
        const error = new Error("Too Many Requests");
        const classified = classifyError(error, { statusCode: 429 });

        expect(classified.category).toBe("quota");
        expect(classified.recoverable).toBe(true);
      });

      it("classifies 5xx as server errors", () => {
        expect(classifyError(new Error(""), { statusCode: 500 }).category).toBe(
          "server"
        );
        expect(classifyError(new Error(""), { statusCode: 502 }).category).toBe(
          "server"
        );
        expect(classifyError(new Error(""), { statusCode: 503 }).category).toBe(
          "server"
        );
      });

      it("classifies 504 as timeout error", () => {
        const classified = classifyError(new Error("Gateway Timeout"), {
          statusCode: 504,
        });

        expect(classified.category).toBe("timeout");
      });
    });

    describe("with options", () => {
      it("includes traceId when provided", () => {
        const classified = classifyError(new Error("test"), {
          traceId: "trace-abc-123",
        });

        expect(classified.traceId).toBe("trace-abc-123");
      });

      it("includes context when provided", () => {
        const classified = classifyError(new Error("test"), {
          context: { action: "save_workflow", userId: "user-1" },
        });

        expect(classified.context).toEqual({
          action: "save_workflow",
          userId: "user-1",
        });
      });

      it("includes code when provided", () => {
        const classified = classifyError(new Error("test"), {
          code: "WORKFLOW_SAVE_FAILED",
        });

        expect(classified.code).toBe("WORKFLOW_SAVE_FAILED");
      });

      it("extracts retryAfter from options", () => {
        const classified = classifyError(new Error("rate limited"), {
          statusCode: 429,
          retryAfter: 30000,
        });

        expect(classified.retryAfter).toBe(30000);
      });
    });
  });

  describe("classifyFetchError", () => {
    it("classifies fetch Response with 401 status", async () => {
      const response = new Response(null, { status: 401 });
      const classified = await classifyFetchError(response);

      expect(classified.category).toBe("authentication");
      expect(classified.statusCode).toBe(401);
    });

    it("classifies fetch Response with 500 status", async () => {
      const response = new Response(null, { status: 500 });
      const classified = await classifyFetchError(response);

      expect(classified.category).toBe("server");
    });

    it("extracts Retry-After header for rate limits", async () => {
      const response = new Response(null, {
        status: 429,
        headers: { "Retry-After": "60" },
      });
      const classified = await classifyFetchError(response);

      expect(classified.category).toBe("quota");
      expect(classified.retryAfter).toBe(60000); // Converted to ms
    });

    it("extracts X-Trace-ID header", async () => {
      const response = new Response(null, {
        status: 500,
        headers: { "X-Trace-ID": "trace-xyz" },
      });
      const classified = await classifyFetchError(response);

      expect(classified.traceId).toBe("trace-xyz");
    });

    it("parses JSON error body when available", async () => {
      const body = JSON.stringify({
        error: { code: "INVALID_INPUT", message: "Name is required" },
      });
      const response = new Response(body, {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
      const classified = await classifyFetchError(response);

      expect(classified.code).toBe("INVALID_INPUT");
      expect(classified.message).toBe("Name is required");
    });

    it("handles TypeError from fetch (network failure)", () => {
      const error = new TypeError("Failed to fetch");
      const classified = classifyFetchError(error);

      expect(classified.category).toBe("network");
      expect(classified.recoverable).toBe(true);
    });

    it("handles AbortError as timeout", () => {
      const error = new DOMException("The operation was aborted", "AbortError");
      const classified = classifyFetchError(error);

      expect(classified.category).toBe("timeout");
    });
  });

  describe("classifyAxiosError", () => {
    it("classifies axios error with response", () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          status: 401,
          data: { error: "Token expired" },
          headers: { "x-trace-id": "trace-123" },
        },
        message: "Request failed with status code 401",
      };

      const classified = classifyAxiosError(axiosError);

      expect(classified.category).toBe("authentication");
      expect(classified.statusCode).toBe(401);
      expect(classified.traceId).toBe("trace-123");
    });

    it("classifies axios network error (no response)", () => {
      const axiosError = {
        isAxiosError: true,
        response: undefined,
        message: "Network Error",
        code: "ERR_NETWORK",
      };

      const classified = classifyAxiosError(axiosError);

      expect(classified.category).toBe("network");
      expect(classified.recoverable).toBe(true);
    });

    it("classifies axios timeout error", () => {
      const axiosError = {
        isAxiosError: true,
        code: "ECONNABORTED",
        message: "timeout of 5000ms exceeded",
      };

      const classified = classifyAxiosError(axiosError);

      expect(classified.category).toBe("timeout");
    });

    it("extracts error code from response data", () => {
      const axiosError = {
        isAxiosError: true,
        response: {
          status: 400,
          data: { error: { code: "VALIDATION_ERROR", message: "Invalid input" } },
        },
      };

      const classified = classifyAxiosError(axiosError);

      expect(classified.code).toBe("VALIDATION_ERROR");
    });
  });

  describe("classifyWebSocketError", () => {
    it("classifies WebSocket close with code 1000 as clean close (not error)", () => {
      const event = { code: 1000, reason: "Normal closure" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("client");
      expect(classified.recoverable).toBe(false);
    });

    it("classifies WebSocket close with code 1006 as network error", () => {
      const event = { code: 1006, reason: "Abnormal closure" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("network");
      expect(classified.recoverable).toBe(true);
    });

    it("classifies WebSocket close with code 1001 as client going away", () => {
      const event = { code: 1001, reason: "Going away" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("client");
    });

    it("classifies WebSocket close with code 1008 as authorization error", () => {
      const event = { code: 1008, reason: "Policy violation" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("authorization");
    });

    it("classifies WebSocket close with code 1011 as server error", () => {
      const event = { code: 1011, reason: "Internal server error" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("server");
    });

    it("classifies custom close code 4001 as authentication error", () => {
      const event = { code: 4001, reason: "Unauthorized" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("authentication");
    });

    it("classifies custom close code 4029 as rate limit error", () => {
      const event = { code: 4029, reason: "Rate limited" };
      const classified = classifyWebSocketError(event);

      expect(classified.category).toBe("quota");
    });
  });

  describe("edge cases", () => {
    it("handles null error gracefully", () => {
      const classified = classifyError(null as unknown as Error);

      expect(classified.category).toBe("unknown");
      expect(classified.message).toBe("Unknown error occurred");
    });

    it("handles undefined error gracefully", () => {
      const classified = classifyError(undefined as unknown as Error);

      expect(classified.category).toBe("unknown");
    });

    it("handles string as error", () => {
      const classified = classifyError("Something went wrong" as unknown as Error);

      expect(classified.message).toBe("Something went wrong");
      expect(classified.category).toBe("unknown");
    });

    it("handles object with message property", () => {
      const classified = classifyError({ message: "Custom error" } as Error);

      expect(classified.message).toBe("Custom error");
    });

    it("preserves original error reference", () => {
      const original = new Error("Original");
      const classified = classifyError(original);

      expect(classified.originalError).toBe(original);
    });
  });
});
