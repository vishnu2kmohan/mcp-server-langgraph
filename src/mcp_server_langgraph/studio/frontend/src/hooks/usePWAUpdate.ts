/**
 * PWA Update Hook
 *
 * Manages service worker updates and offline readiness.
 * Provides state and actions for prompting users to update.
 */

import { useState, useCallback } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";
import { devLogger } from "../utils/devLogger";

// Create prefixed logger for this hook
const logger = devLogger.withPrefix("[PWAUpdate]");

export interface PWAUpdateState {
  /** Whether a new version is available */
  needsUpdate: boolean;
  /** Whether the app is ready for offline use */
  isOfflineReady: boolean;
  /** Whether an update is in progress */
  isUpdating: boolean;
  /** Whether the update prompt was dismissed */
  updateDismissed: boolean;
  /** Service worker registration object */
  registration: ServiceWorkerRegistration | undefined;
  /** Error from registration */
  registrationError: Error | undefined;
}

export interface PWAUpdateActions {
  /** Trigger an update and reload */
  updateApp: () => Promise<void>;
  /** Dismiss the update prompt */
  dismissUpdate: () => void;
}

export type UsePWAUpdateReturn = PWAUpdateState & PWAUpdateActions;

/**
 * Hook to manage PWA updates and offline readiness.
 *
 * @returns State and actions for managing PWA updates
 *
 * @example
 * ```tsx
 * const { needsUpdate, isOfflineReady, updateApp, dismissUpdate } = usePWAUpdate();
 *
 * if (needsUpdate) {
 *   return (
 *     <UpdatePrompt onUpdate={updateApp} onDismiss={dismissUpdate} />
 *   );
 * }
 * ```
 */
export function usePWAUpdate(): UsePWAUpdateReturn {
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [registration, setRegistration] = useState<
    ServiceWorkerRegistration | undefined
  >(undefined);
  const [registrationError, setRegistrationError] = useState<Error | undefined>(
    undefined,
  );

  const {
    needRefresh: [needsUpdate, setNeedsUpdate],
    offlineReady: [isOfflineReady, setIsOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onNeedRefresh() {
      setNeedsUpdate(true);
    },
    onOfflineReady() {
      setIsOfflineReady(true);
    },
    onRegistered(r: ServiceWorkerRegistration | undefined) {
      setRegistration(r);
    },
    onRegisterError(error: Error) {
      setRegistrationError(error);
      logger.error("Service worker registration error:", error);
    },
  });

  const updateApp = useCallback(async () => {
    setIsUpdating(true);
    try {
      await updateServiceWorker(true);
    } catch (error) {
      logger.error("Failed to update service worker:", error);
    } finally {
      setIsUpdating(false);
    }
  }, [updateServiceWorker]);

  const dismissUpdate = useCallback(() => {
    setUpdateDismissed(true);
    setNeedsUpdate(false);
  }, [setNeedsUpdate]);

  return {
    needsUpdate,
    isOfflineReady,
    isUpdating,
    updateDismissed,
    registration,
    registrationError,
    updateApp,
    dismissUpdate,
  };
}
