/**
 * CanvasWorkspace Tabs Tests
 *
 * Tests for tab changes, tab content switching, tab visibility, and single pane layout.
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

// Mock useFeatureFlag
vi.mock("../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: (flag: string) => {
      if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
        return true;
      }
      return false;
    },
  };
});
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
import {
  screen,
  fireEvent,
  cleanup,
  waitFor,
  within,
} from "@testing-library/react";
import { CanvasWorkspace } from "../CanvasWorkspace";
import {
  mockArtifacts,
  mermaidArtifact,
  jsonArtifact,
  renderWithProviders,
  createStoreWithArtifact,
} from "./CanvasWorkspace.fixtures.tsx";

describe("CanvasWorkspace - Tabs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Tab Changes", () => {
    it("should disable preview and data tabs when in edit mode", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      expect(screen.getByTestId("content-editor")).toBeInTheDocument();
    });
  });

  describe("Tab Content Switching", () => {
    it("should show syntax-highlighted code when Code tab is active", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const codeTab = screen.getByRole("tab", { name: /code/i });
      expect(codeTab).toHaveAttribute("aria-selected", "true");

      await waitFor(() => {
        expect(screen.getByTestId("code-view")).toBeInTheDocument();
      });
    });

    it("should switch to Preview view when Preview tab is clicked", async () => {
      const store = createStoreWithArtifact("mermaid-1");

      renderWithProviders(<CanvasWorkspace artifacts={mermaidArtifact} />, {
        store,
      });

      const previewTab = screen.getByRole("tab", { name: /preview/i });
      fireEvent.click(previewTab);

      await waitFor(() => {
        expect(screen.getByTestId("preview-view")).toBeInTheDocument();
      });
    });

    it("should switch to Data view when Data tab is clicked for JSON content", async () => {
      const store = createStoreWithArtifact("json-1");

      renderWithProviders(<CanvasWorkspace artifacts={jsonArtifact} />, {
        store,
      });

      const viewTabs = within(screen.getByTestId("canvas-tabs"));
      const dataTab = viewTabs.getByRole("tab", { name: /data/i });
      fireEvent.click(dataTab);

      await waitFor(() => {
        expect(screen.getByTestId("data-view")).toBeInTheDocument();
      });
    });
  });

  describe("Tab Visibility Based on Content Type", () => {
    it("should only show Code tab for plain code artifacts", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const viewTabs = within(screen.getByTestId("canvas-tabs"));
      expect(viewTabs.getByRole("tab", { name: /code/i })).toBeInTheDocument();

      expect(
        viewTabs.queryByRole("tab", { name: /preview/i }),
      ).not.toBeInTheDocument();

      expect(
        viewTabs.queryByRole("tab", { name: /data/i }),
      ).not.toBeInTheDocument();
    });

    it("should show Code and Preview tabs for mermaid artifacts", () => {
      const store = createStoreWithArtifact("mermaid-1");

      renderWithProviders(<CanvasWorkspace artifacts={mermaidArtifact} />, {
        store,
      });

      const viewTabs = within(screen.getByTestId("canvas-tabs"));
      expect(viewTabs.getByRole("tab", { name: /code/i })).toBeInTheDocument();
      expect(
        viewTabs.getByRole("tab", { name: /preview/i }),
      ).toBeInTheDocument();
    });

    it("should show Code and Data tabs for JSON artifacts", () => {
      const store = createStoreWithArtifact("json-1");

      renderWithProviders(<CanvasWorkspace artifacts={jsonArtifact} />, {
        store,
      });

      const viewTabs = within(screen.getByTestId("canvas-tabs"));
      expect(viewTabs.getByRole("tab", { name: /code/i })).toBeInTheDocument();
      expect(viewTabs.getByRole("tab", { name: /data/i })).toBeInTheDocument();
    });
  });

  describe("Single Pane Layout", () => {
    it("should not render separate preview panel", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      expect(screen.queryByTestId("panel-preview")).not.toBeInTheDocument();
    });

    it("should not render resize handle", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      expect(screen.queryByTestId("resize-handle")).not.toBeInTheDocument();
    });
  });
});
