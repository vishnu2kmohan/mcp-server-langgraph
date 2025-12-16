/**
 * ChatWorkspace Component
 *
 * DevTools-style dockable panel workspace for the chat interface.
 * Provides resizable, collapsible panels with persistence support.
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────────┐
 * │  SessionPanel  │      ChatArea         │  ContextPanel  │
 * │  (collapsible) │   (Messages + Input)  │  (collapsible) │
 * └─────────────────────────────────────────────────────────┘
 */

import { useRef, type ReactNode } from "react";
import {
  DockableLayout,
  DockablePanelGroup,
  DockablePanel,
  DockableResizeHandle,
  type ImperativePanelHandle,
} from "../Layout";

// =============================================================================
// Types
// =============================================================================

export interface ChatWorkspaceProps {
  /** Session panel content */
  sessionPanel: ReactNode;
  /** Main chat area content (header + messages + input) */
  chatArea: ReactNode;
  /** Context panel content */
  contextPanel: ReactNode;
  /** Optional header above the workspace */
  header?: ReactNode;
  /** Unique ID for persisting panel sizes */
  persistenceId?: string;
  /** Default size for session panel (percentage) */
  sessionPanelDefaultSize?: number;
  /** Default size for context panel (percentage) */
  contextPanelDefaultSize?: number;
  /** Minimum size for side panels */
  sidePanelMinSize?: number;
  /** Whether session panel is collapsible */
  sessionPanelCollapsible?: boolean;
  /** Whether context panel is collapsible */
  contextPanelCollapsible?: boolean;
  /** Callback when session panel collapses */
  onSessionPanelCollapse?: () => void;
  /** Callback when session panel expands */
  onSessionPanelExpand?: () => void;
  /** Callback when context panel collapses */
  onContextPanelCollapse?: () => void;
  /** Callback when context panel expands */
  onContextPanelExpand?: () => void;
}

// =============================================================================
// Component
// =============================================================================

export function ChatWorkspace({
  sessionPanel,
  chatArea,
  contextPanel,
  header,
  persistenceId = "chat-workspace",
  sessionPanelDefaultSize = 20,
  contextPanelDefaultSize = 20,
  sidePanelMinSize = 10,
  sessionPanelCollapsible = true,
  contextPanelCollapsible = true,
  onSessionPanelCollapse,
  onSessionPanelExpand,
  onContextPanelCollapse,
  onContextPanelExpand,
}: ChatWorkspaceProps) {
  // Panel refs for imperative control
  const sessionPanelRef = useRef<ImperativePanelHandle>(null);
  const contextPanelRef = useRef<ImperativePanelHandle>(null);

  return (
    <DockableLayout className="h-screen flex flex-col">
      {/* Optional header */}
      {header && <div className="flex-shrink-0">{header}</div>}

      {/* Main workspace with resizable panels */}
      <DockablePanelGroup
        direction="horizontal"
        autoSaveId={persistenceId}
        className="flex-1"
      >
        {/* Left Panel - Sessions */}
        <DockablePanel
          ref={sessionPanelRef}
          id="session-panel"
          order={1}
          defaultSize={sessionPanelDefaultSize}
          minSize={sidePanelMinSize}
          maxSize={40}
          collapsible={sessionPanelCollapsible}
          collapsedSize={0}
          onCollapse={onSessionPanelCollapse}
          onExpand={onSessionPanelExpand}
          className="bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700"
        >
          {sessionPanel}
        </DockablePanel>

        {/* Resize handle */}
        <DockableResizeHandle />

        {/* Center Panel - Chat Area */}
        <DockablePanel
          id="chat-panel"
          order={2}
          defaultSize={100 - sessionPanelDefaultSize - contextPanelDefaultSize}
          minSize={30}
          className="flex flex-col bg-gray-50 dark:bg-gray-900"
        >
          {chatArea}
        </DockablePanel>

        {/* Resize handle */}
        <DockableResizeHandle />

        {/* Right Panel - Context */}
        <DockablePanel
          ref={contextPanelRef}
          id="context-panel"
          order={3}
          defaultSize={contextPanelDefaultSize}
          minSize={sidePanelMinSize}
          maxSize={40}
          collapsible={contextPanelCollapsible}
          collapsedSize={0}
          onCollapse={onContextPanelCollapse}
          onExpand={onContextPanelExpand}
          className="bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700"
        >
          {contextPanel}
        </DockablePanel>
      </DockablePanelGroup>
    </DockableLayout>
  );
}

// =============================================================================
// Helper hooks for panel control
// =============================================================================

export interface UsePanelControlReturn {
  /** Toggle panel collapsed state */
  toggle: () => void;
  /** Collapse the panel */
  collapse: () => void;
  /** Expand the panel */
  expand: () => void;
  /** Check if panel is collapsed */
  isCollapsed: () => boolean;
}

/**
 * Hook for controlling a panel imperatively
 */
// eslint-disable-next-line react-refresh/only-export-components
export function usePanelControl(
  panelRef: React.RefObject<ImperativePanelHandle>,
): UsePanelControlReturn {
  return {
    toggle: () => {
      const panel = panelRef.current;
      if (!panel) return;
      if (panel.isCollapsed()) {
        panel.expand();
      } else {
        panel.collapse();
      }
    },
    collapse: () => panelRef.current?.collapse(),
    expand: () => panelRef.current?.expand(),
    isCollapsed: () => panelRef.current?.isCollapsed() ?? false,
  };
}

export default ChatWorkspace;
