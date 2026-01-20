/**
 * NudgeSpotlight Component
 *
 * Sprint 3 - Phase 1.3: Nudge System
 *
 * A spotlight overlay nudge for guided tours and feature discovery.
 * Creates a focused highlight around a target element with an overlay.
 * Styled with design system colors for a polished appearance.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Lightbulb, Sparkles, X } from "lucide-react";
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
      className={`nudge-spotlight fixed inset-0 z-50 ${className}`}
      data-testid={`nudge-spotlight-${nudge.id}`}
      role="dialog"
      aria-label={`Feature spotlight: ${nudge.message.substring(0, 50)}...`}
      aria-modal="true"
    >
      {/* Overlay with optional spotlight cutout */}
      <div
        className="spotlight-overlay fixed inset-0 bg-neutral-a9 backdrop-blur-sm"
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
        className={`
          spotlight-card spotlight-priority-${nudge.priority}
          ${isCentered ? "spotlight-card-centered fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" : "fixed"}
          rounded-lg border border-neutral-6 bg-neutral-2 p-4 shadow-xl
          max-w-sm
        `}
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
        {/* Header with icon and close button */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            {nudge.priority === "high" ? (
              <Sparkles
                className="h-4 w-4 text-warning-9 flex-shrink-0"
                aria-hidden="true"
              />
            ) : (
              <Lightbulb
                className="h-4 w-4 text-warning-9 flex-shrink-0"
                aria-hidden="true"
              />
            )}
            {showSteps && (
              <span className="text-xs font-medium text-neutral-11">
                Step {currentStep} of {totalSteps}
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            ref={closeButtonRef}
            className="h-6 w-6 p-0.5 text-neutral-10 hover:text-neutral-12"
            onClick={onDismiss}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Message content */}
        <p className="text-sm text-neutral-12 leading-relaxed mb-4">
          {nudge.message}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {onSecondaryAction && secondaryActionText && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onSecondaryAction}
              aria-label={secondaryActionText}
            >
              {secondaryActionText}
            </Button>
          )}
          {onAccept && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onAccept}
              aria-label={actionText}
              className="flex-1"
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
