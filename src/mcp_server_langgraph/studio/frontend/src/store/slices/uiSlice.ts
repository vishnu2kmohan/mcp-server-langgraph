/**
 * UI State Slice
 *
 * Manages global UI state like sidebar visibility, theme, loading states.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  isLoading: boolean;
  activeView: 'workflows' | 'sessions' | 'chat' | 'cost' | 'observability';
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    timestamp: number;
  }>;
}

const initialState: UIState = {
  sidebarOpen: true,
  theme: 'system',
  isLoading: false,
  activeView: 'workflows',
  notifications: [],
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'system'>) => {
      state.theme = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setActiveView: (
      state,
      action: PayloadAction<UIState['activeView']>
    ) => {
      state.activeView = action.payload;
    },
    addNotification: (
      state,
      action: PayloadAction<Omit<UIState['notifications'][0], 'id' | 'timestamp'>>
    ) => {
      state.notifications.push({
        ...action.payload,
        id: crypto.randomUUID(),
        timestamp: Date.now(),
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (n) => n.id !== action.payload
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
  setTheme,
  setLoading,
  setActiveView,
  addNotification,
  removeNotification,
  clearNotifications,
} = uiSlice.actions;

export default uiSlice.reducer;
