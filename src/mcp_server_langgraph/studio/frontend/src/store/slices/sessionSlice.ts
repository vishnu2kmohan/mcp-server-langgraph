/**
 * Session Slice
 *
 * Redux slice for managing chat session state including:
 * - Session CRUD operations
 * - Message management
 * - Streaming state
 * - Persistence to backend
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import type {
  SessionState,
  ClientSession,
  SessionSummary,
  SessionConfig,
  ChatMessage,
} from "../../types/session";
import { DEFAULT_SESSION_CONFIG } from "../../types/session";

/**
 * Generate unique message ID
 */
function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Get auth headers for API requests.
 * Matches the logic in baseQueryWithReauth.ts for consistency.
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Check multiple storage keys for backward compatibility:
  // - "access_token": Used by OAuth2 PKCE callback
  // - "auth_token": Legacy key (deprecated)
  const token =
    localStorage.getItem("access_token") || localStorage.getItem("auth_token");

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
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
  hasMore: false,
  totalCount: 0,
  isLoadingMore: false,
  cursor: null,
};

// ==============================================================================
// Types
// ==============================================================================

interface FetchSessionsParams {
  limit?: number;
  search?: string;
  status?: string;
  cursor?: string;
}

interface PaginatedSessionsResponse {
  items: SessionSummary[];
  total: number;
  next_cursor: string | null;
}

// ==============================================================================
// Async Thunks
// ==============================================================================

/**
 * Fetch list of sessions with pagination support
 */
export const fetchSessions = createAsyncThunk<
  PaginatedSessionsResponse,
  FetchSessionsParams | void,
  { rejectValue: string }
>("session/fetchSessions", async (params, { rejectWithValue }) => {
  try {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.limit !== undefined)
        searchParams.set("limit", String(params.limit));
      if (params.search) searchParams.set("search", params.search);
      if (params.status) searchParams.set("status", params.status);
      if (params.cursor) searchParams.set("cursor", params.cursor);
    }

    const queryString = searchParams.toString();
    const url = queryString
      ? `/api/v1/sessions?${queryString}`
      : "/api/v1/sessions";
    const response = await fetch(url, {
      headers: getAuthHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to fetch sessions");
    }

    const data = await response.json();
    // Support multiple response formats:
    // 1. CursorPaginatedResponse: { data: [], pagination: { count, next_cursor, ... } }
    // 2. Legacy paginated: { items: [], total: N, next_cursor: "..." }
    // 3. Legacy array: { sessions: [] }
    if (data.pagination) {
      // New CursorPaginatedResponse format from backend
      return {
        items: data.data || [],
        total: data.pagination.count ?? data.data?.length ?? 0,
        next_cursor: data.pagination.next_cursor ?? null,
      };
    }
    if (Array.isArray(data.sessions)) {
      // Legacy sessions array format
      return {
        items: data.sessions,
        total: data.sessions.length,
        next_cursor: null,
      };
    }
    // Legacy paginated response
    return {
      items: data.items || data.data || [],
      total: data.total ?? data.items?.length ?? 0,
      next_cursor: data.next_cursor ?? null,
    };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to fetch sessions",
    );
  }
});

/**
 * Fetch more sessions (pagination - append to existing list)
 */
export const fetchMoreSessions = createAsyncThunk<
  PaginatedSessionsResponse,
  void,
  { state: { session: SessionState }; rejectValue: string }
>("session/fetchMoreSessions", async (_, { getState, rejectWithValue }) => {
  try {
    const { cursor } = getState().session;
    const searchParams = new URLSearchParams();
    if (cursor) searchParams.set("cursor", cursor);

    const queryString = searchParams.toString();
    const url = queryString
      ? `/api/v1/sessions?${queryString}`
      : "/api/v1/sessions";
    const response = await fetch(url, {
      headers: getAuthHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to fetch more sessions");
    }

    const data = await response.json();
    // Support CursorPaginatedResponse format from backend
    if (data.pagination) {
      return {
        items: data.data || [],
        total: data.pagination.count ?? data.data?.length ?? 0,
        next_cursor: data.pagination.next_cursor ?? null,
      };
    }
    return {
      items: data.items || data.data || [],
      total: data.total ?? data.items?.length ?? 0,
      next_cursor: data.next_cursor ?? null,
    };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to fetch more sessions",
    );
  }
});

/**
 * Transform API session config (snake_case) to client format (camelCase).
 * Backend SessionConfig has: model, temperature, max_tokens
 * Frontend SessionConfig has: modelName, modelProvider, temperature, maxTokens
 */
function transformApiConfig(
  apiConfig: Record<string, unknown> | undefined,
): Partial<SessionConfig> {
  if (!apiConfig) return {};

  const config: Partial<SessionConfig> = {};

  // Map 'model' to 'modelName' (backend uses 'model' field)
  if (typeof apiConfig.model === "string") {
    config.modelName = apiConfig.model;
  } else if (typeof apiConfig.modelName === "string") {
    // Also support camelCase if already transformed
    config.modelName = apiConfig.modelName;
  }

  // Map 'model_provider' or 'modelProvider'
  if (typeof apiConfig.model_provider === "string") {
    config.modelProvider =
      apiConfig.model_provider as SessionConfig["modelProvider"];
  } else if (typeof apiConfig.modelProvider === "string") {
    config.modelProvider =
      apiConfig.modelProvider as SessionConfig["modelProvider"];
  }

  // Map 'max_tokens' to 'maxTokens'
  if (typeof apiConfig.max_tokens === "number") {
    config.maxTokens = apiConfig.max_tokens;
  } else if (typeof apiConfig.maxTokens === "number") {
    config.maxTokens = apiConfig.maxTokens;
  }

  // Temperature (same name in both)
  if (typeof apiConfig.temperature === "number") {
    config.temperature = apiConfig.temperature;
  }

  // System prompt
  if (typeof apiConfig.system_prompt === "string") {
    config.systemPrompt = apiConfig.system_prompt;
  } else if (typeof apiConfig.systemPrompt === "string") {
    config.systemPrompt = apiConfig.systemPrompt;
  }

  return config;
}

/**
 * Transform API session response to ClientSession format.
 * Converts snake_case to camelCase and applies default config.
 */
function transformApiSession(
  apiSession: Record<string, unknown>,
  providedConfig?: Partial<SessionConfig>,
): ClientSession {
  // Extract and transform config from API response
  const apiConfig = transformApiConfig(
    apiSession.config as Record<string, unknown> | undefined,
  );

  return {
    id: apiSession.id as string,
    name: (apiSession.name as string) || "Untitled",
    config: {
      ...DEFAULT_SESSION_CONFIG,
      ...apiConfig, // Apply config from API response
      ...providedConfig, // Override with explicitly provided config
    },
    messages: Array.isArray(apiSession.messages)
      ? (apiSession.messages as ChatMessage[])
      : [],
    createdAt:
      typeof apiSession.created_at === "string"
        ? new Date(apiSession.created_at).getTime()
        : Date.now(),
    updatedAt:
      typeof apiSession.updated_at === "string"
        ? new Date(apiSession.updated_at).getTime()
        : Date.now(),
    organizationId: apiSession.organization_id as string | undefined,
  };
}

/**
 * Create a new session
 */
export const createSession = createAsyncThunk<
  ClientSession,
  { name: string; config?: Partial<SessionConfig> },
  { rejectValue: string }
>("session/createSession", async ({ name, config }, { rejectWithValue }) => {
  try {
    const response = await fetch("/api/v1/sessions", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, config }),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to create session");
    }

    const apiSession = await response.json();
    return transformApiSession(apiSession, config);
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to create session",
    );
  }
});

/**
 * Load a session by ID
 */
export const loadSession = createAsyncThunk<
  ClientSession,
  string,
  { rejectValue: string }
>("session/loadSession", async (sessionId, { rejectWithValue }) => {
  try {
    const response = await fetch(`/api/v1/sessions/${sessionId}`, {
      headers: getAuthHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to load session");
    }

    const apiSession = await response.json();
    return transformApiSession(apiSession);
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to load session",
    );
  }
});

/**
 * Delete a session
 */
export const deleteSession = createAsyncThunk<
  string,
  string,
  { rejectValue: string }
>("session/deleteSession", async (sessionId, { rejectWithValue }) => {
  try {
    const response = await fetch(`/api/v1/sessions/${sessionId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to delete session");
    }

    return sessionId;
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to delete session",
    );
  }
});

/**
 * Rename a session
 */
export const renameSession = createAsyncThunk<
  { sessionId: string; name: string },
  { sessionId: string; name: string },
  { rejectValue: string }
>("session/renameSession", async ({ sessionId, name }, { rejectWithValue }) => {
  try {
    const response = await fetch(`/api/v1/sessions/${sessionId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ name }),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to rename session");
    }

    return { sessionId, name };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to rename session",
    );
  }
});

/**
 * Send a message in the current session
 */
export const sendMessage = createAsyncThunk<
  ChatMessage | null,
  string,
  { state: { session: SessionState }; rejectValue: string }
>(
  "session/sendMessage",
  async (content, { getState, dispatch, rejectWithValue }) => {
    const { currentSession } = getState().session;

    if (!currentSession) {
      return rejectWithValue("No active session");
    }

    // Add user message immediately via separate action
    const userMessage: ChatMessage = {
      id: generateMessageId(),
      role: "user",
      content,
      timestamp: Date.now(),
    };
    dispatch(addUserMessage(userMessage));

    try {
      const response = await fetch(
        `/api/v1/sessions/${currentSession.id}/messages`,
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({ content }),
          credentials: "include",
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to send message");
      }

      const data = await response.json();
      return data.message || null;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to send message",
      );
    }
  },
);

/**
 * Clear messages in the current session
 */
export const clearMessages = createAsyncThunk<
  void,
  void,
  { state: { session: SessionState }; rejectValue: string }
>("session/clearMessages", async (_, { getState, rejectWithValue }) => {
  const { currentSession } = getState().session;

  if (!currentSession) {
    return;
  }

  try {
    const response = await fetch(
      `/api/v1/sessions/${currentSession.id}/messages`,
      {
        method: "DELETE",
        headers: getAuthHeaders(),
        credentials: "include",
      },
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to clear messages");
    }
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to clear messages",
    );
  }
});

// ==============================================================================
// Slice
// ==============================================================================

export const sessionSlice = createSlice({
  name: "session",
  initialState: initialSessionState,
  reducers: {
    /**
     * Add user message to current session (optimistic update)
     */
    addUserMessage: (state, action: PayloadAction<ChatMessage>) => {
      if (state.currentSession) {
        state.currentSession.messages.push(action.payload);
        state.isSending = true;
        state.error = null;
      }
    },

    /**
     * Add a message to the current session (for streaming)
     */
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      if (state.currentSession) {
        state.currentSession.messages.push(action.payload);
      }
    },

    /**
     * Update a message in the current session
     */
    updateMessage: (
      state,
      action: PayloadAction<{
        messageId: string;
        updates: Partial<ChatMessage>;
      }>,
    ) => {
      if (state.currentSession) {
        const { messageId, updates } = action.payload;
        const messageIndex = state.currentSession.messages.findIndex(
          (m) => m.id === messageId,
        );
        if (messageIndex >= 0) {
          state.currentSession.messages[messageIndex] = {
            ...state.currentSession.messages[messageIndex],
            ...updates,
          };
        }
      }
    },

    /**
     * Delete a message from the current session
     */
    deleteMessage: (state, action: PayloadAction<string>) => {
      if (state.currentSession) {
        const messageId = action.payload;
        state.currentSession.messages = state.currentSession.messages.filter(
          (m) => m.id !== messageId,
        );
      }
    },

    /**
     * Close current session
     */
    closeSession: (state) => {
      state.currentSession = null;
    },

    /**
     * Clear error
     */
    clearError: (state) => {
      state.error = null;
    },

    /**
     * Set sessions (for testing)
     */
    setSessions: (state, action: PayloadAction<SessionSummary[]>) => {
      state.sessions = action.payload;
    },

    /**
     * Set current session (for testing)
     */
    setCurrentSession: (state, action: PayloadAction<ClientSession | null>) => {
      state.currentSession = action.payload;
    },

    /**
     * Reset session state
     */
    resetSession: () => initialSessionState,
  },
  extraReducers: (builder) => {
    // fetchSessions
    builder
      .addCase(fetchSessions.pending, (state) => {
        state.isLoadingSessions = true;
        state.error = null;
      })
      .addCase(fetchSessions.fulfilled, (state, action) => {
        state.sessions = action.payload.items;
        state.totalCount = action.payload.total;
        state.cursor = action.payload.next_cursor;
        state.hasMore = action.payload.next_cursor !== null;
        state.isLoadingSessions = false;
        state.error = null;
      })
      .addCase(fetchSessions.rejected, (state, action) => {
        state.isLoadingSessions = false;
        state.error = action.payload || "Failed to fetch sessions";
      });

    // fetchMoreSessions
    builder
      .addCase(fetchMoreSessions.pending, (state) => {
        state.isLoadingMore = true;
        state.error = null;
      })
      .addCase(fetchMoreSessions.fulfilled, (state, action) => {
        // Append new sessions to existing list, deduplicating by ID
        const existingIds = new Set(state.sessions.map((s) => s.id));
        const newSessions = action.payload.items.filter(
          (s) => !existingIds.has(s.id),
        );
        state.sessions = [...state.sessions, ...newSessions];
        state.totalCount = action.payload.total;
        state.cursor = action.payload.next_cursor;
        state.hasMore = action.payload.next_cursor !== null;
        state.isLoadingMore = false;
        state.error = null;
      })
      .addCase(fetchMoreSessions.rejected, (state, action) => {
        state.isLoadingMore = false;
        state.error = action.payload || "Failed to fetch more sessions";
      });

    // createSession
    builder
      .addCase(createSession.fulfilled, (state, action) => {
        const session = action.payload;
        // Check if session already exists (prevent duplicates from race conditions)
        const existsIndex = state.sessions.findIndex(
          (s) => s.id === session.id,
        );
        if (existsIndex >= 0) {
          // Update existing session instead of adding duplicate
          state.sessions[existsIndex] = {
            id: session.id,
            name: session.name,
            createdAt: session.createdAt,
            updatedAt: session.updatedAt,
            messageCount: 0,
          };
          // Don't increment totalCount for existing session
        } else {
          state.sessions.unshift({
            id: session.id,
            name: session.name,
            createdAt: session.createdAt,
            updatedAt: session.updatedAt,
            messageCount: 0,
          });
          // Increment totalCount for new session
          state.totalCount = (state.totalCount ?? 0) + 1;
        }
        state.currentSession = session;
        state.error = null;
      })
      .addCase(createSession.rejected, (state, action) => {
        state.error = action.payload || "Failed to create session";
      });

    // loadSession
    builder
      .addCase(loadSession.pending, (state) => {
        state.isLoadingSession = true;
        state.error = null;
      })
      .addCase(loadSession.fulfilled, (state, action) => {
        state.currentSession = action.payload;
        state.isLoadingSession = false;
        state.error = null;
      })
      .addCase(loadSession.rejected, (state, action) => {
        state.currentSession = null;
        state.isLoadingSession = false;
        state.error = action.payload || "Failed to load session";
      });

    // deleteSession
    builder
      .addCase(deleteSession.fulfilled, (state, action) => {
        const deletedId = action.payload;
        state.sessions = state.sessions.filter((s) => s.id !== deletedId);
        if (state.currentSession?.id === deletedId) {
          state.currentSession = null;
        }
        state.error = null;
      })
      .addCase(deleteSession.rejected, (state, action) => {
        state.error = action.payload || "Failed to delete session";
      });

    // renameSession
    builder
      .addCase(renameSession.fulfilled, (state, action) => {
        const { sessionId, name } = action.payload;
        const updatedAt = Date.now();

        const sessionIndex = state.sessions.findIndex(
          (s) => s.id === sessionId,
        );
        if (sessionIndex >= 0) {
          state.sessions[sessionIndex].name = name;
          state.sessions[sessionIndex].updatedAt = updatedAt;
        }

        if (state.currentSession?.id === sessionId) {
          state.currentSession.name = name;
          state.currentSession.updatedAt = updatedAt;
        }

        state.error = null;
      })
      .addCase(renameSession.rejected, (state, action) => {
        state.error = action.payload || "Failed to rename session";
      });

    // sendMessage
    builder
      .addCase(sendMessage.fulfilled, (state, action) => {
        if (action.payload && state.currentSession) {
          state.currentSession.messages.push(action.payload);
        }
        state.isSending = false;
        state.error = null;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isSending = false;
        state.error = action.payload || "Failed to send message";
      });

    // clearMessages
    builder
      .addCase(clearMessages.fulfilled, (state) => {
        if (state.currentSession) {
          state.currentSession.messages = [];
        }
        state.error = null;
      })
      .addCase(clearMessages.rejected, (state, action) => {
        state.error = action.payload || "Failed to clear messages";
      });
  },
});

export const {
  addUserMessage,
  addMessage,
  updateMessage,
  deleteMessage,
  closeSession,
  clearError,
  setSessions,
  setCurrentSession,
  resetSession,
} = sessionSlice.actions;

// ==============================================================================
// Selectors
// ==============================================================================

type SessionRootState = { session: SessionState };

export const selectSessions = (state: SessionRootState) =>
  state.session.sessions;
export const selectCurrentSession = (state: SessionRootState) =>
  state.session.currentSession;
export const selectMessages = (state: SessionRootState) =>
  state.session.currentSession?.messages || [];
export const selectIsLoadingSessions = (state: SessionRootState) =>
  state.session.isLoadingSessions;
export const selectIsLoadingSession = (state: SessionRootState) =>
  state.session.isLoadingSession;
export const selectIsSending = (state: SessionRootState) =>
  state.session.isSending;
export const selectSessionError = (state: SessionRootState) =>
  state.session.error;
export const selectSessionById =
  (sessionId: string) => (state: SessionRootState) =>
    state.session.sessions.find((s) => s.id === sessionId);

// Pagination selectors
export const selectHasMore = (state: SessionRootState) =>
  state.session.hasMore ?? false;
export const selectTotalCount = (state: SessionRootState) =>
  state.session.totalCount ?? 0;
export const selectIsLoadingMore = (state: SessionRootState) =>
  state.session.isLoadingMore ?? false;
export const selectCursor = (state: SessionRootState) =>
  state.session.cursor ?? null;

export default sessionSlice.reducer;
