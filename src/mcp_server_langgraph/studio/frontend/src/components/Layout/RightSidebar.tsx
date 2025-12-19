/**
 * RightSidebar Component
 *
 * JupyterLab-inspired property inspector right sidebar.
 * Features:
 * - Collapsible property sections
 * - Context-sensitive content based on active tab type
 * - Redux state integration for section expansion
 * - Document-type-specific property panels
 * - Accessibility (expandable sections)
 */

import { useCallback } from "react";
import { FileText, X, PanelRightClose, Pin, PinOff } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectTabs,
  selectActiveTabId,
  selectExpandedPropertySections,
  selectRightSidebarPinned,
  toggleExpandedPropertySection,
  setRightSidebarCollapsed,
  setRightSidebarPinned,
} from "../../store/slices/workspaceSlice";
import { selectCurrentSession } from "../../store/slices/sessionSlice";
import { selectAllTools } from "../../store/slices/mcpSlice";

// Property panels for each tab type
import {
  ChatProperties,
  WorkflowProperties,
  ProjectProperties,
  SettingsProperties,
  CostProperties,
  ObservabilityProperties,
  GenericProperties,
} from "./PropertyPanels";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface RightSidebarProps {
  /** Additional CSS classes */
  className?: string;
  /** Whether the mobile overlay is open (mobile mode) */
  isOpen?: boolean;
  /** Callback when overlay should close (mobile mode) */
  onClose?: () => void;
}

// =============================================================================
// Component
// =============================================================================

export function RightSidebar({
  className,
  isOpen,
  onClose,
}: RightSidebarProps) {
  const dispatch = useAppDispatch();
  const tabs = useAppSelector(selectTabs);
  const activeTabId = useAppSelector(selectActiveTabId);
  const expandedSections = useAppSelector(selectExpandedPropertySections);
  const isPinned = useAppSelector(selectRightSidebarPinned);
  const currentSession = useAppSelector(selectCurrentSession);
  const mcpTools = useAppSelector(selectAllTools);

  // Find active tab
  const activeTab = tabs.find((tab) => tab.id === activeTabId);

  // Handle section toggle
  const handleToggleSection = useCallback(
    (sectionId: string) => {
      dispatch(toggleExpandedPropertySection(sectionId));
    },
    [dispatch],
  );

  // Check if section is expanded
  const isSectionExpanded = useCallback(
    (sectionId: string) => expandedSections.includes(sectionId),
    [expandedSections],
  );

  // Handle collapse
  const handleCollapse = useCallback(() => {
    dispatch(setRightSidebarCollapsed(true));
  }, [dispatch]);

  // Handle pin toggle
  const handleTogglePin = useCallback(() => {
    dispatch(setRightSidebarPinned(!isPinned));
  }, [dispatch, isPinned]);

  // Determine if in mobile overlay mode
  const isMobileMode = isOpen !== undefined;

  return (
    <>
      {/* Mobile Overlay Backdrop */}
      {isMobileMode && isOpen && (
        <div
          data-testid="right-sidebar-overlay"
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <div
        data-testid="right-sidebar"
        className={cn(
          "flex flex-col h-full",
          "bg-gray-50 dark:bg-gray-800",
          // Mobile overlay positioning
          isMobileMode &&
            "fixed right-0 top-0 z-50 w-80 shadow-xl md:relative md:w-auto md:shadow-none",
          isMobileMode && !isOpen && "translate-x-full md:translate-x-0",
          isMobileMode && isOpen && "translate-x-0",
          "transition-transform duration-200 ease-in-out",
          className,
        )}
      >
        {/* Header */}
        <div
          className={cn(
            "px-3 py-2 flex items-center justify-between",
            "border-b border-gray-200 dark:border-gray-700",
            "text-xs font-semibold tracking-wider",
            "text-gray-500 dark:text-gray-400",
          )}
        >
          <span>PROPERTIES</span>
          <div className="flex items-center gap-1">
            {/* Pin toggle - keep visible in Focus Mode */}
            {!isMobileMode && (
              <button
                type="button"
                onClick={handleTogglePin}
                title={
                  isPinned
                    ? "Unpin sidebar (visible in Focus Mode)"
                    : "Pin sidebar (keep visible in Focus Mode)"
                }
                className={cn(
                  "p-1 rounded",
                  isPinned
                    ? "text-primary-600 dark:text-primary-400"
                    : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
                  "hover:bg-gray-200 dark:hover:bg-gray-700",
                  "focus:outline-none focus:ring-2 focus:ring-primary-500",
                  "transition-colors",
                )}
                aria-label={isPinned ? "Unpin sidebar" : "Pin sidebar"}
              >
                {isPinned ? <PinOff size={14} /> : <Pin size={14} />}
              </button>
            )}
            {isMobileMode && onClose ? (
              <button
                type="button"
                onClick={onClose}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                aria-label="Close sidebar"
              >
                <X size={14} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleCollapse}
                title="Collapse Properties Panel (⌘B)"
                className={cn(
                  "p-1 rounded",
                  "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
                  "hover:bg-gray-200 dark:hover:bg-gray-700",
                  "focus:outline-none focus:ring-2 focus:ring-primary-500",
                  "transition-colors",
                )}
                aria-label="Collapse sidebar"
              >
                <PanelRightClose size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div
          data-testid="right-sidebar-content"
          className="flex-1 overflow-y-auto"
        >
          {!activeTab ? (
            <div className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
              <FileText size={32} className="mx-auto mb-2 opacity-50" />
              <p>Select a document to view its properties</p>
            </div>
          ) : activeTab.type === "chat" ? (
            <ChatProperties
              tab={activeTab}
              session={currentSession}
              tools={mcpTools}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : activeTab.type === "workflow" ? (
            <WorkflowProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : activeTab.type === "project" ? (
            <ProjectProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : activeTab.type === "settings" ? (
            <SettingsProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : activeTab.type === "cost" ? (
            <CostProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : activeTab.type === "observability" ? (
            <ObservabilityProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          ) : (
            <GenericProperties
              tab={activeTab}
              isSectionExpanded={isSectionExpanded}
              onToggleSection={handleToggleSection}
            />
          )}
        </div>
      </div>
    </>
  );
}

export default RightSidebar;
