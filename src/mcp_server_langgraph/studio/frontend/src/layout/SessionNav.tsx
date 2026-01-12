/**
 * SessionNav Component
 *
 * Time-travel grouped session navigation sidebar.
 * Extracted from StudioShellLayout for maintainability.
 *
 * Features:
 * - Session grouping by date (Today, Yesterday, Older)
 * - Search/filter sessions
 * - New chat creation
 * - Active session highlighting
 * - AI-powered session intelligence (Sprint 2)
 */
/* eslint-disable react-refresh/only-export-components -- Exports groupSessionsByDate utility alongside component */
import { useCallback, useMemo, useState, forwardRef, useRef } from "react";
import { useNavigate, useRouteLoaderData, useParams } from "react-router";
import {
  Plus,
  Search,
  Trash2,
  Edit2,
  MessageSquare,
  Clock,
} from "lucide-react";
import type { SessionsLoaderData } from "../router/loaders";
import type { SessionCamelCase as Session } from "../types";
import { cn } from "../utils/cn";
import { useNewChat } from "../hooks/useNewChat";
import { AISessionCard } from "./AISessionCard";
import { InlineEdit } from "../components/UI/InlineEdit";
import { SimilarSessionsPanel } from "../components/Session/SimilarSessionsPanel";
import {
  ContextMenu,
  type ContextMenuItem,
} from "../components/UI/ContextMenu";
import { Tooltip } from "../components/UI/Tooltip";
import { Button, Input } from "../components/UI";

// =============================================================================
// Types
// =============================================================================

export interface GroupedSessions {
  today: Session[];
  yesterday: Session[];
  older: Session[];
}

/** Metadata for session hover details */
export interface SessionMetadata {
  messageCount?: number;
  firstMessage?: string;
}

/** Map of session IDs to their metadata */
export type SessionMetadataMap = Record<string, SessionMetadata>;

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Group sessions by date (Today, Yesterday, Older)
 */
export function groupSessionsByDate(sessions: Session[]): GroupedSessions {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);

  const groups: GroupedSessions = { today: [], yesterday: [], older: [] };

  for (const session of sessions) {
    const sessionDate = new Date(session.createdAt);
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

// =============================================================================
// Component
// =============================================================================

export interface SessionNavProps {
  className?: string;
  /** Enable AI-powered session intelligence (Sprint 2) */
  enableAI?: boolean;
  /** Show AI-generated session summaries */
  showSummary?: boolean;
  /** Show AI-extracted key topics */
  showTopics?: boolean;
  /** User ID for AI features */
  userId?: string;
  /** Enable inline editing of session names */
  enableEdit?: boolean;
  /** Enable context menu on right-click */
  enableContextMenu?: boolean;
  /** Callback when session is renamed */
  onRenameSession?: (sessionId: string, name: string) => void;
  /** Callback when session is deleted */
  onDeleteSession?: (sessionId: string) => void;
  /** Enable hover tooltip with session details */
  enableHover?: boolean;
  /** Session metadata for hover details */
  sessionMetadata?: SessionMetadataMap;
  /** Enable Similar Sessions Panel (AI-powered) */
  enableSimilarSessions?: boolean;
  /** Optional mapping of session IDs to display names for similar sessions */
  similarSessionNames?: Record<string, string>;
}

/** Helper to format relative time */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60)
    return `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`;
  if (diffHours < 24)
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  if (diffDays === 1) return "yesterday";
  return `${diffDays} days ago`;
}

/** Truncate message with ellipsis */
function truncateMessage(message: string, maxLength = 80): string {
  if (message.length <= maxLength) return message;
  return message.slice(0, maxLength).trim() + "...";
}

export const SessionNav = forwardRef<HTMLElement, SessionNavProps>(
  function SessionNav(
    {
      className,
      enableAI = false,
      showSummary = false,
      showTopics = false,
      userId = "default-user",
      enableEdit = false,
      enableContextMenu = false,
      onRenameSession,
      onDeleteSession,
      enableHover = false,
      sessionMetadata = {},
      enableSimilarSessions = false,
      similarSessionNames = {},
    },
    ref,
  ) {
    const navigate = useNavigate();
    const { sessionId: currentSessionId } = useParams();
    const [searchQuery, setSearchQuery] = useState("");
    // Track which session is currently being edited (double-click to edit)
    const [editingSessionId, setEditingSessionId] = useState<string | null>(
      null,
    );
    // Ref to track click timeout for distinguishing single vs double click
    const clickTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Hook for creating new chat sessions
    const { createNewChat, isCreating } = useNewChat();

    // Get sessions from route loader data
    const loaderData = useRouteLoaderData("studio") as
      | SessionsLoaderData
      | undefined;

    // Memoize sessions to prevent unnecessary re-renders
    const sessions = useMemo(
      () => loaderData?.sessions ?? [],
      [loaderData?.sessions],
    );

    // Filter sessions by search query
    const filteredSessions = useMemo(() => {
      if (!searchQuery.trim()) {
        return sessions;
      }
      const query = searchQuery.toLowerCase();
      return sessions.filter(
        (session) =>
          session.name?.toLowerCase().includes(query) ||
          session.id.toLowerCase().includes(query),
      );
    }, [sessions, searchQuery]);

    // Group sessions by date
    const groupedSessions = useMemo(
      () => groupSessionsByDate(filteredSessions),
      [filteredSessions],
    );

    // Compute session names map for SimilarSessionsPanel
    // Uses provided prop or derives from available sessions
    const sessionNamesMap = useMemo(() => {
      if (Object.keys(similarSessionNames).length > 0) {
        return similarSessionNames;
      }
      // Build map from available sessions
      const map: Record<string, string> = {};
      for (const session of sessions) {
        map[session.id] = session.name || `Session ${session.id.slice(0, 8)}`;
      }
      return map;
    }, [similarSessionNames, sessions]);

    const handleSessionClick = useCallback(
      (session: Session) => {
        navigate(`/studio/chat/${session.id}`);
      },
      [navigate],
    );

    const handleNewChat = useCallback(() => {
      createNewChat();
    }, [createNewChat]);

    const handleSearchChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
      },
      [],
    );

    // Navigate to a similar session when clicked
    const handleSimilarSessionSelect = useCallback(
      (sessionId: string) => {
        navigate(`/studio/chat/${sessionId}`);
      },
      [navigate],
    );

    const renderSessionItem = (session: Session) => {
      // Use AISessionCard when AI is enabled
      if (enableAI) {
        return (
          <li key={session.id}>
            <AISessionCard
              sessionId={session.id}
              title={session.name || `Session ${session.id.slice(0, 8)}`}
              userId={userId}
              showSummary={showSummary}
              showTopics={showTopics}
              timestamp={new Date(session.createdAt)}
              onClick={(id) => navigate(`/studio/chat/${id}`)}
              isActive={session.id === currentSessionId}
              enableAI
            />
          </li>
        );
      }

      // Build context menu items if enabled
      const contextMenuItems: ContextMenuItem[] = enableContextMenu
        ? [
            {
              id: "rename",
              label: "Rename",
              icon: <Edit2 size={14} />,
              action: () => {
                // Trigger inline edit mode (handled by InlineEdit click)
              },
            },
            { id: "divider-1", type: "divider" },
            {
              id: "delete",
              label: "Delete",
              icon: <Trash2 size={14} />,
              action: () => onDeleteSession?.(session.id),
            },
          ]
        : [];

      // Session display name
      const displayName = session.name || `Session ${session.id.slice(0, 8)}`;

      // Handle session rename and exit edit mode
      const handleRename = (newName: string) => {
        onRenameSession?.(session.id, newName);
        setEditingSessionId(null);
      };

      // Handle cancel edit mode
      const handleCancelEdit = () => {
        setEditingSessionId(null);
      };

      // Handle click with debounce for distinguishing single vs double click
      // Single-click navigates (after delay), double-click enters edit mode
      const handleClick = () => {
        if (enableEdit) {
          // When editing is enabled, delay navigation to allow double-click detection
          if (clickTimeoutRef.current) {
            clearTimeout(clickTimeoutRef.current);
          }
          clickTimeoutRef.current = setTimeout(() => {
            handleSessionClick(session);
            clickTimeoutRef.current = null;
          }, 200); // 200ms delay to detect double-click
        } else {
          // When editing is disabled, navigate immediately
          handleSessionClick(session);
        }
      };

      // Handle double-click to enter edit mode (when enableEdit is true)
      const handleDoubleClick = (e: React.MouseEvent) => {
        if (enableEdit) {
          e.preventDefault();
          e.stopPropagation();
          // Cancel the pending single-click navigation
          if (clickTimeoutRef.current) {
            clearTimeout(clickTimeoutRef.current);
            clickTimeoutRef.current = null;
          }
          setEditingSessionId(session.id);
        }
      };

      // Check if this session is currently being edited
      const isEditing = editingSessionId === session.id;

      // Get session metadata for hover tooltip
      const metadata = sessionMetadata[session.id];
      const createdAt = new Date(session.createdAt);

      // Build hover tooltip content
      const hoverContent = (
        <div className="space-y-1.5 min-w-48 max-w-64">
          <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
            <Clock size={12} />
            <span>Created {formatRelativeTime(createdAt)}</span>
          </div>
          {metadata?.messageCount !== undefined && (
            <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
              <MessageSquare size={12} />
              <span>
                {metadata.messageCount} message
                {metadata.messageCount === 1 ? "" : "s"}
              </span>
            </div>
          )}
          {metadata?.firstMessage && (
            <p className="text-xs text-neutral-300 italic border-t border-neutral-600 pt-1.5 mt-1.5">
              {truncateMessage(metadata.firstMessage)}
            </p>
          )}
        </div>
      );

      // Standard session item with optional inline edit and context menu
      // Single-click navigates, double-click enters edit mode (when enableEdit is true)
      const sessionContent = (
        <div
          className={cn(
            "w-full text-left px-3 py-2 rounded-lg text-sm",
            "transition-colors",
            session.id === currentSessionId
              ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
              : "text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
          )}
        >
          {isEditing ? (
            <InlineEdit
              value={displayName}
              onSave={handleRename}
              onCancel={handleCancelEdit}
              placeholder="Session name"
              aria-label={`Rename session ${displayName}`}
              className="w-full"
              startInEditMode
            />
          ) : (
            <Button
              className="w-full text-left truncate"
              type="button"
              onClick={handleClick}
              onDoubleClick={handleDoubleClick}
            >
              {displayName}
            </Button>
          )}
        </div>
      );

      // Wrap with Tooltip if hover is enabled
      const sessionWithHover = enableHover ? (
        <Tooltip content={hoverContent} position="right" delay={200}>
          {sessionContent}
        </Tooltip>
      ) : (
        sessionContent
      );

      return (
        <li key={session.id}>
          {enableContextMenu ? (
            <ContextMenu items={contextMenuItems} aria-label="Session actions">
              {sessionWithHover}
            </ContextMenu>
          ) : (
            sessionWithHover
          )}
        </li>
      );
    };

    return (
      <nav
        ref={ref}
        data-testid="session-nav"
        aria-label="Session navigation"
        className={cn(
          "flex flex-col h-full",
          "bg-neutral-50 dark:bg-neutral-800",
          "border-r border-neutral-200 dark:border-neutral-700",
          className,
        )}
      >
        {/* Header with New Chat button */}
        <div className="p-2 border-b border-neutral-200 dark:border-neutral-700">
          <Button
            type="button"
            data-testid="new-chat-button"
            onClick={handleNewChat}
            disabled={isCreating}
            className={cn(
              "w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg",
              "bg-primary-500 hover:bg-primary-600",
              "text-white font-medium text-sm",
              "transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
              isCreating && "opacity-50 cursor-not-allowed",
            )}
          >
            <Plus size={16} className={cn(isCreating && "animate-spin")} />
            <span>{isCreating ? "Creating..." : "New Chat"}</span>
          </Button>
        </div>
        {/* Search */}
        <div className="p-2">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
              aria-hidden="true"
            />
            <Input
              data-testid="session-search"
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={handleSearchChange}
              aria-label="Search sessions"
              className={cn(
                "w-full pl-9 pr-3 py-2 rounded-lg text-sm",
                "bg-white dark:bg-neutral-900",
                "border border-neutral-200 dark:border-neutral-700",
                "focus:outline-none focus:ring-2 focus:ring-primary-500",
                "placeholder-neutral-400",
              )}
            />
          </div>
        </div>
        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-2" aria-label="Sessions">
          {filteredSessions.length === 0 ? (
            <div className="text-sm text-neutral-500 dark:text-neutral-400 italic text-center mt-4">
              {searchQuery ? "No matching sessions" : "No sessions yet"}
            </div>
          ) : (
            <>
              {groupedSessions.today.length > 0 && (
                <section
                  className="mb-3"
                  aria-labelledby="today-sessions-heading"
                >
                  <h3
                    id="today-sessions-heading"
                    className="text-xs text-neutral-400 dark:text-neutral-400 uppercase tracking-wider mb-2"
                  >
                    Today
                  </h3>
                  <ul className="space-y-1" role="list">
                    {groupedSessions.today.map(renderSessionItem)}
                  </ul>
                </section>
              )}
              {groupedSessions.yesterday.length > 0 && (
                <section
                  className="mb-3"
                  aria-labelledby="yesterday-sessions-heading"
                >
                  <h3
                    id="yesterday-sessions-heading"
                    className="text-xs text-neutral-400 dark:text-neutral-400 uppercase tracking-wider mb-2"
                  >
                    Yesterday
                  </h3>
                  <ul className="space-y-1" role="list">
                    {groupedSessions.yesterday.map(renderSessionItem)}
                  </ul>
                </section>
              )}
              {groupedSessions.older.length > 0 && (
                <section
                  className="mb-3"
                  aria-labelledby="older-sessions-heading"
                >
                  <h3
                    id="older-sessions-heading"
                    className="text-xs text-neutral-400 dark:text-neutral-400 uppercase tracking-wider mb-2"
                  >
                    Older
                  </h3>
                  <ul className="space-y-1" role="list">
                    {groupedSessions.older.map(renderSessionItem)}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
        {/* Similar Sessions Panel - shown at bottom when enabled */}
        {enableSimilarSessions && currentSessionId && (
          <div className="border-t border-neutral-200 dark:border-neutral-700">
            <SimilarSessionsPanel
              sessionId={currentSessionId}
              userId={userId}
              sessionNames={sessionNamesMap}
              onSessionSelect={handleSimilarSessionSelect}
              limit={5}
            />
          </div>
        )}
      </nav>
    );
  },
);

// Display name for DevTools
SessionNav.displayName = "SessionNav";
