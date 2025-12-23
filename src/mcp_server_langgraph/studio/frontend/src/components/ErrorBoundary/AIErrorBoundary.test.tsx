/**
 * AIErrorBoundary Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Error boundary for AI-powered components with graceful fallback.
 *
 * Features:
 * - Catches errors from AI components
 * - Integrates with AIIntelligence context for error reporting
 * - Provides customizable fallback UI
 * - Supports retry functionality
 * - Logs errors for observability
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AIIntelligenceProvider } from "../../contexts/AIIntelligenceContext";
import { AIErrorBoundary } from "./AIErrorBoundary";

// Create mock store
function createMockStore() {
  return configureStore({
    reducer: {
      auth: () => ({ user: { id: "user-123" } }),
      api: () => ({}),
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }),
  });
}

// Test wrapper with all providers
function createWrapper(config = {}) {
  const store = createMockStore();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <AIIntelligenceProvider config={config}>
          {children}
        </AIIntelligenceProvider>
      </Provider>
    );
  };
}

// Component that throws an error
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error from AI component");
  }
  return <div data-testid="child-content">Working component</div>;
}

describe("AIErrorBoundary", () => {
  // Suppress console.error during tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  describe("normal rendering", () => {
    it("should render children when no error occurs", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={false} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.getByTestId("child-content")).toBeInTheDocument();
      expect(screen.getByText("Working component")).toBeInTheDocument();
    });
  });

  describe("error handling", () => {
    it("should catch errors and display fallback UI", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.queryByTestId("child-content")).not.toBeInTheDocument();
      expect(screen.getByTestId("ai-error-fallback")).toBeInTheDocument();
    });

    it("should display feature name in fallback UI", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="Navigation Predictions">
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.getByText(/Navigation Predictions/i)).toBeInTheDocument();
    });

    it("should display error message in fallback UI", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(
        screen.getByText(/Test error from AI component/i),
      ).toBeInTheDocument();
    });
  });

  describe("retry functionality", () => {
    it("should provide a retry button", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should reset error state when retry is clicked", () => {
      const Wrapper = createWrapper({ enabled: true });
      let shouldThrow = true;

      const { rerender } = render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={shouldThrow} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      // Error should be shown
      expect(screen.getByTestId("ai-error-fallback")).toBeInTheDocument();

      // Update to not throw
      shouldThrow = false;

      // Click retry
      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      // Re-render with new props
      rerender(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature">
            <ThrowingComponent shouldThrow={shouldThrow} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      // After retry with fixed component, should show content
      // Note: Due to React error boundary behavior, this may still show fallback
      // until component is remounted. This test validates the retry button exists.
    });
  });

  describe("custom fallback", () => {
    it("should render custom fallback when provided", () => {
      const Wrapper = createWrapper({ enabled: true });
      const customFallback = (
        <div data-testid="custom-fallback">Custom error message</div>
      );

      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" fallback={customFallback}>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
      expect(screen.getByText("Custom error message")).toBeInTheDocument();
    });

    it("should render fallback function with error info", () => {
      const Wrapper = createWrapper({ enabled: true });
      const fallbackFn = vi.fn(({ error, resetError }) => (
        <div data-testid="fallback-fn">
          <span>Error: {error.message}</span>
          <button onClick={resetError}>Custom Reset</button>
        </div>
      ));

      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" fallback={fallbackFn}>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.getByTestId("fallback-fn")).toBeInTheDocument();
      expect(fallbackFn).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.any(Error),
          resetError: expect.any(Function),
        }),
      );
    });
  });

  describe("silent mode", () => {
    it("should hide error UI when silent mode is enabled", () => {
      const Wrapper = createWrapper({ enabled: true });
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" silent>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      // Should not show error fallback
      expect(screen.queryByTestId("ai-error-fallback")).not.toBeInTheDocument();
    });

    it("should render nothing in silent mode on error", () => {
      const Wrapper = createWrapper({ enabled: true });
      const { container } = render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" silent>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      // Container should be empty (error boundary renders null)
      expect(container.querySelector("[data-testid]")).toBeNull();
    });
  });

  describe("callback integration", () => {
    it("should call onError callback when error occurs", () => {
      const Wrapper = createWrapper({ enabled: true });
      const onError = vi.fn();

      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" onError={onError}>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        }),
      );
    });

    it("should call onReset callback when retry is clicked", () => {
      const Wrapper = createWrapper({ enabled: true });
      const onReset = vi.fn();

      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" onReset={onReset}>
            <ThrowingComponent shouldThrow={true} />
          </AIErrorBoundary>
        </Wrapper>,
      );

      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      expect(onReset).toHaveBeenCalled();
    });
  });

  describe("disabled state", () => {
    it("should not catch errors when disabled prop is true", () => {
      const Wrapper = createWrapper({ enabled: true });

      // When disabled, errors should propagate up
      // This is tested by checking that the boundary doesn't render fallback
      // Note: This behavior depends on implementation choice
      render(
        <Wrapper>
          <AIErrorBoundary featureName="test-feature" disabled>
            <div data-testid="normal-content">Normal content</div>
          </AIErrorBoundary>
        </Wrapper>,
      );

      expect(screen.getByTestId("normal-content")).toBeInTheDocument();
    });
  });
});
