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
import {
  STATUS_TEXT_COLORS,
  STREAM_STATUS_STYLES,
} from "../utils/devToolsColors";

import { Button } from "@/components/UI";

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
          className={cn("w-4 h-4 animate-spin", STATUS_TEXT_COLORS.info)}
          data-testid="stream-status-active"
        />
      );
    case "success":
      return (
        <CheckCircle2
          className={cn("w-4 h-4", STATUS_TEXT_COLORS.success)}
          data-testid="stream-status-success"
        />
      );
    case "error":
      return (
        <XCircle
          className={cn("w-4 h-4", STATUS_TEXT_COLORS.error)}
          data-testid="stream-status-error"
        />
      );
    case "cancelled":
      return (
        <AlertCircle
          className={cn("w-4 h-4", STATUS_TEXT_COLORS.warning)}
          data-testid="stream-status-cancelled"
        />
      );
  }
}

function getStatusColor(status: ActiveStream["status"]): string {
  // Use semantic stream status styles from design system
  return STREAM_STATUS_STYLES[status];
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
    <div className="flex items-center gap-2 px-3 py-1.5 bg-neutral-100 dark:bg-neutral-800 rounded-md text-sm">
      {status === "connected" && (
        <>
          <Wifi className={cn("w-4 h-4", STATUS_TEXT_COLORS.success)} />
          <span className={STATUS_TEXT_COLORS.success}>Connected</span>
        </>
      )}
      {status === "connecting" && (
        <>
          <Loader2
            className={cn("w-4 h-4 animate-spin", STATUS_TEXT_COLORS.info)}
          />
          <span className={STATUS_TEXT_COLORS.info}>Connecting...</span>
        </>
      )}
      {status === "reconnecting" && (
        <>
          <RefreshCw
            className={cn("w-4 h-4 animate-spin", STATUS_TEXT_COLORS.warning)}
          />
          <span className={STATUS_TEXT_COLORS.warning}>Reconnecting...</span>
        </>
      )}
      {status === "disconnected" && (
        <>
          <WifiOff className={cn("w-4 h-4", STATUS_TEXT_COLORS.neutral)} />
          <span className={STATUS_TEXT_COLORS.neutral}>Disconnected</span>
          <Button
            variant="primary"
            size="sm"
            className="ml-2 px-2 py-0.5 text-xs bg-primary-500 text-white rounded hover:bg-primary-600"
            onClick={onReconnect}
          >
            Reconnect
          </Button>
        </>
      )}
      {status === "error" && (
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <AlertCircle className={cn("w-4 h-4", STATUS_TEXT_COLORS.error)} />
            <span className={STATUS_TEXT_COLORS.error}>Error</span>
          </div>
          {error && (
            <span className={cn("text-xs mt-1", STATUS_TEXT_COLORS.error)}>
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
          <span className="font-medium text-neutral-900 dark:text-white">
            {stream.model}
          </span>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 px-1.5 py-0.5 bg-neutral-200 dark:bg-neutral-700 rounded">
            {stream.provider}
          </span>
        </div>
        <span className="text-xs text-neutral-500 dark:text-neutral-400 font-mono">
          {stream.streamId.slice(0, 8)}...
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* TTFC */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-neutral-900 rounded">
          <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            <Clock className="w-3 h-3" />
            <span>TTFC</span>
          </div>
          <span className="font-mono text-sm font-medium text-neutral-900 dark:text-white">
            {formatDuration(stream.ttfcMs)}
          </span>
        </div>

        {/* Chunks */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-neutral-900 rounded">
          <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            <Layers className="w-3 h-3" />
            <span>Chunks</span>
          </div>
          <span className="font-mono text-sm font-medium text-neutral-900 dark:text-white">
            {stream.chunksReceived}
          </span>
        </div>

        {/* Size */}
        <div className="flex flex-col items-center p-2 bg-white dark:bg-neutral-900 rounded">
          <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            <Activity className="w-3 h-3" />
            <span>Size</span>
          </div>
          <span className="font-mono text-sm font-medium text-neutral-900 dark:text-white">
            {stream.totalChunkSize} B
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
      return new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime();
    });
  }, [activeStreams]);

  return (
    <div
      className={cn("flex flex-col h-full", className)}
      data-testid="llm-streaming-tab"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-neutral-900 dark:text-white">
            LLM Streaming
          </h3>
          {sessionId && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400 px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded">
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
          <div className="flex flex-col items-center justify-center h-full text-neutral-500 dark:text-neutral-400">
            <Activity className="w-12 h-12 mb-3 opacity-50" />
            <p className="text-sm">No active streams</p>
            <p className="text-xs mt-1">
              Streams will appear here when LLM requests are made
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {streamsList.map((stream) => (
              <StreamCard key={stream.streamId} stream={stream} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default LLMStreamingTab;
