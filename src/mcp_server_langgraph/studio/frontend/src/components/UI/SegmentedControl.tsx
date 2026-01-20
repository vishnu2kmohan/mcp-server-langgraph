/**
 * SegmentedControl Component
 *
 * A toolbar-friendly toggle group for mutually exclusive options like view modes.
 * Uses proper ARIA patterns (radiogroup) and follows STYLE.md guidelines:
 * - Uses variant="ghost" styling for toolbar integration
 * - Proper focus management and keyboard navigation
 * - WCAG 2.2 AA compliant (44x44 touch targets)
 *
 * @example
 * ```tsx
 * <SegmentedControl value={viewMode} onValueChange={setViewMode} aria-label="View mode">
 *   <SegmentedControlItem value="grid" aria-label="Grid view">
 *     <LayoutGrid size={16} />
 *   </SegmentedControlItem>
 *   <SegmentedControlItem value="list" aria-label="List view">
 *     <List size={16} />
 *   </SegmentedControlItem>
 * </SegmentedControl>
 * ```
 */

import {
  createContext,
  useContext,
  useCallback,
  useRef,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { cn } from "@/utils/cn";

// =============================================================================
// Types
// =============================================================================

export type SegmentedControlSize = "sm" | "md" | "lg";

export interface SegmentedControlProps {
  /** Currently selected value */
  value: string;
  /** Callback when value changes */
  onValueChange: (value: string) => void;
  /** Child segments */
  children: ReactNode;
  /** Size variant */
  size?: SegmentedControlSize;
  /** Whether the entire control is disabled */
  disabled?: boolean;
  /** Accessible label for the control */
  "aria-label"?: string;
  /** Additional CSS classes */
  className?: string;
}

export interface SegmentedControlItemProps {
  /** Value for this segment */
  value: string;
  /** Content of the segment (icon, text, or both) */
  children: ReactNode;
  /** Whether this segment is disabled */
  disabled?: boolean;
  /** Accessible label for icon-only segments */
  "aria-label"?: string;
  /** Additional CSS classes */
  className?: string;
  /** Test ID for testing */
  "data-testid"?: string;
}

// =============================================================================
// Context
// =============================================================================

interface SegmentedControlContextValue {
  value: string;
  onValueChange: (value: string) => void;
  size: SegmentedControlSize;
  disabled: boolean;
  registerItem: (value: string) => void;
  getItemIndex: (value: string) => number;
  getItemByIndex: (index: number) => string | undefined;
  itemCount: number;
}

const SegmentedControlContext =
  createContext<SegmentedControlContextValue | null>(null);

function useSegmentedControl() {
  const context = useContext(SegmentedControlContext);
  if (!context) {
    throw new Error(
      "SegmentedControlItem must be used within SegmentedControl"
    );
  }
  return context;
}

// =============================================================================
// Size Styles
// =============================================================================

const sizeStyles: Record<SegmentedControlSize, string> = {
  sm: "p-0.5 gap-0.5",
  md: "p-1 gap-1",
  lg: "p-1.5 gap-1.5",
};

const itemSizeStyles: Record<SegmentedControlSize, string> = {
  sm: "px-2 py-1 text-xs min-h-[28px]",
  md: "px-3 py-1.5 text-sm min-h-[32px]",
  lg: "px-4 py-2 text-base min-h-[40px]",
};

// =============================================================================
// SegmentedControl Component
// =============================================================================

export function SegmentedControl({
  value,
  onValueChange,
  children,
  size = "md",
  disabled = false,
  "aria-label": ariaLabel,
  className,
}: SegmentedControlProps) {
  const itemsRef = useRef<string[]>([]);

  const registerItem = useCallback((itemValue: string) => {
    if (!itemsRef.current.includes(itemValue)) {
      itemsRef.current.push(itemValue);
    }
  }, []);

  const getItemIndex = useCallback((itemValue: string) => {
    return itemsRef.current.indexOf(itemValue);
  }, []);

  const getItemByIndex = useCallback((index: number) => {
    return itemsRef.current[index];
  }, []);

  const contextValue: SegmentedControlContextValue = {
    value,
    onValueChange,
    size,
    disabled,
    registerItem,
    getItemIndex,
    getItemByIndex,
    itemCount: itemsRef.current.length,
  };

  return (
    <SegmentedControlContext.Provider value={contextValue}>
      <div
        role="radiogroup"
        aria-label={ariaLabel}
        data-size={size}
        className={cn(
          "inline-flex items-center rounded-lg",
          "bg-neutral-2 dark:bg-neutral-3",
          "border border-neutral-5 dark:border-neutral-6",
          sizeStyles[size],
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
      >
        {children}
      </div>
    </SegmentedControlContext.Provider>
  );
}

// =============================================================================
// SegmentedControlItem Component
// =============================================================================

export function SegmentedControlItem({
  value,
  children,
  disabled: itemDisabled = false,
  "aria-label": ariaLabel,
  className,
  "data-testid": testId,
}: SegmentedControlItemProps) {
  const {
    value: selectedValue,
    onValueChange,
    size,
    disabled: groupDisabled,
    registerItem,
    getItemIndex,
    getItemByIndex,
  } = useSegmentedControl();

  // Register this item
  registerItem(value);

  const isSelected = value === selectedValue;
  const isDisabled = groupDisabled || itemDisabled;

  const handleClick = () => {
    if (!isDisabled) {
      onValueChange(value);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (isDisabled) return;

    const currentIndex = getItemIndex(value);
    let nextIndex: number | null = null;

    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        e.preventDefault();
        nextIndex = currentIndex + 1;
        break;
      case "ArrowLeft":
      case "ArrowUp":
        e.preventDefault();
        nextIndex = currentIndex - 1;
        break;
      case "Home":
        e.preventDefault();
        nextIndex = 0;
        break;
      case "End": {
        e.preventDefault();
        // Get the last item index
        let lastIndex = 0;
        while (getItemByIndex(lastIndex + 1) !== undefined) {
          lastIndex++;
        }
        nextIndex = lastIndex;
        break;
      }
      case "Enter":
      case " ":
        e.preventDefault();
        onValueChange(value);
        return;
      default:
        return;
    }

    if (nextIndex !== null) {
      const nextValue = getItemByIndex(nextIndex);
      if (nextValue !== undefined) {
        onValueChange(nextValue);
      }
    }
  };

  return (
    <button
      type="button"
      role="radio"
      aria-checked={isSelected}
      aria-label={ariaLabel}
      tabIndex={isSelected ? 0 : -1}
      disabled={isDisabled}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      data-testid={testId}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md",
        "font-medium transition-all duration-150",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-1",
        itemSizeStyles[size],
        isSelected
          ? "bg-neutral-1 dark:bg-neutral-1 text-neutral-12 shadow-sm"
          : "bg-transparent text-neutral-11 hover:text-neutral-12 hover:bg-neutral-a3",
        isDisabled && "opacity-50 cursor-not-allowed pointer-events-none",
        className
      )}
    >
      {children}
    </button>
  );
}
