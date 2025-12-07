/**
 * Session Timeout Warning Hook
 *
 * Provides session management with:
 * - Countdown timer
 * - Warning threshold alerts
 * - Session refresh capability
 * - Optional auto-refresh on user activity
 * - Expiration callbacks
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// ==============================================================================
// Types
// ==============================================================================

interface SessionTimeoutOptions {
  sessionDuration: number; // Total session duration in milliseconds
  warningThreshold?: number; // Time remaining before warning (ms)
  autoRefreshOnActivity?: boolean; // Refresh on user activity
  onWarning?: () => void; // Called when entering warning state
  onExpire?: () => void; // Called when session expires
}

interface SessionTimeoutResult {
  remainingTime: number; // Time remaining in milliseconds
  isWarning: boolean; // Whether in warning state
  isExpired: boolean; // Whether session has expired
  refreshSession: () => void; // Refresh/reset the session
  formattedTime: string; // Human-readable time (MM:SS)
}

// ==============================================================================
// Constants
// ==============================================================================

const UPDATE_INTERVAL = 1000; // Update every second

// Activity events to listen for
const ACTIVITY_EVENTS = [
  'mousemove',
  'mousedown',
  'keydown',
  'touchstart',
  'scroll',
];

// ==============================================================================
// Helper Functions
// ==============================================================================

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// ==============================================================================
// Hook Implementation
// ==============================================================================

export function useSessionTimeout(
  options: SessionTimeoutOptions
): SessionTimeoutResult {
  const {
    sessionDuration,
    warningThreshold = 60000, // Default: warn at 1 minute
    autoRefreshOnActivity = false,
    onWarning,
    onExpire,
  } = options;

  // State
  const [remainingTime, setRemainingTime] = useState(sessionDuration);
  const [isExpired, setIsExpired] = useState(false);

  // Refs
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const warningCalledRef = useRef(false);
  const expireCalledRef = useRef(false);
  const mountedRef = useRef(true);

  // Computed values
  const isWarning = remainingTime <= warningThreshold && remainingTime > 0;
  const formattedTime = formatTime(remainingTime);

  // Refresh session
  const refreshSession = useCallback(() => {
    setRemainingTime(sessionDuration);
    setIsExpired(false);
    warningCalledRef.current = false;
    expireCalledRef.current = false;
  }, [sessionDuration]);

  // Handle user activity
  const handleActivity = useCallback(() => {
    if (autoRefreshOnActivity && mountedRef.current) {
      refreshSession();
    }
  }, [autoRefreshOnActivity, refreshSession]);

  // Set up countdown timer
  useEffect(() => {
    mountedRef.current = true;

    intervalRef.current = setInterval(() => {
      if (!mountedRef.current) return;

      setRemainingTime((prev) => {
        const newTime = Math.max(0, prev - UPDATE_INTERVAL);

        // Check for warning state
        if (
          newTime <= warningThreshold &&
          newTime > 0 &&
          !warningCalledRef.current
        ) {
          warningCalledRef.current = true;
          onWarning?.();
        }

        // Check for expiration
        if (newTime === 0 && !expireCalledRef.current) {
          expireCalledRef.current = true;
          setIsExpired(true);
          onExpire?.();
        }

        return newTime;
      });
    }, UPDATE_INTERVAL);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [warningThreshold, onWarning, onExpire]);

  // Set up activity listeners
  useEffect(() => {
    if (!autoRefreshOnActivity) return;

    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [autoRefreshOnActivity, handleActivity]);

  return {
    remainingTime,
    isWarning,
    isExpired,
    refreshSession,
    formattedTime,
  };
}

export default useSessionTimeout;
