/**
 * HumanTimestamp Component
 *
 * Displays timestamps in human-friendly formats with relative time as default.
 *
 * Features:
 * - Relative time display ("5m ago", "2h ago") as default
 * - Auto-updates every 30 seconds for freshness
 * - Full absolute timestamp in tooltip
 * - Multiple format options: relative, time, datetime, both
 */

import * as React from "react";
import { cn } from "../../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type HumanTimestampFormat = "relative" | "time" | "datetime" | "both";

export interface HumanTimestampProps {
  /** Timestamp value (epoch ms or ISO string) */
  timestamp: number | string;
  /** Display format */
  format?: HumanTimestampFormat;
  /** Show UTC timestamp on hover (default: true) */
  showUtcOnHover?: boolean;
  /** Additional CSS class */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Auto-update interval in ms (30 seconds) */
const UPDATE_INTERVAL = 30000;

/** Time thresholds in milliseconds */
const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse timestamp to Date object
 */
function toDate(value: number | string): Date | null {
  if (typeof value === "number") return new Date(value);
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : new Date(parsed);
}

/**
 * Format relative time (e.g., "5m ago", "2h ago")
 */
function formatRelativeTime(date: Date, now: Date): string {
  const diff = now.getTime() - date.getTime();

  // Future timestamps
  if (diff < 0) {
    const absDiff = Math.abs(diff);
    if (absDiff < MINUTE) return "in <1m";
    if (absDiff < HOUR) return `in ${Math.floor(absDiff / MINUTE)}m`;
    if (absDiff < DAY) return `in ${Math.floor(absDiff / HOUR)}h`;
    return `in ${Math.floor(absDiff / DAY)}d`;
  }

  // Past timestamps
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)}m ago`;
  if (diff < DAY) return `${Math.floor(diff / HOUR)}h ago`;
  if (diff < WEEK) return `${Math.floor(diff / DAY)}d ago`;

  // More than a week - show date
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

/**
 * Format absolute time (e.g., "12:34:56.789")
 */
function formatAbsoluteTime(date: Date): string {
  return date.toLocaleTimeString(undefined, {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
}

/**
 * Format full datetime (e.g., "Jan 15, 2026 2:34:56 PM UTC")
 */
function formatDateTime(date: Date): string {
  return date.toLocaleString(undefined, {
    hour12: false,
    timeZoneName: "short",
  });
}

// =============================================================================
// Component
// =============================================================================

/**
 * HumanTimestamp Component
 *
 * @example
 * ```tsx
 * // Relative time (default)
 * <HumanTimestamp timestamp={Date.now() - 300000} />
 * // Shows: "5m ago"
 *
 * // Explicit format
 * <HumanTimestamp timestamp={Date.now()} format="time" />
 * // Shows: "14:30:00.000"
 * ```
 */
export function HumanTimestamp({
  timestamp,
  format = "relative",
  showUtcOnHover = true,
  className,
}: HumanTimestampProps): React.ReactElement | null {
  // State for forcing re-renders on interval
  const [, setTick] = React.useState(0);

  // Parse the timestamp
  const date = React.useMemo(() => toDate(timestamp), [timestamp]);

  // Set up auto-update interval for relative formats
  React.useEffect(() => {
    // Only update for relative or both formats
    if (format !== "relative" && format !== "both") return;

    const intervalId = setInterval(() => {
      setTick((t) => t + 1);
    }, UPDATE_INTERVAL);

    return () => clearInterval(intervalId);
  }, [format]);

  // Return null for invalid dates
  if (!date) return null;

  // Calculate display text based on format
  const now = new Date();
  let text: string;

  switch (format) {
    case "relative":
      text = formatRelativeTime(date, now);
      break;
    case "time":
      text = formatAbsoluteTime(date);
      break;
    case "datetime":
      text = formatDateTime(date);
      break;
    case "both":
      text = `${formatRelativeTime(date, now)} (${formatAbsoluteTime(date)})`;
      break;
    default:
      text = formatRelativeTime(date, now);
  }

  // Tooltip shows full ISO string
  const title = showUtcOnHover ? date.toISOString() : undefined;

  return (
    <span
      className={cn("font-mono text-xs text-neutral-10", className)}
      title={title}
      data-testid="human-timestamp"
    >
      {text}
    </span>
  );
}

export default HumanTimestamp;
