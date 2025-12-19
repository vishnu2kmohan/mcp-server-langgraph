/**
 * WorkflowDocument Component
 *
 * A workflow builder document for use within the MainDock.
 * Displays workflow canvas with controls and toolbar.
 *
 * Features:
 * - Workflow loading by ID
 * - Save, run, export actions
 * - Undo/redo support
 * - Validation status
 * - Compact mode for docked tabs
 */

import { useEffect, useCallback, useState } from "react";
import { ReactFlowProvider } from "reactflow";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  saveWorkflow,
  executeWorkflow,
  loadWorkflow,
  undo,
  redo,
  selectWorkflowMetadata,
  selectWorkflowNodes,
  selectWorkflowEdges,
  selectIsDirty,
  selectIsSaving,
  selectIsLoading,
  selectValidation,
  selectCanUndo,
  selectCanRedo,
  selectExecutionState,
  selectIsReadOnly,
} from "../../store/slices/workflowSlice";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { NodePalette, type NodeType } from "./NodePalette";
import { NodeInspector } from "./NodeInspector";
import { ExecutionTracePanel } from "./ExecutionTracePanel";
import { addNode } from "../../store/slices/workflowSlice";
import type { WorkflowNodeType } from "../../types/workflow";
import {
  Save,
  Undo,
  Redo,
  Play,
  Download,
  Loader2,
  Lock,
  AlertCircle,
  GitBranch,
} from "lucide-react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface WorkflowDocumentProps {
  /** Workflow ID to display */
  workflowId: string;
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowDocument({
  workflowId,
  compact = false,
  className,
}: WorkflowDocumentProps) {
  const dispatch = useAppDispatch();
  const [validationError, setValidationError] = useState<string | null>(null);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(
    null,
  );

  // Callback for ExecutionTracePanel to highlight nodes on hover
  const handleNodeHighlight = useCallback((nodeId: string | null) => {
    setHighlightedNodeId(nodeId);
  }, []);

  // Redux selectors
  const metadata = useAppSelector(selectWorkflowMetadata);
  const nodes = useAppSelector(selectWorkflowNodes);
  const edges = useAppSelector(selectWorkflowEdges);
  const isDirty = useAppSelector(selectIsDirty);
  const isSaving = useAppSelector(selectIsSaving);
  const isLoading = useAppSelector(selectIsLoading);
  const validation = useAppSelector(selectValidation);
  const canUndo = useAppSelector(selectCanUndo);
  const canRedo = useAppSelector(selectCanRedo);
  const executionState = useAppSelector(selectExecutionState);
  const isReadOnly = useAppSelector(selectIsReadOnly);

  // Load workflow on mount or when workflowId changes
  useEffect(() => {
    if (workflowId && metadata?.id !== workflowId) {
      dispatch(loadWorkflow(workflowId));
    }
  }, [dispatch, workflowId, metadata?.id]);

  const handleSave = useCallback(async () => {
    await dispatch(saveWorkflow());
  }, [dispatch]);

  const handleRun = useCallback(async () => {
    setValidationError(null);
    if (!validation.isValid) {
      setValidationError("Please fix validation errors before running");
      return;
    }
    await dispatch(executeWorkflow());
  }, [dispatch, validation.isValid]);

  const handleExportJSON = useCallback(() => {
    const data = { metadata, nodes, edges };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${metadata?.name || "workflow"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [metadata, nodes, edges]);

  // Empty state
  if (!workflowId) {
    return (
      <div
        data-testid="workflow-document"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-gray-50 dark:bg-gray-900",
          "text-gray-500 dark:text-gray-400",
          compact && "text-sm",
          className,
        )}
      >
        <GitBranch size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No workflow selected</h2>
        <p className="text-sm">Select or create a workflow to get started.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        data-testid="workflow-document"
        className={cn(
          "flex items-center justify-center h-full",
          "bg-gray-50 dark:bg-gray-900",
          className,
        )}
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div
        data-testid="workflow-document"
        className={cn(
          "flex flex-col h-full",
          "bg-gray-50 dark:bg-gray-900",
          compact && "text-sm",
          className,
        )}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <GitBranch size={18} className="text-gray-500" />
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              {metadata?.name || "Workflow"}
              {isDirty && <span className="text-yellow-500 ml-1">*</span>}
            </h2>

            {isReadOnly && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded">
                <Lock size={12} />
                Read-Only
              </span>
            )}

            {!validation.isValid && (
              <span className="text-xs px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded">
                {validation.errors.length} errors
              </span>
            )}

            {validationError && (
              <div className="flex items-center gap-2 px-2 py-1 bg-red-100 dark:bg-red-900/30 rounded text-xs text-red-700 dark:text-red-400">
                <AlertCircle size={12} />
                {validationError}
              </div>
            )}

            {executionState !== "idle" && (
              <span
                className={cn(
                  "text-xs px-2 py-1 rounded",
                  executionState === "running" &&
                    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
                  executionState === "completed" &&
                    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                  executionState === "error" &&
                    "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
                )}
              >
                {executionState}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => dispatch(undo())}
              disabled={!canUndo || isReadOnly}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 rounded"
              title="Undo"
            >
              <Undo size={16} />
            </button>
            <button
              onClick={() => dispatch(redo())}
              disabled={!canRedo || isReadOnly}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 rounded"
              title="Redo"
            >
              <Redo size={16} />
            </button>

            <div className="w-px h-5 bg-gray-300 dark:bg-gray-600 mx-1" />

            <button
              onClick={handleRun}
              disabled={executionState === "running" || !validation.isValid}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              title="Run"
            >
              {executionState === "running" ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              Run
            </button>

            <button
              onClick={handleExportJSON}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200"
              title="Export"
            >
              <Download size={14} />
              Export
            </button>

            <button
              onClick={handleSave}
              disabled={isSaving || !isDirty || isReadOnly}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              title="Save"
            >
              {isSaving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Save
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Node Palette */}
          {!isReadOnly && (
            <NodePalette
              onAddNode={(type: NodeType) => {
                dispatch(addNode(type as WorkflowNodeType, { x: 250, y: 250 }));
              }}
            />
          )}

          {/* Canvas */}
          <div className="flex-1 relative">
            <WorkflowCanvas highlightedNodeId={highlightedNodeId} />
            <NodeInspector />
          </div>

          {/* Execution Trace Panel - collapsible right panel */}
          <div className="w-80 border-l border-gray-200 dark:border-gray-700 overflow-hidden">
            <ExecutionTracePanel onNodeHighlight={handleNodeHighlight} />
          </div>
        </div>
      </div>
    </ReactFlowProvider>
  );
}

export default WorkflowDocument;
