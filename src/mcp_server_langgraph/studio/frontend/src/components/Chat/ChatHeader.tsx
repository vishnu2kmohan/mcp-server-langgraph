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

import { Button } from "@/components/UI";

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
      <Button
        variant="danger"
        className="flex px-3 py-1.5 text-sm text-error-10 hover:bg-error-1 dark:hover:bg-error-a3 rounded"
        onClick={onClear}
      >
        <Trash2 size={16} />
        Clear
      </Button>
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
      <header className="px-6 py-4 bg-neutral-1 border-b border-neutral-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
                isReconnecting
                  ? "bg-primary-3 text-primary-11 dark:bg-primary-a3 dark:text-primary-11"
                  : connectionMode === "websocket"
                    ? "bg-success-3 text-success-11 dark:bg-success-a3 dark:text-success-11"
                    : connectionMode === "rest"
                      ? "bg-warning-3 text-warning-10 bg-warning-3 dark:text-warning-9"
                      : "bg-error-3 text-error-11 dark:bg-error-a3 dark:text-error-11"
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
                    className="text-lg font-semibold text-neutral-12"
                  />
                ) : (
                  <h1 className="text-lg font-semibold text-neutral-12">
                    {sessionName}
                  </h1>
                )}
                <p className="text-sm text-neutral-10">
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
        <div className="px-6 py-3 bg-grafana-1 dark:bg-grafana-12/20 border-b border-grafana-3 dark:border-grafana-11 flex items-center justify-between">
          <p className="text-grafana-11 dark:text-grafana-11 text-sm">
            {mcpError}
          </p>
          <Button variant="primary"
            className="text-grafana-10 hover:text-grafana-11 text-sm"
            onClick={onConnect}
            aria-label="Retry connection"
          >Retry</Button>
        </div>
      )}
      {/* Session Error Banner */}
      {sessionError && (
        <div className="px-6 py-3 bg-error-1 dark:bg-error-a3 border-b border-error-4 dark:border-error-11 flex items-center justify-between">
          <p className="text-error-11 dark:text-error-11 text-sm">
            {sessionError}
          </p>
          {onClearError && (
            <Button variant="secondary"
              className="text-error-10 hover:text-error-11 text-sm"
              onClick={onClearError}
              aria-label="Dismiss error"
            >Dismiss</Button>
          )}
        </div>
      )}
    </>
  );
}
