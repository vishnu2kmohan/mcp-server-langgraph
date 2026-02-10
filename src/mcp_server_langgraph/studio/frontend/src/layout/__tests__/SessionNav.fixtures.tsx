/**
 * SessionNav Test Fixtures
 *
 * Shared mocks, test data, and utility functions for SessionNav test shards.
 * Split from SessionNav.test.tsx for memory optimization.
 */
import { vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import canvasReducer from "../../store/slices/canvasSlice";
import personaReducer from "../../store/slices/personaSlice";
import sessionReducer from "../../store/slices/sessionSlice";
import type { ReactNode } from "react";
import type { Session } from "../../types";

export const mockNavigate = vi.fn();
export const mockSetSearchParams = vi.fn();
export const mockRevalidate = vi.fn();

export const mockSessions: Session[] = [
  {
    id: "session-1",
    name: "Today's Chat",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    project_id: "project-1",
    status: "active",
  },
  {
    id: "session-2",
    name: "Yesterday's Chat",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    project_id: "project-1",
    status: "active",
  },
  {
    id: "session-3",
    name: "Older Chat",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    project_id: "project-1",
    status: "active",
  },
];

export function createTestStore() {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
      persona: personaReducer,
      session: sessionReducer,
    },
  });
}

export function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}
