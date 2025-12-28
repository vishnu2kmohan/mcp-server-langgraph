/**
 * Tooltip Component
 *
 * A lightweight hover tooltip for displaying additional information.
 * Supports different positions and rich content.
 */

import {
  useState,
  useCallback,
  useId,
  cloneElement,
  isValidElement,
  type ReactNode,
  type ReactElement,
  type HTMLAttributes,
} from "react";
import { createPortal } from "react-dom";

export type TooltipPosition = "top" | "right" | "bottom" | "left";

export interface TooltipProps {
  /** The content to display in the tooltip */
  content: ReactNode;
  /** The element that triggers the tooltip */
  children: ReactElement;
  /** Position of the tooltip relative to the trigger */
  position?: TooltipPosition;
  /** Delay before showing tooltip in ms */
  delay?: number;
  /** Disable the tooltip */
  disabled?: boolean;
  /** Custom class for the tooltip */
  className?: string;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get position-specific class
 */
function getPositionClass(position: TooltipPosition): string {
  return `tooltip-${position}`;
}

/**
 * Calculate tooltip position styles
 */
function getPositionStyles(
  position: TooltipPosition,
  triggerRect: DOMRect,
): React.CSSProperties {
  const gap = 8; // Gap between trigger and tooltip

  switch (position) {
    case "top":
      return {
        bottom: window.innerHeight - triggerRect.top + gap,
        left: triggerRect.left + triggerRect.width / 2,
        transform: "translateX(-50%)",
      };
    case "bottom":
      return {
        top: triggerRect.bottom + gap,
        left: triggerRect.left + triggerRect.width / 2,
        transform: "translateX(-50%)",
      };
    case "left":
      return {
        top: triggerRect.top + triggerRect.height / 2,
        right: window.innerWidth - triggerRect.left + gap,
        transform: "translateY(-50%)",
      };
    case "right":
      return {
        top: triggerRect.top + triggerRect.height / 2,
        left: triggerRect.right + gap,
        transform: "translateY(-50%)",
      };
    default:
      return {};
  }
}

/**
 * Tooltip component for hover information
 */
export function Tooltip({
  content,
  children,
  position = "top",
  delay = 200,
  disabled = false,
  className,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [triggerRect, setTriggerRect] = useState<DOMRect | null>(null);
  const tooltipId = useId();
  const timeoutRef = { current: null as NodeJS.Timeout | null };

  const showTooltip = useCallback(
    (element: HTMLElement) => {
      if (disabled) return;

      timeoutRef.current = setTimeout(() => {
        setTriggerRect(element.getBoundingClientRect());
        setIsVisible(true);
      }, delay);
    },
    [disabled, delay], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const hideTooltip = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleMouseEnter = useCallback(
    (e: React.MouseEvent<HTMLElement>) => {
      showTooltip(e.currentTarget);
    },
    [showTooltip],
  );

  const handleMouseLeave = useCallback(() => {
    hideTooltip();
  }, [hideTooltip]);

  const handleFocus = useCallback(
    (e: React.FocusEvent<HTMLElement>) => {
      showTooltip(e.currentTarget);
    },
    [showTooltip],
  );

  const handleBlur = useCallback(() => {
    hideTooltip();
  }, [hideTooltip]);

  // Clone child with additional props
  if (!isValidElement(children)) {
    return children;
  }

  const childProps: HTMLAttributes<HTMLElement> = {
    onMouseEnter: handleMouseEnter,
    onMouseLeave: handleMouseLeave,
    onFocus: handleFocus,
    onBlur: handleBlur,
    "aria-describedby": isVisible ? tooltipId : undefined,
  };

  const trigger = cloneElement(children, childProps);

  return (
    <>
      {trigger}
      {isVisible &&
        triggerRect &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            className={cn(
              // Base styles
              "fixed z-50 px-2 py-1 text-sm rounded shadow-lg",
              "bg-gray-900 text-white",
              "dark:bg-gray-700",
              // Animation
              "animate-in fade-in-0 zoom-in-95 duration-150",
              // Position class for styling hooks
              getPositionClass(position),
              className,
            )}
            style={getPositionStyles(position, triggerRect)}
          >
            {content}
            {/* Arrow */}
            <div
              className={cn(
                "absolute w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45",
                position === "top" && "bottom-[-4px] left-1/2 -translate-x-1/2",
                position === "bottom" && "top-[-4px] left-1/2 -translate-x-1/2",
                position === "left" && "right-[-4px] top-1/2 -translate-y-1/2",
                position === "right" && "left-[-4px] top-1/2 -translate-y-1/2",
              )}
              aria-hidden="true"
            />
          </div>,
          document.body,
        )}
    </>
  );
}

Tooltip.displayName = "Tooltip";
