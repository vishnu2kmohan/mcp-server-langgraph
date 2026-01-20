/**
 * Tooltip Component
 *
 * A lightweight hover tooltip for displaying additional information.
 * Supports different positions and rich content.
 * Uses CVA for type-safe position variants.
 */

import { cva, type VariantProps } from "class-variance-authority";
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
import { cn } from "../../utils/cn";

/**
 * Tooltip variant styles using CVA
 */
export const tooltipVariants = cva(
  // Base styles
  [
    "fixed z-tooltip px-2 py-1 text-sm rounded shadow-lg",
    "bg-neutral-2 text-neutral-12",
    "animate-in fade-in-0 zoom-in-95 duration-150",
  ],
  {
    variants: {
      position: {
        top: "tooltip-top",
        right: "tooltip-right",
        bottom: "tooltip-bottom",
        left: "tooltip-left",
      },
    },
    defaultVariants: {
      position: "top",
    },
  },
);

/**
 * Arrow position styles using CVA
 */
export const tooltipArrowVariants = cva(
  "absolute w-2 h-2 bg-neutral-2 rotate-45",
  {
    variants: {
      position: {
        top: "bottom-[-4px] left-1/2 -translate-x-1/2",
        right: "left-[-4px] top-1/2 -translate-y-1/2",
        bottom: "top-[-4px] left-1/2 -translate-x-1/2",
        left: "right-[-4px] top-1/2 -translate-y-1/2",
      },
    },
    defaultVariants: {
      position: "top",
    },
  },
);

export type TooltipPosition = NonNullable<
  VariantProps<typeof tooltipVariants>["position"]
>;

export interface TooltipProps extends VariantProps<typeof tooltipVariants> {
  /** The content to display in the tooltip */
  content: ReactNode;
  /** The element that triggers the tooltip */
  children: ReactElement;
  /** Delay before showing tooltip in ms */
  delay?: number;
  /** Disable the tooltip */
  disabled?: boolean;
  /** Custom class for the tooltip */
  className?: string;
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
  const resolvedPosition = position ?? "top";

  return (
    <>
      {trigger}
      {isVisible &&
        triggerRect &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            className={cn(tooltipVariants({ position }), className)}
            style={getPositionStyles(resolvedPosition, triggerRect)}
          >
            {content}
            {/* Arrow */}
            <div
              className={tooltipArrowVariants({ position })}
              aria-hidden="true"
            />
          </div>,
          document.body,
        )}
    </>
  );
}

Tooltip.displayName = "Tooltip";
