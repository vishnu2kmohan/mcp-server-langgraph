/**
 * AIEmptyState Component Tests
 *
 * Tests for the AI-enhanced empty state component that integrates
 * useAIEmptyState hook with the base EmptyState component.
 *
 * Phase 6.2: AI-Native Integration Layer
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
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
import { clearSuggestionCache } from "../../hooks/useAIEmptyState";

// Mock feature flag - default to enabled for AI empty state
vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: vi.fn((flagName: string) => {
    if (flagName === "ai_empty_state") return true;
    return false;
  }),
}));

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
    // Clear module-level cache between tests for isolation
    clearSuggestionCache();

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
    cleanup();
    server.resetHandlers();
    vi.clearAllMocks();
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

  // ===========================================================================
  // New tests for emptyType and onAction props (Sprint 2)
  // ===========================================================================

  describe("emptyType prop", () => {
    it("should render default title when emptyType is 'empty'", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="sessions" emptyType="empty" enableAI={false} />
        </Wrapper>,
      );

      // Should show default title from registry
      expect(screen.getByText(/no sessions/i)).toBeInTheDocument();
    });

    it("should render 'no matches' title when emptyType is 'no-matches'", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState
            context="sessions"
            emptyType="no-matches"
            enableAI={false}
          />
        </Wrapper>,
      );

      // Should show no matches variant
      expect(screen.getByText(/no sessions found/i)).toBeInTheDocument();
    });

    it("should include search query in 'no-matches' title", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState
            context="projects"
            emptyType="no-matches"
            searchQuery="test-query"
            enableAI={false}
          />
        </Wrapper>,
      );

      // Should show search query in title
      expect(
        screen.getByText(/no projects matching.*test-query/i),
      ).toBeInTheDocument();
    });

    it("should default emptyType to 'empty'", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="files" enableAI={false} />
        </Wrapper>,
      );

      // Should show default title (not "no matches" variant)
      expect(screen.getByText(/no files/i)).toBeInTheDocument();
      expect(screen.queryByText(/no files found/i)).not.toBeInTheDocument();
    });
  });

  describe("onAction prop", () => {
    it("should call onAction when trigger is clicked", async () => {
      const mockOnAction = vi.fn();

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState
            context="projects"
            onAction={mockOnAction}
            actionLabel="Create Project"
            enableAI={false}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(screen.getByRole("button")).toBeInTheDocument();
      });

      await userEvent.click(
        screen.getByRole("button", { name: /create project/i }),
      );

      expect(mockOnAction).toHaveBeenCalled();
    });

    it("should prefer onAction over onNavigate when both provided", async () => {
      const mockOnAction = vi.fn();
      const mockOnNavigate = vi.fn();

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState
            context="projects"
            onAction={mockOnAction}
            onNavigate={mockOnNavigate}
            actionLabel="Create Project"
            enableAI={false}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /create project/i }),
        ).toBeInTheDocument();
      });

      await userEvent.click(
        screen.getByRole("button", { name: /create project/i }),
      );

      expect(mockOnAction).toHaveBeenCalled();
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });

    it("should use actionLabel prop to override registry action", async () => {
      const mockOnAction = vi.fn();

      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState
            context="workflows"
            onAction={mockOnAction}
            actionLabel="Custom Action Label"
            enableAI={false}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /custom action label/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("new contexts (Sprint 2)", () => {
    it("should render prompts context", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="prompts" enableAI={false} />
        </Wrapper>,
      );

      expect(screen.getByTestId("empty-state-prompts")).toBeInTheDocument();
      expect(screen.getByText(/no prompts/i)).toBeInTheDocument();
    });

    it("should render tools context", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="tools" enableAI={false} />
        </Wrapper>,
      );

      expect(screen.getByTestId("empty-state-tools")).toBeInTheDocument();
      expect(screen.getByText(/no tools/i)).toBeInTheDocument();
    });

    it("should render resources context", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="resources" enableAI={false} />
        </Wrapper>,
      );

      expect(screen.getByTestId("empty-state-resources")).toBeInTheDocument();
      expect(screen.getByText(/no resources/i)).toBeInTheDocument();
    });

    it("should render audit context", async () => {
      const Wrapper = createWrapper();
      render(
        <Wrapper>
          <AIEmptyState context="audit" enableAI={false} />
        </Wrapper>,
      );

      expect(screen.getByTestId("empty-state-audit")).toBeInTheDocument();
      expect(screen.getByText(/no audit/i)).toBeInTheDocument();
    });
  });
});
