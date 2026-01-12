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
  FolderOpen,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { usePreferences } from "../../contexts/PreferencesContext";
import {
  useSessionGroups,
  type SessionGroup,
} from "../../hooks/useSessionIntelligence";
import type { SessionSummary } from "../../types/session";
import { AIEmptyState } from "../EmptyState/AIEmptyState";

import { Button, Input } from "@/components/UI";

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
  /** Enable AI-powered session grouping */
  enableAIGrouping?: boolean;
  /** User ID for AI grouping (required when enableAIGrouping is true) */
  userId?: string;
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
  enableAIGrouping = false,
  userId,
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

  // AI-powered session grouping
  const sessionIds = useMemo(() => sessions.map((s) => s.id), [sessions]);
  const {
    groups: aiGroups,
    ungrouped: ungroupedIds,
    isLoading: isGroupsLoading,
    error: groupsError,
  } = useSessionGroups({
    userId: userId ?? "",
    sessionIds: enableAIGrouping && userId ? sessionIds : [],
    enabled: enableAIGrouping && !!userId,
  });

  // Create a session lookup map for group rendering
  const sessionMap = useMemo(() => {
    const map = new Map<string, SessionSummary>();
    sessions.forEach((s) => map.set(s.id, s));
    return map;
  }, [sessions]);

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
    return undefined;
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
          const targetIndex = nextIndex === -1 ? 0 : nextIndex;
          const targetSession = filteredSessions[targetIndex];
          if (
            targetSession &&
            (nextIndex !== currentIndex || currentIndex === -1)
          ) {
            onSelect(targetSession.id);
          }
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const prevIndex = Math.max(currentIndex - 1, 0);
          const prevSession = filteredSessions[prevIndex];
          if (prevSession && prevIndex !== currentIndex) {
            onSelect(prevSession.id);
          }
          break;
        }
        case "Home": {
          e.preventDefault();
          const firstSession = filteredSessions[0];
          if (firstSession) {
            onSelect(firstSession.id);
          }
          break;
        }
        case "End": {
          e.preventDefault();
          const lastSession = filteredSessions[filteredSessions.length - 1];
          if (lastSession) {
            onSelect(lastSession.id);
          }
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
  // Render session item
  // ---------------------------------------------------------------------------
  const renderSessionItem = (session: SessionSummary) => {
    const isPinned = pinnedSessionIds.includes(session.id);
    const isSelected = session.id === selectedId;
    const isEditing = session.id === editingId;

    return (
      <li
        key={session.id}
        aria-current={isSelected ? "true" : undefined}
        className={`group relative px-3 py-2 cursor-pointer border-b border-neutral-100 dark:border-neutral-800 ${
          isSelected
            ? "bg-primary-50 dark:bg-primary-900/30"
            : "hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
        }`}
        onClick={() => !isEditing && onSelect?.(session.id)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <Input
                className="px-1 py-0.5 text-sm border-primary-500 focus:ring-primary-500"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => handleRenameKeyDown(e, session.id)}
                onBlur={() => handleRenameSubmit(session.id)}
                autoFocus
              />
            ) : (
              <div className="flex items-center gap-1.5">
                {isPinned && (
                  <Pin
                    size={12}
                    className="text-primary-500 flex-shrink-0"
                    aria-label="Pinned"
                  />
                )}
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                  {session.name}
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
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
            <Button
              variant="secondary"
              className="p-1 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 focus:ring-primary-500"
              onClick={(e) => {
                e.stopPropagation();
                setActiveMenuId(
                  activeMenuId === session.id ? null : session.id,
                );
              }}
              aria-label="Session actions"
              aria-haspopup="menu"
              aria-expanded={activeMenuId === session.id}
            >
              <MoreVertical size={14} />
            </Button>

            {/* Actions menu */}
            {activeMenuId === session.id && (
              <div
                ref={menuRef}
                role="menu"
                className="absolute right-2 top-10 z-10 w-36 rounded-md bg-white dark:bg-neutral-900 shadow-lg ring-1 ring-black/5 dark:ring-white/10"
              >
                <div className="py-1">
                  <Button
                    variant="secondary"
                    className="w-full flex px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePin(session.id);
                    }}
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
                  </Button>
                  <Button
                    variant="secondary"
                    className="w-full flex px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStartRename(session);
                    }}
                  >
                    <Edit2 size={14} />
                    Rename
                  </Button>
                  <Button
                    variant="danger"
                    className="w-full flex px-3 py-1.5 text-sm text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(session.id);
                    }}
                  >
                    <Trash2 size={14} />
                    Delete
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </li>
    );
  };

  // ---------------------------------------------------------------------------
  // Render group header
  // ---------------------------------------------------------------------------
  const renderGroupHeader = (group: SessionGroup) => (
    <li
      key={`group-${group.topic}`}
      className="px-3 py-2 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-200 dark:border-neutral-700"
      role="presentation"
      data-testid={`group-header-${group.topic.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <div className="flex items-center gap-2">
        <FolderOpen
          size={14}
          className="text-neutral-500 dark:text-neutral-400"
        />
        <span className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 uppercase tracking-wide">
          {group.topic}
        </span>
        <span className="text-xs text-neutral-400 dark:text-neutral-400">
          ({group.sessionIds.length})
        </span>
      </div>
    </li>
  );

  // ---------------------------------------------------------------------------
  // Render sessions content (grouped or flat)
  // ---------------------------------------------------------------------------
  const renderSessionsContent = () => {
    // Show loading indicator for AI grouping
    if (enableAIGrouping && isGroupsLoading) {
      return (
        <li
          className="p-4 text-center"
          data-testid="ai-grouping-loading"
          role="status"
        >
          <Loader2 className="mx-auto h-5 w-5 animate-spin text-primary-500" />
          <span className="sr-only">Loading AI groups...</span>
        </li>
      );
    }

    // Show error state for AI grouping
    if (enableAIGrouping && groupsError) {
      return (
        <li
          className="p-4 text-center text-sm text-warning-600 dark:text-warning-400"
          data-testid="ai-grouping-error"
          role="alert"
        >
          <AlertCircle className="mx-auto h-5 w-5 mb-1" aria-hidden="true" />
          <span>Failed to load AI groups. Showing default order.</span>
        </li>
      );
    }

    // If AI grouping is enabled and we have groups, render grouped view
    if (
      enableAIGrouping &&
      aiGroups.length > 0 &&
      !isGroupsLoading &&
      !groupsError
    ) {
      const elements: React.ReactNode[] = [];

      // Render each group with its sessions
      aiGroups.forEach((group) => {
        elements.push(renderGroupHeader(group));
        group.sessionIds.forEach((sessionId) => {
          const session = sessionMap.get(sessionId);
          if (session) {
            // Apply search filter
            if (
              searchQuery.trim() &&
              !session.name.toLowerCase().includes(searchQuery.toLowerCase())
            ) {
              return;
            }
            elements.push(renderSessionItem(session));
          }
        });
      });

      // Render ungrouped sessions
      if (ungroupedIds.length > 0) {
        elements.push(
          <li
            key="group-ungrouped"
            className="px-3 py-2 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-200 dark:border-neutral-700"
            role="presentation"
          >
            <div className="flex items-center gap-2">
              <MessageSquare
                size={14}
                className="text-neutral-500 dark:text-neutral-400"
              />
              <span className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 uppercase tracking-wide">
                Other
              </span>
              <span className="text-xs text-neutral-400 dark:text-neutral-400">
                ({ungroupedIds.length})
              </span>
            </div>
          </li>,
        );
        ungroupedIds.forEach((sessionId) => {
          const session = sessionMap.get(sessionId);
          if (session) {
            // Apply search filter
            if (
              searchQuery.trim() &&
              !session.name.toLowerCase().includes(searchQuery.toLowerCase())
            ) {
              return;
            }
            elements.push(renderSessionItem(session));
          }
        });
      }

      return elements.length > 0 ? (
        elements
      ) : (
        // No matches in grouped view - AI-enhanced (Sprint 3 Migration)
        <li className="p-4">
          <AIEmptyState
            context="sessions"
            emptyType="no-matches"
            searchQuery={searchQuery || undefined}
            variant="inline"
            enableAI={false}
          />
        </li>
      );
    }

    // Default: render flat list (filteredSessions)
    if (filteredSessions.length === 0) {
      return (
        // No matches in flat view - AI-enhanced (Sprint 3 Migration)
        <li className="p-4">
          <AIEmptyState
            context="sessions"
            emptyType="no-matches"
            searchQuery={searchQuery || undefined}
            variant="inline"
            enableAI={false}
          />
        </li>
      );
    }

    return filteredSessions.map((session) => renderSessionItem(session));
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
              <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-2" />
              <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render empty state - AI-enhanced (Sprint 3 Migration)
  // ---------------------------------------------------------------------------
  if (sessions.length === 0) {
    return (
      <div className={`session-list ${className}`}>
        <AIEmptyState
          context="sessions"
          emptyType="empty"
          variant="compact"
          onAction={onCreate}
          actionLabel="New Session"
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className={`session-list flex flex-col h-full ${className}`}>
      {/* Header with search and new button */}
      <div className="p-3 border-b border-neutral-200 dark:border-neutral-700 space-y-2">
        {/* Search */}
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
            aria-hidden="true"
          />
          <Input
            className="pl-9 pr-8 py-1.5 text-sm -500 focus:ring-primary-500"
            ref={searchInputRef}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search sessions..."
            aria-label="Search sessions"
          />
          {searchQuery && (
            <Button
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
            >
              <X size={14} />
            </Button>
          )}
        </div>

        {/* New session button */}
        {onCreate && (
          <Button
            variant="secondary"
            className="w-full flex .5 px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 rounded-md hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 focus:ring-primary-500"
            onClick={onCreate}
          >
            <Plus size={16} />
            New Session
          </Button>
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
        {renderSessionsContent()}
      </ul>
    </div>
  );
}

export default SessionList;
