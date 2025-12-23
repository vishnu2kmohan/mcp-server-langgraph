/**
 * useTraceLinking Hook
 *
 * Provides trace-to-canvas linking functionality.
 * Allows clicking on trace nodes to highlight corresponding canvas elements.
 */
import { useState, useCallback, useMemo, CSSProperties } from "react";

// =============================================================================
// Types
// =============================================================================

export interface UseTraceLinkingOptions {
  /** Initial highlighted node ID */
  initialNodeId?: string | null;
  /** Callback when highlight changes */
  onHighlight?: (nodeId: string | null) => void;
  /** Callback to scroll to node in canvas */
  scrollToNode?: (nodeId: string) => void;
  /** Whether to scroll to node when highlighting (default: true) */
  scrollOnHighlight?: boolean;
  /** Custom highlight style */
  highlightStyle?: CSSProperties;
  /** Enable navigation history (default: false) */
  enableHistory?: boolean;
}

export interface UseTraceLinkingReturn {
  /** Currently highlighted node ID */
  highlightedNodeId: string | null;
  /** Whether highlight is active */
  isHighlightActive: boolean;
  /** Highlight a specific node */
  highlightNode: (nodeId: string) => void;
  /** Clear the highlight */
  clearHighlight: () => void;
  /** Toggle highlight for a node */
  toggleHighlight: (nodeId: string) => void;
  /** Get highlight style for a node */
  getNodeHighlightStyle: (nodeId: string) => CSSProperties;
  /** Check if a node is highlighted */
  isNodeHighlighted: (nodeId: string) => boolean;
  /** Highlight history (if enabled) */
  highlightHistory: string[];
  /** Navigate back in history */
  navigateBack: () => void;
  /** Navigate forward in history */
  navigateForward: () => void;
  /** Whether back navigation is available */
  canNavigateBack: boolean;
  /** Whether forward navigation is available */
  canNavigateForward: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_HIGHLIGHT_STYLE: CSSProperties = {
  boxShadow: "0 0 0 2px var(--color-primary-500)",
  animation: "pulse 1.5s infinite",
};

// =============================================================================
// Hook Implementation
// =============================================================================

export function useTraceLinking(
  options: UseTraceLinkingOptions = {},
): UseTraceLinkingReturn {
  const {
    initialNodeId = null,
    onHighlight,
    scrollToNode,
    scrollOnHighlight = true,
    highlightStyle = DEFAULT_HIGHLIGHT_STYLE,
    enableHistory = false,
  } = options;

  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(
    initialNodeId,
  );
  const [history, setHistory] = useState<string[]>(
    initialNodeId ? [initialNodeId] : [],
  );
  const [historyIndex, setHistoryIndex] = useState<number>(
    initialNodeId ? 0 : -1,
  );

  /**
   * Highlight a specific node.
   */
  const highlightNode = useCallback(
    (nodeId: string) => {
      setHighlightedNodeId(nodeId);
      onHighlight?.(nodeId);

      // Scroll to node if enabled
      if (scrollOnHighlight && scrollToNode) {
        scrollToNode(nodeId);
      }

      // Add to history if enabled
      if (enableHistory) {
        setHistory((prev) => [...prev, nodeId]);
        setHistoryIndex((prev) => prev + 1);
      }
    },
    [onHighlight, scrollToNode, scrollOnHighlight, enableHistory],
  );

  /**
   * Clear the highlight.
   */
  const clearHighlight = useCallback(() => {
    setHighlightedNodeId(null);
    onHighlight?.(null);
  }, [onHighlight]);

  /**
   * Toggle highlight for a node.
   */
  const toggleHighlight = useCallback(
    (nodeId: string) => {
      if (highlightedNodeId === nodeId) {
        clearHighlight();
      } else {
        highlightNode(nodeId);
      }
    },
    [highlightedNodeId, highlightNode, clearHighlight],
  );

  /**
   * Get highlight style for a node.
   */
  const getNodeHighlightStyle = useCallback(
    (nodeId: string): CSSProperties => {
      if (highlightedNodeId === nodeId) {
        return highlightStyle;
      }
      return {};
    },
    [highlightedNodeId, highlightStyle],
  );

  /**
   * Check if a node is highlighted.
   */
  const isNodeHighlighted = useCallback(
    (nodeId: string): boolean => {
      return highlightedNodeId === nodeId;
    },
    [highlightedNodeId],
  );

  /**
   * Navigate back in history.
   */
  const navigateBack = useCallback(() => {
    if (!enableHistory || historyIndex <= 0) return;

    const newIndex = historyIndex - 1;
    const previousNodeId = history[newIndex];

    setHistoryIndex(newIndex);
    setHighlightedNodeId(previousNodeId);
    onHighlight?.(previousNodeId);

    if (scrollOnHighlight && scrollToNode) {
      scrollToNode(previousNodeId);
    }
  }, [
    enableHistory,
    historyIndex,
    history,
    onHighlight,
    scrollOnHighlight,
    scrollToNode,
  ]);

  /**
   * Navigate forward in history.
   */
  const navigateForward = useCallback(() => {
    if (!enableHistory || historyIndex >= history.length - 1) return;

    const newIndex = historyIndex + 1;
    const nextNodeId = history[newIndex];

    setHistoryIndex(newIndex);
    setHighlightedNodeId(nextNodeId);
    onHighlight?.(nextNodeId);

    if (scrollOnHighlight && scrollToNode) {
      scrollToNode(nextNodeId);
    }
  }, [
    enableHistory,
    historyIndex,
    history,
    onHighlight,
    scrollOnHighlight,
    scrollToNode,
  ]);

  /**
   * Computed values.
   */
  const isHighlightActive = highlightedNodeId !== null;
  const canNavigateBack = enableHistory && historyIndex > 0;
  const canNavigateForward = enableHistory && historyIndex < history.length - 1;

  /**
   * Get highlight history (deduplicated array of node IDs).
   */
  const highlightHistory = useMemo(() => {
    if (!enableHistory) return [];
    return history;
  }, [enableHistory, history]);

  return {
    highlightedNodeId,
    isHighlightActive,
    highlightNode,
    clearHighlight,
    toggleHighlight,
    getNodeHighlightStyle,
    isNodeHighlighted,
    highlightHistory,
    navigateBack,
    navigateForward,
    canNavigateBack,
    canNavigateForward,
  };
}

export default useTraceLinking;
