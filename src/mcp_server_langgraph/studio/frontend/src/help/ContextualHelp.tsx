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
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-gray-50 dark:bg-gray-800 p-4",
          "text-sm text-gray-500 dark:text-gray-400",
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
            "rounded-lg border border-warning-200 dark:border-warning-800/50",
            "bg-warning-50 dark:bg-warning-900/20",
            "p-3",
          )}
        >
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div className="flex-shrink-0 mt-0.5">
              <Lightbulb
                size={16}
                className="text-warning-600 dark:text-warning-400"
              />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {tip.title}
                </span>
                <button
                  type="button"
                  aria-label="Dismiss tip"
                  onClick={() => onDismiss(tip)}
                  className="text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-300"
                >
                  <X size={14} />
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {tip.content}
              </p>
              {tip.learnMoreUrl && (
                <button
                  type="button"
                  onClick={() => onLearnMore(tip)}
                  className={cn(
                    "mt-2 flex items-center gap-1 text-xs",
                    "text-primary-600 dark:text-primary-400",
                    "hover:underline",
                  )}
                >
                  <span>Learn more</span>
                  <ExternalLink size={12} />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
