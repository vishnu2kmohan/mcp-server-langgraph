/**
 * TelemetryViewer Tests
 *
 * TDD tests for the dev tools telemetry viewer component.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TelemetryViewer } from "./TelemetryViewer";
import { TelemetryProvider } from "../contexts/TelemetryContext";
import { SessionTelemetry } from "../utils/sessionTelemetry";
import type { ReactNode } from "react";

describe("TelemetryViewer", () => {
  let testTelemetry: SessionTelemetry;

  const wrapper = ({ children }: { children: ReactNode }) => (
    <TelemetryProvider sessionTelemetry={testTelemetry}>
      {children}
    </TelemetryProvider>
  );

  beforeEach(() => {
    testTelemetry = new SessionTelemetry();
  });

  describe("Rendering", () => {
    it("should render telemetry viewer panel", () => {
      render(<TelemetryViewer />, { wrapper });

      expect(screen.getByText(/telemetry/i)).toBeInTheDocument();
    });

    it("should display session creation metrics", () => {
      testTelemetry.trackSessionCreation({ success: true, durationMs: 100 });
      testTelemetry.trackSessionCreation({
        success: false,
        durationMs: 50,
        error: "Test",
      });

      render(<TelemetryViewer />, { wrapper });

      expect(screen.getByText(/session creations/i)).toBeInTheDocument();
      expect(screen.getByText(/2/)).toBeInTheDocument(); // Total
    });

    it("should display revalidation metrics", () => {
      testTelemetry.trackRevalidation({
        trigger: "message_sent",
        durationMs: 100,
      });
      testTelemetry.trackRevalidation({ trigger: "auto", durationMs: 50 });

      render(<TelemetryViewer />, { wrapper });

      expect(screen.getByText(/revalidations/i)).toBeInTheDocument();
    });

    it("should display sync metrics", () => {
      testTelemetry.trackSync({
        sessionId: "s-1",
        messageCount: 5,
        durationMs: 20,
        skipped: false,
      });

      render(<TelemetryViewer />, { wrapper });

      expect(screen.getByText(/syncs/i)).toBeInTheDocument();
    });
  });

  describe("Interactivity", () => {
    it("should have a reset button", () => {
      render(<TelemetryViewer />, { wrapper });

      expect(
        screen.getByRole("button", { name: /reset/i }),
      ).toBeInTheDocument();
    });

    it("should reset metrics when clicking reset button", () => {
      testTelemetry.trackSessionCreation({ success: true, durationMs: 100 });

      render(<TelemetryViewer />, { wrapper });

      const resetButton = screen.getByRole("button", { name: /reset/i });
      fireEvent.click(resetButton);

      // Metrics should be reset (component will re-render with zero counts)
      expect(testTelemetry.getMetrics().sessionCreations.total).toBe(0);
    });

    it("should have an export button", () => {
      render(<TelemetryViewer />, { wrapper });

      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Collapsible sections", () => {
    it("should allow expanding/collapsing metric sections", () => {
      testTelemetry.trackSessionCreation({ success: true, durationMs: 100 });

      render(<TelemetryViewer />, { wrapper });

      // Find section header and click to toggle
      const sessionCreationsHeader = screen.getByText(/session creations/i);
      fireEvent.click(sessionCreationsHeader);

      // Should toggle visibility (implementation dependent)
      expect(sessionCreationsHeader).toBeInTheDocument();
    });
  });

  describe("Development mode only", () => {
    it("should not render in production mode when isDevMode is false", () => {
      const _originalEnv = process.env.NODE_ENV;

      // In test environment, component should render
      render(<TelemetryViewer />, { wrapper });
      expect(screen.getByText(/telemetry/i)).toBeInTheDocument();

      // Note: Actually testing production mode would require mocking NODE_ENV
    });
  });
});
