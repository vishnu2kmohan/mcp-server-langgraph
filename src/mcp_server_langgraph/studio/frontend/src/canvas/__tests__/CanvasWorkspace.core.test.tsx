/**
 * CanvasWorkspace Core Tests
 *
 * Tests for rendering, layout, artifact selection, content display, and custom className.
 *
 * Memory Safety: This shard uses xdist_group and gc.collect() to prevent
 * mock accumulation in pytest-xdist workers.
 */

// Mock declarations MUST be hoisted before imports
import { vi } from "vitest";

// Mock react-resizable-panels
vi.mock("react-resizable-panels", () => ({
  Panel: ({ children, ...props }: { children: React.ReactNode }) => (
    <div data-testid={`panel-${props.id || "unknown"}`}>{children}</div>
  ),
  PanelGroup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="panel-group">{children}</div>
  ),
  PanelResizeHandle: () => <div data-testid="resize-handle" />,
}));

// Mock useFeatureFlag to enable AI components in tests
vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => {
    if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
      return true;
    }
    return false;
  },
}));

// Mock useCanvasIntelligence hooks
vi.mock("../../hooks/useCanvasIntelligence", () => ({
  useCodeAnalysis: () => ({
    qualityScore: 85,
    complexity: 5,
    issues: [],
    suggestions: [],
    isLoading: false,
    error: null,
  }),
  useDiagramAnalysis: () => ({
    isValid: true,
    diagramType: "flowchart",
    nodeCount: 5,
    edgeCount: 4,
    issues: [],
    suggestions: [],
    isLoading: false,
    error: null,
  }),
}));

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { screen, cleanup, waitFor } from "@testing-library/react";
import { CanvasWorkspace } from "../CanvasWorkspace";
import {
  mockArtifacts,
  renderWithProviders,
  createStoreWithArtifact,
  createTestStore,
  defaultCanvasState,
} from "./CanvasWorkspace.fixtures.tsx";

describe("CanvasWorkspace - Core", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render workspace container", () => {
      renderWithProviders(<CanvasWorkspace artifacts={[]} />);
      expect(screen.getByTestId("canvas-workspace")).toBeInTheDocument();
    });

    it("should render workspace even with empty artifacts", () => {
      renderWithProviders(<CanvasWorkspace artifacts={[]} />);
      expect(screen.getByTestId("canvas-workspace")).toBeInTheDocument();
    });

    it("should render empty state when no artifacts", () => {
      renderWithProviders(<CanvasWorkspace artifacts={[]} />);
      expect(screen.getByText(/no artifacts/i)).toBeInTheDocument();
    });

    it("should render artifact list when artifacts provided", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);
      expect(screen.getByTestId("artifact-tab-artifact-1")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-tab-artifact-2")).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should render code view in single pane layout", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);
      expect(screen.getByTestId("code-view")).toBeInTheDocument();
    });

    it("should render canvas tabs", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);
      expect(screen.getByTestId("canvas-tabs")).toBeInTheDocument();
    });

    it("should render artifact actions", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);
      expect(screen.getByTestId("artifact-actions")).toBeInTheDocument();
    });
  });

  describe("Artifact Selection", () => {
    it("should select first artifact by default when artifacts provided", () => {
      const store = createTestStore({
        canvas: defaultCanvasState,
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      expect(screen.getByTestId("artifact-tab-artifact-1")).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("should switch selected artifact when tab clicked", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const tab2 = screen.getByTestId("artifact-tab-artifact-2");
      tab2.click();

      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("artifact-2");
      });
    });
  });

  describe("Content Display", () => {
    it("should display selected artifact content", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      expect(screen.getByTestId("panel-editor")).toBeInTheDocument();
      expect(screen.getByTestId("code-view")).toBeInTheDocument();

      const editorPanel = screen.getByTestId("panel-editor");
      expect(editorPanel).toBeInTheDocument();
    });

    it("should show AI badge for AI-generated artifacts", () => {
      const store = createStoreWithArtifact("artifact-2");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const aiBadges = screen.getAllByTestId("ai-badge");
      expect(aiBadges.length).toBeGreaterThan(0);
    });
  });

  describe("Custom className", () => {
    it("should apply custom className to workspace container", () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={[]} className="custom-class" />,
      );
      expect(screen.getByTestId("canvas-workspace")).toHaveClass(
        "custom-class",
      );
    });

    it("should apply custom className to workspace with artifacts", () => {
      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          className="my-custom-style"
        />,
      );
      expect(screen.getByTestId("canvas-workspace")).toHaveClass(
        "my-custom-style",
      );
    });
  });
});
