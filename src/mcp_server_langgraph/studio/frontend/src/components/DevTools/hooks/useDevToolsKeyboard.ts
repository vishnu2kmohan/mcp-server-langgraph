/**
 * useDevToolsKeyboard Hook
 *
 * Provides keyboard shortcuts for DevTools:
 * - Cmd+Shift+I: Toggle DevTools panel
 * - Cmd+Shift+C: Focus Console tab
 * - Cmd+K: Clear console
 * - Cmd+]: Next tab
 * - Cmd+[: Previous tab
 */
import { useEffect, useCallback, useMemo } from "react";

import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import {
  toggleDevTools,
  setActiveTab,
  selectActiveTab,
  selectAvailableTabs,
} from "../../../store/slices/devToolsSlice";
import type { DevToolsTabId } from "../types";

// =============================================================================
// Types
// =============================================================================

export interface UseDevToolsKeyboardOptions {
  /** Whether keyboard shortcuts are enabled */
  enabled: boolean;
  /** Callback when Cmd+K (clear console) is pressed */
  onClearConsole?: () => void;
}

export interface KeyboardShortcut {
  /** Key to press */
  key: string;
  /** Modifier keys required */
  modifiers: ("meta" | "ctrl" | "shift" | "alt")[];
  /** Human-readable description */
  description: string;
  /** Action ID */
  action: string;
}

export interface UseDevToolsKeyboardReturn {
  /** List of registered shortcuts */
  shortcuts: KeyboardShortcut[];
  /** Whether shortcuts are enabled */
  isEnabled: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const SHORTCUTS: KeyboardShortcut[] = [
  {
    key: "i",
    modifiers: ["meta", "shift"],
    description: "Toggle DevTools",
    action: "toggle",
  },
  {
    key: "c",
    modifiers: ["meta", "shift"],
    description: "Focus Console",
    action: "focus-console",
  },
  {
    key: "k",
    modifiers: ["meta"],
    description: "Clear Console",
    action: "clear-console",
  },
  {
    key: "]",
    modifiers: ["meta"],
    description: "Next Tab",
    action: "next-tab",
  },
  {
    key: "[",
    modifiers: ["meta"],
    description: "Previous Tab",
    action: "prev-tab",
  },
];

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsKeyboard(
  options: UseDevToolsKeyboardOptions
): UseDevToolsKeyboardReturn {
  const { enabled, onClearConsole } = options;

  const dispatch = useAppDispatch();
  const activeTab = useAppSelector(selectActiveTab);
  const availableTabs = useAppSelector(selectAvailableTabs);

  /**
   * Navigate to next tab
   */
  const goToNextTab = useCallback(() => {
    const currentIndex = availableTabs.indexOf(activeTab);
    const nextIndex = (currentIndex + 1) % availableTabs.length;
    dispatch(setActiveTab(availableTabs[nextIndex] as DevToolsTabId));
  }, [availableTabs, activeTab, dispatch]);

  /**
   * Navigate to previous tab
   */
  const goToPrevTab = useCallback(() => {
    const currentIndex = availableTabs.indexOf(activeTab);
    const prevIndex =
      currentIndex === 0 ? availableTabs.length - 1 : currentIndex - 1;
    dispatch(setActiveTab(availableTabs[prevIndex] as DevToolsTabId));
  }, [availableTabs, activeTab, dispatch]);

  /**
   * Handle keyboard events
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const { key, metaKey, ctrlKey, shiftKey } = event;
      const modKey = metaKey || ctrlKey; // Support both Mac and Windows/Linux

      // Cmd+Shift+I or Ctrl+Shift+I - Toggle DevTools
      if (modKey && shiftKey && key.toLowerCase() === "i") {
        event.preventDefault();
        dispatch(toggleDevTools());
        return;
      }

      // Cmd+Shift+C or Ctrl+Shift+C - Focus Console
      if (modKey && shiftKey && key.toLowerCase() === "c") {
        event.preventDefault();
        dispatch(setActiveTab("console"));
        return;
      }

      // Cmd+K or Ctrl+K - Clear Console
      if (modKey && !shiftKey && key.toLowerCase() === "k") {
        event.preventDefault();
        onClearConsole?.();
        return;
      }

      // Cmd+] or Ctrl+] - Next Tab
      if (modKey && !shiftKey && key === "]") {
        event.preventDefault();
        goToNextTab();
        return;
      }

      // Cmd+[ or Ctrl+[ - Previous Tab
      if (modKey && !shiftKey && key === "[") {
        event.preventDefault();
        goToPrevTab();
        return;
      }
    },
    [dispatch, onClearConsole, goToNextTab, goToPrevTab]
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

export default useDevToolsKeyboard;
