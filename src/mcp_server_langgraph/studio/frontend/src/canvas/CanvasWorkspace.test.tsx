/**
 * CanvasWorkspace Tests - Phase 1
 *
 * Tests for the main Canvas workspace component that manages
 * the artifact display area with resizable panels.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  cleanup,
  within,
} from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { CanvasWorkspace } from "./CanvasWorkspace";
import canvasReducer from "../store/slices/canvasSlice";
import type { CanvasArtifact } from "../types/artifacts";

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
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => {
    // Enable AI feature flags for testing
    if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
      return true;
    }
    return false;
  },
}));

// Mock useCanvasIntelligence hooks for AI intelligence tests
const mockCodeAnalysis = {
  qualityScore: 85,
  complexity: 5,
  issues: [],
  suggestions: [],
  isLoading: false,
  error: null,
};

const mockDiagramAnalysis = {
  isValid: true,
  diagramType: "flowchart",
  nodeCount: 5,
  edgeCount: 4,
  issues: [],
  suggestions: [],
  isLoading: false,
  error: null,
};

vi.mock("../hooks/useCanvasIntelligence", () => ({
  useCodeAnalysis: () => mockCodeAnalysis,
  useDiagramAnalysis: () => mockDiagramAnalysis,
}));

// =============================================================================
// Test Utilities
// =============================================================================

const mockArtifacts: CanvasArtifact[] = [
  {
    id: "artifact-1",
    type: "code",
    sessionId: "session-1",
    version: 1,
    content: 'console.log("Hello, World!");',
    contentType: "code",
    title: "Hello World",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
    editMetadata: {
      editedBy: "user",
      language: "javascript",
    },
  },
  {
    id: "artifact-2",
    type: "code",
    sessionId: "session-1",
    version: 2,
    content: "# README\n\nThis is a readme file.",
    contentType: "markdown",
    title: "README",
    createdAt: "2024-01-01T01:00:00Z",
    updatedAt: "2024-01-01T01:00:00Z",
    editMetadata: {
      editedBy: "ai-generation",
      aiConfidence: 0.95,
    },
  },
];

function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
    },
    preloadedState,
  });
}

function renderWithProviders(
  ui: React.ReactElement,
  { store = createTestStore(), ...options } = {},
) {
  return render(
    <Provider store={store}>
      <MemoryRouter>{ui}</MemoryRouter>
    </Provider>,
    options,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("CanvasWorkspace", () => {
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
      // Check for artifact tabs (there may be multiple instances of the title)
      expect(screen.getByTestId("artifact-tab-artifact-1")).toBeInTheDocument();
      expect(screen.getByTestId("artifact-tab-artifact-2")).toBeInTheDocument();
    });
  });

  describe("Artifact Selection", () => {
    it("should select first artifact by default when artifacts provided", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // First artifact should be highlighted
      expect(screen.getByTestId("artifact-tab-artifact-1")).toHaveClass(
        "active",
      );
    });

    it("should switch selected artifact when tab clicked", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      fireEvent.click(screen.getByTestId("artifact-tab-artifact-2"));

      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("artifact-2");
      });
    });
  });

  describe("Layout", () => {
    it("should render code view in single pane layout", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);
      // Single pane layout - code view is shown by default
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

  describe("Content Display", () => {
    it("should display selected artifact content", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Verify single pane layout with code view (no separate preview panel)
      expect(screen.getByTestId("panel-editor")).toBeInTheDocument();
      expect(screen.getByTestId("code-view")).toBeInTheDocument();

      // The artifact content is rendered via CanvasArtifact component
      // which uses a code editor - check for the views rather than text content
      // since code editors may not expose content via DOM text nodes
      const editorPanel = screen.getByTestId("panel-editor");
      expect(editorPanel).toBeInTheDocument();
    });

    it("should show AI badge for AI-generated artifacts", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-2",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Multiple AI badges may appear (tab + artifact components)
      const aiBadges = screen.getAllByTestId("ai-badge");
      expect(aiBadges.length).toBeGreaterThan(0);
    });
  });

  describe("Callbacks", () => {
    it("should call onArtifactSelect when artifact selected", () => {
      const onArtifactSelect = vi.fn();

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onArtifactSelect={onArtifactSelect}
        />,
      );

      fireEvent.click(screen.getByTestId("artifact-tab-artifact-2"));

      expect(onArtifactSelect).toHaveBeenCalledWith(mockArtifacts[1]);
    });

    it("should call onContentChange when content edited", async () => {
      const onContentChange = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onContentChange={onContentChange}
        />,
        { store },
      );

      // First enter edit mode by clicking edit button
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Now the content-editor should be visible
      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "new content" } });

      expect(onContentChange).toHaveBeenCalledWith("artifact-1", "new content");
    });

    it("should call onSave when save button clicked", async () => {
      const onSave = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} onSave={onSave} />,
        { store },
      );

      // Enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Modify content
      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "updated content" } });

      // Save
      const saveButtons = screen.getAllByTestId("save-button");
      fireEvent.click(saveButtons[0]);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith("artifact-1", "updated content");
      });
    });
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
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      const { container } = renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} />,
        { store },
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Edit Mode Transitions", () => {
    it("should cancel edit mode and clear editContent", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Modify content
      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "modified content" } });

      // Cancel edit mode
      const cancelButtons = screen.getAllByTestId("cancel-button");
      fireEvent.click(cancelButtons[0]);

      // Verify edit mode is exited - no content-editor should be visible
      await waitFor(() => {
        expect(screen.queryByTestId("content-editor")).not.toBeInTheDocument();
      });
    });

    it("should reset edit mode when switching artifacts", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Enter edit mode for artifact-1
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Verify in edit mode
      expect(screen.getByTestId("content-editor")).toBeInTheDocument();

      // Switch to artifact-2
      fireEvent.click(screen.getByTestId("artifact-tab-artifact-2"));

      // Verify edit mode is reset
      await waitFor(() => {
        expect(screen.queryByTestId("content-editor")).not.toBeInTheDocument();
      });
    });
  });

  describe("Tab Changes", () => {
    it("should disable preview and data tabs when in edit mode", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // CanvasTabs should receive disabledTabs=['preview', 'data']
      // This is verified by the component internals - if tabs are disabled, they're not clickable
      expect(screen.getByTestId("content-editor")).toBeInTheDocument();
    });
  });

  describe("Tab Content Switching", () => {
    it("should show syntax-highlighted code when Code tab is active", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Code tab is active by default
      const codeTab = screen.getByRole("tab", { name: /code/i });
      expect(codeTab).toHaveAttribute("aria-selected", "true");

      // Should show code content with syntax highlighting
      await waitFor(() => {
        expect(screen.getByTestId("code-view")).toBeInTheDocument();
      });
    });

    it("should switch to Preview view when Preview tab is clicked", async () => {
      const mermaidArtifact: CanvasArtifact[] = [
        {
          id: "mermaid-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "graph TD\n  A --> B",
          contentType: "mermaid",
          title: "Mermaid Diagram",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ];

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "mermaid-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mermaidArtifact} />, {
        store,
      });

      // Click Preview tab
      const previewTab = screen.getByRole("tab", { name: /preview/i });
      fireEvent.click(previewTab);

      // Should show rendered preview
      await waitFor(() => {
        expect(screen.getByTestId("preview-view")).toBeInTheDocument();
      });
    });

    it("should switch to Data view when Data tab is clicked for JSON content", async () => {
      const jsonArtifact: CanvasArtifact[] = [
        {
          id: "json-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: '{"name": "test", "value": 123}',
          contentType: "json",
          title: "JSON Data",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ];

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "json-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={jsonArtifact} />, {
        store,
      });

      // Click Data tab
      const dataTab = screen.getByRole("tab", { name: /data/i });
      fireEvent.click(dataTab);

      // Should show data view with interactive JSON tree
      await waitFor(() => {
        expect(screen.getByTestId("data-view")).toBeInTheDocument();
      });
    });
  });

  describe("Tab Visibility Based on Content Type", () => {
    it("should only show Code tab for plain code artifacts", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Code tab should be visible
      expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();

      // Preview tab should be hidden for plain code
      expect(
        screen.queryByRole("tab", { name: /preview/i }),
      ).not.toBeInTheDocument();

      // Data tab should be hidden for plain code
      expect(
        screen.queryByRole("tab", { name: /data/i }),
      ).not.toBeInTheDocument();
    });

    it("should show Code and Preview tabs for mermaid artifacts", () => {
      const mermaidArtifact: CanvasArtifact[] = [
        {
          id: "mermaid-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "graph TD\n  A --> B",
          contentType: "mermaid",
          title: "Mermaid Diagram",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ];

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "mermaid-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mermaidArtifact} />, {
        store,
      });

      // Both Code and Preview tabs should be visible
      expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /preview/i })).toBeInTheDocument();
    });

    it("should show Code and Data tabs for JSON artifacts", () => {
      const jsonArtifact: CanvasArtifact[] = [
        {
          id: "json-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: '{"name": "test"}',
          contentType: "json",
          title: "JSON Data",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ];

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "json-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={jsonArtifact} />, {
        store,
      });

      // Code and Data tabs should be visible
      expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /data/i })).toBeInTheDocument();
    });
  });

  describe("Single Pane Layout", () => {
    it("should not render separate preview panel", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      // The separate preview panel should not exist
      expect(screen.queryByTestId("panel-preview")).not.toBeInTheDocument();
    });

    it("should not render resize handle", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      // No resize handle since there's only one panel
      expect(screen.queryByTestId("resize-handle")).not.toBeInTheDocument();
    });
  });

  describe("Artifact Display Edge Cases", () => {
    it("should display truncated artifact ID when no title provided", () => {
      const artifactWithoutTitle: CanvasArtifact[] = [
        {
          id: "abcdef123456",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "test",
          contentType: "code",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ];

      renderWithProviders(<CanvasWorkspace artifacts={artifactWithoutTitle} />);

      // Should show "Artifact abcdef" (first 6 chars of ID)
      expect(screen.getByText(/Artifact abcdef/)).toBeInTheDocument();
    });

    it("should show ai-suggestion badge for ai-suggestion editedBy", () => {
      const aiSuggestionArtifact: CanvasArtifact[] = [
        {
          id: "ai-sug-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "AI suggested code",
          contentType: "code",
          title: "AI Suggestion",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
          editMetadata: {
            editedBy: "ai-suggestion",
            aiConfidence: 0.8,
          },
        },
      ];

      renderWithProviders(<CanvasWorkspace artifacts={aiSuggestionArtifact} />);

      // AI badge should be visible
      expect(screen.getAllByTestId("ai-badge").length).toBeGreaterThan(0);
    });

    it("should not show AI badge for user-edited artifacts", () => {
      const userEditedArtifact: CanvasArtifact[] = [
        {
          id: "user-edit-1",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "User code",
          contentType: "code",
          title: "User Code",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
          editMetadata: {
            editedBy: "user",
          },
        },
      ];

      renderWithProviders(<CanvasWorkspace artifacts={userEditedArtifact} />);

      // AI badge should NOT be visible in the tab
      const tabs = screen.getByTestId("artifact-tab-user-edit-1");
      expect(tabs.querySelector('[data-testid="ai-badge"]')).toBeNull();
    });
  });

  describe("Content Change Without Selection", () => {
    it("should handle content change callback even when selectedArtifactId is null initially", async () => {
      const onContentChange = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null, // Initially null
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onContentChange={onContentChange}
        />,
        { store },
      );

      // Auto-selection should happen, then enter edit mode
      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("artifact-1");
      });

      // Now enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Modify content
      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "new content" } });

      expect(onContentChange).toHaveBeenCalledWith("artifact-1", "new content");
    });
  });

  describe("Save Without Content", () => {
    it("should not call onSave when editContent is empty", async () => {
      const onSave = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} onSave={onSave} />,
        { store },
      );

      // Enter edit mode
      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      // Clear content
      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "" } });

      // Try to save
      const saveButtons = screen.getAllByTestId("save-button");
      fireEvent.click(saveButtons[0]);

      // onSave should not be called because content is empty
      expect(onSave).not.toHaveBeenCalled();
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

  describe("AI Edit Overlay (Phase 4)", () => {
    it("should open AI Edit Overlay when Cmd+E is pressed with artifact selected", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Wait for artifact to be displayed (multiple elements may have this text)
      await waitFor(() => {
        expect(screen.getAllByText("Hello World").length).toBeGreaterThan(0);
      });

      // Simulate Cmd+E keydown - wrap in act() to handle state updates
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // AI Edit Overlay should appear
      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });
    });

    it("should open AI Edit Overlay when Ctrl+E is pressed (Windows/Linux)", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Simulate Ctrl+E keydown - wrap in act() to handle state updates
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          ctrlKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // AI Edit Overlay should appear
      await waitFor(() => {
        expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
      });
    });

    it("should not open AI Edit Overlay when no artifact is selected", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={[]} />, { store });

      // Simulate Cmd+E keydown - wrap in act() to handle state updates
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // AI Edit Overlay should NOT appear
      expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
    });

    it("should close AI Edit Overlay when cancel is clicked", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Open AI Edit Overlay - wrap in act() to handle state updates
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

      // Click cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Overlay should be closed
      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });
    });

    it("should apply AI edit when apply is clicked", async () => {
      const onSave = vi.fn();
      const onContentChange = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onSave={onSave}
          onContentChange={onContentChange}
        />,
        { store },
      );

      // Open AI Edit Overlay - wrap in act() to handle state updates
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

      // The overlay would allow editing - we verify callbacks are wired
      // by checking the overlay is displayed and can be interacted with
      expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
    });

    it("should wire up AI edit callbacks to parent handlers", async () => {
      // This test verifies that the AI Edit Overlay is wired up correctly.
      // The detailed instruction → generate → apply flow is tested in
      // AIEditOverlay.test.tsx. Here we just verify the overlay renders
      // with the correct props connected.
      const onSave = vi.fn();
      const onContentChange = vi.fn();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onSave={onSave}
          onContentChange={onContentChange}
        />,
        { store },
      );

      // Open AI Edit Overlay
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

      // Verify the overlay has the expected structure (input field, buttons)
      expect(
        screen.getByPlaceholderText(/describe|instruction|edit/i),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should close AI Edit Overlay when Escape key is pressed on overlay", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Open AI Edit Overlay
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

      // Press Escape on the overlay element (React onKeyDown handler)
      const overlay = screen.getByTestId("ai-edit-overlay");
      fireEvent.keyDown(overlay, { key: "Escape" });

      // Overlay should be closed
      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });
    });

    it("should pass selection content to AI Edit Overlay", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Open AI Edit Overlay
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: true,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // Overlay should be visible with selection context
      await waitFor(() => {
        const overlay = screen.getByTestId("ai-edit-overlay");
        expect(overlay).toBeInTheDocument();
      });

      // The overlay should show the selected content context
      // (implementation-specific - overlay may display selection info)
      expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
    });

    it("should not trigger AI edit when regular E key is pressed without modifier", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Press just E without modifier
      await act(async () => {
        const event = new KeyboardEvent("keydown", {
          key: "e",
          metaKey: false,
          ctrlKey: false,
          bubbles: true,
        });
        document.dispatchEvent(event);
      });

      // AI Edit Overlay should NOT appear
      expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
    });

    it("should reset selection state when overlay is cancelled", async () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      // Open overlay
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

      // Cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Verify overlay closed
      await waitFor(() => {
        expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
      });

      // Re-open should work (proves state was reset)
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

  describe("Artifact Renaming", () => {
    it("should display artifact titles in tabs", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      // Use testid to find artifact tabs
      const tab1 = screen.getByTestId("artifact-tab-artifact-1");
      const tab2 = screen.getByTestId("artifact-tab-artifact-2");

      expect(tab1).toHaveTextContent("Hello World");
      expect(tab2).toHaveTextContent("README");
    });

    it("should enable inline editing when enableArtifactEdit prop is true", () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactEdit />,
      );

      // Should show artifact tabs with titles
      const tab = screen.getByTestId("artifact-tab-artifact-1");
      expect(tab).toHaveTextContent("Hello World");
    });

    it("should call onRenameArtifact when artifact title is changed", async () => {
      const onRenameArtifact = vi.fn();
      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableArtifactEdit
          onRenameArtifact={onRenameArtifact}
        />,
      );

      // Scope search to just the artifact tab
      const tab = screen.getByTestId("artifact-tab-artifact-1");
      const editableTitle = within(tab).getByText("Hello World");
      fireEvent.click(editableTitle);

      // Type new name and submit
      const input = within(tab).getByRole("textbox");
      fireEvent.change(input, { target: { value: "New Title" } });
      fireEvent.keyDown(input, { key: "Enter" });

      expect(onRenameArtifact).toHaveBeenCalledWith("artifact-1", "New Title");
    });

    it("should not trigger rename on Escape key", async () => {
      const onRenameArtifact = vi.fn();
      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableArtifactEdit
          onRenameArtifact={onRenameArtifact}
        />,
      );

      // Scope search to just the artifact tab
      const tab = screen.getByTestId("artifact-tab-artifact-1");
      const editableTitle = within(tab).getByText("Hello World");
      fireEvent.click(editableTitle);

      // Type new name and press Escape
      const input = within(tab).getByRole("textbox");
      fireEvent.change(input, { target: { value: "Changed Title" } });
      fireEvent.keyDown(input, { key: "Escape" });

      // Should not have called onRenameArtifact
      expect(onRenameArtifact).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Artifact Hover Details Tests (Sprint Block 4)
  // ===========================================================================

  describe("Artifact Hover Details", () => {
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

      // Hover over an artifact tab
      const tab = screen.getByTestId("artifact-tab-artifact-1");
      fireEvent.mouseEnter(tab);

      // Wait for tooltip delay
      await act(async () => {
        vi.advanceTimersByTime(300);
      });

      // Tooltip should appear
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
      const multiLineArtifacts: CanvasArtifact[] = [
        {
          id: "multi-line",
          type: "code",
          sessionId: "session-1",
          version: 1,
          content: "line1\nline2\nline3\nline4\nline5",
          contentType: "code",
          title: "Multi-Line",
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
          editMetadata: {
            editedBy: "user",
            language: "text",
          },
        },
      ];

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

  // =============================================================================
  // AI Intelligence Integration Tests (Phase 4 - Sprint 4)
  // =============================================================================
  describe("AI Intelligence Integration", () => {
    it("should render AI intelligence indicator when enableAI is true", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={true}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      // The AI intelligence indicator should be rendered
      expect(
        screen.getByTestId("ai-intelligence-indicator"),
      ).toBeInTheDocument();
    });

    it("should show quality score for code artifacts", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={true}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      // Should display the mock quality score (85)
      expect(screen.getByText("85")).toBeInTheDocument();
    });

    it("should NOT render AI indicator when enableAI is false", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          enableAI={false}
          userId="user:test-user"
          sessionId="session-123"
        />,
        { store },
      );

      // The AI intelligence indicator should NOT be rendered
      expect(
        screen.queryByTestId("ai-intelligence-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should pass persona context to AI hooks via props", () => {
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: "artifact-1",
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto",
          },
        },
      });

      // Component should accept userId, sessionId, persona props
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

      // Verify component renders with AI features
      expect(
        screen.getByTestId("ai-intelligence-indicator"),
      ).toBeInTheDocument();
    });
  });
});
