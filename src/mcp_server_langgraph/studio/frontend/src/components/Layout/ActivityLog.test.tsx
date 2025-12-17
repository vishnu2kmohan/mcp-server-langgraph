/**
 * ActivityLog Component Tests
 *
 * TDD tests for the activity log panel component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ActivityLog } from "./ActivityLog";
import notificationReducer from "../../store/slices/notificationSlice";

// Create test store
const createTestStore = (
  notifications: Array<{
    id: string;
    type: "info" | "success" | "warning" | "error";
    title: string;
    message: string;
    createdAt: string;
  }> = [],
) => {
  return configureStore({
    reducer: {
      notifications: notificationReducer,
    },
    preloadedState: {
      notifications: {
        notifications,
        unreadCount: notifications.length,
      },
    },
  });
};

const renderWithProviders = (
  ui: React.ReactElement,
  notifications: Array<{
    id: string;
    type: "info" | "success" | "warning" | "error";
    title: string;
    message: string;
    createdAt: string;
  }> = [],
) => {
  const store = createTestStore(notifications);
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

describe("ActivityLog", () => {
  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<ActivityLog />);
      expect(screen.getByTestId("activity-log")).toBeInTheDocument();
    });

    it("should show empty state when no notifications", () => {
      renderWithProviders(<ActivityLog />);
      expect(screen.getByText(/no recent activity/i)).toBeInTheDocument();
    });

    it("should display notifications when present", () => {
      const notifications = [
        {
          id: "1",
          type: "info" as const,
          title: "Test Notification",
          message: "This is a test message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      expect(screen.getByText("Test Notification")).toBeInTheDocument();
    });

    it("should limit displayed notifications to maxItems prop", () => {
      const notifications = Array.from({ length: 15 }, (_, i) => ({
        id: String(i),
        type: "info" as const,
        title: `Notification ${i}`,
        message: `Message ${i}`,
        createdAt: new Date().toISOString(),
      }));
      renderWithProviders(<ActivityLog maxItems={5} />, notifications);

      // Should only show 5 items
      expect(screen.getByText("Notification 0")).toBeInTheDocument();
      expect(screen.getByText("Notification 4")).toBeInTheDocument();
      expect(screen.queryByText("Notification 5")).not.toBeInTheDocument();
    });
  });

  describe("Notification Types", () => {
    it("should render success notification with correct styling", () => {
      const notifications = [
        {
          id: "1",
          type: "success" as const,
          title: "Success",
          message: "Operation completed",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      expect(screen.getByTestId("activity-item-1")).toBeInTheDocument();
    });

    it("should render error notification with correct styling", () => {
      const notifications = [
        {
          id: "1",
          type: "error" as const,
          title: "Error",
          message: "Something went wrong",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      expect(screen.getByTestId("activity-item-1")).toBeInTheDocument();
    });

    it("should render warning notification with correct styling", () => {
      const notifications = [
        {
          id: "1",
          type: "warning" as const,
          title: "Warning",
          message: "Be careful",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      expect(screen.getByTestId("activity-item-1")).toBeInTheDocument();
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<ActivityLog className="custom-class" />);
      expect(screen.getByTestId("activity-log")).toHaveClass("custom-class");
    });

    it("should accept compact prop for reduced spacing", () => {
      renderWithProviders(<ActivityLog compact />);
      expect(screen.getByTestId("activity-log")).toHaveClass("p-2");
    });
  });
});
