/**
 * Error Recovery Integration Tests
 *
 * Tests integration between ErrorBoundary and ErrorRecoveryPanel components.
 */

import React, { useState, type ReactNode } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { http, HttpResponse } from "msw";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ErrorRecoveryPanel } from "../components/ErrorRecovery";
import { server } from "../mocks/server";
import { api } from "../api";

// Create a test store with required reducers
const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

// Render helper that wraps with Redux Provider
const renderWithStore = (ui: ReactNode) => {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

// Component that throws an error
function BuggyComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error: Something went wrong");
  }
  return <div>Working component</div>;
}

// Wrapper component that can trigger recovery (includes Provider)
function RecoverableComponent() {
  const [shouldThrow, setShouldThrow] = useState(true);
  const [resetKey, setResetKey] = useState(0);
  const store = createTestStore();

  return (
    <Provider store={store}>
      <ErrorBoundary
        key={resetKey}
        fallbackRender={({ error }) => (
          <ErrorRecoveryPanel
            error={error}
            onRetry={() => {
              setShouldThrow(false);
              setResetKey((k) => k + 1);
            }}
            testId="error-recovery"
          />
        )}
      >
        <BuggyComponent shouldThrow={shouldThrow} />
      </ErrorBoundary>
    </Provider>
  );
}

describe("Error Recovery Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error for expected errors in tests
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    server.resetHandlers();
    vi.restoreAllMocks();
  });

  describe("ErrorBoundary + ErrorRecoveryPanel", () => {
    it("renders ErrorRecoveryPanel when error caught", async () => {
      renderWithStore(
        <ErrorBoundary
          fallbackRender={({ error, resetErrorBoundary }) => (
            <ErrorRecoveryPanel
              error={error}
              onRetry={resetErrorBoundary}
              testId="error-recovery"
            />
          )}
        >
          <BuggyComponent shouldThrow={true} />
        </ErrorBoundary>,
      );

      // Wait for error panel and loading to complete
      await waitFor(
        () => {
          expect(screen.getByTestId("error-recovery")).toBeInTheDocument();
          expect(
            screen.queryByText(/analyzing error/i),
          ).not.toBeInTheDocument();
        },
        { timeout: 3000 },
      );

      // Should show the error message
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });

    it("shows AI-powered suggestions for the error", async () => {
      renderWithStore(
        <ErrorBoundary
          fallbackRender={({ error, resetErrorBoundary }) => (
            <ErrorRecoveryPanel
              error={error}
              onRetry={resetErrorBoundary}
              testId="error-recovery"
            />
          )}
        >
          <BuggyComponent shouldThrow={true} />
        </ErrorBoundary>,
      );

      // Wait for loading to complete (no longer showing "Analyzing error...")
      await waitFor(
        () => {
          expect(
            screen.queryByText(/analyzing error/i),
          ).not.toBeInTheDocument();
        },
        { timeout: 3000 },
      );

      // Verify there's at least one button for suggestions
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);

      // AI mock returns "Unexpected error" and "Contact support" recovery steps
      // for unknown errors (which "Something went wrong" falls into)
      const suggestionButton = buttons.find(
        (btn) =>
          btn.getAttribute("aria-label") === "Unexpected error" ||
          btn.getAttribute("aria-label") === "Contact support",
      );
      expect(suggestionButton).toBeInTheDocument();
    });

    it("recovers when retry button clicked", async () => {
      // Override handler to return a recoverable error with retry action
      server.use(
        http.post("/api/v1/ai/errors/analyze", () => {
          return HttpResponse.json({
            error_type: "network_timeout",
            recovery_steps: [
              {
                step_number: 1,
                title: "Retry the request",
                description: "Click retry to attempt the operation again.",
                action_type: "automatic", // maps to action: "retry"
              },
            ],
            auto_recoverable: true,
            suggested_action: "retry",
            confidence: 0.92,
          });
        }),
      );

      // Use the RecoverableComponent which handles state properly
      render(<RecoverableComponent />);

      // Wait for loading to complete (no longer showing "Analyzing error...")
      await waitFor(
        () => {
          expect(
            screen.queryByText(/analyzing error/i),
          ).not.toBeInTheDocument();
        },
        { timeout: 3000 },
      );

      // Find and click the retry button
      const retryButton = screen
        .getAllByRole("button")
        .find((btn) => btn.getAttribute("aria-label") === "Retry the request");
      expect(retryButton).toBeInTheDocument();

      // Click retry - this triggers state change and ErrorBoundary remount
      fireEvent.click(retryButton!);

      // Should now show working component
      await waitFor(() => {
        expect(screen.getByText("Working component")).toBeInTheDocument();
      });
    });
  });

  describe("ErrorRecoveryPanel standalone", () => {
    it("analyzes error and shows classification", async () => {
      const error = new Error("Session expired");
      error.name = "AuthenticationError";

      renderWithStore(<ErrorRecoveryPanel error={error} testId="recovery" />);

      // Wait for analysis
      await waitFor(
        () => {
          expect(screen.queryByText(/analyzing/i)).not.toBeInTheDocument();
        },
        { timeout: 2000 },
      );

      // Should show the error in the title
      expect(
        screen.getByRole("heading", { name: /session expired/i }),
      ).toBeInTheDocument();
    });
  });
});
