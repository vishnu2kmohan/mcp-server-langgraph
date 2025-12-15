/**
 * Mock for virtual:pwa-register/react
 *
 * Provides a mock implementation of the PWA registration hook
 * for testing purposes.
 */

import { useState } from "react";

export interface RegisterSWOptions {
  onNeedRefresh?: () => void;
  onOfflineReady?: () => void;
  onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void;
  onRegisterError?: (error: Error) => void;
}

/**
 * Mock useRegisterSW hook for testing
 */
export function useRegisterSW(options?: RegisterSWOptions) {
  const [needRefresh, setNeedRefresh] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);

  // Call callbacks if provided
  if (options?.onNeedRefresh) {
    // Store for testing
  }
  if (options?.onOfflineReady) {
    // Store for testing
  }
  if (options?.onRegistered) {
    // Store for testing
  }
  if (options?.onRegisterError) {
    // Store for testing
  }

  const updateServiceWorker = async (_reload?: boolean): Promise<void> => {
    // Mock implementation
  };

  return {
    needRefresh: [needRefresh, setNeedRefresh] as [
      boolean,
      React.Dispatch<React.SetStateAction<boolean>>,
    ],
    offlineReady: [offlineReady, setOfflineReady] as [
      boolean,
      React.Dispatch<React.SetStateAction<boolean>>,
    ],
    updateServiceWorker,
  };
}
