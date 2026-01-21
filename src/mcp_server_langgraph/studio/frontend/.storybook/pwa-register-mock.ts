/**
 * Mock implementation of virtual:pwa-register/react for Storybook
 *
 * This mock is used when the vite-plugin-pwa is filtered out in Storybook builds.
 * It provides a no-op implementation that satisfies the module resolution
 * without requiring the actual PWA service worker functionality.
 */

import { useState, useCallback } from "react";

export interface RegisterSWOptions {
  immediate?: boolean;
  onNeedRefresh?: () => void;
  onOfflineReady?: () => void;
  onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void;
  onRegisterError?: (error: Error) => void;
}

/**
 * Mock useRegisterSW hook that provides the same interface as the real one
 * but without any actual service worker functionality.
 */
export function useRegisterSW(_options?: RegisterSWOptions) {
  const [needRefresh, setNeedRefresh] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);

  const updateServiceWorker = useCallback(async (_reloadPage?: boolean) => {
    // No-op in Storybook
  }, []);

  return {
    needRefresh: [needRefresh, setNeedRefresh] as const,
    offlineReady: [offlineReady, setOfflineReady] as const,
    updateServiceWorker,
  };
}
