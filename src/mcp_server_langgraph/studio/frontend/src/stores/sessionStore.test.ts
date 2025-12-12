/**
 * sessionStore Tests
 *
 * TDD tests for session state management.
 * Tests cover:
 * - Initial state
 * - Session CRUD operations
 * - Message operations
 * - Loading states
 * - Error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { createTestSessionStore } from './sessionStore';
import type { SessionStore, ChatMessage, SessionSummary, Session } from '../types/session';

// Mock fetch
const mockFetch = vi.fn() as Mock;

describe('sessionStore', () => {
  let store: ReturnType<typeof createTestSessionStore>;

  beforeEach(() => {
    store = createTestSessionStore();
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('initial state', () => {
    it('should have empty sessions array', () => {
      expect(store.getState().sessions).toEqual([]);
    });

    it('should have null current session', () => {
      expect(store.getState().currentSession).toBeNull();
    });

    it('should not be loading initially', () => {
      expect(store.getState().isLoadingSessions).toBe(false);
      expect(store.getState().isLoadingSession).toBe(false);
    });

    it('should not be sending initially', () => {
      expect(store.getState().isSending).toBe(false);
    });

    it('should have no error', () => {
      expect(store.getState().error).toBeNull();
    });
  });

  describe('fetchSessions', () => {
    it('should set isLoadingSessions while fetching', async () => {
      // Arrange
      let resolveFetch!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveFetch = () =>
              resolve({
                ok: true,
                json: () => Promise.resolve({ sessions: [] }),
              });
          })
      );

      // Act
      const fetchPromise = store.getState().fetchSessions();

      // Assert
      expect(store.getState().isLoadingSessions).toBe(true);

      // Cleanup
      resolveFetch();
      await fetchPromise;
      expect(store.getState().isLoadingSessions).toBe(false);
    });

    it('should load sessions from API', async () => {
      // Arrange
      const mockSessions: SessionSummary[] = [
        { id: 's1', name: 'Session 1', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 5 },
        { id: 's2', name: 'Session 2', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 10 },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sessions: mockSessions }),
      });

      // Act
      await store.getState().fetchSessions();

      // Assert
      expect(store.getState().sessions).toHaveLength(2);
      expect(store.getState().sessions[0].name).toBe('Session 1');
    });

    it('should set error on failed fetch', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Server error' }),
      });

      // Act
      await store.getState().fetchSessions();

      // Assert
      expect(store.getState().error).toBe('Server error');
      expect(store.getState().isLoadingSessions).toBe(false);
    });
  });

  describe('createSession', () => {
    it('should create a new session', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'new-session-123',
            name: 'My New Session',
            config: {
              modelProvider: 'openai',
              modelName: 'gpt-4',
              temperature: 0.7,
              maxTokens: 4096,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      // Act
      const sessionId = await store.getState().createSession('My New Session');

      // Assert
      expect(sessionId).toBe('new-session-123');
      expect(store.getState().currentSession?.id).toBe('new-session-123');
    });

    it('should create session with custom config', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'session-custom',
            name: 'Custom Session',
            config: {
              modelProvider: 'anthropic',
              modelName: 'claude-3',
              temperature: 0.5,
              maxTokens: 8192,
            },
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          }),
      });

      // Act
      await store.getState().createSession('Custom Session', {
        modelProvider: 'anthropic',
        modelName: 'claude-3',
      });

      // Assert
      expect(store.getState().currentSession?.config.modelProvider).toBe('anthropic');
    });

    it('should return null on creation failure', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: 'Invalid session name' }),
      });

      // Act
      const sessionId = await store.getState().createSession('');

      // Assert
      expect(sessionId).toBeNull();
      expect(store.getState().error).toBe('Invalid session name');
    });
  });

  describe('loadSession', () => {
    it('should load session by ID', async () => {
      // Arrange
      const mockSession: Session = {
        id: 'session-load-test',
        name: 'Test Session',
        config: {
          modelProvider: 'openai',
          modelName: 'gpt-4',
          temperature: 0.7,
          maxTokens: 4096,
        },
        messages: [
          { id: 'm1', role: 'user', content: 'Hello', timestamp: Date.now() },
          { id: 'm2', role: 'assistant', content: 'Hi there!', timestamp: Date.now() },
        ],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSession),
      });

      // Act
      await store.getState().loadSession('session-load-test');

      // Assert
      expect(store.getState().currentSession?.id).toBe('session-load-test');
      expect(store.getState().currentSession?.messages).toHaveLength(2);
    });

    it('should set isLoadingSession while loading', async () => {
      // Arrange
      let resolveLoad!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveLoad = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    id: 's1',
                    name: 'Session',
                    config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
                    messages: [],
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                  }),
              });
          })
      );

      // Act
      const loadPromise = store.getState().loadSession('s1');

      // Assert
      expect(store.getState().isLoadingSession).toBe(true);

      // Cleanup
      resolveLoad();
      await loadPromise;
      expect(store.getState().isLoadingSession).toBe(false);
    });

    it('should set error on load failure', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Session not found' }),
      });

      // Act
      await store.getState().loadSession('non-existent');

      // Assert
      expect(store.getState().error).toBe('Session not found');
      expect(store.getState().currentSession).toBeNull();
    });
  });

  describe('deleteSession', () => {
    it('should delete session and remove from list', async () => {
      // Arrange - first add sessions to list
      store.setState({
        sessions: [
          { id: 's1', name: 'Session 1', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 },
          { id: 's2', name: 'Session 2', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 },
        ],
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      // Act
      await store.getState().deleteSession('s1');

      // Assert
      expect(store.getState().sessions).toHaveLength(1);
      expect(store.getState().sessions[0].id).toBe('s2');
    });

    it('should close current session if deleted', async () => {
      // Arrange
      store.setState({
        sessions: [{ id: 's1', name: 'Session 1', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 }],
        currentSession: {
          id: 's1',
          name: 'Session 1',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      // Act
      await store.getState().deleteSession('s1');

      // Assert
      expect(store.getState().currentSession).toBeNull();
    });
  });

  describe('renameSession', () => {
    it('should rename session', async () => {
      // Arrange
      store.setState({
        sessions: [{ id: 's1', name: 'Old Name', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 }],
        currentSession: {
          id: 's1',
          name: 'Old Name',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      // Act
      await store.getState().renameSession('s1', 'New Name');

      // Assert
      expect(store.getState().sessions[0].name).toBe('New Name');
      expect(store.getState().currentSession?.name).toBe('New Name');
    });
  });

  describe('sendMessage', () => {
    it('should add user message and set isSending', async () => {
      // Arrange
      store.setState({
        currentSession: {
          id: 's1',
          name: 'Test',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      let resolveSend!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveSend = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    message: { id: 'm2', role: 'assistant', content: 'Response', timestamp: Date.now() },
                  }),
              });
          })
      );

      // Act
      const sendPromise = store.getState().sendMessage('Hello');

      // Assert - user message should be added immediately
      expect(store.getState().currentSession?.messages).toHaveLength(1);
      expect(store.getState().currentSession?.messages[0].role).toBe('user');
      expect(store.getState().isSending).toBe(true);

      // Cleanup
      resolveSend();
      await sendPromise;
      expect(store.getState().isSending).toBe(false);
    });

    it('should set error if no current session', async () => {
      // Act
      await store.getState().sendMessage('Hello');

      // Assert
      expect(store.getState().error).toBe('No active session');
    });
  });

  describe('addMessage', () => {
    it('should add message to current session', () => {
      // Arrange
      store.setState({
        currentSession: {
          id: 's1',
          name: 'Test',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      const newMessage: ChatMessage = {
        id: 'm1',
        role: 'assistant',
        content: 'Hello!',
        timestamp: Date.now(),
      };

      // Act
      store.getState().addMessage(newMessage);

      // Assert
      expect(store.getState().currentSession?.messages).toHaveLength(1);
      expect(store.getState().currentSession?.messages[0].content).toBe('Hello!');
    });
  });

  describe('updateMessage', () => {
    it('should update existing message', () => {
      // Arrange
      store.setState({
        currentSession: {
          id: 's1',
          name: 'Test',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [{ id: 'm1', role: 'assistant', content: 'Partial...', timestamp: Date.now(), isStreaming: true }],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      // Act
      store.getState().updateMessage('m1', { content: 'Complete response', isStreaming: false });

      // Assert
      expect(store.getState().currentSession?.messages[0].content).toBe('Complete response');
      expect(store.getState().currentSession?.messages[0].isStreaming).toBe(false);
    });
  });

  describe('clearMessages', () => {
    it('should clear all messages in current session', async () => {
      // Arrange
      store.setState({
        currentSession: {
          id: 's1',
          name: 'Test',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [
            { id: 'm1', role: 'user', content: 'Hello', timestamp: Date.now() },
            { id: 'm2', role: 'assistant', content: 'Hi', timestamp: Date.now() },
          ],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      // Act
      await store.getState().clearMessages();

      // Assert
      expect(store.getState().currentSession?.messages).toHaveLength(0);
    });
  });

  describe('closeSession', () => {
    it('should set current session to null', () => {
      // Arrange
      store.setState({
        currentSession: {
          id: 's1',
          name: 'Test',
          config: { modelProvider: 'openai', modelName: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      // Act
      store.getState().closeSession();

      // Assert
      expect(store.getState().currentSession).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      // Arrange
      store.setState({ error: 'Some error' });

      // Act
      store.getState().clearError();

      // Assert
      expect(store.getState().error).toBeNull();
    });
  });
});
