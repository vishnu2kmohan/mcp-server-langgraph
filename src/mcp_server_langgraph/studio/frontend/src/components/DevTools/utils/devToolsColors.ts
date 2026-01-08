/**
 * DevTools Color Utilities
 *
 * Centralized color management for DevTools components.
 * Maps to semantic Tailwind colors defined in tailwind.config.ts.
 *
 * WCAG 2.2 Accessibility Compliance:
 * - All colors use semantic names (success, warning, error) not raw colors (green, red)
 * - All colors include dark mode variants for proper contrast
 * - Text colors use 600 shade (light mode) / 400 shade (dark mode) for WCAG AA compliance
 * - Background colors use 50 shade (light) / 900 with opacity (dark) for subtle backgrounds
 *
 * Usage:
 * - Import constants for direct class usage: `className={STATUS_TEXT_COLORS.success}`
 * - Import helpers for dynamic usage: `className={getLogLevelStyle(level)}`
 * - Import SPARKLINE_COLORS for SVG/programmatic color values (hex strings)
 */

import { colors } from "../../../design-system/tokens";

// =============================================================================
// Type Definitions
// =============================================================================

/** Status levels for general UI feedback */
export type StatusLevel = "success" | "warning" | "error" | "info" | "neutral";

/** Trend direction for metrics and sparklines */
export type TrendDirection = "up" | "down" | "stable";

/** Log levels for console and log entries */
export type LogLevel = "debug" | "info" | "warning" | "error";

/** Stream status for LLM streaming tab */
export type StreamStatus = "active" | "success" | "error" | "cancelled";

/** HTTP methods for network tab */
export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | string;

// =============================================================================
// Semantic Text Colors (with dark mode)
// =============================================================================

/**
 * Text colors for status indicators.
 * Uses 600 shade for light mode (good contrast on white)
 * Uses 400 shade for dark mode (good contrast on dark backgrounds)
 */
export const STATUS_TEXT_COLORS = {
  success: "text-success-600 dark:text-success-400",
  warning: "text-warning-600 dark:text-warning-400",
  error: "text-error-600 dark:text-error-400",
  info: "text-primary-600 dark:text-primary-400",
  neutral: "text-gray-500 dark:text-gray-400",
} as const;

// =============================================================================
// Semantic Background Colors (with dark mode)
// =============================================================================

/**
 * Background colors for status containers/cards.
 * Uses 50 shade for light mode (subtle backgrounds)
 * Uses 900 with 30% opacity for dark mode (subtle on dark backgrounds)
 */
export const STATUS_BG_COLORS = {
  success: "bg-success-50 dark:bg-success-900/30",
  warning: "bg-warning-50 dark:bg-warning-900/30",
  error: "bg-error-50 dark:bg-error-900/30",
  info: "bg-primary-50 dark:bg-primary-900/30",
  neutral: "bg-gray-50 dark:bg-gray-800",
} as const;

// =============================================================================
// Log Level Badge Styles (background + text with dark mode)
// =============================================================================

/**
 * Complete badge styles for log levels.
 * Includes background and text colors for both light and dark modes.
 * Used by LogsTab LevelBadge and ConsoleTab level indicators.
 */
export const LEVEL_BADGE_STYLES = {
  debug: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  info: "bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300",
  warning:
    "bg-warning-100 text-warning-700 dark:bg-warning-900/50 dark:text-warning-300",
  error: "bg-error-100 text-error-700 dark:bg-error-900/50 dark:text-error-300",
} as const;

// =============================================================================
// HTTP Method Colors
// =============================================================================

/**
 * Text colors for HTTP method badges.
 * Semantic mapping:
 * - GET: success (safe, idempotent read)
 * - POST: primary (create action)
 * - PUT: warning (modify action)
 * - DELETE: error (destructive action)
 * - PATCH: purple (partial update)
 */
export const HTTP_METHOD_COLORS = {
  GET: "text-success-600 dark:text-success-400",
  POST: "text-primary-600 dark:text-primary-400",
  PUT: "text-warning-600 dark:text-warning-400",
  DELETE: "text-error-600 dark:text-error-400",
  PATCH: "text-insight-600 dark:text-insight-400",
  DEFAULT: "text-gray-600 dark:text-gray-400",
} as const;

// =============================================================================
// Stream Status Styles (border + background)
// =============================================================================

/**
 * Complete styles for LLM streaming status indicators.
 * Includes border and background colors for card/container styling.
 */
export const STREAM_STATUS_STYLES = {
  active:
    "border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-950",
  success:
    "border-success-200 dark:border-success-800 bg-success-50 dark:bg-success-950",
  error: "border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950",
  cancelled:
    "border-warning-200 dark:border-warning-800 bg-warning-50 dark:bg-warning-950",
} as const;

// =============================================================================
// Raw Color Values for SVG/Programmatic Use
// =============================================================================

/**
 * Raw hex color values for use in SVG elements, canvas, or programmatic styling.
 * These are imported from the design system tokens to ensure consistency.
 * Use these for sparklines, charts, or any element that requires a raw color value.
 */
export const SPARKLINE_COLORS = {
  success: colors.success[500], // #22c55e
  error: colors.error[500], // #ef4444
  neutral: colors.gray[500], // #6b7280
  primary: colors.primary[500], // #3b82f6
} as const;

// =============================================================================
// Brand Colors: Grafana Integration
// =============================================================================

/**
 * Grafana brand colors for observability integration buttons and links.
 * Uses the official Grafana brand orange (#F46800).
 */
export const GRAFANA_COLORS = {
  /** Official Grafana brand orange hex value */
  primary: colors.grafana[500], // #F46800
  /** Button styles for "View in Grafana" links */
  button:
    "bg-grafana-500 hover:bg-grafana-600 text-white dark:bg-grafana-600 dark:hover:bg-grafana-500",
  /** Text link styles for Grafana references */
  text: "text-grafana-600 dark:text-grafana-400",
} as const;

// =============================================================================
// Brand Colors: AI/Insights
// =============================================================================

/** Style variants for AI insight elements */
export type AIInsightStyleVariant = "text" | "bg" | "badge";

/**
 * AI/Insights semantic colors for AI-generated content indicators.
 * Uses purple (#a855f7) as the distinctive AI color.
 */
export const AI_INSIGHT_COLORS = {
  /** Raw hex value for programmatic use */
  primary: colors.insight[500], // #a855f7
  /** Glow effect color for sparkle animations */
  glow: colors.insight[400], // #c084fc
  /** Text styles for AI insight labels */
  text: "text-insight-600 dark:text-insight-400",
  /** Background styles for AI insight containers */
  bg: "bg-insight-50 dark:bg-insight-900/30",
  /** Badge styles for AI insight indicators */
  badge:
    "bg-insight-100 text-insight-700 dark:bg-insight-900/50 dark:text-insight-300",
} as const;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get text color class for a trend direction.
 * @param trend - The trend direction (up, down, stable)
 * @returns Tailwind text color class with dark mode variant
 */
export function getTrendTextColor(trend: TrendDirection): string {
  return trend === "up"
    ? STATUS_TEXT_COLORS.success
    : trend === "down"
      ? STATUS_TEXT_COLORS.error
      : STATUS_TEXT_COLORS.neutral;
}

/**
 * Get raw hex color for sparklines based on trend.
 * @param trend - The trend direction (up, down, stable)
 * @returns Hex color string for SVG/programmatic use
 */
export function getSparklineColor(trend: TrendDirection): string {
  return trend === "up"
    ? SPARKLINE_COLORS.success
    : trend === "down"
      ? SPARKLINE_COLORS.error
      : SPARKLINE_COLORS.neutral;
}

/**
 * Get badge style classes for a log level.
 * @param level - The log level (debug, info, warning, error)
 * @returns Tailwind classes for badge styling
 */
export function getLogLevelStyle(level: LogLevel): string {
  return LEVEL_BADGE_STYLES[level] ?? LEVEL_BADGE_STYLES.debug;
}

/**
 * Get text color class for an HTTP method.
 * @param method - The HTTP method (GET, POST, PUT, DELETE, PATCH, or other)
 * @returns Tailwind text color class with dark mode variant
 */
export function getHttpMethodColor(method: HttpMethod): string {
  return (
    HTTP_METHOD_COLORS[method as keyof typeof HTTP_METHOD_COLORS] ??
    HTTP_METHOD_COLORS.DEFAULT
  );
}

/**
 * Get complete style classes for a stream status.
 * @param status - The stream status (active, success, error, cancelled)
 * @returns Tailwind classes for border and background styling
 */
export function getStreamStatusStyle(status: StreamStatus): string {
  return STREAM_STATUS_STYLES[status];
}

/**
 * Get text color class for an HTTP status code.
 * @param statusCode - The HTTP status code (e.g., 200, 404, 500)
 * @returns Tailwind text color class with dark mode variant
 */
export function getStatusCodeColor(statusCode: number | undefined): string {
  if (!statusCode) return STATUS_TEXT_COLORS.neutral;
  if (statusCode >= 200 && statusCode < 300) return STATUS_TEXT_COLORS.success;
  if (statusCode >= 300 && statusCode < 400) return STATUS_TEXT_COLORS.info;
  if (statusCode >= 400 && statusCode < 500) return STATUS_TEXT_COLORS.warning;
  if (statusCode >= 500) return STATUS_TEXT_COLORS.error;
  return STATUS_TEXT_COLORS.neutral;
}

/**
 * Get Grafana brand button styles.
 * Use for "View in Grafana" buttons and links.
 * @returns Tailwind classes for Grafana brand button styling
 */
export function getGrafanaButtonStyle(): string {
  return GRAFANA_COLORS.button;
}

/**
 * Get AI insight style classes by variant.
 * @param variant - The style variant (text, bg, badge)
 * @returns Tailwind classes for the requested variant
 */
export function getAIInsightStyle(variant: AIInsightStyleVariant): string {
  return AI_INSIGHT_COLORS[variant];
}
