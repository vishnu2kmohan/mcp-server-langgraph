/**
 * SessionPanel Component
 *
 * Collapsible left panel showing session list in ChatPage.
 * Features:
 * - List of recent sessions (most recent 5 by default)
 * - New session creation
 * - Session selection
 * - Collapsible/expandable panel
 * - Loading state
 * - Single session delete with confirmation
 */

import { useState } from "react";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  X,
  MoreVertical,
  Trash2,
} from "lucide-react";
import { Skeleton } from "../UI/Skeleton";
import { BulkActionBar } from "../UI/BulkActionBar";
import { ConfirmDialog } from "../UI/ConfirmDialog";

export interface Session {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  messageCount?: number;
}

export interface SessionPanelProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  isLoading?: boolean;
  maxRecent?: number;
  // Search functionality
  enableSearch?: boolean;
  onSearch?: (query: string) => void;
  // Status filter
  enableStatusFilter?: boolean;
  statusFilter?: string;
  onStatusChange?: (status: string) => void;
  // Cursor pagination
  hasMore?: boolean;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  totalCount?: number;
  // Bulk selection
  enableBulkSelect?: boolean;
  onBulkDelete?: (sessionIds: string[]) => void | Promise<void>;
  // Single session delete
  onDelete?: (sessionId: string) => void | Promise<void>;
}

export function SessionPanel({
  sessions,
  currentSessionId,
  onSessionSelect,
  onNewSession,
  isLoading = false,
  maxRecent = 5,
  enableSearch = false,
  onSearch,
  enableStatusFilter = false,
  statusFilter = "",
  onStatusChange,
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  totalCount,
  enableBulkSelect = false,
  onBulkDelete,
  onDelete,
}: SessionPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState(statusFilter);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(
    new Set(),
  );
  // State for single session delete
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [deleteConfirmSessionId, setDeleteConfirmSessionId] = useState<
    string | null
  >(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    onSearch?.(value);
  };

  const handleSearchClear = () => {
    setSearchQuery("");
    onSearch?.("");
  };

  const handleStatusClick = (status: string) => {
    setSelectedStatus(status);
    onStatusChange?.(status);
  };

  // Bulk selection handlers
  const handleSelectAll = () => {
    if (selectedSessions.size === displaySessions.length) {
      setSelectedSessions(new Set());
    } else {
      setSelectedSessions(new Set(displaySessions.map((s) => s.id)));
    }
  };

  const handleSelectSession = (sessionId: string) => {
    setSelectedSessions((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  };

  const handleClearSelection = () => {
    setSelectedSessions(new Set());
  };

  const handleBulkDelete = async () => {
    if (onBulkDelete) {
      await onBulkDelete(Array.from(selectedSessions));
      setSelectedSessions(new Set());
    }
  };

  // Single session delete handlers
  const handleMenuToggle = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === sessionId ? null : sessionId);
  };

  const handleDeleteClick = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuId(null);
    setDeleteConfirmSessionId(sessionId);
  };

  const handleDeleteConfirm = async () => {
    if (deleteConfirmSessionId && onDelete) {
      await onDelete(deleteConfirmSessionId);
      setDeleteConfirmSessionId(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmSessionId(null);
  };

  // Sort sessions by most recent (updatedAt or createdAt)
  const sortedSessions = [...sessions].sort((a, b) => {
    const dateA = new Date(a.updatedAt || a.createdAt).getTime();
    const dateB = new Date(b.updatedAt || b.createdAt).getTime();
    return dateB - dateA;
  });

  // Show only the most recent sessions (or all if cursor pagination is used)
  const displaySessions =
    hasMore || onLoadMore ? sortedSessions : sortedSessions.slice(0, maxRecent);
  // Show Load More button if prop hasMore is true or if there are more sessions than maxRecent
  const showLoadMore = hasMore || sortedSessions.length > maxRecent;

  const handleSessionClick = (sessionId: string) => {
    // Don't trigger if clicking current session
    if (sessionId === currentSessionId) {
      return;
    }
    onSessionSelect(sessionId);
  };

  // Get session name for delete confirmation
  const deleteSessionName = deleteConfirmSessionId
    ? sessions.find((s) => s.id === deleteConfirmSessionId)?.name ||
      "this session"
    : "";

  if (isCollapsed) {
    return (
      <div
        className="hidden md:flex w-12 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex-col items-center py-4"
        role="navigation"
        aria-label="Sessions"
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          aria-label="Expand sessions panel"
        >
          <ChevronRight size={20} />
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Mobile overlay backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 md:hidden"
        onClick={() => setIsCollapsed(true)}
        data-testid="session-panel-overlay"
      />
      <div
        className={`
          w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col
          fixed md:relative z-50 h-full
          transform transition-transform duration-200 ease-in-out
          translate-x-0
        `}
        role="navigation"
        aria-label="Sessions"
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-gray-100">
            Sessions
          </h2>
          <div className="flex items-center gap-1">
            <button
              onClick={onNewSession}
              className="flex items-center gap-1 px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              aria-label="New session"
            >
              <Plus size={16} />
              New
            </button>
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              aria-label="Collapse sessions panel"
            >
              <ChevronLeft size={18} />
            </button>
          </div>
        </div>

        {/* Search Input */}
        {enableSearch && (
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <input
                type="search"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search sessions..."
                className="w-full px-2 py-1.5 pr-8 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {searchQuery.length > 0 && (
                <button
                  type="button"
                  onClick={handleSearchClear}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  aria-label="Clear search"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Status Filter */}
        {enableStatusFilter && (
          <div
            className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex gap-1"
            role="group"
            aria-label="Status filter"
          >
            <button
              onClick={() => handleStatusClick("")}
              className={`px-2 py-1 text-xs rounded ${
                selectedStatus === ""
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
              aria-pressed={selectedStatus === ""}
            >
              All
            </button>
            <button
              onClick={() => handleStatusClick("active")}
              className={`px-2 py-1 text-xs rounded ${
                selectedStatus === "active"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
              aria-pressed={selectedStatus === "active"}
            >
              Active
            </button>
            <button
              onClick={() => handleStatusClick("archived")}
              className={`px-2 py-1 text-xs rounded ${
                selectedStatus === "archived"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
              aria-pressed={selectedStatus === "archived"}
            >
              Archived
            </button>
          </div>
        )}

        {/* Session Count */}
        {totalCount !== undefined && (
          <div className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
            {sessions.length} of {totalCount} sessions
          </div>
        )}

        {/* Select All Checkbox */}
        {enableBulkSelect && sessions.length > 0 && !isLoading && (
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
            <input
              type="checkbox"
              id="select-all-sessions"
              checked={
                selectedSessions.size === displaySessions.length &&
                displaySessions.length > 0
              }
              onChange={handleSelectAll}
              aria-label="Select all sessions"
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label
              htmlFor="select-all-sessions"
              className="text-sm text-gray-600 dark:text-gray-400"
            >
              Select All
            </label>
          </div>
        )}

        {/* Session List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="px-4 py-2 space-y-2">
              {/* Session skeleton items */}
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <Skeleton className="h-4 w-3/4 mb-2" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center text-gray-500 dark:text-gray-400">
              <MessageSquare size={32} className="mb-2 opacity-50" />
              <p className="text-sm mb-3">No sessions yet</p>
              <button
                onClick={onNewSession}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                New Session
              </button>
            </div>
          ) : (
            <div className="px-2 py-2 space-y-1">
              {displaySessions.map((session) => (
                <div
                  key={session.id}
                  data-testid={`session-item-${session.id}`}
                  className={`flex items-center gap-2 w-full text-left px-3 py-2 rounded transition-colors ${
                    session.id === currentSessionId
                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                >
                  {enableBulkSelect && (
                    <input
                      type="checkbox"
                      checked={selectedSessions.has(session.id)}
                      onChange={() => handleSelectSession(session.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
                    />
                  )}
                  <button
                    onClick={() => handleSessionClick(session.id)}
                    className="flex-1 text-left min-w-0"
                  >
                    <div className="font-medium truncate">{session.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {session.messageCount ?? 0} messages
                    </div>
                  </button>
                  {/* Session menu button */}
                  {onDelete && (
                    <div className="relative flex-shrink-0">
                      <button
                        onClick={(e) => handleMenuToggle(session.id, e)}
                        className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                        aria-label="Session menu"
                        data-testid={`session-menu-${session.id}`}
                      >
                        <MoreVertical size={16} />
                      </button>
                      {/* Dropdown menu */}
                      {openMenuId === session.id && (
                        <div className="absolute right-0 mt-1 w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-50">
                          <button
                            onClick={(e) => handleDeleteClick(session.id, e)}
                            className="w-full px-3 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                          >
                            <Trash2 size={14} />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* See All / Load More Link */}
          {showLoadMore && !isLoading && (
            <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={onLoadMore}
                disabled={loadingMore}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
              >
                {loadingMore
                  ? "Loading..."
                  : hasMore || onLoadMore
                    ? "Load More"
                    : `See All (${sortedSessions.length})`}
              </button>
            </div>
          )}
        </div>

        {/* Bulk Action Bar */}
        {enableBulkSelect && (
          <BulkActionBar
            selectedCount={selectedSessions.size}
            onClearSelection={handleClearSelection}
            onDelete={handleBulkDelete}
          />
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteConfirmSessionId !== null}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Session"
        message={`Are you sure you want to delete "${deleteSessionName}"? This action cannot be undone.`}
        confirmText="Confirm"
        cancelText="Cancel"
        isDestructive={true}
      />
    </>
  );
}
