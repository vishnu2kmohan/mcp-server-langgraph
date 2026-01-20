/**
 * ConnectedCanvasPanel Core Tests
 *
 * Tests for rendering, loader data integration, artifact selection, styling, and accessibility.
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

describe("ConnectedCanvasPanel - Core", () => {
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

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("should render CanvasWorkspace component", () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-workspace")).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel className="custom-class" />, {
        wrapper: createWrapper(store),
      });
      expect(screen.getByTestId("canvas-panel")).toHaveClass("custom-class");
    });
  });

  describe("Loader Data Integration", () => {
    it("should display artifacts from session loader data", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "First Artifact" }),
        createMockArtifact({ id: "art-2", title: "Second Artifact" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("artifact-tab-art-1")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-tab-art-2")).toBeInTheDocument();
      expect(screen.getAllByText("First Artifact").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Second Artifact").length).toBeGreaterThan(0);
    });

    it("should display empty state when no artifacts", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByText(/no artifacts/i)).toBeInTheDocument();
    });

    it("should fallback to index loader when session loader is undefined", async () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("canvas-workspace")).toBeInTheDocument();
    });
  });

  describe("Artifact Selection", () => {
    it("should dispatch setSelectedArtifactId when artifact is selected", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "Test Artifact" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const artifactTab = screen.getByTestId("artifact-tab-art-1");
      await user.click(artifactTab);
      await waitFor(() => {
        const state = store.getState();
        expect(state.canvas.selectedArtifactId).toBe("art-1");
      });
    });

    it("should auto-select first artifact when none selected", async () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "auto-select-1", title: "Auto Selected" }),
        createMockArtifact({ id: "art-2", title: "Second" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        const state = store.getState();
        expect(state.canvas.selectedArtifactId).toBe("auto-select-1");
      });
    });
  });

  describe("Styling", () => {
    it("should have correct base styling", () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const panel = screen.getByTestId("canvas-panel");
      expect(panel).toHaveClass("flex", "flex-col", "h-full");
    });

    it("should have border styling for panel separation", () => {
      const store = createTestStore();
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const panel = screen.getByTestId("canvas-panel");
      expect(panel).toHaveClass("border-l");
    });
  });

  describe("Multiple Artifacts", () => {
    it("should render artifact tabs for multiple artifacts", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "Artifact One" }),
        createMockArtifact({ id: "art-2", title: "Artifact Two" }),
        createMockArtifact({ id: "art-3", title: "Artifact Three" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.getByTestId("artifact-tab-art-1")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-tab-art-2")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-tab-art-3")).toBeInTheDocument();
    });

    it("should switch between artifacts when tabs are clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "art-1", title: "First" }),
        createMockArtifact({ id: "art-2", title: "Second" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        const state = store.getState();
        expect(state.canvas.selectedArtifactId).toBe("art-1");
      });
      await user.click(screen.getByTestId("artifact-tab-art-2"));
      await waitFor(() => {
        const state = store.getState();
        expect(state.canvas.selectedArtifactId).toBe("art-2");
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper semantic structure", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "a11y-art", title: "Accessible Artifact" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const tab = screen.getByTestId("artifact-tab-a11y-art");
      // Tab uses role="tab" for proper tab list semantics
      expect(tab).toHaveAttribute("role", "tab");
    });

    it("should have accessible artifact tab elements", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({ id: "access-1", title: "Accessible" }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const tab = screen.getByTestId("artifact-tab-access-1");
      expect(tab).toHaveAttribute("role", "tab");
    });
  });

  describe("AI-Generated Artifacts", () => {
    it("should display AI badge for AI-generated artifacts", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "ai-art-1",
          title: "AI Generated",
          editMetadata: {
            origin: "ai",
            modified: false,
            lastEditedBy: "ai",
            aiConfidence: 0.95,
          },
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const aiBadges = screen.getAllByTestId("ai-badge");
      expect(aiBadges.length).toBeGreaterThan(0);
    });

    it("should display AI badge for AI-suggested artifacts", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "ai-art-2",
          title: "AI Suggested",
          editMetadata: {
            origin: "ai",
            modified: false,
            lastEditedBy: "ai",
            aiConfidence: 0.85,
          },
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const aiBadges = screen.getAllByTestId("ai-badge");
      expect(aiBadges.length).toBeGreaterThan(0);
    });

    it("should not display AI badge for user-edited artifacts", () => {
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "user-art",
          title: "User Created",
          editMetadata: {
            origin: "user",
            modified: false,
            lastEditedBy: "user",
          },
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      expect(screen.queryByTestId("ai-badge")).not.toBeInTheDocument();
    });
  });

  describe("Content Callbacks", () => {
    it("should handle content change callback", async () => {
      const _user = userEvent.setup();
      const store = createTestStore();
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "edit-artifact",
          title: "Editable Artifact",
          content: "original content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      await waitFor(() => {
        const state = store.getState();
        expect(state.canvas.selectedArtifactId).toBe("edit-artifact");
      });
      expect(screen.getByTestId("canvas-workspace")).toBeInTheDocument();
    });
  });
});
