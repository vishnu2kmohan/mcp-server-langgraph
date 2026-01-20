/**
 * chatConnectionSlice
 *
 * Redux slice for managing connection awareness in chat.
 * Handles auth_required events from SSE stream, connection setup state,
 * and proactive connector suggestions.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

/**
 * Auth requirement with tracking metadata
 */
export interface AuthRequirement {
  /** Generated UUID for tracking */
  id: string;
  /** Qualified tool name that triggered the auth requirement */
  toolName: string;
  /** Template ID for suggested connection template */
  templateId: string | null;
  /** Existing connection ID that needs re-authentication, if any */
  connectionId: string | null;
  /** User-friendly message explaining the auth requirement */
  message: string;
  /** Original message ID to retry after auth, if any */
  retryMessageId: string | null;
  /** Timestamp when this requirement was added */
  timestamp: number;
}

/**
 * Connection setup status
 */
export type ConnectionSetupStatus =
  | "idle"
  | "configuring"
  | "authenticating"
  | "testing"
  | "complete"
  | "error";

/**
 * Active connection setup state
 */
export interface ActiveConnectionSetup {
  templateId: string;
  connectionId?: string;
  status: ConnectionSetupStatus;
  error?: string;
}

/**
 * Minimal template info for suggestions (avoid full type dependency)
 */
export interface SuggestionTemplate {
  id: string;
  name: string;
}

/**
 * Connector suggestions state
 */
export interface ConnectorSuggestions {
  visible: boolean;
  templates: SuggestionTemplate[];
  query: string;
}

/**
 * Chat connection state
 */
export interface ChatConnectionState {
  /** Pending auth requirements from stream */
  pendingAuthRequirements: AuthRequirement[];
  /** Active inline connection setup */
  activeConnectionSetup: ActiveConnectionSetup | null;
  /** Suggestion bar state */
  connectorSuggestions: ConnectorSuggestions;
  /** Configured connection template IDs (for filtering suggestions) */
  configuredTemplateIds: string[];
}

const initialState: ChatConnectionState = {
  pendingAuthRequirements: [],
  activeConnectionSetup: null,
  connectorSuggestions: {
    visible: false,
    templates: [],
    query: "" },
  configuredTemplateIds: [],
};

/**
 * Generate a simple unique ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export const chatConnectionSlice = createSlice({
  name: "chatConnection",
  initialState,
  reducers: {
    /**
     * Add an auth requirement from SSE stream
     */
    addAuthRequirement: (
      state,
      action: PayloadAction<{
        toolName: string;
        templateId: string | null;
        connectionId: string | null;
        message: string;
        retryMessageId: string | null;
      }>,
    ) => {
      state.pendingAuthRequirements.push({
        ...action.payload,
        id: generateId(),
        timestamp: Date.now(),
      });
    },

    /**
     * Dismiss an auth requirement by ID
     */
    dismissAuthRequirement: (state, action: PayloadAction<string>) => {
      state.pendingAuthRequirements = state.pendingAuthRequirements.filter(
        (req) => req.id !== action.payload,
      );
    },

    /**
     * Clear all pending auth requirements
     */
    clearPendingAuthRequirements: (state) => {
      state.pendingAuthRequirements = [];
    },

    /**
     * Start connection setup flow
     */
    startConnectionSetup: (
      state,
      action: PayloadAction<{ templateId: string; connectionId?: string }>,
    ) => {
      state.activeConnectionSetup = {
        templateId: action.payload.templateId,
        connectionId: action.payload.connectionId,
        status: "configuring",
        error: undefined,
      };
    },

    /**
     * Update connection setup status
     */
    updateConnectionSetupStatus: (
      state,
      action: PayloadAction<{ status: ConnectionSetupStatus; error?: string }>,
    ) => {
      if (state.activeConnectionSetup) {
        state.activeConnectionSetup.status = action.payload.status;
        state.activeConnectionSetup.error = action.payload.error;
      }
    },

    /**
     * Complete connection setup and add to configured list
     */
    completeConnectionSetup: (state) => {
      if (state.activeConnectionSetup) {
        // Add to configured list
        const templateId = state.activeConnectionSetup.templateId;
        if (!state.configuredTemplateIds.includes(templateId)) {
          state.configuredTemplateIds.push(templateId);
        }
      }
      state.activeConnectionSetup = null;
    },

    /**
     * Show connector suggestions
     */
    showSuggestions: (
      state,
      action: PayloadAction<{ templates: SuggestionTemplate[]; query: string }>,
    ) => {
      state.connectorSuggestions = {
        visible: true,
        templates: action.payload.templates,
        query: action.payload.query,
      };
    },

    /**
     * Hide connector suggestions
     */
    hideSuggestions: (state) => {
      state.connectorSuggestions.visible = false;
    },

    /**
     * Set configured template IDs (from existing connections)
     */
    setConfiguredTemplateIds: (state, action: PayloadAction<string[]>) => {
      state.configuredTemplateIds = action.payload;
    },
  },
});

// Export actions
export const {
  addAuthRequirement,
  dismissAuthRequirement,
  clearPendingAuthRequirements,
  startConnectionSetup,
  updateConnectionSetupStatus,
  completeConnectionSetup,
  showSuggestions,
  hideSuggestions,
  setConfiguredTemplateIds,
} = chatConnectionSlice.actions;

// Selectors
// Use a generic type that accepts any state containing chatConnection
// This allows compatibility with both RootState and partial test states
export const selectPendingAuthRequirements = (
  state: { chatConnection: ChatConnectionState },
) => state.chatConnection.pendingAuthRequirements;

export const selectActiveConnectionSetup = (
  state: { chatConnection: ChatConnectionState },
) => state.chatConnection.activeConnectionSetup;

export const selectConnectorSuggestions = (
  state: { chatConnection: ChatConnectionState },
) => state.chatConnection.connectorSuggestions;

export const selectConfiguredTemplateIds = (
  state: { chatConnection: ChatConnectionState },
) => state.chatConnection.configuredTemplateIds;

// Export reducer as default
export default chatConnectionSlice.reducer;
