/**
 * ConnectionHealthDashboard
 *
 * Real-time connection health monitoring dashboard using WebSocket.
 * Displays:
 * - Health summary with status counts
 * - Live connection status updates
 * - Individual connection health checks
 * - WebSocket connection status
 */

import { useMemo } from "react";
import {
  RefreshCw,
  Wifi,
  WifiOff,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Server,
  Activity,
  Zap,
} from "lucide-react";
import { useConnectionHealthWebSocket } from "../../hooks/useConnectionHealthWebSocket";
import type { ConnectionHealth } from "../../hooks/useConnectionHealthWebSocket";

import { Button } from "@/components/UI";

// Status colors for badges
const statusColors: Record<string, string> = {
  connected:
    "bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-5",
  disconnected: "bg-neutral-2 text-neutral-12",
  connecting:
    "bg-primary-3 text-primary-11 dark:bg-primary-12 dark:text-primary-5",
  error: "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-9",
  auth_required:
    "bg-warning-3 text-warning-11 dark:bg-warning-12 dark:text-warning-6",
};

// Status icons
const statusIcons: Record<string, React.ReactNode> = {
  connected: <CheckCircle className="w-4 h-4 text-success-9" />,
  disconnected: <XCircle className="w-4 h-4 text-neutral-9" />,
  connecting: <Loader2 className="w-4 h-4 text-primary-9 animate-spin" />,
  error: <AlertCircle className="w-4 h-4 text-error-9" />,
  auth_required: <AlertCircle className="w-4 h-4 text-warning-9" />,
};

interface ConnectionHealthDashboardProps {
  compact?: boolean;
}

export function ConnectionHealthDashboard({
  compact = false,
}: ConnectionHealthDashboardProps) {
  const {
    status,
    connections,
    error,
    lastPong,
    summary,
    reconnect,
    refresh,
    checkHealth,
  } = useConnectionHealthWebSocket();

  // Derive isConnected from status for backwards compatibility
  const isConnected = status === "connected";

  // Format last heartbeat time
  const lastHeartbeatText = useMemo(() => {
    if (!lastPong) return "Never";
    // lastPong is now a string timestamp from useConnectionHealthWebSocket
    const pongDate = new Date(lastPong);
    const seconds = Math.floor((Date.now() - pongDate.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ago`;
  }, [lastPong]);

  return (
    <div className="bg-neutral-1 rounded-lg border p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-10" />
          <h2 className="text-lg font-semibold text-neutral-12">
            Connection Health
          </h2>
        </div>

        <div className="flex items-center gap-3">
          {/* WebSocket Status */}
          <div
            className="flex items-center gap-2 text-sm"
            data-testid="ws-status"
          >
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-success-9" />
                <span className="text-success-10 dark:text-success-7">
                  Connected
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-error-9" />
                <span className="text-error-10 dark:text-error-7">
                  Disconnected
                </span>
              </>
            )}
          </div>

          {/* Reconnect or Refresh Button */}
          {isConnected ? (
            <Button
              size="icon"
              variant="secondary"
              className="p-2 text-neutral-11 hover:bg-neutral-2 rounded-md"
              onClick={refresh}
              aria-label="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              className="px-3 py-1 text-sm bg-primary-10 text-neutral-12 rounded-md hover:bg-primary-11"
              onClick={reconnect}
              aria-label="Reconnect"
            >
              Reconnect
            </Button>
          )}
        </div>
      </div>
      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-md">
          <p className="text-sm text-error-10 dark:text-error-7">{error}</p>
        </div>
      )}
      {/* Health Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
        <div className="bg-neutral-1 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-neutral-12">
            {summary.total}
          </div>
          <div className="text-sm text-neutral-10">Total</div>
        </div>

        <div
          data-testid="summary-connected"
          className="bg-success-1 dark:bg-success-a3 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-success-10 dark:text-success-7">
            {summary.connected}
          </div>
          <div className="text-sm text-neutral-10">Connected</div>
        </div>

        <div
          data-testid="summary-disconnected"
          className="bg-neutral-2 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-neutral-11">
            {summary.disconnected}
          </div>
          <div className="text-sm text-neutral-10">Disconnected</div>
        </div>

        <div
          data-testid="summary-error"
          className="bg-error-1 dark:bg-error-a3 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-error-10 dark:text-error-7">
            {summary.error}
          </div>
          <div className="text-sm text-neutral-10">Error</div>
        </div>

        <div
          data-testid="summary-auth-required"
          className="bg-warning-3 bg-warning-3 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-warning-9 dark:text-warning-9">
            {summary.authRequired}
          </div>
          <div className="text-sm text-neutral-10">Auth Required</div>
        </div>
      </div>
      {/* Last Heartbeat */}
      {isConnected && (
        <div className="text-xs text-neutral-9 mb-4">
          Last heartbeat: {lastHeartbeatText}
        </div>
      )}
      {/* Connection List */}
      {connections.length === 0 ? (
        <div className="text-center py-8">
          <Server className="w-12 h-12 text-neutral-9 mx-auto mb-3" />
          <p className="text-neutral-10">No connections configured</p>
        </div>
      ) : (
        <div
          className={`space-y-2 ${compact ? "max-h-64 overflow-y-auto" : ""}`}
        >
          {connections.map((conn) => (
            <ConnectionHealthItem
              key={conn.id}
              connection={conn}
              onCheckHealth={checkHealth}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ConnectionHealthItemProps {
  connection: ConnectionHealth;
  onCheckHealth: (id: string) => void;
}

function ConnectionHealthItem({
  connection,
  onCheckHealth,
}: ConnectionHealthItemProps) {
  const statusIcon = statusIcons[connection.status] || statusIcons.disconnected;
  const statusColor =
    statusColors[connection.status] || statusColors.disconnected;

  return (
    <div className="flex items-center justify-between p-3 bg-neutral-1 rounded-lg">
      <div className="flex items-center gap-3 min-w-0">
        {/* Status Indicator */}
        <div data-testid={`status-indicator-${connection.id}`}>
          {statusIcon}
        </div>

        {/* Connection Info */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-neutral-12 truncate">
              {connection.name}
            </span>
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColor}`}
            >
              {connection.status}
            </span>
          </div>

          {/* Stats for connected */}
          {connection.status === "connected" && (
            <div className="text-xs text-neutral-10 mt-0.5">
              {connection.toolCount} tools · {connection.resourceCount}{" "}
              resources · {connection.promptCount} prompts
            </div>
          )}

          {/* Error message */}
          {connection.lastError && (
            <div className="text-xs text-error-9 dark:text-error-7 mt-0.5">
              {connection.lastError}
            </div>
          )}
        </div>
      </div>
      {/* Actions */}
      <Button
        variant="primary"
        className="p-2 text-primary-10 hover:bg-primary-1 dark:hover:bg-primary-a6 rounded-md flex-shrink-0"
        onClick={() => onCheckHealth(connection.id)}
        aria-label="Check health"
      >
        <Zap className="w-4 h-4" />
      </Button>
    </div>
  );
}
