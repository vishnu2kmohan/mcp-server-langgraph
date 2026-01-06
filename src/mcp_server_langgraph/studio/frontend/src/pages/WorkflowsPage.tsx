/**
 * WorkflowsPage
 *
 * Visual workflow builder page using React Flow for the canvas.
 * Integrates Redux workflow slice for state management.
 */

import { useCallback, useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router";
import { ReactFlowProvider } from "reactflow";
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
import { WorkflowCanvas } from "../components/Workflow/WorkflowCanvas";
import { NodePalette, type NodeType } from "../components/Workflow/NodePalette";
import { NodeInspector } from "../components/Workflow/NodeInspector";
import { ExecutionPanel } from "../components/Workflow/ExecutionPanel";
import {
  ExecutionHistoryPanel,
  type WorkflowExecution,
} from "../components/Workflow/ExecutionHistoryPanel";
import { SuggestionChips } from "../components/Workflow/SuggestionChips";
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
} from "lucide-react";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

export function WorkflowsPage() {
  const [isGeneratingCode, setIsGeneratingCode] = useState(false);
  const [showExecutionPanel, setShowExecutionPanel] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  // AI Suggestions state
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showHistoryPanel, setShowHistoryPanel] = useState(false);
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
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {metadata?.name || "New Workflow"}
              {isDirty && <span className="text-yellow-500 ml-1">*</span>}
            </h1>

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

            {/* Inline validation error alert */}
            {validationError && (
              <div
                role="alert"
                className="flex items-center gap-2 px-3 py-1.5 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg"
              >
                <AlertCircle size={14} className="text-red-500" />
                <span className="text-sm text-red-700 dark:text-red-400">
                  {validationError}
                </span>
                <button
                  onClick={() => setValidationError(null)}
                  className="ml-1 p-0.5 text-red-500 hover:text-red-700"
                  aria-label="Dismiss"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {executionState !== "idle" && (
              <span
                className={`
                  text-xs px-2 py-1 rounded
                  ${executionState === "running" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : ""}
                  ${executionState === "completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : ""}
                  ${executionState === "error" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : ""}
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
                  ${connectionStatus === "connected" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : ""}
                  ${connectionStatus === "connecting" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" : ""}
                  ${connectionStatus === "reconnecting" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" : ""}
                  ${connectionStatus === "disconnected" || connectionStatus === "error" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : ""}
                `}
              >
                {connectionStatus === "connected" && <Wifi size={12} />}
                {connectionStatus === "connecting" && (
                  <Loader2 size={12} className="animate-spin" />
                )}
                {connectionStatus === "reconnecting" && (
                  <>
                    <RefreshCw size={12} className="animate-spin" />
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
                <button
                  onClick={reconnect}
                  className="flex items-center gap-1 text-xs px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50"
                >
                  <RefreshCw size={12} />
                  Reconnect
                </button>
              )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => dispatch(undo())}
              disabled={!canUndo || isReadOnly}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
              title="Undo (Cmd+Z)"
            >
              <Undo size={18} />
            </button>
            <button
              onClick={() => dispatch(redo())}
              disabled={!canRedo || isReadOnly}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
              title="Redo (Cmd+Shift+Z)"
            >
              <Redo size={18} />
            </button>

            <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-2" />

            <button
              onClick={handleRun}
              disabled={
                executionState === "running" ||
                !validation.isValid ||
                (isReadOnly && !canExecute)
              }
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              title="Run Workflow (Cmd+Enter)"
            >
              {executionState === "running" ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} />
              )}
              Run
            </button>

            <button
              onClick={handleGenerateCode}
              disabled={isGeneratingCode}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 rounded hover:bg-purple-200"
            >
              <Code size={16} />
              Generate Code
            </button>

            <button
              onClick={() => {
                setShowSuggestions(!showSuggestions);
                if (!showSuggestions && suggestions.length === 0) {
                  handleRefreshSuggestions();
                }
              }}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded ${
                showSuggestions
                  ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200"
              }`}
              title="AI Suggestions"
              data-testid="ai-suggestions-toggle"
            >
              <Lightbulb size={16} />
              AI Suggest
            </button>

            {/* History button - only shown when workflow has ID */}
            {metadata?.id && (
              <button
                onClick={() => setShowHistoryPanel(!showHistoryPanel)}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded ${
                  showHistoryPanel
                    ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                    : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200"
                }`}
                title="Execution History"
              >
                <History size={16} />
                History
              </button>
            )}

            <button
              onClick={handleExportJSON}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200"
            >
              <Download size={16} />
              Export JSON
            </button>

            <button
              onClick={handleSave}
              disabled={isSaving || !isDirty || isReadOnly}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              title="Save (Cmd+S)"
            >
              {isSaving ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Save size={16} />
              )}
              Save
            </button>
          </div>
        </div>

        {/* Main Content Area */}
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

        {/* Execution Panel - Bottom */}
        {showExecutionPanel && (
          <ExecutionPanel
            onClose={() => setShowExecutionPanel(false)}
            onStop={stopExecution}
          />
        )}

        {/* Execution History Panel - Right Side */}
        {showHistoryPanel && metadata?.id && (
          <ExecutionHistoryPanel
            executions={accumulatedExecutions}
            isLoading={isLoadingExecutions || isFetching}
            onSelectExecution={handleSelectExecution}
            onLoadMore={handleLoadMoreExecutions}
            hasMore={!!executionsData?.nextCursor}
            selectedExecutionId={selectedExecutionId ?? undefined}
          />
        )}
      </div>

      {/* Global OnboardingWizard handles first-time user onboarding in App.tsx */}
    </ReactFlowProvider>
  );
}

export default WorkflowsPage;
