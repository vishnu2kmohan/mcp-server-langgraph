/**
 * useFocusTrap Hook (Sprint 3.3)
 *
 * Traps keyboard focus within a container element, cycling through
 * focusable elements on Tab/Shift+Tab. Required for WCAG 2.1 AA
 * compliance for modal dialogs.
 *
 * Usage:
 *   const ref = useRef<HTMLDivElement>(null);
 *   useFocusTrap(ref, isModalOpen);
 *
 *   return <div ref={ref}>...modal content...</div>;
 */
import { useEffect, type RefObject } from "react";

/**
 * Selector for all focusable elements
 */
const FOCUSABLE_SELECTOR = [
  "button:not([disabled]):not([tabindex='-1'])",
  "[href]:not([tabindex='-1'])",
  "input:not([disabled]):not([tabindex='-1'])",
  "select:not([disabled]):not([tabindex='-1'])",
  "textarea:not([disabled]):not([tabindex='-1'])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

/**
 * Get all focusable elements within a container
 */
function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const elements = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
  return Array.from(elements).filter((el) => {
    // Check if element is visible (hidden elements have display: none or visibility: hidden)
    // Note: offsetParent is null in JSDOM, so we check computed styles instead
    const style = window.getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden";
  });
}

/**
 * Hook to trap focus within a container element
 *
 * @param ref - React ref to the container element
 * @param isActive - Whether the focus trap is active
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement>,
  isActive: boolean,
): void {
  useEffect(() => {
    if (!isActive || !ref.current) {
      return;
    }

    const container = ref.current;
    const focusableElements = getFocusableElements(container);

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    // Note: lastElement is intentionally unused - we re-query in handleKeyDown for dynamic content
    const _lastElement = focusableElements[focusableElements.length - 1];

    // Focus the first element when trap is activated
    firstElement?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") {
        return;
      }

      // Re-query focusable elements in case DOM changed
      const currentFocusable = getFocusableElements(container);
      if (currentFocusable.length === 0) {
        return;
      }

      const first = currentFocusable[0];
      const last = currentFocusable[currentFocusable.length - 1];

      if (event.shiftKey) {
        // Shift+Tab: If on first element, move to last
        if (document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        }
      } else {
        // Tab: If on last element, move to first
        if (document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };

    container.addEventListener("keydown", handleKeyDown);

    return () => {
      container.removeEventListener("keydown", handleKeyDown);
    };
  }, [ref, isActive]);
}

export default useFocusTrap;
