/**
 * useTraceLinking E2E Integration Tests
 *
 * End-to-end tests for the complete trace linking workflow:
 * - Highlight node -> Callback triggered -> Scroll to node
 * - History navigation (back/forward)
 * - Toggle highlight behavior
 *
 * These tests verify the full user flow for trace-to-canvas linking.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTraceLinking } from "./useTraceLinking";

// =============================================================================
// E2E Tests
// =============================================================================

describe("useTraceLinking E2E", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("complete highlight workflow", () => {
    it("should complete full flow: highlight -> callback -> scroll", () => {
      // GIVEN: Callbacks for highlight and scroll
      const onHighlight = vi.fn();
      const scrollToNode = vi.fn();

      const { result } = renderHook(() =>
        useTraceLinking({
          onHighlight,
          scrollToNode,
          scrollOnHighlight: true,
        }),
      );

      // WHEN: Highlight a node
      act(() => {
        result.current.highlightNode("node-123");
      });

      // THEN: Verify complete flow
      expect(result.current.highlightedNodeId).toBe("node-123");
      expect(result.current.isHighlightActive).toBe(true);
      expect(onHighlight).toHaveBeenCalledWith("node-123");
      expect(scrollToNode).toHaveBeenCalledWith("node-123");
    });

    it("should complete toggle flow: toggle on -> toggle off -> toggle on different node", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() => useTraceLinking({ onHighlight }));

      // Step 1: Toggle on
      act(() => {
        result.current.toggleHighlight("node-1");
      });
      expect(result.current.highlightedNodeId).toBe("node-1");
      expect(onHighlight).toHaveBeenLastCalledWith("node-1");

      // Step 2: Toggle off same node
      act(() => {
        result.current.toggleHighlight("node-1");
      });
      expect(result.current.highlightedNodeId).toBeNull();
      expect(onHighlight).toHaveBeenLastCalledWith(null);

      // Step 3: Toggle on different node
      act(() => {
        result.current.toggleHighlight("node-2");
      });
      expect(result.current.highlightedNodeId).toBe("node-2");
      expect(onHighlight).toHaveBeenLastCalledWith("node-2");
    });
  });

  describe("history navigation workflow", () => {
    it("should complete navigation flow: highlight multiple -> back -> forward", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() =>
        useTraceLinking({
          enableHistory: true,
          onHighlight,
        }),
      );

      // Step 1: Build navigation history
      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });
      act(() => {
        result.current.highlightNode("node-3");
      });

      // Verify current state
      expect(result.current.highlightedNodeId).toBe("node-3");
      expect(result.current.highlightHistory).toEqual([
        "node-1",
        "node-2",
        "node-3",
      ]);
      expect(result.current.canNavigateBack).toBe(true);
      expect(result.current.canNavigateForward).toBe(false);

      // Step 2: Navigate back
      act(() => {
        result.current.navigateBack();
      });
      expect(result.current.highlightedNodeId).toBe("node-2");
      expect(result.current.canNavigateBack).toBe(true);
      expect(result.current.canNavigateForward).toBe(true);

      // Step 3: Navigate back again
      act(() => {
        result.current.navigateBack();
      });
      expect(result.current.highlightedNodeId).toBe("node-1");
      expect(result.current.canNavigateBack).toBe(false);
      expect(result.current.canNavigateForward).toBe(true);

      // Step 4: Navigate forward
      act(() => {
        result.current.navigateForward();
      });
      expect(result.current.highlightedNodeId).toBe("node-2");

      // Step 5: Navigate forward to end
      act(() => {
        result.current.navigateForward();
      });
      expect(result.current.highlightedNodeId).toBe("node-3");
      expect(result.current.canNavigateForward).toBe(false);
    });

    it("should append to history when navigating to new node after going back", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      // Build history
      act(() => {
        result.current.highlightNode("node-1");
      });
      act(() => {
        result.current.highlightNode("node-2");
      });
      act(() => {
        result.current.highlightNode("node-3");
      });

      // Go back
      act(() => {
        result.current.navigateBack();
      });
      expect(result.current.highlightedNodeId).toBe("node-2");

      // Navigate to new node (appends to history)
      act(() => {
        result.current.highlightNode("node-4");
      });

      expect(result.current.highlightedNodeId).toBe("node-4");
      expect(result.current.highlightHistory).toContain("node-4");
      expect(result.current.canNavigateBack).toBe(true);
    });
  });

  describe("style application workflow", () => {
    it("should provide highlight styles for correct nodes", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ initialNodeId: "node-123" }),
      );

      // Highlighted node should have styles
      const highlightStyle = result.current.getNodeHighlightStyle("node-123");
      expect(highlightStyle).toHaveProperty("boxShadow");

      // Non-highlighted nodes should have empty styles
      const otherStyle = result.current.getNodeHighlightStyle("node-456");
      expect(otherStyle).toEqual({});

      // Helper method should work
      expect(result.current.isNodeHighlighted("node-123")).toBe(true);
      expect(result.current.isNodeHighlighted("node-456")).toBe(false);
    });

    it("should apply custom highlight styles when provided", () => {
      const customStyle = {
        border: "3px solid red",
        backgroundColor: "rgba(255, 0, 0, 0.1)",
      };

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

  describe("integration with scroll behavior", () => {
    it("should respect scrollOnHighlight setting", () => {
      const scrollToNode = vi.fn();

      // With scrollOnHighlight: true (default)
      const { result: result1 } = renderHook(() =>
        useTraceLinking({ scrollToNode }),
      );

      act(() => {
        result1.current.highlightNode("node-1");
      });
      expect(scrollToNode).toHaveBeenCalledWith("node-1");

      scrollToNode.mockClear();

      // With scrollOnHighlight: false
      const { result: result2 } = renderHook(() =>
        useTraceLinking({ scrollToNode, scrollOnHighlight: false }),
      );

      act(() => {
        result2.current.highlightNode("node-2");
      });
      expect(scrollToNode).not.toHaveBeenCalled();
    });
  });

  describe("edge cases", () => {
    it("should handle rapid highlight changes", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() => useTraceLinking({ onHighlight }));

      // Rapidly change highlights
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.highlightNode(`node-${i}`);
        }
      });

      // Should end on last node
      expect(result.current.highlightedNodeId).toBe("node-9");
      expect(onHighlight).toHaveBeenCalledTimes(10);
    });

    it("should handle clear after highlight", () => {
      const onHighlight = vi.fn();
      const { result } = renderHook(() => useTraceLinking({ onHighlight }));

      act(() => {
        result.current.highlightNode("node-1");
      });
      expect(result.current.isHighlightActive).toBe(true);

      act(() => {
        result.current.clearHighlight();
      });
      expect(result.current.isHighlightActive).toBe(false);
      expect(result.current.highlightedNodeId).toBeNull();
      expect(onHighlight).toHaveBeenLastCalledWith(null);
    });

    it("should handle navigation at boundaries", () => {
      const { result } = renderHook(() =>
        useTraceLinking({ enableHistory: true }),
      );

      // Navigate back when at start (should be no-op)
      act(() => {
        result.current.navigateBack();
      });
      expect(result.current.highlightedNodeId).toBeNull();

      // Add a node
      act(() => {
        result.current.highlightNode("node-1");
      });

      // Navigate forward when at end (should be no-op)
      act(() => {
        result.current.navigateForward();
      });
      expect(result.current.highlightedNodeId).toBe("node-1");
    });
  });
});
