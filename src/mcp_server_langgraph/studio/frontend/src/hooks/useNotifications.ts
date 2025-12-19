/**
 * useNotifications Hook
 *
 * Hook to manage desktop/browser notifications.
 * Features:
 * - Permission request and tracking
 * - Send notifications with title, body, icon
 * - Success/error/info notification types
 * - Fallback for unsupported browsers
 * - Respects user preferences
 */

import { useState, useCallback, useMemo } from "react";

// ==============================================================================
// Types
// ==============================================================================

export type NotificationPermission = "default" | "granted" | "denied";

export interface NotificationOptions {
  body?: string;
  icon?: string;
  tag?: string;
  requireInteraction?: boolean;
  silent?: boolean;
  data?: unknown;
}

export interface UseNotificationsOptions {
  /** Whether notifications are enabled (default: true) */
  enabled?: boolean;
  /** Default icon for notifications */
  defaultIcon?: string;
}

export interface NotificationState {
  /** Current permission state */
  permission: NotificationPermission;
  /** Whether notifications are supported */
  isSupported: boolean;
  /** Request permission to send notifications */
  requestPermission: () => Promise<boolean>;
  /** Send a notification */
  notify: (
    title: string,
    options?: NotificationOptions,
  ) => Notification | undefined;
  /** Send a success notification */
  success: (title: string, body?: string) => Notification | undefined;
  /** Send an error notification */
  error: (title: string, body?: string) => Notification | undefined;
  /** Send an info notification */
  info: (title: string, body?: string) => Notification | undefined;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function getPermission(): NotificationPermission {
  if (
    typeof window === "undefined" ||
    !("Notification" in window) ||
    typeof window.Notification === "undefined"
  ) {
    return "denied";
  }
  return Notification.permission as NotificationPermission;
}

function isNotificationSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "Notification" in window &&
    typeof window.Notification !== "undefined"
  );
}

// ==============================================================================
// Hook
// ==============================================================================

export function useNotifications(
  options: UseNotificationsOptions = {},
): NotificationState {
  const { enabled = true, defaultIcon } = options;

  const [permission, setPermission] = useState<NotificationPermission>(() =>
    getPermission(),
  );

  const isSupported = useMemo(() => isNotificationSupported(), []);

  // Request permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!isSupported) {
      return false;
    }

    // Already granted
    if (Notification.permission === "granted") {
      return true;
    }

    // Already denied (can't re-request)
    if (Notification.permission === "denied") {
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result as NotificationPermission);
      return result === "granted";
    } catch {
      return false;
    }
  }, [isSupported]);

  // Send notification
  const notify = useCallback(
    (
      title: string,
      notificationOptions: NotificationOptions = {},
    ): Notification | undefined => {
      if (!isSupported) {
        return undefined;
      }

      if (!enabled) {
        return undefined;
      }

      if (Notification.permission !== "granted") {
        return undefined;
      }

      const options: NotificationOptions = {
        ...notificationOptions,
      };

      if (defaultIcon && !options.icon) {
        options.icon = defaultIcon;
      }

      return new Notification(title, options);
    },
    [isSupported, enabled, defaultIcon],
  );

  // Success notification
  const success = useCallback(
    (title: string, body?: string): Notification | undefined => {
      return notify(title, { body, tag: "success" });
    },
    [notify],
  );

  // Error notification
  const error = useCallback(
    (title: string, body?: string): Notification | undefined => {
      return notify(title, { body, tag: "error" });
    },
    [notify],
  );

  // Info notification
  const info = useCallback(
    (title: string, body?: string): Notification | undefined => {
      return notify(title, { body, tag: "info" });
    },
    [notify],
  );

  return {
    permission,
    isSupported,
    requestPermission,
    notify,
    success,
    error,
    info,
  };
}

export default useNotifications;
