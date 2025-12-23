/**
 * useTraceLinking Hook Tests
 *
 * TDD tests for trace-to-canvas linking functionality.
 * Allows clicking on trace nodes to highlight corresponding canvas elements.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useTraceLinking } from "./useTraceLinking";

// =============================================================================
// Tests
// =============================================================================

describe("useTraceLinking", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return initial state with no highlighted node", () => {
      const { result } = renderHook(() => useTraceLinking());

      expect(result.current.highlightedNodeId).toBeNull();
      expect(result.current.isHighlightActive).toBe(false);
    });

    it("should accept initial highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      expect(result.current.highlightedNodeId).toBe("node-123");
      expect(result.current.isHighlightActive).toBe(true);
    });
  });

  describe("highlightNode", () => {
    it("should set highlighted node ID", () => {
      const { result } = renderHook(() => useTraceLinking());

      act(() => {
        result.current.highlightNode("node-456");
      });

      expect(result.current.highlightedNodeId).toBe("node-456");
      expect(result.current.isHighlightActive).toBe(true);
    });

    it("should call onHighlight callback when provided", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() => useTraceLinking({ onHighlight }));

      act(() => {
        result.current.highlightNode("node-789");
      });

      expect(onHighlight).toHaveBeenCalledWith("node-789");
    });

    it("should replace previous highlighted node", () => {
      const { result } = renderHook(() => useTraceLinking());

      act(() => {
        result.current.highlightNode("node-1");
      });

      act(() => {
        result.current.highlightNode("node-2");
      });

      expect(result.current.highlightedNodeId).toBe("node-2");
    });
  });

  describe("clearHighlight", () => {
    it("should clear highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      act(() => {
        result.current.clearHighlight();
      });

      expect(result.current.highlightedNodeId).toBeNull();
      expect(result.current.isHighlightActive).toBe(false);
    });

    it("should call onHighlight with null when cleared", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() =>
        useTraceLinking({ onHighlight, initialNodeId: "node-123" }),
      );

      act(() => {
        result.current.clearHighlight();
      });

      expect(onHighlight).toHaveBeenCalledWith(null);
    });
  });

  describe("toggleHighlight", () => {
    it("should toggle highlight on when not active", () => {
      const { result } = renderHook(() => useTraceLinking());

      act(() => {
        result.current.toggleHighlight("node-123");
      });

      expect(result.current.highlightedNodeId).toBe("node-123");
      expect(result.current.isHighlightActive).toBe(true);
    });

    it("should toggle highlight off when same node is clicked", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      act(() => {
        result.current.toggleHighlight("node-123");
      });

      expect(result.current.highlightedNodeId).toBeNull();
      expect(result.current.isHighlightActive).toBe(false);
    });

    it("should switch to different node when clicking different node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      act(() => {
        result.current.toggleHighlight("node-456");
      });

      expect(result.current.highlightedNodeId).toBe("node-456");
    });
  });

  describe("getNodeHighlightStyle", () => {
    it("should return highlight style for highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      const style = result.current.getNodeHighlightStyle("node-123");

      expect(style).toEqual({
        boxShadow: "0 0 0 2px var(--color-primary-500)",
        animation: "pulse 1.5s infinite",
      });
    });

    it("should return empty style for non-highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      const style = result.current.getNodeHighlightStyle("node-456");

      expect(style).toEqual({});
    });

    it("should return custom highlight style when provided", () => {
      const customStyle = { border: "2px solid red" };
      const { result } = renderHook(() =>
        useTraceLinking({
          initialNodeId: "node-123",
          highlightStyle: customStyle,
        }),
      );

      const style = result.current.getNodeHighlightStyle("node-123");

      expect(style).toEqual(customStyle);
    });
  });

  describe("isNodeHighlighted", () => {
    it("should return true for highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      expect(result.current.isNodeHighlighted("node-123")).toBe(true);
    });

    it("should return false for non-highlighted node", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      expect(result.current.isNodeHighlighted("node-456")).toBe(false);
    });

    it("should return false when no node is highlighted", () => {
      const { result } = renderHook(() => useTraceLinking());

      expect(result.current.isNodeHighlighted("node-123")).toBe(false);
    });
  });

  describe("scroll to node", () => {
    it("should call scrollToNode when highlighting", () => {
      const scrollToNode = vi.fn();
      const { result } = renderHook(() =>
        useTraceLinking({ scrollToNode }),
      );

      act(() => {
        result.current.highlightNode("node-123");
      });

      expect(scrollToNode).toHaveBeenCalledWith("node-123");
    });

    it("should not call scrollToNode when disabled", () => {
      const scrollToNode = vi.fn();
      const { result } = renderHook(() =>
        useTraceLinking({ scrollToNode, scrollOnHighlight: false }),
      );

      act(() => {
        result.current.highlightNode("node-123");
      });

      expect(scrollToNode).not.toHaveBeenCalled();
    });
  });

  describe("history tracking", () => {
    it("should track highlight history", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });
      act(() => {
        result.current.highlightNode("node-3");
      });

      expect(result.current.highlightHistory).toEqual([
        "node-1",
        "node-2",
        "node-3",
      ]);
    });

    it("should navigate back in history", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });

      act(() => {
        result.current.navigateBack();
      });

      expect(result.current.highlightedNodeId).toBe("node-1");
    });

    it("should navigate forward in history", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });
      act(() => {
        result.current.navigateBack();
      });
      act(() => {
        result.current.navigateForward();
      });

      expect(result.current.highlightedNodeId).toBe("node-2");
    });

    it("should return canNavigateBack status", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      expect(result.current.canNavigateBack).toBe(false);

      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });

      expect(result.current.canNavigateBack).toBe(true);
    });
  });
});
