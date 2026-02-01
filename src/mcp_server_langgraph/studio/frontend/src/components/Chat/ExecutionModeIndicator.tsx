/**
 * ExecutionModeIndicator Component
 *
 * Visual badge displaying current execution mode with click-to-cycle functionality.
 * Part of the Claude Code-style Ctrl/Cmd+Shift+M mode toggle feature.
 *
 * Design System Compliance:
 * - Uses CVA for mode variants
 * - Uses Motion.dev buttonVariants for press feedback
 * - Implements useReducedMotion() for accessibility
 * - WCAG 2.5.8 minimum touch target (min-h-8 = 32px)
 *
 * @see Plan: Research-Plan-Implement UX with Ctrl/Cmd+Shift+M Mode Toggle
 */

import { motion, useReducedMotion } from "motion/react";
import { cva, type VariantProps } from "class-variance-authority";
import { MessageSquare, ClipboardList, Zap, ShieldOff } from "lucide-react";
import { buttonVariants } from "@/design-system/micro-interactions";
import type { ExecutionMode } from "@/store/slices/executionModeSlice";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Execution mode indicator variants using CVA
 * Each mode has distinct semantic colors per STYLE.md
 */
// eslint-disable-next-line react-refresh/only-export-components
export const executionModeIndicatorVariants = cva(
  // Base styles - meets WCAG 2.5.8 touch target
  [
    "inline-flex items-center gap-1.5 px-2 py-1 rounded-full",
    "text-xs font-medium cursor-pointer min-h-8",
    "transition-colors duration-150",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
    "disabled:opacity-50 disabled:cursor-not-allowed",
  ],
  {
    variants: {
      mode: {
        default: "bg-neutral-3 text-neutral-11 hover:bg-neutral-4",
        plan: "bg-primary-3 text-primary-11 hover:bg-primary-4",
        auto_accept: "bg-success-3 text-success-11 hover:bg-success-4",
        bypass: "bg-warning-3 text-warning-11 hover:bg-warning-4",
      },
    },
    defaultVariants: {
      mode: "default",
    },
  },
);

// =============================================================================
// Mode Configuration
// =============================================================================

/**
 * Configuration for each execution mode
 */
const modeConfig: Record<
  ExecutionMode,
  {
    icon: typeof MessageSquare;
    label: string;
    tooltip: string;
  }
> = {
  default: {
    icon: MessageSquare,
    label: "Default",
    tooltip: "Normal chat - approval for medium/high risk",
  },
  plan: {
    icon: ClipboardList,
    label: "Plan",
    tooltip: "All tasks require approval",
  },
  auto_accept: {
    icon: Zap,
    label: "Auto",
    tooltip: "Accept suggestions automatically",
  },
  bypass: {
    icon: ShieldOff,
    label: "Bypass",
    tooltip: "Risk-aware auto-approval (requires permission)",
  },
};

// =============================================================================
// Types
// =============================================================================

export interface ExecutionModeIndicatorProps extends VariantProps<
  typeof executionModeIndicatorVariants
> {
  /** Current execution mode */
  mode: ExecutionMode;
  /** Callback when indicator is clicked to cycle modes */
  onClick: () => void;
  /** Whether the indicator is disabled */
  disabled?: boolean;
  /** Whether user has bypass permission (OpenFGA bypass_executor on system:global) */
  hasBypassPermission?: boolean;
  /** Additional class names */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * ExecutionModeIndicator - Visual badge for execution mode
 *
 * Displays current mode with icon and label.
 * Clicking cycles through available modes.
 * Uses Motion.dev for subtle press feedback.
 */
export function ExecutionModeIndicator({
  mode,
  onClick,
  disabled = false,
  hasBypassPermission: _hasBypassPermission = false,
  className,
}: ExecutionModeIndicatorProps) {
  // Reduced motion preference for accessibility
  const prefersReducedMotion = useReducedMotion();

  // Get configuration for current mode
  const config = modeConfig[mode];
  const Icon = config.icon;

  return (
    <motion.button
      data-testid="execution-mode-indicator"
      type="button"
      className={executionModeIndicatorVariants({ mode, className })}
      onClick={onClick}
      disabled={disabled}
      variants={prefersReducedMotion ? undefined : buttonVariants}
      initial="rest"
      whileHover={disabled ? undefined : "hover"}
      whileTap={disabled ? undefined : "pressed"}
      aria-label={`Execution mode: ${config.label}. Press Ctrl/Cmd+Shift+M to cycle.`}
      title={config.tooltip}
    >
      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
      <span>{config.label}</span>
    </motion.button>
  );
}

ExecutionModeIndicator.displayName = "ExecutionModeIndicator";
