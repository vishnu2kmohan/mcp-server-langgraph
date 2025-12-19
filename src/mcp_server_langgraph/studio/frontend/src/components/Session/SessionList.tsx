/**
 * SessionList Component
 *
 * Sidebar component for displaying and managing chat sessions.
 * Features:
 * - Session list with search/filter
 * - Pin/unpin sessions
 * - Delete, rename sessions
 * - Keyboard navigation (arrow keys, Cmd+K for search)
 * - Loading and empty states
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import {
  useState,
  useMemo,
  useCallback,
  useRef,
  useEffect,
  type KeyboardEvent,
} from "react";
import {
  Search,
  X,
  Plus,
  MoreVertical,
  Pin,
  PinOff,
  Trash2,
  Edit2,
  MessageSquare,
} from "lucide-react";
import { usePreferences } from "../../contexts/PreferencesContext";
import type { SessionSummary } from "../../types/session";

// ==============================================================================
// Types
// ==============================================================================

export interface SessionListProps {
  /** List of session summaries */
  sessions: SessionSummary[];
  /** Currently selected session ID */
  selectedId?: string;
  /** Whether sessions are loading */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when a session is selected */
  onSelect?: (sessionId: string) => void;
  /** Callback when a session is deleted */
  onDelete?: (sessionId: string) => void;
  /** Callback when a session is renamed */
  onRename?: (sessionId: string, newName: string) => void;
  /** Callback when a new session is created */
  onCreate?: () => void;
}

// ==============================================================================
// Component
// ==============================================================================

export function SessionList({
  sessions,
  selectedId,
  isLoading = false,
  className = "",
  onSelect,
  onDelete,
  onRename,
  onCreate,
}: SessionListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const { preferences, pinSession, unpinSession } = usePreferences();
  const pinnedSessionIds = preferences.session.pinnedSessions;

  // ---------------------------------------------------------------------------
  // Filter and sort sessions
  // ---------------------------------------------------------------------------
  const filteredSessions = useMemo(() => {
    let result = sessions;

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter((s) => s.name.toLowerCase().includes(query));
    }

    // Separate pinned and unpinned
    const pinned = result.filter((s) => pinnedSessionIds.includes(s.id));
    const unpinned = result.filter((s) => !pinnedSessionIds.includes(s.id));

    // Sort each group by updatedAt (most recent first)
    pinned.sort((a, b) => b.updatedAt - a.updatedAt);
    unpinned.sort((a, b) => b.updatedAt - a.updatedAt);

    // Pinned sessions first
    return [...pinned, ...unpinned];
  }, [sessions, searchQuery, pinnedSessionIds]);

  // ---------------------------------------------------------------------------
  // Keyboard shortcuts
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      // Cmd+K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenuId(null);
      }
    };

    if (activeMenuId) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [activeMenuId]);

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const handleListKeyDown = useCallback(
    (e: KeyboardEvent<HTMLUListElement>) => {
      if (!onSelect || filteredSessions.length === 0) return;

      const currentIndex = filteredSessions.findIndex(
        (s) => s.id === selectedId,
      );

      switch (e.key) {
        case "ArrowDown": {
          e.preventDefault();
          const nextIndex = Math.min(
            currentIndex + 1,
            filteredSessions.length - 1,
          );
          if (nextIndex !== currentIndex || currentIndex === -1) {
            onSelect(filteredSessions[nextIndex === -1 ? 0 : nextIndex].id);
          }
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const prevIndex = Math.max(currentIndex - 1, 0);
          if (prevIndex !== currentIndex) {
            onSelect(filteredSessions[prevIndex].id);
          }
          break;
        }
        case "Home": {
          e.preventDefault();
          onSelect(filteredSessions[0].id);
          break;
        }
        case "End": {
          e.preventDefault();
          onSelect(filteredSessions[filteredSessions.length - 1].id);
          break;
        }
      }
    },
    [filteredSessions, selectedId, onSelect],
  );

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  const handlePin = useCallback(
    (sessionId: string) => {
      if (pinnedSessionIds.includes(sessionId)) {
        unpinSession(sessionId);
      } else {
        pinSession(sessionId);
      }
      setActiveMenuId(null);
    },
    [pinnedSessionIds, pinSession, unpinSession],
  );

  const handleDelete = useCallback(
    (sessionId: string) => {
      onDelete?.(sessionId);
      setActiveMenuId(null);
    },
    [onDelete],
  );

  const handleStartRename = useCallback((session: SessionSummary) => {
    setEditingId(session.id);
    setEditName(session.name);
    setActiveMenuId(null);
  }, []);

  const handleRenameSubmit = useCallback(
    (sessionId: string) => {
      if (editName.trim() && onRename) {
        onRename(sessionId, editName.trim());
      }
      setEditingId(null);
      setEditName("");
    },
    [editName, onRename],
  );

  const handleRenameKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>, sessionId: string) => {
      if (e.key === "Enter") {
        handleRenameSubmit(sessionId);
      } else if (e.key === "Escape") {
        setEditingId(null);
        setEditName("");
      }
    },
    [handleRenameSubmit],
  );

  // ---------------------------------------------------------------------------
  // Format relative time
  // ---------------------------------------------------------------------------
  const formatRelativeTime = (timestamp: number): string => {
    const diff = Date.now() - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  // ---------------------------------------------------------------------------
  // Render loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div
        data-testid="session-list-loading"
        className={`session-list ${className}`}
      >
        <div className="p-3 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render empty state
  // ---------------------------------------------------------------------------
  if (sessions.length === 0) {
    return (
      <div className={`session-list ${className}`}>
        <div className="p-4 text-center">
          <MessageSquare
            className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600 mb-3"
            aria-hidden="true"
          />
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            No sessions yet
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Start a new conversation to begin
          </p>
          {onCreate && (
            <button
              onClick={onCreate}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <Plus size={16} />
              New Session
            </button>
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className={`session-list flex flex-col h-full ${className}`}>
      {/* Header with search and new button */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 space-y-2">
        {/* Search */}
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search sessions..."
            aria-label="Search sessions"
            className="w-full pl-9 pr-8 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* New session button */}
        {onCreate && (
          <button
            onClick={onCreate}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Plus size={16} />
            New Session
          </button>
        )}
      </div>

      {/* Session list */}
      <ul
        ref={listRef}
        role="list"
        tabIndex={0}
        onKeyDown={handleListKeyDown}
        className="flex-1 overflow-y-auto"
        aria-label="Chat sessions"
      >
        {filteredSessions.length === 0 ? (
          <li className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
            No sessions found
          </li>
        ) : (
          filteredSessions.map((session) => {
            const isPinned = pinnedSessionIds.includes(session.id);
            const isSelected = session.id === selectedId;
            const isEditing = session.id === editingId;

            return (
              <li
                key={session.id}
                aria-current={isSelected ? "true" : undefined}
                className={`group relative px-3 py-2 cursor-pointer border-b border-gray-100 dark:border-gray-800 ${
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-900/30"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
                }`}
                onClick={() => !isEditing && onSelect?.(session.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => handleRenameKeyDown(e, session.id)}
                        onBlur={() => handleRenameSubmit(session.id)}
                        autoFocus
                        className="w-full px-1 py-0.5 text-sm rounded border border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-800"
                      />
                    ) : (
                      <div className="flex items-center gap-1.5">
                        {isPinned && (
                          <Pin
                            size={12}
                            className="text-blue-500 flex-shrink-0"
                            aria-label="Pinned"
                          />
                        )}
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {session.name}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                      <span>{session.messageCount} messages</span>
                      <span>•</span>
                      <span>{formatRelativeTime(session.updatedAt)}</span>
                    </div>
                  </div>

                  {/* Actions button */}
                  <div
                    className={`flex-shrink-0 ${
                      activeMenuId === session.id
                        ? "opacity-100"
                        : "opacity-0 group-hover:opacity-100"
                    }`}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveMenuId(
                          activeMenuId === session.id ? null : session.id,
                        );
                      }}
                      aria-label="Session actions"
                      aria-haspopup="menu"
                      aria-expanded={activeMenuId === session.id}
                      className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <MoreVertical size={14} />
                    </button>

                    {/* Actions menu */}
                    {activeMenuId === session.id && (
                      <div
                        ref={menuRef}
                        role="menu"
                        className="absolute right-2 top-10 z-10 w-36 rounded-md bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black/5 dark:ring-white/10"
                      >
                        <div className="py-1">
                          <button
                            role="menuitem"
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePin(session.id);
                            }}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                          >
                            {isPinned ? (
                              <>
                                <PinOff size={14} />
                                Unpin
                              </>
                            ) : (
                              <>
                                <Pin size={14} />
                                Pin
                              </>
                            )}
                          </button>
                          <button
                            role="menuitem"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartRename(session);
                            }}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                          >
                            <Edit2 size={14} />
                            Rename
                          </button>
                          <button
                            role="menuitem"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(session.id);
                            }}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            <Trash2 size={14} />
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}

export default SessionList;
