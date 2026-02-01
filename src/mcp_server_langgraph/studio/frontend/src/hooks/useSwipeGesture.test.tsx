/**
 * useSwipeGesture Hook Tests
 *
 * Tests for swipe gesture support hook.
 * Tests cover direction configuration, threshold behavior, and dismiss callbacks.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { useSwipeGesture } from "./useSwipeGesture";
import type { PanInfo } from "motion/react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Helper to create PanInfo for testing
const createPanInfo = (
  offsetX: number,
  offsetY: number,
  velocityX = 0,
  velocityY = 0,
): PanInfo => ({
  point: { x: 0, y: 0 },
  delta: { x: 0, y: 0 },
  offset: { x: offsetX, y: offsetY },
  velocity: { x: velocityX, y: velocityY },
});

describe("useSwipeGesture", () => {
  // ===========================================================================
  // Default Behavior Tests
  // ===========================================================================

  describe("default behavior", () => {
    it("returns horizontal drag axis by default", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.drag).toBe("x");
    });

    it("starts with zero dragOffset", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.dragOffset).toBe(0);
    });

    it("starts with isDragging false", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.isDragging).toBe(false);
    });

    it("starts with full opacity", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.opacity).toBe(1);
    });
  });

  // ===========================================================================
  // Direction Configuration Tests
  // ===========================================================================

  describe("direction configuration", () => {
    it("returns x drag for horizontal direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "horizontal" }),
      );

      expect(result.current.drag).toBe("x");
    });

    it("returns x drag for left direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "left" }),
      );

      expect(result.current.drag).toBe("x");
    });

    it("returns x drag for right direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "right" }),
      );

      expect(result.current.drag).toBe("x");
    });

    it("returns y drag for vertical direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "vertical" }),
      );

      expect(result.current.drag).toBe("y");
    });

    it("returns y drag for up direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "up" }),
      );

      expect(result.current.drag).toBe("y");
    });

    it("returns y drag for down direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "down" }),
      );

      expect(result.current.drag).toBe("y");
    });
  });

  // ===========================================================================
  // Dismiss Behavior Tests
  // ===========================================================================

  describe("dismiss behavior", () => {
    it("calls onDismiss when horizontal swipe exceeds threshold", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "horizontal", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");
      const info = createPanInfo(150, 0);

      result.current.onDragEnd(event, info);

      expect(onDismiss).toHaveBeenCalled();
    });

    it("does not call onDismiss when swipe is below threshold", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "horizontal", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");
      const info = createPanInfo(50, 0);

      result.current.onDragEnd(event, info);

      expect(onDismiss).not.toHaveBeenCalled();
    });

    it("calls onDismiss when velocity is high enough", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "horizontal", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");
      const info = createPanInfo(30, 0, 600, 0); // Low offset but high velocity

      result.current.onDragEnd(event, info);

      expect(onDismiss).toHaveBeenCalled();
    });

    it("respects left-only direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "left", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");

      // Swipe right - should not dismiss
      result.current.onDragEnd(event, createPanInfo(150, 0));
      expect(onDismiss).not.toHaveBeenCalled();

      // Swipe left - should dismiss
      result.current.onDragEnd(event, createPanInfo(-150, 0));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("respects right-only direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "right", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");

      // Swipe left - should not dismiss
      result.current.onDragEnd(event, createPanInfo(-150, 0));
      expect(onDismiss).not.toHaveBeenCalled();

      // Swipe right - should dismiss
      result.current.onDragEnd(event, createPanInfo(150, 0));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("respects up-only direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "up", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");

      // Swipe down - should not dismiss
      result.current.onDragEnd(event, createPanInfo(0, 150));
      expect(onDismiss).not.toHaveBeenCalled();

      // Swipe up - should dismiss
      result.current.onDragEnd(event, createPanInfo(0, -150));
      expect(onDismiss).toHaveBeenCalled();
    });

    it("respects down-only direction", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, direction: "down", threshold: 100 }),
      );

      const event = new MouseEvent("pointerup");

      // Swipe up - should not dismiss
      result.current.onDragEnd(event, createPanInfo(0, -150));
      expect(onDismiss).not.toHaveBeenCalled();

      // Swipe down - should dismiss
      result.current.onDragEnd(event, createPanInfo(0, 150));
      expect(onDismiss).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Enabled/Disabled Tests
  // ===========================================================================

  describe("enabled/disabled", () => {
    it("disables drag when enabled is false", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, enabled: false }),
      );

      expect(result.current.drag).toBe(false);
    });

    it("does not call onDismiss when disabled", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() =>
        useSwipeGesture({ onDismiss, enabled: false }),
      );

      const event = new MouseEvent("pointerup");
      const info = createPanInfo(200, 0);

      result.current.onDragEnd(event, info);

      expect(onDismiss).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Props Structure Tests
  // ===========================================================================

  describe("props structure", () => {
    it("returns drag constraints", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.dragConstraints).toEqual({
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
      });
    });

    it("returns dragElastic value", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(result.current.dragElastic).toBe(0.7);
    });

    it("returns onDragEnd handler", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useSwipeGesture({ onDismiss }));

      expect(typeof result.current.onDragEnd).toBe("function");
    });
  });
});
