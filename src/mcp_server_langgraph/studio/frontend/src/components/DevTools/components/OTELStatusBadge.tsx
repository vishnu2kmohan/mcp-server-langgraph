/**
 * OTELStatusBadge Component
 *
 * Unified status badges for OTEL data visualization.
 * Supports log levels, alert states, span status, HTTP status/methods.
 *
 * Features:
 * - CVA for type-safe variants
 * - Radix semantic colors (1-12 scale)
 * - Dark mode support
 * - WCAG 2.2 AA accessibility
 * - Optional icons
 */

import { cva, type VariantProps } from "class-variance-authority";
import {
  AlertCircle,
  AlertTriangle,
  Bug,
  Check,
  CheckCircle,
  Clock,
  Info,
  VolumeX,
  XCircle,
} from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type OTELStatusType =
  | "log-level"
  | "alert-state"
  | "alert-severity"
  | "span-status"
  | "http-status"
  | "http-method";

export type LogLevelValue = "debug" | "info" | "warning" | "error" | string;
export type AlertStateValue =
  | "firing"
  | "pending"
  | "resolved"
  | "silenced"
  | string;
export type AlertSeverityValue = "critical" | "warning" | "info" | string;
export type SpanStatusValue = "ok" | "error" | "unset" | string;
export type HttpMethodValue =
  | "GET"
  | "POST"
  | "PUT"
  | "DELETE"
  | "PATCH"
  | string;

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Base badge styles using CVA.
 * Semantic color variants follow Radix 1-12 scale.
 */
// eslint-disable-next-line react-refresh/only-export-components -- CVA variants intentionally exported for style composition
export const otelStatusBadgeVariants = cva(
  // Base classes
  [
    "inline-flex items-center gap-1 rounded-md font-medium",
    "transition-colors duration-fast",
  ],
  {
    variants: {
      colorVariant: {
        success: [
          "bg-success-3 text-success-11",
          "dark:bg-success-4 dark:text-success-7",
        ],
        warning: [
          "bg-warning-3 text-warning-11",
          "dark:bg-warning-a4 dark:text-warning-9",
        ],
        error: [
          "bg-error-3 text-error-11",
          "dark:bg-error-4 dark:text-error-7",
        ],
        primary: [
          "bg-primary-3 text-primary-11",
          "dark:bg-primary-4 dark:text-primary-7",
        ],
        insight: [
          "bg-insight-2 text-insight-11",
          "dark:bg-insight-a6 dark:text-insight-5",
        ],
        neutral: ["bg-neutral-2 text-neutral-11"],
      },
      size: {
        sm: "px-1.5 py-0.5 text-xs",
        md: "px-2 py-1 text-sm",
      },
    },
    defaultVariants: {
      colorVariant: "neutral",
      size: "sm",
    },
  },
);

export type OTELStatusBadgeVariants = VariantProps<
  typeof otelStatusBadgeVariants
>;

// =============================================================================
// Props
// =============================================================================

export interface OTELStatusBadgeProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, "children">,
    Omit<OTELStatusBadgeVariants, "colorVariant"> {
  /** Type of status badge */
  type: OTELStatusType;
  /** Value to display (level, state, code, method) */
  value: string | number;
  /** Show icon before text (default: true for log-level, alert-state, span-status) */
  showIcon?: boolean;
}

// =============================================================================
// Helpers
// =============================================================================

type ColorVariant = NonNullable<OTELStatusBadgeVariants["colorVariant"]>;

/**
 * Get color variant for log level
 */
function getLogLevelVariant(level: string): ColorVariant {
  switch (level.toLowerCase()) {
    case "debug":
      return "neutral";
    case "info":
      return "primary";
    case "warning":
    case "warn":
      return "warning";
    case "error":
      return "error";
    default:
      return "neutral";
  }
}

/**
 * Get display text for log level
 */
function getLogLevelText(level: string): string {
  const normalized = level.toLowerCase();
  if (normalized === "warning" || normalized === "warn") return "WARN";
  return level.toUpperCase();
}

/**
 * Get icon for log level
 */
function getLogLevelIcon(level: string): ReactNode {
  switch (level.toLowerCase()) {
    case "debug":
      return <Bug size={12} />;
    case "info":
      return <Info size={12} />;
    case "warning":
    case "warn":
      return <AlertTriangle size={12} />;
    case "error":
      return <XCircle size={12} />;
    default:
      return <Info size={12} />;
  }
}

/**
 * Get color variant for alert state
 */
function getAlertStateVariant(state: string): ColorVariant {
  switch (state.toLowerCase()) {
    case "firing":
      return "error";
    case "pending":
      return "warning";
    case "resolved":
      return "success";
    case "silenced":
      return "neutral";
    default:
      return "neutral";
  }
}

/**
 * Get icon for alert state
 */
function getAlertStateIcon(state: string): ReactNode {
  switch (state.toLowerCase()) {
    case "firing":
      return <AlertCircle size={12} />;
    case "pending":
      return <Clock size={12} />;
    case "resolved":
      return <CheckCircle size={12} />;
    case "silenced":
      return <VolumeX size={12} />;
    default:
      return <AlertCircle size={12} />;
  }
}

/**
 * Get color variant for alert severity
 */
function getAlertSeverityVariant(severity: string): ColorVariant {
  switch (severity.toLowerCase()) {
    case "critical":
      return "error";
    case "warning":
      return "warning";
    case "info":
      return "primary";
    default:
      return "neutral";
  }
}

/**
 * Get color variant for span status
 */
function getSpanStatusVariant(status: string): ColorVariant {
  switch (status.toLowerCase()) {
    case "ok":
      return "success";
    case "error":
      return "error";
    case "unset":
      return "neutral";
    default:
      return "neutral";
  }
}

/**
 * Get icon for span status
 */
function getSpanStatusIcon(status: string): ReactNode {
  switch (status.toLowerCase()) {
    case "ok":
      return <Check size={12} />;
    case "error":
      return <XCircle size={12} />;
    default:
      return null;
  }
}

/**
 * Get color variant for HTTP status code
 */
function getHttpStatusVariant(code: number): ColorVariant {
  if (code >= 200 && code < 300) return "success";
  if (code >= 300 && code < 400) return "primary";
  if (code >= 400 && code < 500) return "warning";
  if (code >= 500) return "error";
  return "neutral";
}

/**
 * Get color variant for HTTP method
 */
function getHttpMethodVariant(method: string): ColorVariant {
  switch (method.toUpperCase()) {
    case "GET":
      return "success";
    case "POST":
      return "primary";
    case "PUT":
      return "warning";
    case "DELETE":
      return "error";
    case "PATCH":
      return "insight";
    default:
      return "neutral";
  }
}

/**
 * Get aria-label based on status type
 */
function getAriaLabel(type: OTELStatusType, value: string | number): string {
  const typeLabels: Record<OTELStatusType, string> = {
    "log-level": "Log level",
    "alert-state": "Alert state",
    "alert-severity": "Alert severity",
    "span-status": "Span status",
    "http-status": "HTTP status",
    "http-method": "HTTP method",
  };
  return `${typeLabels[type]}: ${value}`;
}

/**
 * Determine if icon should be shown by default based on type
 */
function shouldShowIconByDefault(type: OTELStatusType): boolean {
  return (
    type === "log-level" || type === "alert-state" || type === "span-status"
  );
}

// =============================================================================
// Component
// =============================================================================

/**
 * OTEL Status Badge Component
 *
 * Unified badge for displaying status information across DevTools tabs.
 *
 * @example
 * ```tsx
 * <OTELStatusBadge type="log-level" value="error" />
 * <OTELStatusBadge type="http-status" value={404} />
 * <OTELStatusBadge type="http-method" value="POST" />
 * ```
 */
export function OTELStatusBadge({
  type,
  value,
  size,
  showIcon,
  className,
  ...props
}: OTELStatusBadgeProps) {
  // Determine color variant based on type and value
  let colorVariant: ColorVariant;
  let displayText: string;
  let icon: ReactNode = null;

  const stringValue = String(value);

  switch (type) {
    case "log-level":
      colorVariant = getLogLevelVariant(stringValue);
      displayText = getLogLevelText(stringValue);
      icon = getLogLevelIcon(stringValue);
      break;

    case "alert-state":
      colorVariant = getAlertStateVariant(stringValue);
      displayText = stringValue.toUpperCase();
      icon = getAlertStateIcon(stringValue);
      break;

    case "alert-severity":
      colorVariant = getAlertSeverityVariant(stringValue);
      displayText = stringValue.toUpperCase();
      break;

    case "span-status":
      colorVariant = getSpanStatusVariant(stringValue);
      displayText = stringValue.toUpperCase();
      icon = getSpanStatusIcon(stringValue);
      break;

    case "http-status":
      colorVariant = getHttpStatusVariant(Number(value));
      displayText = stringValue;
      break;

    case "http-method":
      colorVariant = getHttpMethodVariant(stringValue);
      displayText = stringValue.toUpperCase();
      break;

    default:
      colorVariant = "neutral";
      displayText = stringValue;
  }

  // Determine if we should show icon
  const shouldShowIcon =
    showIcon ?? (shouldShowIconByDefault(type) && icon !== null);

  return (
    <span
      role="status"
      aria-label={getAriaLabel(type, value)}
      className={cn(otelStatusBadgeVariants({ colorVariant, size }), className)}
      {...props}
    >
      {shouldShowIcon && icon && (
        <span className="shrink-0" aria-hidden="true">
          {icon}
        </span>
      )}
      <span>{displayText}</span>
    </span>
  );
}

export default OTELStatusBadge;
