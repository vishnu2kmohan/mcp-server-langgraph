/**
 * TelemetryContext Tests
 *
 * TDD tests for injectable telemetry via React context.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import {
  TelemetryProvider,
  useTelemetry,
  useSessionTelemetry,
  useWebVitals,
} from "./TelemetryContext";
import { SessionTelemetry } from "../utils/sessionTelemetry";
import { WebVitalsTracker } from "../utils/webVitals";
import type { ReactNode } from "react";

describe("TelemetryContext", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("TelemetryProvider", () => {
    it("should provide default session telemetry instance", () => {
      const { result } = renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider>{children}</TelemetryProvider>
        ),
      });

      expect(result.current.sessionTelemetry).toBeDefined();
      expect(result.current.sessionTelemetry).toBeInstanceOf(SessionTelemetry);
    });

    it("should allow custom telemetry instance injection", () => {
      const customTelemetry = new SessionTelemetry({ debug: true });

      const { result } = renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider sessionTelemetry={customTelemetry}>
            {children}
          </TelemetryProvider>
        ),
      });

      expect(result.current.sessionTelemetry).toBe(customTelemetry);
    });
  });

  describe("useSessionTelemetry", () => {
    it("should return session telemetry from context", () => {
      const { result } = renderHook(() => useSessionTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider>{children}</TelemetryProvider>
        ),
      });

      expect(result.current).toBeInstanceOf(SessionTelemetry);
    });

    it("should track events on injected instance", () => {
      const mockTelemetry = new SessionTelemetry();
      const trackSpy = vi.spyOn(mockTelemetry, "trackSessionCreation");

      const { result } = renderHook(() => useSessionTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider sessionTelemetry={mockTelemetry}>
            {children}
          </TelemetryProvider>
        ),
      });

      act(() => {
        result.current.trackSessionCreation({
          sessionId: "test-123",
          success: true,
          durationMs: 100,
        });
      });

      expect(trackSpy).toHaveBeenCalledWith({
        sessionId: "test-123",
        success: true,
        durationMs: 100,
      });
    });
  });

  describe("Testing utilities", () => {
    it("should allow creating mock telemetry for tests", () => {
      // Create a fresh instance for each test
      const testTelemetry = new SessionTelemetry();

      const { result } = renderHook(() => useSessionTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider sessionTelemetry={testTelemetry}>
            {children}
          </TelemetryProvider>
        ),
      });

      // Track some events
      result.current.trackSessionCreation({ success: true, durationMs: 50 });
      result.current.trackSessionCreation({
        success: false,
        durationMs: 10,
        error: "Test error",
      });

      // Verify metrics
      const metrics = testTelemetry.getMetrics();
      expect(metrics.sessionCreations.total).toBe(2);
      expect(metrics.sessionCreations.successful).toBe(1);
      expect(metrics.sessionCreations.failed).toBe(1);
    });
  });

  describe("useWebVitals", () => {
    it("should return WebVitalsTracker from context", () => {
      const { result } = renderHook(() => useWebVitals(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider>{children}</TelemetryProvider>
        ),
      });

      expect(result.current).toBeInstanceOf(WebVitalsTracker);
    });

    it("should allow custom WebVitalsTracker injection", () => {
      const customTracker = new WebVitalsTracker({ debug: true });

      const { result } = renderHook(() => useWebVitals(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider webVitals={customTracker}>
            {children}
          </TelemetryProvider>
        ),
      });

      expect(result.current).toBe(customTracker);
    });

    it("should get metrics from webVitals", () => {
      const { result } = renderHook(() => useWebVitals(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider>{children}</TelemetryProvider>
        ),
      });

      const metrics = result.current.getMetrics();
      expect(metrics).toHaveProperty("fcp");
      expect(metrics).toHaveProperty("lcp");
      expect(metrics).toHaveProperty("cls");
      expect(metrics).toHaveProperty("inp");
    });
  });

  describe("useTelemetry extended", () => {
    it("should include webVitals in context value", () => {
      const { result } = renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider>{children}</TelemetryProvider>
        ),
      });

      expect(result.current.webVitals).toBeDefined();
      expect(result.current.webVitals).toBeInstanceOf(WebVitalsTracker);
    });

    it("should provide both session telemetry and webVitals", () => {
      const customSession = new SessionTelemetry();
      const customWebVitals = new WebVitalsTracker();

      const { result } = renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider
            sessionTelemetry={customSession}
            webVitals={customWebVitals}
          >
            {children}
          </TelemetryProvider>
        ),
      });

      expect(result.current.sessionTelemetry).toBe(customSession);
      expect(result.current.webVitals).toBe(customWebVitals);
    });
  });

  describe("Auto-start behavior", () => {
    it("should auto-start webVitals tracking by default", () => {
      const mockTracker = new WebVitalsTracker();
      const startSpy = vi.spyOn(mockTracker, "start");

      renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider webVitals={mockTracker} autoStartWebVitals>
            {children}
          </TelemetryProvider>
        ),
      });

      expect(startSpy).toHaveBeenCalled();
    });

    it("should not auto-start when autoStartWebVitals is false", () => {
      const mockTracker = new WebVitalsTracker();
      const startSpy = vi.spyOn(mockTracker, "start");

      renderHook(() => useTelemetry(), {
        wrapper: ({ children }: { children: ReactNode }) => (
          <TelemetryProvider webVitals={mockTracker} autoStartWebVitals={false}>
            {children}
          </TelemetryProvider>
        ),
      });

      expect(startSpy).not.toHaveBeenCalled();
    });
  });
});
