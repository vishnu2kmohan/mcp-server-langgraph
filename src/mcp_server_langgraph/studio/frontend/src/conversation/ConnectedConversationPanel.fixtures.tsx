/**
 * ConnectedConversationPanel Test Fixtures
 *
 * Extracted from ConnectedConversationPanel.test.tsx for OOM prevention.
 * See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */
import { vi } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter, Routes, Route } from "react-router";
import React from "react";
import sessionReducer, {
  initialSessionState,
} from "../store/slices/sessionSlice";
import uiReducer from "../store/slices/uiSlice";
import chatConnectionReducer, {
  type ChatConnectionState,
} from "../store/slices/chatConnectionSlice";
import executionModeReducer, {
  type ExecutionModeState,
} from "../store/slices/executionModeSlice";
import { api } from "../api";
import { createTestUIState } from "../store/slices/__tests__/uiSlice.fixtures";
import type { SessionState, ChatMessage } from "../types/session";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// Default mock for streaming chat hook
export const defaultStreamingChatMock = {
  isStreaming: false,
  streamingContent: "",
  error: null as string | null,
  thinkingContent: "" as string,
  usage: null,
  thinkingTokens: null as number | null,
  startStream: vi.fn(),
  stopStream: vi.fn(),
  clearContent: vi.fn(),
  model: "gemini-2.5-flash",
};

// Default chat connection state
const initialChatConnectionState: ChatConnectionState = {
  pendingAuthRequirements: [],
  activeConnectionSetup: null,
  connectorSuggestions: {
    visible: false,
    templates: [],
    query: "",
  },
  configuredTemplateIds: [],
};

// Default execution mode state
const initialExecutionModeState: ExecutionModeState = {
  executionMode: "default",
  currentPlan: null,
  planStatus: "idle",
  userIsAdmin: false,
  hasBypassPermission: false,
};

// Create test store helper
export const createTestStore = (preloadedState?: {
  session?: Partial<SessionState>;
  chatConnection?: Partial<ChatConnectionState>;
  executionMode?: Partial<ExecutionModeState>;
}) => {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      session: sessionReducer,
      ui: uiReducer,
      chatConnection: chatConnectionReducer,
      executionMode: executionModeReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      session: preloadedState?.session
        ? { ...initialSessionState, ...preloadedState.session }
        : initialSessionState,
      ui: createTestUIState(),
      chatConnection: preloadedState?.chatConnection
        ? { ...initialChatConnectionState, ...preloadedState.chatConnection }
        : initialChatConnectionState,
      executionMode: preloadedState?.executionMode
        ? { ...initialExecutionModeState, ...preloadedState.executionMode }
        : initialExecutionModeState,
    },
  });
};

// Create mock message helper
export const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: "msg-1",
  role: "user",
  content: "Hello, how are you?",
  timestamp: Date.now(),
  ...overrides,
});

// Wrapper props interface
interface WrapperProps {
  children: React.ReactNode;
}

// Create wrapper component factory
export const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: WrapperProps) {
    return (
      <Provider store={store}>
        <TelemetryProvider>
          <MemoryRouter>
            <Routes>
              <Route
                path="/"
                element={<div data-testid="router-wrapper">{children}</div>}
              />
            </Routes>
          </MemoryRouter>
        </TelemetryProvider>
      </Provider>
    );
  };
};
