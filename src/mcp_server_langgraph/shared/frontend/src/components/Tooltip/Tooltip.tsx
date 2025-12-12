/**
 * Tooltip Component
 *
 * Accessible tooltip system for showing contextual help.
 * Supports keyboard navigation, custom positioning, and theming.
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  useId,
  ReactNode,
  ReactElement,
  cloneElement,
  isValidElement,
} from 'react';

// =============================================================================
// Types
// =============================================================================

export interface TooltipProviderProps {
  children: ReactNode;
  /** Delay in ms before showing tooltip (default: 200) */
  delayDuration?: number;
  /** Delay in ms before hiding tooltip after leaving (default: 0) */
  skipDelayDuration?: number;
}

export interface TooltipProps {
  children: ReactNode;
  /** Open state for controlled usage */
  open?: boolean;
  /** Default open state */
  defaultOpen?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
}

export interface TooltipTriggerProps {
  children: ReactNode;
  /** Merge props with child element */
  asChild?: boolean;
}

export interface TooltipContentProps {
  children: ReactNode;
  /** Side of trigger to show tooltip */
  side?: 'top' | 'right' | 'bottom' | 'left';
  /** Alignment relative to trigger */
  align?: 'start' | 'center' | 'end';
  /** Additional CSS classes */
  className?: string;
  /** Styling variant */
  variant?: 'default' | 'dark';
  /** Offset from trigger in pixels */
  sideOffset?: number;
}

// =============================================================================
// Context
// =============================================================================

interface TooltipContextValue {
  delayDuration: number;
  skipDelayDuration: number;
}

const TooltipProviderContext = createContext<TooltipContextValue>({
  delayDuration: 200,
  skipDelayDuration: 0,
});

interface TooltipStateContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  triggerId: string;
  contentId: string;
  triggerRef: React.RefObject<HTMLElement>;
}

const TooltipStateContext = createContext<TooltipStateContextValue | null>(null);

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// =============================================================================
// TooltipProvider Component
// =============================================================================

export function TooltipProvider({
  children,
  delayDuration = 200,
  skipDelayDuration = 0,
}: TooltipProviderProps): ReactElement {
  return (
    <TooltipProviderContext.Provider value={{ delayDuration, skipDelayDuration }}>
      {children}
    </TooltipProviderContext.Provider>
  );
}

// =============================================================================
// Tooltip Component
// =============================================================================

export function Tooltip({
  children,
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
}: TooltipProps): ReactElement {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const open = controlledOpen ?? uncontrolledOpen;
  const triggerId = useId();
  const contentId = useId();
  const triggerRef = useRef<HTMLElement>(null);

  const setOpen = useCallback(
    (newOpen: boolean) => {
      setUncontrolledOpen(newOpen);
      onOpenChange?.(newOpen);
    },
    [onOpenChange]
  );

  return (
    <TooltipStateContext.Provider
      value={{ open, setOpen, triggerId, contentId, triggerRef }}
    >
      {children}
    </TooltipStateContext.Provider>
  );
}

// =============================================================================
// TooltipTrigger Component
// =============================================================================

export function TooltipTrigger({
  children,
  asChild = false,
}: TooltipTriggerProps): ReactElement {
  const context = useContext(TooltipStateContext);
  const providerContext = useContext(TooltipProviderContext);

  if (!context) {
    throw new Error('TooltipTrigger must be used within a Tooltip');
  }

  const { open, setOpen, triggerId, contentId, triggerRef } = context;
  const { delayDuration } = providerContext;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setOpen(true);
    }, delayDuration);
  }, [setOpen, delayDuration]);

  const handleMouseLeave = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setOpen(false);
  }, [setOpen]);

  const handleFocus = useCallback(() => {
    setOpen(true);
  }, [setOpen]);

  const handleBlur = useCallback(() => {
    setOpen(false);
  }, [setOpen]);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const triggerProps = {
    id: triggerId,
    'aria-describedby': open ? contentId : undefined,
    onMouseEnter: handleMouseEnter,
    onMouseLeave: handleMouseLeave,
    onFocus: handleFocus,
    onBlur: handleBlur,
    ref: triggerRef,
  };

  if (asChild && isValidElement(children)) {
    return cloneElement(children as ReactElement<Record<string, unknown>>, triggerProps);
  }

  return <span {...triggerProps}>{children}</span>;
}

// =============================================================================
// TooltipContent Component
// =============================================================================

export function TooltipContent({
  children,
  side = 'top',
  align = 'center',
  className,
  variant = 'default',
  sideOffset = 4,
}: TooltipContentProps): ReactElement | null {
  const context = useContext(TooltipStateContext);

  if (!context) {
    throw new Error('TooltipContent must be used within a Tooltip');
  }

  const { open, contentId, triggerRef } = context;
  const contentRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  // Calculate position based on trigger element
  useEffect(() => {
    if (open && triggerRef.current && contentRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const contentRect = contentRef.current.getBoundingClientRect();

      let top = 0;
      let left = 0;

      // Calculate based on side
      switch (side) {
        case 'top':
          top = triggerRect.top - contentRect.height - sideOffset;
          left = triggerRect.left + triggerRect.width / 2 - contentRect.width / 2;
          break;
        case 'bottom':
          top = triggerRect.bottom + sideOffset;
          left = triggerRect.left + triggerRect.width / 2 - contentRect.width / 2;
          break;
        case 'left':
          top = triggerRect.top + triggerRect.height / 2 - contentRect.height / 2;
          left = triggerRect.left - contentRect.width - sideOffset;
          break;
        case 'right':
          top = triggerRect.top + triggerRect.height / 2 - contentRect.height / 2;
          left = triggerRect.right + sideOffset;
          break;
      }

      // Adjust for alignment
      if (side === 'top' || side === 'bottom') {
        if (align === 'start') {
          left = triggerRect.left;
        } else if (align === 'end') {
          left = triggerRect.right - contentRect.width;
        }
      } else {
        if (align === 'start') {
          top = triggerRect.top;
        } else if (align === 'end') {
          top = triggerRect.bottom - contentRect.height;
        }
      }

      setPosition({ top, left });
    }
  }, [open, side, align, sideOffset, triggerRef]);

  if (!open) {
    return null;
  }

  const baseStyles = clsx(
    'fixed z-50 px-3 py-1.5 text-sm rounded-md shadow-md',
    'animate-in fade-in-0 zoom-in-95',
    variant === 'default' && 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900',
    variant === 'dark' && 'bg-gray-800 text-white',
    className
  );

  return (
    <div
      ref={contentRef}
      id={contentId}
      role="tooltip"
      className={baseStyles}
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        pointerEvents: 'none',
      }}
    >
      {children}
    </div>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default Tooltip;
