/**
 * ErrorRecoveryPanel Component Tests
 *
 * Sprint 3 - Phase 6.4: AI Error Recovery
 *
 * Tests for the error recovery UI component that displays
 * AI-powered suggestions for error resolution.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../../mocks/server";
import { api } from "../../api";
import { ErrorRecoveryPanel } from "./ErrorRecoveryPanel";

// Backend response format (what RTK Query expects from the API)
interface BackendErrorAnalysisResponse {
  error_type: string;
  recovery_steps: Array<{
    step_number: number;
    title: string;
    description: string;
    action_type: "automatic" | "manual" | "contact_support";
    action_target?: string;
  }>;
  auto_recoverable: boolean;
  suggested_action?: string;
  confidence: number;
}

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

// Mock backend response (matches RTK Query endpoint expected format)
const mockBackendResponse: BackendErrorAnalysisResponse = {
  error_type: "network",
  recovery_steps: [
    {
      step_number: 1,
      title: "Try again",
      description: "Wait a moment and retry the request",
      action_type: "automatic",
    },
    {
      step_number: 2,
      title: "Wait and retry",
      description: "Server is under high load, wait 30 seconds",
      action_type: "automatic",
    },
  ],
  auto_recoverable: true,
  suggested_action: "The server took too long to respond due to high load",
  confidence: 0.92,
};

describe("ErrorRecoveryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    server.use(
      http.post("/api/v1/ai/errors/analyze", async () => {
        await delay(50);
        return HttpResponse.json(mockBackendResponse);
      }),
    );
  });

  afterEach(() => {
    cleanup();
    server.resetHandlers();
  });

  describe("rendering", () => {
    it("renders error message and root cause", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(screen.getByText(/request timeout/i)).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(
          screen.getByText(/server took too long to respond/i),
        ).toBeInTheDocument();
      });
    });

    it("renders all suggestion buttons", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /try again/i }),
        ).toBeInTheDocument();
      });

      expect(
        screen.getByRole("button", { name: /wait and retry/i }),
      ).toBeInTheDocument();
    });

    it("displays loading state while analyzing", async () => {
      server.use(
        http.post("/api/v1/ai/errors/analyze", async () => {
          await delay(500);
          return HttpResponse.json(mockBackendResponse);
        }),
      );

      const error = new Error("Test error");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      expect(screen.getByTestId("error-recovery-loading")).toBeInTheDocument();
    });

    it("displays error classification badge", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(screen.getByText(/network/i)).toBeInTheDocument();
      });
    });
  });

  describe("interactions", () => {
    it("calls onRetry when retry suggestion is clicked", async () => {
      const onRetry = vi.fn();
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} onRetry={onRetry} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /try again/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /try again/i }));
      expect(onRetry).toHaveBeenCalled();
    });

    it("calls onDismiss when dismiss button is clicked", async () => {
      const onDismiss = vi.fn();
      const error = new Error("Request timeout");
      renderWithStore(
        <ErrorRecoveryPanel error={error} onDismiss={onDismiss} />,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /dismiss/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("calls onContact when contact_support suggestion is clicked", async () => {
      // Backend format for an error requiring support contact
      const contactBackendResponse: BackendErrorAnalysisResponse = {
        error_type: "server",
        recovery_steps: [
          {
            step_number: 1,
            title: "Contact support",
            description: "Please reach out to our support team",
            action_type: "contact_support",
          },
        ],
        auto_recoverable: false,
        suggested_action: "Server error requires assistance",
        confidence: 0.95,
      };

      server.use(
        http.post("/api/v1/ai/errors/analyze", async () => {
          return HttpResponse.json(contactBackendResponse);
        }),
      );

      const onContact = vi.fn();
      const error = new Error("Server error");
      renderWithStore(
        <ErrorRecoveryPanel error={error} onContact={onContact} />,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /contact support/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /contact support/i }));
      expect(onContact).toHaveBeenCalled();
    });
  });

  describe("confidence display", () => {
    it("shows confidence when showConfidence is true", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} showConfidence />);

      await waitFor(() => {
        // The hook uses overall confidence (0.92 = 92%) for all suggestions
        // Use getAllByText since there's one confidence badge per suggestion
        const confidenceElements = screen.getAllByText(/92%/);
        expect(confidenceElements.length).toBeGreaterThan(0);
      });
    });

    it("hides confidence by default", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /try again/i }),
        ).toBeInTheDocument();
      });

      expect(screen.queryByText(/92%/)).not.toBeInTheDocument();
    });
  });

  describe("similar issues", () => {
    it("does not display similar issues section when backend provides none", async () => {
      // The RTK Query endpoint doesn't return similar_issues, so the hook sets it to undefined
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} showSimilarIssues />);

      // Wait for analysis to complete
      await waitFor(() => {
        expect(screen.getByText(/try again/i)).toBeInTheDocument();
      });

      // Similar issues section should not appear since backend doesn't provide them
      expect(screen.queryByText(/similar issues/i)).not.toBeInTheDocument();
    });

    it("hides similar issues section when showSimilarIssues is false", async () => {
      const error = new Error("Request timeout");
      renderWithStore(
        <ErrorRecoveryPanel error={error} showSimilarIssues={false} />,
      );

      await waitFor(() => {
        expect(screen.getByText(/try again/i)).toBeInTheDocument();
      });

      expect(screen.queryByText(/similar issues/i)).not.toBeInTheDocument();
    });
  });

  describe("error handling", () => {
    it("displays fallback UI when AI analysis fails", async () => {
      server.use(
        http.post("/api/v1/ai/errors/analyze", async () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const error = new Error("Test error");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(screen.getByText(/test error/i)).toBeInTheDocument();
      });

      // Should show generic retry button as fallback
      expect(
        screen.getByRole("button", { name: /try again/i }),
      ).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has accessible role and labels", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });
    });

    it("buttons have accessible names", async () => {
      const error = new Error("Request timeout");
      renderWithStore(<ErrorRecoveryPanel error={error} />);

      await waitFor(() => {
        const buttons = screen.getAllByRole("button");
        buttons.forEach((button) => {
          expect(button).toHaveAccessibleName();
        });
      });
    });
  });
});
