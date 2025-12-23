/**
 * LangGraph Slice
 *
 * Redux slice for managing LangGraph execution events.
 * Enables DevTools time-travel debugging by storing node execution history.
 *
 * Features:
 * - Store LangGraph node execution events
 * - Track nodes by session for multi-session support
 * - Selectors for filtering nodes by session
 * - Integration with DevToolsWebSocketObserver for timeline
 */

import { createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../index";

// =============================================================================
// Types
// =============================================================================

/**
 * LangGraph node type (matching useStreamingChat.LangGraphNode)
 */
export type LangGraphNodeType =
  | "start"
  | "end"
  | "tool"
  | "conditional"
  | "agent"
  | "default";

/**
 * LangGraph node status
 */
export type LangGraphNodeStatus =
  | "pending"
  | "running"
  | "completed"
  | "error"
  | "skipped";

/**
 * LangGraph node data structure with session tracking
 */
export interface LangGraphNode {
  /** Unique node identifier */
  id: string;
  /** Session this node belongs to */
  sessionId: string;
  /** Node name (e.g., "AgentNode", "ToolNode") */
  name: string;
  /** Node type */
  type: LangGraphNodeType;
  /** Execution status */
  status: LangGraphNodeStatus;
  /** Start timestamp (ms since epoch) */
  startTime: number;
  /** End timestamp (ms since epoch) */
  endTime?: number;
  /** Duration in milliseconds */
  duration?: number;
  /** Node output (for completed nodes) */
  output?: string;
}

/**
 * LangGraph slice state
 */
export interface LangGraphState {
  /** All LangGraph nodes across sessions */
  nodes: LangGraphNode[];
  /** Currently active session ID for filtering */
  currentSessionId: string | null;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: LangGraphState = {
  nodes: [],
  currentSessionId: null,
};

// =============================================================================
// Slice
// =============================================================================

const langGraphSlice = createSlice({
  name: "langGraph",
  initialState,
  reducers: {
    /**
     * Add a new node or update existing node with same id
     */
    addNode: (state, action: PayloadAction<LangGraphNode>) => {
      const existingIndex = state.nodes.findIndex(
        (n) => n.id === action.payload.id,
      );
      if (existingIndex >= 0) {
        // Update existing node
        state.nodes[existingIndex] = action.payload;
      } else {
        // Add new node
        state.nodes.push(action.payload);
      }
    },

    /**
     * Update an existing node by id
     */
    updateNode: (
      state,
      action: PayloadAction<{
        id: string;
        changes: Partial<Omit<LangGraphNode, "id" | "sessionId">>;
      }>,
    ) => {
      const { id, changes } = action.payload;
      const node = state.nodes.find((n) => n.id === id);
      if (node) {
        Object.assign(node, changes);
      }
    },

    /**
     * Clear all nodes, or nodes for a specific session
     */
    clearNodes: (state, action: PayloadAction<string | undefined>) => {
      const sessionId = action.payload;
      if (sessionId) {
        // Clear nodes for specific session
        state.nodes = state.nodes.filter((n) => n.sessionId !== sessionId);
      } else {
        // Clear all nodes
        state.nodes = [];
      }
    },

    /**
     * Set the current session ID for filtering
     */
    setCurrentSessionId: (state, action: PayloadAction<string | null>) => {
      state.currentSessionId = action.payload;
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const { addNode, updateNode, clearNodes, setCurrentSessionId } =
  langGraphSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

/**
 * Select all LangGraph nodes
 */
export const selectLangGraphNodes = (state: RootState): LangGraphNode[] =>
  state.langGraph?.nodes ?? [];

/**
 * Select LangGraph nodes for a specific session
 */
export const selectLangGraphNodesBySession = createSelector(
  [selectLangGraphNodes, (_state: RootState, sessionId: string) => sessionId],
  (nodes, sessionId): LangGraphNode[] =>
    nodes.filter((n) => n.sessionId === sessionId),
);

/**
 * Select the current session ID
 */
export const selectCurrentSessionId = (state: RootState): string | null =>
  state.langGraph?.currentSessionId ?? null;

/**
 * Select LangGraph nodes for the current session
 */
export const selectCurrentSessionNodes = createSelector(
  [selectLangGraphNodes, selectCurrentSessionId],
  (nodes, sessionId): LangGraphNode[] =>
    sessionId ? nodes.filter((n) => n.sessionId === sessionId) : [],
);

// =============================================================================
// Export
// =============================================================================

export default langGraphSlice.reducer;
