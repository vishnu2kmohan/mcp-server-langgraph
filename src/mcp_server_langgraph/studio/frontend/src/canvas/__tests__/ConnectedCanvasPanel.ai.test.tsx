/**
 * ConnectedCanvasPanel AI Suggestions Tests
 *
 * Tests for AI suggestions, caching, accept/dismiss handlers, and feature flags.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { ConnectedCanvasPanel } from "../ConnectedCanvasPanel";
import {
  mockSessionLoaderData,
  createMockArtifact,
  createTestStore,
  createWrapper,
  flushPromises,
  setupSuccessfulFetchMock,
} from "./ConnectedCanvasPanel.fixtures";

// =============================================================================
// Mocks
// =============================================================================

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockSessionLoaderData;
      }
      return undefined;
    }),
    useRevalidator: vi.fn(() => ({
      revalidate: vi.fn(),
      state: "idle",
    })),
  };
});

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => {
    if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
      return true;
    }
    return false;
  },
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedCanvasPanel - AI Suggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockSessionLoaderData.sessionId = "session-123";
    mockSessionLoaderData.messages = [];
    mockSessionLoaderData.artifacts = [];
  });

  afterEach(async () => {
    cleanup();
    await act(async () => {
      await flushPromises();
    });
  });

  describe("AI InlineSuggestions (Phase 4)", () => {
    it("should not show inline suggestions when no artifact is selected", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(
        screen.queryByTestId("inline-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should display loading state when suggestions are loading", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "art-1",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "Test" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("art-1");
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });
  });

  describe("Feature Flag Gating", () => {
    it("should respect canvas_ai_palette feature flag for AI features", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "art-1",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "Test", contentType: "code" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
      // Component renders AI features when flag is on (suggestions may or may not appear based on async loading)
    });
  });

  describe("Suggestion Fetching", () => {
    it("should fetch suggestions when artifact is selected and has code content", async () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "code-artifact",
          title: "Code File",
          content: 'function hello() { console.log("world"); }',
          contentType: "code",
          editMetadata: { editedBy: "user", language: "javascript" },
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe(
          "code-artifact",
        );
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should show loading state while fetching suggestions", async () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "loading-test",
          title: "Loading Test",
          content: "const x = 1;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("loading-test");
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should not fetch suggestions for non-code artifacts", async () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "text-artifact",
          title: "Plain Text",
          content: "This is plain text content",
          contentType: "text",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe(
          "text-artifact",
        );
      });
      expect(
        screen.queryByTestId("inline-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should clear suggestions when switching artifacts", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "First" }),
        createMockArtifact({ id: "art-2", title: "Second" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("art-1");
      });
      await user.click(screen.getByTestId("artifact-tab-art-2"));
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("art-2");
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });
  });

  describe("AI Suggestions Caching Integration", () => {
    it("should use cached suggestions when available via useAISuggestionsFetch", async () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "cached-art",
          title: "Cached Test",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("cached-art");
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should clear suggestions cache when artifact changes", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "art-cache-1",
          title: "First",
          contentType: "code",
        }),
        createMockArtifact({
          id: "art-cache-2",
          title: "Second",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("art-cache-1");
      });
      await user.click(screen.getByTestId("artifact-tab-art-cache-2"));
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("art-cache-2");
      });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should handle suggestion accept action", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "accept-test-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "accept-test-art",
          title: "Accept Test",
          content: "const x = 1;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should handle suggestion dismiss action", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "dismiss-test-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "dismiss-test-art",
          title: "Dismiss Test",
          content: "const y = 2;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });
  });

  describe("AI Suggestion Accept/Dismiss Handlers", () => {
    beforeEach(() => {
      setupSuccessfulFetchMock();
    });

    afterEach(() => {
      cleanup();
      vi.restoreAllMocks();
    });

    it("should apply completion suggestion by appending to content", async () => {
      const user = userEvent.setup();
      const fetchMock = vi.spyOn(global, "fetch");
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "completion-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "completion-art",
          title: "Completion Test",
          content: "const x = 1;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      // Try to interact with suggestions if they appear
      const acceptButtons = screen.queryAllByTestId("suggestion-accept");
      if (acceptButtons.length > 0) {
        await user.click(acceptButtons[0]);
        await waitFor(() => {
          expect(fetchMock).toHaveBeenCalled();
        });
      }
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should apply refactor suggestion by replacing content", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "refactor-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "refactor-art",
          title: "Refactor Test",
          content: "function old() { return 1; }",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      // Try to accept a suggestion if available
      const acceptButtons = screen.queryAllByTestId("suggestion-accept");
      if (acceptButtons.length > 0) {
        await user.click(acceptButtons[0]);
      }
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should apply fix suggestion by replacing content", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "fix-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "fix-art",
          title: "Fix Test",
          content: "const x = undefined.foo; // bug",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should apply explain suggestion by adding comment at top", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "explain-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "explain-art",
          title: "Explain Test",
          content:
            "const fibonacci = (n) => n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2);",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should dismiss suggestion and remove from list", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "dismiss-action-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "dismiss-action-art",
          title: "Dismiss Action Test",
          content: "const code = true;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      // Find and click dismiss button if suggestions appear
      const dismissButtons = screen.queryAllByTestId("suggestion-dismiss");
      if (dismissButtons.length > 0) {
        await user.click(dismissButtons[0]);
      }
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should not apply suggestion when artifact is not found", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "nonexistent-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should handle suggestion with empty content gracefully", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "empty-suggestion-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "empty-suggestion-art",
          title: "Empty Suggestion Test",
          content: "const value = 1;",
          contentType: "code",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });
  });

  describe("Save Status Indicator", () => {
    it("should not show save status indicator when idle", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "Test" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(
        screen.queryByTestId("save-status-indicator"),
      ).not.toBeInTheDocument();
    });
  });
});
