/**
 * ConnectedChatInputForm
 *
 * Full-featured chat input with all hooks wired up:
 * - File upload (drag-drop, click to select)
 * - Voice input (Web Speech API)
 * - Slash commands
 * - Inline AI suggestions
 * - Reasoning effort selector (for thinking models)
 * - Model selector
 * - Knowledge Base focus mode (Perplexity-style)
 *
 * This replaces the basic conversation/ChatInput.tsx and provides
 * a consistent, feature-rich chat experience throughout the app.
 *
 * Uses ChatInput (the consolidated pill-style component) which provides
 * all features in a unified interface.
 */
import { useCallback, useMemo, useState, useEffect, useRef } from "react";
import {
  ChatInput,
  type SlashCommand,
  type ModelOption,
} from "../components/Chat/ChatInput";
import type { KBFocusMode } from "../components/Chat/KnowledgeBaseFocus";
import type { ReasoningEffortLevel } from "../components/Chat/ReasoningEffortSelector";
import type { ToolOption } from "../components/Chat/ToolSelector";
import type { ToolSelectionMode } from "../types/tools";
import { useFileUpload } from "../hooks/useFileUpload";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { useKBStatus } from "../hooks/useKBStatus";
import { useUrlContentFetch } from "../hooks/useUrlContentFetch";
import { useInlineSuggestions } from "../hooks/useInlineSuggestions";
import { useAISuggestionsWebSocket } from "../hooks/useAISuggestionsWebSocket";
import { useAvailableTools } from "../hooks/useAvailableTools";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import { useToolPreference } from "../contexts/PreferencesContext";
import { useAppSelector, useAppDispatch } from "../store/hooks";
import { selectSubmitOnEnter } from "../store/slices/uiSlice";
import { useConnectorSuggestions } from "../hooks/useConnectorSuggestions";
import { ConnectorSuggestionBar } from "../components/Chat/ConnectorSuggestionBar";
import { startConnectionSetup } from "../store/slices/chatConnectionSlice";
import {
  selectExecutionMode,
  selectCanBypass,
  cycleExecutionMode,
  setExecutionMode,
  setHasBypassPermission,
  type ExecutionMode,
} from "../store/slices/executionModeSlice";
import { useCheckBypassPermissionQuery } from "../api";
import type { ConnectionTemplate } from "../types/connectionTemplate";
import { toast } from "sonner";
import { TOAST_ID_URL_FETCH_ERROR } from "../constants/toastIds";

// =============================================================================
// Types
// =============================================================================

export interface ConnectedChatInputFormProps {
  /** Current input value */
  value: string;
  /** Called when input value changes */
  onChange: (value: string) => void;
  /** Called when message is submitted */
  onSubmit: (message: string) => void;
  /** Whether the AI is currently processing */
  isProcessing?: boolean;
  /** Whether the AI is currently streaming a response */
  isStreaming?: boolean;
  /** Callback to stop streaming */
  onStopStreaming?: () => void;
  /** Available slash commands */
  slashCommands?: SlashCommand[];
  /** Called when a slash command is selected */
  onSlashCommand?: (command: SlashCommand) => void;
  /** Enable inline ghost text suggestions */
  enableInlineSuggestions?: boolean;
  /** Current inline suggestion text */
  inlineSuggestion?: string;
  /** Whether suggestion is being fetched */
  isSuggestionLoading?: boolean;
  /** Callback when user accepts suggestion (Tab) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape) */
  onDismissSuggestion?: () => void;
  /** Use the useInlineSuggestions hook internally to fetch suggestions */
  useInlineSuggestionsHook?: boolean;
  /** Session ID for inline suggestions context (used when useInlineSuggestionsHook is true) */
  sessionId?: string;
  /** Auto-focus the textarea on mount */
  autoFocus?: boolean;
  /** Controlled KB focus mode value (for lifting state to parent) */
  kbFocusValue?: KBFocusMode;
  /** Callback when KB focus mode changes (for lifting state to parent) */
  onKBFocusChange?: (mode: KBFocusMode) => void;

  // ==========================================================================
  // Model Selection Props (Sprint 1 - Chat Input Gap Fix)
  // ==========================================================================

  /** Whether to show the model selector dropdown */
  showModelSelector?: boolean;
  /** Currently selected model ID */
  selectedModel?: string;
  /** Available models for selection */
  availableModels?: ModelOption[];
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Whether models are currently loading from API */
  isModelsLoading?: boolean;
  /** Recently used model IDs (most recent first) */
  recentModels?: string[];
  /** Whether to show search input in model dropdown (for large model lists) */
  enableModelSearch?: boolean;

  // ==========================================================================
  // Reasoning Effort Props (Sprint 1 - Chat Input Gap Fix)
  // ==========================================================================

  /** Whether the current model supports extended thinking */
  modelSupportsThinking?: boolean;
  /** Current reasoning effort level */
  reasoningEffort?: ReasoningEffortLevel;
  /** Callback when reasoning effort level changes */
  onReasoningEffortChange?: (level: ReasoningEffortLevel) => void;
  /** Whether thinking is enabled for supported models */
  enableThinking?: boolean;
  /** Callback when thinking enabled state changes */
  onEnableThinkingChange?: (enabled: boolean) => void;

  // ==========================================================================
  // URL Fetch Props (Sprint 1 - Chat Input Gap Fix)
  // ==========================================================================

  /** Enable URL content fetching when #https://... detected */
  enableUrlFetch?: boolean;

  // ==========================================================================
  // Tool Selection Props (Manual Tool Selection)
  // ==========================================================================

  /** Controlled selected tools (for lifting state to parent) */
  selectedTools?: string[];
  /** Callback when selected tools change (for lifting state to parent) */
  onSelectedToolsChange?: (tools: string[]) => void;
  /** Controlled tool selection mode (for lifting state to parent) */
  toolSelectionMode?: ToolSelectionMode;
  /** Callback when tool selection mode changes (for lifting state to parent) */
  onToolSelectionModeChange?: (mode: ToolSelectionMode) => void;

  // v7: Tool preference for native vs builtin execution
  /** Controlled tool preference (for lifting state to parent) */
  toolPreference?: "auto" | "native" | "builtin" | "mcp";
  /** Callback when tool preference changes (for lifting state to parent) */
  onToolPreferenceChange?: (
    preference: "auto" | "native" | "builtin" | "mcp",
  ) => void;

  // ==========================================================================
  // Style Presets Props (behind PreferencesMenu)
  // ==========================================================================

  /** Currently active style preset */
  activeStylePreset?: import("../components/Chat/StylePresets").PresetName;
  /** Callback when style preset changes */
  onStylePresetChange?: (
    preset: import("../components/Chat/StylePresets").StylePreset,
  ) => void;
}

// =============================================================================
// Default Slash Commands
// =============================================================================

const DEFAULT_SLASH_COMMANDS: SlashCommand[] = [
  { name: "new", description: "Start a new chat session", icon: "message" },
  { name: "clear", description: "Clear current conversation", icon: "trash" },
  {
    name: "help",
    description: "Show help and available commands",
    icon: "help",
  },
  { name: "export", description: "Export conversation", icon: "download" },
];

// =============================================================================
// Component
// =============================================================================

export function ConnectedChatInputForm({
  value,
  onChange,
  onSubmit,
  isProcessing = false,
  isStreaming = false,
  onStopStreaming,
  slashCommands = DEFAULT_SLASH_COMMANDS,
  onSlashCommand,
  enableInlineSuggestions = false,
  inlineSuggestion: inlineSuggestionProp = "",
  isSuggestionLoading: isSuggestionLoadingProp = false,
  onAcceptSuggestion: onAcceptSuggestionProp,
  onDismissSuggestion: onDismissSuggestionProp,
  useInlineSuggestionsHook = false,
  sessionId,
  autoFocus = false,
  kbFocusValue,
  onKBFocusChange,
  // Model selection (Sprint 1)
  showModelSelector = false,
  selectedModel,
  availableModels = [],
  onModelChange,
  recentModels = [],
  enableModelSearch = false,
  // Reasoning effort (Sprint 1)
  modelSupportsThinking = false,
  reasoningEffort = "medium",
  onReasoningEffortChange,
  enableThinking = false,
  onEnableThinkingChange,
  // URL fetch (Sprint 1)
  enableUrlFetch = false,
  // Models loading state (Sprint 1)
  isModelsLoading = false,
  // Tool selection (Manual Tool Selection)
  selectedTools: selectedToolsProp,
  onSelectedToolsChange,
  toolSelectionMode: toolSelectionModeProp,
  onToolSelectionModeChange,
  // v7: Tool preference for native vs builtin execution
  toolPreference: toolPreferenceProp,
  onToolPreferenceChange,
  // Style presets (behind PreferencesMenu)
  activeStylePreset,
  onStylePresetChange,
}: ConnectedChatInputFormProps) {
  // =============================================================================
  // Feature Flags & UI State
  // =============================================================================
  const enableKBFocus = useFeatureFlag("kb_focus");
  const enableWebSocketSuggestions = useFeatureFlag("ai_suggestions_websocket");
  const enableManualToolSelection = useFeatureFlag("manual_tool_selection");
  const enableExecutionModeToggle = useFeatureFlag("execution_mode_toggle");
  const enablePreferencesMenu = useFeatureFlag("preferences_menu");
  const submitOnEnter = useAppSelector(selectSubmitOnEnter);

  // =============================================================================
  // Execution Mode State (Ctrl/Cmd+Shift+M toggle)
  // =============================================================================
  const dispatch = useAppDispatch();
  const executionMode = useAppSelector(selectExecutionMode);
  const canBypass = useAppSelector(selectCanBypass);
  const telemetry = useSessionTelemetry();

  // Fetch bypass permission from OpenFGA (bypass_executor on system:global)
  const { data: bypassPermission } = useCheckBypassPermissionQuery(undefined, {
    // Skip if execution mode toggle is disabled
    skip: !enableExecutionModeToggle,
    // Refetch periodically in case permission changes
    pollingInterval: 300000, // 5 minutes
  });

  // Sync bypass permission from API to Redux
  useEffect(() => {
    if (bypassPermission?.allowed !== undefined) {
      dispatch(setHasBypassPermission(bypassPermission.allowed));
    }
  }, [bypassPermission?.allowed, dispatch]);

  // Helper to get next mode in cycle (for telemetry before dispatch)
  const getNextCycleMode = useCallback(
    (currentMode: ExecutionMode): ExecutionMode => {
      const modes: ExecutionMode[] = canBypass
        ? ["default", "plan", "auto_accept", "bypass"]
        : ["default", "plan", "auto_accept"];
      const currentIndex = modes.indexOf(currentMode);
      return modes[(currentIndex + 1) % modes.length];
    },
    [canBypass],
  );

  const handleCycleExecutionMode = useCallback(() => {
    const fromMode = executionMode;
    const toMode = getNextCycleMode(fromMode);

    // Track telemetry before dispatch (keyboard trigger)
    telemetry.trackExecutionModeChange({
      fromMode,
      toMode,
      sessionId,
      trigger: "keyboard",
    });

    dispatch(cycleExecutionMode());
  }, [dispatch, executionMode, getNextCycleMode, sessionId, telemetry]);

  const handleExecutionModeChange = useCallback(
    (mode: ExecutionMode) => {
      const fromMode = executionMode;

      // Track telemetry before dispatch (click trigger)
      telemetry.trackExecutionModeChange({
        fromMode,
        toMode: mode,
        sessionId,
        trigger: "click",
      });

      dispatch(setExecutionMode(mode));
    },
    [dispatch, executionMode, sessionId, telemetry],
  );

  // Track previous sessionId for context updates
  const prevSessionIdRef = useRef<string | undefined>(undefined);

  // =============================================================================
  // Tool Selection State & Hook (Manual Tool Selection)
  // =============================================================================
  const [internalSelectedTools, setInternalSelectedTools] = useState<string[]>(
    [],
  );
  const [internalToolSelectionMode, setInternalToolSelectionMode] =
    useState<ToolSelectionMode>("auto");

  // v7: Tool preference with persistence (native vs builtin)
  // Get persisted preference from preferences context
  const {
    toolPreference: persistedToolPreference,
    setToolPreference: persistToolPreference,
  } = useToolPreference();
  // Internal state initialized from persisted preference
  const [internalToolPreference, setInternalToolPreference] = useState<
    "auto" | "native" | "builtin" | "mcp"
  >(persistedToolPreference);

  // Sync internal state when persisted preference changes (e.g., from settings page)
  const prevPersistedRef = useRef(persistedToolPreference);
  useEffect(() => {
    if (persistedToolPreference !== prevPersistedRef.current) {
      prevPersistedRef.current = persistedToolPreference;
      setInternalToolPreference(persistedToolPreference);
    }
  }, [persistedToolPreference]);

  // Use controlled values if provided, otherwise use internal state
  const selectedTools = selectedToolsProp ?? internalSelectedTools;
  const toolSelectionMode = toolSelectionModeProp ?? internalToolSelectionMode;
  // v7: Use controlled value if provided, otherwise use internal state (persisted)
  const toolPreference = toolPreferenceProp ?? internalToolPreference;

  // Fetch available tools (only when feature is enabled)
  const { tools: availableToolsData, isLoading: isToolsLoading } =
    useAvailableTools({
      skip: !enableManualToolSelection,
    });

  // Transform tools to ToolOption format for ToolSelector
  const availableTools: ToolOption[] = useMemo(() => {
    if (!availableToolsData) return [];
    return availableToolsData.map((tool) => ({
      name: tool.name,
      toolId: tool.toolId, // v7: Add toolId for selection
      displayName: tool.displayName,
      source: tool.source,
      serverName: tool.serverName ?? undefined,
      provider: tool.provider ?? undefined, // v7: Add provider for native tools
      description: tool.description,
      category: tool.category ?? undefined,
    }));
  }, [availableToolsData]);

  // Handle tool selection change
  const handleSelectedToolsChange = useCallback(
    (tools: string[]) => {
      setInternalSelectedTools(tools);
      onSelectedToolsChange?.(tools);
    },
    [onSelectedToolsChange],
  );

  // Handle tool selection mode change
  const handleToolSelectionModeChange = useCallback(
    (mode: ToolSelectionMode) => {
      setInternalToolSelectionMode(mode);
      onToolSelectionModeChange?.(mode);
    },
    [onToolSelectionModeChange],
  );

  // v7: Handle tool preference change (native vs builtin execution)
  // Persists the change to localStorage via preferences context
  const handleToolPreferenceChange = useCallback(
    (preference: "auto" | "native" | "builtin" | "mcp") => {
      setInternalToolPreference(preference);
      // Persist to localStorage via preferences context
      persistToolPreference(preference);
      onToolPreferenceChange?.(preference);
    },
    [onToolPreferenceChange, persistToolPreference],
  );

  // =============================================================================
  // Knowledge Base Status Hook
  // =============================================================================
  const { kbStatusForUI, statusMessage: kbStatusMessage } = useKBStatus({
    skip: !enableKBFocus,
  });

  // KB focus mode state (internal fallback, use controlled if provided)
  const [internalKbFocusMode, setInternalKbFocusMode] =
    useState<KBFocusMode>("all");
  // Use controlled value if provided, otherwise use internal state
  const kbFocusMode = kbFocusValue ?? internalKbFocusMode;

  // =============================================================================
  // URL Content Fetch Hook (Sprint 1 - Chat Input Gap Fix)
  // =============================================================================
  const { fetchedContent, loadingUrls, clearUrl, detectUrls } =
    useUrlContentFetch({
      autoFetch: enableUrlFetch,
      debounceMs: 500,
    });

  // Detect URLs in input when enableUrlFetch is true
  useEffect(() => {
    if (enableUrlFetch) {
      detectUrls(value);
    }
  }, [enableUrlFetch, value, detectUrls]);

  // Show toast when URL fetch fails (use ref to avoid re-firing on stable errors)
  const lastToastedUrlError = useRef<string | null>(null);
  useEffect(() => {
    const failedFetch = fetchedContent.find((c) => c.error);
    if (failedFetch && failedFetch.error !== lastToastedUrlError.current) {
      lastToastedUrlError.current = failedFetch.error ?? null;
      toast.error(`Failed to fetch URL: ${failedFetch.error}`, {
        id: TOAST_ID_URL_FETCH_ERROR,
      });
    } else if (!failedFetch) {
      lastToastedUrlError.current = null;
    }
  }, [fetchedContent]);

  // =============================================================================
  // File Upload Hook
  // =============================================================================
  const {
    files: uploadFiles,
    isUploading,
    isDragging,
    error: fileError,
    selectFiles,
    removeFile,
    dragHandlers,
  } = useFileUpload({
    maxSizeMB: 10,
    maxFiles: 5,
    acceptedTypes: [
      "image/*",
      "application/pdf",
      "text/plain",
      "text/csv",
      "application/json",
    ],
  });

  // =============================================================================
  // Voice Input Hook
  // =============================================================================
  const {
    isListening,
    isSupported: isVoiceSupported,
    error: voiceError,
    startListening,
    stopListening,
    transcript: _transcript,
  } = useVoiceInput({
    continuous: false,
    interimResults: true,
    onTranscript: (newTranscript) => {
      // Append transcript to current input
      onChange(value + (value ? " " : "") + newTranscript);
    },
  });

  // =============================================================================
  // Inline Suggestions Hook (optional - enabled via useInlineSuggestionsHook prop)
  // =============================================================================
  const {
    suggestion: hookSuggestion,
    isLoading: hookSuggestionLoading,
    updateInput: updateSuggestionInput,
    acceptSuggestion: acceptHookSuggestion,
    dismissSuggestion: dismissHookSuggestion,
  } = useInlineSuggestions({
    enabled: useInlineSuggestionsHook && enableInlineSuggestions,
    sessionId,
    onAccept: (suggestion) => {
      // Append the suggestion to the current input
      onChange(value + suggestion);
      // Note: Do NOT call onAcceptSuggestionProp here — the outer onAcceptSuggestion
      // handler already calls it, and calling it in both places would double-fire.
    },
    onDismiss: () => {
      // Note: Do NOT call onDismissSuggestionProp here — the outer onDismissSuggestion
      // handler already calls it, and calling it in both places would double-fire.
    },
  });

  // Update suggestions when input changes (only when hook is enabled)
  useEffect(() => {
    if (useInlineSuggestionsHook && enableInlineSuggestions) {
      updateSuggestionInput(value);
    }
  }, [
    value,
    useInlineSuggestionsHook,
    enableInlineSuggestions,
    updateSuggestionInput,
  ]);

  // =============================================================================
  // WebSocket Inline Suggestions Hook (ai_suggestions_websocket feature flag)
  // Uses WebSocket for lower-latency suggestions with cursor position awareness
  // Falls back to REST-based useInlineSuggestions when WebSocket is disconnected
  // =============================================================================
  const useWebSocketForSuggestions =
    enableWebSocketSuggestions && enableInlineSuggestions && !!sessionId;

  const {
    status: wsStatus,
    currentSuggestion: wsSuggestion,
    isPending: wsIsPending,
    requestSuggestionDebounced: wsRequestSuggestionDebounced,
    acceptSuggestion: wsAcceptSuggestion,
    rejectSuggestion: wsRejectSuggestion,
    updateContext: wsUpdateContext,
    clearSuggestion: wsClearSuggestion,
  } = useAISuggestionsWebSocket({
    enabled: useWebSocketForSuggestions,
    sessionId,
    debounceMs: 300, // Built-in debouncing for typing scenarios
    // Note: onSuggestion is intentionally NOT wired to onAcceptSuggestionProp.
    // The accept callback should only fire when the user explicitly accepts
    // (Tab key), not when a suggestion arrives. See onAcceptSuggestion below.
  });

  // Track cursor position for WebSocket suggestions
  const cursorPositionRef = useRef<number>(0);
  // Track previous value to avoid redundant requests
  const prevValueRef = useRef<string>("");

  // Request WebSocket suggestion when input changes (uses hook's built-in debouncing)
  useEffect(() => {
    // Skip if value hasn't changed (prevents redundant requests on cursor-only changes)
    if (value === prevValueRef.current) {
      return;
    }
    prevValueRef.current = value;

    if (
      useWebSocketForSuggestions &&
      wsStatus === "connected" &&
      value.length > 3
    ) {
      // Request suggestion (hook handles debouncing internally)
      wsRequestSuggestionDebounced(value, cursorPositionRef.current);
    }
  }, [
    value,
    useWebSocketForSuggestions,
    wsStatus,
    wsRequestSuggestionDebounced,
  ]);

  // Update context when session changes
  useEffect(() => {
    if (
      useWebSocketForSuggestions &&
      wsStatus === "connected" &&
      sessionId &&
      sessionId !== prevSessionIdRef.current
    ) {
      wsUpdateContext(`Session: ${sessionId}`);
      prevSessionIdRef.current = sessionId;
    }
  }, [sessionId, useWebSocketForSuggestions, wsStatus, wsUpdateContext]);

  // Determine if WebSocket is active and connected
  const isWebSocketActive =
    useWebSocketForSuggestions && wsStatus === "connected";

  // Resolve which suggestion values to use:
  // Priority: WebSocket (when connected) > REST hook > props
  const inlineSuggestion = isWebSocketActive
    ? wsSuggestion?.text || ""
    : useInlineSuggestionsHook
      ? hookSuggestion
      : inlineSuggestionProp;

  const isSuggestionLoading = isWebSocketActive
    ? wsIsPending
    : useInlineSuggestionsHook
      ? hookSuggestionLoading
      : isSuggestionLoadingProp;

  // Accept suggestion handler - works with WebSocket or REST
  const onAcceptSuggestion = useCallback(
    (suggestion: string) => {
      if (isWebSocketActive && wsSuggestion?.suggestionId) {
        // Send accept feedback to WebSocket for learning
        wsAcceptSuggestion(wsSuggestion.suggestionId);
      }
      // Call the REST hook accept if using hook mode
      if (useInlineSuggestionsHook) {
        acceptHookSuggestion();
      }
      // Always call prop callback if provided
      onAcceptSuggestionProp?.(suggestion);
    },
    [
      isWebSocketActive,
      wsSuggestion,
      wsAcceptSuggestion,
      useInlineSuggestionsHook,
      acceptHookSuggestion,
      onAcceptSuggestionProp,
    ],
  );

  // Dismiss suggestion handler - works with WebSocket or REST
  const onDismissSuggestion = useCallback(() => {
    if (isWebSocketActive && wsSuggestion?.suggestionId) {
      // Send reject feedback to WebSocket for learning
      wsRejectSuggestion(wsSuggestion.suggestionId);
    } else if (useWebSocketForSuggestions) {
      // Clear stale WS suggestion when WS is configured but currently disconnected
      wsClearSuggestion();
    }
    // Call the REST hook dismiss if using hook mode
    if (useInlineSuggestionsHook) {
      dismissHookSuggestion();
    }
    // Always call prop callback if provided
    onDismissSuggestionProp?.();
  }, [
    isWebSocketActive,
    useWebSocketForSuggestions,
    wsSuggestion,
    wsRejectSuggestion,
    wsClearSuggestion,
    useInlineSuggestionsHook,
    dismissHookSuggestion,
    onDismissSuggestionProp,
  ]);

  // =============================================================================
  // Connector Suggestions Hook (Phase 5 - Proactive Suggestions)
  // Shows connection suggestions when user input matches tool keywords
  // =============================================================================
  const enableConnectorSuggestions = useFeatureFlag("connector_suggestions");

  const {
    suggestions: connectorSuggestions,
    isLoading: isConnectorSuggestionsLoading,
    isVisible: isConnectorSuggestionsVisible,
    updateInput: updateConnectorSuggestionInput,
    dismiss: dismissConnectorSuggestion,
  } = useConnectorSuggestions({
    enabled: enableConnectorSuggestions,
    minInputLength: 5,
    debounceMs: 300,
  });

  // Update connector suggestions when input changes
  useEffect(() => {
    if (enableConnectorSuggestions) {
      updateConnectorSuggestionInput(value);
    }
  }, [value, enableConnectorSuggestions, updateConnectorSuggestionInput]);

  // Handle connect action from suggestion bar
  const handleConnectorSuggestionConnect = useCallback(
    (template: ConnectionTemplate) => {
      dispatch(startConnectionSetup({ templateId: template.id }));
      dismissConnectorSuggestion();
    },
    [dispatch, dismissConnectorSuggestion],
  );

  // =============================================================================
  // Handlers
  // =============================================================================

  const handleInputChange = useCallback(
    (newValue: string) => {
      onChange(newValue);
    },
    [onChange],
  );

  const handleSubmit = useCallback(() => {
    if (value.trim()) {
      onSubmit(value.trim());
    }
  }, [value, onSubmit]);

  const handleSelectFiles = useCallback(
    (files: File[]) => {
      selectFiles(files);
    },
    [selectFiles],
  );

  const handleRemoveFile = useCallback(
    (id: string) => {
      removeFile(id);
    },
    [removeFile],
  );

  const handleStartListening = useCallback(() => {
    startListening();
  }, [startListening]);

  const handleStopListening = useCallback(() => {
    stopListening();
  }, [stopListening]);

  const handleSlashCommandSelect = useCallback(
    (command: SlashCommand) => {
      onSlashCommand?.(command);
      // Clear input after command selection
      onChange("");
    },
    [onSlashCommand, onChange],
  );

  const handleKBFocusModeChange = useCallback(
    (mode: KBFocusMode) => {
      // Update internal state (for uncontrolled mode)
      setInternalKbFocusMode(mode);
      // Notify parent (for controlled mode)
      onKBFocusChange?.(mode);
    },
    [onKBFocusChange],
  );

  // Memoize cursor position handler to avoid re-renders on every keystroke
  const handleCursorPositionChange = useCallback((pos: number) => {
    cursorPositionRef.current = pos;
  }, []);

  // Memoize drag handlers to avoid re-renders
  const memoizedDragHandlers = useMemo(() => dragHandlers, [dragHandlers]);

  return (
    <>
      {/* Connector Suggestion Bar (Phase 5 - Proactive Suggestions) */}
      {isConnectorSuggestionsVisible && (
        <div className="mb-3 max-w-4xl mx-auto px-4">
          <ConnectorSuggestionBar
            suggestions={connectorSuggestions}
            onConnect={handleConnectorSuggestionConnect}
            onDismiss={dismissConnectorSuggestion}
            isLoading={isConnectorSuggestionsLoading}
          />
        </div>
      )}
      <ChatInput
        value={value}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        disabled={isProcessing}
        isStreaming={isStreaming}
        onStopStreaming={onStopStreaming}
        // Voice input
        isListening={isListening}
        isVoiceSupported={isVoiceSupported}
        voiceError={voiceError ?? undefined}
        onStartListening={handleStartListening}
        onStopListening={handleStopListening}
        // File upload
        uploadFiles={uploadFiles}
        isUploading={isUploading}
        isDragging={isDragging}
        fileError={fileError ?? undefined}
        onSelectFiles={handleSelectFiles}
        onRemoveFile={handleRemoveFile}
        dragHandlers={memoizedDragHandlers}
        // Slash commands
        slashCommands={slashCommands}
        onSlashCommandSelect={handleSlashCommandSelect}
        // Inline suggestions
        enableInlineSuggestions={enableInlineSuggestions}
        inlineSuggestion={inlineSuggestion}
        isSuggestionLoading={isSuggestionLoading}
        onAcceptSuggestion={onAcceptSuggestion}
        onDismissSuggestion={onDismissSuggestion}
        // Auto-focus
        autoFocus={autoFocus}
        // Submit behavior (Enter vs Ctrl+Enter)
        submitOnEnter={submitOnEnter}
        // Knowledge Base Focus (feature flag controlled)
        showKBFocus={enableKBFocus}
        kbFocusValue={kbFocusMode}
        onKBFocusChange={handleKBFocusModeChange as (mode: string) => void}
        kbStatus={kbStatusForUI === "unavailable" ? "error" : kbStatusForUI}
        kbStatusMessage={kbStatusMessage}
        // Model selection (Sprint 1 - Chat Input Gap Fix)
        showModelSelector={showModelSelector}
        selectedModel={selectedModel}
        availableModels={availableModels}
        onModelChange={onModelChange}
        isModelsLoading={isModelsLoading}
        recentModels={recentModels}
        enableModelSearch={enableModelSearch}
        // Reasoning effort (Sprint 1 - Chat Input Gap Fix)
        modelSupportsThinking={modelSupportsThinking}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={onReasoningEffortChange}
        enableThinking={enableThinking}
        onEnableThinkingChange={onEnableThinkingChange}
        // URL fetch (Sprint 1 - Chat Input Gap Fix)
        enableUrlFetch={enableUrlFetch}
        urlFetchLoading={loadingUrls}
        fetchedUrls={fetchedContent.map((c) => ({
          url: c.url,
          title: c.title || c.url,
          content: c.content || "",
        }))}
        onRemoveFetchedUrl={clearUrl}
        // Tool selection (Manual Tool Selection)
        showToolSelector={enableManualToolSelection}
        selectedTools={selectedTools}
        onSelectedToolsChange={handleSelectedToolsChange}
        toolSelectionMode={toolSelectionMode}
        onToolSelectionModeChange={handleToolSelectionModeChange}
        availableTools={availableTools}
        isToolsLoading={isToolsLoading}
        // v7: Tool preference for native vs builtin execution
        toolPreference={toolPreference}
        onToolPreferenceChange={handleToolPreferenceChange}
        // Cursor position tracking for WebSocket suggestions
        onCursorPositionChange={handleCursorPositionChange}
        // Execution mode (Ctrl/Cmd+Shift+M toggle)
        executionMode={executionMode}
        onCycleExecutionMode={
          enableExecutionModeToggle ? handleCycleExecutionMode : undefined
        }
        onExecutionModeChange={
          enableExecutionModeToggle ? handleExecutionModeChange : undefined
        }
        hasBypassPermission={canBypass}
        // Preferences menu (consolidated settings)
        showPreferencesMenu={enablePreferencesMenu}
        kbFocusMode={kbFocusMode as "all" | "kb_only" | "web_only" | "none"}
        onKBFocusModeChange={handleKBFocusModeChange}
        // Style presets (behind PreferencesMenu)
        activeStylePreset={activeStylePreset}
        onStylePresetChange={onStylePresetChange}
      />
    </>
  );
}

export default ConnectedChatInputForm;
