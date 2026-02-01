/**
 * useSwipeGesture Hook
 *
 * Provides swipe gesture support for dismissible elements.
 * Uses Motion's drag gesture for smooth swipe-to-dismiss behavior.
 *
 * @example
 * const swipeProps = useSwipeGesture({
 *   onDismiss: () => setVisible(false),
 *   direction: 'horizontal',
 * });
 *
 * <motion.div {...swipeProps}>
 *   Swipe me to dismiss
 * </motion.div>
 */

import { useState, useCallback } from "react";
import type { PanInfo } from "motion/react";

// =============================================================================
// Types
// =============================================================================

export type SwipeDirection =
  | "horizontal"
  | "vertical"
  | "left"
  | "right"
  | "up"
  | "down";

export interface UseSwipeGestureOptions {
  /** Callback when element is swiped away */
  onDismiss: () => void;
  /** Direction(s) allowed for swipe (default: 'horizontal') */
  direction?: SwipeDirection;
  /** Minimum distance (in pixels) to trigger dismiss (default: 100) */
  threshold?: number;
  /** Whether swipe is enabled (default: true) */
  enabled?: boolean;
}

export interface UseSwipeGestureReturn {
  /** Props to spread onto motion element */
  drag: "x" | "y" | boolean;
  dragConstraints: { left: number; right: number; top: number; bottom: number };
  dragElastic: number;
  onDragEnd: (
    event: MouseEvent | TouchEvent | PointerEvent,
    info: PanInfo,
  ) => void;
  /** Current drag offset for UI feedback */
  dragOffset: number;
  /** Whether currently dragging */
  isDragging: boolean;
  /** Opacity based on drag distance (for fade effect) */
  opacity: number;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for swipe-to-dismiss gesture support.
 *
 * @param options - Swipe configuration options
 * @returns Props to spread onto a motion element
 */
export function useSwipeGesture({
  onDismiss,
  direction = "horizontal",
  threshold = 100,
  enabled = true,
}: UseSwipeGestureOptions): UseSwipeGestureReturn {
  const [dragOffset, setDragOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // Determine drag axis based on direction
  const getDragAxis = (): "x" | "y" | boolean => {
    if (!enabled) return false;
    switch (direction) {
      case "horizontal":
      case "left":
      case "right":
        return "x";
      case "vertical":
      case "up":
      case "down":
        return "y";
      default:
        return "x";
    }
  };

  // Handle drag end
  const handleDragEnd = useCallback(
    (_event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      setIsDragging(false);
      setDragOffset(0);

      if (!enabled) return;

      const { offset, velocity } = info;

      // Check if swipe exceeds threshold or has enough velocity
      const shouldDismiss = (
        offsetValue: number,
        velocityValue: number,
        isPositive: boolean,
      ) => {
        const absOffset = Math.abs(offsetValue);
        const absVelocity = Math.abs(velocityValue);
        const directionMatches = isPositive ? offsetValue > 0 : offsetValue < 0;
        return (absOffset > threshold || absVelocity > 500) && directionMatches;
      };

      switch (direction) {
        case "horizontal":
          if (Math.abs(offset.x) > threshold || Math.abs(velocity.x) > 500) {
            onDismiss();
          }
          break;
        case "left":
          if (shouldDismiss(offset.x, velocity.x, false)) {
            onDismiss();
          }
          break;
        case "right":
          if (shouldDismiss(offset.x, velocity.x, true)) {
            onDismiss();
          }
          break;
        case "vertical":
          if (Math.abs(offset.y) > threshold || Math.abs(velocity.y) > 500) {
            onDismiss();
          }
          break;
        case "up":
          if (shouldDismiss(offset.y, velocity.y, false)) {
            onDismiss();
          }
          break;
        case "down":
          if (shouldDismiss(offset.y, velocity.y, true)) {
            onDismiss();
          }
          break;
      }
    },
    [direction, threshold, enabled, onDismiss],
  );

  // Calculate opacity based on drag distance
  const opacity = Math.max(0, 1 - Math.abs(dragOffset) / (threshold * 2));

  return {
    drag: getDragAxis(),
    dragConstraints: { left: 0, right: 0, top: 0, bottom: 0 },
    dragElastic: 0.7,
    onDragEnd: handleDragEnd,
    dragOffset,
    isDragging,
    opacity,
  };
}

export default useSwipeGesture;
