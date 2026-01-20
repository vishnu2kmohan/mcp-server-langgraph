/**
 * OTELStatusBadge Component Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests status badge variants for logs, alerts, spans, HTTP status/methods.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { OTELStatusBadge } from "./OTELStatusBadge";

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

describe("OTELStatusBadge", () => {
  describe("log-level type", () => {
    it("should render debug level with neutral styling", () => {
      render(<OTELStatusBadge type="log-level" value="debug" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("DEBUG");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should render info level with primary styling", () => {
      render(<OTELStatusBadge type="log-level" value="info" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("INFO");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render warning level with warning styling", () => {
      render(<OTELStatusBadge type="log-level" value="warning" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("WARN");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render error level with error styling", () => {
      render(<OTELStatusBadge type="log-level" value="error" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("ERROR");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should show icon by default for log levels", () => {
      render(<OTELStatusBadge type="log-level" value="error" />);
      const badge = screen.getByRole("status");
      // Icon should be present (aria-hidden)
      expect(badge.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
    });

    it("should hide icon when showIcon is false", () => {
      render(<OTELStatusBadge type="log-level" value="error" showIcon={false} />);
      const badge = screen.getByRole("status");
      expect(badge.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Alert State Tests
  // ===========================================================================

  describe("alert-state type", () => {
    it("should render firing state with error styling", () => {
      render(<OTELStatusBadge type="alert-state" value="firing" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("FIRING");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render pending state with warning styling", () => {
      render(<OTELStatusBadge type="alert-state" value="pending" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PENDING");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render resolved state with success styling", () => {
      render(<OTELStatusBadge type="alert-state" value="resolved" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("RESOLVED");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render silenced state with neutral styling", () => {
      render(<OTELStatusBadge type="alert-state" value="silenced" />);
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
      render(<OTELStatusBadge type="alert-severity" value="critical" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("CRITICAL");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render warning severity with warning styling", () => {
      render(<OTELStatusBadge type="alert-severity" value="warning" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("WARNING");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render info severity with primary styling", () => {
      render(<OTELStatusBadge type="alert-severity" value="info" />);
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
      render(<OTELStatusBadge type="span-status" value="ok" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("OK");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render error status with error styling", () => {
      render(<OTELStatusBadge type="span-status" value="error" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("ERROR");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render unset status with neutral styling", () => {
      render(<OTELStatusBadge type="span-status" value="unset" />);
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
      render(<OTELStatusBadge type="http-status" value={200} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("200");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render 201 with success styling", () => {
      render(<OTELStatusBadge type="http-status" value={201} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("201");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render 3xx status with info styling", () => {
      render(<OTELStatusBadge type="http-status" value={301} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("301");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render 4xx status with warning styling", () => {
      render(<OTELStatusBadge type="http-status" value={404} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("404");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render 5xx status with error styling", () => {
      render(<OTELStatusBadge type="http-status" value={500} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("500");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render 503 with error styling", () => {
      render(<OTELStatusBadge type="http-status" value={503} />);
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
      render(<OTELStatusBadge type="http-method" value="GET" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("GET");
      expect(hasClassStartingWith(badge, "bg-success")).toBe(true);
    });

    it("should render POST with primary styling", () => {
      render(<OTELStatusBadge type="http-method" value="POST" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("POST");
      expect(hasClassStartingWith(badge, "bg-primary")).toBe(true);
    });

    it("should render PUT with warning styling", () => {
      render(<OTELStatusBadge type="http-method" value="PUT" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PUT");
      expect(hasClassStartingWith(badge, "bg-warning")).toBe(true);
    });

    it("should render DELETE with error styling", () => {
      render(<OTELStatusBadge type="http-method" value="DELETE" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("DELETE");
      expect(hasClassStartingWith(badge, "bg-error")).toBe(true);
    });

    it("should render PATCH with insight styling", () => {
      render(<OTELStatusBadge type="http-method" value="PATCH" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("PATCH");
      expect(hasClassStartingWith(badge, "bg-insight")).toBe(true);
    });

    it("should handle lowercase method input", () => {
      render(<OTELStatusBadge type="http-method" value="get" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("GET");
    });
  });

  // ===========================================================================
  // Size Variant Tests
  // ===========================================================================

  describe("size variants", () => {
    it("should render sm size with correct classes", () => {
      render(<OTELStatusBadge type="log-level" value="info" size="sm" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveClass("text-xs");
    });

    it("should render sm size by default", () => {
      render(<OTELStatusBadge type="log-level" value="info" />);
      const badge = screen.getByRole("status");
      // Default is "sm" in CVA
      expect(badge).toHaveClass("text-xs");
    });

    it("should render md size when specified", () => {
      render(<OTELStatusBadge type="log-level" value="info" size="md" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveClass("text-sm");
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have role=status for screen readers", () => {
      render(<OTELStatusBadge type="log-level" value="error" />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should have accessible label describing the status", () => {
      render(<OTELStatusBadge type="log-level" value="error" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveAttribute("aria-label", "Log level: error");
    });

    it("should have accessible label for HTTP status", () => {
      render(<OTELStatusBadge type="http-status" value={404} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveAttribute("aria-label", "HTTP status: 404");
    });

    it("should have accessible label for alert state", () => {
      render(<OTELStatusBadge type="alert-state" value="firing" />);
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
        <OTELStatusBadge
          type="log-level"
          value="info"
          className="custom-class"
        />,
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
      render(<OTELStatusBadge type="log-level" value="unknown" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("UNKNOWN");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should handle unknown HTTP method gracefully", () => {
      render(<OTELStatusBadge type="http-method" value="OPTIONS" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("OPTIONS");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });

    it("should handle undefined status code gracefully", () => {
      render(<OTELStatusBadge type="http-status" value={0} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("0");
      expect(hasClassStartingWith(badge, "bg-neutral")).toBe(true);
    });
  });
});
