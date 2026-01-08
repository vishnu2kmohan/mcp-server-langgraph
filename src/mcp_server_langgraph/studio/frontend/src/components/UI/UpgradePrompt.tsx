/**
 * UpgradePrompt Component
 *
 * Displays a prompt encouraging users to upgrade their tier.
 * Shown when approaching or reaching tier limits.
 * Part of Bob's user journey - clear upgrade path when hitting limits.
 */

import { Sparkles, X } from "lucide-react";

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
        return "bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800";
      case "warning":
        return "bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800";
      case "info":
      default:
        return "bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800";
    }
  };

  const getButtonStyle = () => {
    switch (urgency) {
      case "critical":
        return "bg-error-600 hover:bg-error-700 text-white";
      case "warning":
        return "bg-warning-600 hover:bg-warning-700 text-white";
      case "info":
      default:
        return "bg-primary-600 hover:bg-primary-700 text-white";
    }
  };

  const getIconStyle = () => {
    switch (urgency) {
      case "critical":
        return "text-error-500";
      case "warning":
        return "text-warning-500";
      case "info":
      default:
        return "text-primary-500";
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
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {isAtLimit ? (
              <>Limit reached!</>
            ) : (
              <>
                Upgrade to {formatTierName(targetTier)} for {feature}
              </>
            )}
          </p>
          {currentUsage !== undefined && maxUsage !== undefined && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
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
          <button
            type="button"
            onClick={onUpgrade}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${getButtonStyle()}`}
          >
            Upgrade
          </button>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            className="p-1.5 text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-300 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-700 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default UpgradePrompt;
