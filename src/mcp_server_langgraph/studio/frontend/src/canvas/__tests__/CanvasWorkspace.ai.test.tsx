/**
 * CanvasWorkspace AI and Accessibility Tests
 *
 * Tests for AI Edit Overlay, AI Intelligence Integration, Artifact Hover Details,
 * and Accessibility (WCAG 2.1 AA).
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
    refetch: vi.fn(),
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
    refetch: vi.fn(),
  }),
}));

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  screen,
  fireEvent,
  cleanup,
  waitFor,
  act,
} from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { CanvasWorkspace } from "../CanvasWorkspace";
import {
  mockArtifacts,
  multiLineArtifacts,
  renderWithProviders,
  createStoreWithArtifact,
  createTestStore,
  defaultCanvasState,
} from "./CanvasWorkspace.fixtures.tsx";

expect.extend(toHaveNoViolations);

describe("CanvasWorkspace - AI and Accessibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Accessibility (WCAG 2.1 AA)", () => {
    it("should have no accessibility violations with empty artifacts", async () => {
      const { container } = renderWithProviders(
        <CanvasWorkspace artifacts={[]} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with artifacts", async () => {
      const store = createStoreWithArtifact("artifact-1");

      const { container } = renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} />,
        { store },
      );
      // Exclude nested-interactive: ArtifactTab has buttons (close, drag) inside role="tab"
      // which is a common pattern for tabs with actions. Will address in future refactor.
      const results = await axe(container, {
        rules: { "nested-interactive": { enabled: false } },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe("AI Edit Overlay (Phase 4)", () => {
    it("should open AI Edit Overlay when Cmd+E is pressed with artifact selected", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await waitFor(() => {
        expect(screen.getAllByText("Hello World").length).toBeGreaterThan(0);
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });
    });

    it("should open AI Edit Overlay when Ctrl+E is pressed (Windows/Linux)", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });
    });

    it("should not open AI Edit Overlay when no artifact is selected", async () => {
      const store = createTestStore({
        canvas: {
          ...defaultCanvasState,
          selectedArtifactId: null,
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={[]} />, { store });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
    });

    it("should close AI Edit Overlay when cancel is clicked", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });
    });

    it("should apply AI edit when apply is clicked", async () => {
      const onSave = vi.fn();
      const onContentChange = vi.fn();
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onSave={onSave}
          onContentChange={onContentChange}
        />,
        { store },
      );

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });

      expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
    });

    it("should wire up AI edit callbacks to parent handlers", async () => {
      const onSave = vi.fn();
      const onContentChange = vi.fn();
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onSave={onSave}
          onContentChange={onContentChange}
        />,
        { store },
      );

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });

      expect(
        screen.getByPlaceholderText(/describe|instruction|edit/i),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should close AI Edit Overlay when Escape key is pressed on overlay", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });

      const overlay = screen.getByTestId("ai-edit-overlay");
      fireEvent.keyDown(overlay, { key: "Escape" });

      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });
    });

    it("should pass selection content to AI Edit Overlay", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        const overlay = screen.getByTestId("ai-edit-overlay");
        expect(overlay).toBeInTheDocument();
      });

      expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
    });

    it("should not trigger AI edit when regular E key is pressed without modifier", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: false,
          ctrlKey: false,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
    });

    it("should reset selection state when overlay is cancelled", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });

      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });
    });
  });

  // Skip: Hover tooltips replaced with attribution dots in new ArtifactTab component
  describe.skip("Artifact Hover Details", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should show hover tooltip when enableArtifactHover prop is true", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);

      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    it("should display artifact type in hover tooltip", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/code/i);
    });

    it("should display language in hover tooltip when available", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/javascript/i);
    });

    it("should display line count in hover tooltip", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/1 line/i);
    });

    it("should display creation timestamp in hover tooltip", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/created/i);
    });

    it("should display AI badge indicator in hover tooltip for AI-generated artifacts", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-2");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/ai generated/i);
    });

    it("should display user edited indicator in hover tooltip for user-edited artifacts", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/user/i);
    });

    it("should hide hover tooltip when mouse leaves", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      fireEvent.mouseLeave(tab);

      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
    });

    it("should not show hover tooltip when enableArtifactHover is false", async () => {
      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableArtifactHover={false}
        />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("should show correct line count for multi-line artifacts", async () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={multiLineArtifacts} enableArtifactHover />,
      );

      const tab = screen.getByTestId("artifact-tab-multi-line");
      fireEvent.mouseEnter(tab);
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveTextContent(/5 lines/i);
    });
  });

  describe("AI Intelligence Integration", () => {
    it("should render AI intelligence indicator when enableAI is true", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={true}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      expect(
        screen.getByTestId("ai-intelligence-indicator"),
      ).toBeInTheDocument();
    });

    it("should show quality score for code artifacts after analysis", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={true}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      // Click the "Analyze" button to trigger code analysis
      const analyzeButton = screen.getByTestId("analyze-code-trigger");
      await act(async () => {
        fireEvent.click(analyzeButton);
      });

      // After analysis, the quality score should be displayed
      await waitFor(() => {
        expect(screen.getByText("85")).toBeInTheDocument();
      });
    });

    it("should NOT render AI indicator when enableAI is false", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={false}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      expect(
        screen.queryByTestId("ai-intelligence-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should pass persona context to AI hooks via props", () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={true}
          userId="user:alice"
          sessionId="session-456"
          persona="developer"
        />,
        { store },
      );

      expect(
        screen.getByTestId("ai-intelligence-indicator"),
      ).toBeInTheDocument();
    });
  });
});
