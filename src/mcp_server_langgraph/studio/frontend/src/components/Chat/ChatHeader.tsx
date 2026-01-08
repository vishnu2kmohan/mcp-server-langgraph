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
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-error-600 hover:bg-error-50 dark:hover:bg-error-900/20 rounded"
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
                  ? "bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400"
                  : connectionMode === "websocket"
                    ? "bg-success-100 text-success-700 dark:bg-success-900/20 dark:text-success-400"
                    : connectionMode === "rest"
                      ? "bg-warning-100 text-warning-700 dark:bg-warning-900/20 dark:text-warning-400"
                      : "bg-error-100 text-error-700 dark:bg-error-900/20 dark:text-error-400"
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
        <div className="px-6 py-3 bg-grafana-50 dark:bg-grafana-900/20 border-b border-grafana-200 dark:border-grafana-800 flex items-center justify-between">
          <p className="text-grafana-700 dark:text-grafana-400 text-sm">
            {mcpError}
          </p>
          <button
            onClick={onConnect}
            className="text-grafana-600 hover:text-grafana-800 text-sm"
            aria-label="Retry connection"
          >
            Retry
          </button>
        </div>
      )}

      {/* Session Error Banner */}
      {sessionError && (
        <div className="px-6 py-3 bg-error-50 dark:bg-error-900/20 border-b border-error-200 dark:border-error-800 flex items-center justify-between">
          <p className="text-error-700 dark:text-error-400 text-sm">
            {sessionError}
          </p>
          {onClearError && (
            <button
              onClick={onClearError}
              className="text-error-600 hover:text-error-800 text-sm"
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
