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
});
