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

import { Button } from "@/components/UI";

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
          "bg-neutral-1",
          "text-neutral-10",
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
          "bg-neutral-1",
          className,
        )}
      >
        <Loader2 className="w-8 h-8 animate-spin text-primary-9" />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div
        data-testid="workflow-document"
        className={cn(
          "flex flex-col h-full",
          "bg-neutral-1",
          compact && "text-sm",
          className,
        )}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-neutral-1 border-b border-neutral-5">
          <div className="flex items-center gap-3">
            <GitBranch size={18} className="text-neutral-10" />
            <h2 className="text-base font-semibold text-neutral-12">
              {metadata?.name || "Workflow"}
              {isDirty && <span className="text-warning-9 ml-1">*</span>}
            </h2>

            {isReadOnly && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 bg-neutral-2 text-neutral-11 rounded">
                <Lock size={12} />
                Read-Only
              </span>
            )}

            {!validation.isValid && (
              <span className="text-xs px-2 py-1 bg-error-3 text-error-11 bg-error-4 dark:text-error-7 rounded">
                {validation.errors.length} errors
              </span>
            )}

            {validationError && (
              <div className="flex items-center gap-2 px-2 py-1 bg-error-3 bg-error-4 rounded text-xs text-error-11 dark:text-error-7">
                <AlertCircle size={12} />
                {validationError}
              </div>
            )}

            {executionState !== "idle" && (
              <span
                className={cn(
                  "text-xs px-2 py-1 rounded",
                  executionState === "running" &&
                    "bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7",
                  executionState === "completed" &&
                    "bg-success-3 text-success-11 bg-success-4 dark:text-success-7",
                  executionState === "error" &&
                    "bg-error-3 text-error-11 bg-error-4 dark:text-error-7",
                )}
              >
                {executionState}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded"
              onClick={() => dispatch(undo())}
              disabled={!canUndo || isReadOnly}
              title="Undo"
            >
              <Undo size={16} />
            </Button>
            <Button
              variant="primary"
              className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded"
              onClick={() => dispatch(redo())}
              disabled={!canRedo || isReadOnly}
              title="Redo"
            >
              <Redo size={16} />
            </Button>

            <div className="w-px h-5 bg-neutral-3 mx-1" />

            <Button
              variant="success"
              size="sm"
              className="flex .5 px-2.5 py-1.5 text-xs bg-success-10 text-neutral-12 rounded hover:bg-success-11"
              onClick={handleRun}
              disabled={executionState === "running" || !validation.isValid}
              title="Run"
            >
              {executionState === "running" ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              Run
            </Button>

            <Button
              variant="secondary"
              size="sm"
              className="flex .5 px-2.5 py-1.5 text-xs bg-neutral-2 text-neutral-11 rounded hover:bg-neutral-3"
              onClick={handleExportJSON}
              title="Export"
            >
              <Download size={14} />
              Export
            </Button>

            <Button
              variant="primary"
              size="sm"
              className="flex .5 px-2.5 py-1.5 text-xs bg-primary-10 text-neutral-12 rounded hover:bg-primary-11"
              onClick={handleSave}
              disabled={isSaving || !isDirty || isReadOnly}
              title="Save"
            >
              {isSaving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Save size={14} />
              )}
              Save
            </Button>
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
          <div className="w-80 border-l border-neutral-5 overflow-hidden">
            <ExecutionTracePanel onNodeHighlight={handleNodeHighlight} />
          </div>
        </div>
      </div>
    </ReactFlowProvider>
  );
}

export default WorkflowDocument;
