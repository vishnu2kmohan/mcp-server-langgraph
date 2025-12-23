/**
 * sessionSlice Tests
 *
 * TDD tests for session Redux slice.
 * Tests cover:
 * - Initial state
 * - Synchronous actions
 * - Async thunks (fetchSessions, createSession, loadSession, etc.)
 * - Selectors
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import sessionReducer, {
  initialSessionState,
  fetchSessions,
  fetchMoreSessions,
  createSession,
  loadSession,
  deleteSession,
  renameSession,
  sendMessage,
  clearMessages,
  addMessage,
  updateMessage,
  deleteMessage,
  closeSession,
  clearError,
  setSessions,
  setCurrentSession,
  resetSession,
  selectSessions,
  selectCurrentSession,
  selectMessages,
  selectIsLoadingSessions,
  selectIsLoadingSession,
  selectIsSending,
  selectSessionError,
  selectSessionById,
  selectHasMore,
  selectTotalCount,
  selectIsLoadingMore,
  selectCursor,
  selectHasPendingMutation,
} from "./sessionSlice";
import type { Session, SessionSummary, ChatMessage } from "../../types/session";

// Create a test store
const createTestStore = (
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

// Mock fetch
const mockFetch = vi.fn();

describe("sessionSlice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should have empty sessions array", () => {
      const store = createTestStore();
      expect(selectSessions(store.getState())).toEqual([]);
    });

    it("should have null current session", () => {
      const store = createTestStore();
      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should not be loading initially", () => {
      const store = createTestStore();
      expect(selectIsLoadingSessions(store.getState())).toBe(false);
      expect(selectIsLoadingSession(store.getState())).toBe(false);
    });

    it("should not be sending initially", () => {
      const store = createTestStore();
      expect(selectIsSending(store.getState())).toBe(false);
    });

    it("should have no error", () => {
      const store = createTestStore();
      expect(selectSessionError(store.getState())).toBeNull();
    });
  });

  describe("synchronous actions", () => {
    describe("addMessage", () => {
      it("should add message to current session", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        const newMessage: ChatMessage = {
          id: "m1",
          role: "assistant",
          content: "Hello!",
          timestamp: Date.now(),
        };

        store.dispatch(addMessage(newMessage));

        expect(selectMessages(store.getState())).toHaveLength(1);
        expect(selectMessages(store.getState())[0].content).toBe("Hello!");
      });
    });

    describe("updateMessage", () => {
      it("should update existing message", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "assistant",
                content: "Partial...",
                timestamp: Date.now(),
                isStreaming: true,
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        store.dispatch(
          updateMessage({
            messageId: "m1",
            updates: { content: "Complete response", isStreaming: false },
          }),
        );

        expect(selectMessages(store.getState())[0].content).toBe(
          "Complete response",
        );
        expect(selectMessages(store.getState())[0].isStreaming).toBe(false);
      });
    });

    describe("deleteMessage", () => {
      it("should delete message from current session", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
              },
              {
                id: "m2",
                role: "assistant",
                content: "Hi!",
                timestamp: Date.now(),
              },
              {
                id: "m3",
                role: "user",
                content: "How are you?",
                timestamp: Date.now(),
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        store.dispatch(deleteMessage("m2"));

        const messages = selectMessages(store.getState());
        expect(messages).toHaveLength(2);
        expect(messages[0].id).toBe("m1");
        expect(messages[1].id).toBe("m3");
      });

      it("should do nothing if message not found", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        store.dispatch(deleteMessage("non-existent"));

        expect(selectMessages(store.getState())).toHaveLength(1);
      });

      it("should do nothing if no current session", () => {
        const store = createTestStore();

        // Should not throw
        store.dispatch(deleteMessage("m1"));

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("closeSession", () => {
      it("should set current session to null", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        store.dispatch(closeSession());

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("clearError", () => {
      it("should clear error state", () => {
        const store = createTestStore({
          error: "Some error",
        });

        store.dispatch(clearError());

        expect(selectSessionError(store.getState())).toBeNull();
      });
    });

    describe("setSessions", () => {
      it("should set sessions list", () => {
        const store = createTestStore();
        const sessions: SessionSummary[] = [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 5,
          },
        ];

        store.dispatch(setSessions(sessions));

        expect(selectSessions(store.getState())).toHaveLength(1);
      });
    });

    describe("setCurrentSession", () => {
      it("should set current session", () => {
        const store = createTestStore();
        const session: Session = {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };

        store.dispatch(setCurrentSession(session));

        expect(selectCurrentSession(store.getState())?.id).toBe("s1");
      });
    });

    describe("resetSession", () => {
      it("should reset to initial state", () => {
        const store = createTestStore({
          sessions: [
            {
              id: "s1",
              name: "Session 1",
              createdAt: Date.now(),
              updatedAt: Date.now(),
              messageCount: 5,
            },
          ],
          error: "Some error",
        });

        store.dispatch(resetSession());

        expect(selectSessions(store.getState())).toEqual([]);
        expect(selectSessionError(store.getState())).toBeNull();
      });
    });
  });

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
      const mockSessions: SessionSummary[] = [
        {
          id: "s1",
          name: "Session 1",
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messageCount: 5,
        },
        {
          id: "s2",
          name: "Session 2",
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messageCount: 10,
        },
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
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Server error" }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions());

      expect(selectSessionError(store.getState())).toBe("Server error");
      expect(selectIsLoadingSessions(store.getState())).toBe(false);
    });
  });

  describe("createSession thunk", () => {
    it("should create a new session", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "new-session-123",
            name: "My New Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      const store = createTestStore();
      const result = await store.dispatch(
        createSession({ name: "My New Session" }),
      );

      expect(result.type).toBe("session/createSession/fulfilled");
      expect(selectCurrentSession(store.getState())?.id).toBe(
        "new-session-123",
      );
    });

    it("should add session to sessions list", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "session-custom",
            name: "Custom Session",
            config: {
              modelProvider: "anthropic",
              modelName: "claude-3",
              temperature: 0.5,
              maxTokens: 8192,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(
        createSession({
          name: "Custom Session",
          config: { modelProvider: "anthropic", modelName: "claude-3" },
        }),
      );

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].name).toBe("Custom Session");
    });

    it("should set error on creation failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Invalid session name" }),
      });

      const store = createTestStore();
      await store.dispatch(createSession({ name: "" }));

      expect(selectSessionError(store.getState())).toBe("Invalid session name");
    });

    it("should increment totalCount when creating new session", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "new-session-abc",
            name: "New Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Existing Session",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 5,
          },
        ],
        totalCount: 1,
      });

      await store.dispatch(createSession({ name: "New Session" }));

      // Session count should reflect the new session
      expect(selectSessions(store.getState())).toHaveLength(2);
      expect(selectTotalCount(store.getState())).toBe(2);
    });

    it("should not increment totalCount when updating existing session (race condition)", async () => {
      const existingSessionId = "existing-session-123";
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: existingSessionId,
            name: "Updated Session",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: existingSessionId,
            name: "Existing Session",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 5,
          },
        ],
        totalCount: 1,
      });

      await store.dispatch(createSession({ name: "Updated Session" }));

      // Should not increment if session already exists (race condition case)
      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectTotalCount(store.getState())).toBe(1);
    });

    it("should include Authorization header when access_token is in localStorage", async () => {
      // Set up access_token in localStorage
      const mockToken = "test-access-token-12345";
      localStorage.setItem("access_token", mockToken);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "session-auth-test",
            name: "Auth Test Session",
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(createSession({ name: "Auth Test Session" }));

      // Verify fetch was called with Authorization header
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        }),
      );

      // Clean up
      localStorage.removeItem("access_token");
    });

    it("should include Authorization header from auth_token as fallback", async () => {
      // Set up auth_token in localStorage (fallback key)
      const mockToken = "test-auth-token-67890";
      localStorage.setItem("auth_token", mockToken);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "session-fallback-test",
            name: "Fallback Auth Test",
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
      });

      const store = createTestStore();
      await store.dispatch(createSession({ name: "Fallback Auth Test" }));

      // Verify fetch was called with Authorization header from fallback
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        }),
      );

      // Clean up
      localStorage.removeItem("auth_token");
    });
  });

  describe("loadSession thunk", () => {
    it("should load session by ID", async () => {
      const mockSession: Session = {
        id: "session-load-test",
        name: "Test Session",
        config: {
          modelProvider: "openai",
          modelName: "gpt-4",
          temperature: 0.7,
          maxTokens: 4096,
        },
        messages: [
          { id: "m1", role: "user", content: "Hello", timestamp: Date.now() },
          {
            id: "m2",
            role: "assistant",
            content: "Hi there!",
            timestamp: Date.now(),
          },
        ],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

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
                json: () =>
                  Promise.resolve({
                    id: "s1",
                    name: "Session",
                    config: {
                      modelProvider: "openai",
                      modelName: "gpt-4",
                      temperature: 0.7,
                      maxTokens: 4096,
                    },
                    messages: [],
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                  }),
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
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Session not found" }),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("non-existent"));

      expect(selectSessionError(store.getState())).toBe("Session not found");
      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should read model config from API response (snake_case format)", async () => {
      // API returns config in snake_case format matching backend SessionConfig model
      const apiResponse = {
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
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("session-config-test"));

      const session = selectCurrentSession(store.getState());
      expect(session?.config.modelName).toBe("claude-3-opus");
      expect(session?.config.temperature).toBe(0.5);
      expect(session?.config.maxTokens).toBe(8192);
    });

    it("should fall back to defaults when API response has no config", async () => {
      const apiResponse = {
        id: "session-no-config",
        name: "No Config Session",
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const store = createTestStore();
      await store.dispatch(loadSession("session-no-config"));

      const session = selectCurrentSession(store.getState());
      // Should use defaults (aligned with backend: gpt-4o-mini)
      expect(session?.config.modelName).toBe("gpt-4o-mini");
      expect(session?.config.modelProvider).toBe("openai");
    });
  });

  describe("deleteSession thunk", () => {
    it("should delete session and remove from list", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
          {
            id: "s2",
            name: "Session 2",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].id).toBe("s2");
    });

    it("should close current session if deleted", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
        currentSession: {
          id: "s1",
          name: "Session 1",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should set error on delete failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: "Permission denied" }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Permission denied");
      // Session should still exist
      expect(selectSessions(store.getState())).toHaveLength(1);
    });
  });

  describe("renameSession thunk", () => {
    it("should rename session", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Old Name",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
        currentSession: {
          id: "s1",
          name: "Old Name",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(
        renameSession({ sessionId: "s1", name: "New Name" }),
      );

      expect(selectSessions(store.getState())[0].name).toBe("New Name");
      expect(selectCurrentSession(store.getState())?.name).toBe("New Name");
    });

    it("should set error on rename failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Invalid session name" }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Old Name",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });

      await store.dispatch(renameSession({ sessionId: "s1", name: "" }));

      expect(selectSessionError(store.getState())).toBe("Invalid session name");
      // Name should remain unchanged
      expect(selectSessions(store.getState())[0].name).toBe("Old Name");
    });
  });

  describe("sendMessage thunk", () => {
    it("should add user message and set isSending", async () => {
      let resolveSend!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveSend = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    message: {
                      id: "m2",
                      role: "assistant",
                      content: "Response",
                      timestamp: Date.now(),
                    },
                  }),
              });
          }),
      );

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      const sendPromise = store.dispatch(sendMessage("Hello"));

      // User message should be added immediately via addUserMessage
      expect(selectMessages(store.getState())).toHaveLength(1);
      expect(selectMessages(store.getState())[0].role).toBe("user");
      expect(selectIsSending(store.getState())).toBe(true);

      resolveSend();
      await sendPromise;

      expect(selectIsSending(store.getState())).toBe(false);
      // Assistant message should now be added
      expect(selectMessages(store.getState())).toHaveLength(2);
    });

    it("should set error if no current session", async () => {
      const store = createTestStore();
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe("No active session");
    });
  });

  describe("clearMessages thunk", () => {
    it("should clear all messages in current session", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [
            { id: "m1", role: "user", content: "Hello", timestamp: Date.now() },
            {
              id: "m2",
              role: "assistant",
              content: "Hi",
              timestamp: Date.now(),
            },
          ],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(clearMessages());

      expect(selectMessages(store.getState())).toHaveLength(0);
    });

    it("should set error on clear failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Server error" }),
      });

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [
            { id: "m1", role: "user", content: "Hello", timestamp: Date.now() },
          ],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(clearMessages());

      expect(selectSessionError(store.getState())).toBe("Server error");
      // Messages should still exist
      expect(selectMessages(store.getState())).toHaveLength(1);
    });
  });

  describe("selectSessionById selector", () => {
    it("should find session by ID", () => {
      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 5,
          },
          {
            id: "s2",
            name: "Session 2",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 10,
          },
        ],
      });

      const selector = selectSessionById("s1");
      expect(selector(store.getState())?.name).toBe("Session 1");
    });

    it("should return undefined if session not found", () => {
      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });

      const selector = selectSessionById("non-existent");
      expect(selector(store.getState())).toBeUndefined();
    });
  });

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
      // Create store without hasPendingMutation to test ?? false fallback
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

  describe("fetchSessions with pagination", () => {
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

      // Check that URL includes params
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
            items: [
              {
                id: "s1",
                name: "Session 1",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
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
            items: [
              {
                id: "s1",
                name: "Session 1",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            total: 1,
            next_cursor: null,
          }),
      });

      const store = createTestStore();
      await store.dispatch(fetchSessions({}));

      expect(selectHasMore(store.getState())).toBe(false);
      expect(selectCursor(store.getState())).toBeNull();
    });
  });

  describe("fetchSessions response format handling", () => {
    it("should handle CursorPaginatedResponse format (data.pagination)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [
              {
                id: "s1",
                name: "Cursor Session",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 3,
              },
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
              {
                id: "s1",
                name: "S1",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
              {
                id: "s2",
                name: "S2",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
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
              {
                id: "s1",
                name: "Legacy Items",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
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
            data: [
              {
                id: "s1",
                name: "Data Format",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
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

  describe("fetchMoreSessions response format handling", () => {
    it("should handle CursorPaginatedResponse format", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [
              {
                id: "s3",
                name: "More Session",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            pagination: {
              count: 50,
              next_cursor: "more-cursor",
            },
          }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Existing",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
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
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Rate limit exceeded" }),
      });

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
              {
                id: "s1",
                name: "Duplicate",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
              {
                id: "s2",
                name: "New Session",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            total: 3,
            next_cursor: null,
          }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Existing",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
        cursor: "cursor",
      });

      await store.dispatch(fetchMoreSessions());

      // Should only have 2 sessions (s1 deduplicated)
      expect(selectSessions(store.getState())).toHaveLength(2);
      expect(selectSessions(store.getState()).map((s) => s.id)).toEqual([
        "s1",
        "s2",
      ]);
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

  describe("synchronous actions edge cases", () => {
    describe("addMessage when no current session", () => {
      it("should do nothing if no current session", () => {
        const store = createTestStore();
        const newMessage: ChatMessage = {
          id: "m1",
          role: "assistant",
          content: "Hello!",
          timestamp: Date.now(),
        };

        // Should not throw
        store.dispatch(addMessage(newMessage));

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("updateMessage edge cases", () => {
      it("should do nothing if message not found", () => {
        const store = createTestStore({
          currentSession: {
            id: "s1",
            name: "Test",
            config: {
              modelProvider: "openai",
              modelName: "gpt-4",
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [
              {
                id: "m1",
                role: "user",
                content: "Hello",
                timestamp: Date.now(),
              },
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        });

        store.dispatch(
          updateMessage({
            messageId: "non-existent",
            updates: { content: "Updated" },
          }),
        );

        // Original message should be unchanged
        expect(selectMessages(store.getState())[0].content).toBe("Hello");
      });

      it("should do nothing if no current session", () => {
        const store = createTestStore();

        // Should not throw
        store.dispatch(
          updateMessage({ messageId: "m1", updates: { content: "Updated" } }),
        );

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });
  });

  describe("async thunk error handling", () => {
    it("should handle createSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network failed"));

      const store = createTestStore();
      await store.dispatch(createSession({ name: "Test" }));

      expect(selectSessionError(store.getState())).toBe("Network failed");
    });

    it("should handle createSession non-Error rejection", async () => {
      mockFetch.mockRejectedValueOnce("String error");

      const store = createTestStore();
      await store.dispatch(createSession({ name: "Test" }));

      expect(selectSessionError(store.getState())).toBe(
        "Failed to create session",
      );
    });

    it("should handle loadSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Timeout"));

      const store = createTestStore();
      await store.dispatch(loadSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Timeout");
      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should handle deleteSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection lost"));

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });
      await store.dispatch(deleteSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Connection lost");
      // Session should still exist since delete failed
      expect(selectSessions(store.getState())).toHaveLength(1);
    });

    it("should handle renameSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Server unreachable"));

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Old Name",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });
      await store.dispatch(
        renameSession({ sessionId: "s1", name: "New Name" }),
      );

      expect(selectSessionError(store.getState())).toBe("Server unreachable");
      expect(selectSessions(store.getState())[0].name).toBe("Old Name");
    });

    it("should handle sendMessage network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Send failed"));

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe("Send failed");
      expect(selectIsSending(store.getState())).toBe(false);
    });

    it("should handle sendMessage API error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Model overloaded" }),
      });

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe("Model overloaded");
      expect(selectIsSending(store.getState())).toBe(false);
    });

    it("should handle sendMessage API error response without detail", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({}),
      });

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe(
        "Failed to send message",
      );
      expect(selectIsSending(store.getState())).toBe(false);
    });

    it("should handle clearMessages network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Clear failed"));

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [
            { id: "m1", role: "user", content: "Hello", timestamp: Date.now() },
          ],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });
      await store.dispatch(clearMessages());

      expect(selectSessionError(store.getState())).toBe("Clear failed");
      // Messages should still exist since clear failed
      expect(selectMessages(store.getState())).toHaveLength(1);
    });

    it("should return early from clearMessages when no current session", async () => {
      const store = createTestStore();
      const result = await store.dispatch(clearMessages());

      // Should not call fetch and should succeed
      expect(mockFetch).not.toHaveBeenCalled();
      expect(result.type).toBe("session/clearMessages/fulfilled");
    });

    it("should use fallback error for sendMessage.rejected when payload is undefined", () => {
      // Directly test reducer with undefined payload
      const state = sessionReducer(
        { ...initialSessionState, isSending: true },
        { type: sendMessage.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to send message");
      expect(state.isSending).toBe(false);
    });

    it("should use fallback error for clearMessages.rejected when payload is undefined", () => {
      // Directly test reducer with undefined payload
      const state = sessionReducer(
        { ...initialSessionState },
        { type: clearMessages.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to clear messages");
    });
  });

  describe("renameSession edge cases", () => {
    it("should update session in list but not currentSession if different", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
          {
            id: "s2",
            name: "Session 2",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
        currentSession: {
          id: "s2",
          name: "Session 2",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(
        renameSession({ sessionId: "s1", name: "Renamed Session 1" }),
      );

      expect(selectSessions(store.getState())[0].name).toBe(
        "Renamed Session 1",
      );
      expect(selectCurrentSession(store.getState())?.name).toBe("Session 2"); // unchanged
    });

    it("should handle rename of non-existent session in list", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
      });

      await store.dispatch(
        renameSession({ sessionId: "non-existent", name: "New Name" }),
      );

      // Should not throw, session list unchanged
      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].name).toBe("Session 1");
    });
  });

  describe("deleteSession edge cases", () => {
    it("should not affect currentSession if deleting different session", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
          {
            id: "s2",
            name: "Session 2",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
        ],
        currentSession: {
          id: "s2",
          name: "Session 2",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectCurrentSession(store.getState())?.id).toBe("s2");
    });
  });

  describe("sendMessage edge cases", () => {
    it("should handle null response message", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: null }),
      });

      const store = createTestStore({
        currentSession: {
          id: "s1",
          name: "Test",
          config: {
            modelProvider: "openai",
            modelName: "gpt-4",
            temperature: 0.7,
            maxTokens: 4096,
          },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      await store.dispatch(sendMessage("Hello"));

      // Should only have user message (no assistant message added)
      expect(selectMessages(store.getState())).toHaveLength(1);
      expect(selectMessages(store.getState())[0].role).toBe("user");
      expect(selectIsSending(store.getState())).toBe(false);
    });
  });

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
            items: [
              {
                id: "s3",
                name: "Session 3",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            total: 3,
            next_cursor: null,
          }),
      });

      const store = createTestStore({
        sessions: [
          {
            id: "s1",
            name: "Session 1",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
          {
            id: "s2",
            name: "Session 2",
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messageCount: 0,
          },
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
            items: [
              {
                id: "s3",
                name: "Session 3",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            total: 10,
            next_cursor: "newCursor789",
          }),
      });

      const store = createTestStore({ cursor: "oldCursor" });
      await store.dispatch(fetchMoreSessions());

      expect(selectCursor(store.getState())).toBe("newCursor789");
      expect(selectHasMore(store.getState())).toBe(true);
    });
  });

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

    it("should use fallback error for deleteSession.rejected with undefined payload", () => {
      const state = sessionReducer(
        { ...initialSessionState },
        { type: deleteSession.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to delete session");
    });

    it("should use fallback error for renameSession.rejected with undefined payload", () => {
      const state = sessionReducer(
        { ...initialSessionState },
        { type: renameSession.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to rename session");
    });

    it("should handle renameSession.fulfilled when session not found in list", () => {
      const state = sessionReducer(
        { ...initialSessionState, sessions: [] },
        {
          type: renameSession.fulfilled.type,
          payload: { sessionId: "non-existent", name: "New Name" },
        },
      );
      // Should not throw, error should be null
      expect(state.error).toBeNull();
    });
  });
});
