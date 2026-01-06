/**
 * UI Slice Tests
 *
 * TDD tests for the UI state slice.
 * Tests cover:
 * - Sidebar toggle
 * - Theme setting
 * - Loading state
 * - Active view
 * - Notifications
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import uiReducer, {
  toggleSidebar,
  setSidebarOpen,
  toggleSidebarCollapsed,
  setSidebarCollapsed,
  setTheme,
  setLoading,
  setActiveView,
  addNotification,
  removeNotification,
  clearNotifications,
  getInitialTheme,
  selectSidebarCollapsed,
  selectTheme,
  selectSidebarOpen,
  setSubmitOnEnter,
  selectSubmitOnEnter,
} from "./uiSlice";

// Mock crypto.randomUUID
const mockUUID = "12345678-1234-1234-1234-123456789abc";
vi.stubGlobal("crypto", {
  randomUUID: () => mockUUID,
});

describe("uiSlice", () => {
  // Default theme is now "dark" instead of "system"
  const initialState = {
    sidebarOpen: true,
    theme: "dark" as const,
    isLoading: false,
    activeView: "workflows" as const,
    notifications: [],
    sidebarCollapsed: false,
    submitOnEnter: true, // Sprint 5.1: ChatGPT-style Enter to send
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("should return initial state when called with undefined", () => {
      const result = uiReducer(undefined, { type: "unknown" });
      expect(result).toEqual(initialState);
    });
  });

  describe("toggleSidebar", () => {
    it("should toggle sidebar from open to closed", () => {
      const state = { ...initialState, sidebarOpen: true };
      const result = uiReducer(state, toggleSidebar());
      expect(result.sidebarOpen).toBe(false);
    });

    it("should toggle sidebar from closed to open", () => {
      const state = { ...initialState, sidebarOpen: false };
      const result = uiReducer(state, toggleSidebar());
      expect(result.sidebarOpen).toBe(true);
    });
  });

  describe("setSidebarOpen", () => {
    it("should set sidebar to open", () => {
      const state = { ...initialState, sidebarOpen: false };
      const result = uiReducer(state, setSidebarOpen(true));
      expect(result.sidebarOpen).toBe(true);
    });

    it("should set sidebar to closed", () => {
      const state = { ...initialState, sidebarOpen: true };
      const result = uiReducer(state, setSidebarOpen(false));
      expect(result.sidebarOpen).toBe(false);
    });
  });

  describe("toggleSidebarCollapsed", () => {
    it("should toggle collapsed from false to true", () => {
      const state = { ...initialState, sidebarCollapsed: false };
      const result = uiReducer(state, toggleSidebarCollapsed());
      expect(result.sidebarCollapsed).toBe(true);
    });

    it("should toggle collapsed from true to false", () => {
      const state = { ...initialState, sidebarCollapsed: true };
      const result = uiReducer(state, toggleSidebarCollapsed());
      expect(result.sidebarCollapsed).toBe(false);
    });

    it("should persist to localStorage", () => {
      const state = { ...initialState, sidebarCollapsed: false };
      uiReducer(state, toggleSidebarCollapsed());
      expect(localStorage.getItem("studio-sidebar-collapsed")).toBe("true");
    });
  });

  describe("setSidebarCollapsed", () => {
    it("should set collapsed to true", () => {
      const state = { ...initialState, sidebarCollapsed: false };
      const result = uiReducer(state, setSidebarCollapsed(true));
      expect(result.sidebarCollapsed).toBe(true);
    });

    it("should set collapsed to false", () => {
      const state = { ...initialState, sidebarCollapsed: true };
      const result = uiReducer(state, setSidebarCollapsed(false));
      expect(result.sidebarCollapsed).toBe(false);
    });

    it("should persist to localStorage", () => {
      const state = { ...initialState, sidebarCollapsed: false };
      uiReducer(state, setSidebarCollapsed(true));
      expect(localStorage.getItem("studio-sidebar-collapsed")).toBe("true");
    });
  });

  describe("setTheme", () => {
    it("should set theme to light", () => {
      const result = uiReducer(initialState, setTheme("light"));
      expect(result.theme).toBe("light");
    });

    it("should set theme to dark", () => {
      const result = uiReducer(initialState, setTheme("dark"));
      expect(result.theme).toBe("dark");
    });

    it("should set theme to system", () => {
      const state = { ...initialState, theme: "dark" as const };
      const result = uiReducer(state, setTheme("system"));
      expect(result.theme).toBe("system");
    });
  });

  describe("getInitialTheme", () => {
    it("should be exported and callable", () => {
      // getInitialTheme function should be exported
      expect(typeof getInitialTheme).toBe("function");
    });

    it("should return a valid theme value", () => {
      const result = getInitialTheme();
      expect(["light", "dark", "system"]).toContain(result);
    });

    it("should default to dark when localStorage has no theme", () => {
      // Clear any existing theme
      localStorage.removeItem("theme");
      // The function reads from localStorage
      const result = getInitialTheme();
      expect(result).toBe("dark");
    });

    it("should return light theme when stored in localStorage", () => {
      localStorage.setItem("studio-theme", "light");
      const result = getInitialTheme();
      expect(result).toBe("light");
      localStorage.removeItem("studio-theme");
    });

    it("should return system theme when stored in localStorage", () => {
      localStorage.setItem("studio-theme", "system");
      const result = getInitialTheme();
      expect(result).toBe("system");
      localStorage.removeItem("studio-theme");
    });
  });

  describe("setLoading", () => {
    it("should set loading to true", () => {
      const result = uiReducer(initialState, setLoading(true));
      expect(result.isLoading).toBe(true);
    });

    it("should set loading to false", () => {
      const state = { ...initialState, isLoading: true };
      const result = uiReducer(state, setLoading(false));
      expect(result.isLoading).toBe(false);
    });
  });

  describe("setActiveView", () => {
    it("should set active view to workflows", () => {
      const state = { ...initialState, activeView: "sessions" as const };
      const result = uiReducer(state, setActiveView("workflows"));
      expect(result.activeView).toBe("workflows");
    });

    it("should set active view to sessions", () => {
      const result = uiReducer(initialState, setActiveView("sessions"));
      expect(result.activeView).toBe("sessions");
    });

    it("should set active view to chat", () => {
      const result = uiReducer(initialState, setActiveView("chat"));
      expect(result.activeView).toBe("chat");
    });

    it("should set active view to cost", () => {
      const result = uiReducer(initialState, setActiveView("cost"));
      expect(result.activeView).toBe("cost");
    });

    it("should set active view to observability", () => {
      const result = uiReducer(initialState, setActiveView("observability"));
      expect(result.activeView).toBe("observability");
    });
  });

  describe("addNotification", () => {
    it("should add info notification", () => {
      const notification = { type: "info" as const, message: "Test info" };
      const result = uiReducer(initialState, addNotification(notification));

      expect(result.notifications).toHaveLength(1);
      expect(result.notifications[0].type).toBe("info");
      expect(result.notifications[0].message).toBe("Test info");
      expect(result.notifications[0].id).toBe(mockUUID);
      expect(typeof result.notifications[0].timestamp).toBe("number");
    });

    it("should add success notification", () => {
      const notification = { type: "success" as const, message: "Success!" };
      const result = uiReducer(initialState, addNotification(notification));

      expect(result.notifications[0].type).toBe("success");
    });

    it("should add warning notification", () => {
      const notification = { type: "warning" as const, message: "Warning!" };
      const result = uiReducer(initialState, addNotification(notification));

      expect(result.notifications[0].type).toBe("warning");
    });

    it("should add error notification", () => {
      const notification = { type: "error" as const, message: "Error!" };
      const result = uiReducer(initialState, addNotification(notification));

      expect(result.notifications[0].type).toBe("error");
    });

    it("should append to existing notifications", () => {
      const stateWithNotification = {
        ...initialState,
        notifications: [
          {
            id: "existing",
            type: "info" as const,
            message: "Existing",
            timestamp: 1000,
          },
        ],
      };
      const result = uiReducer(
        stateWithNotification,
        addNotification({ type: "success", message: "New" }),
      );

      expect(result.notifications).toHaveLength(2);
    });
  });

  describe("removeNotification", () => {
    it("should remove notification by id", () => {
      const stateWithNotifications = {
        ...initialState,
        notifications: [
          { id: "a", type: "info" as const, message: "A", timestamp: 1000 },
          { id: "b", type: "success" as const, message: "B", timestamp: 1001 },
        ],
      };
      const result = uiReducer(stateWithNotifications, removeNotification("a"));

      expect(result.notifications).toHaveLength(1);
      expect(result.notifications[0].id).toBe("b");
    });

    it("should do nothing if id not found", () => {
      const stateWithNotifications = {
        ...initialState,
        notifications: [
          { id: "a", type: "info" as const, message: "A", timestamp: 1000 },
        ],
      };
      const result = uiReducer(
        stateWithNotifications,
        removeNotification("nonexistent"),
      );

      expect(result.notifications).toHaveLength(1);
    });
  });

  describe("clearNotifications", () => {
    it("should clear all notifications", () => {
      const stateWithNotifications = {
        ...initialState,
        notifications: [
          { id: "a", type: "info" as const, message: "A", timestamp: 1000 },
          { id: "b", type: "success" as const, message: "B", timestamp: 1001 },
          { id: "c", type: "error" as const, message: "C", timestamp: 1002 },
        ],
      };
      const result = uiReducer(stateWithNotifications, clearNotifications());

      expect(result.notifications).toHaveLength(0);
    });

    it("should work on empty notifications", () => {
      const result = uiReducer(initialState, clearNotifications());
      expect(result.notifications).toHaveLength(0);
    });
  });

  describe("Selectors", () => {
    const mockState = {
      ui: {
        sidebarOpen: true,
        sidebarCollapsed: true,
        theme: "light" as const,
        isLoading: false,
        activeView: "workflows" as const,
        notifications: [],
        submitOnEnter: true,
      },
    };

    it("selectSidebarCollapsed should return sidebarCollapsed state", () => {
      expect(selectSidebarCollapsed(mockState)).toBe(true);
    });

    it("selectTheme should return theme state", () => {
      expect(selectTheme(mockState)).toBe("light");
    });

    it("selectSidebarOpen should return sidebarOpen state", () => {
      expect(selectSidebarOpen(mockState)).toBe(true);
    });

    it("selectSubmitOnEnter should return submitOnEnter state", () => {
      expect(selectSubmitOnEnter(mockState)).toBe(true);
    });
  });

  describe("setSubmitOnEnter", () => {
    it("should set submitOnEnter to false", () => {
      const state = { ...initialState, submitOnEnter: true };
      const result = uiReducer(state, setSubmitOnEnter(false));
      expect(result.submitOnEnter).toBe(false);
    });

    it("should set submitOnEnter to true", () => {
      const state = { ...initialState, submitOnEnter: false };
      const result = uiReducer(state, setSubmitOnEnter(true));
      expect(result.submitOnEnter).toBe(true);
    });
  });
});
