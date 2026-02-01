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

// Import centralized types
import type { ModelStatus } from "@/types";

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

/**
 * Model lifecycle status types (for model selector)
 * @deprecated Use ModelStatus from @/types instead
 */
export type ModelLifecycleStatus = ModelStatus;

// =============================================================================
// Global Status Badge Styles
// =============================================================================

/**
 * Status badge styles (background + text + dark mode).
 * Use for status indicators, tags, and badges throughout the application.
 */
export const STATUS_BADGE_STYLES = {
  success:
    "bg-success-3 text-success-11 dark:bg-success-a6 dark:text-success-5",
  warning:
    "bg-warning-3 text-warning-10 dark:bg-warning-a6 dark:text-warning-6",
  error: "bg-error-3 text-error-11 dark:bg-error-a6 dark:text-error-9",
  info: "bg-primary-3 text-primary-11 dark:bg-primary-a6 dark:text-primary-5",
  neutral: "bg-neutral-2 text-neutral-11",
} as const;

// =============================================================================
// Model Lifecycle Badge Styles
// =============================================================================

/**
 * Model lifecycle status badge styles (for model selector).
 * Use for indicating model version status (preview, legacy, deprecated).
 * Note: 'current' models don't show a badge (no special styling needed).
 *
 * Sprint 1 - Enhanced Model Selector
 */
export const MODEL_LIFECYCLE_BADGE_STYLES = {
  /** Preview models (new/experimental) - cyan for "fresh/new" connotation */
  preview: "bg-info-3 bg-info-4 text-info-9 dark:text-info-11",
  /** Legacy models (older but supported) - amber for caution */
  legacy: "bg-warning-3 dark:bg-warning-a4 text-warning-9 dark:text-warning-9",
  /** Deprecated models (will be removed) - red for warning */
  deprecated: "bg-error-3 bg-error-4 text-error-10 dark:text-error-7",
} as const;

/**
 * Get model lifecycle badge style.
 * @param status - The model lifecycle status (preview, legacy, deprecated)
 * @returns Tailwind classes for badge styling, or undefined for 'current' models
 */
export function getModelLifecycleBadgeStyle(
  status: ModelLifecycleStatus | undefined,
): string | undefined {
  if (!status || status === "current") return undefined;
  return MODEL_LIFECYCLE_BADGE_STYLES[status];
}

// =============================================================================
// Interactive State Colors
// =============================================================================

/**
 * Interactive state colors for hover effects.
 * Use for buttons, links, and clickable elements.
 */
export const INTERACTIVE_COLORS = {
  danger:
    "hover:bg-error-3 dark:hover:bg-error-a4 hover:text-error-10 dark:hover:text-error-7",
  primary:
    "hover:bg-primary-3 dark:hover:bg-primary-a4 hover:text-primary-10 dark:hover:text-primary-7",
  success:
    "hover:bg-success-3 dark:hover:bg-success-a4 hover:text-success-10 dark:hover:text-success-7",
  warning:
    "hover:bg-warning-3 dark:hover:bg-warning-a4 hover:text-warning-9 dark:hover:text-warning-9",
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
  high: "text-success-10 dark:text-success-7",
  medium: "text-warning-9 dark:text-warning-9",
  low: "text-error-10 dark:text-error-7",
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
      return "text-success-10 dark:text-success-7";
    case "medium":
      return "text-warning-9 dark:text-warning-9";
    case "high":
      return "text-error-10 dark:text-error-7";
    case "critical":
      return "text-error-11 dark:text-error-9";
    default:
      return "text-neutral-11";
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
      return "text-success-10 dark:text-success-7";
    case "partial":
      return "text-warning-9 dark:text-warning-9";
    case "non-compliant":
      return "text-error-10 dark:text-error-7";
    default:
      return "text-neutral-11";
  }
}

// =============================================================================
// Info Color Utilities (cyan semantic alias)
// =============================================================================

/** Style variants for info elements */
export type InfoStyleVariant = "text" | "bg" | "badge" | "border";

/**
 * Info semantic colors for informational content, cloud/infrastructure indicators.
 * Uses cyan (#06b6d4) as the distinctive info color.
 */
export const INFO_COLORS = {
  /** Text styles for info labels */
  text: "text-info-9 dark:text-info-11",
  /** Background styles for info containers */
  bg: "bg-info-1 bg-info-4",
  /** Badge styles for info indicators */
  badge: "bg-info-3 text-info-10 dark:bg-info-a6 dark:text-info-5",
  /** Border styles for info containers */
  border: "border-info-4 dark:border-info-11",
} as const;

/**
 * Get info style classes by variant.
 * @param variant - The style variant (text, bg, badge, border)
 * @returns Tailwind classes for the requested variant
 */
export function getInfoStyle(variant: InfoStyleVariant): string {
  return INFO_COLORS[variant];
}

// =============================================================================
// Neutral Color Utilities (gray semantic alias)
// =============================================================================

/**
 * Style variants for neutral UI elements.
 * More comprehensive than status colors since gray is used everywhere.
 */
export type NeutralStyleVariant =
  | "text"
  | "textMuted"
  | "textSubtle"
  | "bg"
  | "bgHover"
  | "bgSelected"
  | "border"
  | "borderLight"
  | "divide";

/**
 * Neutral semantic colors for general UI elements.
 * Uses the standard gray palette for non-semantic content.
 *
 * Why neutral-* instead of gray-*:
 * - Semantic naming aligns with other color systems (success, error, etc.)
 * - Enables easier theme switching without find/replace
 * - Self-documents the intent (neutral = non-semantic UI element)
 */
export const NEUTRAL_COLORS = {
  /** Primary text (highest contrast) */
  text: "text-neutral-12",
  /** Muted text (secondary information) */
  textMuted: "text-neutral-11",
  /** Subtle text (tertiary, less important) */
  textSubtle: "text-neutral-9",
  /** Default background for cards/panels */
  bg: "bg-neutral-1",
  /** Hover background state */
  bgHover: "bg-neutral-2",
  /** Selected/active background state */
  bgSelected: "bg-neutral-3",
  /** Default border color */
  border: "border-neutral-5",
  /** Light/subtle border color */
  borderLight: "border-neutral-5",
  /** Divider/separator lines */
  divide: "divide-neutral-5 dark:divide-neutral-6",
} as const;

/**
 * Get neutral style classes by variant.
 * @param variant - The style variant (text, textMuted, bg, border, etc.)
 * @returns Tailwind classes for the requested variant
 */
export function getNeutralStyle(variant: NeutralStyleVariant): string {
  return NEUTRAL_COLORS[variant];
}
