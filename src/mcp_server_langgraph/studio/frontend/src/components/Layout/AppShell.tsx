/**
 * AppShell Component
 *
 * JupyterLab-inspired main layout orchestrator for Agent Studio.
 * Provides the complete IDE-like shell with:
 * - Left sidebar (hybrid navigation)
 * - Main content area (tabbed documents with splits)
 * - Right sidebar (property inspector)
 * - Bottom panel (activity, problems, inspector)
 * - Status bar
 *
 * Features:
 * - Resizable panels using react-resizable-panels
 * - Focus mode (hides sidebars)
 * - Keyboard shortcuts (Cmd+B, Cmd+J, Escape)
 * - Full workspace persistence via Redux
 */

import { useEffect, useCallback, useRef, type ReactNode } from "react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from "react-resizable-panels";
import {
  Maximize2,
  Minimize2,
  Menu,
  X,
  PanelRight,
  PanelBottom,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectLeftSidebarCollapsed,
  selectRightSidebarCollapsed,
  selectBottomPanelCollapsed,
  selectFocusMode,
  setLeftSidebarCollapsed,
  setRightSidebarCollapsed,
  setBottomPanelCollapsed,
  setFocusMode,
  setLeftSidebarWidth,
  setRightSidebarWidth,
  setBottomPanelHeight,
} from "../../store/slices/workspaceSlice";
import { StatusBar } from "./StatusBar";

// =============================================================================
// Types
// =============================================================================

export interface AppShellProps {
  /** Content for the left sidebar */
  leftSidebar?: ReactNode;
  /** Content for the right sidebar */
  rightSidebar?: ReactNode;
  /** Content for the bottom panel */
  bottomPanel?: ReactNode;
  /** Main content (children) */
  children?: ReactNode;
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Component
// =============================================================================

export function AppShell({
  leftSidebar,
  rightSidebar,
  bottomPanel,
  children,
}: AppShellProps) {
  const dispatch = useAppDispatch();

  // Panel refs for programmatic collapse/expand
  const rightPanelRef = useRef<ImperativePanelHandle>(null);
  const bottomPanelRef = useRef<ImperativePanelHandle>(null);

  // Selectors
  const leftCollapsed = useAppSelector(selectLeftSidebarCollapsed);
  const rightCollapsed = useAppSelector(selectRightSidebarCollapsed);
  const bottomCollapsed = useAppSelector(selectBottomPanelCollapsed);
  const focusMode = useAppSelector(selectFocusMode);

  // Sync right panel collapse state with redux
  useEffect(() => {
    if (rightCollapsed || focusMode) {
      rightPanelRef.current?.collapse();
    } else {
      rightPanelRef.current?.expand();
    }
  }, [rightCollapsed, focusMode]);

  // Sync bottom panel collapse state with redux
  useEffect(() => {
    if (bottomCollapsed || focusMode) {
      bottomPanelRef.current?.collapse();
    } else {
      bottomPanelRef.current?.expand();
    }
  }, [bottomCollapsed, focusMode]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Cmd/Ctrl+B: Toggle right sidebar (left sidebar is always visible)
      if ((event.metaKey || event.ctrlKey) && event.key === "b") {
        event.preventDefault();
        dispatch(setRightSidebarCollapsed(!rightCollapsed));
        return;
      }

      // Cmd/Ctrl+J: Toggle bottom panel
      if ((event.metaKey || event.ctrlKey) && event.key === "j") {
        event.preventDefault();
        dispatch(setBottomPanelCollapsed(!bottomCollapsed));
        return;
      }

      // Escape: Exit focus mode
      if (event.key === "Escape" && focusMode) {
        event.preventDefault();
        dispatch(setFocusMode(false));
        return;
      }
    },
    [dispatch, rightCollapsed, bottomCollapsed, focusMode],
  );

  // Register keyboard shortcuts
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Focus mode toggle handler
  const handleToggleFocusMode = useCallback(() => {
    dispatch(setFocusMode(!focusMode));
  }, [dispatch, focusMode]);

  // Mobile menu toggle handler
  const handleToggleMobileMenu = useCallback(() => {
    dispatch(setLeftSidebarCollapsed(!leftCollapsed));
  }, [dispatch, leftCollapsed]);

  // Mobile right panel toggle handler
  const handleToggleRightPanel = useCallback(() => {
    dispatch(setRightSidebarCollapsed(!rightCollapsed));
  }, [dispatch, rightCollapsed]);

  // Mobile bottom panel toggle handler
  const handleToggleBottomPanel = useCallback(() => {
    dispatch(setBottomPanelCollapsed(!bottomCollapsed));
  }, [dispatch, bottomCollapsed]);

  // Panel resize handlers
  const handleLeftResize = useCallback(
    (size: number) => {
      // Convert percentage to pixels (assuming typical viewport)
      const pixelWidth = (size / 100) * window.innerWidth;
      dispatch(setLeftSidebarWidth(pixelWidth));
    },
    [dispatch],
  );

  const handleRightResize = useCallback(
    (size: number) => {
      const pixelWidth = (size / 100) * window.innerWidth;
      dispatch(setRightSidebarWidth(pixelWidth));
    },
    [dispatch],
  );

  const handleBottomResize = useCallback(
    (size: number) => {
      // Convert percentage to pixels
      const pixelHeight = (size / 100) * window.innerHeight;
      dispatch(setBottomPanelHeight(pixelHeight));
    },
    [dispatch],
  );

  // Calculate visibility
  // Left sidebar is always visible on desktop (only collapsed state affects mobile)
  const showLeftSidebar = true; // Always visible on desktop
  const showRightSidebar = !focusMode && !rightCollapsed;
  const showBottomPanel = !focusMode && !bottomCollapsed;

  return (
    <div
      data-testid="app-shell"
      className={cn(
        "h-screen w-screen overflow-hidden",
        "bg-white dark:bg-gray-900",
        "flex flex-col",
      )}
    >
      {/* Mobile Header with Menu Toggle */}
      <div
        className={cn(
          "h-10 flex-shrink-0 md:hidden",
          "border-b border-gray-200 dark:border-gray-700",
          "bg-gray-100 dark:bg-gray-800",
          "flex items-center justify-between px-3",
        )}
      >
        <button
          type="button"
          aria-label="Toggle menu"
          onClick={handleToggleMobileMenu}
          className={cn(
            "p-2 rounded-md",
            "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "transition-colors",
          )}
        >
          {leftCollapsed ? <Menu size={20} /> : <X size={20} />}
        </button>
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          Agent Studio
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Toggle bottom panel"
            onClick={handleToggleBottomPanel}
            className={cn(
              "p-2 rounded-md",
              "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
              "hover:bg-gray-200 dark:hover:bg-gray-700",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              "transition-colors",
            )}
          >
            <PanelBottom size={20} />
          </button>
          <button
            type="button"
            aria-label="Toggle right panel"
            onClick={handleToggleRightPanel}
            className={cn(
              "p-2 rounded-md",
              "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
              "hover:bg-gray-200 dark:hover:bg-gray-700",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              "transition-colors",
            )}
          >
            <PanelRight size={20} />
          </button>
        </div>
      </div>

      {/* Mobile Left Sidebar Overlay Backdrop */}
      {!leftCollapsed && (
        <div
          data-testid="mobile-sidebar-overlay"
          className={cn(
            "fixed inset-0 bg-black/50 z-40 md:hidden",
            "transition-opacity",
          )}
          onClick={handleToggleMobileMenu}
          aria-hidden="true"
        />
      )}

      {/* Mobile Right Sidebar Overlay Backdrop */}
      {!rightCollapsed && (
        <div
          data-testid="mobile-right-sidebar-overlay"
          className={cn(
            "fixed inset-0 bg-black/50 z-40 md:hidden",
            "transition-opacity",
          )}
          onClick={handleToggleRightPanel}
          aria-hidden="true"
        />
      )}

      {/* Mobile Bottom Panel Overlay Backdrop */}
      {!bottomCollapsed && (
        <div
          data-testid="mobile-bottom-panel-overlay"
          className={cn(
            "fixed inset-0 bg-black/50 z-40 md:hidden",
            "transition-opacity",
          )}
          onClick={handleToggleBottomPanel}
          aria-hidden="true"
        />
      )}

      {/* Main content area with horizontal panels */}
      <PanelGroup
        direction="horizontal"
        className="flex-1"
        autoSaveId="app-shell-horizontal"
      >
        {/* Left Sidebar Panel - Always visible on desktop */}
        <Panel
          id="left-sidebar"
          order={1}
          defaultSize={20}
          minSize={15}
          maxSize={35}
          onResize={handleLeftResize}
          className={cn(
            "transition-all duration-300",
            // Mobile: Fixed overlay positioning with hamburger menu toggle
            "max-md:fixed max-md:left-0 max-md:top-10 max-md:bottom-0 max-md:z-50",
            "max-md:w-80 max-md:shadow-xl",
            leftCollapsed && "max-md:!-translate-x-full",
          )}
        >
          <div
            data-testid="left-sidebar-panel"
            data-focus-hidden="false"
            className={cn(
              "h-full overflow-hidden",
              "border-r border-gray-200 dark:border-gray-700",
              "bg-gray-50 dark:bg-gray-800",
            )}
          >
            {leftSidebar}
          </div>
        </Panel>

        {/* Left Resize Handle - Touch-friendly */}
        {showLeftSidebar && (
          <PanelResizeHandle
            className={cn(
              // Base styling
              "w-1 bg-gray-200 dark:bg-gray-700",
              "hover:bg-blue-500 active:bg-blue-600",
              "transition-colors cursor-col-resize",
              // Touch-friendly: Larger hit area on touch devices
              "touch-none relative",
              "before:absolute before:inset-y-0 before:-left-2 before:-right-2",
              "before:content-[''] before:md:hidden",
              // Desktop hover effect
              "md:hover:w-1.5",
            )}
          />
        )}

        {/* Center Content (Main + Bottom) */}
        <Panel id="center" order={2} defaultSize={60} minSize={30}>
          <PanelGroup
            direction="vertical"
            autoSaveId="app-shell-vertical"
            className="h-full"
          >
            {/* Main Content Area */}
            <Panel id="main" order={1} defaultSize={75} minSize={30}>
              <main
                role="main"
                data-testid="main-content-area"
                className="h-full overflow-auto bg-white dark:bg-gray-900"
              >
                {children}
              </main>
            </Panel>

            {/* Bottom Resize Handle - Touch-friendly */}
            {showBottomPanel && (
              <PanelResizeHandle
                className={cn(
                  // Base styling
                  "h-1 bg-gray-200 dark:bg-gray-700",
                  "hover:bg-blue-500 active:bg-blue-600",
                  "transition-colors cursor-row-resize",
                  // Touch-friendly: Larger hit area on touch devices
                  "touch-none relative",
                  "before:absolute before:inset-x-0 before:-top-2 before:-bottom-2",
                  "before:content-[''] before:md:hidden",
                  // Desktop hover effect
                  "md:hover:h-1.5",
                )}
              />
            )}

            {/* Bottom Panel */}
            <Panel
              ref={bottomPanelRef}
              id="bottom"
              order={2}
              defaultSize={25}
              minSize={10}
              maxSize={50}
              collapsible
              collapsedSize={0}
              onResize={handleBottomResize}
              className={cn(
                "transition-all duration-300",
                // Mobile: Fixed overlay positioning (bottom sheet)
                "max-md:fixed max-md:left-0 max-md:right-0 max-md:bottom-0 max-md:z-50",
                "max-md:h-64 max-md:shadow-xl",
                !showBottomPanel && "max-md:!translate-y-full",
              )}
            >
              <div
                data-testid="bottom-panel"
                className={cn(
                  "h-full overflow-hidden",
                  "border-t border-gray-200 dark:border-gray-700",
                  "bg-gray-50 dark:bg-gray-800",
                )}
              >
                {bottomPanel}
              </div>
            </Panel>
          </PanelGroup>
        </Panel>

        {/* Right Resize Handle - Touch-friendly */}
        {showRightSidebar && (
          <PanelResizeHandle
            className={cn(
              // Base styling
              "w-1 bg-gray-200 dark:bg-gray-700",
              "hover:bg-blue-500 active:bg-blue-600",
              "transition-colors cursor-col-resize",
              // Touch-friendly: Larger hit area on touch devices
              "touch-none relative",
              "before:absolute before:inset-y-0 before:-left-2 before:-right-2",
              "before:content-[''] before:md:hidden",
              // Desktop hover effect
              "md:hover:w-1.5",
            )}
          />
        )}

        {/* Right Sidebar Panel */}
        <Panel
          ref={rightPanelRef}
          id="right-sidebar"
          order={3}
          defaultSize={20}
          minSize={15}
          maxSize={35}
          collapsible
          collapsedSize={0}
          onResize={handleRightResize}
          className={cn(
            "transition-all duration-300",
            // Mobile: Fixed overlay positioning
            "max-md:fixed max-md:right-0 max-md:top-10 max-md:bottom-0 max-md:z-50",
            "max-md:w-80 max-md:shadow-xl",
            !showRightSidebar && "max-md:!translate-x-full",
          )}
        >
          <div
            data-testid="right-sidebar-panel"
            data-focus-hidden={focusMode ? "true" : "false"}
            className={cn(
              "h-full overflow-hidden",
              "border-l border-gray-200 dark:border-gray-700",
              "bg-gray-50 dark:bg-gray-800",
            )}
          >
            {rightSidebar}
          </div>
        </Panel>
      </PanelGroup>

      {/* Status Bar with Focus Mode Toggle */}
      <div className="relative flex-shrink-0">
        <StatusBar />
        {/* Focus Mode Toggle Button */}
        <button
          type="button"
          aria-label="Focus mode"
          onClick={handleToggleFocusMode}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2",
            "p-1 rounded",
            "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "transition-colors",
          )}
        >
          {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>
    </div>
  );
}

export default AppShell;
