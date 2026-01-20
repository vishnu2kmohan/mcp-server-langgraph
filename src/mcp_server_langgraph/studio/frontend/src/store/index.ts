/**
 * Redux Store Configuration
 *
 * Unified store using Redux Toolkit with RTK Query for API caching.
 * All state management has been consolidated to Redux slices.
 */

import {
  configureStore,
  createListenerMiddleware,
  isAnyOf,
} from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { api } from "../api";
import uiReducer from "./slices/uiSlice";
import personaReducer from "./slices/personaSlice";
import sessionReducer, { deleteSession } from "./slices/sessionSlice";
import projectReducer from "./slices/projectSlice";
import workflowReducer from "./slices/workflowSlice";
import artifactReducer from "./slices/artifactSlice";
import mcpReducer from "./slices/mcpSlice";
import authReducer from "./slices/authSlice";
import notificationReducer from "./slices/notificationSlice";
import observabilityReducer from "./slices/observabilitySlice";
import workspaceReducer, {
  workspacePersistenceMiddleware,
  removeTabsByEntityId,
} from "./slices/workspaceSlice";
// Studio Canvas state (Phase 7 integration)
import canvasReducer from "./slices/canvasSlice";
import backgroundAgentReducer from "./slices/backgroundAgentSlice";
import aiContextReducer from "./slices/aiContextSlice";
import complianceReducer from "./slices/complianceSlice";
import helpReducer from "./slices/helpSlice";
import alertReducer, { initializeSoundFromStorage } from "./slices/alertSlice";
import disclosureReducer from "./slices/disclosureSlice";
import nudgeReducer from "./slices/nudgeSlice";
import devToolsReducer from "./slices/devToolsSlice";
import langGraphReducer from "./slices/langGraphSlice";
import chatConnectionReducer from "./slices/chatConnectionSlice";
import executionModeReducer from "./slices/executionModeSlice";

// =============================================================================
// Listener Middleware for Cross-Slice Side Effects
// =============================================================================

const listenerMiddleware = createListenerMiddleware();

// Clean up orphan tabs when a session is deleted
listenerMiddleware.startListening({
  matcher: isAnyOf(deleteSession.fulfilled),
  effect: (action, listenerApi) => {
    // When a session is deleted, remove any tabs that reference it
    const sessionId = action.payload as string;
    listenerApi.dispatch(removeTabsByEntityId(sessionId));
  },
});

export const store = configureStore({
  reducer: {
    // RTK Query API reducer (includes feature flags via useGetFeatureFlagsQuery)
    [api.reducerPath]: api.reducer,
    // UI state
    ui: uiReducer,
    // Persona/RBAC state
    persona: personaReducer,
    // Session state
    session: sessionReducer,
    // Project state
    project: projectReducer,
    // Workflow builder state
    workflow: workflowReducer,
    // Artifact state (charts, tables, code, etc.)
    artifact: artifactReducer,
    // MCP (Model Context Protocol) state
    mcp: mcpReducer,
    // Authentication state
    auth: authReducer,
    // Notifications state
    notifications: notificationReducer,
    // Observability filter state
    observability: observabilityReducer,
    // Workspace layout state (JupyterLab-inspired)
    workspace: workspaceReducer,
    // Studio Canvas layout state (Phase 7 - separate from workspace)
    canvas: canvasReducer,
    // Background agent state (Phase 7 - AI agents)
    backgroundAgent: backgroundAgentReducer,
    // AI context and suggestions state (Phase 7)
    aiContext: aiContextReducer,
    // Compliance dashboard state (Phase 7)
    compliance: complianceReducer,
    // Help pane state (Phase 7)
    help: helpReducer,
    // Alert management state (Phase 7 - Admin dashboard)
    alerts: alertReducer,
    // Progressive disclosure state (Phase 7 - UX enhancement)
    disclosure: disclosureReducer,
    // Nudge state (Phase 7 - Contextual hints and feature discovery)
    nudge: nudgeReducer,
    // DevTools panel state (Chrome DevTools-like debugging)
    devTools: devToolsReducer,
    // LangGraph execution events (for DevTools time-travel debugging)
    langGraph: langGraphReducer,
    // Chat connection awareness (auth requirements, setup, suggestions)
    chatConnection: chatConnectionReducer,
    // Execution mode toggle and plan approval workflow
    executionMode: executionModeReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .prepend(listenerMiddleware.middleware)
      .concat(api.middleware)
      .concat(workspacePersistenceMiddleware),
  devTools: process.env.NODE_ENV !== "production",
});

// Enable refetchOnFocus and refetchOnReconnect
setupListeners(store.dispatch);

// Initialize alert sound preference from localStorage
store.dispatch(initializeSoundFromStorage());

// Infer types from store
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
