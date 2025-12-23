/**
 * errorReporter Tests
 *
 * TDD - Sprint 3 - Phase 2.4: Error Reporting Pipeline
 *
 * Tests for the error reporting utility that:
 * - Posts errors to backend telemetry
 * - Includes stack traces, user context, session info
 * - Rate limits reports (max 10/minute)
 * - Integrates with ClassifiedError types
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

import {
  ErrorReporter,
  type ErrorReport,
  type ErrorReporterConfig,
  createErrorReport,
} from "./errorReporter";

// =============================================================================
// Test Data
// =============================================================================

const mockError = new Error("Test error message");
mockError.stack = "Error: Test error message\n    at test.ts:10:5";

const mockClassifiedError = {
  category: "network" as const,
  code: "NETWORK_ERROR",
  message: "Connection failed",
  originalError: mockError,
  recoverable: true,
  statusCode: undefined,
};

const mockUserContext = {
  userId: "user-123",
  persona: "alice-builder",
  sessionId: "session-456",
};

// =============================================================================
// Tests
// =============================================================================

describe("errorReporter", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();

    // Default handler for error reporting
    server.use(
      http.post("/api/v1/errors/report", async () => {
        return HttpResponse.json({ success: true, reportId: "report-123" });
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("createErrorReport", () => {
    it("creates report from Error object", () => {
      const report = createErrorReport(mockError);

      expect(report.message).toBe("Test error message");
      expect(report.stack).toBeDefined();
      expect(report.category).toBe("unknown");
      expect(report.timestamp).toBeDefined();
    });

    it("creates report from ClassifiedError", () => {
      const report = createErrorReport(mockClassifiedError);

      expect(report.message).toBe("Connection failed");
      expect(report.category).toBe("network");
      expect(report.code).toBe("NETWORK_ERROR");
      expect(report.recoverable).toBe(true);
    });

    it("includes user context when provided", () => {
      const report = createErrorReport(mockError, {
        userContext: mockUserContext,
      });

      expect(report.userContext?.userId).toBe("user-123");
      expect(report.userContext?.persona).toBe("alice-builder");
      expect(report.userContext?.sessionId).toBe("session-456");
    });

    it("includes browser info", () => {
      const report = createErrorReport(mockError);

      expect(report.browserInfo).toBeDefined();
      expect(report.browserInfo.url).toBeDefined();
    });

    it("includes custom context", () => {
      const report = createErrorReport(mockError, {
        customContext: { component: "ChatPage", action: "sendMessage" },
      });

      expect(report.customContext).toEqual({
        component: "ChatPage",
        action: "sendMessage",
      });
    });
  });

  describe("ErrorReporter", () => {
    describe("Initialization", () => {
      it("creates instance with default config", () => {
        const reporter = new ErrorReporter();

        expect(reporter).toBeDefined();
      });

      it("accepts custom config", () => {
        const config: ErrorReporterConfig = {
          endpoint: "/custom/errors",
          maxReportsPerMinute: 5,
          enabled: true,
        };

        const reporter = new ErrorReporter(config);
        expect(reporter).toBeDefined();
      });
    });

    describe("Reporting Errors", () => {
      it("sends error report to backend", async () => {
        let capturedBody: ErrorReport | null = null;
        server.use(
          http.post("/api/v1/errors/report", async ({ request }) => {
            capturedBody = (await request.json()) as ErrorReport;
            return HttpResponse.json({ success: true, reportId: "report-123" });
          }),
        );

        const reporter = new ErrorReporter();
        const result = await reporter.report(mockError);

        expect(result.success).toBe(true);
        expect(result.reportId).toBe("report-123");
        expect(capturedBody?.message).toBe("Test error message");
      });

      it("reports classified errors with full context", async () => {
        let capturedBody: ErrorReport | null = null;
        server.use(
          http.post("/api/v1/errors/report", async ({ request }) => {
            capturedBody = (await request.json()) as ErrorReport;
            return HttpResponse.json({ success: true, reportId: "report-456" });
          }),
        );

        const reporter = new ErrorReporter();
        await reporter.report(mockClassifiedError);

        expect(capturedBody?.category).toBe("network");
        expect(capturedBody?.code).toBe("NETWORK_ERROR");
      });

      it("handles API failure gracefully", async () => {
        server.use(
          http.post("/api/v1/errors/report", async () => {
            return new HttpResponse(null, { status: 500 });
          }),
        );

        const reporter = new ErrorReporter();
        const result = await reporter.report(mockError);

        expect(result.success).toBe(false);
        expect(result.error).toBeDefined();
      });

      it("does not throw on report failure", async () => {
        server.use(
          http.post("/api/v1/errors/report", async () => {
            return new HttpResponse(null, { status: 500 });
          }),
        );

        const reporter = new ErrorReporter();

        await expect(reporter.report(mockError)).resolves.not.toThrow();
      });
    });

    describe("Rate Limiting", () => {
      it("rate limits to maxReportsPerMinute", async () => {
        const reporter = new ErrorReporter({ maxReportsPerMinute: 3 });

        // Send 3 reports (should succeed)
        const result1 = await reporter.report(mockError);
        const result2 = await reporter.report(mockError);
        const result3 = await reporter.report(mockError);

        expect(result1.success).toBe(true);
        expect(result2.success).toBe(true);
        expect(result3.success).toBe(true);

        // 4th report should be rate limited
        const result4 = await reporter.report(mockError);
        expect(result4.success).toBe(false);
        expect(result4.rateLimited).toBe(true);
      });

      it("resets rate limit after 1 minute", async () => {
        const reporter = new ErrorReporter({ maxReportsPerMinute: 2 });

        // Use up the quota
        await reporter.report(mockError);
        await reporter.report(mockError);

        // Should be rate limited
        const limitedResult = await reporter.report(mockError);
        expect(limitedResult.rateLimited).toBe(true);

        // Advance time by 1 minute
        await vi.advanceTimersByTimeAsync(60000);

        // Should be allowed again
        const result = await reporter.report(mockError);
        expect(result.success).toBe(true);
        expect(result.rateLimited).not.toBe(true);
      });
    });

    describe("Enabled/Disabled", () => {
      it("does not send when disabled", async () => {
        let called = false;
        server.use(
          http.post("/api/v1/errors/report", async () => {
            called = true;
            return HttpResponse.json({ success: true });
          }),
        );

        const reporter = new ErrorReporter({ enabled: false });
        const result = await reporter.report(mockError);

        expect(called).toBe(false);
        expect(result.success).toBe(false);
        expect(result.disabled).toBe(true);
      });

      it("can be enabled/disabled at runtime", async () => {
        const reporter = new ErrorReporter({ enabled: true });
        reporter.disable();

        const result = await reporter.report(mockError);
        expect(result.disabled).toBe(true);

        reporter.enable();
        const result2 = await reporter.report(mockError);
        expect(result2.success).toBe(true);
      });

      it("stops batch timer when disabled", async () => {
        const reporter = new ErrorReporter({
          enabled: true,
          batchMode: true,
          batchInterval: 1000,
        });

        // Start triggers the batch timer
        reporter.report(mockError);
        expect(reporter.getQueueSize()).toBe(1);

        // Disable should stop the batch timer
        reporter.disable();

        // Queue reports while disabled
        reporter.report(mockError);

        // Advance time - batch should NOT flush because disabled
        await vi.advanceTimersByTimeAsync(2000);

        // Queue should still have the original item (new ones returned disabled)
        expect(reporter.getQueueSize()).toBe(1);
      });

      it("starts batch timer when enabled with batch mode", async () => {
        let callCount = 0;
        server.use(
          http.post("/api/v1/errors/report/batch", async () => {
            callCount++;
            return HttpResponse.json({ success: true });
          }),
        );

        const reporter = new ErrorReporter({
          enabled: false,
          batchMode: true,
          batchInterval: 1000,
          batchEndpoint: "/api/v1/errors/report/batch",
        });

        // Enable should start the batch timer
        reporter.enable();

        // Queue a report
        reporter.report(mockError);

        // Before interval
        expect(callCount).toBe(0);

        // After interval - should flush
        await vi.advanceTimersByTimeAsync(1000);
        expect(callCount).toBe(1);
      });
    });

    describe("Batch Mode", () => {
      it("queues reports in batch mode", async () => {
        const reporter = new ErrorReporter({
          batchMode: true,
          batchInterval: 1000,
        });

        // Queue reports
        reporter.report(mockError);
        reporter.report(mockError);

        // Check queue size
        expect(reporter.getQueueSize()).toBe(2);
      });

      it("flushes batch on interval", async () => {
        let callCount = 0;
        server.use(
          http.post("/api/v1/errors/report/batch", async () => {
            callCount++;
            return HttpResponse.json({ success: true });
          }),
        );

        const reporter = new ErrorReporter({
          batchMode: true,
          batchInterval: 1000,
          batchEndpoint: "/api/v1/errors/report/batch",
        });

        reporter.report(mockError);
        reporter.report(mockError);

        // Before interval
        expect(callCount).toBe(0);

        // After interval
        await vi.advanceTimersByTimeAsync(1000);

        expect(callCount).toBe(1);
      });

      it("flushes batch on manual flush", async () => {
        let capturedBody: { reports: ErrorReport[] } | null = null;
        server.use(
          http.post("/api/v1/errors/report/batch", async ({ request }) => {
            capturedBody = (await request.json()) as { reports: ErrorReport[] };
            return HttpResponse.json({ success: true });
          }),
        );

        const reporter = new ErrorReporter({
          batchMode: true,
          batchInterval: 10000,
          batchEndpoint: "/api/v1/errors/report/batch",
        });

        reporter.report(mockError);
        reporter.report(mockError);

        await reporter.flush();

        expect(capturedBody?.reports).toHaveLength(2);
        expect(reporter.getQueueSize()).toBe(0);
      });
    });

    describe("Statistics", () => {
      it("tracks report count", async () => {
        const reporter = new ErrorReporter();

        await reporter.report(mockError);
        await reporter.report(mockError);

        const stats = reporter.getStats();
        expect(stats.totalReported).toBe(2);
      });

      it("tracks rate limited count", async () => {
        const reporter = new ErrorReporter({ maxReportsPerMinute: 1 });

        await reporter.report(mockError);
        await reporter.report(mockError);
        await reporter.report(mockError);

        const stats = reporter.getStats();
        expect(stats.rateLimited).toBe(2);
      });

      it("tracks failed count", async () => {
        server.use(
          http.post("/api/v1/errors/report", async () => {
            return new HttpResponse(null, { status: 500 });
          }),
        );

        const reporter = new ErrorReporter();
        await reporter.report(mockError);

        const stats = reporter.getStats();
        expect(stats.failed).toBe(1);
      });
    });
  });
});
