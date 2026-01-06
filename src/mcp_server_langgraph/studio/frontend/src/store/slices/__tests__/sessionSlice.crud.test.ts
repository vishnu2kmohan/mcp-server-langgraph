/**
 * sessionSlice CRUD Tests
 *
 * Tests for session CRUD operations:
 * - Initial state
 * - Synchronous actions (messages, session management)
 * - createSession, deleteSession, renameSession thunks
 * - sendMessage, clearMessages thunks
 * - Error handling
 *
 * @see sessionSlice.fixtures.ts for shared utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import sessionReducer, {
  initialSessionState,
  createSession,
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
  selectTotalCount,
  selectHasPendingMutation,
} from "../sessionSlice";
import {
  createTestStore,
  mockFetch,
  setupMockFetch,
  resetMockFetch,
  createMockSession,
  createMockSessionSummary,
  createMockMessage,
  createMockSuccessResponse,
  createMockErrorResponse,
} from "./sessionSlice.fixtures";
import type { ChatMessage } from "../../../types/session";

describe("sessionSlice - CRUD", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMockFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetMockFetch();
  });

  // ===========================================================================
  // INITIAL STATE
  // ===========================================================================

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

  // ===========================================================================
  // SYNCHRONOUS ACTIONS - MESSAGES
  // ===========================================================================

  describe("synchronous actions", () => {
    describe("addMessage", () => {
      it("should add message to current session", () => {
        const store = createTestStore({
          currentSession: createMockSession(),
        });

        const newMessage: ChatMessage = createMockMessage({
          id: "m1",
          role: "assistant",
          content: "Hello!",
        });

        store.dispatch(addMessage(newMessage));

        expect(selectMessages(store.getState())).toHaveLength(1);
        expect(selectMessages(store.getState())[0].content).toBe("Hello!");
      });

      it("should do nothing if no current session", () => {
        const store = createTestStore();
        const newMessage = createMockMessage();

        store.dispatch(addMessage(newMessage));

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("updateMessage", () => {
      it("should update existing message", () => {
        const store = createTestStore({
          currentSession: createMockSession({
            messages: [
              createMockMessage({
                id: "m1",
                role: "assistant",
                content: "Partial...",
                isStreaming: true,
              }),
            ],
          }),
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

      it("should do nothing if message not found", () => {
        const store = createTestStore({
          currentSession: createMockSession({
            messages: [createMockMessage({ content: "Hello" })],
          }),
        });

        store.dispatch(
          updateMessage({
            messageId: "non-existent",
            updates: { content: "Updated" },
          }),
        );

        expect(selectMessages(store.getState())[0].content).toBe("Hello");
      });

      it("should do nothing if no current session", () => {
        const store = createTestStore();

        store.dispatch(
          updateMessage({ messageId: "m1", updates: { content: "Updated" } }),
        );

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("deleteMessage", () => {
      it("should delete message from current session", () => {
        const store = createTestStore({
          currentSession: createMockSession({
            messages: [
              createMockMessage({ id: "m1", content: "Hello" }),
              createMockMessage({
                id: "m2",
                role: "assistant",
                content: "Hi!",
              }),
              createMockMessage({ id: "m3", content: "How are you?" }),
            ],
          }),
        });

        store.dispatch(deleteMessage("m2"));

        const messages = selectMessages(store.getState());
        expect(messages).toHaveLength(2);
        expect(messages[0].id).toBe("m1");
        expect(messages[1].id).toBe("m3");
      });

      it("should do nothing if message not found", () => {
        const store = createTestStore({
          currentSession: createMockSession({
            messages: [createMockMessage()],
          }),
        });

        store.dispatch(deleteMessage("non-existent"));

        expect(selectMessages(store.getState())).toHaveLength(1);
      });

      it("should do nothing if no current session", () => {
        const store = createTestStore();

        store.dispatch(deleteMessage("m1"));

        expect(selectCurrentSession(store.getState())).toBeNull();
      });
    });

    describe("closeSession", () => {
      it("should set current session to null", () => {
        const store = createTestStore({
          currentSession: createMockSession(),
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
        const sessions = [createMockSessionSummary()];

        store.dispatch(setSessions(sessions));

        expect(selectSessions(store.getState())).toHaveLength(1);
      });
    });

    describe("setCurrentSession", () => {
      it("should set current session", () => {
        const store = createTestStore();
        const session = createMockSession();

        store.dispatch(setCurrentSession(session));

        expect(selectCurrentSession(store.getState())?.id).toBe("s1");
      });
    });

    describe("resetSession", () => {
      it("should reset to initial state", () => {
        const store = createTestStore({
          sessions: [createMockSessionSummary()],
          error: "Some error",
        });

        store.dispatch(resetSession());

        expect(selectSessions(store.getState())).toEqual([]);
        expect(selectSessionError(store.getState())).toBeNull();
      });
    });
  });

  // ===========================================================================
  // CREATE SESSION THUNK
  // ===========================================================================

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
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(400, "Invalid session name"),
      );

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
        sessions: [createMockSessionSummary({ messageCount: 5 })],
        totalCount: 1,
      });

      await store.dispatch(createSession({ name: "New Session" }));

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
          createMockSessionSummary({ id: existingSessionId, messageCount: 5 }),
        ],
        totalCount: 1,
      });

      await store.dispatch(createSession({ name: "Updated Session" }));

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectTotalCount(store.getState())).toBe(1);
    });

    it("should create session successfully when access_token is in localStorage", async () => {
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

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          method: "POST",
        }),
      );

      localStorage.removeItem("access_token");
    });

    it("should create session successfully when auth_token is in localStorage as fallback", async () => {
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

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          method: "POST",
        }),
      );

      localStorage.removeItem("auth_token");
    });
  });

  // ===========================================================================
  // DELETE SESSION THUNK
  // ===========================================================================

  describe("deleteSession thunk", () => {
    it("should delete session and remove from list", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [
          createMockSessionSummary({ id: "s1", name: "Session 1" }),
          createMockSessionSummary({ id: "s2", name: "Session 2" }),
        ],
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].id).toBe("s2");
    });

    it("should close current session if deleted", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1" })],
        currentSession: createMockSession({ id: "s1" }),
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectCurrentSession(store.getState())).toBeNull();
    });

    it("should set error on delete failure", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(403, "Permission denied"),
      );

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1" })],
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Permission denied");
      expect(selectSessions(store.getState())).toHaveLength(1);
    });

    it("should not affect currentSession if deleting different session", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [
          createMockSessionSummary({ id: "s1" }),
          createMockSessionSummary({ id: "s2" }),
        ],
        currentSession: createMockSession({ id: "s2", name: "Session 2" }),
      });

      await store.dispatch(deleteSession("s1"));

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectCurrentSession(store.getState())?.id).toBe("s2");
    });
  });

  // ===========================================================================
  // RENAME SESSION THUNK
  // ===========================================================================

  describe("renameSession thunk", () => {
    it("should rename session", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Old Name" })],
        currentSession: createMockSession({ id: "s1", name: "Old Name" }),
      });

      await store.dispatch(
        renameSession({ sessionId: "s1", name: "New Name" }),
      );

      expect(selectSessions(store.getState())[0].name).toBe("New Name");
      expect(selectCurrentSession(store.getState())?.name).toBe("New Name");
    });

    it("should set error on rename failure", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(400, "Invalid session name"),
      );

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Old Name" })],
      });

      await store.dispatch(renameSession({ sessionId: "s1", name: "" }));

      expect(selectSessionError(store.getState())).toBe("Invalid session name");
      expect(selectSessions(store.getState())[0].name).toBe("Old Name");
    });

    it("should update session in list but not currentSession if different", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [
          createMockSessionSummary({ id: "s1", name: "Session 1" }),
          createMockSessionSummary({ id: "s2", name: "Session 2" }),
        ],
        currentSession: createMockSession({ id: "s2", name: "Session 2" }),
      });

      await store.dispatch(
        renameSession({ sessionId: "s1", name: "Renamed Session 1" }),
      );

      expect(selectSessions(store.getState())[0].name).toBe(
        "Renamed Session 1",
      );
      expect(selectCurrentSession(store.getState())?.name).toBe("Session 2");
    });

    it("should handle rename of non-existent session in list", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Session 1" })],
      });

      await store.dispatch(
        renameSession({ sessionId: "non-existent", name: "New Name" }),
      );

      expect(selectSessions(store.getState())).toHaveLength(1);
      expect(selectSessions(store.getState())[0].name).toBe("Session 1");
    });
  });

  // ===========================================================================
  // SEND MESSAGE THUNK
  // ===========================================================================

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
        currentSession: createMockSession(),
      });

      const sendPromise = store.dispatch(sendMessage("Hello"));

      expect(selectMessages(store.getState())).toHaveLength(1);
      expect(selectMessages(store.getState())[0].role).toBe("user");
      expect(selectIsSending(store.getState())).toBe(true);

      resolveSend();
      await sendPromise;

      expect(selectIsSending(store.getState())).toBe(false);
      expect(selectMessages(store.getState())).toHaveLength(2);
    });

    it("should set error if no current session", async () => {
      const store = createTestStore();
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe("No active session");
    });

    it("should handle null response message", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: null }),
      });

      const store = createTestStore({
        currentSession: createMockSession(),
      });

      await store.dispatch(sendMessage("Hello"));

      expect(selectMessages(store.getState())).toHaveLength(1);
      expect(selectMessages(store.getState())[0].role).toBe("user");
      expect(selectIsSending(store.getState())).toBe(false);
    });
  });

  // ===========================================================================
  // CLEAR MESSAGES THUNK
  // ===========================================================================

  describe("clearMessages thunk", () => {
    it("should clear all messages in current session", async () => {
      mockFetch.mockResolvedValueOnce(createMockSuccessResponse());

      const store = createTestStore({
        currentSession: createMockSession({
          messages: [
            createMockMessage({ content: "Hello" }),
            createMockMessage({ id: "m2", role: "assistant", content: "Hi" }),
          ],
        }),
      });

      await store.dispatch(clearMessages());

      expect(selectMessages(store.getState())).toHaveLength(0);
    });

    it("should set error on clear failure", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(500, "Server error"),
      );

      const store = createTestStore({
        currentSession: createMockSession({
          messages: [createMockMessage()],
        }),
      });

      await store.dispatch(clearMessages());

      expect(selectSessionError(store.getState())).toBe("Server error");
      expect(selectMessages(store.getState())).toHaveLength(1);
    });

    it("should return early from clearMessages when no current session", async () => {
      const store = createTestStore();
      const result = await store.dispatch(clearMessages());

      expect(mockFetch).not.toHaveBeenCalled();
      expect(result.type).toBe("session/clearMessages/fulfilled");
    });
  });

  // ===========================================================================
  // SELECTORS
  // ===========================================================================

  describe("selectSessionById selector", () => {
    it("should find session by ID", () => {
      const store = createTestStore({
        sessions: [
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
        ],
      });

      const selector = selectSessionById("s1");
      expect(selector(store.getState())?.name).toBe("Session 1");
    });

    it("should return undefined if session not found", () => {
      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1" })],
      });

      const selector = selectSessionById("non-existent");
      expect(selector(store.getState())).toBeUndefined();
    });
  });

  // ===========================================================================
  // ASYNC THUNK ERROR HANDLING
  // ===========================================================================

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

    it("should handle deleteSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Connection lost"));

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1" })],
      });
      await store.dispatch(deleteSession("s1"));

      expect(selectSessionError(store.getState())).toBe("Connection lost");
      expect(selectSessions(store.getState())).toHaveLength(1);
    });

    it("should handle renameSession network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Server unreachable"));

      const store = createTestStore({
        sessions: [createMockSessionSummary({ id: "s1", name: "Old Name" })],
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
        currentSession: createMockSession(),
      });
      await store.dispatch(sendMessage("Hello"));

      expect(selectSessionError(store.getState())).toBe("Send failed");
      expect(selectIsSending(store.getState())).toBe(false);
    });

    it("should handle sendMessage API error response", async () => {
      mockFetch.mockResolvedValueOnce(
        createMockErrorResponse(500, "Model overloaded"),
      );

      const store = createTestStore({
        currentSession: createMockSession(),
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
        currentSession: createMockSession(),
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
        currentSession: createMockSession({
          messages: [createMockMessage()],
        }),
      });
      await store.dispatch(clearMessages());

      expect(selectSessionError(store.getState())).toBe("Clear failed");
      expect(selectMessages(store.getState())).toHaveLength(1);
    });
  });

  // ===========================================================================
  // REJECTED ACTION FALLBACK ERROR MESSAGES
  // ===========================================================================

  describe("Rejected action fallback error messages", () => {
    it("should use fallback error for sendMessage.rejected when payload is undefined", () => {
      const state = sessionReducer(
        { ...initialSessionState, isSending: true },
        { type: sendMessage.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to send message");
      expect(state.isSending).toBe(false);
    });

    it("should use fallback error for clearMessages.rejected when payload is undefined", () => {
      const state = sessionReducer(
        { ...initialSessionState },
        { type: clearMessages.rejected.type, payload: undefined },
      );
      expect(state.error).toBe("Failed to clear messages");
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
      expect(state.error).toBeNull();
    });
  });

  // ===========================================================================
  // CROSS-SLICE INTERACTIONS
  // ===========================================================================

  describe("cross-slice interactions", () => {
    describe("logout action from authSlice", () => {
      it("should reset hasPendingMutation when logout is dispatched", async () => {
        const store = createTestStore({
          hasPendingMutation: true,
          currentSession: createMockSession(),
        });

        expect(selectHasPendingMutation(store.getState())).toBe(true);
        expect(selectCurrentSession(store.getState())).not.toBeNull();

        const { logout } = await import("../authSlice");
        store.dispatch(logout());

        expect(selectHasPendingMutation(store.getState())).toBe(false);
        expect(selectCurrentSession(store.getState())).toBeNull();
      });

      it("should handle logout even when hasPendingMutation is already false", async () => {
        const store = createTestStore({
          hasPendingMutation: false,
        });

        expect(selectHasPendingMutation(store.getState())).toBe(false);

        const { logout } = await import("../authSlice");
        store.dispatch(logout());

        expect(selectHasPendingMutation(store.getState())).toBe(false);
      });
    });
  });
});
