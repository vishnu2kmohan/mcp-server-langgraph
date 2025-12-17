/**
 * BottomPanel Component
 *
 * JupyterLab-inspired bottom panel (Down Area) for Agent Studio.
 * Features:
 * - Tabbed interface (Activity, Problems, Inspector)
 * - Collapsible panel
 * - Redux state integration
 * - Accessibility (ARIA tab structure)
 * - Uses extracted sub-components for each tab
 */

import { useCallback } from "react";
import { X, Activity, AlertCircle, Eye } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectBottomPanelActiveTab,
  setBottomPanelActiveTab,
  setBottomPanelCollapsed,
} from "../../store/slices/workspaceSlice";
import { ActivityLog } from "./ActivityLog";
import { ProblemsPanel } from "./ProblemsPanel";
import { InspectorPanel } from "./InspectorPanel";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface BottomPanelProps {
  /** Additional CSS classes */
  className?: string;
  /** Whether the mobile overlay is open (mobile mode) */
  isOpen?: boolean;
  /** Callback when overlay should close (mobile mode) */
  onClose?: () => void;
}

type BottomPanelTab = "activity" | "problems" | "inspector";

interface TabConfig {
  id: BottomPanelTab;
  label: string;
  icon: React.ReactNode;
}

// =============================================================================
// Constants
// =============================================================================

const TABS: TabConfig[] = [
  { id: "activity", label: "Activity", icon: <Activity size={14} /> },
  { id: "problems", label: "Problems", icon: <AlertCircle size={14} /> },
  { id: "inspector", label: "Inspector", icon: <Eye size={14} /> },
];

// =============================================================================
// Main Component
// =============================================================================

export function BottomPanel({ className, isOpen, onClose }: BottomPanelProps) {
  const dispatch = useAppDispatch();
  const activeTab = useAppSelector(
    selectBottomPanelActiveTab,
  ) as BottomPanelTab;

  // Determine if in mobile overlay mode
  const isMobileMode = isOpen !== undefined;

  // Handle tab selection
  const handleSelectTab = useCallback(
    (tabId: BottomPanelTab) => {
      dispatch(setBottomPanelActiveTab(tabId));
    },
    [dispatch],
  );

  // Handle collapse
  const handleClose = useCallback(() => {
    dispatch(setBottomPanelCollapsed(true));
  }, [dispatch]);

  return (
    <>
      {/* Mobile Overlay Backdrop */}
      {isMobileMode && isOpen && (
        <div
          data-testid="bottom-panel-overlay"
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <div
        data-testid="bottom-panel-container"
        className={cn(
          "flex flex-col h-full",
          "bg-gray-50 dark:bg-gray-800",
          // Mobile overlay positioning
          isMobileMode &&
            "fixed bottom-0 left-0 right-0 z-50 h-64 shadow-xl md:relative md:h-full md:shadow-none",
          isMobileMode && !isOpen && "translate-y-full md:translate-y-0",
          isMobileMode && isOpen && "translate-y-0",
          "transition-transform duration-200 ease-in-out",
          className,
        )}
      >
        {/* Tab Bar */}
        <div
          data-testid="bottom-panel-tabs"
          className={cn(
            "flex items-center justify-between",
            "border-b border-gray-200 dark:border-gray-700",
            "bg-gray-100 dark:bg-gray-900",
          )}
        >
          {/* Tab List */}
          <div role="tablist" className="flex items-center gap-0.5 px-2">
            {TABS.map((tab) => {
              const isActive = tab.id === activeTab;

              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => handleSelectTab(tab.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5",
                    "text-xs font-medium transition-colors",
                    "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset",
                    // Active state
                    isActive && "text-gray-900 dark:text-gray-100",
                    isActive && "border-b-2 border-primary-500",
                    // Inactive state
                    !isActive && "text-gray-500 dark:text-gray-400",
                    !isActive && "hover:text-gray-700 dark:hover:text-gray-200",
                    !isActive &&
                      "hover:bg-gray-200/50 dark:hover:bg-gray-700/50",
                  )}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Panel Controls */}
          <div className="flex items-center px-2">
            <button
              type="button"
              aria-label="Close panel"
              onClick={handleClose}
              className={cn(
                "p-1 rounded",
                "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
                "hover:bg-gray-200 dark:hover:bg-gray-700",
                "focus:outline-none focus:ring-2 focus:ring-primary-500",
              )}
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div
          data-testid="bottom-panel-content"
          role="tabpanel"
          className="flex-1 overflow-auto"
        >
          {activeTab === "activity" && (
            <div data-testid="activity-tab-content">
              <ActivityLog />
            </div>
          )}

          {activeTab === "problems" && (
            <div data-testid="problems-tab-content">
              <ProblemsPanel />
            </div>
          )}

          {activeTab === "inspector" && (
            <div data-testid="inspector-tab-content">
              <InspectorPanel />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default BottomPanel;
