/**
 * ChatHeader Component
 *
 * Header for the chat interface with connection status,
 * session info, and action buttons.
 *
 * Extracted from ChatPage for improved modularity.
 */

import { Wifi, WifiOff, Radio, RefreshCw, Trash2 } from "lucide-react";
import { SaveAsWorkflowButton } from "./SaveAsWorkflowButton";
import { ExportButton } from "./ExportButton";
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";
import { InlineEdit } from "../UI/InlineEdit";

export type ConnectionMode = "websocket" | "rest" | "disconnected";

// =============================================================================
// ChatHeaderActions - Internal Component
// =============================================================================

interface ChatHeaderActionsProps {
  sessionId: string;
  sessionName?: string;
  onClear: () => void;
}

function ChatHeaderActions({
  sessionId,
  sessionName,
  onClear,
}: ChatHeaderActionsProps) {
  const enableSessionExport = useFeatureFlag("session_export");

  return (
    <div className="flex items-center gap-2">
      <SaveAsWorkflowButton sessionId={sessionId} />
      {enableSessionExport && (
        <ExportButton sessionId={sessionId} sessionTitle={sessionName} />
      )}
      <button
        onClick={onClear}
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
      >
        <Trash2 size={16} />
        Clear
      </button>
    </div>
  );
}

// =============================================================================
// ChatHeader
// =============================================================================

export interface ChatHeaderProps {
  connectionMode: ConnectionMode;
  isReconnecting: boolean;
  reconnectAttempts: number;
  sessionName?: string;
  messageCount: number;
  sessionId?: string;
  mcpError?: string;
  sessionError?: string;
  onConnect: () => void;
  onClear: () => void;
  onClearError?: () => void;
  /** Enable inline editing of session name */
  enableEdit?: boolean;
  /** Callback when session is renamed */
  onRenameSession?: (sessionId: string, name: string) => void;
}

export function ChatHeader({
  connectionMode,
  isReconnecting,
  reconnectAttempts,
  sessionName,
  messageCount,
  sessionId,
  mcpError,
  sessionError,
  onConnect,
  onClear,
  onClearError,
  enableEdit = false,
  onRenameSession,
}: ChatHeaderProps) {
  const messageLabel =
    messageCount === 1 ? "1 message" : `${messageCount} messages`;

  return (
    <>
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
                isReconnecting
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                  : connectionMode === "websocket"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : connectionMode === "rest"
                      ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400"
                      : "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400"
              }`}
            >
              {isReconnecting ? (
                <RefreshCw size={12} className="animate-spin" />
              ) : connectionMode === "websocket" ? (
                <Wifi size={12} />
              ) : connectionMode === "rest" ? (
                <Radio size={12} />
              ) : (
                <WifiOff size={12} />
              )}
              <span>
                {isReconnecting
                  ? `Reconnecting (${reconnectAttempts}/5)...`
                  : connectionMode === "websocket"
                    ? "Connected"
                    : connectionMode === "rest"
                      ? "REST"
                      : "Disconnected"}
              </span>
            </div>

            {/* Session Name */}
            {sessionName && (
              <div>
                {enableEdit && sessionId ? (
                  <InlineEdit
                    value={sessionName}
                    onSave={(newName) => {
                      if (onRenameSession && sessionId) {
                        onRenameSession(sessionId, newName);
                      }
                    }}
                    placeholder="Session name"
                    aria-label={`Rename session ${sessionName}`}
                    className="text-lg font-semibold text-gray-900 dark:text-gray-100"
                  />
                ) : (
                  <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {sessionName}
                  </h1>
                )}
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {messageLabel}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          {sessionId && (
            <ChatHeaderActions
              sessionId={sessionId}
              sessionName={sessionName}
              onClear={onClear}
            />
          )}
        </div>
      </header>

      {/* MCP Connection Error Banner */}
      {mcpError && (
        <div className="px-6 py-3 bg-orange-50 dark:bg-orange-900/20 border-b border-orange-200 dark:border-orange-800 flex items-center justify-between">
          <p className="text-orange-700 dark:text-orange-400 text-sm">
            {mcpError}
          </p>
          <button
            onClick={onConnect}
            className="text-orange-600 hover:text-orange-800 text-sm"
            aria-label="Retry connection"
          >
            Retry
          </button>
        </div>
      )}

      {/* Session Error Banner */}
      {sessionError && (
        <div className="px-6 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 flex items-center justify-between">
          <p className="text-red-700 dark:text-red-400 text-sm">
            {sessionError}
          </p>
          {onClearError && (
            <button
              onClick={onClearError}
              className="text-red-600 hover:text-red-800 text-sm"
              aria-label="Dismiss error"
            >
              Dismiss
            </button>
          )}
        </div>
      )}
    </>
  );
}
