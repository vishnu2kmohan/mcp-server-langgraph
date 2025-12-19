/**
 * HybridShellLayout - Phase 1 Implementation
 *
 * New app shell for the Hybrid Canvas paradigm (Gemini/ChatGPT Canvas style).
 * Uses react-resizable-panels for flexible panel sizing.
 *
 * Layout:
 * +----------------------------------------------------------------+
 * | Activity  |  Session   |  Conversation  |    Canvas Panel      |
 * |   Bar     |    Nav     |     Panel      |                      |
 * |  (56px)   | (resizable)|  (resizable)   |    (resizable)       |
 * +----------------------------------------------------------------+
 * |                      Status Bar                                 |
 * +----------------------------------------------------------------+
 */
import { useCallback } from "react";
import { Outlet, useNavigate } from "react-router";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import {
  MessageSquare,
  GitBranch,
  Cpu,
  Activity,
  Settings,
  Shield,
  Plus,
  Search,
  FileCode2,
  Command,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectActiveNavItem,
  selectCanvasCollapsed,
  selectSessionNavCollapsed,
  setActiveNavItem,
  setPanelSizes,
  type CanvasPanelSizes,
} from "../store/slices/canvasSlice";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// ActivityBar Component
// =============================================================================

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "chat",
    icon: <MessageSquare size={20} />,
    label: "Chat",
    path: "/studio/v2/chat",
  },
  { id: "workflows", icon: <GitBranch size={20} />, label: "Workflows" },
  { id: "agents", icon: <Cpu size={20} />, label: "Agents" },
  { id: "observability", icon: <Activity size={20} />, label: "Observability" },
  { id: "admin", icon: <Shield size={20} />, label: "Admin" },
];

const BOTTOM_ITEMS: NavItem[] = [
  { id: "settings", icon: <Settings size={20} />, label: "Settings" },
];

function ActivityBar() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activeNavItem = useAppSelector(selectActiveNavItem);

  const handleNavClick = useCallback(
    (item: NavItem) => {
      dispatch(setActiveNavItem(item.id));
      if (item.path) {
        navigate(item.path);
      }
    },
    [dispatch, navigate],
  );

  return (
    <div
      data-testid="activity-bar"
      className={cn(
        "flex flex-col items-center w-14 py-2",
        "bg-gray-100 dark:bg-gray-900",
        "border-r border-gray-200 dark:border-gray-700",
      )}
    >
      {/* Main navigation icons */}
      <div className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-label={item.label}
            title={item.label}
            onClick={() => handleNavClick(item)}
            className={cn(
              "p-2 rounded-lg transition-all",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              activeNavItem === item.id &&
                "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300",
              activeNavItem !== item.id &&
                "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            {item.icon}
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom icons */}
      <div className="flex flex-col gap-1">
        <button
          type="button"
          aria-label="Command Palette"
          title="Command Palette (⌘K)"
          className={cn(
            "p-2 rounded-lg transition-all",
            "text-gray-500 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
          )}
        >
          <Command size={20} />
        </button>
        {BOTTOM_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-label={item.label}
            title={item.label}
            onClick={() => handleNavClick(item)}
            className={cn(
              "p-2 rounded-lg transition-all",
              "text-gray-500 dark:text-gray-400",
              "hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            {item.icon}
          </button>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// SessionNav Component
// =============================================================================

function SessionNav() {
  return (
    <div
      data-testid="session-nav"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-800",
        "border-r border-gray-200 dark:border-gray-700",
      )}
    >
      {/* Header with New Chat button */}
      <div className="p-2 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          className={cn(
            "w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg",
            "bg-primary-500 hover:bg-primary-600",
            "text-white font-medium text-sm",
            "transition-colors",
          )}
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-2">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search sessions..."
            className={cn(
              "w-full pl-9 pr-3 py-2 rounded-lg text-sm",
              "bg-white dark:bg-gray-900",
              "border border-gray-200 dark:border-gray-700",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              "placeholder-gray-400",
            )}
          />
        </div>
      </div>

      {/* Session list placeholder */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
          Today
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400 italic">
          No sessions yet
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ConversationPanel Component
// =============================================================================

function ConversationPanel() {
  return (
    <div
      data-testid="conversation-panel"
      className={cn("flex flex-col h-full", "bg-white dark:bg-gray-900")}
    >
      {/* Message area */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-sm">Start a conversation</p>
          </div>
        </div>
      </div>

      {/* Input area placeholder */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div
          className={cn(
            "flex items-center gap-2 px-4 py-3 rounded-lg",
            "bg-gray-50 dark:bg-gray-800",
            "border border-gray-200 dark:border-gray-700",
          )}
        >
          <input
            type="text"
            placeholder="Type a message..."
            className={cn(
              "flex-1 bg-transparent",
              "focus:outline-none",
              "text-gray-900 dark:text-gray-100",
              "placeholder-gray-400",
            )}
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// CanvasPanel Component
// =============================================================================

function CanvasPanel() {
  return (
    <div
      data-testid="canvas-panel"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-800",
        "border-l border-gray-200 dark:border-gray-700",
      )}
    >
      {/* Canvas header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
          Canvas
        </span>
      </div>

      {/* Canvas content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <FileCode2 size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-sm">No artifact selected</p>
            <p className="text-xs mt-1 text-gray-500">
              Select an artifact from the conversation to view and edit
            </p>
          </div>
        </div>
        {/* Outlet for nested routes (artifact detail, etc.) */}
        <Outlet />
      </div>
    </div>
  );
}

// =============================================================================
// StatusBar Component
// =============================================================================

function CanvasStatusBar() {
  return (
    <div
      data-testid="canvas-status-bar"
      className={cn(
        "flex items-center justify-between px-4 py-1",
        "bg-gray-100 dark:bg-gray-900",
        "border-t border-gray-200 dark:border-gray-700",
        "text-xs text-gray-500 dark:text-gray-400",
      )}
    >
      <div className="flex items-center gap-4">
        <span>Ready</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="hidden sm:inline">⌘K Command Palette</span>
        <span className="hidden sm:inline">⌘/ Toggle Canvas</span>
      </div>
    </div>
  );
}

// =============================================================================
// ResizeHandle Component
// =============================================================================

function ResizeHandle({ className }: { className?: string }) {
  return (
    <PanelResizeHandle
      className={cn(
        "w-1 hover:w-2 transition-all",
        "bg-transparent hover:bg-primary-500/30",
        "cursor-col-resize",
        className,
      )}
    />
  );
}

// =============================================================================
// HybridShellLayout Component
// =============================================================================

export function HybridShellLayout() {
  const dispatch = useAppDispatch();
  const sessionNavCollapsed = useAppSelector(selectSessionNavCollapsed);
  const canvasCollapsed = useAppSelector(selectCanvasCollapsed);

  // Handle panel resize
  const handlePanelResize = useCallback(
    (sizes: number[]) => {
      if (sizes.length === 3) {
        const newSizes: CanvasPanelSizes = {
          sessionNav: sizes[0],
          conversation: sizes[1],
          canvas: sizes[2],
        };
        dispatch(setPanelSizes(newSizes));
      }
    },
    [dispatch],
  );

  return (
    <div
      data-testid="hybrid-shell"
      className="hybrid-shell flex flex-col h-screen bg-white dark:bg-gray-900"
    >
      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Activity Bar - fixed width */}
        <ActivityBar />

        {/* Resizable panels */}
        <PanelGroup
          direction="horizontal"
          onLayout={handlePanelResize}
          className="flex-1"
        >
          {/* Session Nav Panel */}
          {!sessionNavCollapsed && (
            <>
              <Panel
                id="session-nav"
                order={1}
                defaultSize={20}
                minSize={15}
                maxSize={35}
              >
                <SessionNav />
              </Panel>
              <ResizeHandle />
            </>
          )}

          {/* Conversation Panel */}
          <Panel
            id="conversation"
            order={2}
            defaultSize={canvasCollapsed ? 80 : 40}
            minSize={30}
          >
            <ConversationPanel />
          </Panel>

          {/* Canvas Panel */}
          {!canvasCollapsed && (
            <>
              <ResizeHandle />
              <Panel
                id="canvas"
                order={3}
                defaultSize={40}
                minSize={25}
                maxSize={60}
              >
                <CanvasPanel />
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>

      {/* Status Bar */}
      <CanvasStatusBar />
    </div>
  );
}
