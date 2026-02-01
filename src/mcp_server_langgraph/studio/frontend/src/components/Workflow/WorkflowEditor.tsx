/**
 * WorkflowEditor Component
 *
 * Main workflow editor shell with tabs/split view for visual and code editing.
 * Uses the centralized /validate endpoint (NO JS DUPLICATION).
 *
 * Features:
 * - Tab-based switching between Visual (React Flow) and Code (Monaco) views
 * - Real-time validation via debounced /validate endpoint
 * - Validation errors/warnings panel
 * - Loading states
 *
 * References:
 * - Plan: Chat-to-Workflow Feature
 * - ADR-0089: Prompt Architecture Centralization
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { ReactFlowProvider } from "reactflow";
import {
  Code,
  LayoutGrid,
  Loader2,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import Editor from "@monaco-editor/react";
import { useDispatch, useSelector } from "react-redux";

import { useWorkflowValidation } from "../../hooks/useWorkflowValidation";
import { useGetWorkflowQuery } from "../../api";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { cn } from "../../utils/cn";
import { setNodes, setEdges } from "../../store/slices/workflowSlice";
import type { RootState } from "../../store";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

type EditorView = "visual" | "code";

export interface WorkflowEditorProps {
  /** Workflow ID to edit */
  workflowId: string;
  /** Initial view mode */
  initialView?: EditorView;
  /** Callback when workflow is saved */
  onSave?: () => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowEditor({
  workflowId,
  initialView = "visual",
  onSave: _onSave,
  className,
}: WorkflowEditorProps) {
  const dispatch = useDispatch();
  const [currentView, setCurrentView] = useState<EditorView>(initialView);
  const [codeContent, setCodeContent] = useState<string>("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Ref to track sync direction and prevent infinite loops
  // When true, we're syncing from code to visual - don't sync back
  const isSyncingFromCodeRef = useRef(false);

  // Get nodes/edges from Redux store (updated by React Flow canvas)
  const reduxNodes = useSelector((state: RootState) => state.workflow.nodes);
  const reduxEdges = useSelector((state: RootState) => state.workflow.edges);

  // Fetch workflow data
  const {
    data: workflow,
    isLoading: isLoadingWorkflow,
    error: workflowError,
  } = useGetWorkflowQuery(workflowId);

  // Validation hook with debounced validation
  const {
    validationResult,
    isValidating,
    error: _validationError,
    validate,
  } = useWorkflowValidation({
    debounceMs: 300,
  });

  // Initialize code content from workflow data
  useEffect(() => {
    if (workflow) {
      const workflowJson = JSON.stringify(
        {
          nodes: workflow.nodes,
          edges: workflow.edges,
        },
        null,
        2,
      );
      setCodeContent(workflowJson);
      setParseError(null);
    }
  }, [workflow]);

  // Visual → Code sync: Update Monaco when Redux nodes/edges change
  // This handles changes from React Flow canvas
  useEffect(() => {
    // Skip if we're currently syncing from code (prevents infinite loop)
    if (isSyncingFromCodeRef.current) {
      return;
    }

    // Skip if no nodes and edges (initial state)
    if (reduxNodes.length === 0 && reduxEdges.length === 0) {
      return;
    }

    // Update code content from Redux state
    const workflowJson = JSON.stringify(
      {
        nodes: reduxNodes,
        edges: reduxEdges,
      },
      null,
      2,
    );

    // Only update if actually different (prevents unnecessary re-renders)
    setCodeContent((prev) => {
      if (prev === workflowJson) {
        return prev;
      }
      return workflowJson;
    });
    setParseError(null);
  }, [reduxNodes, reduxEdges]);

  // Trigger validation when workflow changes
  useEffect(() => {
    if (workflowId) {
      validate(workflowId);
    }
  }, [workflowId, validate]);

  // Handle view switch
  const handleViewChange = useCallback((view: EditorView) => {
    setCurrentView(view);
  }, []);

  // Sync code changes to visual canvas (Code → Visual)
  const syncCodeToVisual = useCallback(
    (jsonString: string) => {
      try {
        const parsed = JSON.parse(jsonString);

        // Validate structure
        if (!parsed || typeof parsed !== "object") {
          setParseError("Invalid workflow structure");
          return false;
        }

        const nodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
        const edges = Array.isArray(parsed.edges) ? parsed.edges : [];

        // Set flag to prevent Visual → Code sync from triggering
        isSyncingFromCodeRef.current = true;
        setIsSyncing(true);

        // Dispatch to Redux store to update visual canvas
        dispatch(setNodes(nodes));
        dispatch(setEdges(edges));
        setParseError(null);

        // Clear flag after a short delay to allow Redux update to complete
        setTimeout(() => {
          isSyncingFromCodeRef.current = false;
          setIsSyncing(false);
        }, 50);

        return true;
      } catch (e) {
        const error = e instanceof Error ? e.message : "Invalid JSON";
        setParseError(error);
        isSyncingFromCodeRef.current = false;
        setIsSyncing(false);
        return false;
      }
    },
    [dispatch],
  );

  // Handle code changes in Monaco with bidirectional sync
  const handleCodeChange = useCallback(
    (value: string | undefined) => {
      if (value !== undefined) {
        setCodeContent(value);

        // Attempt to sync to visual canvas
        syncCodeToVisual(value);

        // Trigger validation
        validate(workflowId);
      }
    },
    [workflowId, validate, syncCodeToVisual],
  );

  // Loading state
  if (isLoadingWorkflow) {
    return (
      <div
        data-testid="loading-indicator"
        className={cn(
          "flex items-center justify-center h-full",
          "bg-neutral-1",
          className,
        )}
      >
        <Loader2 size={24} className="animate-spin text-neutral-9" />
      </div>
    );
  }

  // Error state
  if (workflowError) {
    return (
      <div
        data-testid="error-state"
        className={cn(
          "flex items-center justify-center h-full",
          "bg-neutral-1",
          className,
        )}
      >
        <div className="text-center">
          <AlertCircle size={32} className="mx-auto mb-2 text-error-9" />
          <p className="text-neutral-10">Failed to load workflow</p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="workflow-editor"
      className={cn("flex flex-col h-full bg-neutral-1", className)}
    >
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b border-neutral-5 px-4 py-2">
        <h2 className="text-sm font-medium text-neutral-12 truncate">
          {workflow?.name || "Untitled Workflow"}
        </h2>

        {/* View tabs */}
        <div className="flex items-center gap-1 bg-neutral-2 rounded-md p-0.5">
          <Button
            variant="ghost"
            data-testid="visual-tab"
            data-active={currentView === "visual"}
            type="button"
            onClick={() => handleViewChange("visual")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium",
              "transition-colors",
              currentView === "visual"
                ? "bg-neutral-1 text-neutral-12 shadow-sm"
                : "text-neutral-10 hover:text-neutral-11",
            )}
          >
            <LayoutGrid size={12} />
            Visual
          </Button>
          <Button
            variant="ghost"
            data-testid="code-tab"
            data-active={currentView === "code"}
            type="button"
            onClick={() => handleViewChange("code")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium",
              "transition-colors",
              currentView === "code"
                ? "bg-neutral-1 text-neutral-12 shadow-sm"
                : "text-neutral-10 hover:text-neutral-11",
            )}
          >
            <Code size={12} />
            Code
          </Button>
        </div>
      </div>
      {/* Sync status bar */}
      {isSyncing && (
        <div
          data-testid="sync-status"
          className="flex items-center gap-2 px-4 py-1.5 bg-insight-1 dark:bg-insight-a3 border-b border-insight-4 dark:border-insight-11"
        >
          <RefreshCw size={12} className="animate-spin text-insight-9" />
          <span className="text-xs text-insight-10 dark:text-insight-9">
            Syncing...
          </span>
        </div>
      )}
      {/* Parse error indicator */}
      {parseError && (
        <div
          data-testid="parse-error"
          className="flex items-center gap-2 px-4 py-1.5 bg-grafana-1 dark:bg-grafana-12/20 border-b border-grafana-3 dark:border-grafana-11"
        >
          <AlertCircle size={12} className="text-grafana-9" />
          <span className="text-xs text-grafana-10 dark:text-grafana-5">
            JSON Error: {parseError}
          </span>
        </div>
      )}
      {/* Validation status bar */}
      {isValidating && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-primary-1 dark:bg-primary-a3 border-b border-primary-4 dark:border-primary-11">
          <Loader2 size={12} className="animate-spin text-primary-9" />
          <span className="text-xs text-primary-10 dark:text-primary-7">
            Validating...
          </span>
        </div>
      )}
      {/* Validation errors */}
      {validationResult &&
        !validationResult.valid &&
        validationResult.errors.length > 0 && (
          <div
            data-testid="validation-errors"
            className="px-4 py-2 bg-error-1 dark:bg-error-a3 border-b border-error-4 dark:border-error-11"
          >
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle size={12} className="text-error-9" />
              <span className="text-xs font-medium text-error-10 dark:text-error-7">
                Validation Errors
              </span>
            </div>
            <ul className="text-xs text-error-10 dark:text-error-7 space-y-0.5 pl-4">
              {validationResult.errors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </div>
        )}
      {/* Validation warnings */}
      {validationResult && validationResult.warnings.length > 0 && (
        <div
          data-testid="validation-warnings"
          className="px-4 py-2 bg-warning-3 bg-warning-3 border-b border-warning-6 dark:border-warning-11"
        >
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={12} className="text-warning-9" />
            <span className="text-xs font-medium text-warning-9 dark:text-warning-9">
              Warnings
            </span>
          </div>
          <ul className="text-xs text-warning-9 dark:text-warning-9 space-y-0.5 pl-4">
            {validationResult.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
      {/* Editor content */}
      <div className="flex-1 overflow-hidden">
        {currentView === "visual" ? (
          <ReactFlowProvider>
            <WorkflowCanvas />
          </ReactFlowProvider>
        ) : (
          <div data-testid="code-editor" className="h-full">
            <Editor
              height="100%"
              defaultLanguage="json"
              value={codeContent}
              onChange={handleCodeChange}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                wordWrap: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowEditor;
