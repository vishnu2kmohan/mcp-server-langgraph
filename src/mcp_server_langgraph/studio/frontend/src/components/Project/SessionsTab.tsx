/**
 * SessionsTab Component
 *
 * Project sessions tab with list display, create/remove operations,
 * and bulk selection with BulkActionBar.
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { Plus, MessageSquare, Trash2, X } from "lucide-react";
import { BulkActionBar } from "../UI/BulkActionBar";
import { authenticatedFetch } from "../../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../../utils/intendedRoute";

// ============================================================================
// Types
// ============================================================================

export interface SessionRef {
  id: string;
  name: string;
  messageCount: number;
  createdAt: string | null;
}

export interface SessionsTabProps {
  sessions: SessionRef[];
  projectId: string;
  onRefresh: () => void;
}

// ============================================================================
// Dialog Components
// ============================================================================

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

function Dialog({ isOpen, onClose, title, children }: DialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

interface CreateSessionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string) => void;
}

function CreateSessionDialog({
  isOpen,
  onClose,
  onSubmit,
}: CreateSessionDialogProps) {
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onSubmit(name.trim());
      setName("");
      onClose();
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Create New Session">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label
            htmlFor="session-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Session Name
          </label>
          <input
            id="session-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter session name"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim()}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </form>
    </Dialog>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function SessionsTab({
  sessions,
  projectId,
  onRefresh,
}: SessionsTabProps) {
  const navigate = useNavigate();
  const [showDialog, setShowDialog] = useState(false);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(
    new Set(),
  );

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  const handleCreateSession = async (name: string) => {
    // Step 1: Create the session in global storage first
    const createResponse = await authenticatedFetch("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
      onAuthFailure: handleAuthFailure,
    });

    if (!createResponse.ok) {
      console.error("Failed to create session:", createResponse.status);
      return;
    }

    const session = await createResponse.json();
    const sessionId = session.sessionId || session.id;

    // Step 2: Add the session to the project
    const addResponse = await authenticatedFetch(
      `/api/v1/projects/${projectId}/sessions?session_id=${sessionId}&session_name=${encodeURIComponent(name)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        onAuthFailure: handleAuthFailure,
      },
    );

    if (addResponse.ok) {
      onRefresh();
    }
  };

  const handleRemoveSession = async (
    sessionId: string,
    e: React.MouseEvent,
  ) => {
    e.stopPropagation(); // Prevent navigation
    const response = await authenticatedFetch(
      `/api/v1/projects/${projectId}/sessions/${sessionId}`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        onAuthFailure: handleAuthFailure,
      },
    );
    if (response.ok) {
      onRefresh();
    }
  };

  // Bulk selection handlers
  const handleSelectSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation
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

  const handleSelectAll = () => {
    if (selectedSessions.size === sessions.length) {
      setSelectedSessions(new Set());
    } else {
      setSelectedSessions(new Set(sessions.map((s) => s.id)));
    }
  };

  const handleClearSelection = () => {
    setSelectedSessions(new Set());
  };

  const handleBulkDelete = async () => {
    // Delete each selected session
    const deletePromises = Array.from(selectedSessions).map(
      async (sessionId) => {
        const response = await authenticatedFetch(
          `/api/v1/projects/${projectId}/sessions/${sessionId}`,
          {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            onAuthFailure: handleAuthFailure,
          },
        );
        return response.ok;
      },
    );
    await Promise.all(deletePromises);
    setSelectedSessions(new Set());
    onRefresh();
  };

  return (
    <div>
      <CreateSessionDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onSubmit={handleCreateSession}
      />
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Sessions
          </h2>
          {sessions.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={
                  selectedSessions.size === sessions.length &&
                  sessions.length > 0
                }
                onChange={handleSelectAll}
                aria-label="Select all sessions"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Select All
            </label>
          )}
        </div>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          New Session
        </button>
      </div>
      {sessions.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No sessions yet. Create your first session to start chatting.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-sm cursor-pointer"
              onClick={() => navigate(`/studio/chat?session=${session.id}`)}
            >
              <input
                type="checkbox"
                checked={selectedSessions.has(session.id)}
                onChange={() => {}}
                onClick={(e) => handleSelectSession(session.id, e)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {session.name}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {session.messageCount} messages
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  aria-label="Remove session"
                  onClick={(e) => handleRemoveSession(session.id, e)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <MessageSquare className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Bulk Action Bar */}
      <BulkActionBar
        selectedCount={selectedSessions.size}
        onClearSelection={handleClearSelection}
        onDelete={handleBulkDelete}
      />
    </div>
  );
}

export default SessionsTab;
