/**
 * Global Color Utilities
 *
 * Semantic color management for all frontend components.
 * Import these instead of using raw Tailwind color classes.
 *
 * WCAG 2.2 Accessibility Compliance:
 * - All colors use semantic names (success, warning, error) not raw colors (green, red)
 * - All colors include dark mode variants for proper contrast
 * - Text colors use 600 shade (light mode) / 400 shade (dark mode) for WCAG AA compliance
 * - Background colors use 100 shade (light) / 900 with opacity (dark) for subtle backgrounds
 *
 * Usage:
 * - Import constants for direct class usage: `className={STATUS_BADGE_STYLES.success}`
 * - Import helpers for dynamic usage: `className={getConfidenceColor(0.85)}`
 * - Re-exports all DevTools utilities for backward compatibility
 */

// Re-export DevTools colors for backward compatibility
export * from "../components/DevTools/utils/devToolsColors";

// =============================================================================
// Type Definitions
// =============================================================================

/** Status types for badges */
export type StatusBadgeType =
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

/** Interactive state types */
export type InteractiveType = "danger" | "primary" | "success" | "warning";

/** Confidence level types */
export type ConfidenceLevel = "high" | "medium" | "low";

/** Risk level types */
export type RiskLevel = "low" | "medium" | "high" | "critical";

/** Compliance status types */
export type ComplianceStatus = "compliant" | "partial" | "non-compliant";

// =============================================================================
// Global Status Badge Styles
// =============================================================================

/**
 * Status badge styles (background + text + dark mode).
 * Use for status indicators, tags, and badges throughout the application.
 */
export const STATUS_BADGE_STYLES = {
  success:
    "bg-success-100 text-success-700 dark:bg-success-900/50 dark:text-success-300",
  warning:
    "bg-warning-100 text-warning-700 dark:bg-warning-900/50 dark:text-warning-300",
  error: "bg-error-100 text-error-700 dark:bg-error-900/50 dark:text-error-300",
  info: "bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300",
  neutral: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
} as const;

// =============================================================================
// Interactive State Colors
// =============================================================================

/**
 * Interactive state colors for hover effects.
 * Use for buttons, links, and clickable elements.
 */
export const INTERACTIVE_COLORS = {
  danger:
    "hover:bg-error-100 dark:hover:bg-error-900/30 hover:text-error-600 dark:hover:text-error-400",
  primary:
    "hover:bg-primary-100 dark:hover:bg-primary-900/30 hover:text-primary-600 dark:hover:text-primary-400",
  success:
    "hover:bg-success-100 dark:hover:bg-success-900/30 hover:text-success-600 dark:hover:text-success-400",
  warning:
    "hover:bg-warning-100 dark:hover:bg-warning-900/30 hover:text-warning-600 dark:hover:text-warning-400",
} as const;

// =============================================================================
// Confidence Level Colors (AI Components)
// =============================================================================

/**
 * Confidence level colors for AI components.
 * - High (>= 0.9): success (green)
 * - Medium (>= 0.7): warning (amber)
 * - Low (< 0.7): error (red)
 */
export const CONFIDENCE_COLORS = {
  high: "text-success-600 dark:text-success-400",
  medium: "text-warning-600 dark:text-warning-400",
  low: "text-error-600 dark:text-error-400",
} as const;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get status badge style by type.
 * @param status - The status type (success, warning, error, info, neutral)
 * @returns Tailwind classes for badge styling
 */
export function getStatusBadgeStyle(status: StatusBadgeType): string {
  return STATUS_BADGE_STYLES[status] ?? STATUS_BADGE_STYLES.neutral;
}

/**
 * Get confidence color by score.
 * @param confidence - A number between 0 and 1
 * @returns Tailwind text color class with dark mode variant
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return CONFIDENCE_COLORS.high;
  if (confidence >= 0.7) return CONFIDENCE_COLORS.medium;
  return CONFIDENCE_COLORS.low;
}

/**
 * Get risk level color.
 * @param level - The risk level (low, medium, high, critical)
 * @returns Tailwind text color class with dark mode variant
 */
export function getRiskLevelColor(level: RiskLevel): string {
  switch (level) {
    case "low":
      return "text-success-600 dark:text-success-400";
    case "medium":
      return "text-warning-600 dark:text-warning-400";
    case "high":
      return "text-error-600 dark:text-error-400";
    case "critical":
      return "text-error-700 dark:text-error-300";
    default:
      return "text-gray-600 dark:text-gray-400";
  }
}

/**
 * Get compliance status color.
 * @param status - The compliance status (compliant, partial, non-compliant)
 * @returns Tailwind text color class with dark mode variant
 */
export function getComplianceStatusColor(status: ComplianceStatus): string {
  switch (status) {
    case "compliant":
      return "text-success-600 dark:text-success-400";
    case "partial":
      return "text-warning-600 dark:text-warning-400";
    case "non-compliant":
      return "text-error-600 dark:text-error-400";
    default:
      return "text-gray-600 dark:text-gray-400";
  }
}
