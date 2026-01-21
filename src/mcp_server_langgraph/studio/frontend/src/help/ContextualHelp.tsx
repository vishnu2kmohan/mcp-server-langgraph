/**
 * ContextualHelp Component
 *
 * Phase 6: Help & Accessibility
 * Context-aware help tips that appear based on user actions.
 *
 * Features:
 * - Dismissible tips
 * - Learn more links
 * - Multiple tips support
 */

import { Lightbulb, X, ExternalLink } from "lucide-react";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface HelpTip {
  id: string;
  title: string;
  content: string;
  learnMoreUrl?: string;
}

export interface ContextualHelpProps {
  tips: HelpTip[];
  onDismiss: (tip: HelpTip) => void;
  onLearnMore: (tip: HelpTip) => void;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ContextualHelp({
  tips,
  onDismiss,
  onLearnMore,
  className,
}: ContextualHelpProps) {
  // Empty state
  if (tips.length === 0) {
    return (
      <div
        data-testid="contextual-help"
        className={cn(
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-4",
          "text-sm text-neutral-10",
          className,
        )}
      >
        <div className="flex items-center gap-2">
          <Lightbulb size={16} className="opacity-50" />
          <span>No tips available</span>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="contextual-help" className={cn("space-y-2", className)}>
      {tips.map((tip) => (
        <div
          key={tip.id}
          className={cn(
            "rounded-lg border border-warning-6 dark:border-warning-a6",
            "bg-warning-3 bg-warning-3",
            "p-3",
          )}
        >
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div className="flex-shrink-0 mt-0.5">
              <Lightbulb
                size={16}
                className="text-warning-9 dark:text-warning-9"
              />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-neutral-11">
                  {tip.title}
                </span>
                <Button
                  variant="secondary"
                  className="text-neutral-9 hover:text-neutral-11"
                  type="button"
                  aria-label="Dismiss tip"
                  onClick={() => onDismiss(tip)}>
                  <X size={14} />
                </Button>
              </div>
              <p className="text-sm text-neutral-11">
                {tip.content}
              </p>
              {tip.learnMoreUrl && (
                <Button
                  variant="ghost"
                  type="button"
                  onClick={() => onLearnMore(tip)}
                  className={cn(
                    "mt-2 flex items-center gap-1 text-xs",
                    "text-primary-10 dark:text-primary-7",
                    "hover:underline",
                  )}>
                  <span>Learn more</span>
                  <ExternalLink size={12} />
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
