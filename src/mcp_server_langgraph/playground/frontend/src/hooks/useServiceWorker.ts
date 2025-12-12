/**
 * useServiceWorker Hook
 *
 * Registers and manages the service worker for offline support.
 * Provides update detection and notification.
 */

import { useState, useEffect, useCallback } from 'react';

export interface UseServiceWorkerResult {
  isSupported: boolean;
  isRegistered: boolean;
  isOffline: boolean;
  hasUpdate: boolean;
  updateServiceWorker: () => void;
}

export function useServiceWorker(): UseServiceWorkerResult {
  const [isSupported] = useState(() => 'serviceWorker' in navigator);
  const [isRegistered, setIsRegistered] = useState(false);
  const [isOffline, setIsOffline] = useState(() => !navigator.onLine);
  const [hasUpdate, setHasUpdate] = useState(false);
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  // Register service worker
  useEffect(() => {
    if (!isSupported) return;

    // Skip in development mode
    if (import.meta.env.DEV) {
      return;
    }

    const registerSW = async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js', {
          scope: '/chat/',
        });

        setRegistration(reg);
        setIsRegistered(true);

        // Check for updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New content is available
                setHasUpdate(true);
              }
            });
          }
        });

        // Check for updates periodically (every hour)
        setInterval(() => {
          reg.update();
        }, 60 * 60 * 1000);
      } catch (error) {
        console.error('Service worker registration failed:', error);
      }
    };

    registerSW();
  }, [isSupported]);

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Update service worker
  const updateServiceWorker = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      setHasUpdate(false);
      // Reload page to use new service worker
      window.location.reload();
    }
  }, [registration]);

  return {
    isSupported,
    isRegistered,
    isOffline,
    hasUpdate,
    updateServiceWorker,
  };
}
