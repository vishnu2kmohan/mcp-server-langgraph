/**
 * useCanvasKeyboardNav Hook
 *
 * Provides keyboard navigation shortcuts for the HybridShell canvas.
 *
 * Shortcuts:
 * - Cmd+1: Focus Activity Bar
 * - Cmd+2: Focus Session Nav
 * - Cmd+3: Focus Conversation Panel
 * - Cmd+4: Focus Canvas Panel
 *
 * Works with both Cmd (Mac) and Ctrl (Windows/Linux).
 */
import { useEffect, useCallback, type RefObject } from "react";

// =============================================================================
// Types
// =============================================================================

export interface CanvasKeyboardNavRefs {
  activityBarRef: RefObject<HTMLElement | null>;
  sessionNavRef: RefObject<HTMLElement | null>;
  conversationRef: RefObject<HTMLElement | null>;
  canvasRef: RefObject<HTMLElement | null>;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for canvas keyboard navigation.
 *
 * @param refs - Object containing refs to focusable panel elements
 */
export function useCanvasKeyboardNav(refs: CanvasKeyboardNavRefs): void {
  const {
    activityBarRef,
    sessionNavRef,
    conversationRef,
    canvasRef,
  } = refs;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Check for Cmd (Mac) or Ctrl (Windows/Linux)
      if (!e.metaKey && !e.ctrlKey) {
        return;
      }

      // Number key shortcuts for panel focus
      switch (e.key) {
        case "1":
          e.preventDefault();
          activityBarRef.current?.focus();
          break;
        case "2":
          e.preventDefault();
          sessionNavRef.current?.focus();
          break;
        case "3":
          e.preventDefault();
          conversationRef.current?.focus();
          break;
        case "4":
          e.preventDefault();
          canvasRef.current?.focus();
          break;
      }
    },
    [activityBarRef, sessionNavRef, conversationRef, canvasRef],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}
