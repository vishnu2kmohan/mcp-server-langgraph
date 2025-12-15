/**
 * Redux Store Configuration
 *
 * Unified store using Redux Toolkit with RTK Query for API caching.
 * All state management has been consolidated to Redux slices.
 */

import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { api } from "../api";
import uiReducer from "./slices/uiSlice";
import personaReducer from "./slices/personaSlice";
import sessionReducer from "./slices/sessionSlice";
import projectReducer from "./slices/projectSlice";
import workflowReducer from "./slices/workflowSlice";
import artifactReducer from "./slices/artifactSlice";
import mcpReducer from "./slices/mcpSlice";
import authReducer from "./slices/authSlice";
import notificationReducer from "./slices/notificationSlice";

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
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(api.middleware),
  devTools: process.env.NODE_ENV !== "production",
});

// Enable refetchOnFocus and refetchOnReconnect
setupListeners(store.dispatch);

// Infer types from store
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
