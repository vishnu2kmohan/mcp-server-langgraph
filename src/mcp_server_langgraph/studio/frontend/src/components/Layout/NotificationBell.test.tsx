/**
 * NotificationBell Component Tests
 *
 * TDD tests for the notification bell dropdown component.
 * Features:
 * - Bell icon with unread count badge
 * - Dropdown panel with notification list
 * - Mark as read / Mark all as read
 * - Remove individual notifications
 * - Navigate to notification action
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { NotificationBell } from "./NotificationBell";
import notificationReducer, {
  type Notification,
} from "../../store/slices/notificationSlice";
import { TestRouter } from "../../test-utils";

// Mock navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Create test store
const createTestStore = (notifications: Notification[] = []) => {
  return configureStore({
    reducer: {
      notifications: notificationReducer,
    },
    preloadedState: {
      notifications: {
        notifications,
      },
    },
  });
};

const renderWithProviders = (notifications: Notification[] = []) => {
  const store = createTestStore(notifications);
  return {
    store,
    ...render(
      <Provider store={store}>
        <TestRouter>
          <NotificationBell />
        </TestRouter>
      </Provider>,
    ),
  };
};

// Sample notifications
const sampleNotifications: Notification[] = [
  {
    id: "n1",
    type: "info",
    title: "New Message",
    message: "You have a new message from the system",
    read: false,
    createdAt: new Date().toISOString(),
  },
  {
    id: "n2",
    type: "success",
    title: "Workflow Complete",
    message: "Your workflow finished successfully",
    read: false,
    createdAt: new Date().toISOString(),
    action: {
      label: "View Results",
      href: "/studio/workflows/123",
    },
  },
  {
    id: "n3",
    type: "warning",
    title: "Warning",
    message: "API rate limit approaching",
    read: true,
    createdAt: new Date().toISOString(),
  },
];

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Bell Icon", () => {
    it("should render the bell icon button", () => {
      renderWithProviders();
      expect(
        screen.getByRole("button", { name: /notifications/i }),
      ).toBeInTheDocument();
    });

    it("should show unread count badge when there are unread notifications", () => {
      renderWithProviders(sampleNotifications);
      // 2 unread notifications
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("should not show badge when no unread notifications", () => {
      const allRead = sampleNotifications.map((n) => ({ ...n, read: true }));
      renderWithProviders(allRead);
      expect(screen.queryByText("0")).not.toBeInTheDocument();
    });

    it("should show 9+ when more than 9 unread", () => {
      const manyUnread = Array.from({ length: 12 }, (_, i) => ({
        id: `n${i}`,
        type: "info" as const,
        title: `Notification ${i}`,
        message: `Message ${i}`,
        read: false,
        createdAt: new Date().toISOString(),
      }));
      renderWithProviders(manyUnread);
      expect(screen.getByText("9+")).toBeInTheDocument();
    });
  });

  describe("Dropdown Panel", () => {
    it("should be hidden by default", () => {
      renderWithProviders(sampleNotifications);
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("should open when bell is clicked", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });
    });

    it("should close when clicking outside", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Click outside (on body)
      fireEvent.mouseDown(document.body);

      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
    });

    it('should display "No notifications" when empty', async () => {
      renderWithProviders([]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText(/no notifications/i)).toBeInTheDocument();
      });
    });

    it("should show notification list header with title", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("Notifications")).toBeInTheDocument();
      });
    });
  });

  describe("Notification Items", () => {
    it("should display notification title and message", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
        expect(
          screen.getByText("You have a new message from the system"),
        ).toBeInTheDocument();
      });
    });

    it("should show unread indicator for unread notifications", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        // Should have 2 unread indicators (dots)
        const unreadDots = screen.getAllByTestId("unread-indicator");
        expect(unreadDots.length).toBe(2);
      });
    });

    it("should show action button when notification has action", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "View Results" }),
        ).toBeInTheDocument();
      });
    });

    it("should navigate when action button is clicked", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "View Results" }),
        ).toBeInTheDocument();
      });

      const actionButton = screen.getByRole("button", { name: "View Results" });
      fireEvent.click(actionButton);

      expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows/123");
    });

    it("should have remove button for each notification", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        const removeButtons = screen.getAllByRole("button", {
          name: /remove/i,
        });
        expect(removeButtons.length).toBe(3);
      });
    });

    it("should remove notification when remove button is clicked", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByRole("button", { name: /remove/i });
      fireEvent.click(removeButtons[0]);

      // Check store was updated
      const state = store.getState();
      expect(state.notifications.notifications.length).toBe(2);
    });
  });

  describe("Mark as Read", () => {
    it("should mark notification as read when clicked", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      // Click on the notification item (now a div with role="menuitem")
      const notificationItem = screen
        .getByText("New Message")
        .closest('[role="menuitem"]');
      if (notificationItem) {
        fireEvent.click(notificationItem);
      }

      // Check store was updated
      const state = store.getState();
      const notification = state.notifications.notifications.find(
        (n) => n.id === "n1",
      );
      expect(notification?.read).toBe(true);
    });

    it('should show "Mark all as read" button when there are unread notifications', async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /mark all as read/i }),
        ).toBeInTheDocument();
      });
    });

    it("should mark all as read when button is clicked", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /mark all as read/i }),
        ).toBeInTheDocument();
      });

      const markAllButton = screen.getByRole("button", {
        name: /mark all as read/i,
      });
      fireEvent.click(markAllButton);

      // Check all are read
      const state = store.getState();
      expect(state.notifications.notifications.every((n) => n.read)).toBe(true);
    });

    it('should hide "Mark all as read" when all are read', async () => {
      const allRead = sampleNotifications.map((n) => ({ ...n, read: true }));
      renderWithProviders(allRead);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      expect(
        screen.queryByRole("button", { name: /mark all as read/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Notification Types", () => {
    it("should show info icon for info notifications", async () => {
      renderWithProviders([sampleNotifications[0]]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByTestId("notification-icon-info"),
        ).toBeInTheDocument();
      });
    });

    it("should show success icon for success notifications", async () => {
      renderWithProviders([sampleNotifications[1]]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByTestId("notification-icon-success"),
        ).toBeInTheDocument();
      });
    });

    it("should show warning icon for warning notifications", async () => {
      const warningNotification = {
        id: "w1",
        type: "warning" as const,
        title: "Warning",
        message: "Test warning",
        read: false,
        createdAt: new Date().toISOString(),
      };
      renderWithProviders([warningNotification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByTestId("notification-icon-warning"),
        ).toBeInTheDocument();
      });
    });

    it("should show error icon for error notifications", async () => {
      const errorNotification = {
        id: "e1",
        type: "error" as const,
        title: "Error",
        message: "Test error",
        read: false,
        createdAt: new Date().toISOString(),
      };
      renderWithProviders([errorNotification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByTestId("notification-icon-error"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Time Formatting", () => {
    it('should show "Just now" for notifications less than a minute old', async () => {
      const recentNotification = {
        id: "recent",
        type: "info" as const,
        title: "Recent",
        message: "Just happened",
        read: false,
        createdAt: new Date().toISOString(),
      };
      renderWithProviders([recentNotification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText(/just now/i)).toBeInTheDocument();
      });
    });

    it("should show minutes ago for notifications less than an hour old", async () => {
      const minutesAgo = new Date(Date.now() - 5 * 60 * 1000); // 5 minutes ago
      const notification = {
        id: "mins",
        type: "info" as const,
        title: "Minutes Ago",
        message: "Test",
        read: false,
        createdAt: minutesAgo.toISOString(),
      };
      renderWithProviders([notification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText(/5m ago/i)).toBeInTheDocument();
      });
    });

    it("should show hours ago for notifications less than a day old", async () => {
      const hoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000); // 3 hours ago
      const notification = {
        id: "hours",
        type: "info" as const,
        title: "Hours Ago",
        message: "Test",
        read: false,
        createdAt: hoursAgo.toISOString(),
      };
      renderWithProviders([notification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText(/3h ago/i)).toBeInTheDocument();
      });
    });

    it("should show days ago for notifications less than a week old", async () => {
      const daysAgo = new Date(Date.now() - 4 * 24 * 60 * 60 * 1000); // 4 days ago
      const notification = {
        id: "days",
        type: "info" as const,
        title: "Days Ago",
        message: "Test",
        read: false,
        createdAt: daysAgo.toISOString(),
      };
      renderWithProviders([notification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText(/4d ago/i)).toBeInTheDocument();
      });
    });

    it("should show formatted date for notifications older than a week", async () => {
      const weeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000); // 14 days ago
      const notification = {
        id: "old",
        type: "info" as const,
        title: "Old Notification",
        message: "Test",
        read: false,
        createdAt: weeksAgo.toISOString(),
      };
      renderWithProviders([notification]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        // Should show formatted date like "12/7/2025" or similar
        expect(screen.queryByText(/ago/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Keyboard Navigation", () => {
    it("should mark notification as read on Enter key press", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      const notificationItem = screen
        .getByText("New Message")
        .closest('[role="menuitem"]');
      if (notificationItem) {
        fireEvent.keyDown(notificationItem, { key: "Enter" });
      }

      const state = store.getState();
      const notification = state.notifications.notifications.find(
        (n) => n.id === "n1",
      );
      expect(notification?.read).toBe(true);
    });

    it("should mark notification as read on Space key press", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      const notificationItem = screen
        .getByText("New Message")
        .closest('[role="menuitem"]');
      if (notificationItem) {
        fireEvent.keyDown(notificationItem, { key: " " });
      }

      const state = store.getState();
      const notification = state.notifications.notifications.find(
        (n) => n.id === "n1",
      );
      expect(notification?.read).toBe(true);
    });

    it("should not mark as read on other key presses", async () => {
      const { store } = renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      const notificationItem = screen
        .getByText("New Message")
        .closest('[role="menuitem"]');
      if (notificationItem) {
        fireEvent.keyDown(notificationItem, { key: "Tab" });
      }

      const state = store.getState();
      const notification = state.notifications.notifications.find(
        (n) => n.id === "n1",
      );
      expect(notification?.read).toBe(false);
    });
  });

  describe("Already Read Notifications", () => {
    it("should not dispatch markAsRead when clicking already-read notification", async () => {
      const allRead = sampleNotifications.map((n) => ({ ...n, read: true }));
      const { store } = renderWithProviders(allRead);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByText("New Message")).toBeInTheDocument();
      });

      // Get initial state
      const initialState = store.getState();

      const notificationItem = screen
        .getByText("New Message")
        .closest('[role="menuitem"]');
      if (notificationItem) {
        fireEvent.click(notificationItem);
      }

      // State should be unchanged
      const newState = store.getState();
      expect(newState.notifications).toEqual(initialState.notifications);
    });
  });

  describe("Action Callbacks", () => {
    it("should call onClick callback when action has onClick", async () => {
      const onClickMock = vi.fn();
      const notificationWithCallback = {
        id: "cb1",
        type: "info" as const,
        title: "Callback Test",
        message: "Test message",
        read: false,
        createdAt: new Date().toISOString(),
        action: {
          label: "Do Action",
          onClick: onClickMock,
        },
      };
      renderWithProviders([notificationWithCallback]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "Do Action" }),
        ).toBeInTheDocument();
      });

      const actionButton = screen.getByRole("button", { name: "Do Action" });
      fireEvent.click(actionButton);

      expect(onClickMock).toHaveBeenCalled();
    });

    it("should call both navigate and onClick when action has both", async () => {
      const onClickMock = vi.fn();
      const notificationWithBoth = {
        id: "both1",
        type: "info" as const,
        title: "Both Test",
        message: "Test message",
        read: false,
        createdAt: new Date().toISOString(),
        action: {
          label: "Do Both",
          href: "/studio/test",
          onClick: onClickMock,
        },
      };
      renderWithProviders([notificationWithBoth]);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: "Do Both" }),
        ).toBeInTheDocument();
      });

      const actionButton = screen.getByRole("button", { name: "Do Both" });
      fireEvent.click(actionButton);

      expect(mockNavigate).toHaveBeenCalledWith("/studio/test");
      expect(onClickMock).toHaveBeenCalled();
    });
  });

  describe("Click Outside Behavior", () => {
    it("should not close when clicking inside the panel", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Click inside the panel (on the header)
      const header = screen.getByText("Notifications");
      fireEvent.mouseDown(header);

      // Panel should still be open
      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("should not close when clicking on the bell button while open", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Mousedown on the bell button
      fireEvent.mouseDown(bellButton);

      // The handleClickOutside should not close because click is on buttonRef
      // Panel may still be open
      expect(screen.getByRole("menu")).toBeInTheDocument();
    });
  });

  describe("Toggle Behavior", () => {
    it("should toggle panel closed when clicking bell while open", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Click bell again to close
      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
    });
  });

  describe("ARIA Attributes", () => {
    it("should have proper aria-expanded state", async () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      expect(bellButton).toHaveAttribute("aria-expanded", "false");

      fireEvent.click(bellButton);

      await waitFor(() => {
        expect(bellButton).toHaveAttribute("aria-expanded", "true");
      });
    });

    it("should have aria-haspopup attribute", () => {
      renderWithProviders(sampleNotifications);

      const bellButton = screen.getByRole("button", { name: /notifications/i });
      expect(bellButton).toHaveAttribute("aria-haspopup", "true");
    });
  });
});
