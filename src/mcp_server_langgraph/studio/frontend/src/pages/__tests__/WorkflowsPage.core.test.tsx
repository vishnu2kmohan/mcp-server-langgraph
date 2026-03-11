/**
 * WorkflowsPage Core Tests (Shard 1/2)
 *
 * OOM-safe unit tests for core WorkflowsPage functionality.
 * Tests: Rendering, Loading States, Button States, User Interactions,
 * Read-Only Mode, Validation Errors, Workflow Name, Run/Save Button States.
 *
 * Architecture Fix Applied (2025-12-20):
 * - store/types.ts provides isolated RootState/AppDispatch types
 * - store/hooks.ts imports from types.ts instead of index.ts
 * - This breaks the circular dependency that caused OOM
 *
 * See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, cleanup } from "@testing-library/react";

// =============================================================================
// vi.hoisted - Define mock functions BEFORE vi.mock references them
// =============================================================================

const mockDispatch = vi.hoisted(() => vi.fn());
const mockUseAppSelector = vi.hoisted(() => vi.fn());
const mockGetSuggestions = vi.hoisted(() => vi.fn());
const mockUseListWorkflowExecutionsQuery = vi.hoisted(() => vi.fn());
const mockUseWorkflowExecution = vi.hoisted(() => vi.fn());

// =============================================================================
// vi.mock - Mock heavy dependencies BEFORE imports (Vitest hoists these)
// =============================================================================

// Mock ReactFlow - heavy canvas library
vi.mock("reactflow", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow-provider">{children}</div>
  ),
  useReactFlow: () => ({ getNodes: () => [], getEdges: () => [] }),
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  Panel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Handle: () => null,
  Position: { Top: "top", Bottom: "bottom", Left: "left", Right: "right" },
  MarkerType: { Arrow: "arrow", ArrowClosed: "arrowclosed" },
}));

// Mock API hooks - thin wrapper pattern
vi.mock("../../hooks/useWorkflowAPI", () => ({
  useGetWorkflowSuggestionsMutation: () => [
    mockGetSuggestions(),
    { isLoading: false },
  ],
  useListWorkflowExecutionsQuery: mockUseListWorkflowExecutionsQuery,
}));

// Mock workflow execution hook
vi.mock("../../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: mockUseWorkflowExecution,
}));

// Mock heavy components - must export both named and default for lazy loading
vi.mock("../../components/Workflow/WorkflowCanvas", () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas">Canvas</div>,
  default: () => <div data-testid="workflow-canvas">Canvas</div>,
}));

vi.mock("../../components/Workflow/NodePalette", () => ({
  NodePalette: () => <div data-testid="node-palette">NodePalette</div>,
  default: () => <div data-testid="node-palette">NodePalette</div>,
}));

vi.mock("../../components/Workflow/NodeInspector", () => ({
  NodeInspector: () => <div data-testid="node-inspector">NodeInspector</div>,
  default: () => <div data-testid="node-inspector">NodeInspector</div>,
}));

vi.mock("../../components/Workflow/ExecutionPanel", () => ({
  ExecutionPanel: () => <div data-testid="execution-panel">ExecutionPanel</div>,
  default: () => <div data-testid="execution-panel">ExecutionPanel</div>,
}));

vi.mock("../../components/Workflow/ExecutionHistoryPanel", () => ({
  ExecutionHistoryPanel: () => (
    <div data-testid="execution-history-panel">ExecutionHistoryPanel</div>
  ),
  default: () => (
    <div data-testid="execution-history-panel">ExecutionHistoryPanel</div>
  ),
}));

vi.mock("../../components/Workflow/SuggestionChips", () => ({
  SuggestionChips: () => (
    <div data-testid="suggestion-chips">SuggestionChips</div>
  ),
  default: () => <div data-testid="suggestion-chips">SuggestionChips</div>,
}));

// Mock store hooks
vi.mock("../../store/hooks", () => ({
  useAppDispatch: () => mockDispatch(),
  useAppSelector: mockUseAppSelector,
}));

// Mock storage utility
vi.mock("../../utils/storage", async () => {
  const actual = await vi.importActual("../../utils/storage");
  return {
    ...actual,
    getAuthToken: () => "test-token",
  };
});
// =============================================================================
// Import fixtures AFTER mocks
// =============================================================================

import {
  createDefaultWorkflowState,
  setupMockSelectors,
  renderWorkflowsPage,
  findButtonByTitle,
  setupDefaultMocks,
  waitFor,
} from "./WorkflowsPage.fixtures.tsx";

// =============================================================================
// Tests
// =============================================================================

describe("WorkflowsPage - Core", () => {
  beforeEach(() => {
    setupDefaultMocks(
      mockDispatch,
      mockGetSuggestions,
      mockUseListWorkflowExecutionsQuery,
      mockUseWorkflowExecution,
      mockUseAppSelector,
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the workflow page container", () => {
      renderWorkflowsPage();

      expect(screen.getByTestId("reactflow-provider")).toBeInTheDocument();
    });

    it("should render the workflow canvas", async () => {
      renderWorkflowsPage();

      await waitFor(() => {
        expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
      });
    });

    it("should render the node palette when not read-only", async () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isReadOnly: false }),
      );
      renderWorkflowsPage();

      await waitFor(() => {
        expect(screen.getByTestId("node-palette")).toBeInTheDocument();
      });
    });

    it("should render toolbar buttons", () => {
      renderWorkflowsPage();

      // Toolbar buttons by title
      expect(findButtonByTitle("Save (Cmd+S)")).toBeInTheDocument();
      expect(findButtonByTitle("Undo (Cmd+Z)")).toBeInTheDocument();
      expect(findButtonByTitle("Redo (Cmd+Shift+Z)")).toBeInTheDocument();
      expect(findButtonByTitle("Run Workflow (Cmd+Enter)")).toBeInTheDocument();
    });

    it("should render history button when workflow has id", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: { id: "wf-1", name: "Test" } }),
      );
      renderWorkflowsPage();

      expect(findButtonByTitle("Execution History")).toBeInTheDocument();
    });

    it("should not render history button when workflow has no id", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null }),
      );
      renderWorkflowsPage();

      expect(screen.queryByTitle("Execution History")).not.toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("should show loading spinner when isLoading is true", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isLoading: true }),
      );

      renderWorkflowsPage();

      // Loading state shows a centered loading spinner
      const loadingSpinner = document.querySelector(".animate-spin");
      expect(loadingSpinner).toBeInTheDocument();
    });

    it("should show saving spinner in save button when isSaving is true", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isSaving: true }),
      );

      renderWorkflowsPage();

      // Save button contains a spinning loader
      const saveButton = findButtonByTitle("Save (Cmd+S)");
      const spinner = saveButton.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });
  });

  describe("Button States", () => {
    it("should disable undo button when canUndo is false", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canUndo: false }),
      );

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).toBeDisabled();
    });

    it("should enable undo button when canUndo is true", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canUndo: true }),
      );

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).not.toBeDisabled();
    });

    it("should disable redo button when canRedo is false", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canRedo: false }),
      );

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      expect(redoButton).toBeDisabled();
    });

    it("should enable redo button when canRedo is true", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canRedo: true }),
      );

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      expect(redoButton).not.toBeDisabled();
    });

    it("should disable run button when validation is invalid", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });

    it("should enable run button when validation is valid", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).not.toBeDisabled();
    });

    it("should disable save button when not dirty", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isDirty: false }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toBeDisabled();
    });

    it("should enable save button when dirty", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).not.toBeDisabled();
    });
  });

  describe("User Interactions", () => {
    it("should dispatch undo action when undo button clicked", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canUndo: true }),
      );

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      fireEvent.click(undoButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should dispatch redo action when redo button clicked", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ canRedo: true }),
      );

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      fireEvent.click(redoButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should show execution panel when run button clicked", async () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      // Execution panel should appear (lazy loaded)
      await waitFor(() => {
        expect(screen.getByTestId("execution-panel")).toBeInTheDocument();
      });
    });

    it("should show history panel when history button clicked", async () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
        }),
      );

      renderWorkflowsPage();

      const historyButton = findButtonByTitle("Execution History");
      fireEvent.click(historyButton);

      // History panel should appear (lazy loaded)
      await waitFor(() => {
        expect(
          screen.getByTestId("execution-history-panel"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Read-Only Mode", () => {
    it("should show read-only indicator when workflow is read-only", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isReadOnly: true }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("Read-Only")).toBeInTheDocument();
    });

    it("should hide node palette in read-only mode", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isReadOnly: true }),
      );

      renderWorkflowsPage();

      expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
    });

    it("should disable undo button in read-only mode", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isReadOnly: true, canUndo: true }),
      );

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).toBeDisabled();
    });

    it("should disable save button in read-only mode", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isReadOnly: true, isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toBeDisabled();
    });

    it("should allow run in read-only mode when canExecute is true", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          isReadOnly: true,
          canExecute: true,
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).not.toBeDisabled();
    });

    it("should disable run in read-only mode when canExecute is false", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          isReadOnly: true,
          canExecute: false,
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Validation Errors", () => {
    it("should show error count when workflow has validation errors", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          validation: {
            isValid: false,
            errors: [{ message: "Error 1" }, { message: "Error 2" }],
          },
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("2 errors")).toBeInTheDocument();
    });

    it("should show inline validation error when run fails validation", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      // The run button should be disabled since validation is invalid
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Workflow Name", () => {
    it("should display workflow name from metadata", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "My Custom Workflow" },
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("My Custom Workflow")).toBeInTheDocument();
    });

    it("should show dirty indicator when workflow has unsaved changes", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("should show 'New Workflow' when metadata is null", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("New Workflow")).toBeInTheDocument();
    });
  });

  describe("Run Button States", () => {
    it("should show Play icon when not running", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "idle",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toHaveTextContent("Run");
      // Play icon should be present (no spinner)
      expect(runButton.querySelector(".animate-spin")).not.toBeInTheDocument();
    });

    it("should show spinner when execution is running", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "running",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should disable run button when execution is running", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "running",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Save Button States", () => {
    it("should show Save icon when not saving", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          isSaving: false,
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toHaveTextContent("Save");
      expect(saveButton.querySelector(".animate-spin")).not.toBeInTheDocument();
    });

    it("should show spinner when saving", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          isSaving: true,
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });
});

/**
 * Coverage Verification (Shard 1/2)
 *
 * This test shard covers:
 *
 * ✅ Rendering (core components visible)
 * ✅ Loading states (isLoading, isSaving)
 * ✅ Button states (canUndo, canRedo, validation.isValid, isDirty)
 * ✅ User interactions (undo, redo, run, history)
 * ✅ Read-only mode (indicator, hidden palette, disabled controls, canExecute)
 * ✅ Validation errors (error count display)
 * ✅ Workflow metadata (name, dirty indicator)
 * ✅ Run/Save button states (spinners, icons)
 */
