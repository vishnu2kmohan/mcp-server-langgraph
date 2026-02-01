/**
 * UpgradePrompt Component
 *
 * Displays a prompt encouraging users to upgrade their tier.
 * Shown when approaching or reaching tier limits.
 * Part of Bob's user journey - clear upgrade path when hitting limits.
 */

import { Sparkles, X } from "lucide-react";

import { Button } from "@/components/UI";

export interface UpgradePromptProps {
  /** Whether to show the prompt */
  show: boolean;
  /** Feature being limited */
  feature: string;
  /** Target tier to upgrade to */
  targetTier: "hybrid" | "dedicated";
  /** Current tier (for messaging) */
  currentTier?: "shared" | "hybrid";
  /** Current usage count */
  currentUsage?: number;
  /** Maximum usage allowed */
  maxUsage?: number;
  /** Link to upgrade page */
  upgradeLink?: string;
  /** Urgency level affects styling */
  urgency?: "info" | "warning" | "critical";
  /** Callback when upgrade button clicked */
  onUpgrade?: () => void;
  /** Callback when dismiss button clicked */
  onDismiss?: () => void;
}

/**
 * Upgrade prompt banner for tier limits.
 *
 * @example
 * ```tsx
 * <UpgradePrompt
 *   show={activeSessions >= maxSessions * 0.8}
 *   feature="unlimited sessions"
 *   targetTier="hybrid"
 *   currentUsage={4}
 *   maxUsage={5}
 *   onUpgrade={() => navigate('/settings?tab=billing')}
 *   onDismiss={() => setDismissed(true)}
 * />
 * ```
 */
export function UpgradePrompt({
  show,
  feature,
  targetTier,
  currentUsage,
  maxUsage,
  urgency = "info",
  onUpgrade,
  onDismiss,
}: UpgradePromptProps) {
  if (!show) {
    return null;
  }

  const formatTierName = (tier: string) => {
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  const isAtLimit =
    currentUsage !== undefined &&
    maxUsage !== undefined &&
    currentUsage >= maxUsage;

  // Get urgency-based styling
  const getUrgencyStyle = () => {
    switch (urgency) {
      case "critical":
        return "bg-error-1 dark:bg-error-a3 border-error-4 dark:border-error-11";
      case "warning":
        return "bg-warning-3 bg-warning-3 border-warning-6 dark:border-warning-11";
      case "info":
      default:
        return "bg-primary-1 dark:bg-primary-a3 border-primary-4 dark:border-primary-11";
    }
  };

  const _getButtonStyle = () => {
    switch (urgency) {
      case "critical":
        return "bg-error-10 hover:bg-error-11 text-neutral-12";
      case "warning":
        return "bg-warning-9 hover:bg-warning-10 text-neutral-12";
      case "info":
      default:
        return "bg-primary-10 hover:bg-primary-11 text-neutral-12";
    }
  };

  const getIconStyle = () => {
    switch (urgency) {
      case "critical":
        return "text-error-9";
      case "warning":
        return "text-warning-9";
      case "info":
      default:
        return "text-primary-9";
    }
  };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`rounded-lg border p-3 ${getUrgencyStyle()}`}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <Sparkles
          size={20}
          className={`flex-shrink-0 ${getIconStyle()}`}
          data-testid="upgrade-icon"
        />

        {/* Message */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neutral-12">
            {isAtLimit ? (
              <>Limit reached!</>
            ) : (
              <>
                Upgrade to {formatTierName(targetTier)} for {feature}
              </>
            )}
          </p>
          {currentUsage !== undefined && maxUsage !== undefined && (
            <p className="text-xs text-neutral-11 mt-0.5">
              {isAtLimit ? (
                <>
                  You've used all {maxUsage} of your {feature}. Upgrade for
                  more.
                </>
              ) : (
                <>
                  Using {currentUsage} of {maxUsage} available
                </>
              )}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            variant="primary"
            className="px-3 py-1.5 text-sm rounded-lg"
            type="button"
            onClick={onUpgrade}
          >
            Upgrade
          </Button>
          <Button
            variant="secondary"
            className="p-1.5 text-neutral-9 hover:text-neutral-11 rounded-lg hover:bg-neutral-3"
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            <X size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default UpgradePrompt;
