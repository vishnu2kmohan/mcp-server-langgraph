/**
 * Notification Slice Tests
 *
 * TDD tests for the notification Redux slice.
 * Features:
 * - Add notifications (info, success, warning, error)
 * - Mark notifications as read
 * - Remove notifications
 * - Clear all notifications
 * - Unread count selector
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import notificationReducer, {
  addNotification,
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearNotifications,
  selectNotifications,
  selectUnreadCount,
  selectUnreadNotifications,
  type Notification,
} from "./notificationSlice";

// Create test store
const createTestStore = (initialNotifications: Notification[] = []) => {
  return configureStore({
    reducer: {
      notifications: notificationReducer,
    },
    preloadedState: {
      notifications: {
        notifications: initialNotifications,
      },
    },
  });
};

describe("notificationSlice", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("addNotification", () => {
    it("should add a notification with generated id and timestamp", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "info",
          title: "Test Notification",
          message: "This is a test message",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe("info");
      expect(notifications[0].title).toBe("Test Notification");
      expect(notifications[0].message).toBe("This is a test message");
      expect(notifications[0].read).toBe(false);
      expect(notifications[0].id).toBeDefined();
      expect(notifications[0].createdAt).toBeDefined();
    });

    it("should add info notification", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "info",
          title: "Info",
          message: "Information message",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].type).toBe("info");
    });

    it("should add success notification", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "success",
          title: "Success",
          message: "Operation completed",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].type).toBe("success");
    });

    it("should add warning notification", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "warning",
          title: "Warning",
          message: "Please be careful",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].type).toBe("warning");
    });

    it("should add error notification", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "error",
          title: "Error",
          message: "Something went wrong",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].type).toBe("error");
    });

    it("should add notification with optional action", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "info",
          title: "With Action",
          message: "Click to proceed",
          action: {
            label: "Click Me",
            href: "/some/path",
          },
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].action).toBeDefined();
      expect(notifications[0].action?.label).toBe("Click Me");
      expect(notifications[0].action?.href).toBe("/some/path");
    });

    it("should prepend new notifications (newest first)", () => {
      const store = createTestStore();

      store.dispatch(
        addNotification({
          type: "info",
          title: "First",
          message: "First notification",
        }),
      );

      store.dispatch(
        addNotification({
          type: "info",
          title: "Second",
          message: "Second notification",
        }),
      );

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications).toHaveLength(2);
      expect(notifications[0].title).toBe("Second");
      expect(notifications[1].title).toBe("First");
    });
  });

  describe("markAsRead", () => {
    it("should mark a notification as read", () => {
      const notification: Notification = {
        id: "test-1",
        type: "info",
        title: "Test",
        message: "Test message",
        read: false,
        createdAt: new Date().toISOString(),
      };
      const store = createTestStore([notification]);

      store.dispatch(markAsRead("test-1"));

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].read).toBe(true);
    });

    it("should not affect other notifications", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-2",
          type: "info",
          title: "Second",
          message: "Second",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(markAsRead("test-1"));

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications[0].read).toBe(true);
      expect(currentNotifications[1].read).toBe(false);
    });

    it("should handle non-existent notification id gracefully", () => {
      const notification: Notification = {
        id: "test-1",
        type: "info",
        title: "Test",
        message: "Test message",
        read: false,
        createdAt: new Date().toISOString(),
      };
      const store = createTestStore([notification]);

      store.dispatch(markAsRead("non-existent"));

      const state = store.getState();
      const notifications = selectNotifications(state);

      expect(notifications[0].read).toBe(false);
    });
  });

  describe("markAllAsRead", () => {
    it("should mark all notifications as read", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-2",
          type: "info",
          title: "Second",
          message: "Second",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-3",
          type: "info",
          title: "Third",
          message: "Third",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(markAllAsRead());

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications.every((n) => n.read)).toBe(true);
    });

    it("should not change already read notifications", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: true,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-2",
          type: "info",
          title: "Second",
          message: "Second",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(markAllAsRead());

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications.every((n) => n.read)).toBe(true);
    });
  });

  describe("removeNotification", () => {
    it("should remove a notification by id", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-2",
          type: "info",
          title: "Second",
          message: "Second",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(removeNotification("test-1"));

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications).toHaveLength(1);
      expect(currentNotifications[0].id).toBe("test-2");
    });

    it("should handle non-existent notification id gracefully", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: false,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(removeNotification("non-existent"));

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications).toHaveLength(1);
    });
  });

  describe("clearNotifications", () => {
    it("should clear all notifications", () => {
      const notifications: Notification[] = [
        {
          id: "test-1",
          type: "info",
          title: "First",
          message: "First",
          read: false,
          createdAt: new Date().toISOString(),
        },
        {
          id: "test-2",
          type: "info",
          title: "Second",
          message: "Second",
          read: true,
          createdAt: new Date().toISOString(),
        },
      ];
      const store = createTestStore(notifications);

      store.dispatch(clearNotifications());

      const state = store.getState();
      const currentNotifications = selectNotifications(state);

      expect(currentNotifications).toHaveLength(0);
    });
  });

  describe("Selectors", () => {
    describe("selectNotifications", () => {
      it("should return all notifications", () => {
        const notifications: Notification[] = [
          {
            id: "test-1",
            type: "info",
            title: "First",
            message: "First",
            read: false,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-2",
            type: "info",
            title: "Second",
            message: "Second",
            read: true,
            createdAt: new Date().toISOString(),
          },
        ];
        const store = createTestStore(notifications);

        const state = store.getState();
        const result = selectNotifications(state);

        expect(result).toHaveLength(2);
      });
    });

    describe("selectUnreadCount", () => {
      it("should return count of unread notifications", () => {
        const notifications: Notification[] = [
          {
            id: "test-1",
            type: "info",
            title: "First",
            message: "First",
            read: false,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-2",
            type: "info",
            title: "Second",
            message: "Second",
            read: true,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-3",
            type: "info",
            title: "Third",
            message: "Third",
            read: false,
            createdAt: new Date().toISOString(),
          },
        ];
        const store = createTestStore(notifications);

        const state = store.getState();
        const count = selectUnreadCount(state);

        expect(count).toBe(2);
      });

      it("should return 0 when all are read", () => {
        const notifications: Notification[] = [
          {
            id: "test-1",
            type: "info",
            title: "First",
            message: "First",
            read: true,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-2",
            type: "info",
            title: "Second",
            message: "Second",
            read: true,
            createdAt: new Date().toISOString(),
          },
        ];
        const store = createTestStore(notifications);

        const state = store.getState();
        const count = selectUnreadCount(state);

        expect(count).toBe(0);
      });

      it("should return 0 when there are no notifications", () => {
        const store = createTestStore([]);

        const state = store.getState();
        const count = selectUnreadCount(state);

        expect(count).toBe(0);
      });
    });

    describe("selectUnreadNotifications", () => {
      it("should return only unread notifications", () => {
        const notifications: Notification[] = [
          {
            id: "test-1",
            type: "info",
            title: "First",
            message: "First",
            read: false,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-2",
            type: "info",
            title: "Second",
            message: "Second",
            read: true,
            createdAt: new Date().toISOString(),
          },
          {
            id: "test-3",
            type: "info",
            title: "Third",
            message: "Third",
            read: false,
            createdAt: new Date().toISOString(),
          },
        ];
        const store = createTestStore(notifications);

        const state = store.getState();
        const unread = selectUnreadNotifications(state);

        expect(unread).toHaveLength(2);
        expect(unread.every((n) => !n.read)).toBe(true);
      });
    });
  });
});
