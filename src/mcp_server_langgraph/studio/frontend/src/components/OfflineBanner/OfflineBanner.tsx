/**
 * OfflineBanner Component
 *
 * Sprint 3 - Phase 2.3: Offline Resilience Enhancement
 *
 * Displays offline status with pending action count and manual sync trigger.
 *
 * Features:
 * - Persistent banner when offline
 * - Pending action count display
 * - Manual sync trigger button
 * - Last sync time display
 * - Dismissible with callback
 *
 * @example
 * ```tsx
 * const { isOffline, pendingCount, sync, isSyncing, lastSyncResult } = useOfflineQueue();
 *
 * <OfflineBanner
 *   isOffline={isOffline}
 *   pendingCount={pendingCount}
 *   onSync={sync}
 *   isSyncing={isSyncing}
 *   lastSyncTime={lastSyncResult?.timestamp}
 * />
 * ```
 */

import React from "react";

export interface OfflineBannerProps {
  /** Whether the app is currently offline */
  isOffline: boolean;
  /** Number of pending actions in queue */
  pendingCount?: number;
  /** Callback when sync button clicked */
  onSync?: () => void;
  /** Whether sync is in progress */
  isSyncing?: boolean;
  /** Callback when dismiss button clicked */
  onDismiss?: () => void;
  /** Last successful sync time */
  lastSyncTime?: Date;
  /** Additional CSS classes */
  className?: string;
  /** Test ID for testing */
  testId?: string;
}

/**
 * Format relative time for display
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * Offline status banner with sync controls.
 */
export function OfflineBanner({
  isOffline,
  pendingCount = 0,
  onSync,
  isSyncing = false,
  onDismiss,
  lastSyncTime,
  className = "",
  testId,
}: OfflineBannerProps): React.ReactElement | null {
  // Don't render if online and no pending actions
  if (!isOffline && pendingCount === 0) {
    return null;
  }

  const showSyncButton = onSync && pendingCount > 0;

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`offline-banner ${isOffline ? "offline-banner--offline" : "offline-banner--pending"} ${className}`}
      data-testid={testId}
    >
      <div className="offline-banner__content">
        {/* Status Icon */}
        <span className="offline-banner__icon" aria-hidden="true">
          {isOffline ? "📡" : "⏳"}
        </span>

        {/* Message */}
        <span className="offline-banner__message">
          {isOffline ? (
            <>You are currently <strong>offline</strong></>
          ) : (
            <>Syncing changes...</>
          )}
        </span>

        {/* Pending Count */}
        {pendingCount > 0 && (
          <span className="offline-banner__pending">
            <span className="offline-banner__pending-count">{pendingCount}</span>
            {" "}pending action{pendingCount !== 1 ? "s" : ""}
          </span>
        )}

        {/* Last Sync Time */}
        {lastSyncTime && (
          <span className="offline-banner__last-sync">
            Last sync: {formatRelativeTime(lastSyncTime)}
          </span>
        )}
      </div>

      <div className="offline-banner__actions">
        {/* Sync Button */}
        {showSyncButton && (
          <button
            type="button"
            className="offline-banner__sync-btn"
            onClick={onSync}
            disabled={isSyncing}
            aria-label={isSyncing ? "Syncing..." : "Sync now"}
          >
            {isSyncing ? "Syncing..." : "Sync Now"}
          </button>
        )}

        {/* Dismiss Button */}
        {onDismiss && (
          <button
            type="button"
            className="offline-banner__dismiss-btn"
            onClick={onDismiss}
            aria-label="Dismiss offline banner"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

export default OfflineBanner;
