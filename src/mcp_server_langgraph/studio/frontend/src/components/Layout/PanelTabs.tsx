/**
 * PanelTabs Component
 *
 * JupyterLab-style tabbed panels for multi-view sidebars.
 *
 * Features:
 * - Multiple tabs within a panel
 * - Closable tabs
 * - Icons support
 * - Keyboard navigation (arrow keys)
 * - Controlled and uncontrolled modes
 */

import {
  useState,
  useCallback,
  useRef,
  type ReactNode,
  type HTMLAttributes,
  type KeyboardEvent,
} from "react";
import { X } from "lucide-react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface TabDefinition {
  /** Unique tab ID */
  id: string;
  /** Tab label */
  label: string;
  /** Tab content */
  content: ReactNode;
  /** Optional icon */
  icon?: ReactNode;
  /** Whether tab can be closed */
  closable?: boolean;
}

export interface PanelTabsProps {
  /** Tab definitions */
  tabs: TabDefinition[];
  /** Default active tab ID (uncontrolled mode) */
  defaultActiveId?: string;
  /** Active tab ID (controlled mode) */
  activeId?: string;
  /** Callback when tab changes */
  onTabChange?: (id: string) => void;
  /** Callback when tab is closed */
  onTabClose?: (id: string) => void;
  /** Additional class names */
  className?: string;
}

// =============================================================================
// PanelTabs - Main container
// =============================================================================

export function PanelTabs({
  tabs,
  defaultActiveId,
  activeId: controlledActiveId,
  onTabChange,
  onTabClose,
  className,
}: PanelTabsProps) {
  // Internal state for uncontrolled mode
  const [internalActiveId, setInternalActiveId] = useState(
    defaultActiveId ?? tabs[0]?.id ?? "",
  );

  // Use controlled or uncontrolled value
  const isControlled = controlledActiveId !== undefined;
  const activeId = isControlled ? controlledActiveId : internalActiveId;

  // Refs for keyboard navigation
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  // Handle tab selection
  const handleSelect = useCallback(
    (id: string) => {
      if (!isControlled) {
        setInternalActiveId(id);
      }
      onTabChange?.(id);
    },
    [isControlled, onTabChange],
  );

  // Handle tab close
  const handleClose = useCallback(
    (id: string, event: React.MouseEvent) => {
      event.stopPropagation();
      onTabClose?.(id);
    },
    [onTabClose],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (event: KeyboardEvent, currentIndex: number) => {
      let newIndex = currentIndex;

      if (event.key === "ArrowRight") {
        event.preventDefault();
        newIndex = (currentIndex + 1) % tabs.length;
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        newIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        event.preventDefault();
        newIndex = 0;
      } else if (event.key === "End") {
        event.preventDefault();
        newIndex = tabs.length - 1;
      }

      if (newIndex !== currentIndex) {
        const targetTab = tabs[newIndex];
        if (targetTab) {
          const targetElement = tabRefs.current.get(targetTab.id);
          targetElement?.focus();
        }
      }
    },
    [tabs],
  );

  // Find active tab content
  const activeTab = tabs.find((tab) => tab.id === activeId);

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Tab list */}
      <PanelTabList>
        {tabs.map((tab, index) => (
          <div key={tab.id} className="flex items-center">
            <PanelTab
              ref={(el) => {
                if (el) tabRefs.current.set(tab.id, el);
                else tabRefs.current.delete(tab.id);
              }}
              id={tab.id}
              isActive={tab.id === activeId}
              onClick={() => handleSelect(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              icon={tab.icon}
            >
              {tab.label}
            </PanelTab>
            {tab.closable && (
              <button
                type="button"
                onClick={(e) => handleClose(tab.id, e)}
                className={cn(
                  "p-0.5 ml-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700",
                  "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
                  "focus:outline-none focus:ring-1 focus:ring-primary-500",
                )}
                aria-label="Close tab"
              >
                <X size={12} />
              </button>
            )}
          </div>
        ))}
      </PanelTabList>

      {/* Tab content */}
      <PanelTabContent>{activeTab?.content}</PanelTabContent>
    </div>
  );
}

// =============================================================================
// PanelTabList - Container for tabs
// =============================================================================

export interface PanelTabListProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function PanelTabList({
  children,
  className,
  ...props
}: PanelTabListProps) {
  return (
    <div
      role="tablist"
      className={cn(
        "flex gap-0.5 px-2 py-1",
        "border-b border-gray-200 dark:border-gray-700",
        "bg-gray-50 dark:bg-gray-800",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// =============================================================================
// PanelTab - Individual tab button
// =============================================================================

export interface PanelTabProps extends Omit<
  HTMLAttributes<HTMLButtonElement>,
  "id"
> {
  /** Tab ID */
  id: string;
  /** Whether tab is active */
  isActive: boolean;
  /** Tab icon */
  icon?: ReactNode;
  /** Children (label) */
  children: ReactNode;
}

import { forwardRef } from "react";

export const PanelTab = forwardRef<HTMLButtonElement, PanelTabProps>(
  ({ id: _id, isActive, icon, children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        tabIndex={isActive ? 0 : -1}
        className={cn(
          "flex items-center gap-1 px-3 py-1.5 text-sm font-medium",
          "rounded-t transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset",
          // Active state
          isActive && "bg-white dark:bg-gray-900",
          isActive && "text-gray-900 dark:text-gray-100",
          isActive && "border-b-2 border-primary-500",
          // Inactive state
          !isActive && "text-gray-500 dark:text-gray-400",
          !isActive && "hover:text-gray-700 dark:hover:text-gray-200",
          !isActive && "hover:bg-gray-100 dark:hover:bg-gray-700",
          className,
        )}
        {...props}
      >
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span>{children}</span>
      </button>
    );
  },
);

PanelTab.displayName = "PanelTab";

// =============================================================================
// PanelTabContent - Content area for tabs
// =============================================================================

export interface PanelTabContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function PanelTabContent({
  children,
  className,
  ...props
}: PanelTabContentProps) {
  return (
    <div
      role="tabpanel"
      className={cn("flex-1 overflow-auto", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export default PanelTabs;
