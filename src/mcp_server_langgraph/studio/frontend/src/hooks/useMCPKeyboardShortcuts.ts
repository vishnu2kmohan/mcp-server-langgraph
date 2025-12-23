/**
 * useMCPKeyboardShortcuts Hook
 *
 * Provides keyboard shortcut handling for MCP (Model Context Protocol) dialogs.
 *
 * Shortcuts:
 * - Cmd/Ctrl+M: Toggle MCP connections panel
 * - Cmd/Ctrl+Shift+T: Open tool invocation dialog
 * - Cmd/Ctrl+Shift+R: Open resource viewer
 * - Cmd/Ctrl+Shift+P: Open prompt tester
 * - Escape: Close active MCP dialog
 *
 * Features:
 * - Cross-platform (Mac: Cmd, Windows/Linux: Ctrl)
 * - Does not fire when focus is in input/textarea
 * - Can be disabled via options
 * - Cleans up event listeners on unmount
 */

import { useEffect, useCallback } from "react";

// =============================================================================
// Types
// =============================================================================

export interface MCPKeyboardShortcutsOptions {
  /** Callback when Cmd/Ctrl+M is pressed */
  onToggleMCPPanel?: () => void;
  /** Callback when Cmd/Ctrl+Shift+T is pressed */
  onOpenToolDialog?: () => void;
  /** Callback when Cmd/Ctrl+Shift+R is pressed */
  onOpenResourceViewer?: () => void;
  /** Callback when Cmd/Ctrl+Shift+P is pressed */
  onOpenPromptTester?: () => void;
  /** Callback when Escape is pressed */
  onCloseActiveDialog?: () => void;
  /** Disable all shortcuts */
  disabled?: boolean;
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Check if focus is in an input element (where shortcuts should not fire)
 */
const isInputFocused = (): boolean => {
  const activeElement = document.activeElement;
  if (!activeElement) return false;

  const tagName = activeElement.tagName.toLowerCase();
  return (
    tagName === "input" ||
    tagName === "textarea" ||
    (activeElement as HTMLElement).isContentEditable
  );
};

/**
 * Check if modifier key is pressed (Cmd on Mac, Ctrl on Windows/Linux)
 */
const hasModifierKey = (event: KeyboardEvent): boolean => {
  return event.metaKey || event.ctrlKey;
};

// =============================================================================
// Hook
// =============================================================================

export function useMCPKeyboardShortcuts(
  options: MCPKeyboardShortcutsOptions,
): void {
  const {
    onToggleMCPPanel,
    onOpenToolDialog,
    onOpenResourceViewer,
    onOpenPromptTester,
    onCloseActiveDialog,
    disabled = false,
  } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't handle shortcuts when disabled
      if (disabled) return;

      // Don't handle shortcuts when focus is in an input
      if (isInputFocused()) return;

      const key = event.key.toLowerCase();
      const hasModifier = hasModifierKey(event);
      const hasShift = event.shiftKey;

      // Escape - Close active dialog
      if (key === "escape") {
        onCloseActiveDialog?.();
        return;
      }

      // Cmd/Ctrl+M - Toggle MCP panel
      if (key === "m" && hasModifier && !hasShift) {
        event.preventDefault();
        onToggleMCPPanel?.();
        return;
      }

      // Cmd/Ctrl+Shift+T - Open tool dialog
      if (key === "t" && hasModifier && hasShift) {
        event.preventDefault();
        onOpenToolDialog?.();
        return;
      }

      // Cmd/Ctrl+Shift+R - Open resource viewer
      if (key === "r" && hasModifier && hasShift) {
        event.preventDefault();
        onOpenResourceViewer?.();
        return;
      }

      // Cmd/Ctrl+Shift+P - Open prompt tester
      if (key === "p" && hasModifier && hasShift) {
        event.preventDefault();
        onOpenPromptTester?.();
        return;
      }
    },
    [
      disabled,
      onToggleMCPPanel,
      onOpenToolDialog,
      onOpenResourceViewer,
      onOpenPromptTester,
      onCloseActiveDialog,
    ],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);
}

// =============================================================================
// Shortcut Definitions (for help/documentation)
// =============================================================================

export const MCP_SHORTCUTS = [
  {
    id: "mcp-toggle-panel",
    keys: ["Cmd", "M"],
    description: "Toggle MCP connections panel",
    category: "MCP",
  },
  {
    id: "mcp-tool-dialog",
    keys: ["Cmd", "Shift", "T"],
    description: "Open tool invocation dialog",
    category: "MCP",
  },
  {
    id: "mcp-resource-viewer",
    keys: ["Cmd", "Shift", "R"],
    description: "Open resource viewer",
    category: "MCP",
  },
  {
    id: "mcp-prompt-tester",
    keys: ["Cmd", "Shift", "P"],
    description: "Open prompt tester",
    category: "MCP",
  },
];
