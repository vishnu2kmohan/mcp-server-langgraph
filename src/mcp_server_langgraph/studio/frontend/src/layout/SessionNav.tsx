/**
 * SessionNav Component
 *
 * Time-travel grouped session navigation sidebar.
 * Extracted from HybridShellLayout for maintainability.
 *
 * Features:
 * - Session grouping by date (Today, Yesterday, Older)
 * - Search/filter sessions
 * - New chat creation
 * - Active session highlighting
 * - AI-powered session intelligence (Sprint 2)
 */
/* eslint-disable react-refresh/only-export-components -- Exports groupSessionsByDate utility alongside component */
import { useCallback, useMemo, useState } from "react";
import { useNavigate, useRouteLoaderData, useParams } from "react-router";
import { Plus, Search } from "lucide-react";
import type { SessionsLoaderData } from "../router/loaders";
import type { Session } from "../types";
import { cn } from "../utils/cn";
import { useNewChat } from "../hooks/useNewChat";
import { AISessionCard } from "./AISessionCard";

// =============================================================================
// Types
// =============================================================================

export interface GroupedSessions {
  today: Session[];
  yesterday: Session[];
  older: Session[];
}

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
}

export function SessionNav({
  className,
  enableAI = false,
  showSummary = false,
  showTopics = false,
  userId = "default-user",
}: SessionNavProps) {
  const navigate = useNavigate();
  const { sessionId: currentSessionId } = useParams();
  const [searchQuery, setSearchQuery] = useState("");

  // Hook for creating new chat sessions
  const { createNewChat, isCreating } = useNewChat();

  // Get sessions from route loader data
  const loaderData = useRouteLoaderData("studio-v2") as
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

  const handleSessionClick = useCallback(
    (session: Session) => {
      navigate(`/studio/v2/chat/${session.id}`);
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
            timestamp={new Date(session.created_at)}
            onClick={(id) => navigate(`/studio/v2/chat/${id}`)}
            isActive={session.id === currentSessionId}
            enableAI
          />
        </li>
      );
    }

    // Standard session button (when AI is disabled)
    return (
      <li key={session.id}>
        <button
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
      </li>
    );
  };

  return (
    <nav
      data-testid="session-nav"
      aria-label="Session navigation"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-800",
        "border-r border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Header with New Chat button */}
      <div className="p-2 border-b border-gray-200 dark:border-gray-700">
        <button
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
        </button>
      </div>

      {/* Search */}
      <div className="p-2">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <input
            type="text"
            data-testid="session-search"
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={handleSearchChange}
            aria-label="Search sessions"
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
      <div className="flex-1 overflow-y-auto p-2" aria-label="Sessions">
        {filteredSessions.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 italic text-center mt-4">
            {searchQuery ? "No matching sessions" : "No sessions yet"}
          </div>
        ) : (
          <>
            {groupedSessions.today.length > 0 && (
              <section className="mb-3" aria-labelledby="today-sessions-heading">
                <h3 id="today-sessions-heading" className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Today
                </h3>
                <ul className="space-y-1" role="list">
                  {groupedSessions.today.map(renderSessionItem)}
                </ul>
              </section>
            )}
            {groupedSessions.yesterday.length > 0 && (
              <section className="mb-3" aria-labelledby="yesterday-sessions-heading">
                <h3 id="yesterday-sessions-heading" className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Yesterday
                </h3>
                <ul className="space-y-1" role="list">
                  {groupedSessions.yesterday.map(renderSessionItem)}
                </ul>
              </section>
            )}
            {groupedSessions.older.length > 0 && (
              <section className="mb-3" aria-labelledby="older-sessions-heading">
                <h3 id="older-sessions-heading" className="text-xs text-gray-400 uppercase tracking-wider mb-2">
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
    </nav>
  );
}
