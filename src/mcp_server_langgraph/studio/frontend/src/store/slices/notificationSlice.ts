/**
 * Notification Slice
 *
 * Redux slice for managing application notifications.
 * Features:
 * - Add notifications (info, success, warning, error)
 * - Mark notifications as read
 * - Remove notifications
 * - Clear all notifications
 * - Selectors for unread count and filtered lists
 */

import { createSlice, PayloadAction, nanoid } from "@reduxjs/toolkit";

/**
 * Notification types
 */
export type NotificationType = "info" | "success" | "warning" | "error";

/**
 * Notification action (optional link/button)
 */
export interface NotificationAction {
  label: string;
  href?: string;
  onClick?: () => void;
}

/**
 * Notification data structure
 */
export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  action?: NotificationAction;
}

/**
 * Payload for adding a notification
 */
export interface AddNotificationPayload {
  type: NotificationType;
  title: string;
  message: string;
  action?: NotificationAction;
}

/**
 * Notification state
 */
interface NotificationState {
  notifications: Notification[];
}

const initialState: NotificationState = {
  notifications: [],
};

/**
 * Notification slice
 */
const notificationSlice = createSlice({
  name: "notifications",
  initialState,
  reducers: {
    /**
     * Add a new notification (newest first)
     */
    addNotification: {
      reducer: (state, action: PayloadAction<Notification>) => {
        state.notifications.unshift(action.payload);
      },
      prepare: (payload: AddNotificationPayload) => ({
        payload: {
          id: nanoid(),
          type: payload.type,
          title: payload.title,
          message: payload.message,
          read: false,
          createdAt: new Date().toISOString(),
          action: payload.action,
        },
      }),
    },

    /**
     * Mark a specific notification as read
     */
    markAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(
        (n) => n.id === action.payload,
      );
      if (notification) {
        notification.read = true;
      }
    },

    /**
     * Mark all notifications as read
     */
    markAllAsRead: (state) => {
      state.notifications.forEach((n) => {
        n.read = true;
      });
    },

    /**
     * Remove a notification by id
     */
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (n) => n.id !== action.payload,
      );
    },

    /**
     * Clear all notifications
     */
    clearNotifications: (state) => {
      state.notifications = [];
    },
  },
});

// Export actions
export const {
  addNotification,
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearNotifications,
} = notificationSlice.actions;

// Export reducer
export default notificationSlice.reducer;

// Selectors
interface RootState {
  notifications: NotificationState;
}

/**
 * Select all notifications
 */
export const selectNotifications = (state: RootState): Notification[] =>
  state.notifications.notifications;

/**
 * Select count of unread notifications
 */
export const selectUnreadCount = (state: RootState): number =>
  state.notifications.notifications.filter((n) => !n.read).length;

/**
 * Select only unread notifications
 */
export const selectUnreadNotifications = (state: RootState): Notification[] =>
  state.notifications.notifications.filter((n) => !n.read);
