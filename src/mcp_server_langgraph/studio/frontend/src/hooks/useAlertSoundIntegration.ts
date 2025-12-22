/**
 * useAlertSoundIntegration Hook
 *
 * Integrates Redux alert state with sound notifications.
 * Watches for new critical alerts and plays sound when they occur.
 *
 * Features:
 * - Watch lastCriticalAlertTime for changes
 * - Play sound for new critical alerts
 * - Respect soundEnabled preference from Redux
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useEffect, useRef } from "react";
import { useAppSelector } from "../store/hooks";
import {
  selectLastCriticalAlertTime,
  selectSoundEnabled,
} from "../store/slices/alertSlice";
import { useAlertSound } from "./useAlertSound";

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook that integrates Redux alert state with sound notifications.
 *
 * This hook watches for changes to lastCriticalAlertTime in Redux and
 * triggers a sound notification when a new critical alert is received.
 *
 * @example
 * ```tsx
 * function App() {
 *   // Enable alert sound notifications
 *   useAlertSoundIntegration();
 *
 *   return <AlertsPanel />;
 * }
 * ```
 */
export function useAlertSoundIntegration(): void {
  const lastCriticalAlertTime = useAppSelector(selectLastCriticalAlertTime);
  const soundEnabled = useAppSelector(selectSoundEnabled);
  const { playAlertSound } = useAlertSound({ enabled: soundEnabled });

  // Track previous value to detect changes
  const prevTimeRef = useRef<number | null>(null);

  useEffect(() => {
    // Skip if sound is disabled
    if (!soundEnabled) {
      return;
    }

    // Skip if no new critical alert
    if (lastCriticalAlertTime === null) {
      return;
    }

    // Skip if this is the same timestamp (not a new alert)
    if (prevTimeRef.current === lastCriticalAlertTime) {
      return;
    }

    // Play sound for the new critical alert
    playAlertSound("critical");

    // Update the tracked timestamp
    prevTimeRef.current = lastCriticalAlertTime;
  }, [lastCriticalAlertTime, soundEnabled, playAlertSound]);
}
