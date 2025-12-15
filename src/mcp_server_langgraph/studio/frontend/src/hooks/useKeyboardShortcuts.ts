/**
 * useKeyboardShortcuts Hook
 *
 * Provides keyboard shortcut handling for the application.
 * Supports modifier keys (Ctrl, Alt, Shift, Meta) and prevents
 * conflicts with input fields.
 *
 * Usage:
 *   useKeyboardShortcuts({
 *     'ctrl+n': () => openNewDialog(),
 *     'ctrl+f': () => focusSearch(),
 *     'delete': () => deleteSelected(),
 *   });
 */

import { useEffect, useCallback, useRef } from "react";

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  handler: () => void;
  description?: string;
}

export interface ShortcutMap {
  [shortcut: string]: () => void;
}

/**
 * Parse a shortcut string into key components.
 * Examples: "ctrl+n", "alt+shift+d", "escape"
 */
function parseShortcut(shortcut: string): {
  key: string;
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
} {
  const parts = shortcut.toLowerCase().split("+");
  const key = parts.pop() || "";

  return {
    key,
    ctrl: parts.includes("ctrl") || parts.includes("control"),
    alt: parts.includes("alt"),
    shift: parts.includes("shift"),
    meta: parts.includes("meta") || parts.includes("cmd"),
  };
}

/**
 * Check if the current focus is on an input element.
 */
function isInputFocused(): boolean {
  const activeElement = document.activeElement;
  if (!activeElement) return false;

  const tagName = activeElement.tagName.toLowerCase();
  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true;
  }

  // Check for contentEditable elements
  if ((activeElement as HTMLElement).isContentEditable) {
    return true;
  }

  return false;
}

/**
 * Custom hook for handling keyboard shortcuts.
 *
 * @param shortcuts - Map of shortcut strings to handler functions
 * @param options - Configuration options
 */
export function useKeyboardShortcuts(
  shortcuts: ShortcutMap,
  options: {
    enabled?: boolean;
    allowInInputs?: boolean;
    preventDefault?: boolean;
  } = {},
): void {
  const {
    enabled = true,
    allowInInputs = false,
    preventDefault = true,
  } = options;

  // Use ref to avoid re-creating event handler on every render
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Skip if shortcuts are disabled
      if (!enabled) return;

      // Skip if focused on input (unless explicitly allowed)
      if (!allowInInputs && isInputFocused()) {
        // Allow escape in inputs to blur
        if (event.key === "Escape") {
          (document.activeElement as HTMLElement)?.blur?.();
        }
        return;
      }

      // Check each shortcut
      for (const [shortcutStr, handler] of Object.entries(
        shortcutsRef.current,
      )) {
        const shortcut = parseShortcut(shortcutStr);

        // Match key
        const keyMatch =
          event.key.toLowerCase() === shortcut.key ||
          event.code.toLowerCase() === `key${shortcut.key}`;

        // Match modifiers
        const modifiersMatch =
          event.ctrlKey === shortcut.ctrl &&
          event.altKey === shortcut.alt &&
          event.shiftKey === shortcut.shift &&
          event.metaKey === shortcut.meta;

        if (keyMatch && modifiersMatch) {
          if (preventDefault) {
            event.preventDefault();
          }
          handler();
          return;
        }
      }
    },
    [enabled, allowInInputs, preventDefault],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

/**
 * Hook for showing keyboard shortcut hints.
 * Returns formatted shortcut strings for display.
 */
export function useShortcutDisplay(): {
  formatShortcut: (shortcut: string) => string;
  isMac: boolean;
} {
  const isMac =
    typeof navigator !== "undefined" &&
    navigator.platform.toLowerCase().includes("mac");

  const formatShortcut = useCallback(
    (shortcut: string): string => {
      const parts = shortcut.split("+");
      return parts
        .map((part) => {
          const key = part.toLowerCase();
          switch (key) {
            case "ctrl":
            case "control":
              return isMac ? "⌃" : "Ctrl";
            case "alt":
              return isMac ? "⌥" : "Alt";
            case "shift":
              return isMac ? "⇧" : "Shift";
            case "meta":
            case "cmd":
              return isMac ? "⌘" : "Win";
            case "escape":
            case "esc":
              return "Esc";
            case "delete":
            case "backspace":
              return isMac ? "⌫" : "Del";
            case "enter":
            case "return":
              return "↵";
            case "arrowup":
              return "↑";
            case "arrowdown":
              return "↓";
            case "arrowleft":
              return "←";
            case "arrowright":
              return "→";
            default:
              return key.toUpperCase();
          }
        })
        .join(isMac ? "" : "+");
    },
    [isMac],
  );

  return { formatShortcut, isMac };
}

/**
 * Predefined common shortcuts.
 */
export const COMMON_SHORTCUTS = {
  // Navigation
  SEARCH: "ctrl+f",
  NEW: "ctrl+n",
  SAVE: "ctrl+s",
  CLOSE: "escape",

  // Selection
  SELECT_ALL: "ctrl+a",
  DESELECT: "escape",

  // Actions
  DELETE: "delete",
  REFRESH: "ctrl+r",
  UNDO: "ctrl+z",
  REDO: "ctrl+shift+z",

  // Navigation
  UP: "arrowup",
  DOWN: "arrowdown",
  LEFT: "arrowleft",
  RIGHT: "arrowright",
} as const;

export default useKeyboardShortcuts;
