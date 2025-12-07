/**
 * Undo/Redo Hook for Workflow Builder
 *
 * Provides history management for nodes and edges with:
 * - Snapshot-based history
 * - Undo/redo operations
 * - Configurable history limit
 */

import { useCallback, useState, useRef } from 'react';
import type { Node, Edge } from 'reactflow';

// ==============================================================================
// Types
// ==============================================================================

interface HistoryState {
  nodes: Node[];
  edges: Edge[];
}

interface UndoRedoResult {
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  takeSnapshot: () => void;
}

// ==============================================================================
// Hook Implementation
// ==============================================================================

const DEFAULT_HISTORY_LIMIT = 50;

export function useUndoRedo(
  nodes: Node[],
  edges: Edge[],
  setNodes: (nodes: Node[]) => void,
  setEdges: (edges: Edge[]) => void,
  historyLimit: number = DEFAULT_HISTORY_LIMIT
): UndoRedoResult {
  // History stack for undo
  const [undoStack, setUndoStack] = useState<HistoryState[]>([]);
  // History stack for redo
  const [redoStack, setRedoStack] = useState<HistoryState[]>([]);

  // Current state refs to avoid stale closures
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  // Take a snapshot of current state
  const takeSnapshot = useCallback(() => {
    const snapshot: HistoryState = {
      nodes: [...nodesRef.current],
      edges: [...edgesRef.current],
    };

    setUndoStack((prev) => {
      const newStack = [...prev, snapshot];
      // Limit history size
      if (newStack.length > historyLimit) {
        return newStack.slice(-historyLimit);
      }
      return newStack;
    });

    // Clear redo stack when new action is taken
    setRedoStack([]);
  }, [historyLimit]);

  // Undo to previous state
  const undo = useCallback(() => {
    if (undoStack.length === 0) return;

    // Save current state to redo stack
    const currentState: HistoryState = {
      nodes: [...nodesRef.current],
      edges: [...edgesRef.current],
    };
    setRedoStack((prev) => [...prev, currentState]);

    // Pop and apply previous state
    const newUndoStack = [...undoStack];
    const previousState = newUndoStack.pop()!;
    setUndoStack(newUndoStack);

    setNodes(previousState.nodes);
    setEdges(previousState.edges);
  }, [undoStack, setNodes, setEdges]);

  // Redo to next state
  const redo = useCallback(() => {
    if (redoStack.length === 0) return;

    // Save current state to undo stack
    const currentState: HistoryState = {
      nodes: [...nodesRef.current],
      edges: [...edgesRef.current],
    };
    setUndoStack((prev) => [...prev, currentState]);

    // Pop and apply next state
    const newRedoStack = [...redoStack];
    const nextState = newRedoStack.pop()!;
    setRedoStack(newRedoStack);

    setNodes(nextState.nodes);
    setEdges(nextState.edges);
  }, [redoStack, setNodes, setEdges]);

  return {
    undo,
    redo,
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
    takeSnapshot,
  };
}

export default useUndoRedo;
