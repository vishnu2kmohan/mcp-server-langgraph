/**
 * CanvasTabs - Phase 1
 *
 * Code/Preview/Data tabs component for switching between
 * different views of an artifact in the Canvas panel.
 */
import { useCallback, useRef } from "react";
import { Code, Eye, Database } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type TabType = "code" | "preview" | "data";

export interface CanvasTabsProps {
  /** Currently active tab */
  activeTab: TabType;
  /** Callback when tab changes */
  onTabChange: (tab: TabType) => void;
  /** Disable all tabs */
  disabled?: boolean;
  /** Specific tabs to disable */
  disabledTabs?: TabType[];
  /** Which tabs to show (defaults to all) */
  visibleTabs?: TabType[];
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const TAB_ORDER: TabType[] = ["code", "preview", "data"];

const TAB_CONFIG: Record<
  TabType,
  { label: string; icon: typeof Code; testId: string }
> = {
  code: { label: "Code", icon: Code, testId: "code-icon" },
  preview: { label: "Preview", icon: Eye, testId: "preview-icon" },
  data: { label: "Data", icon: Database, testId: "data-icon" },
};

// =============================================================================
// Component
// =============================================================================

export function CanvasTabs({
  activeTab,
  onTabChange,
  disabled = false,
  disabledTabs = [],
  visibleTabs,
  className,
}: CanvasTabsProps) {
  const tabRefs = useRef<Map<TabType, HTMLButtonElement | null>>(new Map());

  // Filter tabs to only show visible ones
  const displayedTabs = visibleTabs
    ? TAB_ORDER.filter((tab) => visibleTabs.includes(tab))
    : TAB_ORDER;

  const isTabDisabled = useCallback(
    (tab: TabType) => disabled || disabledTabs.includes(tab),
    [disabled, disabledTabs],
  );

  const handleTabClick = useCallback(
    (tab: TabType) => {
      if (tab !== activeTab && !isTabDisabled(tab)) {
        onTabChange(tab);
      }
    },
    [activeTab, onTabChange, isTabDisabled],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, currentTab: TabType) => {
      const currentIndex = displayedTabs.indexOf(currentTab);
      let nextIndex: number;

      switch (e.key) {
        case "ArrowRight":
          e.preventDefault();
          nextIndex = (currentIndex + 1) % displayedTabs.length;
          break;
        case "ArrowLeft":
          e.preventDefault();
          nextIndex =
            (currentIndex - 1 + displayedTabs.length) % displayedTabs.length;
          break;
        default:
          return;
      }

      const nextTab = displayedTabs[nextIndex];
      if (nextTab && !isTabDisabled(nextTab)) {
        onTabChange(nextTab);
        tabRefs.current.get(nextTab)?.focus();
      }
    },
    [displayedTabs, onTabChange, isTabDisabled],
  );

  return (
    <div
      data-testid="canvas-tabs"
      role="tablist"
      aria-label="Artifact view tabs"
      className={cn(
        "flex items-center gap-1 p-1",
        "bg-gray-100 dark:bg-gray-800 rounded-lg",
        className,
      )}
    >
      {displayedTabs.map((tab) => {
        const config = TAB_CONFIG[tab];
        const Icon = config.icon;
        const isActive = tab === activeTab;
        const isDisabled = isTabDisabled(tab);

        return (
          <button
            key={tab}
            ref={(el) => tabRefs.current.set(tab, el)}
            role="tab"
            type="button"
            aria-selected={isActive}
            aria-disabled={isDisabled}
            disabled={isDisabled}
            tabIndex={isActive ? 0 : -1}
            onClick={() => handleTabClick(tab)}
            onKeyDown={(e) => handleKeyDown(e, tab)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium",
              "transition-all focus:outline-none focus:ring-2 focus:ring-primary-500",
              isActive &&
                "bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm",
              !isActive &&
                !isDisabled &&
                "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600",
              isDisabled && "opacity-50 cursor-not-allowed",
            )}
          >
            <Icon size={14} data-testid={config.testId} />
            <span>{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
