/**
 * UI State Slice
 *
 * Manages global UI state like sidebar visibility, theme, loading states.
 * Uses centralized storage utility for localStorage operations.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { storage, STORAGE_KEYS } from "../../utils/storage";

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean; // Desktop collapse state (shows only icons)
  theme: "light" | "dark" | "system";
  isLoading: boolean;
  activeView: "workflows" | "sessions" | "chat" | "cost" | "observability";
  notifications: Array<{
    id: string;
    type: "info" | "success" | "warning" | "error";
    message: string;
    timestamp: number;
  }>;
}

// Load collapsed state from localStorage using storage utility
const getInitialCollapsedState = (): boolean => {
  const stored = storage.get<boolean>(STORAGE_KEYS.SIDEBAR_COLLAPSED);
  return stored === true;
};

// Load theme from localStorage, defaulting to "dark" for better UX
const getInitialTheme = (): "light" | "dark" | "system" => {
  const stored = storage.get<string>(STORAGE_KEYS.THEME);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "dark"; // Default to dark mode
};

const initialState: UIState = {
  sidebarOpen: true,
  sidebarCollapsed: getInitialCollapsedState(),
  theme: getInitialTheme(),
  isLoading: false,
  activeView: "workflows",
  notifications: [],
};

export const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    toggleSidebarCollapsed: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      // Persist to localStorage using storage utility
      storage.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, state.sidebarCollapsed);
    },
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload;
      // Persist to localStorage using storage utility
      storage.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, state.sidebarCollapsed);
    },
    setTheme: (state, action: PayloadAction<"light" | "dark" | "system">) => {
      state.theme = action.payload;
      // Persist to localStorage using storage utility
      storage.set(STORAGE_KEYS.THEME, action.payload);
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setActiveView: (state, action: PayloadAction<UIState["activeView"]>) => {
      state.activeView = action.payload;
    },
    addNotification: (
      state,
      action: PayloadAction<
        Omit<UIState["notifications"][0], "id" | "timestamp">
      >,
    ) => {
      state.notifications.push({
        ...action.payload,
        id: crypto.randomUUID(),
        timestamp: Date.now(),
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (n) => n.id !== action.payload,
      );
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
  },
});

export const {
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
} = uiSlice.actions;

// Selectors
export const selectSidebarCollapsed = (state: { ui: UIState }) =>
  state.ui.sidebarCollapsed;

export const selectTheme = (state: { ui: UIState }) => state.ui.theme;

export const selectSidebarOpen = (state: { ui: UIState }) =>
  state.ui.sidebarOpen;

// Export getInitialTheme for testing
export { getInitialTheme };

export default uiSlice.reducer;
