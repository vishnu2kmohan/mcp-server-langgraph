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
import { useCallback, useMemo, useEffect, useState, Suspense } from "react";
import { useLocation, Outlet } from "react-router";
import { Panel, PanelGroup } from "react-resizable-panels";
import { ConnectedConversationPanel } from "../conversation/ConnectedConversationPanel";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectCanvasCollapsed,
  selectSessionNavCollapsed,
  selectFocusModeEnabled,
  setPanelSizes,
  toggleCanvas,
  toggleSessionNav,
  toggleFocusMode,
  setFocusModeEnabled,
  type CanvasPanelSizes,
} from "../store/slices/canvasSlice";
import {
  selectCurrentSession,
  createSession,
} from "../store/slices/sessionSlice";
import { selectUsername } from "../store/slices/personaSlice";
import {
  selectAllAgents,
  updateAgentStatus,
} from "../store/slices/backgroundAgentSlice";
import { usePersonaRouting } from "../hooks/usePersonaRouting";
import { useConnectionHealthWebSocket } from "../hooks/useConnectionHealthWebSocket";
import { useNudges } from "../hooks/useNudges";
import { useAIPersonaAnalysis } from "../hooks/useAIPersonaAnalysis";
import { useCrossInsightsPanel } from "../hooks/useCrossInsightsPanel";
import { useHITLDialogs } from "../hooks/useHITLDialogs";
import { useIsChatRoute } from "../hooks/useIsChatRoute";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import type { ConnectionStatus, TokenBreakdown } from "./StatusBar";
import { NudgeTooltip } from "../components/Nudge";
import { CrossInsightsPanel } from "../components/Analytics/CrossInsightsPanel";
import { AgentApprovalDialog } from "../components/Admin/AgentApprovalDialog";
import { ClarificationDialog } from "../components/Admin/ClarificationDialog";
// Use consolidated HITL types from types/hitl.ts
import {
  convertUIResponseToAPIResponse,
  convertApprovalPayloadToRequest,
  convertClarificationPayloadToRequest,
} from "../types/hitl";

// Import lazy-loaded AI components (Phase 4) - code-split for reduced bundle size
import {
  LazyAICommandPalette,
  LazyBackgroundAgentPanel,
  LazyAgentTaskQueue,
  type Command,
  type AIInterpretation,
} from "../ai/lazy";

// Import extracted components (de-duplicated from inline versions)
import { ActivityBar } from "./ActivityBar";
import { SessionNav } from "./SessionNav";
import { StatusBar } from "./StatusBar";
import { TopBar } from "./TopBar";
import { ResizeHandle } from "./ResizeHandle";
import { ConnectedCanvasPanel } from "../canvas/ConnectedCanvasPanel";
import { TelemetryViewer } from "../devtools";
import { devLogger } from "../utils/devLogger";
import { LazyDevToolsPanel } from "../components/DevTools";
import {
  selectDevToolsCollapsed,
  selectDevToolsHeight,
  toggleDevTools,
} from "../store/slices/devToolsSlice";
import { authenticatedFetch } from "../utils/authenticatedFetch";

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
// StudioShellLayout Component
// =============================================================================

export function StudioShellLayout() {
  const dispatch = useAppDispatch();
  const sessionNavCollapsed = useAppSelector(selectSessionNavCollapsed);
  const canvasCollapsed = useAppSelector(selectCanvasCollapsed);
  const focusModeEnabled = useAppSelector(selectFocusModeEnabled);
  const devToolsCollapsed = useAppSelector(selectDevToolsCollapsed);
  const _devToolsHeight = useAppSelector(selectDevToolsHeight);

  // AI component state
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showAgentPanel, setShowAgentPanel] = useState(false);

  // Background agents from Redux
  const backgroundAgents = useAppSelector(selectAllAgents);

  // Feature flags for AI components (Phase 4)
  const aiCommandPaletteEnabled = useFeatureFlag("canvas_ai_palette");
  const aiSuggestionsEnabled = useFeatureFlag("ai_suggestions");
  const nudgesEnabled = useFeatureFlag("nudges");

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

  // Get real-time connection health status
  const { status: wsStatus, reconnectAttempts: wsReconnectAttempts } =
    useConnectionHealthWebSocket();

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

  // Get current session for model info
  const currentSession = useAppSelector(selectCurrentSession);
  const modelName = currentSession?.config?.modelName;

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

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      // Check for Cmd+/ (Mac) or Ctrl+/ (Windows/Linux) to toggle canvas
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        dispatch(toggleCanvas());
        return;
      }

      // Check for Cmd+K (Mac) or Ctrl+K (Windows/Linux) to open command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowCommandPalette(true);
        return;
      }

      // Check for Cmd+Shift+I (Mac) or Ctrl+Shift+I (Windows/Linux) to toggle DevTools
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "I") {
        e.preventDefault();
        dispatch(toggleDevTools());
        return;
      }

      // Check for Cmd+Shift+F (Mac) or Ctrl+Shift+F (Windows/Linux) to toggle Focus Mode
      if (
        (e.metaKey || e.ctrlKey) &&
        e.shiftKey &&
        e.key.toLowerCase() === "f"
      ) {
        e.preventDefault();
        dispatch(toggleFocusMode());
        return;
      }

      // Escape key exits focus mode
      if (e.key === "Escape" && focusModeEnabled) {
        e.preventDefault();
        dispatch(setFocusModeEnabled(false));
        return;
      }

      // Note: Cmd+I / Ctrl+I for insights panel is handled by useCrossInsightsPanel hook
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [dispatch, focusModeEnabled]);

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
            // Navigation handled by router
            window.location.href = "/studio/settings";
            break;
          case "open-help":
            window.location.href = "/studio/help";
            break;
          case "open-observability":
            window.location.href = "/studio/observability";
            break;
          case "open-compliance":
            window.location.href = "/studio/compliance";
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
            // Navigate to specified path
            if (typeof interpretation.params.path === "string") {
              window.location.href = interpretation.params.path;
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
    [dispatch],
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

  return (
    <div
      data-testid="studio-shell"
      className="studio-shell flex flex-col h-screen bg-white dark:bg-gray-900"
    >
      {/* TopBar - persona-aware header (hidden in focus mode) */}
      {!focusModeEnabled && (
        <TopBar
          onUserMenuClick={handleUserMenuClick}
          pendingApprovals={
            agentHitlEnabled ? pendingApprovals.length : undefined
          }
          onPendingApprovalsClick={
            agentHitlEnabled ? handlePendingApprovalsClick : undefined
          }
        />
      )}

      {/* Focus Mode Exit Button - shows when in focus mode */}
      {focusModeEnabled && (
        <button
          data-testid="focus-mode-exit"
          onClick={() => dispatch(setFocusModeEnabled(false))}
          className="fixed top-2 right-2 z-50 p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-white text-xs transition-opacity opacity-30 hover:opacity-100"
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
        </button>
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
            className="flex h-full overflow-hidden"
          >
            {/* Activity Bar - fixed width (hidden in focus mode) */}
            {/* Sprint 4: AI-native navigation predictions enabled via feature flag */}
            {!focusModeEnabled && (
              <ActivityBar
                enableAI={aiSuggestionsEnabled}
                reorderByPrediction={aiSuggestionsEnabled}
              />
            )}

            {/* Main content area - conditionally render based on route */}
            {/* Key props force React to unmount/remount when switching between layouts */}
            {/* This prevents PanelGroup state from persisting across route type changes */}
            {isChatRoute ? (
              /* Chat routes: 3-panel canvas layout */
              <PanelGroup
                key="chat-canvas-layout"
                direction="horizontal"
                onLayout={handlePanelResize}
                className="flex-1"
              >
                {/* Session Nav Panel */}
                {!sessionNavCollapsed && (
                  <>
                    <Panel
                      id="session-nav"
                      order={1}
                      defaultSize={20}
                      minSize={15}
                      maxSize={35}
                    >
                      <SessionNav />
                    </Panel>
                    <ResizeHandle />
                  </>
                )}

                {/* Conversation Panel */}
                <Panel
                  id="conversation"
                  order={2}
                  defaultSize={canvasCollapsed ? 80 : 40}
                  minSize={30}
                >
                  <ConnectedConversationPanel />
                </Panel>

                {/* Canvas Panel */}
                {!canvasCollapsed && (
                  <>
                    <ResizeHandle />
                    <Panel
                      id="canvas"
                      order={3}
                      defaultSize={40}
                      minSize={25}
                      maxSize={60}
                    >
                      <ConnectedCanvasPanel />
                    </Panel>
                  </>
                )}
              </PanelGroup>
            ) : (
              /* Full-page routes: Render the routed component via Outlet */
              /* Suspense boundary handles lazy-loaded routes (e.g., WorkflowsPage, ObservabilityPage) */
              <div
                key="full-page-outlet"
                data-testid="route-outlet"
                className="flex-1 h-full overflow-auto bg-white dark:bg-gray-900"
              >
                <Suspense
                  fallback={
                    <div
                      className="flex items-center justify-center h-full"
                      data-testid="route-loading"
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          Loading...
                        </span>
                      </div>
                    </div>
                  }
                >
                  <Outlet />
                </Suspense>
              </div>
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
              defaultSize={25}
              minSize={10}
              maxSize={50}
            >
              <Suspense
                fallback={
                  <div className="flex items-center justify-center h-full bg-white dark:bg-gray-900">
                    <span className="text-sm text-gray-400">
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

      {/* StatusBar - connection status, model, tokens, user, DevTools toggle (hidden in focus mode) */}
      {!focusModeEnabled && (
        <StatusBar
          connectionStatus={connectionStatus}
          reconnectAttempts={wsReconnectAttempts}
          modelName={modelName ?? undefined}
          tokenCount={tokenCount > 0 ? tokenCount : undefined}
          tokenBreakdown={tokenBreakdown}
          userName={username ?? undefined}
          agentCount={backgroundAgents.length}
          onAgentQueueToggle={handleAgentQueueToggle}
          agentQueueOpen={showAgentPanel}
          pendingApprovals={
            agentHitlEnabled ? pendingApprovals.length : undefined
          }
          onPendingApprovalsClick={
            agentHitlEnabled ? handlePendingApprovalsClick : undefined
          }
          devToolsCollapsed={devToolsCollapsed}
          onDevToolsToggle={() => dispatch(toggleDevTools())}
        />
      )}

      {/* Dev mode telemetry viewer (fixed position overlay) */}
      <TelemetryViewer />

      {/* AI Nudges (Phase 1.3 + 6.3) - contextual hints and feature discovery */}
      {nudgesEnabled && activeNudge && (
        <div className="fixed bottom-20 left-16 z-50 max-w-xs">
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
            className="fixed top-16 left-1/2 transform -translate-x-1/2 z-50 max-w-lg"
            role="alert"
            data-testid="persona-mismatch-banner"
          >
            <div className="bg-purple-50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-700 rounded-lg shadow-lg p-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0">
                  <svg
                    className="w-5 h-5 text-purple-600 dark:text-purple-400"
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
                  <h4 className="text-sm font-semibold text-purple-800 dark:text-purple-200">
                    We noticed you&apos;re using advanced features
                  </h4>
                  <p className="text-sm text-purple-700 dark:text-purple-300 mt-1">
                    Your usage pattern suggests you might benefit from{" "}
                    <strong>{detectedPersona?.replace(/-/g, " ")}</strong>{" "}
                    capabilities.
                  </p>
                  {recommendation && (
                    <p className="text-sm text-purple-600 dark:text-purple-400 mt-2">
                      {recommendation}
                    </p>
                  )}
                  {behaviorSignals.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {behaviorSignals.slice(0, 3).map((signal, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center px-2 py-0.5 text-xs bg-purple-100 dark:bg-purple-800/50 text-purple-700 dark:text-purple-300 rounded"
                        >
                          {signal}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setPersonaBannerDismissed(true)}
                  className="flex-shrink-0 p-1 text-purple-400 hover:text-purple-600 dark:hover:text-purple-200"
                  aria-label="Dismiss persona suggestion"
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
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
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
            className="fixed bottom-16 left-16 z-40 w-80"
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

      {/* AI Command Palette (Cmd+K) - gated by canvas_ai_palette feature flag */}
      {/* Lazy-loaded to reduce initial bundle size */}
      {aiCommandPaletteEnabled && (
        <Suspense fallback={null}>
          <LazyAICommandPalette
            commands={PALETTE_COMMANDS}
            isOpen={showCommandPalette}
            onClose={() => setShowCommandPalette(false)}
            onExecute={handleCommandExecute}
            onAIInterpret={handleAIInterpret}
            groupByCategory
          />
        </Suspense>
      )}

      {/* Background Agent Panel (floating, bottom-right) - gated by ai_suggestions feature flag */}
      {/* Lazy-loaded to reduce initial bundle size */}
      {aiSuggestionsEnabled && backgroundAgents.length > 0 && (
        <div className="fixed bottom-16 right-4 z-40 w-80">
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
      {aiSuggestionsEnabled && showAgentPanel && (
        <div className="fixed top-14 right-0 bottom-8 w-80 z-30 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg">
          <Suspense fallback={null}>
            <LazyAgentTaskQueue onCancel={handleAgentCancel} />
          </Suspense>
        </div>
      )}

      {/* HITL Agent Approval Dialog (Phase 4 HITL) - gated by agent_hitl feature flag */}
      {agentHitlEnabled && showApprovalDialog && activeApproval && (
        <div data-testid="agent-approval-dialog">
          <AgentApprovalDialog
            request={convertApprovalPayloadToRequest(activeApproval)}
            isOpen={showApprovalDialog}
            onClose={closeApprovalDialog}
            onApprove={(data) => handleApprove(data.request_id, data.reason)}
            onReject={(data) => handleReject(data.request_id, data.reason)}
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
            request={convertClarificationPayloadToRequest(activeClarification)}
            isOpen={showClarificationDialog}
            onClose={closeClarificationDialog}
            onRespond={(response) =>
              handleClarificationRespond(
                convertUIResponseToAPIResponse(response),
              )
            }
            isSubmitting={isClarificationSubmitting}
            currentUser={username ?? undefined}
          />
        </div>
      )}
    </div>
  );
}

// Helper functions for HITL type conversions are now imported from types/hitl.ts
