/**
 * ErrorRecovery Tests
 *
 * TDD tests for the Error Recovery component.
 * Tests cover:
 * - Error display rendering
 * - Recovery action buttons
 * - Error details expansion
 * - Copy error info
 * - WCAG 2.1 AA accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ErrorRecovery } from "./ErrorRecovery";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

const mockError = {
  code: "ERR_NETWORK_TIMEOUT",
  message: "Request timed out. The server did not respond in time.",
  traceId: "abc123def456",
  timestamp: Date.now(),
};

describe("ErrorRecovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the error message", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByText(mockError.message)).toBeInTheDocument();
    });

    it("should render the error code", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByText(mockError.code)).toBeInTheDocument();
    });

    it("should render error icon", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    });

    it("should render with custom className", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-recovery")).toHaveClass("custom-class");
    });
  });

  // ===========================================================================
  // Recovery Actions Tests
  // ===========================================================================

  describe("recovery actions", () => {
    it("should show retry button when onRetry is provided", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} onRetry={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should call onRetry when retry button is clicked", async () => {
      const onRetry = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} onRetry={onRetry} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /retry/i }));

      expect(onRetry).toHaveBeenCalled();
    });

    it("should show dismiss button when onDismiss is provided", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} onDismiss={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });

    it("should call onDismiss when dismiss button is clicked", async () => {
      const onDismiss = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} onDismiss={onDismiss} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /dismiss/i }));

      expect(onDismiss).toHaveBeenCalled();
    });

    it("should show report button when onReport is provided", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} onReport={() => {}} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /report/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Details Expansion Tests
  // ===========================================================================

  describe("details expansion", () => {
    it("should show expand details button", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /details/i }),
      ).toBeInTheDocument();
    });

    it("should expand details when button is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /details/i }));

      expect(screen.getByText(mockError.traceId)).toBeInTheDocument();
    });

    it("should collapse details when clicked again", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      const detailsButton = screen.getByRole("button", { name: /details/i });
      await user.click(detailsButton);
      await user.click(detailsButton);

      expect(screen.queryByText(mockError.traceId)).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Copy Error Info Tests
  // ===========================================================================

  describe("copy error info", () => {
    it("should show copy button in details", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /details/i }));

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should copy error info to clipboard", async () => {
      const user = userEvent.setup();
      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: mockWriteText },
        writable: true,
        configurable: true,
      });

      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /details/i }));
      await user.click(screen.getByRole("button", { name: /copy/i }));

      expect(mockWriteText).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Severity Levels Tests
  // ===========================================================================

  describe("severity levels", () => {
    it("should show error styling by default", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-recovery")).toHaveAttribute(
        "data-severity",
        "error",
      );
    });

    it("should show warning styling when severity is warning", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} severity="warning" />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-recovery")).toHaveAttribute(
        "data-severity",
        "warning",
      );
    });

    it("should show info styling when severity is info", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} severity="info" />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-recovery")).toHaveAttribute(
        "data-severity",
        "info",
      );
    });
  });

  // ===========================================================================
  // Suggestions Tests
  // ===========================================================================

  describe("suggestions", () => {
    it("should show suggestions when provided", () => {
      const suggestions = [
        "Check your internet connection",
        "Try again in a few minutes",
      ];
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} suggestions={suggestions} />
        </TestProvider>,
      );

      expect(
        screen.getByText("Check your internet connection"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Try again in a few minutes"),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have role alert", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have proper aria-live", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toHaveAttribute(
        "aria-live",
        "assertive",
      );
    });

    it("should have proper heading", () => {
      render(
        <TestProvider>
          <ErrorRecovery error={mockError} />
        </TestProvider>,
      );

      expect(screen.getByRole("heading")).toBeInTheDocument();
    });
  });
});
