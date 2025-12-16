/**
 * DockableLayout Component
 *
 * DevTools-style dockable panel layout using react-resizable-panels.
 * Provides resizable, collapsible panels with persistence support.
 */

import {
  forwardRef,
  type HTMLAttributes,
  type ReactNode,
  createContext,
  useContext,
} from "react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from "react-resizable-panels";

// =============================================================================
// Context for panel group direction
// =============================================================================

type PanelDirection = "horizontal" | "vertical";

const DirectionContext = createContext<PanelDirection>("horizontal");

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// DockableLayout - Main container
// =============================================================================

export interface DockableLayoutProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export const DockableLayout = forwardRef<HTMLDivElement, DockableLayoutProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "h-full w-full overflow-hidden",
          "bg-white dark:bg-gray-900",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);

DockableLayout.displayName = "DockableLayout";

// =============================================================================
// DockablePanelGroup - Container for panels
// =============================================================================

export interface DockablePanelGroupProps {
  /** Layout direction */
  direction: PanelDirection;
  /** Unique ID for persisting panel sizes to localStorage */
  autoSaveId?: string;
  /** Children panels and resize handles */
  children: ReactNode;
  /** Additional class names */
  className?: string;
}

export function DockablePanelGroup({
  direction,
  autoSaveId,
  children,
  className,
}: DockablePanelGroupProps) {
  return (
    <DirectionContext.Provider value={direction}>
      <PanelGroup
        direction={direction}
        autoSaveId={autoSaveId}
        className={cn("h-full w-full", className)}
      >
        {children}
      </PanelGroup>
    </DirectionContext.Provider>
  );
}

// =============================================================================
// DockablePanel - Individual panel
// =============================================================================

export interface DockablePanelProps {
  /** Default panel size (percentage 0-100) */
  defaultSize?: number;
  /** Minimum panel size */
  minSize?: number;
  /** Maximum panel size */
  maxSize?: number;
  /** Whether panel can be collapsed */
  collapsible?: boolean;
  /** Size when collapsed */
  collapsedSize?: number;
  /** Callback when panel is collapsed */
  onCollapse?: () => void;
  /** Callback when panel is expanded */
  onExpand?: () => void;
  /** Panel order for consistent rendering */
  order?: number;
  /** Panel ID for imperative control */
  id?: string;
  /** Panel content */
  children: ReactNode;
  /** Additional class names */
  className?: string;
  /** Data attributes for testing */
  "data-testid"?: string;
}

export const DockablePanel = forwardRef<
  ImperativePanelHandle,
  DockablePanelProps
>(
  (
    {
      defaultSize,
      minSize,
      maxSize,
      collapsible = false,
      collapsedSize = 0,
      onCollapse,
      onExpand,
      order,
      id,
      children,
      className,
      "data-testid": dataTestId,
    },
    ref,
  ) => {
    return (
      <Panel
        ref={ref}
        id={id}
        order={order}
        defaultSize={defaultSize}
        minSize={minSize}
        maxSize={maxSize}
        collapsible={collapsible}
        collapsedSize={collapsedSize}
        onCollapse={onCollapse}
        onExpand={onExpand}
        className={cn("overflow-hidden", className)}
        data-testid={dataTestId}
      >
        {children}
      </Panel>
    );
  },
);

DockablePanel.displayName = "DockablePanel";

// =============================================================================
// DockableResizeHandle - Draggable resize handle
// =============================================================================

export interface DockableResizeHandleProps {
  /** Whether handle is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
  /** Data attributes for testing */
  "data-testid"?: string;
}

export function DockableResizeHandle({
  disabled = false,
  className,
  "data-testid": dataTestId,
}: DockableResizeHandleProps) {
  const direction = useContext(DirectionContext);
  const isHorizontal = direction === "horizontal";

  return (
    <PanelResizeHandle
      disabled={disabled}
      className={cn(
        // Base styles
        "relative flex items-center justify-center",
        "bg-gray-200 dark:bg-gray-700",
        "transition-colors duration-fast",
        // Hover state
        "hover:bg-primary-500 hover:dark:bg-primary-600",
        // Active state
        "active:bg-primary-600 active:dark:bg-primary-700",
        // Direction-specific sizing
        isHorizontal ? "w-1 cursor-col-resize" : "h-1 cursor-row-resize",
        // Disabled state
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
      data-testid={dataTestId}
    >
      {/* Visual grip indicator */}
      <div
        className={cn(
          "rounded-full bg-gray-400 dark:bg-gray-500",
          "opacity-0 transition-opacity duration-fast",
          "group-hover:opacity-100",
          isHorizontal ? "h-8 w-0.5" : "h-0.5 w-8",
        )}
        aria-hidden="true"
      />
    </PanelResizeHandle>
  );
}

// =============================================================================
// PanelHeader - Header for panels with title and actions
// =============================================================================

export interface PanelHeaderProps extends HTMLAttributes<HTMLDivElement> {
  /** Panel title */
  title: string;
  /** Optional icon before title */
  icon?: ReactNode;
  /** Optional action buttons */
  actions?: ReactNode;
}

export function PanelHeader({
  title,
  icon,
  actions,
  className,
  ...props
}: PanelHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between",
        "h-10 px-3",
        "border-b border-gray-200 dark:border-gray-700",
        "bg-gray-50 dark:bg-gray-800",
        className,
      )}
      {...props}
    >
      <div className="flex items-center gap-2">
        {icon && (
          <span className="text-gray-500 dark:text-gray-400">{icon}</span>
        )}
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {title}
        </h3>
      </div>
      {actions && <div className="flex items-center gap-1">{actions}</div>}
    </div>
  );
}

// =============================================================================
// PanelContent - Scrollable content area for panels
// =============================================================================

export interface PanelContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function PanelContent({
  children,
  className,
  ...props
}: PanelContentProps) {
  return (
    <div
      className={cn(
        "flex-1 overflow-auto",
        "bg-white dark:bg-gray-900",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// =============================================================================
// Re-export imperative handle type
// =============================================================================

export type { ImperativePanelHandle };
