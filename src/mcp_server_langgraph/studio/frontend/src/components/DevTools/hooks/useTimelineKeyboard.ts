/**
 * useTimelineKeyboard Hook
 *
 * Provides keyboard shortcuts for timeline navigation:
 * - Space: Play/Pause
 * - ArrowLeft: Step backward
 * - ArrowRight: Step forward
 * - Home: Jump to start
 * - End: Jump to end / Live mode
 * - B: Add bookmark at current time
 * - Shift+ArrowLeft: Previous bookmark
 * - Shift+ArrowRight: Next bookmark
 * - 1-9: Set playback speed
 */
import { useEffect, useCallback, useMemo } from "react";

// =============================================================================
// Types
// =============================================================================

export interface UseTimelineKeyboardOptions {
  /** Whether keyboard shortcuts are enabled */
  enabled: boolean;
  /** Callback for play/pause toggle */
  onPlayPause?: () => void;
  /** Callback for step forward */
  onStepForward?: () => void;
  /** Callback for step backward */
  onStepBackward?: () => void;
  /** Callback for jump to start */
  onJumpToStart?: () => void;
  /** Callback for jump to end */
  onJumpToEnd?: () => void;
  /** Callback for adding bookmark */
  onAddBookmark?: () => void;
  /** Callback for next bookmark */
  onNextBookmark?: () => void;
  /** Callback for previous bookmark */
  onPrevBookmark?: () => void;
  /** Callback for setting speed (1-9) */
  onSetSpeed?: (speed: number) => void;
}

export interface TimelineKeyboardShortcut {
  /** Key to press */
  key: string;
  /** Modifier keys required */
  modifiers: ("meta" | "ctrl" | "shift" | "alt")[];
  /** Human-readable description */
  description: string;
  /** Action ID */
  action: string;
}

export interface UseTimelineKeyboardReturn {
  /** List of registered shortcuts */
  shortcuts: TimelineKeyboardShortcut[];
  /** Whether shortcuts are enabled */
  isEnabled: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const SHORTCUTS: TimelineKeyboardShortcut[] = [
  {
    key: "Space",
    modifiers: [],
    description: "Play/Pause timeline",
    action: "play-pause",
  },
  {
    key: "ArrowLeft",
    modifiers: [],
    description: "Step backward",
    action: "step-backward",
  },
  {
    key: "ArrowRight",
    modifiers: [],
    description: "Step forward",
    action: "step-forward",
  },
  {
    key: "Home",
    modifiers: [],
    description: "Jump to start",
    action: "jump-start",
  },
  {
    key: "End",
    modifiers: [],
    description: "Jump to end / Live mode",
    action: "jump-end",
  },
  {
    key: "B",
    modifiers: [],
    description: "Add bookmark",
    action: "add-bookmark",
  },
  {
    key: "ArrowLeft",
    modifiers: ["shift"],
    description: "Previous bookmark",
    action: "prev-bookmark",
  },
  {
    key: "ArrowRight",
    modifiers: ["shift"],
    description: "Next bookmark",
    action: "next-bookmark",
  },
  {
    key: "1-9",
    modifiers: [],
    description: "Set playback speed",
    action: "set-speed",
  },
];

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if the active element is an input-like element
 */
function isInputFocused(): boolean {
  const activeElement = document.activeElement;
  if (!activeElement) return false;

  const tagName = activeElement.tagName.toLowerCase();
  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true;
  }

  // Check for contenteditable
  if (activeElement.getAttribute("contenteditable") === "true") {
    return true;
  }

  return false;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useTimelineKeyboard(
  options: UseTimelineKeyboardOptions,
): UseTimelineKeyboardReturn {
  const {
    enabled,
    onPlayPause,
    onStepForward,
    onStepBackward,
    onJumpToStart,
    onJumpToEnd,
    onAddBookmark,
    onNextBookmark,
    onPrevBookmark,
    onSetSpeed,
  } = options;

  /**
   * Handle keyboard events
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't handle if an input is focused
      if (isInputFocused()) {
        return;
      }

      const { key, shiftKey } = event;

      // Space - Play/Pause
      if (key === " " && !shiftKey) {
        event.preventDefault();
        onPlayPause?.();
        return;
      }

      // ArrowLeft - Step backward or previous bookmark
      if (key === "ArrowLeft") {
        event.preventDefault();
        if (shiftKey) {
          onPrevBookmark?.();
        } else {
          onStepBackward?.();
        }
        return;
      }

      // ArrowRight - Step forward or next bookmark
      if (key === "ArrowRight") {
        event.preventDefault();
        if (shiftKey) {
          onNextBookmark?.();
        } else {
          onStepForward?.();
        }
        return;
      }

      // Home - Jump to start
      if (key === "Home") {
        event.preventDefault();
        onJumpToStart?.();
        return;
      }

      // End - Jump to end / Live mode
      if (key === "End") {
        event.preventDefault();
        onJumpToEnd?.();
        return;
      }

      // B - Add bookmark
      if (key.toLowerCase() === "b" && !shiftKey) {
        event.preventDefault();
        onAddBookmark?.();
        return;
      }

      // 1-9 - Set playback speed
      const speedNumber = parseInt(key, 10);
      if (speedNumber >= 1 && speedNumber <= 9 && !shiftKey) {
        event.preventDefault();
        onSetSpeed?.(speedNumber);
        return;
      }
    },
    [
      onPlayPause,
      onStepForward,
      onStepBackward,
      onJumpToStart,
      onJumpToEnd,
      onAddBookmark,
      onNextBookmark,
      onPrevBookmark,
      onSetSpeed,
    ],
  );

  /**
   * Register/unregister keyboard listeners
   */
  useEffect(() => {
    if (!enabled) {
      return;
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [enabled, handleKeyDown]);

  /**
   * Return value
   */
  const shortcuts = useMemo(() => SHORTCUTS, []);

  return {
    shortcuts,
    isEnabled: enabled,
  };
}

export default useTimelineKeyboard;
