/**
 * NudgeTooltip Component
 *
 * Sprint 3 - Phase 1.3: Nudge System
 *
 * A tooltip-style nudge for contextual hints and feature discovery.
 * Styled with design system colors for a subtle, non-intrusive appearance.
 */

import React from "react";
import { Lightbulb, X } from "lucide-react";
import type { Nudge } from "../../hooks/useNudges";

import { Button } from "@/components/UI";

export interface NudgeTooltipProps {
  /** The nudge to display */
  nudge: Nudge;
  /** Called when user dismisses the nudge */
  onDismiss: () => void;
  /** Called when user accepts/acknowledges the nudge */
  onAccept?: () => void;
  /** Custom action button text */
  actionText?: string;
  /** Custom className for styling */
  className?: string;
}

export function NudgeTooltip({
  nudge,
  onDismiss,
  onAccept,
  actionText = "Got it",
  className = "",
}: NudgeTooltipProps): React.ReactElement {
  return (
    <div
      role="tooltip"
      className={`
        rounded-lg border border-neutral-6 bg-neutral-2 p-3 shadow-lg
        max-w-xs
        ${className}
      `}
      data-testid={`nudge-tooltip-${nudge.id}`}
    >
      {/* Header with icon and close button */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Lightbulb
            className="h-4 w-4 text-warning-9 flex-shrink-0"
            aria-hidden="true"
          />
          {nudge.priority === "high" && (
            <span className="text-xs font-medium text-warning-11 bg-warning-3 px-1.5 py-0.5 rounded">
              High
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 min-h-6 min-w-6 p-1 text-neutral-10 hover:text-neutral-12"
          data-testid="nudge-dismiss"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Message */}
      <p className="text-sm text-neutral-12 leading-relaxed">{nudge.message}</p>

      {/* Action button */}
      {onAccept && (
        <div className="mt-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={onAccept}
            aria-label={actionText}
            className="w-full min-h-6"
          >
            {actionText}
          </Button>
        </div>
      )}
    </div>
  );
}

export default NudgeTooltip;
