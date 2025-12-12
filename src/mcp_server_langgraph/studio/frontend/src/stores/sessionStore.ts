/**
 * Session Store
 *
 * Zustand store for managing chat session state including:
 * - Session CRUD operations
 * - Message management
 * - Streaming state
 * - Persistence to backend
 */

import { create, StateCreator } from 'zustand';
import type {
  SessionStore,
  SessionState,
  Session,
  SessionSummary,
  SessionConfig,
  ChatMessage,
  DEFAULT_SESSION_CONFIG,
} from '../types/session';

/**
 * Generate unique message ID
 */
function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Initial session state
 */
export const initialSessionState: SessionState = {
  sessions: [],
  currentSession: null,
  isLoadingSessions: false,
  isLoadingSession: false,
  isSending: false,
  error: null,
};

/**
 * Create the session store state and actions
 */
const createSessionStore: StateCreator<SessionStore> = (set, get) => ({
  ...initialSessionState,

  /**
   * Fetch list of sessions
   */
  fetchSessions: async () => {
    set({ isLoadingSessions: true, error: null });

    try {
      const response = await fetch('/api/v1/sessions');

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch sessions');
      }

      const data = await response.json();

      set({
        sessions: data.sessions || [],
        isLoadingSessions: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoadingSessions: false,
        error: error instanceof Error ? error.message : 'Failed to fetch sessions',
      });
    }
  },

  /**
   * Create a new session
   */
  createSession: async (name: string, config?: Partial<SessionConfig>): Promise<string | null> => {
    set({ error: null });

    try {
      const response = await fetch('/api/v1/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, config }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create session');
      }

      const session: Session = await response.json();

      // Add to sessions list and set as current
      set((state) => ({
        sessions: [
          {
            id: session.id,
            name: session.name,
            createdAt: session.createdAt,
            updatedAt: session.updatedAt,
            messageCount: 0,
          },
          ...state.sessions,
        ],
        currentSession: session,
        error: null,
      }));

      return session.id;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create session',
      });
      return null;
    }
  },

  /**
   * Load a session by ID
   */
  loadSession: async (sessionId: string) => {
    set({ isLoadingSession: true, error: null });

    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load session');
      }

      const session: Session = await response.json();

      set({
        currentSession: session,
        isLoadingSession: false,
        error: null,
      });
    } catch (error) {
      set({
        currentSession: null,
        isLoadingSession: false,
        error: error instanceof Error ? error.message : 'Failed to load session',
      });
    }
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string) => {
    set({ error: null });

    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete session');
      }

      const { currentSession } = get();

      set((state) => ({
        sessions: state.sessions.filter((s) => s.id !== sessionId),
        // Close current session if it's being deleted
        currentSession: currentSession?.id === sessionId ? null : currentSession,
        error: null,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete session',
      });
    }
  },

  /**
   * Rename a session
   */
  renameSession: async (sessionId: string, name: string) => {
    set({ error: null });

    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to rename session');
      }

      const { currentSession } = get();

      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === sessionId ? { ...s, name, updatedAt: Date.now() } : s
        ),
        currentSession:
          currentSession?.id === sessionId
            ? { ...currentSession, name, updatedAt: Date.now() }
            : currentSession,
        error: null,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to rename session',
      });
    }
  },

  /**
   * Send a message in the current session
   */
  sendMessage: async (content: string) => {
    const { currentSession } = get();

    if (!currentSession) {
      set({ error: 'No active session' });
      return;
    }

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    set((state) => ({
      currentSession: state.currentSession
        ? {
            ...state.currentSession,
            messages: [...state.currentSession.messages, userMessage],
          }
        : null,
      isSending: true,
      error: null,
    }));

    try {
      const response = await fetch(`/api/v1/sessions/${currentSession.id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send message');
      }

      const data = await response.json();

      // Add assistant message
      if (data.message) {
        set((state) => ({
          currentSession: state.currentSession
            ? {
                ...state.currentSession,
                messages: [...state.currentSession.messages, data.message],
              }
            : null,
          isSending: false,
          error: null,
        }));
      } else {
        set({ isSending: false });
      }
    } catch (error) {
      set({
        isSending: false,
        error: error instanceof Error ? error.message : 'Failed to send message',
      });
    }
  },

  /**
   * Add a message to the current session
   */
  addMessage: (message: ChatMessage) => {
    set((state) => ({
      currentSession: state.currentSession
        ? {
            ...state.currentSession,
            messages: [...state.currentSession.messages, message],
          }
        : null,
    }));
  },

  /**
   * Update a message in the current session
   */
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => {
    set((state) => ({
      currentSession: state.currentSession
        ? {
            ...state.currentSession,
            messages: state.currentSession.messages.map((m) =>
              m.id === messageId ? { ...m, ...updates } : m
            ),
          }
        : null,
    }));
  },

  /**
   * Clear messages in the current session
   */
  clearMessages: async () => {
    const { currentSession } = get();

    if (!currentSession) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/sessions/${currentSession.id}/messages`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to clear messages');
      }

      set((state) => ({
        currentSession: state.currentSession
          ? {
              ...state.currentSession,
              messages: [],
            }
          : null,
        error: null,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to clear messages',
      });
    }
  },

  /**
   * Close current session
   */
  closeSession: () => {
    set({ currentSession: null });
  },

  /**
   * Clear error
   */
  clearError: () => {
    set({ error: null });
  },
});

/**
 * Session store with Zustand
 */
export const useSessionStore = create<SessionStore>()(createSessionStore);

/**
 * Create a test store without persistence
 */
export const createTestSessionStore = () => create<SessionStore>()(createSessionStore);
