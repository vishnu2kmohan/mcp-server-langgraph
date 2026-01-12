/**
 * NudgeTooltip Component
 *
 * Sprint 3 - Phase 1.3: Nudge System
 *
 * A tooltip-style nudge for contextual hints and feature discovery.
 */

import React from "react";
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
      className={`nudge-tooltip nudge-priority-${nudge.priority} ${className}`}
      data-testid={`nudge-tooltip-${nudge.id}`}
    >
      <div className="nudge-header">
        <span className="nudge-icon" aria-hidden="true">
          💡
        </span>
        {nudge.priority === "high" && (
          <span className="nudge-priority-badge">High</span>
        )}
        <Button
          className="nudge-dismiss"
          data-testid="nudge-dismiss"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          ×
        </Button>
      </div>
      <p className="nudge-message">{nudge.message}</p>
      <div className="nudge-actions">
        {onAccept && (
          <Button
            className="nudge-accept"
            onClick={onAccept}
            aria-label={actionText}
          >
            {actionText}
          </Button>
        )}
      </div>
    </div>
  );
}

export default NudgeTooltip;
