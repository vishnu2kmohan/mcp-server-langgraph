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

import { Button, Input, Checkbox } from "@/components/UI";

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
      <div
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Enter" && onClose()}
        role="button"
        tabIndex={0}
        aria-label="Close dialog"
      />
      <div className="relative bg-neutral-1 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5">
          <h3 className="text-lg font-medium text-neutral-12">{title}</h3>
          <Button
            size="icon"
            variant="ghost"
            className="p-1 text-neutral-10 hover:text-neutral-11"
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </Button>
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
            className="block text-sm font-medium text-neutral-11 mb-1"
          >
            Session Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
            id="session-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter session name"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            className="px-4 py-2 text-sm text-neutral-11 hover:bg-neutral-2 rounded-lg"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            className="px-4 py-2 text-sm bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
            type="submit"
            disabled={!name.trim()}
          >
            Create
          </Button>
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
          <h2 className="text-lg font-medium text-neutral-12">Sessions</h2>
          {sessions.length > 0 && (
            <Checkbox
              checked={
                selectedSessions.size === sessions.length && sessions.length > 0
              }
              onChange={handleSelectAll}
              label="Select All"
              size="sm"
            />
          )}
        </div>
        <Button
          variant="primary"
          className="flex px-3 py-1.5 bg-primary-10 text-neutral-12 text-sm rounded-lg hover:bg-primary-11"
          onClick={() => setShowDialog(true)}
        >
          <Plus className="w-4 h-4" />
          New Session
        </Button>
      </div>
      {sessions.length === 0 ? (
        <div className="text-center py-12 text-neutral-10">
          No sessions yet. Create your first session to start chatting.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center gap-3 p-4 bg-neutral-1 border border-neutral-5 rounded-lg hover:shadow-sm cursor-pointer"
              onClick={() => navigate(`/studio/chat?session=${session.id}`)}
            >
              <Checkbox
                checked={selectedSessions.has(session.id)}
                onChange={() => handleSelectSession(session.id)}
                onClick={(e) => e.stopPropagation()}
                size="sm"
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-neutral-12">
                  {session.name}
                </div>
                <div className="text-sm text-neutral-10">
                  {session.messageCount} messages
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  className="p-1.5 text-neutral-9 hover:text-error-9 hover:bg-error-1 dark:hover:bg-error-a3 rounded"
                  aria-label="Remove session"
                  onClick={(e) => handleRemoveSession(session.id, e)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                <MessageSquare className="w-5 h-5 text-neutral-9" />
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
