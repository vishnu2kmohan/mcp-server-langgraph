/**
 * Workflow Slice
 *
 * Redux slice for managing workflow builder state including:
 * - Node and edge CRUD operations
 * - Selection state
 * - Undo/redo history
 * - Workflow validation
 * - Persistence to backend
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import type { Edge, XYPosition } from "reactflow";
import type { RootState } from "../index";
import type {
  WorkflowNode,
  WorkflowNodeData,
  WorkflowNodeType,
  WorkflowMetadata,
  WorkflowSnapshot,
  ValidationResult,
  ValidationError,
  ExecutionLog,
  NodeStatus,
  ExecutionState,
} from "../../types/workflow";
import { authenticatedFetch } from "../../utils/authenticatedFetch";

// ============================================================================
// Constants
// ============================================================================

/** Maximum history size for undo/redo */
const MAX_HISTORY_SIZE = 50;

/** Default labels for node types */
const DEFAULT_NODE_LABELS: Record<WorkflowNodeType, string> = {
  start: "Start",
  tool: "Tool",
  llm: "LLM",
  conditional: "Conditional",
  approval: "Approval",
  end: "End",
  custom: "Custom",
};

/**
 * Generate a unique ID for nodes and edges
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// ============================================================================
// State Type (Redux-compatible - using Record instead of Map)
// ============================================================================

export interface WorkflowSliceState {
  metadata: WorkflowMetadata | null;
  nodes: WorkflowNode[];
  edges: Edge[];
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  undoStack: WorkflowSnapshot[];
  redoStack: WorkflowSnapshot[];
  validation: ValidationResult;
  isDirty: boolean;
  isSaving: boolean;
  isLoading: boolean;
  error: string | null;
  executionState: ExecutionState;
  nodeStatuses: Record<string, NodeStatus>; // Changed from Map to Record for serialization
  executionLogs: ExecutionLog[];
  isReadOnly: boolean; // For shared workflows with view permission
  canExecute: boolean; // For shared workflows with execute permission
}

// ============================================================================
// Initial State
// ============================================================================

export const initialWorkflowState: WorkflowSliceState = {
  metadata: null,
  nodes: [],
  edges: [],
  selectedNodeIds: [],
  selectedEdgeIds: [],
  undoStack: [],
  redoStack: [],
  validation: { isValid: true, errors: [], warnings: [] },
  isDirty: false,
  isSaving: false,
  isLoading: false,
  error: null,
  executionState: "idle",
  nodeStatuses: {},
  executionLogs: [],
  isReadOnly: false,
  canExecute: true,
};

// ============================================================================
// Async Thunks
// ============================================================================

export const loadWorkflow = createAsyncThunk<
  { metadata: WorkflowMetadata; nodes: WorkflowNode[]; edges: Edge[] },
  string,
  { rejectValue: string }
>("workflow/loadWorkflow", async (id, { rejectWithValue }) => {
  try {
    const response = await authenticatedFetch(`/api/v1/workflows/${id}`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to load workflow");
    }

    const data = await response.json();
    return {
      metadata: data.metadata,
      nodes: data.nodes || [],
      edges: data.edges || [],
    };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to load workflow",
    );
  }
});

export const saveWorkflow = createAsyncThunk<
  void,
  void,
  { state: RootState; rejectValue: string }
>("workflow/saveWorkflow", async (_, { getState, rejectWithValue }) => {
  const { metadata, nodes, edges } = getState().workflow;

  if (!metadata) {
    return rejectWithValue("No workflow to save");
  }

  try {
    const response = await authenticatedFetch(
      `/api/v1/workflows/${metadata.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metadata: { ...metadata, updatedAt: Date.now() },
          nodes,
          edges,
        }),
      },
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to save workflow");
    }
    return undefined;
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to save workflow",
    );
  }
});

/**
 * Rename a workflow (updates only the name, not the full workflow)
 */
export const renameWorkflow = createAsyncThunk<
  { name: string },
  { workflowId: string; name: string },
  { state: RootState; rejectValue: string }
>(
  "workflow/renameWorkflow",
  async ({ workflowId, name }, { rejectWithValue }) => {
    try {
      const response = await authenticatedFetch(
        `/api/v1/workflows/${workflowId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to rename workflow");
      }

      return { name };
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to rename workflow",
      );
    }
  },
);

export const executeWorkflow = createAsyncThunk<
  void,
  void,
  { state: RootState; rejectValue: string }
>(
  "workflow/executeWorkflow",
  async (_, { getState, dispatch, rejectWithValue }) => {
    const { metadata, nodes, edges } = getState().workflow;

    if (!metadata) {
      return rejectWithValue("No workflow to execute");
    }

    dispatch(
      addExecutionLog({
        level: "info",
        message: `Starting workflow execution: ${metadata.name}`,
      }),
    );

    try {
      const response = await authenticatedFetch(
        `/api/v1/workflows/${metadata.id}/execute`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nodes, edges }),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to execute workflow");
      }

      await response.json();

      dispatch(
        addExecutionLog({
          level: "info",
          message: "Workflow execution completed successfully",
        }),
      );
      return undefined;
    } catch (error) {
      dispatch(
        addExecutionLog({
          level: "error",
          message:
            error instanceof Error
              ? error.message
              : "Failed to execute workflow",
        }),
      );
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to execute workflow",
      );
    }
  },
);

// ============================================================================
// Slice
// ============================================================================

export const workflowSlice = createSlice({
  name: "workflow",
  initialState: initialWorkflowState,
  reducers: {
    createWorkflow: (
      state,
      action: PayloadAction<{ name: string; description?: string }>,
    ) => {
      const now = Date.now();
      state.metadata = {
        id: generateId(),
        name: action.payload.name,
        description: action.payload.description || "",
        version: 1,
        createdAt: now,
        updatedAt: now,
      };
      state.nodes = [];
      state.edges = [];
      state.selectedNodeIds = [];
      state.selectedEdgeIds = [];
      state.undoStack = [];
      state.redoStack = [];
      state.validation = { isValid: true, errors: [], warnings: [] };
      state.isDirty = false;
      state.error = null;
    },

    addNode: {
      reducer: (
        state,
        action: PayloadAction<{
          nodeId: string;
          nodeType: WorkflowNodeType;
          position: XYPosition;
          label?: string;
        }>,
      ) => {
        const { nodeId, nodeType, position, label } = action.payload;
        const newNode: WorkflowNode = {
          id: nodeId,
          type: "default",
          position,
          data: {
            label: label || DEFAULT_NODE_LABELS[nodeType],
            nodeType,
            config: {},
          },
        };
        state.nodes.push(newNode);
        state.isDirty = true;
        state.redoStack = [];
      },
      prepare: (
        nodeType: WorkflowNodeType,
        position: XYPosition,
        label?: string,
      ) => ({
        payload: {
          nodeId: `node-${generateId()}`,
          nodeType,
          position,
          label,
        },
      }),
    },

    updateNode: (
      state,
      action: PayloadAction<{
        nodeId: string;
        data: Partial<WorkflowNodeData>;
      }>,
    ) => {
      const { nodeId, data } = action.payload;
      const node = state.nodes.find((n) => n.id === nodeId);
      if (node) {
        node.data = { ...node.data, ...data };
        state.isDirty = true;
        state.redoStack = [];
      }
    },

    deleteNode: (state, action: PayloadAction<string>) => {
      const nodeId = action.payload;
      state.nodes = state.nodes.filter((n) => n.id !== nodeId);
      state.edges = state.edges.filter(
        (e) => e.source !== nodeId && e.target !== nodeId,
      );
      state.selectedNodeIds = state.selectedNodeIds.filter(
        (id) => id !== nodeId,
      );
      state.isDirty = true;
      state.redoStack = [];
    },

    deleteNodes: (state, action: PayloadAction<string[]>) => {
      const nodeIdSet = new Set(action.payload);
      state.nodes = state.nodes.filter((n) => !nodeIdSet.has(n.id));
      state.edges = state.edges.filter(
        (e) => !nodeIdSet.has(e.source) && !nodeIdSet.has(e.target),
      );
      state.selectedNodeIds = state.selectedNodeIds.filter(
        (id) => !nodeIdSet.has(id),
      );
      state.isDirty = true;
      state.redoStack = [];
    },

    addEdge: {
      reducer: (
        state,
        action: PayloadAction<{
          edgeId: string | null;
          sourceId: string;
          targetId: string;
          sourceHandle?: string;
          targetHandle?: string;
        }>,
      ) => {
        const { edgeId, sourceId, targetId, sourceHandle, targetHandle } =
          action.payload;
        if (!edgeId) return; // Edge was rejected (self-loop or duplicate)

        const newEdge: Edge = {
          id: edgeId,
          source: sourceId,
          target: targetId,
          sourceHandle,
          targetHandle,
        };
        state.edges.push(newEdge);
        state.isDirty = true;
        state.redoStack = [];
      },
      prepare: (
        sourceId: string,
        targetId: string,
        sourceHandle?: string,
        targetHandle?: string,
      ) => {
        // Prevent self-loops
        if (sourceId === targetId) {
          return {
            payload: {
              edgeId: null,
              sourceId,
              targetId,
              sourceHandle,
              targetHandle,
            },
          };
        }
        return {
          payload: {
            edgeId: `edge-${generateId()}`,
            sourceId,
            targetId,
            sourceHandle,
            targetHandle,
          },
        };
      },
    },

    deleteEdge: (state, action: PayloadAction<string>) => {
      const edgeId = action.payload;
      state.edges = state.edges.filter((e) => e.id !== edgeId);
      state.selectedEdgeIds = state.selectedEdgeIds.filter(
        (id) => id !== edgeId,
      );
      state.isDirty = true;
      state.redoStack = [];
    },

    updateNodePositions: (
      state,
      action: PayloadAction<Array<{ id: string; position: XYPosition }>>,
    ) => {
      const updateMap = new Map(action.payload.map((u) => [u.id, u.position]));
      state.nodes = state.nodes.map((node) => {
        const newPosition = updateMap.get(node.id);
        return newPosition ? { ...node, position: newPosition } : node;
      });
      state.isDirty = true;
    },

    setSelectedNodes: (state, action: PayloadAction<string[]>) => {
      state.selectedNodeIds = action.payload;
    },

    setSelectedEdges: (state, action: PayloadAction<string[]>) => {
      state.selectedEdgeIds = action.payload;
    },

    clearSelection: (state) => {
      state.selectedNodeIds = [];
      state.selectedEdgeIds = [];
    },

    takeSnapshot: (state) => {
      const snapshot: WorkflowSnapshot = {
        nodes: [...state.nodes],
        edges: [...state.edges],
        timestamp: Date.now(),
      };
      state.undoStack.push(snapshot);
      if (state.undoStack.length > MAX_HISTORY_SIZE) {
        state.undoStack.shift();
      }
      state.redoStack = [];
    },

    undo: (state) => {
      if (state.undoStack.length === 0) return;

      const currentSnapshot: WorkflowSnapshot = {
        nodes: [...state.nodes],
        edges: [...state.edges],
        timestamp: Date.now(),
      };

      const previousState = state.undoStack.pop()!;
      state.nodes = previousState.nodes;
      state.edges = previousState.edges;
      state.redoStack.push(currentSnapshot);
    },

    redo: (state) => {
      if (state.redoStack.length === 0) return;

      const currentSnapshot: WorkflowSnapshot = {
        nodes: [...state.nodes],
        edges: [...state.edges],
        timestamp: Date.now(),
      };

      const nextState = state.redoStack.pop()!;
      state.nodes = nextState.nodes;
      state.edges = nextState.edges;
      state.undoStack.push(currentSnapshot);
    },

    validate: (state) => {
      const errors: ValidationError[] = [];
      const warnings: ValidationError[] = [];

      // Check for empty labels
      for (const node of state.nodes) {
        if (!node.data.label || node.data.label.trim() === "") {
          errors.push({
            nodeId: node.id,
            type: "error",
            message: "Node must have a label",
          });
        }
      }

      // Check for disconnected nodes (only if there are multiple nodes)
      if (state.nodes.length > 1) {
        const connectedNodes = new Set<string>();
        for (const edge of state.edges) {
          connectedNodes.add(edge.source);
          connectedNodes.add(edge.target);
        }

        for (const node of state.nodes) {
          if (!connectedNodes.has(node.id)) {
            warnings.push({
              nodeId: node.id,
              type: "warning",
              message: `Node "${node.data.label}" is not connected to any other node`,
            });
          }
        }
      }

      state.validation = {
        isValid: errors.length === 0,
        errors,
        warnings,
      };
    },

    clearError: (state) => {
      state.error = null;
    },

    resetWorkflow: (_state) => {
      return initialWorkflowState;
    },

    updateNodeStatus: (
      state,
      action: PayloadAction<{ nodeId: string; status: NodeStatus }>,
    ) => {
      state.nodeStatuses[action.payload.nodeId] = action.payload.status;
    },

    addExecutionLog: (
      state,
      action: PayloadAction<Omit<ExecutionLog, "id" | "timestamp">>,
    ) => {
      const newLog: ExecutionLog = {
        ...action.payload,
        id: generateId(),
        timestamp: Date.now(),
      };
      state.executionLogs.push(newLog);
    },

    clearExecutionLogs: (state) => {
      state.executionLogs = [];
    },

    setExecutionState: (state, action: PayloadAction<ExecutionState>) => {
      state.executionState = action.payload;
    },

    setNodes: (state, action: PayloadAction<WorkflowNode[]>) => {
      state.nodes = action.payload;
    },

    setEdges: (state, action: PayloadAction<Edge[]>) => {
      state.edges = action.payload;
    },
  },
  extraReducers: (builder) => {
    // loadWorkflow
    builder
      .addCase(loadWorkflow.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loadWorkflow.fulfilled, (state, action) => {
        state.metadata = action.payload.metadata;
        state.nodes = action.payload.nodes;
        state.edges = action.payload.edges;
        state.selectedNodeIds = [];
        state.selectedEdgeIds = [];
        state.undoStack = [];
        state.redoStack = [];
        state.isDirty = false;
        state.isLoading = false;
        state.error = null;
      })
      .addCase(loadWorkflow.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Failed to load workflow";
      });

    // saveWorkflow
    builder
      .addCase(saveWorkflow.pending, (state) => {
        state.isSaving = true;
        state.error = null;
      })
      .addCase(saveWorkflow.fulfilled, (state) => {
        state.isDirty = false;
        state.isSaving = false;
        state.error = null;
      })
      .addCase(saveWorkflow.rejected, (state, action) => {
        state.isSaving = false;
        state.error = action.payload || "Failed to save workflow";
      });

    // executeWorkflow
    builder
      .addCase(executeWorkflow.pending, (state) => {
        state.executionState = "running";
        state.nodeStatuses = {};
        state.error = null;
      })
      .addCase(executeWorkflow.fulfilled, (state) => {
        state.executionState = "completed";
      })
      .addCase(executeWorkflow.rejected, (state, action) => {
        state.executionState = "error";
        state.error = action.payload || "Failed to execute workflow";
      });

    // renameWorkflow
    builder
      .addCase(renameWorkflow.pending, (state) => {
        state.isSaving = true;
        state.error = null;
      })
      .addCase(renameWorkflow.fulfilled, (state, action) => {
        if (state.metadata) {
          state.metadata.name = action.payload.name;
          state.metadata.updatedAt = Date.now();
        }
        state.isSaving = false;
        state.error = null;
      })
      .addCase(renameWorkflow.rejected, (state, action) => {
        state.isSaving = false;
        state.error = action.payload || "Failed to rename workflow";
      });
  },
});

// ============================================================================
// Actions
// ============================================================================

export const {
  createWorkflow,
  addNode,
  updateNode,
  deleteNode,
  deleteNodes,
  addEdge,
  deleteEdge,
  updateNodePositions,
  setSelectedNodes,
  setSelectedEdges,
  clearSelection,
  takeSnapshot,
  undo,
  redo,
  validate,
  clearError,
  resetWorkflow,
  updateNodeStatus,
  addExecutionLog,
  clearExecutionLogs,
  setExecutionState,
  setNodes,
  setEdges,
} = workflowSlice.actions;

// ============================================================================
// Selectors
// ============================================================================

export const selectWorkflowMetadata = (state: RootState) =>
  state.workflow.metadata;
export const selectWorkflowNodes = (state: RootState) => state.workflow.nodes;
export const selectWorkflowEdges = (state: RootState) => state.workflow.edges;
export const selectSelectedNodeIds = (state: RootState) =>
  state.workflow.selectedNodeIds;
export const selectSelectedEdgeIds = (state: RootState) =>
  state.workflow.selectedEdgeIds;
export const selectValidation = (state: RootState) => state.workflow.validation;
export const selectIsDirty = (state: RootState) => state.workflow.isDirty;
export const selectIsSaving = (state: RootState) => state.workflow.isSaving;
export const selectIsLoading = (state: RootState) => state.workflow.isLoading;
export const selectWorkflowError = (state: RootState) => state.workflow.error;
export const selectExecutionState = (state: RootState) =>
  state.workflow.executionState;
export const selectNodeStatuses = (state: RootState) =>
  state.workflow.nodeStatuses;
export const selectExecutionLogs = (state: RootState) =>
  state.workflow.executionLogs;
export const selectCanUndo = (state: RootState) =>
  state.workflow.undoStack.length > 0;
export const selectCanRedo = (state: RootState) =>
  state.workflow.redoStack.length > 0;
export const selectNodeById = (nodeId: string) => (state: RootState) =>
  state.workflow.nodes.find((n) => n.id === nodeId);
export const selectIsReadOnly = (state: RootState) => state.workflow.isReadOnly;
export const selectCanExecute = (state: RootState) => state.workflow.canExecute;

// ============================================================================
// Export
// ============================================================================

export default workflowSlice.reducer;
