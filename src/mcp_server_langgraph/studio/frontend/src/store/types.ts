/**
 * Store Types - Isolated Type Definitions
 *
 * This file exports RootState and AppDispatch types WITHOUT importing
 * the full store or api modules. This allows tests to import these types
 * without triggering OOM from RTK Query initialization.
 *
 * IMPORTANT: This file should ONLY contain type imports and type definitions.
 * No value imports from store/index.ts or api/index.ts!
 *
 * Usage in components:
 *   import type { RootState, AppDispatch } from "../store/types";
 *
 * Usage in test files:
 *   import type { RootState, SliceStates } from "../store/types";
 *   // Then create minimal test store with just needed slices
 */

import type { ThunkDispatch, UnknownAction } from "@reduxjs/toolkit";

// =============================================================================
// Import state types from individual slices (type-only imports)
// These do NOT trigger module evaluation since they're type-only
// =============================================================================

// Import initial states and infer types from them
import type uiReducer from "./slices/uiSlice";
import type personaReducer from "./slices/personaSlice";
import type sessionReducer from "./slices/sessionSlice";
import type projectReducer from "./slices/projectSlice";
import type workflowReducer from "./slices/workflowSlice";
import type artifactReducer from "./slices/artifactSlice";
import type mcpReducer from "./slices/mcpSlice";
import type authReducer from "./slices/authSlice";
import type notificationReducer from "./slices/notificationSlice";
import type observabilityReducer from "./slices/observabilitySlice";
import type workspaceReducer from "./slices/workspaceSlice";
import type canvasReducer from "./slices/canvasSlice";
import type backgroundAgentReducer from "./slices/backgroundAgentSlice";
import type aiContextReducer from "./slices/aiContextSlice";
import type complianceReducer from "./slices/complianceSlice";
import type helpReducer from "./slices/helpSlice";
import type alertReducer from "./slices/alertSlice";
import type disclosureReducer from "./slices/disclosureSlice";
import type nudgeReducer from "./slices/nudgeSlice";

// =============================================================================
// Slice State Types (inferred from reducer return types)
// =============================================================================

type UIState = ReturnType<typeof uiReducer>;
type PersonaState = ReturnType<typeof personaReducer>;
type SessionState = ReturnType<typeof sessionReducer>;
type ProjectState = ReturnType<typeof projectReducer>;
type WorkflowState = ReturnType<typeof workflowReducer>;
type ArtifactState = ReturnType<typeof artifactReducer>;
type MCPState = ReturnType<typeof mcpReducer>;
type AuthState = ReturnType<typeof authReducer>;
type NotificationState = ReturnType<typeof notificationReducer>;
type ObservabilityState = ReturnType<typeof observabilityReducer>;
type WorkspaceState = ReturnType<typeof workspaceReducer>;
type CanvasState = ReturnType<typeof canvasReducer>;
type BackgroundAgentState = ReturnType<typeof backgroundAgentReducer>;
type AIContextState = ReturnType<typeof aiContextReducer>;
type ComplianceState = ReturnType<typeof complianceReducer>;
type HelpState = ReturnType<typeof helpReducer>;
type AlertState = ReturnType<typeof alertReducer>;
type DisclosureState = ReturnType<typeof disclosureReducer>;
type NudgeState = ReturnType<typeof nudgeReducer>;

// =============================================================================
// SliceStates - Individual state types for test stores
// =============================================================================

/**
 * Individual slice state types for creating partial test stores.
 *
 * Usage:
 *   const testStore = configureStore({
 *     reducer: { workflow: workflowReducer },
 *     preloadedState: { workflow: partialState as SliceStates['workflow'] }
 *   });
 */
export interface SliceStates {
  ui: UIState;
  persona: PersonaState;
  session: SessionState;
  project: ProjectState;
  workflow: WorkflowState;
  artifact: ArtifactState;
  mcp: MCPState;
  auth: AuthState;
  notifications: NotificationState;
  observability: ObservabilityState;
  workspace: WorkspaceState;
  canvas: CanvasState;
  backgroundAgent: BackgroundAgentState;
  aiContext: AIContextState;
  compliance: ComplianceState;
  help: HelpState;
  alerts: AlertState;
  disclosure: DisclosureState;
  nudge: NudgeState;
}

// =============================================================================
// RootState - Complete store state type
// =============================================================================

/**
 * Placeholder type for RTK Query api state.
 * We use `unknown` to avoid importing the actual api module which causes OOM.
 * This allows selectors to type-check while keeping the types isolated.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ApiState = any;

/**
 * RootState type constructed from slice types.
 *
 * This matches the shape of the real store state but is defined
 * independently to avoid importing store/index.ts.
 *
 * The api state is typed as `any` to avoid importing the api module.
 * At runtime, the actual api state will be present from the real store.
 */
export interface RootState extends SliceStates {
  // RTK Query api state - typed as any to prevent OOM from api module loading
  // The real store has the full api state, but we use any for type isolation
  api: ApiState;
}

// =============================================================================
// AppDispatch - Dispatch type for thunks and actions
// =============================================================================

/**
 * AppDispatch type for dispatching actions and thunks.
 *
 * This is a minimal dispatch type that works with Redux Toolkit.
 * For full typing including api middleware, use the real store.
 */
export type AppDispatch = ThunkDispatch<RootState, undefined, UnknownAction>;

// =============================================================================
// Helper type for testing
// =============================================================================

/**
 * PartialRootState - Use for creating test stores with subset of state
 */
export type PartialRootState = {
  [K in keyof RootState]?: Partial<RootState[K]>;
};
