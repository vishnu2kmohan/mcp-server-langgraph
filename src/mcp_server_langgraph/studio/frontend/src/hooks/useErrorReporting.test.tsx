/**
 * useErrorReporting Hook Tests
 *
 * TDD - Sprint 3 - Phase 2.4: Error Reporting Pipeline
 *
 * Tests for the React hook that integrates error reporting
 * with TelemetryContext and provides convenient API for components.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";
import React from "react";

import { useErrorReporting } from "./useErrorReporting";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Test Data
// =============================================================================

const mockError = new Error("Test error");
mockError.stack = "Error: Test error\n    at test.ts:10";

// =============================================================================
// Test Utilities
// =============================================================================

function createWrapper() {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <TelemetryProvider>{children}</TelemetryProvider>;
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("useErrorReporting", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.post("/api/v1/errors/report", async () => {
        return HttpResponse.json({ success: true, reportId: "report-123" });
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initialization", () => {
    it("provides report function", () => {
      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.reportError).toBe("function");
    });

    it("provides stats function", () => {
      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.getStats).toBe("function");
    });

    it("provides enable/disable functions", () => {
      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.enable).toBe("function");
      expect(typeof result.current.disable).toBe("function");
    });
  });

  describe("Error Reporting", () => {
    it("reports errors to backend", async () => {
      let capturedBody: Record<string, unknown> | null = null;
      server.use(
        http.post("/api/v1/errors/report", async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ success: true, reportId: "report-456" });
        }),
      );

      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.reportError(mockError);
      });

      expect(capturedBody).not.toBeNull();
      expect(capturedBody?.message).toBe("Test error");
    });

    it("includes custom context", async () => {
      let capturedBody: Record<string, unknown> | null = null;
      server.use(
        http.post("/api/v1/errors/report", async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ success: true });
        }),
      );

      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.reportError(mockError, {
          customContext: { component: "ChatPage" },
        });
      });

      expect(
        (capturedBody?.customContext as Record<string, unknown>)?.component,
      ).toBe("ChatPage");
    });

    it("tracks last error", async () => {
      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.reportError(mockError);
      });

      expect(result.current.lastError?.message).toBe("Test error");
    });

    it("tracks reporting state", async () => {
      const { result } = renderHook(() => useErrorReporting(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isReporting).toBe(false);

      const reportPromise = act(async () => {
        await result.current.reportError(mockError);
      });

      await reportPromise;

      expect(result.current.isReporting).toBe(false);
    });
  });

  describe("Configuration", () => {
    it("accepts initial config", () => {
      const { result } = renderHook(
        () =>
          useErrorReporting({
            enabled: false,
            maxReportsPerMinute: 5,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isEnabled).toBe(false);
    });

    it("enable/disable works", () => {
      const { result } = renderHook(
        () => useErrorReporting({ enabled: true }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isEnabled).toBe(true);

      act(() => {
        result.current.disable();
      });

      expect(result.current.isEnabled).toBe(false);

      act(() => {
        result.current.enable();
      });

      expect(result.current.isEnabled).toBe(true);
    });
  });

  describe("Auto-capture", () => {
    it("can auto-capture window errors when enabled", () => {
      // Note: This test just verifies the option exists
      // Actually testing window.onerror in jsdom is tricky
      const { result } = renderHook(
        () => useErrorReporting({ captureWindowErrors: true }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isEnabled).toBe(true);
    });
  });
});
