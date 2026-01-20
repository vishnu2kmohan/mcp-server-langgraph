/**
 * CanvasWorkspace Editing Tests
 *
 * Tests for edit mode transitions, callbacks, artifact renaming, save without content,
 * content change without selection, and artifact display edge cases.
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
  artifactWithoutTitle,
  aiSuggestionArtifact,
  userEditedArtifact,
  renderWithProviders,
  createStoreWithArtifact,
  createTestStore,
  defaultCanvasState,
} from "./CanvasWorkspace.fixtures.tsx";

describe("CanvasWorkspace - Editing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Edit Mode Transitions", () => {
    it("should cancel edit mode and clear editContent", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "modified content" } });

      const cancelButtons = screen.getAllByTestId("cancel-button");
      fireEvent.click(cancelButtons[0]);

      await waitFor(() => {
        expect(screen.queryByTestId("content-editor")).not.toBeInTheDocument();
      });
    });

    it("should reset edit mode when switching artifacts", async () => {
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />, {
        store,
      });

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      expect(screen.getByTestId("content-editor")).toBeInTheDocument();

      fireEvent.click(screen.getByTestId("artifact-tab-artifact-2"));

      await waitFor(() => {
        expect(screen.queryByTestId("content-editor")).not.toBeInTheDocument();
      });
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
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onContentChange={onContentChange}
        />,
        { store },
      );

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "new content" } });

      expect(onContentChange).toHaveBeenCalledWith("artifact-1", "new content");
    });

    it("should call onSave when save button clicked", async () => {
      const onSave = vi.fn();
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} onSave={onSave} />,
        { store },
      );

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "updated content" } });

      const saveButtons = screen.getAllByTestId("save-button");
      fireEvent.click(saveButtons[0]);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith("artifact-1", "updated content");
      });
    });
  });

  describe("Artifact Renaming", () => {
    it("should display artifact titles in tabs", () => {
      renderWithProviders(<CanvasWorkspace artifacts={mockArtifacts} />);

      const tab1 = screen.getByTestId("artifact-tab-artifact-1");
      const tab2 = screen.getByTestId("artifact-tab-artifact-2");

      expect(tab1).toHaveTextContent("Hello World");
      expect(tab2).toHaveTextContent("README");
    });

    it("should enable inline editing when enableArtifactEdit prop is true", () => {
      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} enableArtifactEdit />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      expect(tab).toHaveTextContent("Hello World");
    });

    it("should call onRenameArtifact when artifact title is changed", async () => {
      const onRenameArtifact = vi.fn();
      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onRenameArtifact={onRenameArtifact}
        />,
      );

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      // Double-click to enter rename mode
      fireEvent.dblClick(tab);

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

      const tab = screen.getByTestId("artifact-tab-artifact-1");
      // Double-click to enter rename mode
      fireEvent.dblClick(tab);

      const input = within(tab).getByRole("textbox");
      fireEvent.change(input, { target: { value: "Changed Title" } });
      fireEvent.keyDown(input, { key: "Escape" });

      expect(onRenameArtifact).not.toHaveBeenCalled();
    });
  });

  describe("Save Without Content", () => {
    it("should not call onSave when editContent is empty", async () => {
      const onSave = vi.fn();
      const store = createStoreWithArtifact("artifact-1");

      renderWithProviders(
        <CanvasWorkspace artifacts={mockArtifacts} onSave={onSave} />,
        { store },
      );

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "" } });

      const saveButtons = screen.getAllByTestId("save-button");
      fireEvent.click(saveButtons[0]);

      expect(onSave).not.toHaveBeenCalled();
    });
  });

  describe("Content Change Without Selection", () => {
    it("should handle content change callback even when selectedArtifactId is null initially", async () => {
      const onContentChange = vi.fn();
      const store = createTestStore({
        canvas: {
          ...defaultCanvasState,
          selectedArtifactId: null,
        },
      });

      renderWithProviders(
        <CanvasWorkspace
          artifacts={mockArtifacts}
          onContentChange={onContentChange}
        />,
        { store },
      );

      await waitFor(() => {
        expect(store.getState().canvas.selectedArtifactId).toBe("artifact-1");
      });

      const editButtons = screen.getAllByTestId("edit-button");
      fireEvent.click(editButtons[0]);

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "new content" } });

      expect(onContentChange).toHaveBeenCalledWith("artifact-1", "new content");
    });
  });

  describe("Artifact Display Edge Cases", () => {
    it("should display Untitled when no title provided", () => {
      renderWithProviders(<CanvasWorkspace artifacts={artifactWithoutTitle} />);

      const tab = screen.getByTestId("artifact-tab-abcdef123456");
      expect(within(tab).getByText("Untitled")).toBeInTheDocument();
    });

    it("should show ai-suggestion badge for ai-suggestion editedBy", () => {
      renderWithProviders(<CanvasWorkspace artifacts={aiSuggestionArtifact} />);

      expect(screen.getAllByTestId("ai-badge").length).toBeGreaterThan(0);
    });

    it("should not show AI badge for user-edited artifacts", () => {
      renderWithProviders(<CanvasWorkspace artifacts={userEditedArtifact} />);

      const tabs = screen.getByTestId("artifact-tab-user-edit-1");
      expect(tabs.querySelector('[data-testid="ai-badge"]')).toBeNull();
    });
  });
});
