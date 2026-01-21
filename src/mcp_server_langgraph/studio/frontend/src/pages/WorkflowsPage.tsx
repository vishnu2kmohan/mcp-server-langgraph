/**
 * WorkflowsPage
 *
 * Visual workflow builder page using React Flow for the canvas.
 * Integrates Redux workflow slice for state management.
 */

import { useCallback, useState, useEffect, lazy, Suspense } from "react";
import { useReducedMotion } from "motion/react";
import { PAGE_CLASSES } from "../constants/layout";
import { useSearchParams, useNavigate } from "react-router";
import { ReactFlowProvider } from "reactflow";
import { cn } from "../utils/cn";
// Direct imports to avoid Rollup circular dependency warnings
import { Skeleton } from "../components/UI/Skeleton";
import { Dialog } from "../components/UI/Dialog";
import { Button } from "../components/UI/Button";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  createWorkflow,
  saveWorkflow,
  executeWorkflow,
  loadWorkflow,
  addNode,
  undo,
  redo,
  validate,
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
  selectCanExecute,
} from "../store/slices/workflowSlice";
import type { WorkflowNodeType } from "../types/workflow";
import type { NodeType } from "../components/Workflow/NodePalette";
import type { WorkflowExecution } from "../components/Workflow/ExecutionHistoryPanel";

// Lazy load heavy ReactFlow components for better initial page load
const WorkflowCanvas = lazy(() =>
  import("../components/Workflow/WorkflowCanvas").then((m) => ({
    default: m.WorkflowCanvas,
  }))
);
const NodePalette = lazy(() =>
  import("../components/Workflow/NodePalette").then((m) => ({
    default: m.NodePalette,
  }))
);
const NodeInspector = lazy(() =>
  import("../components/Workflow/NodeInspector").then((m) => ({
    default: m.NodeInspector,
  }))
);
const ExecutionPanel = lazy(() =>
  import("../components/Workflow/ExecutionPanel").then((m) => ({
    default: m.ExecutionPanel,
  }))
);
const ExecutionHistoryPanel = lazy(() =>
  import("../components/Workflow/ExecutionHistoryPanel").then((m) => ({
    default: m.ExecutionHistoryPanel,
  }))
);
const SuggestionChips = lazy(() =>
  import("../components/Workflow/SuggestionChips").then((m) => ({
    default: m.SuggestionChips,
  }))
);
const WorkflowVersionHistory = lazy(() =>
  import("../components/Workflow/WorkflowVersionHistory").then((m) => ({
    default: m.WorkflowVersionHistory,
  }))
);
const ShareWorkflowDialog = lazy(() =>
  import("../components/Workflow/ShareWorkflowDialog").then((m) => ({
    default: m.ShareWorkflowDialog,
  }))
);
import { useWorkflowExecution } from "../hooks/useWorkflowExecution";
import {
  useGetWorkflowSuggestionsMutation,
  useListWorkflowExecutionsQuery,
} from "../hooks/useWorkflowAPI";
import type { AISuggestion } from "../types/api";
import {
  Save,
  Undo,
  Redo,
  Code,
  Download,
  Play,
  Loader2,
  Lock,
  AlertCircle,
  X,
  Wifi,
  WifiOff,
  RefreshCw,
  Lightbulb,
  History,
  GitBranch,
  Share2,
} from "lucide-react";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

export function WorkflowsPage() {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  const [isGeneratingCode, setIsGeneratingCode] = useState(false);
  const [showExecutionPanel, setShowExecutionPanel] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  // AI Suggestions state
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
  // Version history and sharing dialogs (Phase 3 workflow features)
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showShareDialog, setShowShareDialog] = useState(false);
  // Execution history pagination state
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(
    null,
  );
  const [executionsCursor, setExecutionsCursor] = useState<
    string | undefined
  >();
  const [accumulatedExecutions, setAccumulatedExecutions] = useState<
    WorkflowExecution[]
  >([]);
  const [searchParams] = useSearchParams();
  const workflowIdFromUrl = searchParams.get("id");
  const suggestionsFromUrl = searchParams.get("suggestions") === "true";
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  // Auth failure handler for authenticatedFetch
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // AI Suggestions mutation
  const [getSuggestions, { isLoading: isLoadingSuggestions }] =
    useGetWorkflowSuggestionsMutation();

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
  const canExecute = useAppSelector(selectCanExecute);

  // Execution history query - only fetch when panel is visible and workflow has ID
  const {
    data: executionsData,
    isLoading: isLoadingExecutions,
    isFetching,
  } = useListWorkflowExecutionsQuery(
    {
      workflow_id: metadata?.id ?? "",
      limit: 20,
      cursor: executionsCursor,
    },
    { skip: !metadata?.id || !showHistoryPanel },
  );

  // Accumulate executions when new data arrives (for pagination)
  // RTK Query transformResponse already converts to camelCase
  useEffect(() => {
    if (executionsData?.items) {
      if (!executionsCursor) {
        // First page - replace all
        setAccumulatedExecutions(executionsData.items);
      } else {
        // Subsequent pages - append (avoid duplicates)
        setAccumulatedExecutions((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          const newItems = executionsData.items.filter(
            (item) => !existingIds.has(item.id),
          );
          return [...prev, ...newItems];
        });
      }
    }
  }, [executionsData?.items, executionsCursor]);

  // Reset accumulated executions when workflow changes or panel closes
  useEffect(() => {
    if (!showHistoryPanel || !metadata?.id) {
      setAccumulatedExecutions([]);
      setExecutionsCursor(undefined);
      setSelectedExecutionId(null);
    }
  }, [showHistoryPanel, metadata?.id]);

  // Handle execution selection
  const handleSelectExecution = useCallback((execution: WorkflowExecution) => {
    setSelectedExecutionId(execution.id);
    // Show execution panel with the selected execution's output/logs
    setShowExecutionPanel(true);
  }, []);

  // Handle load more (pagination)
  const handleLoadMoreExecutions = useCallback(() => {
    if (executionsData?.nextCursor && !isFetching) {
      setExecutionsCursor(executionsData.nextCursor);
    }
  }, [executionsData?.nextCursor, isFetching]);

  // Real-time WebSocket updates for workflow execution
  // Only connect when we have a workflow and the execution panel is visible
  const { connectionStatus, reconnectAttempts, stopExecution, reconnect } =
    useWorkflowExecution(metadata?.id ?? "", {
      autoConnect: showExecutionPanel && !!metadata?.id,
    });

  // Load workflow from URL param on mount
  useEffect(() => {
    if (workflowIdFromUrl && !isLoading && metadata?.id !== workflowIdFromUrl) {
      dispatch(loadWorkflow(workflowIdFromUrl));
    }
  }, [dispatch, workflowIdFromUrl, isLoading, metadata?.id]);

  // Show suggestions panel if URL param is set
  useEffect(() => {
    if (suggestionsFromUrl) {
      setShowSuggestions(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch suggestions when workflow has nodes
  const handleRefreshSuggestions = useCallback(async () => {
    if (nodes.length === 0) {
      setSuggestionsError("Add some nodes to get AI suggestions");
      return;
    }

    setSuggestionsError(null);
    try {
      const result = await getSuggestions({
        workflow: { nodes, edges },
        max_suggestions: 5,
        confidence_threshold: 0.6,
      }).unwrap();
      setSuggestions(result.suggestions);
    } catch (error) {
      setSuggestionsError("Failed to fetch suggestions");
      console.error("Failed to fetch suggestions:", error);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  // Handle applying a suggestion
  const handleApplySuggestion = useCallback(
    (suggestion: AISuggestion) => {
      const meta = suggestion.metadata;

      // Handle different suggestion types
      switch (suggestion.type) {
        case "add_node": {
          // Extract node type and position from metadata
          const nodeType = (meta.nodeType as WorkflowNodeType) ?? "custom";
          const position = (meta.position as { x: number; y: number }) ?? {
            x: 250 + nodes.length * 50,
            y: 250,
          };
          const label = meta.label as string | undefined;
          dispatch(addNode(nodeType, position, label));
          break;
        }
        case "connect_nodes": {
          // Extract source and target from metadata
          const sourceId = meta.sourceId as string | undefined;
          const targetId = meta.targetId as string | undefined;
          if (sourceId && targetId) {
            dispatch({
              type: "workflow/addEdge",
              payload: {
                edgeId: `edge-${Date.now()}`,
                sourceId,
                targetId,
              },
            });
          }
          break;
        }
        case "update_config": {
          // For config updates, we'd need to select the node first
          // This is informational - user can apply manually
          break;
        }
        default:
          // Unknown suggestion type - just dismiss
          break;
      }

      // Remove the applied suggestion from the list
      setSuggestions((prev) => prev.filter((s) => s !== suggestion));
    },
    [dispatch, nodes.length],
  );

  // Handle dismissing a suggestion
  const handleDismissSuggestion = useCallback((suggestion: AISuggestion) => {
    setSuggestions((prev) => prev.filter((s) => s !== suggestion));
  }, []);

  const handleSave = useCallback(async () => {
    if (!metadata) {
      // Create new workflow if none exists
      dispatch(
        createWorkflow({
          name: "New Workflow",
          description: "Created in visual builder",
        }),
      );
    }
    await dispatch(saveWorkflow());
  }, [dispatch, metadata]);

  const handleGenerateCode = useCallback(async () => {
    setIsGeneratingCode(true);
    setValidationError(null);
    try {
      // Validate first
      dispatch(validate());
      if (!validation.isValid) {
        setValidationError(
          "Please fix validation errors before generating code",
        );
        return;
      }

      const response = await authenticatedFetch("/api/v1/workflows/generate", {
        method: "POST",
        body: JSON.stringify({
          name: metadata?.name || "Workflow",
          nodes,
          edges,
        }),
        onAuthFailure: handleAuthFailure,
      });

      if (response.ok) {
        const data = await response.json();
        // Create blob and download
        const blob = new Blob([data.code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename || "workflow.py";
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Failed to generate code:", error);
    } finally {
      setIsGeneratingCode(false);
    }
  }, [dispatch, metadata, nodes, edges, validation.isValid, handleAuthFailure]);

  const handleExportJSON = useCallback(() => {
    const data = {
      metadata,
      nodes,
      edges,
    };
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

  const handleRun = useCallback(async () => {
    setValidationError(null);
    if (!validation.isValid) {
      setValidationError("Please fix validation errors before running");
      return;
    }
    setShowExecutionPanel(true);
    await dispatch(executeWorkflow());
  }, [dispatch, validation.isValid]);

  if (isLoading) {
    return (
      <div className={PAGE_CLASSES.shellLoading}>
        <Loader2 className={cn("w-8 h-8 text-primary-9", !prefersReducedMotion && "animate-spin")} />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className={PAGE_CLASSES.shell}>
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-neutral-1 border-b border-neutral-5">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-neutral-12">
              {metadata?.name || "New Workflow"}
              {isDirty && <span className="text-warning-9 ml-1">*</span>}
            </h1>

            {isReadOnly && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 bg-neutral-2 text-neutral-11 rounded">
                <Lock size={12} />
                Read-Only
              </span>
            )}

            {!validation.isValid && (
              <span className="text-xs px-2 py-1 bg-error-3 text-error-11 rounded">
                {validation.errors.length} errors
              </span>
            )}

            {/* Inline validation error alert */}
            {validationError && (
              <div
                role="alert"
                className="flex items-center gap-2 px-3 py-1.5 bg-error-3 border border-error-4 rounded-lg"
              >
                <AlertCircle size={14} className="text-error-9" />
                <span className="text-sm text-error-11">
                  {validationError}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setValidationError(null)}
                  aria-label="Dismiss"
                >
                  <X size={14} />
                </Button>
              </div>
            )}

            {executionState !== "idle" && (
              <span
                className={`
                  text-xs px-2 py-1 rounded
                  ${executionState === "running" ? "bg-primary-3 text-primary-11" : ""}
                  ${executionState === "completed" ? "bg-success-3 text-success-11" : ""}
                  ${executionState === "error" ? "bg-error-3 text-error-11" : ""}
                `}
              >
                {executionState}
              </span>
            )}

            {/* Connection Status Indicator - shown when execution panel is visible */}
            {showExecutionPanel && (
              <div
                data-testid="connection-status"
                title={`Connection: ${connectionStatus}${reconnectAttempts > 0 ? ` (attempt ${reconnectAttempts})` : ""}`}
                className={`
                  flex items-center gap-1 text-xs px-2 py-1 rounded
                  ${connectionStatus === "connected" ? "bg-success-3 text-success-11" : ""}
                  ${connectionStatus === "connecting" ? "bg-warning-3 text-warning-11" : ""}
                  ${connectionStatus === "reconnecting" ? "bg-grafana-2 text-grafana-11" : ""}
                  ${connectionStatus === "disconnected" || connectionStatus === "error" ? "bg-error-3 text-error-11" : ""}
                `}
              >
                {connectionStatus === "connected" && <Wifi size={12} />}
                {connectionStatus === "connecting" && (
                  <Loader2 size={12} className={cn(!prefersReducedMotion && "animate-spin")} />
                )}
                {connectionStatus === "reconnecting" && (
                  <>
                    <RefreshCw size={12} className={cn(!prefersReducedMotion && "animate-spin")} />
                    <span>{reconnectAttempts}</span>
                  </>
                )}
                {(connectionStatus === "disconnected" ||
                  connectionStatus === "error") && <WifiOff size={12} />}
              </div>
            )}

            {/* Reconnect button - shown when disconnected or error */}
            {showExecutionPanel &&
              (connectionStatus === "disconnected" ||
                connectionStatus === "error") && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={reconnect}
                >
                  <RefreshCw size={12} />
                  Reconnect
                </Button>
              )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => dispatch(undo())}
              disabled={!canUndo || isReadOnly}
              title="Undo (Cmd+Z)"
            >
              <Undo size={18} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => dispatch(redo())}
              disabled={!canRedo || isReadOnly}
              title="Redo (Cmd+Shift+Z)"
            >
              <Redo size={18} />
            </Button>

            <div className="w-px h-6 bg-neutral-3 mx-2" />

            <Button
              variant="success"
              onClick={handleRun}
              disabled={
                executionState === "running" ||
                !validation.isValid ||
                (isReadOnly && !canExecute)
              }
              title="Run Workflow (Cmd+Enter)"
            >
              {executionState === "running" ? (
                <Loader2 size={16} className={cn(!prefersReducedMotion && "animate-spin")} />
              ) : (
                <Play size={16} />
              )}
              Run
            </Button>

            <Button
              variant="secondary"
              onClick={handleGenerateCode}
              disabled={isGeneratingCode}
            >
              <Code size={16} />
              Generate Code
            </Button>

            <Button
              variant="ghost"
              onClick={() => {
                setShowSuggestions(!showSuggestions);
                if (!showSuggestions && suggestions.length === 0) {
                  handleRefreshSuggestions();
                }
              }}
              title="AI Suggestions"
              data-testid="ai-suggestions-toggle"
            >
              <Lightbulb size={16} />
              AI Suggest
            </Button>

            {/* History button - only shown when workflow has ID */}
            {metadata?.id && (
              <Button
                variant="ghost"
                onClick={() => setShowHistoryPanel(!showHistoryPanel)}
                title="Execution History"
              >
                <History size={16} />
                History
              </Button>
            )}

            {/* Version History button - only shown when workflow has ID */}
            {metadata?.id && (
              <Button
                variant="ghost"
                onClick={() => setShowVersionHistory(true)}
                title="Version History"
                data-testid="version-history-button"
              >
                <GitBranch size={16} />
                Versions
              </Button>
            )}

            {/* Share button - only shown when workflow has ID */}
            {metadata?.id && (
              <Button
                variant="ghost"
                onClick={() => setShowShareDialog(true)}
                title="Share Workflow"
                data-testid="share-workflow-button"
              >
                <Share2 size={16} />
                Share
              </Button>
            )}

            <Button
              variant="secondary"
              onClick={handleExportJSON}
            >
              <Download size={16} />
              Export JSON
            </Button>

            <Button
              variant="primary"
              onClick={handleSave}
              disabled={isSaving || !isDirty || isReadOnly}
              title="Save (Cmd+S)"
            >
              {isSaving ? (
                <Loader2 size={16} className={cn(!prefersReducedMotion && "animate-spin")} />
              ) : (
                <Save size={16} />
              )}
              Save
            </Button>
          </div>
        </div>

        {/* Main Content Area - Lazy loaded for better initial page load */}
        <Suspense
          fallback={
            <div className="flex flex-1 overflow-hidden relative">
              {/* Node Palette skeleton */}
              {!isReadOnly && (
                <div className="w-56 border-r border-neutral-5 bg-neutral-1 p-4">
                  <Skeleton className="h-6 w-32 mb-4" />
                  <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                </div>
              )}
              {/* Canvas skeleton */}
              <div className="flex-1 relative bg-neutral-2">
                <Skeleton className="absolute inset-4" />
              </div>
            </div>
          }
        >
          <div className="flex flex-1 overflow-hidden relative">
            {/* Node Palette - Left Sidebar */}
            {!isReadOnly && (
              <NodePalette
                onAddNode={(type: NodeType) => {
                  // Add node at center of canvas when clicked
                  dispatch(addNode(type as WorkflowNodeType, { x: 250, y: 250 }));
                }}
              />
            )}

            {/* Canvas Area */}
            <div className="flex-1 relative">
              <WorkflowCanvas />
              {/* Node Inspector - Floating Panel */}
              <NodeInspector />
              {/* AI Suggestions - Floating Panel */}
              {showSuggestions && (
                <div className="absolute bottom-4 right-4 w-80 z-10">
                  <SuggestionChips
                    suggestions={suggestions}
                    isLoading={isLoadingSuggestions}
                    error={suggestionsError}
                    onApply={handleApplySuggestion}
                    onDismiss={handleDismissSuggestion}
                    onRefresh={handleRefreshSuggestions}
                    maxVisible={5}
                  />
                </div>
              )}
            </div>
          </div>
        </Suspense>

        {/* Execution Panel - Bottom (lazy loaded) */}
        {showExecutionPanel && (
          <Suspense fallback={<Skeleton className="h-48 w-full" />}>
            <ExecutionPanel
              onClose={() => setShowExecutionPanel(false)}
              onStop={stopExecution}
            />
          </Suspense>
        )}

        {/* Execution History Panel - Right Side (lazy loaded) */}
        {showHistoryPanel && metadata?.id && (
          <Suspense fallback={<Skeleton className="w-80 h-full" />}>
            <ExecutionHistoryPanel
              executions={accumulatedExecutions}
              isLoading={isLoadingExecutions || isFetching}
              onSelectExecution={handleSelectExecution}
              onLoadMore={handleLoadMoreExecutions}
              hasMore={!!executionsData?.nextCursor}
              selectedExecutionId={selectedExecutionId ?? undefined}
            />
          </Suspense>
        )}
      </div>

      {/* Version History Dialog (Phase 3 workflow features) */}
      {metadata?.id && showVersionHistory && (
        <Dialog
          open={showVersionHistory}
          onClose={() => setShowVersionHistory(false)}
          title="Version History"
        >
          <Suspense fallback={<Skeleton className="h-64 w-full" />}>
            <WorkflowVersionHistory workflowId={metadata.id} />
          </Suspense>
        </Dialog>
      )}

      {/* Share Workflow Dialog (Phase 3 workflow features) */}
      {metadata?.id && showShareDialog && (
        <Suspense fallback={null}>
          <ShareWorkflowDialog
            open={showShareDialog}
            onClose={() => setShowShareDialog(false)}
            workflow={{
              id: metadata.id,
              name: metadata.name || "Untitled Workflow",
            }}
          />
        </Suspense>
      )}

      {/* Global OnboardingWizard handles first-time user onboarding in App.tsx */}
    </ReactFlowProvider>
  );
}

export default WorkflowsPage;
