/**
 * LLMStreamingTab Component
 *
 * Real-time LLM streaming observability panel for DevTools.
 * Displays Time To First Chunk (TTFC), inter-chunk latency,
 * and active stream status via WebSocket.
 */

import React, { useMemo } from "react";
import { useParams } from "react-router";
import {
  Activity,
  Clock,
  Layers,
  Wifi,
  WifiOff,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import {
  useLLMStreamingWebSocket,
  type ActiveStream,
} from "../../../hooks/useLLMStreamingWebSocket";

// =============================================================================
// Types
// =============================================================================

export interface LLMStreamingTabProps {
  className?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

function formatDuration(ms: number | undefined): string {
  if (ms === undefined) return "-";
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function getStatusIcon(status: ActiveStream["status"]): React.ReactNode {
  switch (status) {
    case "active":
      return (
        <Loader2
          className="w-4 h-4 text-blue-500 animate-spin"
          data-testid="stream-status-active"
        />
      );
    case "success":
      return (
        <CheckCircle2
          className="w-4 h-4 text-green-500"
          data-testid="stream-status-success"
        />
      );
    case "error":
      return (
        <XCircle
          className="w-4 h-4 text-red-500"
          data-testid="stream-status-error"
        />
      );
    case "cancelled":
      return (
        <AlertCircle
          className="w-4 h-4 text-yellow-500"
          data-testid="stream-status-cancelled"
        />
      );
  }
}

function getStatusColor(status: ActiveStream["status"]): string {
  switch (status) {
    case "active":
      return "border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950";
    case "success":
      return "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950";
    case "error":
      return "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950";
    case "cancelled":
      return "border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-950";
  }
}

// =============================================================================
// Subcomponents
// =============================================================================

interface ConnectionStatusProps {
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  error: string | null;
  onReconnect: () => void;
}

function ConnectionStatus({
  status,
  error,
  onReconnect,
}: ConnectionStatusProps): React.ReactElement {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-md text-sm">
      {status === "connected" && (
        <>
          <Wifi className="w-4 h-4 text-green-500" />
          <span className="text-green-700 dark:text-green-400">Connected</span>
        </>
      )}
      {status === "connecting" && (
        <>
          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          <span className="text-blue-700 dark:text-blue-400">
            Connecting...
          </span>
        </>
      )}
      {status === "reconnecting" && (
        <>
          <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />
          <span className="text-yellow-700 dark:text-yellow-400">
            Reconnecting...
          </span>
        </>
      )}
      {status === "disconnected" && (
        <>
          <WifiOff className="w-4 h-4 text-gray-500" />
          <span className="text-gray-600 dark:text-gray-400">Disconnected</span>
          <button
            onClick={onReconnect}
            className="ml-2 px-2 py-0.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          >
            Reconnect
          </button>
        </>
      )}
      {status === "error" && (
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-red-700 dark:text-red-400">Error</span>
          </div>
          {error && (
            <span className="text-xs text-red-600 dark:text-red-400 mt-1">
              {error}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface StreamCardProps {
  stream: ActiveStream;
}

function StreamCard({ stream }: StreamCardProps): React.ReactElement {
  return (
    <div
      className={cn(
        "border rounded-lg p-3 transition-colors",
        getStatusColor(stream.status),
      )}
      data-testid="stream-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon(stream.status)}
          <span className="font-medium text-gray-900 dark:text-white">
            {stream.model}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">
            {stream.provider}
          </span>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
          {stream.stream_id.slice(0, 8)}...
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* TTFC */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-gray-900 rounded">
          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-1">
            <Clock className="w-3 h-3" />
            <span>TTFC</span>
          </div>
          <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
            {formatDuration(stream.ttfc_ms)}
          </span>
        </div>

        {/* Chunks */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-gray-900 rounded">
          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-1">
            <Layers className="w-3 h-3" />
            <span>Chunks</span>
          </div>
          <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
            {stream.chunks_received}
          </span>
        </div>

        {/* Size */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-gray-900 rounded">
          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-1">
            <Activity className="w-3 h-3" />
            <span>Size</span>
          </div>
          <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
            {stream.total_chunk_size} B
          </span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function LLMStreamingTab({
  className,
}: LLMStreamingTabProps): React.ReactElement {
  const { sessionId: routeSessionId } = useParams<{ sessionId: string }>();

  const { status, activeStreams, sessionId, error, reconnect } =
    useLLMStreamingWebSocket({
      sessionId: routeSessionId,
    });

  // Convert Map to array for rendering
  const streamsList = useMemo(() => {
    return Array.from(activeStreams.values()).sort((a, b) => {
      // Active streams first, then by start time
      if (a.status === "active" && b.status !== "active") return -1;
      if (a.status !== "active" && b.status === "active") return 1;
      /* eslint-disable no-restricted-syntax -- TODO: ADR-0091 Phase 6: Transform ActiveStream to camelCase */
      return (
        new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
      );
      /* eslint-enable no-restricted-syntax */
    });
  }, [activeStreams]);

  return (
    <div
      className={cn("flex flex-col h-full", className)}
      data-testid="llm-streaming-tab"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">
            LLM Streaming
          </h3>
          {sessionId && (
            <span className="text-xs text-gray-500 dark:text-gray-400 px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
              {sessionId}
            </span>
          )}
        </div>
        <ConnectionStatus
          status={status}
          error={error}
          onReconnect={reconnect}
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {streamsList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <Activity className="w-12 h-12 mb-3 opacity-50" />
            <p className="text-sm">No active streams</p>
            <p className="text-xs mt-1">
              Streams will appear here when LLM requests are made
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {streamsList.map((stream) => (
              <StreamCard key={stream.stream_id} stream={stream} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default LLMStreamingTab;
