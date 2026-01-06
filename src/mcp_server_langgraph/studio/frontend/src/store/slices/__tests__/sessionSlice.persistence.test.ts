/**
 * sessionSlice Persistence Tests
 *
 * Tests for session fetching and persistence:
 * - fetchSessions thunk
 * - loadSession thunk
 * - fetchMoreSessions thunk
 * - Pagination selectors
 * - Response format handling
 * - API config transformation
 *
 * @see sessionSlice.fixtures.ts for shared utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import sessionReducer, {
  initialSessionState,
  fetchSessions,
  fetchMoreSessions,
  loadSession,
  selectSessions,
  selectCurrentSession,
  selectMessages,
  selectIsLoadingSessions,
  selectIsLoadingSession,
  selectSessionError,
  selectHasMore,
  selectTotalCount,
  selectIsLoadingMore,
  selectCursor,
  selectHasPendingMutation,
} from "../sessionSlice";
import {
  createTestStore,
  mockFetch,
  setupMockFetch,
  resetMockFetch,
  createMockSession,
  createMockSessionSummary,
  createMockErrorResponse,
} from "./sessionSlice.fixtures";

describe("sessionSlice - Persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMockFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetMockFetch();
  });

  // ===========================================================================
  // FETCH SESSIONS THUNK
  // ===========================================================================

  describe("fetchSessions thunk", () => {
    it("should set isLoadingSessions while fetching", async () => {
      let resolveFetch!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveFetch = () =>
              resolve({
                ok: true,
                json: () => Promise.resolve({ sessions: [] }),
              });
          }),
      );

      const store = createTestStore();
      const fetchPromise = store.dispatch(fetchSessions());

      expect(selectIsLoadingSessions(store.getState())).toBe(true);

      resolveFetch();
      await fetchPromise;

      expect(selectIsLoadingSessions(store.getState())).toBe(false);
    });

    it("should load sessions from API", async () => {
      const mockSessions = [
        createMockSessionSummary({
          id: "s1",
          name: "Session 1",
          messageCount: 5,
        }),
        createMockSessionSummary({
          id: "s2",
          name: "Session 2",
          messageCount: 10,
        }),
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sessions: mockSessions }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessions(store.getState())).toHaveLength(2);
      expect(selectSessions(store.getState())[0].name).toBe("Session 1");
    });

    it("should set error on failed fetch", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(500, "Server error"),
      );

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessionError(store.getState())).toBe("Server error");
      expect(selectIsLoadingSessions(store.getState())).toBe(false);
    });

    it("should pass pagination params to API", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [],
            total: 0,
            next_cursor: null,
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions({ limit: 10, search: "test" }));

      expect(mockFetch).toHaveBeenCalled();
      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("/api/v1/sessions");
      expect(callUrl).toContain("limit=10");
      expect(callUrl).toContain("search=test");
    });

    it("should update hasMore when API returns next_cursor", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [createMockSessionSummary({ id: "s1" })],
            total: 25,
            next_cursor: "cursor123",
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions({}));

      expect(selectHasMore(store.getState())).toBe(true);
      expect(selectCursor(store.getState())).toBe("cursor123");
      expect(selectTotalCount(store.getState())).toBe(25);
    });

    it("should set hasMore to false when no next_cursor", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [createMockSessionSummary({ id: "s1" })],
            total: 1,
            next_cursor: null,
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions({}));

      expect(selectHasMore(store.getState())).toBe(false);
      expect(selectCursor(store.getState())).toBeNull();
    });

    it("should pass status param when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sessions: [] }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions({ status: "active" }));

      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("status=active");
    });
  });

  // ===========================================================================
  // FETCH SESSIONS RESPONSE FORMAT HANDLING
  // ===========================================================================

  describe("fetchSessions response format handling", () => {
    it("should handle CursorPaginatedResponse format (data.pagination)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [
              createMockSessionSummary({
                id: "s1",
                name: "Cursor Session",
                messageCount: 3,
              }),
            ],
            pagination: {
              count: 25,
              next_cursor: "cursor-abc",
            },
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].name).toBe("Cursor Session");
      expect(selectTotalCount(store.getState())).toBe(25);
      expect(selectCursor(store.getState())).toBe("cursor-abc");
    });

    it("should handle CursorPaginatedResponse with missing count (fallback to data.length)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [
              createMockSessionSummary({ id: "s1", name: "S1" }),
              createMockSessionSummary({ id: "s2", name: "S2" }),
            ],
            pagination: {
              next_cursor: null,
            },
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectTotalCount(store.getState())).toBe(2);
      expect(selectHasMore(store.getState())).toBe(false);
    });

    it("should handle legacy items/total format", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [
              createMockSessionSummary({ id: "s1", name: "Legacy Items" }),
            ],
            total: 10,
            next_cursor: "legacy-cursor",
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectTotalCount(store.getState())).toBe(10);
      expect(selectCursor(store.getState())).toBe("legacy-cursor");
    });

    it("should handle legacy data array format (fallback)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [createMockSessionSummary({ id: "s1", name: "Data Format" })],
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].name).toBe("Data Format");
    });

    it("should handle network error (non-Error type)", async () => {
      mockFetch.mockRejectedValueOnce("Network failure string");

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessionError(store.getState())).toBe(
        "Failed to fetch sessions",
      );
      expect(selectIsLoadingSessions(store.getState())).toBe(false);
    });
  });

  // ===========================================================================
  // LOAD SESSION THUNK
  // ===========================================================================

  describe("loadSession thunk", () => {
    it("should load session by ID", async () => {
      const mockSession = createMockSession({
        id: "session-load-test",
        name: "Test Session",
        messages: [
          { id: "m1", role: "user", content: "Hello", timestamp: Date.now() },
          {
            id: "m2",
            role: "assistant",
            content: "Hi there!",
            timestamp: Date.now(),
          },
        ],
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSession),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("session-load-test"));

      expect(selectCurrentSession(store.getState())?.id).toBe(
        "session-load-test",
      );
      expect(selectMessages(store.getState())).toHaveLength(2);
    });

    it("should set isLoadingSession while loading", async () => {
      let resolveLoad!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveLoad = () =>
              resolve({
                ok: true,
                json: () => Promise.resolve(createMockSession()),
              });
          }),
      );

      const store = createTestStore();
      const loadPromise = store.dispatch(loadSession("s1"));

      expect(selectIsLoadingSession(store.getState())).toBe(true);

      resolveLoad();
      await loadPromise;

      expect(selectIsLoadingSession(store.getState())).toBe(false);
    });

    it("should set error on load failure", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(404, "Session not found"),
      );

      const store = createTestStore();
      await store.dispatch(loadSession("non-existent"));

      expect(selectSessionError(store.getState())).toBe("Session not found");
      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should read model config from API response (snake_case format)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "session-config-test",
            name: "Config Test Session",
            config: {
              model: "claude-3-opus",
              temperature: 0.5,
              max_tokens: 8192,
            },
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("session-config-test"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.modelName).toBe("claude-3-opus");
      expect(session?.config.temperature).toBe(0.5);
      expect(session?.config.maxTokens).toBe(8192);
    });

    it("should fall back to defaults when API response has no config", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "session-no-config",
            name: "No Config Session",
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("session-no-config"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.modelName).toBe("gemini-2.5-flash");
      expect(session?.config.modelProvider).toBe("google");
    });

    it("should handle loadSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Timeout"));

      const store = createTestStore();
      await store.dispatch(loadSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Timeout");
      expect(selectCurrentSession(store.getState())).toBeNull();
    });
  });

  // ===========================================================================
  // TRANSFORM API CONFIG EDGE CASES
  // ===========================================================================

  describe("transformApiConfig edge cases", () => {
    it("should map model_provider to modelProvider", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "s1",
            name: "Provider Test",
            config: {
              model: "gpt-4",
              model_provider: "azure",
              temperature: 0.8,
            },
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("s1"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.modelProvider).toBe("azure");
    });

    it("should map system_prompt to systemPrompt", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "s1",
            name: "System Prompt Test",
            config: {
              system_prompt: "You are a helpful assistant.",
            },
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("s1"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.systemPrompt).toBe("You are a helpful assistant.");
    });

    it("should handle camelCase fields when already transformed", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "s1",
            name: "CamelCase Config",
            config: {
              modelName: "claude-3",
              modelProvider: "anthropic",
              maxTokens: 16384,
              systemPrompt: "Pre-transformed prompt",
            },
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("s1"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.modelName).toBe("claude-3");
      expect(session?.config.modelProvider).toBe("anthropic");
      expect(session?.config.maxTokens).toBe(16384);
      expect(session?.config.systemPrompt).toBe("Pre-transformed prompt");
    });
  });

  // ===========================================================================
  // FETCH MORE SESSIONS THUNK
  // ===========================================================================

  describe("fetchMoreSessions thunk", () => {
    it("should set isLoadingMore while fetching", async () => {
      let resolveFetch!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveFetch = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    items: [],
                    total: 0,
                    next_cursor: null,
                  }),
              });
          }),
      );

      const store = createTestStore({ cursor: "cursor123" });
      const fetchPromise = store.dispatch(fetchMoreSessions());

      expect(selectIsLoadingMore(store.getState())).toBe(true);

      resolveFetch();
      await fetchPromise;

      expect(selectIsLoadingMore(store.getState())).toBe(false);
    });

    it("should append sessions to existing list", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [createMockSessionSummary({ id: "s3", name: "Session 3" })],
            total: 3,
            next_cursor: null,
          }),
      });

      const store = createTestStore({
        sessions: [
          createMockSessionSummary({ id: "s1", name: "Session 1" }),
          createMockSessionSummary({ id: "s2", name: "Session 2" }),
        ],
        cursor: "cursor123",
      });

      await store.dispatch(fetchMoreSessions());

      expect(selectSessions(store.getState())).toHaveLength(3);
      expect(selectSessions(store.getState())[2].id).toBe("s3");
    });

    it("should use current cursor from state", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [],
            total: 0,
            next_cursor: null,
          }),
      });

      const store = createTestStore({ cursor: "myCursor456" });
      await store.dispatch(fetchMoreSessions());

      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("cursor=myCursor456");
    });

    it("should update cursor after fetching more", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [createMockSessionSummary({ id: "s3", name: "Session 3" })],
            total: 10,
            next_cursor: "newCursor789",
          }),
      });

      const store = createTestStore({ cursor: "oldCursor" });
      await store.dispatch(fetchMoreSessions());

      expect(selectCursor(store.getState())).toBe("newCursor789");
      expect(selectHasMore(store.getState())).toBe(true);
    });

    it("should fetch without cursor when none exists", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, next_cursor: null }),
      });

      const store = createTestStore({ cursor: null });
      await store.dispatch(fetchMoreSessions());

      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toBe("/api/v1/sessions");
    });
  });

  // ===========================================================================
  // FETCH MORE SESSIONS RESPONSE FORMAT HANDLING
  // ===========================================================================

  describe("fetchMoreSessions response format handling", () => {
    it("should handle CursorPaginatedResponse format", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [
              createMockSessionSummary({ id: "s3", name: "More Session" }),
            ],
            pagination: {
              count: 50,
              next_cursor: "more-cursor",
            },
          }),
      });

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Existing" })],
        cursor: "initial-cursor",
      });

      await store.dispatch(fetchMoreSessions());

      expect(selectSessions(store.getState())).toHaveLength(2);
      expect(selectTotalCount(store.getState())).toBe(50);
      expect(selectCursor(store.getState())).toBe("more-cursor");
    });

    it("should handle network error (non-Error type)", async () => {
      mockFetch.mockRejectedValueOnce({ message: "Connection failed" });

      const store = createTestStore({ cursor: "some-cursor" });
      await store.dispatch(fetchMoreSessions());

      expect(selectSessionError(store.getState())).toBe(
        "Failed to fetch more sessions",
      );
      expect(selectIsLoadingMore(store.getState())).toBe(false);
    });

    it("should handle API error response", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(429, "Rate limit exceeded"),
      );

      const store = createTestStore({ cursor: "some-cursor" });
      await store.dispatch(fetchMoreSessions());

      expect(selectSessionError(store.getState())).toBe("Rate limit exceeded");
      expect(selectIsLoadingMore(store.getState())).toBe(false);
    });

    it("should handle API error response without detail", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({}),
      });

      const store = createTestStore({ cursor: "some-cursor" });
      await store.dispatch(fetchMoreSessions());

      expect(selectSessionError(store.getState())).toBe(
        "Failed to fetch more sessions",
      );
      expect(selectIsLoadingMore(store.getState())).toBe(false);
    });

    it("should deduplicate sessions when fetching more", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [
              createMockSessionSummary({ id: "s1", name: "Duplicate" }),
              createMockSessionSummary({ id: "s2", name: "New Session" }),
            ],
            total: 3,
            next_cursor: null,
          }),
      });

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Existing" })],
        cursor: "cursor",
      });

      await store.dispatch(fetchMoreSessions());

      expect(selectSessions(store.getState())).toHaveLength(2);
      expect(selectSessions(store.getState()).map((s) => s.id)).toEqual([
        "s1",
        "s2",
      ]);
    });
  });

  // ===========================================================================
  // PAGINATION SELECTORS
  // ===========================================================================

  describe("pagination selectors", () => {
    it("should select hasMore", () => {
      const store = createTestStore({ hasMore: true });
      expect(selectHasMore(store.getState())).toBe(true);
    });

    it("should select totalCount", () => {
      const store = createTestStore({ totalCount: 50 });
      expect(selectTotalCount(store.getState())).toBe(50);
    });

    it("should select isLoadingMore", () => {
      const store = createTestStore({ isLoadingMore: true });
      expect(selectIsLoadingMore(store.getState())).toBe(true);
    });

    it("should select cursor", () => {
      const store = createTestStore({ cursor: "abc123" });
      expect(selectCursor(store.getState())).toBe("abc123");
    });

    it("should select hasPendingMutation", () => {
      const store = createTestStore({ hasPendingMutation: true });
      expect(selectHasPendingMutation(store.getState())).toBe(true);
    });

    it("should return false for hasPendingMutation when undefined", () => {
      const store = configureStore({
        reducer: { session: sessionReducer },
        preloadedState: {
          session: {
            ...initialSessionState,
            hasPendingMutation: undefined as unknown as boolean,
          },
        },
      });
      expect(selectHasPendingMutation(store.getState())).toBe(false);
    });

    it("should return false for hasMore when undefined", () => {
      const store = configureStore({
        reducer: { session: sessionReducer },
        preloadedState: {
          session: {
            ...initialSessionState,
            hasMore: undefined as unknown as boolean,
          },
        },
      });
      expect(selectHasMore(store.getState())).toBe(false);
    });

    it("should return 0 for totalCount when undefined", () => {
      const store = configureStore({
        reducer: { session: sessionReducer },
        preloadedState: {
          session: {
            ...initialSessionState,
            totalCount: undefined as unknown as number,
          },
        },
      });
      expect(selectTotalCount(store.getState())).toBe(0);
    });

    it("should return false for isLoadingMore when undefined", () => {
      const store = configureStore({
        reducer: { session: sessionReducer },
        preloadedState: {
          session: {
            ...initialSessionState,
            isLoadingMore: undefined as unknown as boolean,
          },
        },
      });
      expect(selectIsLoadingMore(store.getState())).toBe(false);
    });

    it("should return null for cursor when undefined", () => {
      const store = configureStore({
        reducer: { session: sessionReducer },
        preloadedState: {
          session: {
            ...initialSessionState,
            cursor: undefined as unknown as string | null,
          },
        },
      });
      expect(selectCursor(store.getState())).toBe(null);
    });

    it("should return empty array for messages when currentSession is null", () => {
      const store = createTestStore({ currentSession: null });
      expect(selectMessages(store.getState())).toEqual([]);
    });
  });

  // ===========================================================================
  // REJECTED ACTION FALLBACK ERROR MESSAGES
  // ===========================================================================

  describe("Rejected action fallback error messages", () => {
    it("should use fallback error for loadSession.rejected with undefined payload", () => {
      const state = sessionReducer(
        { ...initialSessionState, isLoadingSession: true },
        { type: loadSession.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to load session");
      expect(state.isLoadingSession).toBe(false);
      expect(state.currentSession).toBeNull();
    });
  });
});
