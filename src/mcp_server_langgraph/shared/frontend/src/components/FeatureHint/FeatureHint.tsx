/**
 * FeatureHint Component
 *
 * Progressive disclosure hints for feature discovery.
 * Helps users discover features at the right moment.
 */

import { ReactElement, useState, useCallback, useMemo, useEffect } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface FeatureHintProps {
  /** Unique identifier for this feature hint */
  featureId: string;
  /** Title of the hint */
  title: string;
  /** Description of the feature */
  description: string;
  /** Label for the action button */
  actionLabel?: string;
  /** Callback when action button is clicked */
  onAction?: () => void;
  /** Display variant */
  variant?: 'inline' | 'banner' | 'popover';
  /** Additional CSS classes */
  className?: string;
}

export interface HintConfig {
  featureId: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export interface UseFeatureDiscoveryResult {
  /** Current hint to display (null if none) */
  currentHint: HintConfig | null;
  /** Dismiss a hint by feature ID */
  dismissHint: (featureId: string) => void;
  /** Mark a feature as explored (same as dismiss) */
  markFeatureExplored: (featureId: string) => void;
}

// =============================================================================
// Constants
// =============================================================================

const DISMISSED_STORAGE_KEY = 'feature_hints_dismissed';

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

function getDismissedHints(): string[] {
  try {
    const stored = localStorage.getItem(DISMISSED_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveDismissedHints(dismissed: string[]): void {
  try {
    localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify(dismissed));
  } catch {
    // Ignore storage errors
  }
}

// =============================================================================
// useFeatureDiscovery Hook
// =============================================================================

export function useFeatureDiscovery(hints: HintConfig[]): UseFeatureDiscoveryResult {
  const [dismissedIds, setDismissedIds] = useState<string[]>(() => getDismissedHints());

  const dismissHint = useCallback((featureId: string) => {
    setDismissedIds((prev) => {
      if (prev.includes(featureId)) return prev;
      const updated = [...prev, featureId];
      saveDismissedHints(updated);
      return updated;
    });
  }, []);

  const markFeatureExplored = useCallback((featureId: string) => {
    dismissHint(featureId);
  }, [dismissHint]);

  const currentHint = useMemo(() => {
    const availableHints = hints.filter((hint) => !dismissedIds.includes(hint.featureId));
    return availableHints.length > 0 ? availableHints[0] : null;
  }, [hints, dismissedIds]);

  return {
    currentHint,
    dismissHint,
    markFeatureExplored,
  };
}

// =============================================================================
// FeatureHint Component
// =============================================================================

export function FeatureHint({
  featureId,
  title,
  description,
  actionLabel,
  onAction,
  variant = 'inline',
  className,
}: FeatureHintProps): ReactElement | null {
  const [isDismissed, setIsDismissed] = useState<boolean>(() => {
    const dismissed = getDismissedHints();
    return dismissed.includes(featureId);
  });

  // Re-check on mount in case localStorage changed
  useEffect(() => {
    const dismissed = getDismissedHints();
    if (dismissed.includes(featureId)) {
      setIsDismissed(true);
    }
  }, [featureId]);

  const handleDismiss = useCallback(() => {
    const dismissed = getDismissedHints();
    if (!dismissed.includes(featureId)) {
      saveDismissedHints([...dismissed, featureId]);
    }
    setIsDismissed(true);
  }, [featureId]);

  const handleAction = useCallback(() => {
    onAction?.();
  }, [onAction]);

  if (isDismissed) {
    return null;
  }

  const baseStyles = clsx(
    'rounded-lg border p-4',
    'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    variant === 'banner' && 'w-full',
    variant === 'popover' && 'shadow-lg max-w-sm',
    className
  );

  return (
    <aside role="complementary" className={baseStyles}>
      {/* Title */}
      <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-1">
        {title}
      </h4>

      {/* Description */}
      <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
        {description}
      </p>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={handleAction}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-medium',
              'bg-blue-600 text-white hover:bg-blue-700',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            )}
          >
            {actionLabel}
          </button>
        )}
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss hint"
          className={clsx(
            'px-3 py-1.5 rounded-md text-xs font-medium',
            'bg-white text-blue-700 border border-blue-300 hover:bg-blue-50',
            'dark:bg-gray-800 dark:text-blue-300 dark:border-blue-700 dark:hover:bg-gray-700',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
          )}
        >
          Dismiss
        </button>
      </div>
    </aside>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default FeatureHint;
