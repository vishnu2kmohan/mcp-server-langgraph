/**
 * SplitContainer Component
 *
 * Recursive split layout container for JupyterLab-inspired dock area.
 * Features:
 * - Tab groups with tabs
 * - Horizontal and vertical splits
 * - Nested splits (tree structure)
 * - Drop zones for drag-to-split
 * - Resizable panels via react-resizable-panels
 */

import { useCallback, useState, type ReactNode } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import {
  X,
  MessageSquare,
  GitBranch,
  Settings,
  Activity,
  DollarSign,
  FolderKanban,
  SplitSquareHorizontal,
  SplitSquareVertical,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectTabs,
  selectActiveTabId,
  setActiveTabId,
  removeTab,
  type DockLayout,
  type TabState,
} from "../../store/slices/workspaceSlice";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface SplitInfo {
  direction: "horizontal" | "vertical";
  position: "before" | "after";
  sourceTabId: string;
}

export interface SplitContainerProps {
  /** The dock layout to render */
  layout: DockLayout;
  /** Custom content renderer for tabs */
  renderTabContent?: (tab: TabState) => ReactNode;
  /** Whether a tab is being dragged (shows drop zones) */
  isDragging?: boolean;
  /** Callback when a tab is dropped to create a split */
  onSplit?: (info: SplitInfo) => void;
  /** Callback when panels are resized */
  onResize?: (sizes: number[]) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Tab Icon Map
// =============================================================================

function getTabIcon(type: TabState["type"]) {
  switch (type) {
    case "chat":
      return <MessageSquare size={14} />;
    case "workflow":
      return <GitBranch size={14} />;
    case "project":
      return <FolderKanban size={14} />;
    case "settings":
      return <Settings size={14} />;
    case "observability":
      return <Activity size={14} />;
    case "cost":
      return <DollarSign size={14} />;
    default:
      return null;
  }
}

// =============================================================================
// Drop Zone Component
// =============================================================================

interface DropZoneProps {
  position: "top" | "right" | "bottom" | "left";
  onDrop: (sourceTabId: string) => void;
}

function DropZone({ position, onDrop }: DropZoneProps) {
  const [isOver, setIsOver] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = "move";
    }
    setIsOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const sourceTabId = e.dataTransfer.getData("text/plain");
      if (sourceTabId) {
        onDrop(sourceTabId);
      }
      setIsOver(false);
    },
    [onDrop],
  );

  const positionClasses: Record<string, string> = {
    top: "top-0 left-0 right-0 h-1/4",
    right: "top-0 right-0 bottom-0 w-1/4",
    bottom: "bottom-0 left-0 right-0 h-1/4",
    left: "top-0 left-0 bottom-0 w-1/4",
  };

  // Position-specific styles for the indicator
  const indicatorPositionClasses: Record<string, string> = {
    top: "top-2 left-1/2 -translate-x-1/2",
    right: "right-2 top-1/2 -translate-y-1/2",
    bottom: "bottom-2 left-1/2 -translate-x-1/2",
    left: "left-2 top-1/2 -translate-y-1/2",
  };

  // Get the indicator icon for each position
  const getIndicatorIcon = () => {
    const iconProps = {
      size: 16,
      className: "text-primary-600 dark:text-primary-400",
    };
    switch (position) {
      case "left":
        return <SplitSquareHorizontal {...iconProps} />;
      case "right":
        return <SplitSquareHorizontal {...iconProps} />;
      case "top":
        return <SplitSquareVertical {...iconProps} />;
      case "bottom":
        return <SplitSquareVertical {...iconProps} />;
    }
  };

  // Border style for visual preview of split location
  const borderClasses: Record<string, string> = {
    top: "border-b-2 border-primary-500",
    right: "border-l-2 border-primary-500",
    bottom: "border-t-2 border-primary-500",
    left: "border-r-2 border-primary-500",
  };

  return (
    <div
      data-testid={`drop-zone-${position}`}
      className={cn(
        "absolute z-50 transition-all duration-150 pointer-events-auto",
        "flex items-center justify-center",
        positionClasses[position],
        isOver && "bg-primary-500/20",
        isOver && borderClasses[position],
        !isOver && "bg-transparent hover:bg-primary-500/10",
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Indicator icon shown when hovering */}
      <div
        className={cn(
          "absolute p-1.5 rounded-full transition-all duration-150",
          indicatorPositionClasses[position],
          isOver && "bg-primary-100 dark:bg-primary-900/50 scale-110",
          !isOver && "bg-white/80 dark:bg-gray-800/80 scale-100 opacity-70",
        )}
      >
        {getIndicatorIcon()}
      </div>
    </div>
  );
}

// =============================================================================
// Tab Group Component
// =============================================================================

interface TabGroupProps {
  tabIds: string[];
  renderTabContent?: (tab: TabState) => ReactNode;
  isDragging?: boolean;
  onSplit?: (info: SplitInfo) => void;
}

function TabGroup({
  tabIds,
  renderTabContent,
  isDragging,
  onSplit,
}: TabGroupProps) {
  const dispatch = useAppDispatch();
  const allTabs = useAppSelector(selectTabs);
  const activeTabId = useAppSelector(selectActiveTabId);

  // Filter to only tabs in this group
  const tabs = allTabs.filter((t) => tabIds.includes(t.id));
  const activeTab = tabs.find((t) => t.id === activeTabId) || tabs[0];

  const handleSelectTab = useCallback(
    (tabId: string) => {
      dispatch(setActiveTabId(tabId));
    },
    [dispatch],
  );

  const handleCloseTab = useCallback(
    (tabId: string, event: React.MouseEvent) => {
      event.stopPropagation();
      dispatch(removeTab(tabId));
    },
    [dispatch],
  );

  const handleDropZone = useCallback(
    (position: "top" | "right" | "bottom" | "left") =>
      (sourceTabId: string) => {
        if (!onSplit) return;

        const direction =
          position === "top" || position === "bottom"
            ? "vertical"
            : "horizontal";
        const pos =
          position === "top" || position === "left" ? "before" : "after";

        onSplit({
          direction,
          position: pos,
          sourceTabId,
        });
      },
    [onSplit],
  );

  return (
    <div data-testid="tab-group" className="relative flex flex-col h-full">
      {/* Drop zones (shown when dragging) */}
      {isDragging && (
        <div className="absolute inset-0 z-40 pointer-events-none">
          <DropZone position="top" onDrop={handleDropZone("top")} />
          <DropZone position="right" onDrop={handleDropZone("right")} />
          <DropZone position="bottom" onDrop={handleDropZone("bottom")} />
          <DropZone position="left" onDrop={handleDropZone("left")} />
        </div>
      )}

      {/* Tab bar */}
      <div
        role="tablist"
        className={cn(
          "flex items-center gap-0.5 px-2 h-9",
          "border-b border-gray-200 dark:border-gray-700",
          "bg-gray-50 dark:bg-gray-800",
          "overflow-x-auto",
        )}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab?.id;
          const icon = getTabIcon(tab.type);

          return (
            <div
              key={tab.id}
              role="tab"
              tabIndex={0}
              aria-selected={isActive}
              onClick={() => handleSelectTab(tab.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleSelectTab(tab.id);
                }
              }}
              className={cn(
                "group flex items-center gap-1.5 px-3 py-1.5 h-8 cursor-pointer",
                "text-sm font-medium rounded-t transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset",
                isActive && "bg-white dark:bg-gray-900",
                isActive && "text-gray-900 dark:text-gray-100",
                isActive && "border-t-2 border-primary-500",
                !isActive && "text-gray-500 dark:text-gray-400",
                !isActive && "hover:text-gray-700 dark:hover:text-gray-200",
                !isActive && "hover:bg-gray-100 dark:hover:bg-gray-700",
              )}
            >
              {icon && <span className="flex-shrink-0">{icon}</span>}
              <span className="truncate max-w-32">{tab.title}</span>
              <button
                type="button"
                aria-label={`Close ${tab.title}`}
                onClick={(e) => handleCloseTab(tab.id, e)}
                className={cn(
                  "p-0.5 rounded opacity-0 group-hover:opacity-100",
                  "hover:bg-gray-200 dark:hover:bg-gray-600",
                  "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
                  "focus:opacity-100 focus:outline-none focus:ring-1 focus:ring-primary-500",
                  "transition-opacity",
                )}
              >
                <X size={12} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Tab content */}
      <div role="tabpanel" className="flex-1 overflow-auto">
        {activeTab && renderTabContent ? (
          renderTabContent(activeTab)
        ) : activeTab ? (
          <div className="p-4 text-gray-500 dark:text-gray-400">
            <p>Content for: {activeTab.title}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// =============================================================================
// Main SplitContainer Component
// =============================================================================

export function SplitContainer({
  layout,
  renderTabContent,
  isDragging = false,
  onSplit,
  onResize,
  className,
}: SplitContainerProps) {
  const handleResize = useCallback(
    (sizes: number[]) => {
      if (onResize) {
        onResize(sizes);
      }
    },
    [onResize],
  );

  // Render based on layout type
  const renderLayout = (currentLayout: DockLayout): ReactNode => {
    switch (currentLayout.type) {
      case "tab-group":
        return (
          <TabGroup
            tabIds={currentLayout.tabIds || []}
            renderTabContent={renderTabContent}
            isDragging={isDragging}
            onSplit={onSplit}
          />
        );

      case "horizontal-split":
      case "vertical-split": {
        const direction =
          currentLayout.type === "horizontal-split" ? "horizontal" : "vertical";
        const children = currentLayout.children || [];
        const sizes =
          currentLayout.sizes || children.map(() => 100 / children.length);

        return (
          <PanelGroup
            direction={direction}
            className="h-full"
            onLayout={handleResize}
          >
            {children.map((child, index) => (
              <div key={index} className="contents">
                <Panel defaultSize={sizes[index]} minSize={10}>
                  {renderLayout(child)}
                </Panel>
                {index < children.length - 1 && (
                  <PanelResizeHandle
                    className={cn(
                      direction === "horizontal" ? "w-1" : "h-1",
                      "bg-gray-200 dark:bg-gray-700",
                      "hover:bg-primary-500 transition-colors",
                      "cursor-col-resize",
                    )}
                  />
                )}
              </div>
            ))}
          </PanelGroup>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div data-testid="split-container" className={cn("h-full", className)}>
      {renderLayout(layout)}
    </div>
  );
}

export default SplitContainer;
