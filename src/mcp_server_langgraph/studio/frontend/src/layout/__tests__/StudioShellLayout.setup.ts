/**
 * StudioShellLayout Test Setup
 *
 * Shared mock definitions, state objects, and helper functions for all
 * StudioShellLayout test files. This consolidation:
 * 1. Reduces memory overhead from duplicate mock closures
 * 2. Ensures consistent mock behavior across test files
 * 3. Provides centralized reset functions for test isolation
 *
 * USAGE:
 *   import { mocks, resetAllMocks, createTestStore, renderWithProviders } from './StudioShellLayout.setup';
 *
 *   beforeEach(() => {
 *     resetAllMocks();
 *   });
 */

import { vi } from "vitest";
import { act } from "@testing-library/react";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Import reducers (these don't depend on mocked modules)
import canvasReducer from "../../store/slices/canvasSlice";
import personaReducer, {
  setUserInfo,
  type Persona,
} from "../../store/slices/personaSlice";
import authReducer, { initialAuthState } from "../../store/slices/authSlice";
import sessionReducer from "../../store/slices/sessionSlice";
import backgroundAgentReducer from "../../store/slices/backgroundAgentSlice";
import devToolsReducer from "../../store/slices/devToolsSlice";
import alertReducer from "../../store/slices/alertSlice";
import mcpReducer, { initialMCPState } from "../../store/slices/mcpSlice";
import type { User } from "../../types/auth";

// =============================================================================
// MOCK STATE OBJECTS - Mutable for per-test configuration
// =============================================================================

/** Feature flag mock - controls which flags return true */
export const mockFeatureFlags = {
  enabledFlags: ["canvas_ai_palette", "ai_suggestions"] as string[],
  defaultValue: false,
};

/** Nudges hook mock state */
export const mockNudgesState = {
  activeNudge: null as null | {
    id: string;
    type: string;
    title: string;
    message: string;
    action: unknown;
    priority: number;
    dismissable: boolean;
  },
  nudges: [] as unknown[],
  isLoading: false,
};

/** AI Persona Analysis mock state */
export const mockPersonaAnalysisState = {
  isLoading: false,
  error: null as null | Error,
  assignedPersona: "user" as string,
  detectedPersona: null as null | string,
  confidence: 0,
  behaviorSignals: [] as string[],
  recommendation: null as null | string,
  uiAdaptations: [] as string[],
  isPersonaMismatch: false,
};

/** Agent Request WebSocket mock state */
export const mockAgentRequestWSState = {
  status: "connected" as "connected" | "disconnected" | "error",
  pendingApprovals: [] as Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    confidence: number;
    threshold: number;
    proposed_action: string;
    trigger_reason: string;
    context: Record<string, unknown>;
    requested_at: string;
  }>,
  pendingClarifications: [] as Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    clarification_type: "text" | "choice" | "confirmation";
    question: string;
    options: Array<{
      id: string;
      label: string;
      description?: string;
      is_recommended?: boolean;
    }>;
    placeholder: string | null;
    required: boolean;
    context: Record<string, unknown>;
    requested_at: string;
  }>,
};

/** HITL Dialogs mock state */
export const mockHITLState = {
  enabled: true,
  showApprovalDialog: false,
  showClarificationDialog: false,
  activeApproval: null as unknown,
  activeClarification: null as unknown,
  isApproving: false,
  isRejecting: false,
  isClarificationSubmitting: false,
  pendingApprovals: [] as unknown[],
  pendingClarifications: [] as unknown[],
};

/** Breakpoint mock state for ResponsiveLayout integration testing */
export const mockBreakpointState = {
  currentBreakpoint: "xl" as "sm" | "md" | "lg" | "xl",
};

/** KB Status mock state (DynamicContextLoader integration) */
export const mockKBStatusState = {
  kbStatusForUI: "ready" as
    | "ready"
    | "misconfigured"
    | "unavailable"
    | "loading",
  statusMessage: "Knowledge Base ready",
  contextStats: undefined as
    | { refsCount: number; tokensUsed: number; tokenBudget: number }
    | undefined,
  isLoading: false,
  isError: false,
  error: null as Error | null,
  isReady: true,
  isMisconfigured: false,
  isUnavailable: false,
  collectionName: "test-collection",
  vectorsCount: 100,
  skipCalled: false, // Tracks whether skip option was passed
};

// =============================================================================
// MOCK FUNCTIONS - Shared mock function instances
// =============================================================================

export const mockFns = {
  // Feature flags
  useFeatureFlag: vi.fn((flag: string) => {
    return mockFeatureFlags.enabledFlags.includes(flag)
      ? true
      : mockFeatureFlags.defaultValue;
  }),

  // Nudges
  dismissNudge: vi.fn(),
  trackAcceptance: vi.fn(),

  // Persona analysis
  personaRefresh: vi.fn(),

  // Agent request WebSocket
  agentWSDisconnect: vi.fn(),
  agentWSReconnect: vi.fn(),

  // HITL dialogs
  openApprovalDialog: vi.fn(),
  closeApprovalDialog: vi.fn(),
  openClarificationDialog: vi.fn(),
  closeClarificationDialog: vi.fn(),
  handleApprove: vi.fn().mockResolvedValue(undefined),
  handleReject: vi.fn().mockResolvedValue(undefined),
  handleClarificationRespond: vi.fn().mockResolvedValue(undefined),

  // Navigation/routing
  navigate: vi.fn(),
  revalidate: vi.fn(),

  // Cross insights
  fetchInsights: vi.fn(),
  clearInsights: vi.fn(),

  // Connection health
  reconnectHealth: vi.fn(),

  // Message revalidation
  revalidateMessages: vi.fn(),

  // Various intelligence hooks
  detectIntent: vi.fn(),
  optimizeContext: vi.fn(),
  trackGoal: vi.fn(),
  fetchHelp: vi.fn(),
  advanceLearning: vi.fn(),
};

// =============================================================================
// RESET FUNCTIONS
// =============================================================================

/**
 * Reset all mock states to their default values.
 * Call in beforeEach() for test isolation.
 */
export function resetAllMocks(): void {
  // Reset feature flags
  mockFeatureFlags.enabledFlags = ["canvas_ai_palette", "ai_suggestions"];
  mockFeatureFlags.defaultValue = false;

  // Reset nudges state
  mockNudgesState.activeNudge = null;
  mockNudgesState.nudges = [];
  mockNudgesState.isLoading = false;

  // Reset persona analysis state
  mockPersonaAnalysisState.isLoading = false;
  mockPersonaAnalysisState.error = null;
  mockPersonaAnalysisState.assignedPersona = "user";
  mockPersonaAnalysisState.detectedPersona = null;
  mockPersonaAnalysisState.confidence = 0;
  mockPersonaAnalysisState.behaviorSignals = [];
  mockPersonaAnalysisState.recommendation = null;
  mockPersonaAnalysisState.uiAdaptations = [];
  mockPersonaAnalysisState.isPersonaMismatch = false;

  // Reset agent request WS state
  mockAgentRequestWSState.status = "connected";
  mockAgentRequestWSState.pendingApprovals = [];
  mockAgentRequestWSState.pendingClarifications = [];

  // Reset HITL state
  mockHITLState.enabled = true;
  mockHITLState.showApprovalDialog = false;
  mockHITLState.showClarificationDialog = false;
  mockHITLState.activeApproval = null;
  mockHITLState.activeClarification = null;
  mockHITLState.isApproving = false;
  mockHITLState.isRejecting = false;
  mockHITLState.isClarificationSubmitting = false;
  mockHITLState.pendingApprovals = [];
  mockHITLState.pendingClarifications = [];

  // Reset breakpoint state
  mockBreakpointState.currentBreakpoint = "xl";

  // Reset KB status state
  mockKBStatusState.kbStatusForUI = "ready";
  mockKBStatusState.statusMessage = "Knowledge Base ready";
  mockKBStatusState.contextStats = undefined;
  mockKBStatusState.isLoading = false;
  mockKBStatusState.isError = false;
  mockKBStatusState.error = null;
  mockKBStatusState.isReady = true;
  mockKBStatusState.isMisconfigured = false;
  mockKBStatusState.isUnavailable = false;
  mockKBStatusState.collectionName = "test-collection";
  mockKBStatusState.vectorsCount = 100;
  mockKBStatusState.skipCalled = false;

  // Clear all mock function calls
  vi.clearAllMocks();
  // eslint-disable-next-line no-restricted-globals -- Test reset needs direct localStorage access
  localStorage.clear();
}

// =============================================================================
// TEST HELPERS
// =============================================================================

/** Default test user for authenticated state */
export const defaultTestUser: User = {
  id: "user-1",
  username: "testuser",
  email: "test@example.com",
  roles: ["user"],
  persona: "user",
};

/**
 * Create test store with canvas, persona, and auth slices
 */
export const createTestStore = (
  preloadedState: {
    canvas?: Partial<ReturnType<typeof canvasReducer>>;
    persona?: {
      persona: Persona;
      username: string | null;
      email: string | null;
      permissions: string[];
      isPersonaLoading: boolean;
    };
    auth?: Partial<ReturnType<typeof authReducer>>;
    session?: Partial<ReturnType<typeof sessionReducer>>;
    backgroundAgent?: Partial<ReturnType<typeof backgroundAgentReducer>>;
    devTools?: Partial<ReturnType<typeof devToolsReducer>>;
    mcp?: Partial<ReturnType<typeof mcpReducer>>;
  } = {},
) => {
  // Build the reducer map
  const reducer = {
    canvas: canvasReducer,
    persona: personaReducer,
    auth: authReducer,
    session: sessionReducer,
    backgroundAgent: backgroundAgentReducer,
    devTools: devToolsReducer,
    alerts: alertReducer,
    mcp: mcpReducer,
  };

  const store = configureStore({
    reducer,
    preloadedState: {
      ...preloadedState,
      // Always provide a default authenticated user for StudioShell tests
      auth: {
        ...initialAuthState,
        user: defaultTestUser,
        isInitializing: false,
        ...(preloadedState.auth ?? {}),
      },
      // Always provide a default MCP state
      mcp: {
        ...initialMCPState,
        ...(preloadedState.mcp ?? {}),
      },
    } as Parameters<typeof configureStore>[0]["preloadedState"],
  });
  return store;
};

/**
 * Create store with specific persona
 */
export const createStoreWithPersona = (persona: Persona) => {
  const store = createTestStore();
  store.dispatch(
    setUserInfo({
      username: "testuser",
      email: "test@example.com",
      roles: [persona],
      persona,
    }),
  );
  return store;
};

/**
 * Helper to flush pending promises and allow React to settle.
 */
export const flushPromises = () =>
  new Promise<void>((resolve) => setTimeout(resolve, 10));

/**
 * Helper to dispatch keyboard events wrapped in act().
 */
export const dispatchKeyboardEvent = async (
  key: string,
  options: { metaKey?: boolean; ctrlKey?: boolean } = {},
) => {
  await act(async () => {
    const event = new KeyboardEvent("keydown", {
      key,
      metaKey: options.metaKey ?? false,
      ctrlKey: options.ctrlKey ?? false,
      bubbles: true,
    });
    document.dispatchEvent(event);
  });
};

// =============================================================================
// MOCK IMPLEMENTATIONS FOR vi.mock()
// These are the implementations to use in vi.mock() calls
// =============================================================================

export const mockImplementations = {
  TelemetryContext: {
    TelemetryProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    useSessionTelemetry: () => ({
      trackSessionCreation: vi.fn(),
      trackRevalidation: vi.fn(),
      trackSync: vi.fn(),
      getMetrics: () => ({}),
    }),
    useWebVitals: () => ({
      start: vi.fn(),
      stop: vi.fn(),
      getMetrics: () => ({ fcp: null, lcp: null, cls: null, inp: null }),
    }),
  },

  TelemetryViewer: {
    TelemetryViewer: () =>
      React.createElement(
        "div",
        { "data-testid": "telemetry-viewer-mock" },
        "Telemetry Viewer (Mocked)",
      ),
  },

  FeatureFlagContext: {
    useFeatureFlag: (flag: string) => mockFns.useFeatureFlag(flag),
  },

  useNudges: {
    useNudges: () => ({
      ...mockNudgesState,
      dismiss: mockFns.dismissNudge,
      trackAcceptance: mockFns.trackAcceptance,
    }),
  },

  useAIPersonaAnalysis: {
    useAIPersonaAnalysis: () => ({
      ...mockPersonaAnalysisState,
      refresh: mockFns.personaRefresh,
    }),
  },

  useAgentRequestWebSocket: {
    useAgentRequestWebSocket: () => ({
      ...mockAgentRequestWSState,
      disconnect: mockFns.agentWSDisconnect,
      reconnect: mockFns.agentWSReconnect,
    }),
  },

  useHITLDialogs: {
    useHITLDialogs: () => ({
      ...mockHITLState,
      openApprovalDialog: mockFns.openApprovalDialog,
      closeApprovalDialog: mockFns.closeApprovalDialog,
      openClarificationDialog: mockFns.openClarificationDialog,
      closeClarificationDialog: mockFns.closeClarificationDialog,
      handleApprove: mockFns.handleApprove,
      handleReject: mockFns.handleReject,
      handleClarificationRespond: mockFns.handleClarificationRespond,
    }),
  },

  useAIOnboarding: {
    useAIOnboarding: () => ({
      detectedIntent: null,
      confidence: 0,
      recommendedPath: [],
      skipSteps: [],
      personaPrediction: null,
      isLoading: false,
    }),
  },

  usePersonaRouting: {
    usePersonaRouting: () => ({
      isAuthenticated: true,
      persona: "user",
      defaultRoute: "/studio/chat",
      canAccessRoute: true,
    }),
  },

  useConnectionHealthWebSocket: {
    useConnectionHealthWebSocket: () => ({
      status: "connected" as const,
      lastPing: Date.now(),
      reconnect: mockFns.reconnectHealth,
    }),
  },

  useCrossInsightsPanel: {
    useCrossInsightsPanel: () => ({
      isLoading: false,
      isBatchLoading: false,
      crossInsights: [],
      insights: null,
      error: null,
      isAvailable: false,
      fetchInsights: mockFns.fetchInsights,
      clearInsights: mockFns.clearInsights,
    }),
  },

  useUXIntelligence: {
    useNavPrediction: () => ({
      predictedItems: [],
      isLoading: false,
      confidence: 0,
      enabled: false,
    }),
    useContextualHelp: () => ({
      suggestions: [],
      isLoading: false,
      error: null,
      fetchHelp: mockFns.fetchHelp,
    }),
    useLearningPath: () => ({
      steps: [],
      currentStep: null,
      isLoading: false,
      advance: mockFns.advanceLearning,
    }),
  },

  useMessageRevalidation: {
    useMessageRevalidation: () => ({
      revalidateMessages: mockFns.revalidateMessages,
      isRevalidating: false,
    }),
  },

  useConversationIntelligence: {
    useIntentDetection: () => ({
      intent: null,
      confidence: 0,
      isLoading: false,
      detectIntent: mockFns.detectIntent,
    }),
    useContextOptimization: () => ({
      optimizedContext: null,
      isLoading: false,
      optimize: mockFns.optimizeContext,
    }),
    useGoalTracking: () => ({
      goals: [],
      currentGoal: null,
      isLoading: false,
      trackGoal: mockFns.trackGoal,
    }),
  },

  api: {
    useApproveAgentRequestMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve({ success: true }) })),
      { isLoading: false, isError: false, isSuccess: false },
    ],
    useRejectAgentRequestMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve({ success: true }) })),
      { isLoading: false, isError: false, isSuccess: false },
    ],
    useRespondToAgentRequestMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve({ success: true }) })),
      { isLoading: false, isError: false, isSuccess: false },
    ],
    useStudioAnalyzeMutation: () => [
      vi.fn(() => ({
        unwrap: () =>
          Promise.resolve({ results: [], synthesis: {}, total_cost: "0.00" }),
      })),
      { isLoading: false, isError: false, isSuccess: false },
    ],
    useGetKBStatusQuery: () => ({
      data: {
        status: "ready",
        collectionName: "test-collection",
        vectorsCount: 100,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    }),
    useGetServerConfigQuery: () => ({
      data: {
        model_name: "gpt-4",
        provider: "openai",
        features: {},
      },
      isLoading: false,
      isError: false,
      error: null,
    }),
    useGetAvailableModelsQuery: () => ({
      data: [
        { id: "gpt-4", name: "GPT-4", provider: "openai" },
        { id: "claude-3", name: "Claude 3", provider: "anthropic" },
      ],
      isLoading: false,
      isError: false,
      error: null,
    }),
    api: { reducerPath: "api", reducer: () => ({}), middleware: () => [] },
  },

  useKBStatus: {
    useKBStatus: (options?: { skip?: boolean }) => {
      // Track whether skip was passed (for testing)
      mockKBStatusState.skipCalled = options?.skip ?? false;
      return {
        data: undefined,
        status: mockKBStatusState.kbStatusForUI,
        statusMessage: mockKBStatusState.statusMessage,
        isLoading: mockKBStatusState.isLoading,
        isError: mockKBStatusState.isError,
        error: mockKBStatusState.error,
        isReady: mockKBStatusState.isReady,
        isMisconfigured: mockKBStatusState.isMisconfigured,
        isUnavailable: mockKBStatusState.isUnavailable,
        collectionName: mockKBStatusState.collectionName,
        vectorsCount: mockKBStatusState.vectorsCount,
        contextStats: mockKBStatusState.contextStats,
        kbStatusForUI: mockKBStatusState.kbStatusForUI,
        refetch: vi.fn(),
      };
    },
  },

  ResponsiveLayout: {
    useBreakpoint: () => mockBreakpointState.currentBreakpoint,
    ResponsiveLayout: ({
      children,
      className,
    }: {
      children: React.ReactNode;
      className?: string;
    }) =>
      React.createElement(
        "div",
        {
          "data-testid": "responsive-layout",
          "data-breakpoint": mockBreakpointState.currentBreakpoint,
          className,
        },
        children,
      ),
  },
};

// Panel counter for unique testids
let panelGroupCounter = 0;

export const mockResizablePanels = {
  Panel: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement(
      "div",
      {
        "data-testid": props["data-testid" as keyof typeof props],
        className: props["className" as keyof typeof props],
      },
      children,
    ),
  PanelGroup: ({
    children,
    direction,
    ...props
  }: {
    children: React.ReactNode;
    direction?: string;
  }) => {
    const testId = direction
      ? `panel-group-${direction}`
      : `panel-group-${panelGroupCounter++}`;
    return React.createElement(
      "div",
      {
        "data-testid": testId,
        className: props["className" as keyof typeof props],
      },
      children,
    );
  },
  PanelResizeHandle: (props: { className?: string }) =>
    React.createElement("div", {
      "data-testid": "resize-handle",
      className: props.className,
    }),
};

export const mockReactRouter = {
  MemoryRouter: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "mock-router" }, children),
  useLocation: () => ({
    pathname: "/studio/chat",
    search: "",
    hash: "",
    state: null,
  }),
  useNavigate: () => mockFns.navigate,
  useParams: () => ({}),
  useRouteLoaderData: (id: string) => {
    if (id === "studio") {
      return {
        sessions: [
          {
            id: "session-1",
            name: "Test Session 1",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            status: "active",
          },
          {
            id: "session-2",
            name: "Test Session 2",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            status: "active",
          },
        ],
      };
    }
    if (id === "chat-session") {
      return { sessionId: "session-1", artifacts: [] };
    }
    return undefined;
  },
  useRevalidator: () => ({ revalidate: mockFns.revalidate, state: "idle" }),
  Outlet: () => React.createElement("div", { "data-testid": "outlet" }),
  NavLink: ({
    children,
    to,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
  }) => React.createElement("a", { href: to, ...props }, children),
  Link: ({
    children,
    to,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
  }) => React.createElement("a", { href: to, ...props }, children),
  useMatches: () => [
    {
      id: "studio",
      pathname: "/studio",
      params: {},
      data: {},
      handle: { title: "Studio", breadcrumb: "Studio" },
    },
    {
      id: "chat",
      pathname: "/studio/chat",
      params: {},
      data: {},
      handle: { title: "Chat", breadcrumb: "Chat" },
    },
  ],
};

/**
 * Reset panel counter - call in afterEach if tests depend on predictable panel IDs
 */
export function resetPanelCounter(): void {
  panelGroupCounter = 0;
}
