/**
 * MainDock Component
 *
 * JupyterLab-inspired main dock area for tabbed documents.
 * Features:
 * - Tabbed interface with close buttons
 * - Redux-managed tab state
 * - Custom content rendering via renderContent prop
 * - Empty state display
 * - Accessibility (ARIA tab structure)
 */

import {
  useCallback,
  useState,
  useRef,
  useEffect,
  type ReactNode,
} from "react";
import {
  X,
  MessageSquare,
  GitBranch,
  Settings,
  Activity,
  DollarSign,
  FolderKanban,
  Check,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectTabs,
  selectActiveTabId,
  selectDockLayout,
  setActiveTabId,
  removeTab,
  reorderTabs,
  splitTab,
  updateTabTitle,
  type TabState,
} from "../../store/slices/workspaceSlice";
import { SplitContainer } from "./SplitContainer";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface MainDockProps {
  /** Custom content renderer for tabs */
  renderContent?: (tab: TabState) => ReactNode;
  /** Whether to use split layout mode (uses SplitContainer) */
  useSplitLayout?: boolean;
  /** Callback when a tab is selected (for navigation) */
  onTabNavigate?: (tab: TabState) => void;
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
// Component
// =============================================================================

export function MainDock({
  renderContent,
  useSplitLayout = false,
  onTabNavigate,
  className,
}: MainDockProps) {
  const dispatch = useAppDispatch();
  const tabs = useAppSelector(selectTabs);
  const activeTabId = useAppSelector(selectActiveTabId);
  const dockLayout = useAppSelector(selectDockLayout);

  // Drag state
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // Tab rename state
  const [editingTabId, setEditingTabId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle tab selection
  const handleSelectTab = useCallback(
    (tabId: string) => {
      dispatch(setActiveTabId(tabId));

      // Call navigation callback if provided
      if (onTabNavigate) {
        const tab = tabs.find((t) => t.id === tabId);
        if (tab) {
          onTabNavigate(tab);
        }
      }
    },
    [dispatch, onTabNavigate, tabs],
  );

  // Handle tab close
  const handleCloseTab = useCallback(
    (tabId: string, event: React.MouseEvent) => {
      event.stopPropagation();
      dispatch(removeTab(tabId));
    },
    [dispatch],
  );

  // Drag handlers
  const handleDragStart = useCallback(
    (index: number, event: React.DragEvent) => {
      setDraggedIndex(index);
      event.dataTransfer.setData("text/plain", String(index));
      event.dataTransfer.effectAllowed = "move";
    },
    [],
  );

  const handleDragOver = useCallback(
    (index: number, event: React.DragEvent) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      setDragOverIndex(index);
    },
    [],
  );

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null);
  }, []);

  const handleDrop = useCallback(
    (toIndex: number, event: React.DragEvent) => {
      event.preventDefault();
      const fromIndex = parseInt(event.dataTransfer.getData("text/plain"), 10);

      if (!isNaN(fromIndex) && fromIndex !== toIndex) {
        dispatch(reorderTabs({ fromIndex, toIndex }));
      }

      setDraggedIndex(null);
      setDragOverIndex(null);
    },
    [dispatch],
  );

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  }, []);

  // Tab rename handlers
  const handleDoubleClick = useCallback(
    (tabId: string, currentTitle: string) => {
      setEditingTabId(tabId);
      setEditingTitle(currentTitle);
    },
    [],
  );

  const handleRenameSubmit = useCallback(
    (tabId: string) => {
      if (editingTitle.trim()) {
        dispatch(updateTabTitle({ tabId, title: editingTitle.trim() }));
      }
      setEditingTabId(null);
      setEditingTitle("");
    },
    [dispatch, editingTitle],
  );

  const handleRenameCancel = useCallback(() => {
    setEditingTabId(null);
    setEditingTitle("");
  }, []);

  const handleRenameKeyDown = useCallback(
    (e: React.KeyboardEvent, tabId: string) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleRenameSubmit(tabId);
      } else if (e.key === "Escape") {
        handleRenameCancel();
      }
    },
    [handleRenameSubmit, handleRenameCancel],
  );

  // Focus input when editing starts
  useEffect(() => {
    if (editingTabId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingTabId]);

  // Handle split from SplitContainer drop zones
  const handleSplit = useCallback(
    (info: {
      direction: "horizontal" | "vertical";
      position: "before" | "after";
      sourceTabId: string;
    }) => {
      dispatch(
        splitTab({
          tabId: info.sourceTabId,
          direction: info.direction,
          position: info.position,
        }),
      );
    },
    [dispatch],
  );

  // Find active tab
  const activeTab = tabs.find((tab) => tab.id === activeTabId);

  // Split layout mode - use SplitContainer
  if (useSplitLayout && dockLayout) {
    return (
      <div
        data-testid="main-dock"
        className={cn(
          "flex flex-col h-full",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <SplitContainer
          layout={dockLayout}
          renderTabContent={renderContent}
          isDragging={draggedIndex !== null}
          onSplit={handleSplit}
        />
      </div>
    );
  }

  // Empty state
  if (tabs.length === 0) {
    return (
      <div
        data-testid="main-dock"
        className={cn(
          "flex flex-col h-full",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <div
          data-testid="dock-tab-bar"
          role="tablist"
          className="h-9 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
        />
        <div
          data-testid="dock-content"
          role="tabpanel"
          className="flex-1 flex items-center justify-center"
        >
          <div
            data-testid="dock-empty-state"
            className="text-center text-gray-500 dark:text-gray-400"
          >
            <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">No documents open</p>
            <p className="text-sm mt-2">
              Start a new chat session or open a workflow to get started
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="main-dock"
      className={cn(
        "flex flex-col h-full",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Tab Bar */}
      <div
        data-testid="dock-tab-bar"
        role="tablist"
        className={cn(
          "flex items-center gap-0.5 px-2 h-9",
          "border-b border-gray-200 dark:border-gray-700",
          "bg-gray-50 dark:bg-gray-800",
          "overflow-x-auto",
        )}
      >
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeTabId;
          const icon = getTabIcon(tab.type);
          const isDragging = draggedIndex === index;
          const isDragOver = dragOverIndex === index;
          const isEditing = editingTabId === tab.id;

          return (
            <div
              key={tab.id}
              role="tab"
              tabIndex={0}
              aria-selected={isActive}
              draggable={!isEditing}
              onDragStart={(e) => !isEditing && handleDragStart(index, e)}
              onDragOver={(e) => handleDragOver(index, e)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(index, e)}
              onDragEnd={handleDragEnd}
              onClick={() => !isEditing && handleSelectTab(tab.id)}
              onDoubleClick={() => handleDoubleClick(tab.id, tab.title)}
              onKeyDown={(e) => {
                if (!isEditing && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  handleSelectTab(tab.id);
                }
              }}
              className={cn(
                "group flex items-center gap-1.5 px-3 py-1.5 h-8 cursor-pointer",
                "text-sm font-medium rounded-t transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset",
                // Active state
                isActive && "bg-white dark:bg-gray-900",
                isActive && "text-gray-900 dark:text-gray-100",
                isActive && "border-t-2 border-primary-500",
                // Inactive state
                !isActive && "text-gray-500 dark:text-gray-400",
                !isActive && "hover:text-gray-700 dark:hover:text-gray-200",
                !isActive && "hover:bg-gray-100 dark:hover:bg-gray-700",
                // Drag state
                isDragging && "opacity-50 scale-95",
                isDragOver &&
                  "border-l-2 border-primary-500 bg-primary-50 dark:bg-primary-900/20",
              )}
            >
              {icon && <span className="flex-shrink-0">{icon}</span>}
              {isEditing ? (
                <div className="flex items-center gap-1">
                  <input
                    ref={inputRef}
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => handleRenameKeyDown(e, tab.id)}
                    onBlur={() => handleRenameSubmit(tab.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-24 px-1 py-0.5 text-sm border border-primary-500 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    data-testid={`tab-rename-input-${tab.id}`}
                  />
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRenameSubmit(tab.id);
                    }}
                    className="p-0.5 text-green-600 hover:text-green-700 dark:text-green-400"
                    aria-label="Save tab name"
                  >
                    <Check size={12} />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRenameCancel();
                    }}
                    className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    aria-label="Cancel rename"
                  >
                    <X size={12} />
                  </button>
                </div>
              ) : (
                <span className="truncate max-w-32">{tab.title}</span>
              )}
              {!isEditing && (
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
              )}
            </div>
          );
        })}
      </div>

      {/* Content Area */}
      <div
        data-testid="dock-content"
        role="tabpanel"
        className="flex-1 overflow-auto"
      >
        {activeTab && renderContent ? (
          renderContent(activeTab)
        ) : activeTab ? (
          <div className="p-4 text-gray-500 dark:text-gray-400">
            <p>Content for: {activeTab.title}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default MainDock;
