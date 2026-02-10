import React from "react";
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { createTestUIState } from "../../../store/slices/__tests__/uiSlice.fixtures";
import sessionReducer from "../../../store/slices/sessionSlice";
import personaReducer, {
  initialState as initialPersonaState,
} from "../../../store/slices/personaSlice";
import uiReducer from "../../../store/slices/uiSlice";
import authReducer, { initialAuthState } from "../../../store/slices/authSlice";
import type { SessionState, ClientSession } from "../../../types/session";

export const defaultSessionState: SessionState = {
  sessions: [],
  currentSession: null,
  isLoadingSessions: false,
  isLoadingSession: false,
  isSending: false,
  error: null,
  hasMore: false,
  totalCount: 0,
  isLoadingMore: false,
  cursor: null,
  recentPages: [],
  currentPage: "/",
  navigationContext: { page: "/" },
};

export const mockSession: ClientSession = {
  id: "session-123",
  name: "Test Session",
  config: {
    modelProvider: "anthropic",
    modelName: "claude-sonnet-4-20250514",
    temperature: 0.7,
    maxTokens: 4096,
  },
  messages: [
    { id: "msg-1", role: "user", content: "Hello", timestamp: Date.now() },
    {
      id: "msg-2",
      role: "assistant",
      content: "Hi there!",
      timestamp: Date.now(),
    },
  ],
  createdAt: Date.now(),
  updatedAt: Date.now(),
};

export function createTestStore(
  overrides: { session?: Partial<SessionState> } = {},
) {
  return configureStore({
    reducer: {
      session: sessionReducer,
      persona: personaReducer,
      ui: uiReducer,
      auth: authReducer,
    },
    preloadedState: {
      session: { ...defaultSessionState, ...overrides.session },
      persona: initialPersonaState,
      ui: createTestUIState(),
      auth: initialAuthState,
    },
  });
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    sessionOverrides?: Partial<SessionState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({ session: options.sessionOverrides ?? {} });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}
