/**
 * Mock for virtual:pwa-register
 *
 * Provides a mock implementation of the PWA registration function
 * for testing purposes.
 */

export interface RegisterSWOptions {
  immediate?: boolean;
  onNeedRefresh?: () => void;
  onOfflineReady?: () => void;
  onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void;
  onRegisterError?: (error: Error) => void;
}

/**
 * Mock registerSW function for testing
 */
export function registerSW(
  _options?: RegisterSWOptions,
): (reloadPage?: boolean) => Promise<void> {
  return async (_reloadPage?: boolean): Promise<void> => {
    // Mock implementation - returns cleanup function
  };
}
