/**
 * SmartValue Component
 *
 * Human-friendly value formatting for OTEL data visualization.
 * Auto-detects type and renders appropriately.
 *
 * Features:
 * - Relative timestamps ("5m ago")
 * - Formatted durations ("234ms", "1.2s")
 * - Human-readable bytes ("1.5 KB", "2.3 MB")
 * - Locale-formatted numbers ("1,234,567")
 * - Truncated IDs with tooltip ("abc123...def456")
 * - JSON object summaries
 * - Click-to-copy support
 */

import { useState, useCallback, type HTMLAttributes } from "react";
import { Copy, Check } from "lucide-react";

import { cn } from "../../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type SmartValueType =
  | "auto"
  | "timestamp"
  | "duration"
  | "bytes"
  | "number"
  | "id"
  | "json";

export interface SmartValueProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  /** The value to format */
  value: unknown;
  /** Type hint for formatting (default: auto-detect) */
  type?: SmartValueType;
  /** Character limit for ID/string truncation (default: 16) */
  truncateAt?: number;
  /** Enable click-to-copy functionality */
  copyable?: boolean;
  /** Enable expandable view for objects */
  expandable?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_TRUNCATE_AT = 16;
const JUST_NOW_THRESHOLD_MS = 30 * 1000; // 30 seconds

// =============================================================================
// Formatting Helpers
// =============================================================================

/**
 * Format relative time from timestamp
 */
function formatRelativeTime(timestamp: number, now: number): string {
  const diffMs = now - timestamp;

  if (diffMs < JUST_NOW_THRESHOLD_MS) {
    return "just now";
  }

  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays}d ago`;
  }
  if (diffHours > 0) {
    return `${diffHours}h ago`;
  }
  if (diffMinutes > 0) {
    return `${diffMinutes}m ago`;
  }
  return `${diffSeconds}s ago`;
}

/**
 * Format absolute timestamp for tooltip
 */
function formatAbsoluteTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

/**
 * Format duration in milliseconds to human-readable
 */
function formatDuration(ms: number): { display: string; tooltip: string } {
  if (ms < 1) {
    return { display: "<1ms", tooltip: `${ms.toFixed(3)} ms` };
  }
  if (ms < 1000) {
    return {
      display: `${Math.round(ms)}ms`,
      tooltip: `${ms.toLocaleString()} ms`,
    };
  }
  if (ms < 60000) {
    return {
      display: `${(ms / 1000).toFixed(1)}s`,
      tooltip: `${ms.toLocaleString(undefined, { maximumFractionDigits: 3 })} ms`,
    };
  }
  // Minutes
  return {
    display: `${(ms / 60000).toFixed(1)}m`,
    tooltip: `${ms.toLocaleString(undefined, { maximumFractionDigits: 3 })} ms`,
  };
}

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes: number): { display: string; tooltip: string } {
  const tooltip = `${bytes.toLocaleString()} bytes`;

  if (bytes < 1024) {
    return { display: `${bytes} B`, tooltip };
  }
  if (bytes < 1024 * 1024) {
    return { display: `${(bytes / 1024).toFixed(1)} KB`, tooltip };
  }
  if (bytes < 1024 * 1024 * 1024) {
    return { display: `${(bytes / (1024 * 1024)).toFixed(1)} MB`, tooltip };
  }
  return {
    display: `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`,
    tooltip,
  };
}

/**
 * Format number with locale separators
 */
function formatNumber(num: number): string {
  if (Number.isInteger(num)) {
    return num.toLocaleString();
  }
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/**
 * Truncate ID/string with ellipsis
 */
function truncateId(
  id: string,
  truncateAt: number,
): { display: string; isTruncated: boolean } {
  if (id.length <= truncateAt) {
    return { display: id, isTruncated: false };
  }
  const startChars = Math.ceil(truncateAt / 2);
  const endChars = Math.floor(truncateAt / 2);
  return {
    display: `${id.slice(0, startChars)}...${id.slice(-endChars)}`,
    isTruncated: true,
  };
}

/**
 * Format object/array as summary
 */
function formatJson(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return `[${value.length} items]`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 0) return "{}";
    return `{${keys.length} keys}`;
  }
  return String(value);
}

/**
 * Check if string is ISO timestamp
 */
function isIsoTimestamp(value: string): boolean {
  // Quick regex check for ISO 8601 format
  const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/;
  if (!isoRegex.test(value)) return false;
  // Verify it's a valid date
  const parsed = Date.parse(value);
  return !isNaN(parsed);
}

/**
 * Auto-detect value type
 */
function detectType(value: unknown): SmartValueType {
  if (value === null || value === undefined) return "auto";
  if (typeof value === "string" && isIsoTimestamp(value)) return "timestamp";
  if (Array.isArray(value)) return "json";
  if (typeof value === "object") return "json";
  if (typeof value === "number") return "number";
  return "auto";
}

// =============================================================================
// Component
// =============================================================================

/**
 * SmartValue Component
 *
 * Renders values in human-friendly format.
 *
 * @example
 * ```tsx
 * <SmartValue value="2026-01-15T14:25:00Z" /> // "5m ago"
 * <SmartValue value={1234} type="duration" /> // "1.2s"
 * <SmartValue value={1536} type="bytes" /> // "1.5 KB"
 * <SmartValue value="abc123def456" type="id" copyable />
 * ```
 */
export function SmartValue({
  value,
  type = "auto",
  truncateAt = DEFAULT_TRUNCATE_AT,
  copyable = false,
  expandable: _expandable = false,
  className,
  ...props
}: SmartValueProps) {
  const [copied, setCopied] = useState(false);

  // Handle copy to clipboard
  const handleCopy = useCallback(async () => {
    if (!copyable) return;
    try {
      const textValue = typeof value === "object"
        ? JSON.stringify(value, null, 2)
        : String(value);
      await navigator.clipboard.writeText(textValue);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [copyable, value]);

  // Determine effective type
  const effectiveType = type === "auto" ? detectType(value) : type;

  // Render based on type
  let displayText: string;
  let tooltip: string | undefined;

  // Handle null/undefined/boolean specially
  if (value === null) {
    displayText = "null";
  } else if (value === undefined) {
    displayText = "undefined";
  } else if (typeof value === "boolean") {
    displayText = String(value);
  } else if (value === "") {
    displayText = '""';
  } else {
    switch (effectiveType) {
      case "timestamp": {
        const timestamp =
          typeof value === "number" ? value : Date.parse(String(value));
        const now = Date.now();
        displayText = formatRelativeTime(timestamp, now);
        tooltip = formatAbsoluteTime(timestamp);
        break;
      }

      case "duration": {
        const { display, tooltip: durationTooltip } = formatDuration(
          Number(value),
        );
        displayText = display;
        tooltip = durationTooltip;
        break;
      }

      case "bytes": {
        const { display, tooltip: bytesTooltip } = formatBytes(Number(value));
        displayText = display;
        tooltip = bytesTooltip;
        break;
      }

      case "number": {
        displayText = formatNumber(Number(value));
        break;
      }

      case "id": {
        const { display, isTruncated } = truncateId(
          String(value),
          truncateAt,
        );
        displayText = display;
        if (isTruncated) {
          tooltip = String(value);
        }
        break;
      }

      case "json": {
        displayText = formatJson(value);
        break;
      }

      default: {
        displayText = String(value);
      }
    }
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1",
        copyable && "cursor-pointer hover:text-primary-10",
        className,
      )}
      onClick={copyable ? handleCopy : undefined}
      {...props}
    >
      <span
        title={tooltip}
        className={cn(
          "font-mono text-sm",
          tooltip && "cursor-help",
        )}
      >
        {displayText}
      </span>
      {copyable && (
        <span className="shrink-0" aria-hidden="true">
          {copied ? (
            <Check size={12} className="text-success-10" />
          ) : (
            <Copy size={12} className="opacity-50" />
          )}
        </span>
      )}
    </span>
  );
}

export default SmartValue;
