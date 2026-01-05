/**
 * ConnectedConversationPanel
 *
 * Redux-connected wrapper for ConversationPanel that integrates with:
 * - React Router loaders (messages, session)
 * - Redux actions (sendMessage)
 * - Session telemetry (message tracking)
 * - Message revalidation (refresh after sending)
 * - Conversation Intelligence (Sprint 3)
 *
 * Use this in StudioShellLayout instead of the standalone ConversationPanel.
 */
import {
  useCallback,
  useMemo,
  useState,
  useEffect,
  useRef,
  forwardRef,
} from "react";
import { useNavigate, useRouteLoaderData, useParams } from "react-router";
import {
  AlertTriangle,
  Target,
  Sparkles,
  Wifi,
  WifiOff,
  X,
  Lightbulb,
  AlertCircle,
  Brain,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  sendMessage,
  selectCurrentSession,
  createSession,
  clearMessages,
  saveAssistantMessage,
} from "../store/slices/sessionSlice";
import { useMessageRevalidation } from "../hooks/useMessageRevalidation";
import { useSessionAutoName } from "../hooks/useSessionAutoName";
import { useStreamingChat } from "../hooks/useStreamingChat";
import { useSessionSync } from "../hooks/useSessionSync";
import {
  useIntentDetection,
  useContextOptimization,
  useGoalTracking,
} from "../hooks/useConversationIntelligence";
import { useAIRealTimeUXSuggestions } from "../hooks/useAIRealTimeUXSuggestions";
import type { Suggestion } from "../hooks/useAIRealTimeSuggestions";
import { useArtifactExtraction } from "../hooks/useArtifactExtraction";
import { useInlineSuggestions } from "../hooks/useInlineSuggestions";
import { useDebounce } from "../hooks/useDebounce";
import { ConversationPanel } from "./ConversationPanel";
import type { SlashCommand } from "../components/Chat/ChatInputForm";
import type { ChatLoaderData } from "../router/loaders";
import { devLogger } from "../utils/devLogger";
import { cn } from "../utils/cn";

const logger = devLogger.withPrefix("[ConnectedConversationPanel]");

// =============================================================================
// Types
// =============================================================================

export interface ConnectedConversationPanelProps {
  /** Additional class name */
  className?: string;
  /** Enable AI conversation intelligence (Sprint 3) */
  enableAI?: boolean;
  /** Enable real-time AI UX suggestions via WebSocket */
  enableRealTimeSuggestions?: boolean;
  /** Enable inline ghost text suggestions (VSCode Copilot style) */
  enableInlineSuggestions?: boolean;
  /** User ID for AI features (format: "user:username") */
  userId?: string;
  /** Current persona for RBAC-aware AI responses */
  persona?: string;
  /** Show context optimization warning */
  showContextWarning?: boolean;
  /** Show goal tracking panel */
  showGoals?: boolean;
  /** Current token count (for context optimization) */
  currentTokens?: number;
  /** Maximum tokens (for context optimization) */
  maxTokens?: number;
}

// =============================================================================
// Slash Commands (can be extended via props or config)
// =============================================================================

const DEFAULT_SLASH_COMMANDS: SlashCommand[] = [
  {
    name: "new",
    description: "Start a new conversation",
    icon: "message",
  },
  {
    name: "clear",
    description: "Clear conversation history",
    icon: "trash",
  },
  {
    name: "help",
    description: "Show available commands",
    icon: "help",
  },
];

// =============================================================================
// Component
// =============================================================================

export const ConnectedConversationPanel = forwardRef<
  HTMLDivElement,
  ConnectedConversationPanelProps
>(function ConnectedConversationPanel(
  {
    className,
    enableAI = false,
    enableRealTimeSuggestions = false,
    enableInlineSuggestions = false,
    userId = "default-user",
    persona,
    showContextWarning = false,
    showGoals = false,
    currentTokens = 0,
    maxTokens = 128000,
  },
  ref,
) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { sessionId } = useParams();

  // Track input for intent detection
  const [inputQuery, setInputQuery] = useState("");
  // Debounce the input query to prevent excessive API calls on every keystroke
  // 500ms delay balances responsiveness with API efficiency
  const debouncedInputQuery = useDebounce(inputQuery, 500);

  // State for dismissing streaming errors and collapsing thinking content
  const [isStreamingErrorDismissed, setIsStreamingErrorDismissed] =
    useState(false);
  const [isThinkingContentCollapsed, setIsThinkingContentCollapsed] =
    useState(false);

  // =============================================================================
  // Streaming Chat (LLM Response Generation)
  // =============================================================================

  const {
    isStreaming,
    streamingContent,
    error: streamingError,
    thinkingContent,
    usage: streamingUsage, // Token usage from streaming response
    thinkingTokens,
    startStream,
  } = useStreamingChat();

  // Reset dismissed error state when a new error occurs
  useEffect(() => {
    if (streamingError) {
      setIsStreamingErrorDismissed(false);
    }
  }, [streamingError]);

  // Track if we need to save the streaming response when complete
  const streamingCompleteRef = useRef(false);
  const lastStreamedContentRef = useRef<string>("");
  const lastStreamedUsageRef = useRef<typeof streamingUsage>(null);
  const lastThinkingTokensRef = useRef<number | null>(null);

  // =============================================================================
  // Artifact Extraction (connects Chat to Canvas)
  // =============================================================================

  const { extractAndSaveArtifacts, resetExtraction } = useArtifactExtraction({
    sessionId: sessionId ?? "default-session",
    onArtifactsExtracted: (count) => {
      logger.debug("Extracted and saved artifacts from stream", { count });
    },
  });

  // Reset artifact extraction cache when session changes
  useEffect(() => {
    resetExtraction();
  }, [sessionId, resetExtraction]);

  // =============================================================================
  // Inline Suggestions (Ghost Text) - VSCode Copilot Style
  // =============================================================================

  const {
    suggestion: inlineSuggestion,
    isLoading: isSuggestionLoading,
    updateInput: updateInlineSuggestionInput,
    acceptSuggestion: acceptInlineSuggestion,
    dismissSuggestion: dismissInlineSuggestion,
  } = useInlineSuggestions({
    enabled: enableInlineSuggestions,
    sessionId: sessionId ?? "default-session",
    minLength: 3,
    debounceMs: 300,
    onError: (error) => {
      logger.debug("Inline suggestion error", { error: error.message });
    },
  });

  // =============================================================================
  // Real-time AI UX Suggestions (WebSocket)
  // =============================================================================

  const {
    isConnected: aiSuggestionsConnected,
    error: aiSuggestionsError,
    suggestions: aiSuggestions,
    isEnabled: aiSuggestionsEnabled,
    requestSuggestions,
    dismissSuggestion,
  } = useAIRealTimeUXSuggestions();

  // Request suggestions when typing (debounced effect)
  useEffect(() => {
    if (
      !enableRealTimeSuggestions ||
      !aiSuggestionsEnabled ||
      inputQuery.length < 3
    ) {
      return;
    }

    const timer = setTimeout(() => {
      requestSuggestions({
        page: "conversation",
        action: "typing",
        query: inputQuery,
        sessionId: sessionId ?? "default-session",
        userId,
        persona,
      });
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [
    enableRealTimeSuggestions,
    aiSuggestionsEnabled,
    inputQuery,
    sessionId,
    userId,
    persona,
    requestSuggestions,
  ]);

  // Filter suggestions by type
  const bannerSuggestions = useMemo(
    () => aiSuggestions.filter((s: Suggestion) => s.type === "banner"),
    [aiSuggestions],
  );

  const tooltipSuggestions = useMemo(
    () => aiSuggestions.filter((s: Suggestion) => s.type === "tooltip"),
    [aiSuggestions],
  );

  const spotlightSuggestions = useMemo(
    () => aiSuggestions.filter((s: Suggestion) => s.type === "spotlight"),
    [aiSuggestions],
  );

  // Hook for revalidating loader data after sending messages
  const { revalidateMessages } = useMessageRevalidation();

  // Get messages from the chat loader (try both session and index routes)
  const sessionLoaderData = useRouteLoaderData("chat-session") as
    | ChatLoaderData
    | undefined;
  const indexLoaderData = useRouteLoaderData("chat-index") as
    | ChatLoaderData
    | undefined;
  const loaderData = sessionLoaderData ?? indexLoaderData;

  // Sync loader data to Redux so sendMessage and other Redux actions work
  // This bridges React Router loaders with Redux session state
  useSessionSync(loaderData);

  // Get current session from Redux (contains optimistic updates)
  const currentSession = useAppSelector(selectCurrentSession);

  // Combine Redux messages with loader data and streaming content for display
  // CRITICAL: Redux currentSession.messages contains optimistic updates (user messages added immediately)
  // Loader data may be stale until revalidation completes
  // Use Redux as the primary source, with deduplication to handle overlap
  const messages = useMemo(() => {
    // Primary source: Redux state (has optimistic updates)
    const reduxMessages = currentSession?.messages ?? [];

    // Secondary source: Loader data (may have messages Redux doesn't know about yet)
    const loaderMessages = loaderData?.messages ?? [];

    // Merge with deduplication by ID (prefer Redux version if both have same ID)
    const messageMap = new Map<string, (typeof reduxMessages)[number]>();

    // Add loader messages first (will be overwritten by Redux if duplicate)
    for (const msg of loaderMessages) {
      messageMap.set(msg.id, msg);
    }

    // Add Redux messages (overwrites loader duplicates, adds optimistic updates)
    for (const msg of reduxMessages) {
      messageMap.set(msg.id, msg);
    }

    // Convert back to array and sort by timestamp
    const mergedMessages = Array.from(messageMap.values()).sort(
      (a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0),
    );

    // If streaming, append a temporary assistant message with the current content
    if (isStreaming && streamingContent) {
      return [
        ...mergedMessages,
        {
          id: "streaming-message",
          role: "assistant" as const,
          content: streamingContent,
          timestamp: Date.now(), // Use number timestamp for type compatibility
        },
      ];
    }

    return mergedMessages;
  }, [
    currentSession?.messages,
    loaderData?.messages,
    isStreaming,
    streamingContent,
  ]);

  // =============================================================================
  // Session Auto-Naming
  // =============================================================================

  // Automatically generate a session title when the first message is sent
  // This provides ChatGPT/Claude-like behavior where sessions are named
  // based on their content instead of staying "New Chat"
  useSessionAutoName({
    sessionId: sessionId ?? currentSession?.id,
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    currentName: currentSession?.name,
    enabled: true,
  });

  // =============================================================================
  // Streaming Completion Effects
  // =============================================================================

  // When streaming completes, save the assistant message to the session
  useEffect(() => {
    if (
      !isStreaming &&
      streamingCompleteRef.current &&
      lastStreamedContentRef.current
    ) {
      const assistantContent = lastStreamedContentRef.current;
      streamingCompleteRef.current = false;
      lastStreamedContentRef.current = "";

      // Add assistant message to Redux and persist to backend
      if (sessionId && assistantContent.trim()) {
        // Get captured usage data from refs
        const capturedUsage = lastStreamedUsageRef.current;
        const capturedThinkingTokens = lastThinkingTokensRef.current;

        // Clear refs after capturing
        lastStreamedUsageRef.current = null;
        lastThinkingTokensRef.current = null;

        dispatch(
          saveAssistantMessage({
            role: "assistant",
            content: assistantContent,
            // Include token usage for cost tracking in the UI
            usage: capturedUsage ?? undefined,
            thinkingTokens: capturedThinkingTokens ?? undefined,
          }),
        )
          .unwrap()
          .then(() => {
            // Revalidate to sync with loader after save completes
            revalidateMessages();

            // Extract artifacts from the completed stream and save to canvas
            // This connects chat streaming to the canvas panel
            extractAndSaveArtifacts(assistantContent);
          })
          .catch(() => {
            // Error already logged by thunk
          });
      }
    }
  }, [
    isStreaming,
    sessionId,
    dispatch,
    revalidateMessages,
    extractAndSaveArtifacts,
  ]);

  // Track streaming content and usage for saving when complete
  useEffect(() => {
    if (isStreaming && streamingContent) {
      streamingCompleteRef.current = true;
      lastStreamedContentRef.current = streamingContent;
      // Also capture usage data at stream completion
      lastStreamedUsageRef.current = streamingUsage;
      lastThinkingTokensRef.current = thinkingTokens;
    }
  }, [isStreaming, streamingContent, streamingUsage, thinkingTokens]);

  // Get session title for display (currentSession defined earlier for message merging)
  const sessionTitle = currentSession?.name;

  // =============================================================================
  // Conversation Intelligence Hooks (Sprint 3)
  // =============================================================================

  // Intent detection - classifies user intent as they type (debounced)
  const intentDetection = useIntentDetection({
    userId,
    sessionId: sessionId ?? "default-session",
    query: debouncedInputQuery,
    enabled: enableAI && debouncedInputQuery.length >= 3,
  });

  // Context optimization - suggests trimming when approaching token limit
  const contextOptimization = useContextOptimization({
    userId,
    sessionId: sessionId ?? "default-session",
    currentTokens,
    maxTokens,
    enabled: enableAI && showContextWarning,
  });

  // Goal tracking - tracks session goals across messages
  const goalTracking = useGoalTracking({
    userId,
    sessionId: sessionId ?? "default-session",
    enabled: enableAI && showGoals,
  });

  // Handle sending a message
  const handleSendMessage = useCallback(
    async (content: string) => {
      // Get effective session ID (from URL params or current session)
      const effectiveSessionId =
        sessionId ?? currentSession?.id ?? "default-session";

      try {
        // 1. Store the user message in the session
        await dispatch(sendMessage(content)).unwrap();

        // 2. Start streaming response from LLM
        // This calls POST /api/v1/chat/completions/stream
        startStream(effectiveSessionId, content);

        // 3. Trigger revalidation to sync loader data
        revalidateMessages();
      } catch {
        // Error is already logged by the thunk
      }

      // Clear input for next message
      setInputQuery("");
    },
    [dispatch, revalidateMessages, sessionId, currentSession?.id, startStream],
  );

  // Handle input change for intent detection and inline suggestions
  const handleInputChange = useCallback(
    (value: string) => {
      setInputQuery(value);
      // Update inline suggestions hook (debounced internally)
      if (enableInlineSuggestions) {
        updateInlineSuggestionInput(value);
      }
    },
    [enableInlineSuggestions, updateInlineSuggestionInput],
  );

  // Handle telemetry for messages
  const handleMessageSent = useCallback(
    (data: { messageLength: number; timestamp: number }) => {
      logger.debug("Message sent", data);
    },
    [],
  );

  // Handle telemetry for suggestions
  const handleSuggestionUsed = useCallback(
    (data: { suggestionId: string; suggestionType: string }) => {
      logger.debug("Suggestion used", data);
    },
    [],
  );

  // Handle slash commands
  const handleSlashCommand = useCallback(
    (command: SlashCommand) => {
      switch (command.name) {
        case "new":
          // Create a new session and navigate to it
          dispatch(createSession({ name: "New Chat" }))
            .unwrap()
            .then((session) => {
              navigate(`/studio/chat/${session.id}`);
              logger.debug("Created new session", { sessionId: session.id });
            })
            .catch((error) => {
              logger.error("Failed to create session", error);
            });
          break;
        case "clear":
          // Clear messages in current session
          dispatch(clearMessages())
            .unwrap()
            .then(() => {
              revalidateMessages();
              logger.debug("Cleared messages");
            })
            .catch((error) => {
              logger.error("Failed to clear messages", error);
            });
          break;
        case "help":
          // Navigate to help page
          navigate("/studio/help");
          break;
      }
    },
    [dispatch, navigate, revalidateMessages],
  );

  // Should show context warning when usage is high (>80%)
  const shouldShowContextWarning =
    enableAI &&
    showContextWarning &&
    contextOptimization.usagePercent !== null &&
    contextOptimization.usagePercent > 80;

  return (
    <div ref={ref} className={cn("flex flex-col h-full", className)}>
      {/* Streaming Error Display (Phase 3.4) */}
      {streamingError && !isStreamingErrorDismissed && (
        <div
          data-testid="streaming-error"
          className={cn(
            "flex items-center gap-2 px-4 py-2",
            "bg-red-50 dark:bg-red-900/20",
            "border-b border-red-200 dark:border-red-800",
            "text-sm text-red-700 dark:text-red-300",
          )}
        >
          <AlertCircle size={16} className="flex-shrink-0" />
          <div className="flex-1">
            <span className="font-medium">Streaming Error: </span>
            <span>{streamingError}</span>
          </div>
          <button
            data-testid="dismiss-streaming-error"
            onClick={() => setIsStreamingErrorDismissed(true)}
            className="p-1 hover:bg-red-100 dark:hover:bg-red-800/50 rounded"
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Thinking Content Display (Phase 3.4) */}
      {thinkingContent && isStreaming && (
        <div
          data-testid="thinking-content"
          className={cn(
            "flex flex-col gap-1 px-4 py-2",
            "bg-purple-50 dark:bg-purple-900/20",
            "border-b border-purple-200 dark:border-purple-800",
            "text-sm text-purple-700 dark:text-purple-300",
          )}
        >
          <div className="flex items-center gap-2">
            <Brain size={16} className="flex-shrink-0 animate-pulse" />
            <span className="font-medium">Thinking</span>
            {thinkingTokens && (
              <span
                data-testid="thinking-tokens-badge"
                className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-800/50 rounded text-xs"
              >
                {thinkingTokens.toLocaleString()}
              </span>
            )}
            <button
              data-testid="toggle-thinking-content"
              onClick={() =>
                setIsThinkingContentCollapsed(!isThinkingContentCollapsed)
              }
              className="ml-auto p-1 hover:bg-purple-100 dark:hover:bg-purple-800/50 rounded"
              aria-label={
                isThinkingContentCollapsed
                  ? "Expand thinking content"
                  : "Collapse thinking content"
              }
            >
              {isThinkingContentCollapsed ? (
                <ChevronDown size={14} />
              ) : (
                <ChevronUp size={14} />
              )}
            </button>
          </div>
          {!isThinkingContentCollapsed && (
            <div className="pl-6 text-xs text-purple-600 dark:text-purple-400 whitespace-pre-wrap max-h-24 overflow-y-auto">
              {thinkingContent}
            </div>
          )}
        </div>
      )}

      {/* Goal Tracker (Sprint 3) */}
      {enableAI && showGoals && goalTracking.primaryGoal && (
        <div
          data-testid="goal-tracker"
          className={cn(
            "flex items-center gap-2 px-4 py-2",
            "bg-blue-50 dark:bg-blue-900/20",
            "border-b border-blue-200 dark:border-blue-800",
            "text-sm text-blue-700 dark:text-blue-300",
          )}
        >
          <Target size={16} className="flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-medium">Goal: </span>
            <span className="truncate">{goalTracking.primaryGoal}</span>
            {goalTracking.progressPercent !== null && (
              <span className="ml-2 text-blue-600 dark:text-blue-400">
                ({goalTracking.progressPercent}% complete)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Context Warning (Sprint 3) */}
      {shouldShowContextWarning && (
        <div
          data-testid="context-warning"
          className={cn(
            "flex items-center gap-2 px-4 py-2",
            "bg-amber-50 dark:bg-amber-900/20",
            "border-b border-amber-200 dark:border-amber-800",
            "text-sm text-amber-700 dark:text-amber-300",
          )}
        >
          <AlertTriangle size={16} className="flex-shrink-0" />
          <div className="flex-1">
            <span className="font-medium">Context Usage: </span>
            <span>{contextOptimization.usagePercent?.toFixed(0)}%</span>
            {contextOptimization.recommendedAction && (
              <span className="ml-2 text-amber-600 dark:text-amber-400">
                - {contextOptimization.recommendedAction.replace(/_/g, " ")}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Intent Indicator (Sprint 3) */}
      {enableAI && intentDetection.intent && inputQuery.length >= 3 && (
        <div
          data-testid="intent-indicator"
          className={cn(
            "flex items-center gap-2 px-4 py-1.5",
            "bg-purple-50 dark:bg-purple-900/20",
            "border-b border-purple-200 dark:border-purple-800",
            "text-xs text-purple-700 dark:text-purple-300",
          )}
        >
          <Sparkles size={12} className="flex-shrink-0" />
          <span>
            Detected intent:{" "}
            <span className="font-medium">
              {intentDetection.intent.replace(/_/g, " ")}
            </span>
            {intentDetection.confidence !== null && (
              <span className="ml-1 text-purple-500 dark:text-purple-400">
                ({(intentDetection.confidence * 100).toFixed(0)}%)
              </span>
            )}
          </span>
        </div>
      )}

      {/* AI Suggestions Status Indicator (Real-time WebSocket) */}
      {enableRealTimeSuggestions && (
        <div
          data-testid="ai-suggestions-status"
          data-connected={aiSuggestionsConnected ? "true" : "false"}
          data-error={aiSuggestionsError ? "true" : "false"}
          className={cn(
            "flex items-center gap-2 px-4 py-1",
            "border-b",
            aiSuggestionsError
              ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
              : aiSuggestionsConnected
                ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                : "bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700",
          )}
        >
          {aiSuggestionsConnected ? (
            <Wifi size={12} className="text-green-500" />
          ) : (
            <WifiOff size={12} className="text-gray-400" />
          )}
          <span
            className={cn(
              "text-xs",
              aiSuggestionsError
                ? "text-red-600 dark:text-red-400"
                : aiSuggestionsConnected
                  ? "text-green-600 dark:text-green-400"
                  : "text-gray-500 dark:text-gray-400",
            )}
          >
            {aiSuggestionsError
              ? "AI suggestions offline"
              : aiSuggestionsConnected
                ? "AI suggestions active"
                : "AI suggestions connecting..."}
          </span>
        </div>
      )}

      {/* Banner Suggestions (Real-time AI UX) */}
      {enableRealTimeSuggestions &&
        bannerSuggestions.map((suggestion: Suggestion) => (
          <div
            key={suggestion.id}
            data-testid="ai-suggestion-banner"
            className={cn(
              "flex items-center gap-2 px-4 py-2",
              suggestion.priority === "high"
                ? "bg-orange-50 dark:bg-orange-900/20 border-b border-orange-200 dark:border-orange-800"
                : "bg-cyan-50 dark:bg-cyan-900/20 border-b border-cyan-200 dark:border-cyan-800",
            )}
          >
            <Lightbulb
              size={16}
              className={cn(
                "flex-shrink-0",
                suggestion.priority === "high"
                  ? "text-orange-500"
                  : "text-cyan-500",
              )}
            />
            <div className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              {suggestion.message}
            </div>
            <button
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              aria-label="Dismiss suggestion"
            >
              <X size={14} className="text-gray-400" />
            </button>
          </div>
        ))}

      {/* Spotlight Suggestions (Real-time AI UX - High Priority) */}
      {enableRealTimeSuggestions &&
        spotlightSuggestions.map((suggestion: Suggestion) => (
          <div
            key={suggestion.id}
            data-testid="ai-suggestion-spotlight"
            className={cn(
              "flex items-center gap-3 px-4 py-3",
              "bg-gradient-to-r from-purple-50 to-pink-50",
              "dark:from-purple-900/20 dark:to-pink-900/20",
              "border-b border-purple-200 dark:border-purple-800",
            )}
          >
            <Sparkles
              size={20}
              className="flex-shrink-0 text-purple-500 animate-pulse"
            />
            <div className="flex-1 text-sm font-medium text-purple-700 dark:text-purple-300">
              {suggestion.message}
            </div>
            <button
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              className="p-1 hover:bg-purple-200 dark:hover:bg-purple-700 rounded"
              aria-label="Dismiss suggestion"
            >
              <X size={14} className="text-purple-400" />
            </button>
          </div>
        ))}

      {/* Tooltip Suggestions (Real-time AI UX) */}
      {enableRealTimeSuggestions &&
        tooltipSuggestions.map((suggestion: Suggestion) => (
          <div
            key={suggestion.id}
            data-testid="ai-suggestion-tooltip"
            className={cn(
              "flex items-center gap-2 px-4 py-1.5",
              "bg-gray-50 dark:bg-gray-800/50",
              "border-b border-gray-200 dark:border-gray-700",
            )}
          >
            <Lightbulb size={12} className="flex-shrink-0 text-gray-400" />
            <div className="flex-1 text-xs text-gray-600 dark:text-gray-400">
              {suggestion.targetElement && (
                <span className="font-mono text-xs text-gray-400 mr-2">
                  [{suggestion.targetElement}]
                </span>
              )}
              {suggestion.message}
            </div>
            <button
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              aria-label="Dismiss suggestion"
            >
              <X size={12} className="text-gray-400" />
            </button>
          </div>
        ))}

      <ConversationPanel
        data-testid="connected-conversation-panel"
        messages={messages}
        onSendMessage={handleSendMessage}
        sessionId={sessionId}
        sessionTitle={sessionTitle}
        slashCommands={DEFAULT_SLASH_COMMANDS}
        onSlashCommand={handleSlashCommand}
        onMessageSent={handleMessageSent}
        onSuggestionUsed={handleSuggestionUsed}
        onInputChange={handleInputChange}
        isStreaming={isStreaming}
        autoFocus
        className="flex-1"
        // Inline AI Suggestions (VSCode Copilot style)
        enableInlineSuggestions={enableInlineSuggestions}
        inlineSuggestion={inlineSuggestion}
        isSuggestionLoading={isSuggestionLoading}
        onAcceptSuggestion={acceptInlineSuggestion}
        onDismissSuggestion={dismissInlineSuggestion}
      />
    </div>
  );
});

// Display name for DevTools
ConnectedConversationPanel.displayName = "ConnectedConversationPanel";
