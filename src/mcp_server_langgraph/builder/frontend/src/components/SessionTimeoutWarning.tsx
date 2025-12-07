/**
 * Session Timeout Warning Component
 *
 * Displays a warning banner when the session is about to expire.
 * Features:
 * - Countdown timer display
 * - Refresh/extend session button
 * - Expiration message
 * - ARIA accessibility
 */

import React from 'react';
import { AlertTriangle, Clock, RefreshCw } from 'lucide-react';
import { useSessionTimeout } from '../hooks/useSessionTimeout';

// ==============================================================================
// Types
// ==============================================================================

interface SessionTimeoutWarningProps {
  sessionDuration: number; // Total session duration in ms
  warningThreshold: number; // Time before warning shows
  onRefresh?: () => void; // Called when user clicks refresh
  onExpire?: () => void; // Called when session expires
  className?: string;
}

// ==============================================================================
// Component Implementation
// ==============================================================================

export function SessionTimeoutWarning({
  sessionDuration,
  warningThreshold,
  onRefresh,
  onExpire,
  className = '',
}: SessionTimeoutWarningProps) {
  const {
    remainingTime,
    isWarning,
    isExpired,
    refreshSession,
    formattedTime,
  } = useSessionTimeout({
    sessionDuration,
    warningThreshold,
    onExpire,
  });

  // Handle refresh button click
  const handleRefresh = () => {
    refreshSession();
    onRefresh?.();
  };

  // Don't render if not in warning/expired state
  if (!isWarning && !isExpired) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`fixed bottom-4 right-4 z-50 max-w-sm ${className}`}
    >
      <div
        className={`rounded-lg shadow-lg p-4 ${
          isExpired
            ? 'bg-red-100 border border-red-300'
            : 'bg-yellow-100 border border-yellow-300'
        }`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          {isExpired ? (
            <AlertTriangle className="text-red-600\" size={20} />
          ) : (
            <Clock className="text-yellow-600" size={20} />
          )}
          <h3
            className={`font-semibold ${
              isExpired ? 'text-red-800' : 'text-yellow-800'
            }`}
          >
            {isExpired ? 'Session Expired' : 'Session Expiring Soon'}
          </h3>
        </div>

        {/* Body */}
        <div className={`text-sm ${isExpired ? 'text-red-700' : 'text-yellow-700'}`}>
          {isExpired ? (
            <p>
              Your session has expired. Please refresh the page or log in again.
            </p>
          ) : (
            <p>
              Your session will expire in{' '}
              <span className="font-mono font-bold">{formattedTime}</span>.
              Click below to continue.
            </p>
          )}
        </div>

        {/* Action Button */}
        {!isExpired && (
          <button
            onClick={handleRefresh}
            className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 transition-colors"
          >
            <RefreshCw size={16} />
            Continue Session
          </button>
        )}

        {/* Expired Action */}
        {isExpired && (
          <button
            onClick={() => window.location.reload()}
            className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
          >
            <RefreshCw size={16} />
            Refresh Page
          </button>
        )}
      </div>
    </div>
  );
}

export default SessionTimeoutWarning;
