/**
 * Push Notifications Hook
 *
 * Manages Web Push notification subscriptions.
 * Provides state and actions for subscribing/unsubscribing to push notifications.
 */

import { useState, useEffect, useCallback } from "react";

// VAPID public key for push notifications (should come from env in production)
// This is a test key - replace with actual key in production
const VAPID_PUBLIC_KEY =
  import.meta.env.VITE_VAPID_PUBLIC_KEY ||
  "BLc4xRLAFKrpqKtxOaJkaNGvOhNvVZ2M7qFXnXmP3X-5QJ6LR5XZxFNz1LGxnGvt";

/**
 * Convert a base64 string to Uint8Array for VAPID key
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export interface PushNotificationState {
  /** Whether push notifications are supported */
  isSupported: boolean;
  /** Whether currently subscribed to push notifications */
  isSubscribed: boolean;
  /** Current notification permission status */
  permission: NotificationPermission | "unsupported";
  /** Current push subscription */
  subscription: PushSubscription | null;
  /** Whether loading subscription status */
  isLoading: boolean;
  /** Error from subscription operations */
  error: Error | null;
}

export interface PushNotificationActions {
  /** Subscribe to push notifications */
  subscribe: () => Promise<void>;
  /** Unsubscribe from push notifications */
  unsubscribe: () => Promise<void>;
}

export type UsePushNotificationsReturn = PushNotificationState &
  PushNotificationActions;

/**
 * Hook to manage push notification subscriptions.
 *
 * @returns State and actions for managing push notifications
 *
 * @example
 * ```tsx
 * const { isSubscribed, permission, subscribe, unsubscribe } = usePushNotifications();
 *
 * if (permission === 'default') {
 *   return <button onClick={subscribe}>Enable Notifications</button>;
 * }
 * ```
 */
export function usePushNotifications(): UsePushNotificationsReturn {
  const [isLoading, setIsLoading] = useState(true);
  const [subscription, setSubscription] = useState<PushSubscription | null>(
    null,
  );
  const [error, setError] = useState<Error | null>(null);
  const [permission, setPermission] = useState<
    NotificationPermission | "unsupported"
  >("default");

  // Check if push notifications are supported
  const isSupported =
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window;

  // Check for existing subscription on mount
  useEffect(() => {
    const checkSubscription = async () => {
      if (!isSupported) {
        setPermission("unsupported");
        setIsLoading(false);
        return;
      }

      try {
        // Update permission status (safely check Notification exists)
        if (typeof Notification !== "undefined") {
          setPermission(Notification.permission);
        }

        // Check for existing subscription
        const registration = await navigator.serviceWorker.ready;
        const existingSubscription =
          await registration.pushManager.getSubscription();

        if (existingSubscription) {
          setSubscription(existingSubscription);
        }
      } catch (err) {
        console.error("Failed to check push subscription:", err);
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setIsLoading(false);
      }
    };

    checkSubscription();
  }, [isSupported]);

  const subscribe = useCallback(async () => {
    if (!isSupported) {
      setError(new Error("Push notifications are not supported"));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Request notification permission
      const permissionResult = await Notification.requestPermission();
      setPermission(permissionResult);

      if (permissionResult !== "granted") {
        setIsLoading(false);
        return;
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;

      // Subscribe to push manager
      const pushSubscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(
          VAPID_PUBLIC_KEY,
        ) as BufferSource,
      });

      // Send subscription to backend
      const token = localStorage.getItem("auth_token");
      const response = await fetch("/api/v1/notifications/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(pushSubscription.toJSON()),
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to register subscription with server");
      }

      setSubscription(pushSubscription);
    } catch (err) {
      console.error("Failed to subscribe to push notifications:", err);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    if (!subscription) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Unsubscribe from push manager
      await subscription.unsubscribe();

      // Notify backend
      const token = localStorage.getItem("auth_token");
      await fetch("/api/v1/notifications/unsubscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ endpoint: subscription.endpoint }),
        credentials: "include",
      });

      setSubscription(null);
    } catch (err) {
      console.error("Failed to unsubscribe from push notifications:", err);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [subscription]);

  return {
    isSupported,
    isSubscribed: subscription !== null,
    permission,
    subscription,
    isLoading,
    error,
    subscribe,
    unsubscribe,
  };
}
