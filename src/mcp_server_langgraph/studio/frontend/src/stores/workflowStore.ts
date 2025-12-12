/**
 * Workflow Store
 *
 * Zustand store for managing workflow builder state including:
 * - Node and edge CRUD operations
 * - Selection state
 * - Undo/redo history
 * - Workflow validation
 * - Persistence to backend
 */

import { create, StateCreator } from 'zustand';
import type {
  WorkflowStore,
  WorkflowState,
  WorkflowNode,
  WorkflowNodeData,
  WorkflowNodeType,
  WorkflowMetadata,
  WorkflowSnapshot,
  ValidationResult,
  ValidationError,
} from '../types/workflow';
import type { Edge, XYPosition } from 'reactflow';

/** Maximum history size for undo/redo */
const MAX_HISTORY_SIZE = 50;

/** Default labels for node types */
const DEFAULT_NODE_LABELS: Record<WorkflowNodeType, string> = {
  tool: 'Tool',
  llm: 'LLM',
  conditional: 'Conditional',
  approval: 'Approval',
  custom: 'Custom',
};

/**
 * Generate a unique ID for nodes and edges
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Initial workflow state
 */
export const initialWorkflowState: WorkflowState = {
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
};

/**
 * Create the workflow store state and actions
 */
const createWorkflowStore: StateCreator<WorkflowStore> = (set, get) => ({
  ...initialWorkflowState,

  /**
   * Create a new workflow
   */
  createWorkflow: (name: string, description = '') => {
    const now = Date.now();
    const metadata: WorkflowMetadata = {
      id: generateId(),
      name,
      description,
      version: 1,
      createdAt: now,
      updatedAt: now,
    };

    set({
      metadata,
      nodes: [],
      edges: [],
      selectedNodeIds: [],
      selectedEdgeIds: [],
      undoStack: [],
      redoStack: [],
      validation: { isValid: true, errors: [], warnings: [] },
      isDirty: false,
      error: null,
    });
  },

  /**
   * Load an existing workflow from the API
   */
  loadWorkflow: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      const response = await fetch(`/api/v1/workflows/${id}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load workflow');
      }

      const data = await response.json();

      set({
        metadata: data.metadata,
        nodes: data.nodes || [],
        edges: data.edges || [],
        selectedNodeIds: [],
        selectedEdgeIds: [],
        undoStack: [],
        redoStack: [],
        isDirty: false,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load workflow',
      });
    }
  },

  /**
   * Save current workflow to the API
   */
  saveWorkflow: async () => {
    const { metadata, nodes, edges } = get();

    if (!metadata) {
      set({ error: 'No workflow to save' });
      return;
    }

    set({ isSaving: true, error: null });

    try {
      const response = await fetch(`/api/v1/workflows/${metadata.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metadata: {
            ...metadata,
            updatedAt: Date.now(),
          },
          nodes,
          edges,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save workflow');
      }

      set({
        isDirty: false,
        isSaving: false,
        error: null,
      });
    } catch (error) {
      set({
        isSaving: false,
        error: error instanceof Error ? error.message : 'Failed to save workflow',
      });
    }
  },

  /**
   * Add a new node to the workflow
   */
  addNode: (nodeType: WorkflowNodeType, position: XYPosition, label?: string): string => {
    const nodeId = `node-${generateId()}`;
    const newNode: WorkflowNode = {
      id: nodeId,
      type: 'default',
      position,
      data: {
        label: label || DEFAULT_NODE_LABELS[nodeType],
        nodeType,
        config: {},
      },
    };

    set((state) => ({
      nodes: [...state.nodes, newNode],
      isDirty: true,
      redoStack: [], // Clear redo on new action
    }));

    return nodeId;
  },

  /**
   * Update node data
   */
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
      isDirty: true,
      redoStack: [],
    }));
  },

  /**
   * Delete a node
   */
  deleteNode: (nodeId: string) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNodeIds: state.selectedNodeIds.filter((id) => id !== nodeId),
      isDirty: true,
      redoStack: [],
    }));
  },

  /**
   * Delete multiple nodes
   */
  deleteNodes: (nodeIds: string[]) => {
    const nodeIdSet = new Set(nodeIds);
    set((state) => ({
      nodes: state.nodes.filter((node) => !nodeIdSet.has(node.id)),
      edges: state.edges.filter(
        (edge) => !nodeIdSet.has(edge.source) && !nodeIdSet.has(edge.target)
      ),
      selectedNodeIds: state.selectedNodeIds.filter((id) => !nodeIdSet.has(id)),
      isDirty: true,
      redoStack: [],
    }));
  },

  /**
   * Add an edge between nodes
   */
  addEdge: (
    sourceId: string,
    targetId: string,
    sourceHandle?: string,
    targetHandle?: string
  ): string | null => {
    // Prevent self-loops
    if (sourceId === targetId) {
      return null;
    }

    // Check for existing edge
    const { edges } = get();
    const exists = edges.some(
      (edge) => edge.source === sourceId && edge.target === targetId
    );
    if (exists) {
      return null;
    }

    const edgeId = `edge-${generateId()}`;
    const newEdge: Edge = {
      id: edgeId,
      source: sourceId,
      target: targetId,
      sourceHandle,
      targetHandle,
    };

    set((state) => ({
      edges: [...state.edges, newEdge],
      isDirty: true,
      redoStack: [],
    }));

    return edgeId;
  },

  /**
   * Delete an edge
   */
  deleteEdge: (edgeId: string) => {
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId),
      selectedEdgeIds: state.selectedEdgeIds.filter((id) => id !== edgeId),
      isDirty: true,
      redoStack: [],
    }));
  },

  /**
   * Update node positions
   */
  updateNodePositions: (updates: Array<{ id: string; position: XYPosition }>) => {
    const updateMap = new Map(updates.map((u) => [u.id, u.position]));
    set((state) => ({
      nodes: state.nodes.map((node) => {
        const newPosition = updateMap.get(node.id);
        return newPosition ? { ...node, position: newPosition } : node;
      }),
      isDirty: true,
    }));
  },

  /**
   * Set selected nodes
   */
  setSelectedNodes: (nodeIds: string[]) => {
    set({ selectedNodeIds: nodeIds });
  },

  /**
   * Set selected edges
   */
  setSelectedEdges: (edgeIds: string[]) => {
    set({ selectedEdgeIds: edgeIds });
  },

  /**
   * Clear all selection
   */
  clearSelection: () => {
    set({ selectedNodeIds: [], selectedEdgeIds: [] });
  },

  /**
   * Take a snapshot for undo
   */
  takeSnapshot: () => {
    const { nodes, edges, undoStack } = get();
    const snapshot: WorkflowSnapshot = {
      nodes: [...nodes],
      edges: [...edges],
      timestamp: Date.now(),
    };

    const newStack = [...undoStack, snapshot];
    if (newStack.length > MAX_HISTORY_SIZE) {
      newStack.shift();
    }

    set({
      undoStack: newStack,
      redoStack: [], // Clear redo on new snapshot
    });
  },

  /**
   * Undo last action
   */
  undo: () => {
    const { undoStack, nodes, edges, redoStack } = get();
    if (undoStack.length === 0) return;

    // Save current state to redo
    const currentSnapshot: WorkflowSnapshot = {
      nodes: [...nodes],
      edges: [...edges],
      timestamp: Date.now(),
    };

    const newUndoStack = [...undoStack];
    const previousState = newUndoStack.pop()!;

    set({
      nodes: previousState.nodes,
      edges: previousState.edges,
      undoStack: newUndoStack,
      redoStack: [...redoStack, currentSnapshot],
    });
  },

  /**
   * Redo last undone action
   */
  redo: () => {
    const { redoStack, nodes, edges, undoStack } = get();
    if (redoStack.length === 0) return;

    // Save current state to undo
    const currentSnapshot: WorkflowSnapshot = {
      nodes: [...nodes],
      edges: [...edges],
      timestamp: Date.now(),
    };

    const newRedoStack = [...redoStack];
    const nextState = newRedoStack.pop()!;

    set({
      nodes: nextState.nodes,
      edges: nextState.edges,
      undoStack: [...undoStack, currentSnapshot],
      redoStack: newRedoStack,
    });
  },

  /**
   * Validate workflow
   */
  validate: (): ValidationResult => {
    const { nodes, edges } = get();
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];

    // Check for empty labels
    for (const node of nodes) {
      if (!node.data.label || node.data.label.trim() === '') {
        errors.push({
          nodeId: node.id,
          type: 'error',
          message: 'Node must have a label',
        });
      }
    }

    // Check for disconnected nodes (only if there are multiple nodes)
    if (nodes.length > 1) {
      const connectedNodes = new Set<string>();
      for (const edge of edges) {
        connectedNodes.add(edge.source);
        connectedNodes.add(edge.target);
      }

      for (const node of nodes) {
        if (!connectedNodes.has(node.id)) {
          warnings.push({
            nodeId: node.id,
            type: 'warning',
            message: `Node "${node.data.label}" is not connected to any other node`,
          });
        }
      }
    }

    const result: ValidationResult = {
      isValid: errors.length === 0,
      errors,
      warnings,
    };

    set({ validation: result });
    return result;
  },

  /**
   * Clear error
   */
  clearError: () => {
    set({ error: null });
  },

  /**
   * Reset workflow to initial state
   */
  reset: () => {
    set({ ...initialWorkflowState });
  },
});

/**
 * Workflow store with Zustand
 */
export const useWorkflowStore = create<WorkflowStore>()(createWorkflowStore);

/**
 * Create a test store without persistence
 */
export const createTestWorkflowStore = () => create<WorkflowStore>()(createWorkflowStore);
