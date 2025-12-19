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
import { useCallback, useMemo } from "react";
import {
  Outlet,
  useNavigate,
  useRouteLoaderData,
  useParams,
} from "react-router";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import type { SessionsLoaderData, ChatLoaderData } from "../router/loaders";
import type { Session } from "../types";
import type { CanvasArtifact } from "../types/artifacts";
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
  selectSelectedArtifactId,
  setActiveNavItem,
  setPanelSizes,
  setSelectedArtifactId,
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

interface GroupedSessions {
  today: Session[];
  yesterday: Session[];
  older: Session[];
}

function groupSessionsByDate(sessions: Session[]): GroupedSessions {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);

  const groups: GroupedSessions = { today: [], yesterday: [], older: [] };

  for (const session of sessions) {
    const sessionDate = new Date(session.created_at);
    const sessionDay = new Date(
      sessionDate.getFullYear(),
      sessionDate.getMonth(),
      sessionDate.getDate(),
    );

    if (sessionDay.getTime() === today.getTime()) {
      groups.today.push(session);
    } else if (sessionDay.getTime() === yesterday.getTime()) {
      groups.yesterday.push(session);
    } else {
      groups.older.push(session);
    }
  }

  return groups;
}

function SessionNav() {
  const navigate = useNavigate();
  const { sessionId: currentSessionId } = useParams();

  // Get sessions from route loader data
  const loaderData = useRouteLoaderData("studio-v2") as
    | SessionsLoaderData
    | undefined;

  // Memoize sessions to prevent unnecessary re-renders
  const sessions = useMemo(
    () => loaderData?.sessions ?? [],
    [loaderData?.sessions],
  );

  // Group sessions by date
  const groupedSessions = useMemo(
    () => groupSessionsByDate(sessions),
    [sessions],
  );

  const handleSessionClick = useCallback(
    (session: Session) => {
      navigate(`/studio/v2/chat/${session.id}`);
    },
    [navigate],
  );

  const handleNewChat = useCallback(() => {
    navigate("/studio/v2/chat");
  }, [navigate]);

  const renderSessionItem = (session: Session) => (
    <button
      key={session.id}
      type="button"
      onClick={() => handleSessionClick(session)}
      className={cn(
        "w-full text-left px-3 py-2 rounded-lg text-sm truncate",
        "transition-colors",
        session.id === currentSessionId
          ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
          : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700",
      )}
    >
      {session.name || `Session ${session.id.slice(0, 8)}`}
    </button>
  );

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
          onClick={handleNewChat}
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

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 italic text-center mt-4">
            No sessions yet
          </div>
        ) : (
          <>
            {groupedSessions.today.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Today
                </div>
                <div className="space-y-1">
                  {groupedSessions.today.map(renderSessionItem)}
                </div>
              </div>
            )}
            {groupedSessions.yesterday.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Yesterday
                </div>
                <div className="space-y-1">
                  {groupedSessions.yesterday.map(renderSessionItem)}
                </div>
              </div>
            )}
            {groupedSessions.older.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Older
                </div>
                <div className="space-y-1">
                  {groupedSessions.older.map(renderSessionItem)}
                </div>
              </div>
            )}
          </>
        )}
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

/** Get icon for artifact content type */
function getArtifactIcon(contentType: CanvasArtifact["contentType"]) {
  switch (contentType) {
    case "code":
      return <FileCode2 size={16} />;
    case "markdown":
      return <FileCode2 size={16} />;
    case "json":
      return <FileCode2 size={16} />;
    default:
      return <FileCode2 size={16} />;
  }
}

function CanvasPanel() {
  const dispatch = useAppDispatch();
  const selectedArtifactId = useAppSelector(selectSelectedArtifactId);

  // Get artifacts from the chat loader
  const loaderData = useRouteLoaderData("chat-session") as
    | ChatLoaderData
    | undefined;
  const artifacts = useMemo(
    () => loaderData?.artifacts ?? [],
    [loaderData?.artifacts],
  );

  // Find the selected artifact
  const selectedArtifact = useMemo(
    () => artifacts.find((a) => a.id === selectedArtifactId),
    [artifacts, selectedArtifactId],
  );

  const handleArtifactSelect = useCallback(
    (artifact: CanvasArtifact) => {
      dispatch(setSelectedArtifactId(artifact.id));
    },
    [dispatch],
  );

  return (
    <div
      data-testid="canvas-panel"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-800",
        "border-l border-gray-200 dark:border-gray-700",
      )}
    >
      {/* Canvas header with artifact tabs */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
          Canvas
        </span>
        {artifacts.length > 0 && (
          <span className="text-xs text-gray-400">
            {artifacts.length} artifact{artifacts.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Artifact tabs */}
      {artifacts.length > 0 && (
        <div className="flex gap-1 p-2 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
          {artifacts.map((artifact) => (
            <button
              key={artifact.id}
              type="button"
              onClick={() => handleArtifactSelect(artifact)}
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded text-xs whitespace-nowrap",
                "transition-colors",
                artifact.id === selectedArtifactId
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700",
              )}
            >
              {getArtifactIcon(artifact.contentType)}
              <span className="max-w-24 truncate">
                {artifact.title || `Artifact ${artifact.id.slice(0, 6)}`}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Canvas content */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedArtifact ? (
          <div className="h-full">
            {/* Artifact header */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {selectedArtifact.title || "Untitled"}
              </h3>
              <span className="text-xs text-gray-400">
                v{selectedArtifact.version} &bull;{" "}
                {selectedArtifact.contentType}
              </span>
            </div>
            {/* Artifact content */}
            <pre
              className={cn(
                "p-4 rounded-lg text-sm overflow-auto",
                "bg-gray-100 dark:bg-gray-900",
                "text-gray-800 dark:text-gray-200",
                "font-mono",
              )}
            >
              {selectedArtifact.content}
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <FileCode2 size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-sm">No artifact selected</p>
              <p className="text-xs mt-1 text-gray-500">
                {artifacts.length > 0
                  ? "Select an artifact from the tabs above"
                  : "Artifacts will appear here when generated"}
              </p>
            </div>
          </div>
        )}
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
