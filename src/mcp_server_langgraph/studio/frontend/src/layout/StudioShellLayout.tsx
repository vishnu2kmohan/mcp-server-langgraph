/**
 * StudioShellLayout - Studio Canvas Implementation
 *
 * New app shell for the Studio Canvas paradigm (Gemini/ChatGPT Canvas style).
 * Uses react-resizable-panels for flexible panel sizing.
 *
 * Layout:
 * +----------------------------------------------------------------+
 * |                     TopBar (persona-aware)                      |
 * +----------------------------------------------------------------+
 * | Activity  |  Session   |  Conversation  |    Canvas Workspace  |
 * |   Bar     |    Nav     |     Panel      |    (full features)   |
 * |  (56px)   | (resizable)|  (resizable)   |    (resizable)       |
 * +----------------------------------------------------------------+
 * |   StatusBar: Model | Tokens | Connection | Agent | User         |
 * +----------------------------------------------------------------+
 */
import {
  useCallback,
  useMemo,
  useEffect,
  useState,
  Suspense,
  useRef,
} from "react";
import { useLocation, Outlet, useNavigate } from "react-router";
import { Panel, PanelGroup } from "react-resizable-panels";
import { ConnectedConversationPanel } from "../conversation/ConnectedConversationPanel";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectCanvasCollapsed,
  selectSessionNavCollapsed,
  selectFocusModeEnabled,
  selectPanelSizes,
  selectHasCustomLayout,
  selectMaximizedPanelId,
  setPanelSizes,
  toggleCanvas,
  toggleSessionNav,
  toggleFocusMode,
  setFocusModeEnabled,
  setSessionNavCollapsed,
  type CanvasPanelSizes,
} from "../store/slices/canvasSlice";
import { storage, STORAGE_KEYS } from "../utils/storage";
import { cn } from "../utils/cn";
import {
  selectCurrentSession,
  selectSessionError,
  createSession,
  renameSession,
  deleteSession,
} from "../store/slices/sessionSlice";
import {
  selectMCPError,
  selectPendingElicitations,
  selectPendingSamplingRequests,
  respondToElicitation,
  respondToSampling,
} from "../store/slices/mcpSlice";
import {
  selectUsername,
  selectPersona,
  selectSubPersona,
} from "../store/slices/personaSlice";
import {
  selectAllAgents,
  updateAgentStatus,
} from "../store/slices/backgroundAgentSlice";
import { usePersonaRouting } from "../hooks/usePersonaRouting";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { useConnectionHealthWebSocket } from "../hooks/useConnectionHealthWebSocket";
import { useNudges } from "../hooks/useNudges";
import { useAIPersonaAnalysis } from "../hooks/useAIPersonaAnalysis";
import { useCrossInsightsPanel } from "../hooks/useCrossInsightsPanel";
import { useHITLDialogs } from "../hooks/useHITLDialogs";
import { useIsChatRoute } from "../hooks/useIsChatRoute";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useAIOrchestratorStatus } from "../hooks/useAIOrchestratorStatus";
import { useCostTrackingWebSocket } from "../hooks/useCostTrackingWebSocket";
import { useCanvasKeyboardNav } from "../hooks/useCanvasKeyboardNav";
import { useKBStatus } from "../hooks/useKBStatus";
import { useBreadcrumb } from "../hooks/useBreadcrumb";
import type { ConnectionStatus } from "../types/connection";
import type { SamplingResponse } from "../types/mcp";
import type { TokenBreakdown, CostBreakdown } from "../types/session";
import { NudgeTooltip } from "../components/Nudge";
import { CrossInsightsPanel } from "../components/Analytics/CrossInsightsPanel";
import { KeyboardShortcutOverlay } from "../components/Common/KeyboardShortcutOverlay";
import { OnboardingWizard } from "../components/Onboarding/OnboardingWizard";
import type {
  OnboardingResult,
  WorkflowTemplate,
} from "../components/Onboarding/OnboardingWizard";
import { AgentApprovalDialog } from "../components/Admin/AgentApprovalDialog";
import { ClarificationDialog } from "../components/Admin/ClarificationDialog";
import { ConfirmDialog } from "../components/UI/ConfirmDialog";
// Use consolidated HITL types from types/hitl.ts (ADR-0091 Phase 10: dialogs use camelCase)
import { convertUIResponseCamelCaseToAPIResponse } from "../types/hitl";

// Import lazy-loaded AI components (Phase 4) - code-split for reduced bundle size
import {
  LazyAICommandPalette,
  LazyBackgroundAgentPanel,
  LazyAgentTaskQueue,
  type Command,
  type AIInterpretation,
} from "../ai/lazy";

// Import CommandPalette context and route commands (Sprint 4)
import {
  CommandPaletteProvider,
  useCommandPalette,
} from "../contexts/CommandPaletteContext";
import { useRouteCommands } from "../hooks/useRouteCommands";

// Import extracted components (de-duplicated from inline versions)
import { ActivityBar } from "./ActivityBar";
import { SessionNav } from "./SessionNav";
import { StatusBar } from "./StatusBar";
import { TopBar } from "./TopBar";
import { ResizeHandle } from "./ResizeHandle";
import { useBreakpoint } from "./ResponsiveLayout";
import { MobileDrawer } from "./MobileDrawer";
import { HamburgerMenu } from "./HamburgerMenu";
import { ConnectedCanvasPanel } from "../canvas/ConnectedCanvasPanel";
import { TelemetryViewer } from "../devtools";
import {
  MCPConnectionProvider,
  useMCPConnection,
} from "../contexts/MCPConnectionContext";
import {
  LazyInboundElicitationModal,
  LazyInboundSamplingModal,
} from "../components/MCP";
import { devLogger } from "../utils/devLogger";
import { LazyDevToolsPanel } from "../components/DevTools";
import {
  selectDevToolsCollapsed,
  selectDevToolsHeight,
  toggleDevTools,
} from "../store/slices/devToolsSlice";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { toast } from "sonner";
import { useGetAvailableModelsQuery, useGetServerConfigQuery } from "../api";
import {
  getConnectionToastId,
  TOAST_ID_CONNECTION_ERROR,
  TOAST_ID_BUDGET_WARNING,
  TOAST_ID_SESSION_DELETED,
  TOAST_ID_MODELS_LOAD_FAILED,
} from "../constants/toastIds";

import { Button } from "@/components/UI";

const logger = devLogger.withPrefix("[StudioShell]");

// =============================================================================
// Command Palette Commands
// =============================================================================

const PALETTE_COMMANDS: Command[] = [
  {
    id: "new-chat",
    name: "New Chat",
    description: "Start a new conversation",
    shortcut: "⌘N",
    category: "chat",
  },
  {
    id: "toggle-canvas",
    name: "Toggle Canvas",
    description: "Show or hide the canvas panel",
    shortcut: "⌘/",
    category: "layout",
  },
  {
    id: "toggle-sidebar",
    name: "Toggle Sidebar",
    description: "Show or hide the session sidebar",
    shortcut: "⌘B",
    category: "layout",
  },
  {
    id: "open-settings",
    name: "Open Settings",
    description: "Open application settings",
    shortcut: "⌘,",
    category: "navigation",
  },
  {
    id: "open-help",
    name: "Help",
    description: "Open help documentation",
    shortcut: "?",
    category: "navigation",
  },
  {
    id: "open-observability",
    name: "Observability",
    description: "Open observability dashboard",
    category: "navigation",
  },
  {
    id: "open-compliance",
    name: "Compliance Dashboard",
    description: "Open compliance monitoring",
    category: "navigation",
  },
  {
    id: "toggle-focus-mode",
    name: "Toggle Focus Mode",
    description: "Hide UI chrome for distraction-free experience",
    shortcut: "⌘⇧F",
    category: "layout",
  },
];

// =============================================================================
// Command Palette Wrapper (Sprint 4)
// =============================================================================

/**
 * Wrapper component to bridge CommandPaletteContext with LazyAICommandPalette.
 * This component consumes the context and passes merged commands to the palette.
 */
interface CommandPaletteWrapperProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (command: Command | AIInterpretation) => void;
  onAIInterpret?: (query: string) => Promise<AIInterpretation>;
}

function CommandPaletteWrapper({
  isOpen,
  onClose,
  onExecute,
  onAIInterpret,
}: CommandPaletteWrapperProps) {
  // Register route-specific commands
  useRouteCommands();

  // Get merged commands from context
  const { commands } = useCommandPalette();

  if (!isOpen) return null;

  return (
    <LazyAICommandPalette
      commands={commands}
      isOpen={isOpen}
      onClose={onClose}
      onExecute={onExecute}
      onAIInterpret={onAIInterpret}
      groupByCategory
    />
  );
}

// =============================================================================
// Inbound MCP Modals (Server-Initiated JSON-RPC Requests)
// =============================================================================

/**
 * InboundMCPModals - handles server-initiated elicitation and sampling requests.
 * Must be rendered inside MCPConnectionProvider to access useMCPConnection.
 */
function InboundMCPModals() {
  const dispatch = useAppDispatch();
  const { sendResponse } = useMCPConnection();

  // Get pending requests from Redux
  const pendingElicitations = useAppSelector(selectPendingElicitations);
  const pendingSamplingRequests = useAppSelector(selectPendingSamplingRequests);

  // Handle elicitation response
  const handleElicitationRespond = useCallback(
    (result: Record<string, unknown>) => {
      if (pendingElicitations.length > 0) {
        const request = pendingElicitations[0];
        sendResponse(request.id, result);
        dispatch(respondToElicitation(request.id));
      }
    },
    [pendingElicitations, sendResponse, dispatch],
  );

  // Handle elicitation cancel
  const handleElicitationCancel = useCallback(() => {
    if (pendingElicitations.length > 0) {
      const request = pendingElicitations[0];
      sendResponse(request.id, null, { code: -32000, message: "User cancelled" });
      dispatch(respondToElicitation(request.id));
    }
  }, [pendingElicitations, sendResponse, dispatch]);

  // Handle sampling approval
  const handleSamplingApprove = useCallback(
    (response: SamplingResponse) => {
      if (pendingSamplingRequests.length > 0) {
        const request = pendingSamplingRequests[0];
        sendResponse(request.id, response);
        dispatch(respondToSampling(request.id));
      }
    },
    [pendingSamplingRequests, sendResponse, dispatch],
  );

  // Handle sampling rejection
  const handleSamplingReject = useCallback(() => {
    if (pendingSamplingRequests.length > 0) {
      const request = pendingSamplingRequests[0];
      sendResponse(request.id, null, {
        code: -32000,
        message: "User rejected sampling request",
      });
      dispatch(respondToSampling(request.id));
    }
  }, [pendingSamplingRequests, sendResponse, dispatch]);

  return (
    <>
      {/* Inbound Elicitation Modal */}
      {pendingElicitations.length > 0 && (
        <Suspense fallback={null}>
          <LazyInboundElicitationModal
            request={pendingElicitations[0]}
            onRespond={handleElicitationRespond}
            onCancel={handleElicitationCancel}
          />
        </Suspense>
      )}

      {/* Inbound Sampling Modal */}
      {pendingSamplingRequests.length > 0 && (
        <Suspense fallback={null}>
          <LazyInboundSamplingModal
            request={pendingSamplingRequests[0]}
            onApprove={handleSamplingApprove}
            onReject={handleSamplingReject}
          />
        </Suspense>
      )}
    </>
  );
}

// =============================================================================
// StudioShellLayout Component
// =============================================================================

export function StudioShellLayout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const sessionNavCollapsed = useAppSelector(selectSessionNavCollapsed);
  const canvasCollapsed = useAppSelector(selectCanvasCollapsed);
  const focusModeEnabled = useAppSelector(selectFocusModeEnabled);
  const devToolsCollapsed = useAppSelector(selectDevToolsCollapsed);
  const devToolsHeight = useAppSelector(selectDevToolsHeight);
  const panelSizes = useAppSelector(selectPanelSizes);
  const hasCustomLayout = useAppSelector(selectHasCustomLayout);
  const maximizedPanelId = useAppSelector(selectMaximizedPanelId);

  // Responsive layout - auto-collapse at narrow widths (Sprint 2.2)
  const breakpoint = useBreakpoint();
  const hasAppliedInitialCollapse = useRef(false);

  // AI component state
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showAgentPanel, setShowAgentPanel] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Model selection state (Sprint 1 - Chat Input Gap Fix)
  // Initialize from localStorage if available, otherwise undefined (will be set from server config)
  const [selectedModel, setSelectedModel] = useState<string | undefined>(() => {
    return storage.get<string>(STORAGE_KEYS.SELECTED_MODEL);
  });
  // Reasoning effort levels: none, low, medium, high, ultra
  // Support varies by vendor - see ReasoningEffortSelector for details
  const [reasoningEffort, setReasoningEffort] = useState<
    "none" | "low" | "medium" | "high" | "ultra"
  >(() => {
    const stored = storage.get<string>(STORAGE_KEYS.REASONING_EFFORT);
    if (
      stored === "none" ||
      stored === "low" ||
      stored === "medium" ||
      stored === "high" ||
      stored === "ultra"
    ) {
      return stored;
    }
    return "medium"; // Fallback default until server config loads
  });
  const [enableThinking, setEnableThinking] = useState(() => {
    const stored = storage.get<boolean>(STORAGE_KEYS.ENABLE_THINKING);
    return stored !== undefined ? stored : true;
  });

  // Recent models state (Sprint 1 - Enhanced Model Selector)
  // Tracks the last 5 models used for quick access in the dropdown
  const [recentModels, setRecentModels] = useState<string[]>(() => {
    const stored = storage.get<string[]>(STORAGE_KEYS.RECENT_MODELS);
    return stored ?? [];
  });

  // Fetch server config for default model (12-Factor App compliance)
  // Issue 1 fix: Added isSuccess to prevent race condition where fallback
  // effect fires before serverConfig is populated
  const {
    data: serverConfig,
    isLoading: isServerConfigLoading,
    isSuccess: isServerConfigSuccess,
  } = useGetServerConfigQuery();

  // Fetch available models from API (12-Factor App - single source of truth)
  const {
    data: fetchedModels,
    isLoading: isModelsLoading,
    isError: isModelsError,
  } = useGetAvailableModelsQuery();

  // Fallback models when API fails (graceful degradation)
  // IMPORTANT: These are only used when /api/v1/config/models is unavailable.
  // The backend sets isDefault based on MODEL_NAME environment variable.
  // Frontend should NOT hardcode default - backend is single source of truth.
  //
  // 12-Factor App Compliance:
  // - Default model is determined by backend settings.model_name
  // - API response includes isDefault: true for the configured model
  // - Fallback exists only for network failure scenarios
  const fallbackModels = useMemo(
    (): Array<{
      id: string;
      name: string;
      provider: string;
      supportsThinking: boolean;
      isDefault?: boolean;
    }> => [
      {
        id: "gemini-2.5-flash",
        name: "Gemini 2.5 Flash",
        provider: "google",
        supportsThinking: true,
        // isDefault is set by backend API, not hardcoded here
      },
      {
        id: "claude-3-5-sonnet",
        name: "Claude 3.5 Sonnet",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
        supportsThinking: false,
      },
    ],
    [],
  );

  // Use fetched models or fallback on error
  const effectiveModels = useMemo(() => {
    if (isModelsError || (!isModelsLoading && !fetchedModels)) {
      return fallbackModels;
    }
    return fetchedModels ?? [];
  }, [fetchedModels, isModelsLoading, isModelsError, fallbackModels]);

  // Sync default model from server config when loaded
  // Only set once - don't override user's selection
  const hasSetDefaultModel = useRef(false);
  useEffect(() => {
    if (
      !hasSetDefaultModel.current &&
      serverConfig?.modelName &&
      !selectedModel
    ) {
      setSelectedModel(serverConfig.modelName);
      hasSetDefaultModel.current = true;
      logger.debug(
        "Set default model from server config:",
        serverConfig.modelName,
      );
    }
  }, [serverConfig?.modelName, selectedModel]);

  // Fallback: if server config doesn't have a modelName, use model marked as default or first available
  // Issue 1 fix: Use isServerConfigSuccess to ensure server config was successfully fetched
  // before applying the fallback. This prevents the race condition where fallback fires
  // before serverConfig data is populated.
  useEffect(() => {
    if (
      !hasSetDefaultModel.current &&
      isServerConfigSuccess && // Wait for successful fetch, not just done loading
      !serverConfig?.modelName && // Server explicitly has no model configured
      effectiveModels.length > 0 &&
      !selectedModel
    ) {
      // Prefer model marked as isDefault, fall back to first available
      const defaultModel =
        effectiveModels.find((m) => m.isDefault) ?? effectiveModels[0];
      if (defaultModel) {
        setSelectedModel(defaultModel.id);
        hasSetDefaultModel.current = true;
        logger.debug(
          "Set default model from available models:",
          defaultModel.id,
          defaultModel.isDefault ? "(marked as default)" : "(first available)",
        );
      }
    }
  }, [
    isServerConfigSuccess,
    serverConfig?.modelName,
    effectiveModels,
    selectedModel,
  ]);

  // Sync default reasoning effort from server config when loaded
  // Only set once if not already stored in localStorage - don't override user's selection
  const hasSetDefaultReasoningEffort = useRef(false);
  useEffect(() => {
    const storedEffort = storage.get<string>(STORAGE_KEYS.REASONING_EFFORT);
    if (
      !hasSetDefaultReasoningEffort.current &&
      serverConfig?.defaultReasoningEffort &&
      !storedEffort // Only set if user hasn't chosen a preference
    ) {
      const effort = serverConfig.defaultReasoningEffort;
      // Validate all 5 supported levels
      if (
        effort === "none" ||
        effort === "low" ||
        effort === "medium" ||
        effort === "high" ||
        effort === "ultra"
      ) {
        setReasoningEffort(effort);
        hasSetDefaultReasoningEffort.current = true;
        logger.debug(
          "Set default reasoning effort from server config:",
          effort,
        );
      }
    }
  }, [serverConfig?.defaultReasoningEffort]);

  // Available models from API, transformed to expected format
  const availableModels = useMemo(() => {
    return effectiveModels.map((model) => ({
      id: model.id,
      name: model.name,
      provider: model.provider,
    }));
  }, [effectiveModels]);

  // Combined loading state for model-related data
  const isModelDataLoading = isModelsLoading || isServerConfigLoading;

  // Validate selected model against available models
  // If the selected model is not in the list, fall back to first available
  useEffect(() => {
    // Skip validation while loading
    if (isModelDataLoading || effectiveModels.length === 0) return;

    // Skip if no model is selected yet (initial load)
    if (!selectedModel) return;

    // Check if selected model exists in available models
    const modelExists = effectiveModels.some((m) => m.id === selectedModel);

    if (!modelExists) {
      // Selected model is invalid, fall back to default or first available
      const fallbackModel =
        effectiveModels.find((m) => m.isDefault) ?? effectiveModels[0];
      if (fallbackModel) {
        logger.warn(
          `Selected model "${selectedModel}" not in available models. Falling back to "${fallbackModel.id}"`,
        );
        setSelectedModel(fallbackModel.id);
      }
    }
  }, [selectedModel, effectiveModels, isModelDataLoading]);

  // Show error toast when models API fails
  // Track previous error state to prevent duplicate toasts on re-renders
  const prevModelsErrorRef = useRef(false);
  useEffect(() => {
    if (isModelsError && !prevModelsErrorRef.current) {
      toast.error("Failed to load models. Using fallback models.", {
        id: TOAST_ID_MODELS_LOAD_FAILED,
      });
      logger.warn("Models API failed, using fallback models");
    }
    prevModelsErrorRef.current = isModelsError;
  }, [isModelsError]);

  // Persist model selection to localStorage when it changes
  useEffect(() => {
    if (selectedModel) {
      storage.set(STORAGE_KEYS.SELECTED_MODEL, selectedModel);
    }
  }, [selectedModel]);

  // Persist reasoning effort to localStorage when it changes
  useEffect(() => {
    storage.set(STORAGE_KEYS.REASONING_EFFORT, reasoningEffort);
  }, [reasoningEffort]);

  // Persist enable thinking to localStorage when it changes
  useEffect(() => {
    storage.set(STORAGE_KEYS.ENABLE_THINKING, enableThinking);
  }, [enableThinking]);

  // Update and persist recent models when selected model changes
  // Adds selected model to front, removes duplicates, limits to 5 entries
  useEffect(() => {
    if (!selectedModel) return;

    setRecentModels((prev) => {
      // Remove the current model if it exists (to move it to front)
      const filtered = prev.filter((id) => id !== selectedModel);
      // Add current model to front and limit to 5
      const updated = [selectedModel, ...filtered].slice(0, 5);
      // Persist to localStorage
      storage.set(STORAGE_KEYS.RECENT_MODELS, updated);
      return updated;
    });
  }, [selectedModel]);

  // Determine if selected model supports extended thinking (from API data)
  const modelSupportsThinking = useMemo(() => {
    if (!selectedModel) return false;
    const model = effectiveModels.find((m) => m.id === selectedModel);
    return model?.supportsThinking ?? false;
  }, [selectedModel, effectiveModels]);

  // Get the provider of the selected model for StatusBar display
  const modelProvider = useMemo(() => {
    if (!selectedModel) return undefined;
    const model = effectiveModels.find((m) => m.id === selectedModel);
    return model?.provider as "openai" | "anthropic" | "google" | undefined;
  }, [effectiveModels, selectedModel]);

  // Panel refs for keyboard navigation (Phase 5 - useCanvasKeyboardNav integration)
  // Note: ActivityBar and SessionNav use HTMLElement (nav elements), while
  // ConnectedConversationPanel and ConnectedCanvasPanel use HTMLDivElement
  const activityBarRef = useRef<HTMLElement>(null);
  const sessionNavRef = useRef<HTMLElement>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  // Keyboard navigation for panel focus (Cmd+1/2/3/4)
  useCanvasKeyboardNav({
    activityBarRef,
    sessionNavRef,
    conversationRef,
    canvasRef,
  });

  // Background agents from Redux
  const backgroundAgents = useAppSelector(selectAllAgents);

  // Feature flags for AI components (Phase 4)
  const aiCommandPaletteEnabled = useFeatureFlag("canvas_ai_palette");
  const aiSuggestionsEnabled = useFeatureFlag("ai_suggestions");
  const nudgesEnabled = useFeatureFlag("nudges");
  const onboardingWizardEnabled = useFeatureFlag("onboarding_wizard");
  // Sprint 4.1: Panel zoom/maximize feature flag
  const panelZoomEnabled = useFeatureFlag("panel_zoom");
  // Sprint 5.1: Mobile drawer navigation feature flag
  const mobileDrawerEnabled = useFeatureFlag("mobile_drawer");
  // KB Focus feature flag (DynamicContextLoader integration)
  const kbFocusEnabled = useFeatureFlag("kb_focus");
  // Sprint 1: Enhanced Model Selector feature flag (recent models, search, capability badges)
  const enhancedModelSelectorEnabled = useFeatureFlag(
    "enhanced_model_selector",
  );
  // Session AI feature flags (AI session intelligence)
  const sessionAIEnabled = useFeatureFlag("session_ai");
  const sessionSummaryEnabled = useFeatureFlag("session_summary");
  const sessionTopicsEnabled = useFeatureFlag("session_topics");

  // KB Status for StatusBar indicator (DynamicContextLoader integration)
  const {
    kbStatusForUI: kbStatus,
    statusMessage: kbStatusMessage,
    contextStats: kbContextStats,
  } = useKBStatus({
    skip: !kbFocusEnabled,
  });

  // Sprint 5.1: Mobile drawer state
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  // Show hamburger menu at narrow breakpoints when feature is enabled
  const showMobileNav =
    mobileDrawerEnabled && (breakpoint === "sm" || breakpoint === "md");

  // Onboarding wizard state (Sprint 3.2)
  // Show wizard for first-time users when feature flag is enabled
  const [showOnboarding, setShowOnboarding] = useState(() => {
    if (!onboardingWizardEnabled) return false;
    // Check if user has already completed onboarding using storage utility
    return storage.get<boolean>(STORAGE_KEYS.ONBOARDING) !== true;
  });

  // HITL dialog state management (extracted to hook for reusability)
  // Handles: approval/clarification dialogs, loading states, dismissed tracking,
  // WebSocket integration, auto-show on pending requests, API handlers
  const {
    enabled: agentHitlEnabled,
    showApprovalDialog,
    showClarificationDialog,
    activeApproval,
    activeClarification,
    isApproving,
    isRejecting,
    isClarificationSubmitting,
    pendingApprovals,
    openApprovalDialog,
    closeApprovalDialog,
    closeClarificationDialog,
    handleApprove,
    handleReject,
    handleClarificationRespond,
  } = useHITLDialogs();

  // Get current route for page context
  const location = useLocation();

  // Sprint 2.3 Phase 2: Breadcrumb items for deeper navigation hierarchy
  // Uses route handle.breadcrumb metadata for nested routes
  // Note: Legacy SECTION_TITLES approach deprecated - all routes now use handle.breadcrumb
  const breadcrumbItems = useBreadcrumb();

  // Get sub-persona for TopBar badge (more granular than base persona)
  const subPersona = useAppSelector(selectSubPersona);

  // Determine if we should show the canvas layout (3-panel: SessionNav + Conversation + Canvas)
  // or the outlet for full-page routes like Observability, Workflows, Cost, etc.
  // Only /studio/chat and /studio/chat/:sessionId use the 3-panel canvas layout.
  // All other /studio/* routes use the Outlet for full-page rendering.
  const isChatRoute = useIsChatRoute();

  // AI-powered nudges (Phase 1.3 + 6.3)
  const { activeNudge, dismiss, trackAcceptance } = useNudges({
    enableAI: nudgesEnabled,
    pageContext: location.pathname,
    maxPerSession: 3,
  });

  // AI-powered persona behavior analysis (Phase 6.7)
  const personaAnalysisEnabled = useFeatureFlag("persona_analysis");
  const {
    isPersonaMismatch,
    detectedPersona,
    recommendation,
    behaviorSignals,
    confidence: personaConfidence,
  } = useAIPersonaAnalysis({
    enabled: personaAnalysisEnabled,
  });

  // Track whether the persona mismatch banner has been dismissed
  const [personaBannerDismissed, setPersonaBannerDismissed] = useState(false);

  // Session delete confirmation dialog state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  // CrossInsightsPanel state management (extracted to hook for reusability)
  // Handles: dismissed state, localStorage persistence, keyboard shortcut (Cmd+I), batch analysis
  const {
    dismissed: crossInsightsDismissed,
    setDismissed: setCrossInsightsDismissed,
    crossInsights,
    confidence: batchConfidence,
    isLoading: isBatchLoading,
    personaResult: batchPersonaResult,
    disclosureResult: batchDisclosureResult,
    batchAnalysisEnabled,
  } = useCrossInsightsPanel();

  // Persona-based routing: handles default route redirects and access validation
  // This integrates PersonaRouter logic into the StudioShell
  usePersonaRouting();

  // Sprint 2.2: Auto-collapse SessionNav at narrow widths (sm/md breakpoints)
  // Only runs ONCE at mount to prevent flip-flopping on window resize.
  // Respects user's custom layout - if hasCustomLayout is true, don't auto-collapse.
  useEffect(() => {
    // Only apply once at mount
    if (hasAppliedInitialCollapse.current) return;

    // Don't override user's custom layout
    if (hasCustomLayout) {
      hasAppliedInitialCollapse.current = true;
      return;
    }

    // Auto-collapse SessionNav on narrow breakpoints (sm or md)
    if (breakpoint === "sm" || breakpoint === "md") {
      dispatch(setSessionNavCollapsed(true));
    }

    hasAppliedInitialCollapse.current = true;
  }, [breakpoint, hasCustomLayout, dispatch]);

  // Get real-time connection health status with toast notifications
  // Uses unique IDs per connection to deduplicate rapid status changes
  const { status: wsStatus, reconnectAttempts: wsReconnectAttempts } =
    useConnectionHealthWebSocket({
      onConnectionUpdate: (conn) => {
        // Use connection name as toast ID to deduplicate rapid status changes
        const toastId = getConnectionToastId(conn.name);
        if (conn.status === "disconnected") {
          toast.warning(`Connection "${conn.name}" disconnected`, { id: toastId });
        } else if (conn.status === "connected") {
          toast.success(`Connection "${conn.name}" connected`, { id: toastId });
        }
      },
      onError: (error) => {
        toast.error(`Connection error: ${error}`, { id: TOAST_ID_CONNECTION_ERROR });
      },
    });

  // Get AI orchestrator status for StatusBar (context-aware display)
  const { statusForStatusBar: aiOrchestratorStatus } =
    useAIOrchestratorStatus();

  // Real-time cost tracking via WebSocket (Phase 5 hook integration)
  const {
    sessionCosts,
    subscribeSession: subscribeCostSession,
    unsubscribeSession: unsubscribeCostSession,
  } = useCostTrackingWebSocket({
    onBudgetWarning: (warning) => {
      toast.warning(`Budget warning: ${warning.message}`, {
        id: TOAST_ID_BUDGET_WARNING,
        duration: 10000,
      });
    },
    onCostEvent: (event) => {
      // Log cost events for DevTools visibility (appears in console/network tabs)
      logger.debug(
        `Cost event: $${event.cost.toFixed(4)} for ${event.model} ` +
          `(${event.tokens.input} in / ${event.tokens.output} out)`,
        { sessionId: event.sessionId, cost: event.cost, model: event.model },
      );
    },
  });

  // Map WebSocket status to StatusBar connection status
  const connectionStatus: ConnectionStatus = useMemo(() => {
    switch (wsStatus) {
      case "connected":
        return "connected";
      case "connecting":
      case "reconnecting":
        return "connecting";
      case "disconnected":
        return "disconnected";
      case "error":
        return "error";
      default:
        return "disconnected";
    }
  }, [wsStatus]);

  // Get user info from Redux
  const username = useAppSelector(selectUsername);
  const currentPersona = useAppSelector(selectPersona);
  // Use username as userId for AI features (format: "user:username")
  const currentUserId = username ? `user:${username}` : undefined;

  // Get current session for model info
  const currentSession = useAppSelector(selectCurrentSession);
  const modelName = currentSession?.config?.modelName;

  // Get aggregated errors for StatusBar problem count
  const sessionError = useAppSelector(selectSessionError);
  const mcpError = useAppSelector(selectMCPError);
  const problemCount = useMemo(() => {
    let count = 0;
    if (sessionError) count++;
    if (mcpError) count++;
    return count > 0 ? count : undefined;
  }, [sessionError, mcpError]);

  // Log cross-insights for debugging (dev mode only)
  useEffect(() => {
    if (crossInsights.length > 0 && !isBatchLoading) {
      logger.debug("Batch composite analysis cross-insights:", crossInsights);
    }
  }, [crossInsights, isBatchLoading]);

  // Compute token count from messages using backend-provided usage data
  // Falls back to character-based approximation if no usage data available
  const tokenCount = useMemo(() => {
    if (!currentSession?.messages?.length) return 0;

    // Sum up actual token usage from backend if available
    let totalFromUsage = 0;
    let hasUsageData = false;

    for (const msg of currentSession.messages) {
      if (msg.usage?.totalTokens) {
        totalFromUsage += msg.usage.totalTokens;
        hasUsageData = true;
      }
      // Also include thinking tokens if available (extended thinking)
      if (msg.thinkingTokens) {
        totalFromUsage += msg.thinkingTokens;
        hasUsageData = true;
      }
    }

    // If we have backend data, use it
    if (hasUsageData) {
      return totalFromUsage;
    }

    // Fallback: Approximate tokens from character count (~4 chars per token)
    const totalChars = currentSession.messages.reduce(
      (sum, msg) => sum + (msg.content?.length ?? 0),
      0,
    );
    return Math.round(totalChars / 4);
  }, [currentSession?.messages]);

  // Compute token breakdown (promptTokens and completionTokens) for StatusBar tooltip
  const tokenBreakdown = useMemo((): TokenBreakdown | undefined => {
    if (!currentSession?.messages?.length) return undefined;

    let promptTokens = 0;
    let completionTokens = 0;
    let hasUsageData = false;

    for (const msg of currentSession.messages) {
      if (msg.usage) {
        promptTokens += msg.usage.promptTokens ?? 0;
        completionTokens += msg.usage.completionTokens ?? 0;
        hasUsageData = true;
      }
    }

    // Only return breakdown if we have actual usage data from backend
    if (!hasUsageData) return undefined;

    return {
      promptTokens,
      completionTokens,
      totalTokens: promptTokens + completionTokens,
    };
  }, [currentSession?.messages]);

  // Subscribe to cost tracking for current session
  useEffect(() => {
    const sessionId = currentSession?.id;
    if (!sessionId) return;

    subscribeCostSession(sessionId);

    return () => {
      unsubscribeCostSession(sessionId);
    };
  }, [currentSession?.id, subscribeCostSession, unsubscribeCostSession]);

  // Compute cost breakdown from WebSocket data for StatusBar
  const costBreakdown = useMemo((): CostBreakdown | undefined => {
    const sessionId = currentSession?.id;
    if (!sessionId) return undefined;

    const sessionCost = sessionCosts[sessionId];
    if (!sessionCost) return undefined;

    return {
      estimatedCostUsd: sessionCost.totalCost,
      byModel: sessionCost.model
        ? {
            [sessionCost.model]: {
              tokens: sessionCost.tokenCount,
              cost: sessionCost.totalCost,
            },
          }
        : undefined,
    };
  }, [currentSession?.id, sessionCosts]);

  // Sprint 4.1: Compute panel visibility based on maximizedPanelId
  // When a panel is maximized (and feature flag enabled), hide other panels
  const effectiveSessionNavVisible = useMemo(() => {
    if (!panelZoomEnabled || !maximizedPanelId) {
      // Normal behavior: respect sessionNavCollapsed
      return !sessionNavCollapsed;
    }
    // When a panel is maximized, only show session-nav if it's the maximized one
    return maximizedPanelId === "session-nav";
  }, [panelZoomEnabled, maximizedPanelId, sessionNavCollapsed]);

  const effectiveCanvasVisible = useMemo(() => {
    if (!panelZoomEnabled || !maximizedPanelId) {
      // Normal behavior: respect canvasCollapsed
      return !canvasCollapsed;
    }
    // When a panel is maximized, only show canvas if it's the maximized one
    return maximizedPanelId === "canvas";
  }, [panelZoomEnabled, maximizedPanelId, canvasCollapsed]);

  const effectiveConversationVisible = useMemo(() => {
    if (!panelZoomEnabled || !maximizedPanelId) {
      // Conversation is always visible by default
      return true;
    }
    // When a panel is maximized, only show conversation if it's the maximized one
    return maximizedPanelId === "conversation";
  }, [panelZoomEnabled, maximizedPanelId]);

  // Handle panel resize
  const handlePanelResize = useCallback(
    (sizes: number[]) => {
      if (sizes.length === 3) {
        const sessionNavSize = sizes[0];
        const conversationSize = sizes[1];
        const canvasSize = sizes[2];
        if (
          sessionNavSize !== undefined &&
          conversationSize !== undefined &&
          canvasSize !== undefined
        ) {
          const newSizes: CanvasPanelSizes = {
            sessionNav: sessionNavSize,
            conversation: conversationSize,
            canvas: canvasSize,
          };
          dispatch(setPanelSizes(newSizes));
        }
      }
    },
    [dispatch],
  );

  // Keyboard shortcuts (using hook instead of manual handling)
  // Note: Define both ctrl+key and meta+key (cmd+key on Mac) for cross-platform support
  const keyboardShortcuts = useMemo(
    () => ({
      // Toggle canvas: Ctrl+/ (Windows/Linux) or Cmd+/ (Mac)
      "ctrl+/": () => dispatch(toggleCanvas()),
      "meta+/": () => dispatch(toggleCanvas()),
      // Open command palette: Ctrl+K or Cmd+K
      "ctrl+k": () => setShowCommandPalette(true),
      "meta+k": () => setShowCommandPalette(true),
      // Toggle DevTools: Ctrl+Shift+I or Cmd+Shift+I
      "ctrl+shift+i": () => dispatch(toggleDevTools()),
      "meta+shift+i": () => dispatch(toggleDevTools()),
      // Toggle Focus Mode: Ctrl+Shift+F or Cmd+Shift+F
      "ctrl+shift+f": () => dispatch(toggleFocusMode()),
      "meta+shift+f": () => dispatch(toggleFocusMode()),
      // Show keyboard shortcuts overlay: ? key (Sprint 3.1)
      "shift+?": () => setShowShortcuts(true),
      "?": () => setShowShortcuts(true),
      // Exit focus mode: Escape (only when focus mode is enabled)
      ...(focusModeEnabled && {
        escape: () => dispatch(setFocusModeEnabled(false)),
      }),
      // Note: Cmd+I / Ctrl+I for insights panel is handled by useCrossInsightsPanel hook
    }),
    [dispatch, focusModeEnabled, setShowShortcuts],
  );

  useKeyboardShortcuts(keyboardShortcuts);

  // Handler for command palette execution
  const handleCommandExecute = useCallback(
    (commandOrInterpretation: Command | AIInterpretation) => {
      // Check if it's a Command or AIInterpretation
      if ("id" in commandOrInterpretation) {
        const command = commandOrInterpretation;
        logger.debug("Command executed:", command.id);

        switch (command.id) {
          case "new-chat":
            dispatch(createSession({ name: "New Chat" }));
            break;
          case "toggle-canvas":
            dispatch(toggleCanvas());
            break;
          case "toggle-sidebar":
            dispatch(toggleSessionNav());
            break;
          case "open-settings":
            navigate("/studio/settings");
            break;
          case "open-help":
            navigate("/studio/help");
            break;
          case "open-observability":
            navigate("/studio/observability");
            break;
          case "open-compliance":
            navigate("/studio/compliance");
            break;
          case "toggle-focus-mode":
            dispatch(toggleFocusMode());
            break;
          default:
            logger.warn("Unknown command:", command.id);
        }
      } else {
        // AIInterpretation - handle natural language commands
        const interpretation = commandOrInterpretation;
        logger.debug(
          "AI interpretation executed:",
          interpretation.action,
          interpretation.params,
        );

        // Handle AI interpretations based on action type
        switch (interpretation.action) {
          case "navigate":
            // Navigate to specified path using SPA navigation
            if (typeof interpretation.params.path === "string") {
              navigate(interpretation.params.path);
            }
            break;
          case "toggle-panel":
            // Toggle specified panel
            if (interpretation.params.panel === "canvas") {
              dispatch(toggleCanvas());
            } else if (interpretation.params.panel === "sidebar") {
              dispatch(toggleSessionNav());
            }
            break;
          case "new-chat":
            dispatch(createSession({ name: "New Chat" }));
            break;
          case "search":
            // Log search intent - could trigger search UI
            logger.debug("Search requested:", interpretation.params.query);
            break;
          default:
            logger.warn("Unhandled AI interpretation:", interpretation.action);
        }
      }
    },
    [dispatch, navigate],
  );

  // Handler for agent cancel
  const handleAgentCancel = useCallback(
    (agentId: string) => {
      logger.debug("Cancelling agent:", agentId);
      dispatch(
        updateAgentStatus({
          id: agentId,
          status: "failed",
          error: "Cancelled by user",
        }),
      );
    },
    [dispatch],
  );

  // Handler for agent retry
  const handleAgentRetry = useCallback(
    (agentId: string) => {
      logger.debug("Retrying agent:", agentId);
      dispatch(updateAgentStatus({ id: agentId, status: "queued" }));
    },
    [dispatch],
  );

  // Handler for session rename (from SessionNav inline editing or context menu)
  const handleRenameSession = useCallback(
    (sessionId: string, name: string) => {
      logger.debug("Renaming session:", sessionId, "to:", name);
      dispatch(renameSession({ sessionId, name }));
    },
    [dispatch],
  );

  // Handler for session delete (from SessionNav context menu)
  // Shows confirmation dialog before deleting to prevent accidental data loss
  const handleDeleteSession = useCallback((sessionId: string) => {
    logger.debug("Delete session requested:", sessionId);
    setSessionToDelete(sessionId);
    setDeleteConfirmOpen(true);
  }, []);

  // Confirm session deletion after user confirms in dialog
  const handleConfirmDelete = useCallback(() => {
    if (sessionToDelete) {
      logger.debug("Deleting session:", sessionToDelete);
      dispatch(deleteSession(sessionToDelete));
      toast.success("Session deleted", { id: TOAST_ID_SESSION_DELETED });
      setDeleteConfirmOpen(false);
      setSessionToDelete(null);
    }
  }, [dispatch, sessionToDelete]);

  // Cancel session deletion
  const handleCancelDelete = useCallback(() => {
    setDeleteConfirmOpen(false);
    setSessionToDelete(null);
  }, []);

  // Handler for user menu click (dropdown is managed by TopBar component)
  const handleUserMenuClick = useCallback(() => {
    logger.debug("User menu clicked");
  }, []);

  // Handler for agent queue toggle
  const handleAgentQueueToggle = useCallback(() => {
    setShowAgentPanel((prev) => !prev);
  }, []);

  // Handler for pending approvals click - opens first pending approval dialog
  const handlePendingApprovalsClick = useCallback(() => {
    logger.debug("Pending approvals clicked, count:", pendingApprovals.length);
    if (pendingApprovals.length > 0) {
      const firstApproval = pendingApprovals[0];
      if (firstApproval) {
        openApprovalDialog(firstApproval);
      }
    }
  }, [pendingApprovals, openApprovalDialog]);

  // Handler for AI natural language interpretation (Phase 4)
  const handleAIInterpret = useCallback(
    async (query: string): Promise<AIInterpretation> => {
      logger.debug("AI interpretation requested:", query);

      try {
        const response = await authenticatedFetch(
          "/api/v1/ai/interpret-command",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
          },
        );

        if (response.ok) {
          const interpretation: AIInterpretation = await response.json();
          logger.debug("AI interpretation result:", interpretation);
          return interpretation;
        }

        // Fallback on API error - return a search action
        logger.warn("AI interpretation API error:", response.status);
        return {
          action: "search",
          params: { query },
          confidence: 0.5,
        };
      } catch (error) {
        logger.error("AI interpretation failed:", error);
        // Fallback on network error - return a search action
        return {
          action: "search",
          params: { query },
          confidence: 0.3,
        };
      }
    },
    [],
  );

  // Onboarding wizard handlers (Sprint 3.2)
  const handleOnboardingComplete = useCallback((result: OnboardingResult) => {
    logger.debug("Onboarding completed:", result);
    storage.set(STORAGE_KEYS.ONBOARDING, true);
    setShowOnboarding(false);
  }, []);

  const handleOnboardingSkip = useCallback(() => {
    logger.debug("Onboarding skipped");
    storage.set(STORAGE_KEYS.ONBOARDING, true);
    setShowOnboarding(false);
  }, []);

  // Sample workflow templates for onboarding
  const onboardingTemplates: WorkflowTemplate[] = useMemo(
    () => [
      {
        id: "conversational-agent",
        name: "Conversational Agent",
        description: "A basic chat agent with context retention",
        category: "conversational",
        tags: ["chat", "basic"],
      },
      {
        id: "data-pipeline",
        name: "Data Pipeline",
        description: "Process and transform data with AI",
        category: "pipeline",
        tags: ["data", "processing"],
      },
      {
        id: "multi-agent",
        name: "Multi-Agent Collaboration",
        description: "Multiple agents working together",
        category: "collaboration",
        tags: ["multi-agent", "advanced"],
      },
    ],
    [],
  );

  return (
    // Sprint 4: Wrap with CommandPaletteProvider for dynamic route commands
    // MCPConnectionProvider: Single MCP WebSocket connection shared across app
    <CommandPaletteProvider staticCommands={PALETTE_COMMANDS}>
      <MCPConnectionProvider>
      <div
        data-testid="studio-shell"
        className={cn(
          "studio-shell flex flex-col h-screen bg-neutral-1",
          focusModeEnabled && "focus-mode",
        )}
      >
        {/* Skip-to-content link (WCAG 2.1 AA - 2.4.1 Bypass Blocks) */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-notification focus:p-4 focus:bg-neutral-1 focus:text-primary-10 focus:ring-2 focus:ring-primary-7"
        >
          Skip to main content
        </a>

        {/* TopBar - persona-aware header (hidden in focus mode) */}
        {/* Sprint 2.3 Phase 2: breadcrumbItems provides wayfinding via useBreadcrumb hook */}
        {/* Sprint 5.1: Add hamburger menu for mobile navigation */}
        {!focusModeEnabled && (
          <div className="flex items-center w-full">
            {/* Sprint 5.1: Hamburger menu for mobile breakpoints */}
            {showMobileNav && (
              <div className="flex-shrink-0 p-2">
                <HamburgerMenu
                  onClick={() => setMobileDrawerOpen(true)}
                  isOpen={mobileDrawerOpen}
                />
              </div>
            )}
            <TopBar
              breadcrumbItems={
                breadcrumbItems.length > 0 ? breadcrumbItems : undefined
              }
              subPersonaBadge={subPersona || undefined}
              onUserMenuClick={handleUserMenuClick}
              pendingApprovals={
                agentHitlEnabled ? pendingApprovals.length : undefined
              }
              onPendingApprovalsClick={
                agentHitlEnabled ? handlePendingApprovalsClick : undefined
              }
              onAlertClick={() => navigate("/admin/alerts")}
              className="flex-1"
            />
          </div>
        )}

        {/* Focus Mode Exit Button - shows when in focus mode */}
        {focusModeEnabled && (
          <Button
            variant="secondary"
            size="sm"
            className="fixed top-2 right-2 z-panel p-2 rounded-lg bg-neutral-a9 hover:bg-neutral-4 text-neutral-12 text-xs -opacity opacity-30 hover:opacity-100"
            data-testid="focus-mode-exit"
            onClick={() => dispatch(setFocusModeEnabled(false))}
            aria-label="Exit focus mode (Escape)"
            title="Exit Focus Mode (Escape or ⌘⇧F)"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5"
              />
            </svg>
          </Button>
        )}

        {/* Main content area with DevTools */}
        <PanelGroup direction="vertical" className="flex-1">
          {/* Main horizontal panels */}
          <Panel
            id="main-content"
            order={1}
            defaultSize={devToolsCollapsed ? 100 : 75}
            minSize={50}
          >
            <div
              data-testid={
                focusModeEnabled ? "main-content-focus" : "left-sidebar"
              }
              className="flex h-full"
            >
              {/* Activity Bar - fixed width (hidden in focus mode) */}
              {/* Sprint 4: AI-native navigation predictions enabled via feature flag */}
              {!focusModeEnabled && (
                <ActivityBar
                  ref={activityBarRef}
                  enableAI={aiSuggestionsEnabled}
                  reorderByPrediction={aiSuggestionsEnabled}
                />
              )}

              {/* Main content area - conditionally render based on route */}
              {/* Key props force React to unmount/remount when switching between layouts */}
              {/* This prevents PanelGroup state from persisting across route type changes */}
              {isChatRoute ? (
                /* Chat routes: 3-panel canvas layout */
                (<PanelGroup
                  key="chat-canvas-layout"
                  direction="horizontal"
                  onLayout={handlePanelResize}
                  className="flex-1"
                >
                  {/* Session Nav Panel */}
                  {/* Sprint 4.1: Uses effectiveSessionNavVisible for maximize support */}
                  {effectiveSessionNavVisible && (
                    <>
                      <Panel
                        id="session-nav"
                        data-testid="session-nav"
                        order={1}
                        defaultSize={
                          maximizedPanelId === "session-nav"
                            ? 100
                            : panelSizes.sessionNav
                        }
                        minSize={maximizedPanelId ? undefined : 5}
                        maxSize={maximizedPanelId ? undefined : 25}
                      >
                        <SessionNav
                          ref={sessionNavRef}
                          enableEdit
                          enableContextMenu
                          enableHover
                          onRenameSession={handleRenameSession}
                          onDeleteSession={handleDeleteSession}
                          enableAI={sessionAIEnabled}
                          showSummary={sessionSummaryEnabled}
                          showTopics={sessionTopicsEnabled}
                          enableSimilarSessions={aiSuggestionsEnabled}
                          userId={currentUserId}
                        />
                      </Panel>
                      {!maximizedPanelId && <ResizeHandle />}
                    </>
                  )}
                  {/* Conversation Panel */}
                  {/* Sprint 4.1: Uses effectiveConversationVisible for maximize support */}
                  {effectiveConversationVisible && (
                    <Panel
                      id="conversation"
                      order={2}
                      defaultSize={
                        maximizedPanelId === "conversation"
                          ? 100
                          : canvasCollapsed
                            ? 85
                            : panelSizes.conversation
                      }
                      minSize={maximizedPanelId ? undefined : 25}
                      maxSize={maximizedPanelId ? undefined : 50}
                    >
                      <ConnectedConversationPanel
                        ref={conversationRef}
                        enableAI={aiSuggestionsEnabled}
                        enableRealTimeSuggestions={aiSuggestionsEnabled}
                        enableInlineSuggestions={aiSuggestionsEnabled}
                        userId={currentUserId}
                        persona={currentPersona}
                        currentTokens={tokenCount}
                        maxTokens={128000}
                        showContextWarning={tokenCount > 100000}
                        // Model selection (Sprint 1 - Chat Input Gap Fix)
                        showModelSelector
                        selectedModel={selectedModel}
                        availableModels={availableModels}
                        onModelChange={setSelectedModel}
                        isModelsLoading={isModelDataLoading}
                        // Enhanced model selector features (gated by feature flag)
                        recentModels={
                          enhancedModelSelectorEnabled
                            ? recentModels
                            : undefined
                        }
                        enableModelSearch={
                          enhancedModelSelectorEnabled &&
                          availableModels.length > 5
                        }
                        // Reasoning effort
                        modelSupportsThinking={modelSupportsThinking}
                        reasoningEffort={reasoningEffort}
                        onReasoningEffortChange={setReasoningEffort}
                        enableThinking={enableThinking}
                        onEnableThinkingChange={setEnableThinking}
                      />
                    </Panel>
                  )}
                  {/* Canvas Panel */}
                  {/* Sprint 4.1: Uses effectiveCanvasVisible for maximize support */}
                  {effectiveCanvasVisible && (
                    <>
                      {!maximizedPanelId && <ResizeHandle />}
                      <Panel
                        id="canvas"
                        data-testid="canvas-panel"
                        order={3}
                        defaultSize={
                          maximizedPanelId === "canvas"
                            ? 100
                            : panelSizes.canvas
                        }
                        minSize={maximizedPanelId ? undefined : 35}
                        maxSize={maximizedPanelId ? undefined : 60}
                      >
                        <ConnectedCanvasPanel
                          ref={canvasRef}
                          userId={currentUserId}
                          persona={currentPersona}
                        />
                      </Panel>
                    </>
                  )}
                </PanelGroup>)
              ) : (
                /* Full-page routes: Render the routed component via Outlet */
                /* Suspense boundary handles lazy-loaded routes (e.g., WorkflowsPage, ObservabilityPage) */
                (<div
                  key="full-page-outlet"
                  data-testid="route-outlet"
                  className="flex-1 h-full overflow-auto bg-neutral-1"
                >
                  <Suspense
                    fallback={
                      <div
                        className="flex items-center justify-center h-full"
                        data-testid="route-loading"
                      >
                        <div className="flex flex-col items-center gap-2">
                          <div className="w-8 h-8 border-2 border-primary-9 border-t-transparent rounded-full motion-safe:animate-spin" />
                          <span className="text-sm text-neutral-10">
                            Loading...
                          </span>
                        </div>
                      </div>
                    }
                  >
                    <Outlet />
                  </Suspense>
                </div>)
              )}
            </div>
          </Panel>

          {/* DevTools Panel */}
          {!devToolsCollapsed && (
            <>
              <ResizeHandle vertical />
              <Panel
                id="devtools"
                order={2}
                defaultSize={devToolsHeight}
                minSize={10}
                maxSize={50}
              >
                <Suspense
                  fallback={
                    <div className="flex items-center justify-center h-full bg-neutral-1">
                      <span className="text-sm text-neutral-9">
                        Loading DevTools...
                      </span>
                    </div>
                  }
                >
                  <LazyDevToolsPanel />
                </Suspense>
              </Panel>
            </>
          )}
        </PanelGroup>

        {/* StatusBar - context-aware status, connection, model, tokens, DevTools (hidden in focus mode) */}
        {!focusModeEnabled && (
          <StatusBar
            connectionStatus={connectionStatus}
            reconnectAttempts={wsReconnectAttempts}
            agentStatus={aiOrchestratorStatus}
            modelName={modelName ?? undefined}
            modelProvider={modelProvider}
            tokenCount={tokenCount > 0 ? tokenCount : undefined}
            tokenBreakdown={tokenBreakdown}
            costBreakdown={costBreakdown}
            // userName removed - redundant with top-bar user display
            agentCount={backgroundAgents.length}
            onAgentQueueToggle={handleAgentQueueToggle}
            agentQueueOpen={showAgentPanel}
            pendingApprovals={
              agentHitlEnabled ? pendingApprovals.length : undefined
            }
            onPendingApprovalsClick={
              agentHitlEnabled ? handlePendingApprovalsClick : undefined
            }
            approvalsPanelOpen={showApprovalDialog}
            problemCount={problemCount}
            devToolsCollapsed={devToolsCollapsed}
            onDevToolsToggle={() => dispatch(toggleDevTools())}
            kbStatus={kbFocusEnabled ? kbStatus : undefined}
            kbStatusMessage={kbFocusEnabled ? kbStatusMessage : undefined}
            kbContextStats={kbFocusEnabled ? kbContextStats : undefined}
          />
        )}

        {/* Dev mode telemetry viewer (fixed position overlay) */}
        <TelemetryViewer />

        {/* AI Nudges (Phase 1.3 + 6.3) - contextual hints and feature discovery */}
        {nudgesEnabled && activeNudge && (
          <div className="fixed bottom-20 left-16 z-notification max-w-xs">
            <NudgeTooltip
              nudge={activeNudge}
              onDismiss={() => dismiss(activeNudge.id)}
              onAccept={() => trackAcceptance(activeNudge.id)}
            />
          </div>
        )}

        {/* AI Persona Mismatch Banner (Phase 6.7) */}
        {personaAnalysisEnabled &&
          isPersonaMismatch &&
          !personaBannerDismissed &&
          personaConfidence >= 0.75 && (
            <div
              className="fixed top-16 left-1/2 transform -translate-x-1/2 z-notification max-w-lg"
              role="alert"
              data-testid="persona-mismatch-banner"
            >
              <div className="bg-insight-1 dark:bg-insight-a4 border border-insight-4 dark:border-insight-11 rounded-lg shadow-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <svg
                      className="w-5 h-5 text-insight-10 dark:text-insight-9"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-insight-11 dark:text-insight-4">
                      We noticed you&apos;re using advanced features
                    </h4>
                    <p className="text-sm text-insight-11 dark:text-insight-5 mt-1">
                      Your usage pattern suggests you might benefit from{" "}
                      <strong>{detectedPersona?.replace(/-/g, " ")}</strong>{" "}
                      capabilities.
                    </p>
                    {recommendation && (
                      <p className="text-sm text-insight-10 dark:text-insight-9 mt-2">
                        {recommendation}
                      </p>
                    )}
                    {behaviorSignals.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {behaviorSignals.slice(0, 3).map((signal, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-0.5 text-xs bg-insight-2 dark:bg-insight-a6 text-insight-11 dark:text-insight-5 rounded"
                          >
                            {signal}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    className="flex-shrink-0 p-1 text-insight-9 hover:text-insight-10 dark:hover:text-insight-4"
                    onClick={() => setPersonaBannerDismissed(true)}
                    aria-label="Dismiss persona suggestion">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </Button>
                </div>
              </div>
            </div>
          )}

        {/* AI Cross-Insights Panel (Phase 6+) - shows batch composite analysis results */}
        {/* Positioned bottom-left to avoid overlap with agent panel (bottom-right) */}
        {batchAnalysisEnabled &&
          !crossInsightsDismissed &&
          !isBatchLoading &&
          (crossInsights.length > 0 ||
            batchPersonaResult ||
            batchDisclosureResult) && (
            <div
              className="fixed bottom-16 left-16 z-panel w-80"
              data-testid="cross-insights-panel-container"
            >
              <CrossInsightsPanel
                crossInsights={crossInsights}
                personaResult={batchPersonaResult}
                disclosureResult={batchDisclosureResult}
                confidence={batchConfidence}
                isLoading={isBatchLoading}
                onDismiss={() => setCrossInsightsDismissed(true)}
                defaultCollapsed={true}
              />
            </div>
          )}

        {/* Keyboard Shortcuts Overlay (? key) - Sprint 3.1 */}
        <KeyboardShortcutOverlay
          shortcuts={keyboardShortcuts}
          isOpen={showShortcuts}
          onClose={() => setShowShortcuts(false)}
        />

        {/* AI Command Palette (Cmd+K) - gated by canvas_ai_palette feature flag */}
        {/* Sprint 4: Uses CommandPaletteWrapper to consume context with route commands */}
        {/* Lazy-loaded to reduce initial bundle size */}
        {aiCommandPaletteEnabled && (
          <Suspense fallback={null}>
            <CommandPaletteWrapper
              isOpen={showCommandPalette}
              onClose={() => setShowCommandPalette(false)}
              onExecute={handleCommandExecute}
              onAIInterpret={handleAIInterpret}
            />
          </Suspense>
        )}

        {/* Background Agent Panel (floating, bottom-right) - gated by ai_suggestions feature flag */}
        {/* Lazy-loaded to reduce initial bundle size */}
        {aiSuggestionsEnabled && backgroundAgents.length > 0 && (
          <div className="fixed bottom-16 right-4 z-panel w-80">
            <Suspense fallback={null}>
              <LazyBackgroundAgentPanel
                agents={backgroundAgents}
                onCancel={handleAgentCancel}
                onRetry={handleAgentRetry}
              />
            </Suspense>
          </div>
        )}

        {/* Agent Task Queue (side panel, toggled via showAgentPanel) - gated by ai_suggestions feature flag */}
        {/* Lazy-loaded to reduce initial bundle size */}
        {/* Uses CSS vars for dynamic bar heights (updated by ResizeObserver) */}
        {aiSuggestionsEnabled && showAgentPanel && (
          <div
            className="fixed right-0 w-80 z-panel border-l border-neutral-5 bg-neutral-1 shadow-lg"
            style={{
              top: "calc(var(--topbar-height) + 0.5rem)",
              bottom: "calc(var(--statusbar-height) + 0.5rem)",
            }}
          >
            <Suspense fallback={null}>
              <LazyAgentTaskQueue onCancel={handleAgentCancel} />
            </Suspense>
          </div>
        )}

        {/* HITL Agent Approval Dialog (Phase 4 HITL) - gated by agent_hitl feature flag */}
        {agentHitlEnabled && showApprovalDialog && activeApproval && (
          <div data-testid="agent-approval-dialog">
            <AgentApprovalDialog
              request={activeApproval}
              isOpen={showApprovalDialog}
              onClose={closeApprovalDialog}
              onApprove={(data) => handleApprove(data.requestId, data.reason)}
              onReject={(data) => handleReject(data.requestId, data.reason)}
              isApproving={isApproving}
              isRejecting={isRejecting}
              currentUser={username ?? undefined}
            />
          </div>
        )}

        {/* HITL Clarification Dialog (Phase 4 HITL) - gated by agent_hitl feature flag */}
        {agentHitlEnabled && showClarificationDialog && activeClarification && (
          <div data-testid="clarification-dialog">
            <ClarificationDialog
              request={activeClarification}
              isOpen={showClarificationDialog}
              onClose={closeClarificationDialog}
              onRespond={(response) =>
                handleClarificationRespond(
                  convertUIResponseCamelCaseToAPIResponse(response),
                )
              }
              isSubmitting={isClarificationSubmitting}
              currentUser={username ?? undefined}
            />
          </div>
        )}

        {/* Session Delete Confirmation Dialog */}
        <ConfirmDialog
          open={deleteConfirmOpen}
          onClose={handleCancelDelete}
          onConfirm={handleConfirmDelete}
          title="Delete Session"
          message="Are you sure you want to delete this session? This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          isDestructive
        />

        {/* Sprint 5.1: Mobile Drawer Navigation - gated by mobile_drawer feature flag */}
        {/* Renders at narrow breakpoints (sm, md) for mobile navigation */}
        {showMobileNav && (
          <MobileDrawer
            isOpen={mobileDrawerOpen}
            onClose={() => setMobileDrawerOpen(false)}
          />
        )}

        {/* Onboarding Wizard (Sprint 3.2) - gated by onboarding_wizard feature flag */}
        {/* High z-index to ensure it appears above other overlays for first-time users */}
        <OnboardingWizard
          isOpen={showOnboarding}
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
          templates={onboardingTemplates}
        />

        {/* Inbound MCP Modals - Server-initiated JSON-RPC requests (ADR-0069) */}
        <InboundMCPModals />
      </div>
      </MCPConnectionProvider>
    </CommandPaletteProvider>
  );
}

// Helper functions for HITL type conversions are now imported from types/hitl.ts
