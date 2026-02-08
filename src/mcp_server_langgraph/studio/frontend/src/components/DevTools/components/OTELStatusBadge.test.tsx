/**
 * OTELStatusBadge Component Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests status badge variants for logs, alerts, spans, HTTP status/methods.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { OTELStatusBadge } from "./OTELStatusBadge";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Helper for class matching (matches partial class names)
// =============================================================================

/**
 * Check if element has a class that starts with the given prefix
 */
function hasClassStartingWith(element: HTMLElement, prefix: string): boolean {
  const classes = element.className.split(" ");
  return classes.some((cls) => cls.startsWith(prefix));
}

// =============================================================================
// Log Level Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OTELStatusBadge", () => {
  describe("log-level type", () => {
    it("should render debug level with neutral styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="debug" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("DEBUG");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should render info level with primary styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="info" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("INFO");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render warning level with warning styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="warning" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("WARN");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render error level with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="error" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("ERROR");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should show icon by default for log levels", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="error" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      // Icon should be present (aria-hidden)
      expect(badge.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
    });

    it("should hide icon when showIcon is false", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="error" showIcon={false} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(
        badge.querySelector('[aria-hidden="true"]'),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Alert State Tests
  // ===========================================================================

  describe("alert-state type", () => {
    it("should render firing state with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-state" value="firing" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("FIRING");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render pending state with warning styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-state" value="pending" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PENDING");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render resolved state with success styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-state" value="resolved" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("RESOLVED");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render silenced state with neutral styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-state" value="silenced" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("SILENCED");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });
  });

  // ===========================================================================
  // Alert Severity Tests
  // ===========================================================================

  describe("alert-severity type", () => {
    it("should render critical severity with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-severity" value="critical" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("CRITICAL");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render warning severity with warning styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-severity" value="warning" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("WARNING");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render info severity with primary styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-severity" value="info" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("INFO");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });
  });

  // ===========================================================================
  // Span Status Tests
  // ===========================================================================

  describe("span-status type", () => {
    it("should render ok status with success styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="span-status" value="ok" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("OK");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render error status with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="span-status" value="error" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("ERROR");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render unset status with neutral styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="span-status" value="unset" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("UNSET");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });
  });

  // ===========================================================================
  // HTTP Status Tests
  // ===========================================================================

  describe("http-status type", () => {
    it("should render 2xx status with success styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={200} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("200");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render 201 with success styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={201} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("201");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render 3xx status with info styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={301} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("301");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render 4xx status with warning styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={404} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("404");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render 5xx status with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={500} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("500");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render 503 with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={503} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("503");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });
  });

  // ===========================================================================
  // HTTP Method Tests
  // ===========================================================================

  describe("http-method type", () => {
    it("should render GET with success styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="GET" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("GET");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render POST with primary styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="POST" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("POST");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render PUT with warning styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="PUT" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PUT");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render DELETE with error styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="DELETE" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("DELETE");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render PATCH with insight styling", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="PATCH" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PATCH");
      expect(hasClassStartingWith(badge, "bg-insight")).toBe(true);
    });

    it("should handle lowercase method input", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="get" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("GET");
    });
  });

  // ===========================================================================
  // Size Variant Tests
  // ===========================================================================

  describe("size variants", () => {
    it("should render sm size with correct classes", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="info" size="sm" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveClass("text-xs");
    });

    it("should render sm size by default", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="info" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      // Default is "sm" in CVA
      expect(badge).toHaveClass("text-xs");
    });

    it("should render md size when specified", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="info" size="md" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveClass("text-sm");
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have role=status for screen readers", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="error" />
        </TestProvider>,
      );
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should have accessible label describing the status", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="error" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveAttribute("aria-label", "Log level: error");
    });

    it("should have accessible label for HTTP status", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={404} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveAttribute("aria-label", "HTTP status: 404");
    });

    it("should have accessible label for alert state", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="alert-state" value="firing" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveAttribute("aria-label", "Alert state: firing");
    });
  });

  // ===========================================================================
  // Custom className Tests
  // ===========================================================================

  describe("className prop", () => {
    it("should merge custom className with default styles", () => {
      render(
        <TestProvider>
          <OTELStatusBadge
            type="log-level"
            value="info"
            className="custom-class"
          />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveClass("custom-class");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("edge cases", () => {
    it("should handle unknown log level gracefully", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="log-level" value="unknown" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("UNKNOWN");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should handle unknown HTTP method gracefully", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-method" value="OPTIONS" />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("OPTIONS");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should handle undefined status code gracefully", () => {
      render(
        <TestProvider>
          <OTELStatusBadge type="http-status" value={0} />
        </TestProvider>,
      );
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("0");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });
  });
});
