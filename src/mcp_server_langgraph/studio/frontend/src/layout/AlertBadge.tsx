/**
 * AlertBadge Component
 *
 * Header badge indicator for infrastructure alerts.
 *
 * Features:
 * - Display alert count
 * - Color coding by severity (red for critical, yellow for warning)
 * - Animated pulse for new critical alerts
 * - Click to navigate to admin alerts
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useCallback, useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { useAppSelector } from "../store/hooks";
import {
  selectCriticalAlertCount,
  selectWarningAlertCount,
  selectLastCriticalAlertTime,
} from "../store/slices/alertSlice";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface AlertBadgeProps {
  /** Callback when badge is clicked */
  onClick: () => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

/** Time window for pulse animation (30 seconds) */
const PULSE_WINDOW_MS = 30000;

/** Max count to display before showing "99+" */
const MAX_DISPLAY_COUNT = 99;

// =============================================================================
// Component
// =============================================================================

export function AlertBadge({ onClick, className }: AlertBadgeProps) {
  // Redux selectors
  const criticalCount = useAppSelector(selectCriticalAlertCount);
  const warningCount = useAppSelector(selectWarningAlertCount);
  const lastCriticalAlertTime = useAppSelector(selectLastCriticalAlertTime);

  // Computed values
  const totalCount = criticalCount + warningCount;
  const hasCritical = criticalCount > 0;

  // Check if we should pulse (recent critical alert)
  const shouldPulse = useMemo(() => {
    if (!hasCritical || !lastCriticalAlertTime) return false;
    const timeSinceLastCritical = Date.now() - lastCriticalAlertTime;
    return timeSinceLastCritical < PULSE_WINDOW_MS;
  }, [hasCritical, lastCriticalAlertTime]);

  // Format display count
  const displayCount =
    totalCount > MAX_DISPLAY_COUNT ? "99+" : String(totalCount);

  // Aria label
  const ariaLabel = useMemo(() => {
    const parts: string[] = [];
    if (criticalCount > 0) {
      parts.push(`${criticalCount} critical`);
    }
    if (warningCount > 0) {
      parts.push(`${warningCount} warning`);
    }
    return `${totalCount} alerts: ${parts.join(", ")}`;
  }, [criticalCount, warningCount, totalCount]);

  // Tooltip text
  const tooltipText = useMemo(() => {
    const parts: string[] = [];
    if (criticalCount > 0) {
      parts.push(`${criticalCount} critical`);
    }
    if (warningCount > 0) {
      parts.push(`${warningCount} warning`);
    }
    return parts.join(", ");
  }, [criticalCount, warningCount]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick();
      }
    },
    [onClick],
  );

  // Don't render if no alerts
  if (totalCount === 0) {
    return null;
  }

  return (
    <div
      data-testid="alert-badge"
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      aria-label={ariaLabel}
      title={tooltipText}
      className={cn(
        "flex items-center gap-1.5 px-2 py-1 rounded-full cursor-pointer",
        "text-white text-xs font-medium",
        "transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
        hasCritical
          ? "bg-error-500 hover:bg-error-600 focus:ring-error-500"
          : "bg-warning-500 hover:bg-warning-600 focus:ring-warning-500",
        shouldPulse && "animate-pulse",
        className,
      )}
    >
      <AlertTriangle data-testid="alert-icon" className="w-3.5 h-3.5" />
      <span data-testid="alert-count">{displayCount}</span>
    </div>
  );
}
