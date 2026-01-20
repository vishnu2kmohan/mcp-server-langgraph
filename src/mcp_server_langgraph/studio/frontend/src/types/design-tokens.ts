/**
 * Design Token Type Definitions
 *
 * Centralized type definitions for the design system.
 * These types ensure consistency across all components.
 *
 * @see tailwind.config.ts for the actual token values
 * @see docs-internal/frontend/DESIGN_SYSTEM.md for documentation
 */

// =============================================================================
// Color Types
// =============================================================================

/**
 * Semantic color names used across the design system.
 * Maps to Tailwind color scales in tailwind.config.ts
 */
export type SemanticColor =
  | "primary" // Main brand actions (sky blue)
  | "success" // Positive states, confirmations (green)
  | "warning" // Cautions, pending states (amber)
  | "error" // Errors, destructive actions (red)
  | "info" // Informational, cloud/infrastructure (cyan)
  | "insight" // AI features, suggestions (purple)
  | "grafana" // Observability integration (orange)
  | "neutral"; // General UI (gray replacement)

/**
 * Color scale values (50-950)
 * Used for generating utility classes like `bg-primary-9`
 */
export type ColorScale =
  | 50
  | 100
  | 200
  | 300
  | 400
  | 500
  | 600
  | 700
  | 800
  | 900
  | 950;

/**
 * Status type for badges, indicators, and feedback
 */
export type StatusType = "success" | "warning" | "error" | "info" | "neutral";

// =============================================================================
// Size Types
// =============================================================================

/**
 * Size scale used across components
 */
export type SizeScale = "xs" | "sm" | "md" | "lg" | "xl";

/**
 * Common component sizes (subset of SizeScale)
 */
export type ComponentSize = "sm" | "md" | "lg";

// =============================================================================
// Spacing & Layout
// =============================================================================

/**
 * Border radius tokens
 */
export type BorderRadius = "none" | "sm" | "md" | "lg" | "xl" | "2xl" | "full";

/**
 * Shadow tokens
 */
export type Shadow = "none" | "soft" | "elevated" | "modal";

/**
 * Transition duration tokens
 */
export type TransitionDuration = "fast" | "normal" | "slow";

// =============================================================================
// Component Variant Types
// =============================================================================

/**
 * Button variant options
 */
export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "success"
  | "outline";

/**
 * Badge variant options
 */
export type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

/**
 * Card variant options
 */
export type CardVariant = "default" | "elevated" | "ghost";

/**
 * Dialog size options
 */
export type DialogSize = "sm" | "md" | "lg" | "xl" | "full";

/**
 * StatusBadge status options
 */
export type StatusBadgeStatus =
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

/**
 * Tooltip position options
 */
export type TooltipPosition = "top" | "right" | "bottom" | "left";

/**
 * ErrorState variant options
 */
export type ErrorStateVariant = "default" | "compact" | "fullscreen";

/**
 * RiskBadge level options
 */
export type RiskLevel = "low" | "medium" | "high" | "critical";

// =============================================================================
// Utility Types
// =============================================================================

/**
 * Helper type to generate Tailwind class strings
 * e.g., `bg-${SemanticColor}-${ColorScale}`
 */
export type TailwindColorClass<
  Prefix extends string,
  Color extends SemanticColor,
  Scale extends ColorScale,
> = `${Prefix}-${Color}-${Scale}`;

/**
 * Interactive element state
 */
export type InteractiveState =
  | "default"
  | "hover"
  | "active"
  | "focus"
  | "disabled";

// =============================================================================
// Theme Types
// =============================================================================

/**
 * Theme mode
 */
export type ThemeMode = "light" | "dark" | "system";

/**
 * Accessibility preference
 */
export type ReducedMotion = "no-preference" | "reduce";
