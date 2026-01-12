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
    "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-300",
  disconnected:
    "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300",
  connecting:
    "bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-300",
  error: "bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-300",
  auth_required:
    "bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-300",
};

// Status icons
const statusIcons: Record<string, React.ReactNode> = {
  connected: <CheckCircle className="w-4 h-4 text-success-500" />,
  disconnected: (
    <XCircle className="w-4 h-4 text-neutral-400 dark:text-neutral-400" />
  ),
  connecting: <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />,
  error: <AlertCircle className="w-4 h-4 text-error-500" />,
  auth_required: <AlertCircle className="w-4 h-4 text-warning-500" />,
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
    <div className="bg-white dark:bg-neutral-800 rounded-lg border dark:border-neutral-700 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
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
                <Wifi className="w-4 h-4 text-success-500" />
                <span className="text-success-600 dark:text-success-400">
                  Connected
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-error-500" />
                <span className="text-error-600 dark:text-error-400">
                  Disconnected
                </span>
              </>
            )}
          </div>

          {/* Reconnect or Refresh Button */}
          {isConnected ? (
            <Button
              variant="secondary"
              className="p-2 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700 rounded-md"
              onClick={refresh}
              aria-label="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              className="px-3 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700"
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
        <div className="mb-4 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-md">
          <p className="text-sm text-error-600 dark:text-error-400">{error}</p>
        </div>
      )}
      {/* Health Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
        <div className="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-neutral-900 dark:text-white">
            {summary.total}
          </div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Total
          </div>
        </div>

        <div
          data-testid="summary-connected"
          className="bg-success-50 dark:bg-success-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-success-600 dark:text-success-400">
            {summary.connected}
          </div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Connected
          </div>
        </div>

        <div
          data-testid="summary-disconnected"
          className="bg-neutral-100 dark:bg-neutral-700/50 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-neutral-600 dark:text-neutral-400">
            {summary.disconnected}
          </div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Disconnected
          </div>
        </div>

        <div
          data-testid="summary-error"
          className="bg-error-50 dark:bg-error-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-error-600 dark:text-error-400">
            {summary.error}
          </div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Error
          </div>
        </div>

        <div
          data-testid="summary-auth-required"
          className="bg-warning-50 dark:bg-warning-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-warning-600 dark:text-warning-400">
            {summary.authRequired}
          </div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            Auth Required
          </div>
        </div>
      </div>
      {/* Last Heartbeat */}
      {isConnected && (
        <div className="text-xs text-neutral-400 dark:text-neutral-400 mb-4">
          Last heartbeat: {lastHeartbeatText}
        </div>
      )}
      {/* Connection List */}
      {connections.length === 0 ? (
        <div className="text-center py-8">
          <Server className="w-12 h-12 text-neutral-300 dark:text-neutral-600 dark:text-neutral-300 mx-auto mb-3" />
          <p className="text-neutral-500 dark:text-neutral-400">
            No connections configured
          </p>
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
    <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg">
      <div className="flex items-center gap-3 min-w-0">
        {/* Status Indicator */}
        <div data-testid={`status-indicator-${connection.id}`}>
          {statusIcon}
        </div>

        {/* Connection Info */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-neutral-900 dark:text-white truncate">
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
            <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              {connection.toolCount} tools · {connection.resourceCount}{" "}
              resources · {connection.promptCount} prompts
            </div>
          )}

          {/* Error message */}
          {connection.lastError && (
            <div className="text-xs text-error-500 dark:text-error-400 mt-0.5">
              {connection.lastError}
            </div>
          )}
        </div>
      </div>
      {/* Actions */}
      <Button
        variant="primary"
        className="p-2 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/50 rounded-md flex-shrink-0"
        onClick={() => onCheckHealth(connection.id)}
        aria-label="Check health"
      >
        <Zap className="w-4 h-4" />
      </Button>
    </div>
  );
}
