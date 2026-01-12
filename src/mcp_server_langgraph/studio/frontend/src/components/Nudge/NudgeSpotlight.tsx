/**
 * NudgeSpotlight Component
 *
 * Sprint 3 - Phase 1.3: Nudge System
 *
 * A spotlight overlay nudge for guided tours and feature discovery.
 * Creates a focused highlight around a target element with an overlay.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import type { Nudge } from "../../hooks/useNudges";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface NudgeSpotlightProps {
  /** The nudge to display */
  nudge: Nudge;
  /** Called when user dismisses the spotlight */
  onDismiss: () => void;
  /** Called when user accepts/acknowledges the spotlight */
  onAccept?: () => void;
  /** Custom action button text */
  actionText?: string;
  /** Secondary action text (e.g., "Skip Tour") */
  secondaryActionText?: string;
  /** Called when secondary action is clicked */
  onSecondaryAction?: () => void;
  /** Current step number (for multi-step tours) */
  currentStep?: number;
  /** Total number of steps */
  totalSteps?: number;
  /** Custom className for styling */
  className?: string;
}

interface SpotlightPosition {
  top: number;
  left: number;
  width: number;
  height: number;
}

// =============================================================================
// Component
// =============================================================================

export function NudgeSpotlight({
  nudge,
  onDismiss,
  onAccept,
  actionText = "Got it",
  secondaryActionText,
  onSecondaryAction,
  currentStep,
  totalSteps,
  className = "",
}: NudgeSpotlightProps): React.ReactElement {
  const [targetPosition, setTargetPosition] =
    useState<SpotlightPosition | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  // Calculate target element position
  useEffect(() => {
    if (nudge.targetElement) {
      const target = document.querySelector(nudge.targetElement);
      if (target) {
        const rect = target.getBoundingClientRect();
        setTargetPosition({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        });
      }
    }
  }, [nudge.targetElement]);

  // Focus trap: Focus close button on mount
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onDismiss();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onDismiss]);

  // Handle overlay click (but not card click)
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onDismiss();
      }
    },
    [onDismiss],
  );

  // Prevent card click from bubbling to overlay
  const handleCardClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  const isCentered = !nudge.targetElement || !targetPosition;
  const showSteps = currentStep !== undefined && totalSteps !== undefined;

  return (
    <div
      className={`nudge-spotlight ${className}`}
      data-testid={`nudge-spotlight-${nudge.id}`}
      role="dialog"
      aria-label={`Feature spotlight: ${nudge.message.substring(0, 50)}...`}
      aria-modal="true"
    >
      {/* Overlay with optional spotlight cutout */}
      <div
        className="spotlight-overlay"
        data-testid="spotlight-overlay"
        onClick={handleOverlayClick}
        style={
          targetPosition
            ? {
                clipPath: `polygon(
                  0% 0%,
                  0% 100%,
                  ${targetPosition.left}px 100%,
                  ${targetPosition.left}px ${targetPosition.top}px,
                  ${targetPosition.left + targetPosition.width}px ${targetPosition.top}px,
                  ${targetPosition.left + targetPosition.width}px ${targetPosition.top + targetPosition.height}px,
                  ${targetPosition.left}px ${targetPosition.top + targetPosition.height}px,
                  ${targetPosition.left}px 100%,
                  100% 100%,
                  100% 0%
                )`,
              }
            : undefined
        }
      />
      {/* Spotlight card */}
      <div
        ref={cardRef}
        className={`spotlight-card spotlight-priority-${nudge.priority} ${
          isCentered ? "spotlight-card-centered" : ""
        }`}
        data-testid="spotlight-card"
        onClick={handleCardClick}
        style={
          targetPosition
            ? {
                top: targetPosition.top + targetPosition.height + 16,
                left: targetPosition.left,
              }
            : undefined
        }
      >
        {/* Header with close button */}
        <div className="spotlight-header">
          <span className="spotlight-icon" aria-hidden="true">
            {nudge.priority === "high" ? "🌟" : "💡"}
          </span>
          {showSteps && (
            <span className="spotlight-step-indicator">
              Step {currentStep} of {totalSteps}
            </span>
          )}
          <Button
            className="spotlight-close"
            ref={closeButtonRef}
            onClick={onDismiss}
            aria-label="Close"
          >
            ×
          </Button>
        </div>

        {/* Message content */}
        <p className="spotlight-message">{nudge.message}</p>

        {/* Actions */}
        <div className="spotlight-actions">
          {onSecondaryAction && secondaryActionText && (
            <Button
              className="spotlight-action-secondary"
              onClick={onSecondaryAction}
              aria-label={secondaryActionText}
            >
              {secondaryActionText}
            </Button>
          )}
          {onAccept && (
            <Button
              className="spotlight-action-primary"
              onClick={onAccept}
              aria-label={actionText}
            >
              {actionText}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default NudgeSpotlight;
