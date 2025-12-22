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

    it("should use p-4 padding in non-compact mode", () => {
      renderWithProviders(<ActivityLog compact={false} />);
      expect(screen.getByTestId("activity-log")).toHaveClass("p-4");
    });

    it("should render compact activity items with reduced styling", () => {
      const notifications = [
        {
          id: "1",
          type: "info" as const,
          title: "Compact Notification",
          message: "Compact message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog compact />, notifications);
      const item = screen.getByTestId("activity-item-1");
      expect(item).toHaveClass("p-1.5");
    });

    it("should render non-compact activity items with standard padding", () => {
      const notifications = [
        {
          id: "1",
          type: "info" as const,
          title: "Normal Notification",
          message: "Normal message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog compact={false} />, notifications);
      const item = screen.getByTestId("activity-item-1");
      expect(item).toHaveClass("p-2");
    });
  });

  describe("Notification Types - Icons", () => {
    it("should render info notification (default case) with blue icon", () => {
      const notifications = [
        {
          id: "info-1",
          type: "info" as const,
          title: "Info",
          message: "Information message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      const item = screen.getByTestId("activity-item-info-1");
      expect(item).toBeInTheDocument();
      // The info icon should have text-blue-500 class
      expect(item.querySelector(".text-blue-500")).toBeInTheDocument();
    });

    it("should render success notification with green icon", () => {
      const notifications = [
        {
          id: "success-1",
          type: "success" as const,
          title: "Success",
          message: "Success message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      const item = screen.getByTestId("activity-item-success-1");
      expect(item.querySelector(".text-green-500")).toBeInTheDocument();
    });

    it("should render warning notification with yellow icon", () => {
      const notifications = [
        {
          id: "warning-1",
          type: "warning" as const,
          title: "Warning",
          message: "Warning message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      const item = screen.getByTestId("activity-item-warning-1");
      expect(item.querySelector(".text-yellow-500")).toBeInTheDocument();
    });

    it("should render error notification with red icon", () => {
      const notifications = [
        {
          id: "error-1",
          type: "error" as const,
          title: "Error",
          message: "Error message",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      const item = screen.getByTestId("activity-item-error-1");
      expect(item.querySelector(".text-red-500")).toBeInTheDocument();
    });
  });

  describe("Time Formatting", () => {
    it("should format timestamp as HH:MM", () => {
      const testDate = new Date("2024-01-15T14:30:00");
      const notifications = [
        {
          id: "time-1",
          type: "info" as const,
          title: "Timed Notification",
          message: "Message",
          createdAt: testDate.toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);
      // Should show the time formatted
      const item = screen.getByTestId("activity-item-time-1");
      expect(item).toBeInTheDocument();
      // Time should be visible (format depends on locale, so we just check item renders)
      expect(item).toHaveTextContent(/\d{1,2}:\d{2}/);
    });
  });

  describe("Multiple Notifications", () => {
    it("should render all notification types together", () => {
      const notifications = [
        {
          id: "multi-1",
          type: "success" as const,
          title: "Success Item",
          message: "Success",
          createdAt: new Date().toISOString(),
        },
        {
          id: "multi-2",
          type: "error" as const,
          title: "Error Item",
          message: "Error",
          createdAt: new Date().toISOString(),
        },
        {
          id: "multi-3",
          type: "warning" as const,
          title: "Warning Item",
          message: "Warning",
          createdAt: new Date().toISOString(),
        },
        {
          id: "multi-4",
          type: "info" as const,
          title: "Info Item",
          message: "Info",
          createdAt: new Date().toISOString(),
        },
      ];
      renderWithProviders(<ActivityLog />, notifications);

      expect(screen.getByText("Success Item")).toBeInTheDocument();
      expect(screen.getByText("Error Item")).toBeInTheDocument();
      expect(screen.getByText("Warning Item")).toBeInTheDocument();
      expect(screen.getByText("Info Item")).toBeInTheDocument();
    });

    it("should respect maxItems default of 10", () => {
      const notifications = Array.from({ length: 15 }, (_, i) => ({
        id: `item-${i}`,
        type: "info" as const,
        title: `Title ${i}`,
        message: `Message ${i}`,
        createdAt: new Date().toISOString(),
      }));
      renderWithProviders(<ActivityLog />, notifications);

      // First 10 should be visible
      expect(screen.getByText("Title 0")).toBeInTheDocument();
      expect(screen.getByText("Title 9")).toBeInTheDocument();
      // 11th and beyond should not be visible
      expect(screen.queryByText("Title 10")).not.toBeInTheDocument();
    });
  });
});
