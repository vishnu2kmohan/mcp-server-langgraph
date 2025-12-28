/**
 * Workflow Types
 *
 * Type definitions for workflow builder state including:
 * - Node and edge types
 * - Workflow metadata
 * - Store state and actions
 */

import type { Node, Edge, XYPosition } from "reactflow";

// ==============================================================================
// Node Types
// ==============================================================================

/** Available workflow node types */
export type WorkflowNodeType =
  | "start"
  | "tool"
  | "llm"
  | "conditional"
  | "approval"
  | "end"
  | "custom";

/** Node execution status */
export type NodeStatus = "idle" | "running" | "success" | "error";

/** Workflow execution state */
export type ExecutionState = "idle" | "running" | "completed" | "error";

/** Node data attached to workflow nodes */
export interface WorkflowNodeData {
  label: string;
  nodeType: WorkflowNodeType;
  config: Record<string, unknown>;
  description?: string;
  status?: NodeStatus;
}

/** Extended ReactFlow node with typed data */
export interface WorkflowNode extends Node<WorkflowNodeData> {
  data: WorkflowNodeData;
}

// ==============================================================================
// Workflow Metadata
// ==============================================================================

/** Workflow metadata */
export interface WorkflowMetadata {
  id: string;
  name: string;
  /** Human-friendly display title (defaults to name if not provided) */
  title?: string;
  description: string;
  version: number;
  createdAt: number;
  updatedAt: number;
  createdBy?: string;
  organizationId?: string;
}

// ==============================================================================
// Validation
// ==============================================================================

/** Validation error for workflow */
export interface ValidationError {
  nodeId?: string;
  edgeId?: string;
  type: "error" | "warning";
  message: string;
}

/** Validation result */
export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

// ==============================================================================
// History
// ==============================================================================

/** Snapshot of workflow state for undo/redo */
export interface WorkflowSnapshot {
  nodes: WorkflowNode[];
  edges: Edge[];
  timestamp: number;
}

// ==============================================================================
// Store State
// ==============================================================================

/** Execution log entry */
export interface ExecutionLog {
  id: string;
  timestamp: number;
  nodeId?: string;
  level: "info" | "warning" | "error";
  message: string;
  /** Optional structured data for log details (e.g., node output, token counts) */
  data?: {
    output?: string;
    tokens?: number;
    [key: string]: unknown;
  };
}

/** Workflow store state */
export interface WorkflowState {
  /** Current workflow metadata */
  metadata: WorkflowMetadata | null;

  /** Workflow nodes */
  nodes: WorkflowNode[];

  /** Workflow edges */
  edges: Edge[];

  /** Currently selected node IDs */
  selectedNodeIds: string[];

  /** Currently selected edge IDs */
  selectedEdgeIds: string[];

  /** Undo history stack */
  undoStack: WorkflowSnapshot[];

  /** Redo history stack */
  redoStack: WorkflowSnapshot[];

  /** Validation result */
  validation: ValidationResult;

  /** Whether workflow has unsaved changes */
  isDirty: boolean;

  /** Whether workflow is being saved */
  isSaving: boolean;

  /** Whether workflow is being loaded */
  isLoading: boolean;

  /** Error message if any */
  error: string | null;

  /** Execution state */
  executionState: ExecutionState;

  /** Node execution statuses */
  nodeStatuses: Map<string, NodeStatus>;

  /** Execution logs */
  executionLogs: ExecutionLog[];
}

/** Workflow store actions */
export interface WorkflowActions {
  /** Initialize a new workflow */
  createWorkflow: (name: string, description?: string) => void;

  /** Load an existing workflow */
  loadWorkflow: (id: string) => Promise<void>;

  /** Save current workflow */
  saveWorkflow: () => Promise<void>;

  /** Add a new node */
  addNode: (
    nodeType: WorkflowNodeType,
    position: XYPosition,
    label?: string,
  ) => string;

  /** Update node data */
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => void;

  /** Delete a node */
  deleteNode: (nodeId: string) => void;

  /** Delete multiple nodes */
  deleteNodes: (nodeIds: string[]) => void;

  /** Add an edge between nodes */
  addEdge: (
    sourceId: string,
    targetId: string,
    sourceHandle?: string,
    targetHandle?: string,
  ) => string | null;

  /** Delete an edge */
  deleteEdge: (edgeId: string) => void;

  /** Update node positions */
  updateNodePositions: (
    updates: Array<{ id: string; position: XYPosition }>,
  ) => void;

  /** Set selected nodes */
  setSelectedNodes: (nodeIds: string[]) => void;

  /** Set selected edges */
  setSelectedEdges: (edgeIds: string[]) => void;

  /** Clear selection */
  clearSelection: () => void;

  /** Take snapshot for undo */
  takeSnapshot: () => void;

  /** Undo last action */
  undo: () => void;

  /** Redo last undone action */
  redo: () => void;

  /** Validate workflow */
  validate: () => ValidationResult;

  /** Clear error */
  clearError: () => void;

  /** Reset workflow to initial state */
  reset: () => void;

  /** Execute workflow */
  executeWorkflow: () => Promise<void>;

  /** Update node execution status */
  updateNodeStatus: (nodeId: string, status: NodeStatus) => void;

  /** Add execution log */
  addExecutionLog: (log: Omit<ExecutionLog, "id" | "timestamp">) => void;

  /** Clear execution logs */
  clearExecutionLogs: () => void;
}

/** Combined workflow store type */
export type WorkflowStore = WorkflowState & WorkflowActions;
