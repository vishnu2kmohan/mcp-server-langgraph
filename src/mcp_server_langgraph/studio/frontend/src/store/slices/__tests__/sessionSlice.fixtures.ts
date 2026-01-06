/**
 * sessionSlice Test Fixtures
 *
 * Shared utilities and fixtures for sessionSlice test shards.
 */

import { vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import sessionReducer, { initialSessionState } from "../sessionSlice";
import type {
  ClientSession,
  SessionSummary,
  ChatMessage,
} from "../../../types/session";

// =============================================================================
// STORE FACTORY
// =============================================================================

export const createTestStore = (
  preloadedState?: Partial<typeof initialSessionState>,
) => {
  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    preloadedState: preloadedState
      ? { session: { ...initialSessionState, ...preloadedState } }
      : undefined,
  });
};

// =============================================================================
// MOCK FETCH
// =============================================================================

export const mockFetch = vi.fn();

export const setupMockFetch = () => {
  global.fetch = mockFetch;
};

export const resetMockFetch = () => {
  mockFetch.mockClear();
};

// =============================================================================
// SESSION FIXTURES
// =============================================================================

export const createMockSession = (
  overrides?: Partial<ClientSession>,
): ClientSession => ({
  id: "s1",
  name: "Test Session",
  config: {
    modelProvider: "openai",
    modelName: "gpt-4",
    temperature: 0.7,
    maxTokens: 4096,
  },
  messages: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
  ...overrides,
});

export const createMockSessionSummary = (
  overrides?: Partial<SessionSummary>,
): SessionSummary => ({
  id: "s1",
  name: "Session 1",
  createdAt: Date.now(),
  updatedAt: Date.now(),
  messageCount: 0,
  ...overrides,
});

export const createMockMessage = (
  overrides?: Partial<ChatMessage>,
): ChatMessage => ({
  id: "m1",
  role: "user",
  content: "Hello",
  timestamp: Date.now(),
  ...overrides,
});

// =============================================================================
// API RESPONSE FACTORIES
// =============================================================================

export const createMockSessionsResponse = (sessions: SessionSummary[]) => ({
  ok: true,
  json: () => Promise.resolve({ sessions }),
});

export const createMockSessionResponse = (session: ClientSession) => ({
  ok: true,
  json: () => Promise.resolve(session),
});

export const createMockPaginatedResponse = (
  items: SessionSummary[],
  total: number,
  nextCursor: string | null = null,
) => ({
  ok: true,
  json: () =>
    Promise.resolve({
      items,
      total,
      next_cursor: nextCursor,
    }),
});

export const createMockCursorPaginatedResponse = (
  data: SessionSummary[],
  count: number,
  nextCursor: string | null = null,
) => ({
  ok: true,
  json: () =>
    Promise.resolve({
      data,
      pagination: {
        count,
        next_cursor: nextCursor,
      },
    }),
});

export const createMockErrorResponse = (status: number, detail: string) => ({
  ok: false,
  status,
  json: () => Promise.resolve({ detail }),
});

export const createMockSuccessResponse = () => ({
  ok: true,
  json: () => Promise.resolve({ success: true }),
});

// =============================================================================
// DEFERRED PROMISE HELPER
// =============================================================================

export const createDeferredPromise = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

// Re-export types
export type { ClientSession, SessionSummary, ChatMessage };
