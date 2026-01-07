/**
 * useFocusTrap Hook
 *
 * Traps keyboard focus within a container element for accessibility.
 * Used in modal dialogs to prevent focus from escaping.
 *
 * Features:
 * - Traps Tab and Shift+Tab within container
 * - Focuses first focusable element on activation
 * - Cleans up event listeners on deactivation
 * - Supports all standard focusable elements
 *
 * Reference: Plan - StudioShell UX Audit - Sprint 5.2
 */

import { useEffect, useCallback, type RefObject } from "react";

// =============================================================================
// Constants
// =============================================================================

/**
 * Selector for all focusable elements
 */
const FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

// =============================================================================
// Hook
// =============================================================================

/**
 * Traps focus within a container element.
 *
 * @param ref - Ref to the container element
 * @param isActive - Whether the trap is active
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  isActive: boolean,
): void {
  /**
   * Get all focusable elements within the container
   */
  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!ref.current) return [];
    const elements =
      ref.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    return Array.from(elements);
  }, [ref]);

  /**
   * Handle keydown events to trap Tab key
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      // Shift+Tab on first element -> cycle to last
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
        return;
      }

      // Tab on last element -> cycle to first
      if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
        return;
      }
    },
    [getFocusableElements],
  );

  useEffect(() => {
    const element = ref.current;
    if (!element || !isActive) return;

    // Focus the first focusable element when activated
    const focusableElements = getFocusableElements();
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    // Add keydown listener
    element.addEventListener("keydown", handleKeyDown);

    // Cleanup
    return () => {
      element.removeEventListener("keydown", handleKeyDown);
    };
  }, [ref, isActive, getFocusableElements, handleKeyDown]);
}
