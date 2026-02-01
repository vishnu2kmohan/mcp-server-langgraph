/**
 * ConnectionStatus Component
 *
 * Persistent status indicator showing connection state.
 * Features:
 * - Connection state (connected/connecting/disconnected/reconnecting)
 * - API latency display with color coding
 * - Last sync time display
 * - Click to reconnect
 * - Compact mode with tooltip
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { useState, useCallback, useMemo } from "react";
import { Wifi, WifiOff, RefreshCw, Clock } from "lucide-react";

import { Button } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export type ConnectionState =
  | "connected"
  | "connecting"
  | "disconnected"
  | "reconnecting";

export interface ConnectionStatusProps {
  /** Current connection state */
  status: ConnectionState;
  /** API latency in milliseconds */
  latencyMs?: number;
  /** Last sync timestamp */
  lastSyncAt?: number;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when user clicks reconnect */
  onReconnect?: () => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const LATENCY_THRESHOLDS = {
  good: 100,
  moderate: 200,
};

const STATUS_CONFIG: Record<
  ConnectionState,
  { label: string; color: string; icon: typeof Wifi; pulse?: boolean }
> = {
  connected: {
    label: "Connected",
    color: "bg-success-9",
    icon: Wifi,
  },
  connecting: {
    label: "Connecting",
    color: "bg-warning-9",
    icon: Wifi,
    pulse: true,
  },
  disconnected: {
    label: "Disconnected",
    color: "bg-error-9",
    icon: WifiOff,
  },
  reconnecting: {
    label: "Reconnecting",
    color: "bg-warning-9",
    icon: RefreshCw,
    pulse: true,
  },
};

// ==============================================================================
// Component
// ==============================================================================

export function ConnectionStatus({
  status,
  latencyMs,
  lastSyncAt,
  compact = false,
  className = "",
  onReconnect,
}: ConnectionStatusProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const config = STATUS_CONFIG[status];

  // Format latency with color
  const latencyInfo = useMemo(() => {
    if (latencyMs === undefined) return null;

    let colorClass = "text-success-10 dark:text-success-7";
    if (latencyMs > LATENCY_THRESHOLDS.moderate) {
      colorClass = "text-error-10 dark:text-error-7";
    } else if (latencyMs > LATENCY_THRESHOLDS.good) {
      colorClass = "text-warning-9 dark:text-warning-9";
    }

    return { value: `${latencyMs}ms`, colorClass };
  }, [latencyMs]);

  // Format last sync time
  const syncTimeDisplay = useMemo(() => {
    if (!lastSyncAt) return null;

    const diff = Date.now() - lastSyncAt;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (seconds < 30) return "just now";
    if (minutes < 1) return `${seconds}s ago`;
    if (hours < 1) return `${minutes}m ago`;
    return `${hours}h ago`;
  }, [lastSyncAt]);

  const handleMouseEnter = useCallback(() => {
    if (compact) {
      setShowTooltip(true);
    }
  }, [compact]);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  const handleReconnect = useCallback(() => {
    if (onReconnect && status === "disconnected") {
      onReconnect();
    }
  }, [onReconnect, status]);

  const ariaLabel = useMemo(() => {
    let label = `Connection status: ${config.label}`;
    if (latencyMs !== undefined) {
      label += `, latency ${latencyMs}ms`;
    }
    if (syncTimeDisplay) {
      label += `, synced ${syncTimeDisplay}`;
    }
    return label;
  }, [config.label, latencyMs, syncTimeDisplay]);

  const Icon = config.icon;

  return (
    <div
      data-testid="connection-status"
      data-compact={compact ? "true" : undefined}
      aria-label={ariaLabel}
      className={`relative inline-flex items-center gap-2 ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <span
          data-testid="status-indicator"
          className={`inline-block h-2 w-2 rounded-full ${config.color} ${
            config.pulse ? "animate-pulse" : ""
          }`}
        />

        {!compact && (
          <>
            <Icon size={14} className="text-neutral-10" />
            <span
              role="status"
              aria-live="polite"
              className="text-sm text-neutral-11"
            >
              {config.label}
            </span>
          </>
        )}
      </div>
      {/* Latency display */}
      {!compact && latencyInfo && (
        <span className={`text-xs font-mono ${latencyInfo.colorClass}`}>
          {latencyInfo.value}
        </span>
      )}
      {/* Last sync time */}
      {!compact && syncTimeDisplay && (
        <span className="flex items-center gap-1 text-xs text-neutral-10">
          <Clock size={12} aria-hidden="true" />
          <span>Synced {syncTimeDisplay}</span>
        </span>
      )}
      {/* Reconnect button */}
      {status === "disconnected" && onReconnect && (
        <Button
          variant="primary"
          size="sm"
          className="ml-2 px-2 py-1 text-xs text-primary-10 dark:text-primary-7 bg-primary-1 dark:bg-primary-a3 rounded hover:bg-primary-3 dark:hover:bg-primary-a5 focus:ring-primary-7"
          type="button"
          onClick={handleReconnect}
        >
          Reconnect
        </Button>
      )}
      {/* Tooltip for compact mode */}
      {compact && showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-neutral-2 text-neutral-12 text-xs rounded shadow-lg whitespace-nowrap z-50"
        >
          <div className="flex items-center gap-2">
            <span>{config.label}</span>
            {latencyInfo && (
              <span className={latencyInfo.colorClass}>
                {latencyInfo.value}
              </span>
            )}
          </div>
          {syncTimeDisplay && (
            <div className="mt-1 text-neutral-9">Synced {syncTimeDisplay}</div>
          )}
          {/* Tooltip arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-12 dark:border-t-neutral-11" />
        </div>
      )}
    </div>
  );
}

export default ConnectionStatus;
