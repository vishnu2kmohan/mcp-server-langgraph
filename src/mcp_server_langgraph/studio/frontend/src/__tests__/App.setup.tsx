/**
 * App Test Setup
 *
 * Shared utilities and fixtures for App test shards.
 * Note: vi.mock calls must be in each test file for hoisting.
 */

import { vi } from "vitest";
import { render } from "@testing-library/react";
import { configureStore } from "@reduxjs/toolkit";
import { Provider } from "react-redux";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";
import notificationReducer from "../store/slices/notificationSlice";
import uiReducer from "../store/slices/uiSlice";
import workspaceReducer from "../store/slices/workspaceSlice";
import sessionReducer from "../store/slices/sessionSlice";
import mcpReducer from "../store/slices/mcpSlice";

// =============================================================================
// MOCK STATE VARIABLES
// =============================================================================

// Controls whether useGetCurrentUserQuery returns error or success
export let mockUserQueryError: { status: number } | null = null;

export function setMockUserQueryError(error: { status: number } | null): void {
  mockUserQueryError = error;
}

export function resetMockUserQueryError(): void {
  mockUserQueryError = null;
}

// =============================================================================
// MOCK FUNCTIONS
// =============================================================================

export const mockUseGetCurrentUserQuery = vi.fn();
export const mockUseNotificationWebSocket = vi.fn(() => ({
  status: "connected" as const,
  disconnect: vi.fn(),
  reconnect: vi.fn(),
}));
export const mockUseAlertWebSocket = vi.fn(() => ({
  status: "connected" as const,
  disconnect: vi.fn(),
  reconnect: vi.fn(),
}));
export const mockUseOffline = vi.fn(() => false);
export const mockUsePWAUpdate = vi.fn(() => ({
  needsUpdate: false,
  isOfflineReady: false,
  isUpdating: false,
  updateDismissed: false,
  registration: undefined,
  registrationError: undefined,
  updateApp: vi.fn(),
  dismissUpdate: vi.fn(),
}));
export const mockReportError = vi.fn();
export const mockErrorReportingFlush = vi.fn();
export const mockAnnounce = vi.fn();

// =============================================================================
// STORE FACTORY
// =============================================================================

export const createTestStore = () => {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
      notifications: notificationReducer,
      ui: uiReducer,
      workspace: workspaceReducer,
      session: sessionReducer,
      mcp: mcpReducer,
    },
  });
};

// =============================================================================
// RENDER HELPER
// =============================================================================

export const renderWithStore = (
  ui: React.ReactElement,
  { store = createTestStore() } = {},
) => {
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

// =============================================================================
// RESET HELPERS
// =============================================================================

export function resetAllMocks(): void {
  mockUserQueryError = null;
  mockUseGetCurrentUserQuery.mockClear();
  mockUseNotificationWebSocket.mockClear();
  mockUseAlertWebSocket.mockClear();
  mockUseOffline.mockReturnValue(false);
  mockUsePWAUpdate.mockReturnValue({
    needsUpdate: false,
    isOfflineReady: false,
    isUpdating: false,
    updateDismissed: false,
    registration: undefined,
    registrationError: undefined,
    updateApp: vi.fn(),
    dismissUpdate: vi.fn(),
  });
  mockReportError.mockClear();
  mockErrorReportingFlush.mockClear();
  mockAnnounce.mockClear();
}

// =============================================================================
// MOCK API RESPONSE FACTORY
// =============================================================================

export function createMockApiModule(
  options: { userQueryError?: { status: number } | null } = {},
) {
  return {
    useGetFeatureFlagsQuery: () => ({
      data: {
        workflows: true,
        cost: true,
        observability: true,
        projects: true,
        chat: true,
      },
      isLoading: false,
      error: null,
    }),
    useGetCurrentUserQuery: (arg: undefined, opts: { skip: boolean }) => {
      mockUseGetCurrentUserQuery(arg, opts);
      if (opts?.skip) {
        return { data: undefined, error: undefined };
      }
      if (options.userQueryError || mockUserQueryError) {
        return {
          data: undefined,
          error: options.userQueryError || mockUserQueryError,
        };
      }
      return {
        data: {
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
          persona: "developer" as const,
        },
        error: undefined,
      };
    },
    useGetWorkflowTemplatesQuery: () => ({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
    useLogoutMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve() })),
      { isLoading: false },
    ],
    useCreateSessionMutation: () => [
      vi.fn(() => ({
        unwrap: () =>
          Promise.resolve({ session_id: "test-session-id", name: "New Chat" }),
      })),
      { isLoading: false },
    ],
    useCreateProjectMutation: () => [
      vi.fn(() => ({
        unwrap: () =>
          Promise.resolve({ id: "test-project-id", name: "New Project" }),
      })),
      { isLoading: false },
    ],
    useGetHealthQuery: () => ({
      data: { status: "healthy", version: "1.0.0" },
      isLoading: false,
      isError: false,
    }),
    useListSessionsQuery: () => ({
      data: { items: [], total: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
    }),
    useListProjectsQuery: () => ({
      data: { items: [], total: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
    }),
  };
}
