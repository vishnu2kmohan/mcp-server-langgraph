/**
 * AIEmptyState Component Tests
 *
 * Tests for the AI-enhanced empty state component that integrates
 * useAIEmptyState hook with the base EmptyState component.
 *
 * Phase 6.2: AI-Native Integration Layer
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../../mocks/server";
import { AIEmptyState } from "./AIEmptyState";
import personaReducer from "../../store/slices/personaSlice";
import sessionReducer from "../../store/slices/sessionSlice";
import { api } from "../../api";

const AI_ENDPOINT = "/api/v1/ai/empty-state/suggestions";

// Create wrapper with Redux store including RTK Query API
function createWrapper(personaState = {}, sessionState = {}) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
      session: sessionReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      persona: {
        persona: "developer" as const,
        subPersona: "alice-builder" as const,
        username: "alice",
        email: "alice@example.com",
        permissions: [],
        isPersonaLoading: false,
        ...personaState,
      },
      session: {
        sessions: [],
        currentSession: { id: "test-session-123", messages: [] },
        isLoadingSessions: false,
        isLoadingSession: false,
        isSending: false,
        error: null,
        hasMore: false,
        totalCount: 0,
        isLoadingMore: false,
        cursor: null,
        hasPendingMutation: false,
        ...sessionState,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

describe("AIEmptyState", () => {
  beforeEach(() => {
    // Default success response - uses RTK Query API schema
    // API returns: title, description, action_type, action_target, priority, icon?
    // Hook transforms to: text, action, target, confidence, category
    server.use(
      http.post(AI_ENDPOINT, () => {
        return HttpResponse.json({
          suggestions: [
            {
              title: "AI suggested action",
              description: "Try this AI suggested action",
              action_type: "navigate",
              action_target: "/ai-suggested-path",
              priority: 1, // priority 1 → confidence 1.0
              icon: "arrow-right",
            },
          ],
        });
      }),
    );
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("rendering", () => {
    it("should render empty state with context", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" />
        </Wrapper>,
      );

      // Should render empty state
      expect(screen.getByTestId("empty-state-workflows")).toBeInTheDocument();
    });

    it("should show loading state initially", async () => {
      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delay("infinite");
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="sessions" />
        </Wrapper>,
      );

      // Should show loading indicator
      expect(screen.getByTestId("empty-state-loading")).toBeInTheDocument();
    });

    it("should show AI suggestion when loaded", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(screen.getByText("AI suggested action")).toBeInTheDocument();
      });
    });
  });

  describe("fallback behavior", () => {
    it("should show fallback content when AI fails", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.error();
        }),
      );

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="sessions" />
        </Wrapper>,
      );

      await waitFor(() => {
        // Should show fallback from registry
        expect(screen.getByTestId("empty-state-sessions")).toBeInTheDocument();
      });
    });

    it("should render fallback trigger when AI unavailable", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return new HttpResponse(null, { status: 503 });
        }),
      );

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" />
        </Wrapper>,
      );

      await waitFor(() => {
        // Should show fallback action from registry
        expect(screen.getByRole("button")).toBeInTheDocument();
      });
    });
  });

  describe("AI suggestions integration", () => {
    it("should render primary AI suggestion as trigger", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" />
        </Wrapper>,
      );

      await waitFor(() => {
        const button = screen.getByText("AI suggested action");
        expect(button).toBeInTheDocument();
      });
    });

    it("should handle navigate action", async () => {
      const mockNavigate = vi.fn();

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" onNavigate={mockNavigate} />
        </Wrapper>,
      );

      await waitFor(() => {
        const button = screen.getByText("AI suggested action");
        expect(button).toBeInTheDocument();
      });

      await userEvent.click(screen.getByText("AI suggested action"));

      expect(mockNavigate).toHaveBeenCalledWith("/ai-suggested-path");
    });

    it("should show confidence indicator for high confidence", async () => {
      // RTK Query API schema: priority 1 → confidence 1.0 (highest)
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({
            suggestions: [
              {
                title: "High confidence suggestion",
                description: "A high priority suggestion",
                action_type: "navigate",
                action_target: "/path",
                priority: 1, // priority 1 → confidence 1.0 (highest)
                icon: "sparkle",
              },
            ],
          });
        }),
      );

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" showConfidence />
        </Wrapper>,
      );

      await waitFor(() => {
        // Should show sparkle/AI indicator for high confidence
        expect(
          screen.getByTestId("ai-suggestion-indicator"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("props forwarding", () => {
    it("should forward variant to EmptyState", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="projects" variant="compact" />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("empty-state-projects")).toHaveAttribute(
          "data-variant",
          "compact",
        );
      });
    });

    it("should forward className to EmptyState", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="traces" className="custom-class" />
        </Wrapper>,
      );

      await waitFor(() => {
        const container = screen.getByTestId("empty-state-traces");
        expect(container).toHaveClass("custom-class");
      });
    });

    it("should accept custom testId", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="files" testId="my-custom-empty-state" />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("my-custom-empty-state")).toBeInTheDocument();
      });
    });
  });

  describe("disabled mode", () => {
    it("should use fallback when enableAI is false", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="workflows" enableAI={false} />
        </Wrapper>,
      );

      // Should immediately show fallback, not loading
      expect(
        screen.queryByTestId("empty-state-loading"),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("empty-state-workflows")).toBeInTheDocument();
    });
  });
});
