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

// Status colors for badges
const statusColors: Record<string, string> = {
  connected:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  disconnected: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  connecting: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  auth_required:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
};

// Status icons
const statusIcons: Record<string, React.ReactNode> = {
  connected: <CheckCircle className="w-4 h-4 text-green-500" />,
  disconnected: <XCircle className="w-4 h-4 text-gray-400" />,
  connecting: <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />,
  error: <AlertCircle className="w-4 h-4 text-red-500" />,
  auth_required: <AlertCircle className="w-4 h-4 text-yellow-500" />,
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
    <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
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
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-green-600 dark:text-green-400">
                  Connected
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-red-600 dark:text-red-400">
                  Disconnected
                </span>
              </>
            )}
          </div>

          {/* Reconnect or Refresh Button */}
          {isConnected ? (
            <button
              onClick={refresh}
              className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-md"
              aria-label="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={reconnect}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
              aria-label="Reconnect"
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Health Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {summary.total}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Total</div>
        </div>

        <div
          data-testid="summary-connected"
          className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {summary.connected}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Connected
          </div>
        </div>

        <div
          data-testid="summary-disconnected"
          className="bg-gray-100 dark:bg-gray-700/50 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
            {summary.disconnected}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Disconnected
          </div>
        </div>

        <div
          data-testid="summary-error"
          className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {summary.error}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Error</div>
        </div>

        <div
          data-testid="summary-auth-required"
          className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 text-center"
        >
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
            {summary.authRequired}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Auth Required
          </div>
        </div>
      </div>

      {/* Last Heartbeat */}
      {isConnected && (
        <div className="text-xs text-gray-400 dark:text-gray-500 mb-4">
          Last heartbeat: {lastHeartbeatText}
        </div>
      )}

      {/* Connection List */}
      {connections.length === 0 ? (
        <div className="text-center py-8">
          <Server className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
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
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="flex items-center gap-3 min-w-0">
        {/* Status Indicator */}
        <div data-testid={`status-indicator-${connection.id}`}>
          {statusIcon}
        </div>

        {/* Connection Info */}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-white truncate">
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
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {connection.toolCount} tools · {connection.resourceCount}{" "}
              resources · {connection.promptCount} prompts
            </div>
          )}

          {/* Error message */}
          {connection.lastError && (
            <div className="text-xs text-red-500 dark:text-red-400 mt-0.5">
              {connection.lastError}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <button
        onClick={() => onCheckHealth(connection.id)}
        className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/50 rounded-md flex-shrink-0"
        aria-label="Check health"
      >
        <Zap className="w-4 h-4" />
      </button>
    </div>
  );
}
