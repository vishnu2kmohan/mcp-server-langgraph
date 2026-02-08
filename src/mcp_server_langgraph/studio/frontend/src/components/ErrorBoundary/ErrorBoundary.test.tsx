/**
 * ErrorBoundary Tests
 *
 * Tests for global error boundary with telemetry integration:
 * - Error catching and display
 * - Telemetry tracking of errors
 * - Recovery actions
 * - Accessibility
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { ErrorBoundary, type ErrorInfo } from "./ErrorBoundary";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

// Component that throws an error
const ThrowingComponent = ({ error }: { error?: Error }) => {
  if (error) {
    throw error;
  }
  return <div data-testid="child-content">Child Content</div>;
};

// Suppress console.error during error boundary tests
const originalConsoleError = console.error;

describe("ErrorBoundary", () => {
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    cleanup();
    console.error = originalConsoleError;
    vi.clearAllMocks();
  });

  describe("Normal Rendering", () => {
    it("should render children when no error occurs", () => {
      render(
        <TestProvider>
          <ErrorBoundary>
            <div data-testid="test-child">Test Child</div>
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByTestId("test-child")).toBeInTheDocument();
    });

    it("should render multiple children", () => {
      render(
        <TestProvider>
          <ErrorBoundary>
            <div data-testid="child-1">Child 1</div>
            <div data-testid="child-2">Child 2</div>
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByTestId("child-1")).toBeInTheDocument();
      expect(screen.getByTestId("child-2")).toBeInTheDocument();
    });
  });

  describe("Error Catching", () => {
    it("should catch errors from children and display fallback UI", () => {
      const testError = new Error("Test error message");

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.queryByTestId("child-content")).not.toBeInTheDocument();
    });

    it("should display error message in fallback UI", () => {
      const testError = new Error("Custom error message for testing");

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(
        screen.getByText(/custom error message for testing/i),
      ).toBeInTheDocument();
    });

    it("should display generic message for errors without message", () => {
      const testError = new Error();

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(
        screen.getByText(/an unexpected error occurred/i),
      ).toBeInTheDocument();
    });
  });

  describe("Telemetry Integration", () => {
    it("should call onError callback when error is caught", () => {
      const onError = vi.fn();
      const testError = new Error("Test error");

      render(
        <TestProvider>
          <ErrorBoundary onError={onError}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledWith(
        testError,
        expect.objectContaining({
          componentStack: expect.any(String),
        }),
      );
    });

    it("should include component stack in error info", () => {
      const onError = vi.fn();
      const testError = new Error("Stack trace test");

      render(
        <TestProvider>
          <ErrorBoundary onError={onError}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      const errorInfo = onError.mock.calls[0][1] as ErrorInfo;
      expect(errorInfo.componentStack).toBeDefined();
      expect(typeof errorInfo.componentStack).toBe("string");
    });

    it("should handle onError callback that throws", () => {
      const onError = vi.fn().mockImplementation(() => {
        throw new Error("Callback error");
      });
      const testError = new Error("Original error");

      // Should not throw - error boundary should handle this gracefully
      expect(() =>
        render(
          <TestProvider>
            <ErrorBoundary onError={onError}>
              <ThrowingComponent error={testError} />
            </ErrorBoundary>
          </TestProvider>,
        ),
      ).not.toThrow();

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("Recovery Actions", () => {
    it("should display retry button by default", () => {
      const testError = new Error("Retry test");

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /try again/i }),
      ).toBeInTheDocument();
    });

    it("should call onReset when retry button is clicked", () => {
      const onReset = vi.fn();
      const testError = new Error("Reset test");

      render(
        <TestProvider>
          <ErrorBoundary onReset={onReset}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /try again/i }));

      expect(onReset).toHaveBeenCalledTimes(1);
    });

    it("should reset error state when retry is clicked", () => {
      let shouldThrow = true;
      const ToggleComponent = () => {
        if (shouldThrow) {
          throw new Error("Toggle error");
        }
        return <div data-testid="recovered">Recovered!</div>;
      };

      const { rerender } = render(
        <TestProvider>
          <ErrorBoundary>
            <ToggleComponent />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();

      // Fix the error condition
      shouldThrow = false;

      // Click retry
      fireEvent.click(screen.getByRole("button", { name: /try again/i }));

      // Re-render to trigger state update
      rerender(
        <ErrorBoundary>
          <ToggleComponent />
        </ErrorBoundary>,
      );

      // Error boundary should have reset
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  describe("Custom Fallback", () => {
    it("should render custom fallback component", () => {
      const CustomFallback = () => (
        <div data-testid="custom-fallback">Custom Error UI</div>
      );
      const testError = new Error("Custom fallback test");

      render(
        <TestProvider>
          <ErrorBoundary fallback={<CustomFallback />}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    });

    it("should render fallback render prop with error details", () => {
      const fallbackRender = vi
        .fn()
        .mockReturnValue(
          <div data-testid="render-fallback">Render Fallback</div>,
        );
      const testError = new Error("Render prop test");

      render(
        <TestProvider>
          <ErrorBoundary fallbackRender={fallbackRender}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(fallbackRender).toHaveBeenCalledWith({
        error: testError,
        resetErrorBoundary: expect.any(Function),
      });
      expect(screen.getByTestId("render-fallback")).toBeInTheDocument();
    });
  });

  describe("Error Details", () => {
    it("should show error details when showDetails is true", () => {
      const testError = new Error("Detailed error");
      testError.stack = "Error: Detailed error\n    at test.js:1:1";

      render(
        <TestProvider>
          <ErrorBoundary showDetails>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByText(/error:/i)).toBeInTheDocument();
    });

    it("should hide error details by default in production", () => {
      const testError = new Error("Hidden error");
      testError.stack = "Error stack trace";

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      // Stack trace should not be visible by default
      expect(screen.queryByText(/error stack trace/i)).not.toBeInTheDocument();
    });
  });

  describe("Boundary Identification", () => {
    it("should include boundary name in error info when provided", () => {
      const onError = vi.fn();
      const testError = new Error("Named boundary test");

      render(
        <TestProvider>
          <ErrorBoundary name="TestBoundary" onError={onError}>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      const errorInfo = onError.mock.calls[0][1] as ErrorInfo;
      expect(errorInfo.boundaryName).toBe("TestBoundary");
    });
  });

  describe("Accessibility (WCAG 2.1 AA)", () => {
    it("should have no accessibility violations in error state", async () => {
      const testError = new Error("A11y test error");

      const { container } = render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper ARIA attributes on error UI", () => {
      const testError = new Error("ARIA test");

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "assertive");
    });

    it("should have focusable retry button for keyboard users", () => {
      const testError = new Error("Focus test");

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      const retryButton = screen.getByRole("button", { name: /try again/i });
      // Button should be focusable (has proper tabindex or is naturally focusable)
      expect(retryButton).toHaveAttribute("type", "button");
      retryButton.focus();
      expect(document.activeElement).toBe(retryButton);
    });
  });

  describe("Edge Cases", () => {
    it("should handle null error message", () => {
      const testError = new Error();
      testError.message = null as unknown as string;

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowingComponent error={testError} />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should handle non-Error objects thrown", () => {
      const ThrowStringComponent = () => {
        throw "String error";
      };

      render(
        <TestProvider>
          <ErrorBoundary>
            <ThrowStringComponent />
          </ErrorBoundary>
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should allow recovery after error is fixed", () => {
      // Test that ErrorBoundary can recover when the underlying issue is resolved
      const testError = new Error("Recoverable error");
      let shouldError = true;

      const ConditionalComponent = () => {
        if (shouldError) {
          throw testError;
        }
        return <div data-testid="success">Success</div>;
      };

      const { rerender } = render(
        <TestProvider>
          <ErrorBoundary>
            <ConditionalComponent />
          </ErrorBoundary>
        </TestProvider>,
      );

      // First render - should catch error
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.queryByTestId("success")).not.toBeInTheDocument();

      // Fix the underlying issue
      shouldError = false;

      // Click reset
      fireEvent.click(screen.getByRole("button", { name: /try again/i }));

      // Rerender to apply state change
      rerender(
        <ErrorBoundary>
          <ConditionalComponent />
        </ErrorBoundary>,
      );

      // Should now render successfully
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByTestId("success")).toBeInTheDocument();
    });
  });
});
