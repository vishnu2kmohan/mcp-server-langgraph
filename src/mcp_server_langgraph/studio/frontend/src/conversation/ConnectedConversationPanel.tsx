/**
 * ConnectedConversationPanel
 *
 * Redux-connected wrapper for ConversationPanel that integrates with:
 * - React Router loaders (messages, session)
 * - Redux actions (addUserMessage, setPendingMutation)
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
  X,
  Lightbulb,
  AlertCircle,
  Brain,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  addAuthRequirement,
  dismissAuthRequirement,
  selectPendingAuthRequirements,
} from "../store/slices/chatConnectionSlice";
import { InlineConnectionCard } from "../components/Chat/InlineConnectionCard";
import {
  selectCurrentSession,
  selectMessages,
  createSession,
  clearMessages,
  addUserMessage,
  updateMessage,
  sendMessage,
  setPendingMutation,
} from "../store/slices/sessionSlice";
import {
  selectExecutionMode,
  selectCurrentPlan,
  selectRoutingDecision,
  selectShowPlanApproval,
  setPlanStatus,
  clearPlan,
} from "../store/slices/executionModeSlice";
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
import {
  useSubmitMessageRatingMutation,
  useSubmitHallucinationReportMutation,
} from "../api";
import { ConversationPanel } from "./ConversationPanel";
import type { SlashCommand, ModelOption } from "../components/Chat/ChatInput";
import type { ReasoningEffortLevel } from "../components/Chat/ReasoningEffortSelector";
import type { KBFocusMode, ToolPreference } from "../hooks/useStreamingChat";
import type { ChatLoaderData } from "../router/loaders";
import { devLogger } from "../utils/devLogger";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

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

  // ===========================================================================
  // Model Selection Props (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

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

  // ===========================================================================
  // Reasoning Effort Props (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

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

  // ===========================================================================
  // UnifiedMessageList Props (ADR-0104)
  // ===========================================================================

  /** Show user/assistant avatars */
  showAvatars?: boolean;
  /** Show token usage per message */
  showTokenUsage?: boolean;
  /** Show agent execution traces per message */
  showAgentTraces?: boolean;
  /** Show rating controls for assistant messages */
  showRating?: boolean;
  /** Enable hallucination reporting */
  enableHallucinationReporting?: boolean;
  /** Enable AI-powered trace intelligence */
  enableTraceAI?: boolean;
  /** Model provider for cost calculation */
  modelProvider?: "openai" | "anthropic" | "google" | "azure";
  /** Show cost estimation */
  showCost?: boolean;
  /** User initials for avatar */
  userInitials?: string;
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
    // Model selection (Sprint 1)
    showModelSelector = false,
    selectedModel,
    availableModels = [],
    onModelChange,
    isModelsLoading = false,
    recentModels = [],
    enableModelSearch = false,
    // Reasoning effort (Sprint 1)
    modelSupportsThinking = false,
    reasoningEffort = "medium",
    onReasoningEffortChange,
    enableThinking = false,
    onEnableThinkingChange,
    // UnifiedMessageList (ADR-0104)
    showAvatars = false,
    showTokenUsage = false,
    showAgentTraces = false,
    showRating = false,
    enableHallucinationReporting = false,
    enableTraceAI = false,
    modelProvider = "openai",
    showCost = false,
    userInitials,
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

  // KB focus mode state (lifted from ConnectedChatInputForm for API integration)
  const [kbFocusMode, setKbFocusMode] = useState<KBFocusMode>("all");

  // v7: Tool preference state for native vs builtin execution
  const [toolPreference, setToolPreference] = useState<ToolPreference>("auto");

  // =============================================================================
  // Message Ratings & Actions State (ADR-0104 UnifiedMessageList)
  // =============================================================================

  const [messageRatings, setMessageRatings] = useState<
    Record<string, "up" | "down" | null>
  >({});
  const [isRegenerating, setIsRegenerating] = useState(false);

  // RTK Query mutations for feedback APIs
  const [submitRating, { isLoading: isRatingSubmitting }] =
    useSubmitMessageRatingMutation();
  const [submitHallucinationReport] = useSubmitHallucinationReportMutation();

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
    authRequired, // Auth required event from SSE stream (ADR-0102)
    sources: streamingSources, // Source citations from web search (ADR-0099)
  } = useStreamingChat();

  // Reset dismissed error state when a new error occurs
  useEffect(() => {
    if (streamingError) {
      setIsStreamingErrorDismissed(false);
    }
  }, [streamingError]);

  // Finding 2: Mark optimistic message as failed when async stream errors occur.
  // startStream is fire-and-forget, so errors from the fetch/SSE stream are
  // surfaced asynchronously via the `streamingError` state rather than the
  // catch block in handleSendMessage. Without this, the optimistic message
  // would remain in a "sending" state indefinitely.
  useEffect(() => {
    if (streamingError && lastSentMessageIdRef.current) {
      dispatch(
        updateMessage({
          messageId: lastSentMessageIdRef.current,
          updates: { status: "failed" as const },
        }),
      );
      dispatch(setPendingMutation(false));
      lastSentMessageIdRef.current = "";
    }
  }, [streamingError, dispatch]);

  // Dispatch auth_required events to Redux (ADR-0102)
  // This allows InlineConnectionCard to display and handle authentication
  useEffect(() => {
    if (authRequired) {
      dispatch(addAuthRequirement(authRequired));
    }
  }, [authRequired, dispatch]);

  // Track if we need to save the streaming response when complete
  const streamingCompleteRef = useRef(false);
  const lastStreamedContentRef = useRef<string>("");
  const lastStreamedUsageRef = useRef<typeof streamingUsage>(null);
  const lastThinkingTokensRef = useRef<number | null>(null);
  const lastStreamedSourcesRef = useRef<typeof streamingSources>([]);

  // Finding 2: Track the last sent messageId for async error handling
  const lastSentMessageIdRef = useRef<string>("");

  // Fix 1: Seamless handoff state for UI flicker prevention
  // The backend streaming endpoint already persists the message, so we DON'T call saveAssistantMessage.
  // These states enable seamless handoff from streaming content to persisted message.
  const [lastStreamedContent, setLastStreamedContent] = useState<string | null>(
    null,
  );
  const [revalidationInProgress, setRevalidationInProgress] = useState(false);
  const [revalidationFailed, setRevalidationFailed] = useState(false);

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
    isConnected: _aiSuggestionsConnected,
    error: _aiSuggestionsError,
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

  // Retry handler for failed revalidation (Fix 1: graceful degradation)
  // Note: This handler can be passed to MessageBubble for retry UI, or exposed via context
  const _retryRevalidation = useCallback(() => {
    if (!lastStreamedContent) return;

    setRevalidationInProgress(true);
    setRevalidationFailed(false);

    Promise.resolve()
      .then(() => revalidateMessages())
      .then(() => new Promise((resolve) => setTimeout(resolve, 50)))
      .then(() => {
        setLastStreamedContent(null);
      })
      .catch((error: unknown) => {
        console.error("Revalidation retry failed:", error);
        setRevalidationFailed(true);
      })
      .finally(() => {
        setRevalidationInProgress(false);
      });
  }, [lastStreamedContent, revalidateMessages]);

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

  // RC4 Fix: Get current messages for defense-in-depth history fallback
  const currentMessages = useAppSelector(selectMessages);

  // S4: Use ref for currentMessages to avoid re-creating handleSendMessage on every message change
  const currentMessagesRef = useRef(currentMessages);
  currentMessagesRef.current = currentMessages;

  // Get execution mode from Redux (plan/default/auto_accept/bypass)
  const executionMode = useAppSelector(selectExecutionMode);

  // Get current plan and approval status from Redux (Issue 7: Plan Rendering)
  const currentPlan = useAppSelector(selectCurrentPlan);
  const routingDecision = useAppSelector(selectRoutingDecision);
  const showPlanApproval = useAppSelector(selectShowPlanApproval);

  // Get pending auth requirements for InlineConnectionCard (ADR-0102)
  const pendingAuthRequirements = useAppSelector(selectPendingAuthRequirements);

  // Handle dismissing an auth requirement
  const handleDismissAuthRequirement = useCallback(
    (id: string) => {
      dispatch(dismissAuthRequirement(id));
    },
    [dispatch],
  );

  // Plan approval handlers (Issue 7: Plan Rendering)
  const handleApprovePlan = useCallback(
    (_planId: string) => {
      dispatch(setPlanStatus("approved"));
      // Clear the plan after a short delay to allow UI feedback
      setTimeout(() => dispatch(clearPlan()), 500);
    },
    [dispatch],
  );

  const handleRejectPlan = useCallback(
    (_planId: string) => {
      dispatch(setPlanStatus("rejected"));
      // Clear the plan after a short delay to allow UI feedback
      setTimeout(() => dispatch(clearPlan()), 500);
    },
    [dispatch],
  );

  // Combine Redux messages with loader data for display.
  // CRITICAL: Redux currentSession.messages contains optimistic updates (user messages added immediately)
  // Loader data may be stale until revalidation completes
  // Use Redux as the primary source, with deduplication to handle overlap
  const baseMessages = useMemo(() => {
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
    return Array.from(messageMap.values()).sort(
      (a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0),
    );
  }, [currentSession?.messages, loaderData?.messages]);

  // Append the streaming message separately so we don't re-merge/re-sort on every chunk.
  // Fix 1: Seamless handoff - show lastStreamedContent during revalidation to prevent flicker.
  const messages = useMemo(() => {
    // Check if we have a persisted assistant message that matches our streamed content
    // This prevents the brief double-render gap
    const lastPersistedAssistantMessage = baseMessages
      .filter((m) => m.role === "assistant")
      .pop();
    const hasMatchingPersistedMessage =
      lastPersistedAssistantMessage &&
      lastStreamedContent &&
      lastPersistedAssistantMessage.content?.startsWith(
        lastStreamedContent.slice(0, 100),
      );

    // Show streaming placeholder if:
    // - We're actively streaming, OR
    // - We have lastStreamedContent AND no matching persisted message yet
    const contentToShow = streamingContent || lastStreamedContent;
    const shouldShowPlaceholder =
      (isStreaming && streamingContent) ||
      (lastStreamedContent && !hasMatchingPersistedMessage);

    if (shouldShowPlaceholder && contentToShow) {
      return [
        ...baseMessages,
        {
          id: "streaming-message",
          role: "assistant" as const,
          content: contentToShow,
          timestamp: Date.now(),
          isStreaming: isStreaming, // Only show streaming indicator when actually streaming
          isRevalidating: revalidationInProgress && !isStreaming, // Show saving indicator
          revalidationFailed: revalidationFailed, // Show retry option on failure
          sources: streamingSources, // Source citations from web search
        },
      ];
    }
    return baseMessages;
  }, [
    baseMessages,
    isStreaming,
    streamingContent,
    streamingSources,
    lastStreamedContent,
    revalidationInProgress,
    revalidationFailed,
  ]);

  // =============================================================================
  // Session Auto-Naming
  // =============================================================================

  // Automatically generate a session title when the first message is sent
  // This provides ChatGPT/Claude-like behavior where sessions are named
  // based on their content instead of staying "New Chat"
  useSessionAutoName({
    sessionId: sessionId ?? currentSession?.id,
    messages: baseMessages.map((m) => ({ role: m.role, content: m.content })),
    currentName: currentSession?.name,
    enabled: true,
  });

  // =============================================================================
  // Streaming Completion Effects
  // =============================================================================

  // Finding 4 fix: Clear pendingMutation when streaming ends, not synchronously
  // after startStream (which is fire-and-forget). This prevents stale loader
  // data from overwriting optimistic updates while the stream is still active.
  const prevIsStreamingRef = useRef(false);
  useEffect(() => {
    if (prevIsStreamingRef.current && !isStreaming) {
      // Streaming just ended (transition from true -> false)
      dispatch(setPendingMutation(false));
    }
    prevIsStreamingRef.current = isStreaming;
  }, [isStreaming, dispatch]);

  // When streaming completes, revalidate to fetch the persisted message
  // Fix 1: DO NOT call saveAssistantMessage - backend already persists during streaming.
  // This eliminates the duplicate message issue.
  useEffect(() => {
    if (
      !isStreaming &&
      streamingCompleteRef.current &&
      lastStreamedContentRef.current
    ) {
      const assistantContent = lastStreamedContentRef.current;
      streamingCompleteRef.current = false;
      lastStreamedContentRef.current = "";
      lastSentMessageIdRef.current = ""; // Finding 2: Clear on successful completion

      // Only revalidate if we have content (backend already persisted)
      if (sessionId && assistantContent.trim()) {
        // Clear refs after capturing
        lastStreamedUsageRef.current = null;
        lastThinkingTokensRef.current = null;
        lastStreamedSourcesRef.current = [];

        // Fix 1: Seamless Handoff Pattern
        // 1. Capture streamed content BEFORE any async operations
        setLastStreamedContent(assistantContent);
        setRevalidationInProgress(true);
        setRevalidationFailed(false);

        // 2. Revalidate to fetch persisted message from backend
        // Note: We use Promise.resolve().then() instead of async/await
        // to avoid needing to mark this effect as async
        Promise.resolve()
          .then(() => revalidateMessages())
          .then(() => {
            // 3. SUCCESS: Clear placeholder after messages are confirmed in store
            // Small delay ensures React has re-rendered with new messages
            return new Promise((resolve) => setTimeout(resolve, 50));
          })
          .then(() => {
            // Clear the placeholder - persisted message is now in store
            setLastStreamedContent(null);
          })
          .catch((error: unknown) => {
            // 4. FAILURE: Keep lastStreamedContent visible, show retry option
            console.error("Revalidation failed:", error);
            setRevalidationFailed(true);
            // Do NOT clear lastStreamedContent - keep message visible
          })
          .finally(() => {
            setRevalidationInProgress(false);
          });

        // 5. Extract artifacts (independent of message display)
        extractAndSaveArtifacts(assistantContent);
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
      // Also capture usage and sources data at stream completion
      lastStreamedUsageRef.current = streamingUsage;
      lastThinkingTokensRef.current = thinkingTokens;
      lastStreamedSourcesRef.current = streamingSources;
    }
  }, [
    isStreaming,
    streamingContent,
    streamingUsage,
    thinkingTokens,
    streamingSources,
  ]);

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
      let effectiveSessionId = sessionId ?? currentSession?.id;
      // Hoist messageId so it's accessible in the catch block for status updates
      let messageId = "";

      try {
        // Auto-create session on first message if no session exists
        if (!effectiveSessionId) {
          logger.debug(
            "No session found, creating new session for first message",
          );
          const newSession = await dispatch(
            createSession({ name: "New Chat" }),
          ).unwrap();
          effectiveSessionId = newSession.id;
          // Navigate to the new session URL
          navigate(`/studio/chat/${newSession.id}`, { replace: true });
        }

        // 1. Optimistic update: add user message to Redux immediately
        // RC1 Fix: Do NOT call sendMessage thunk (which POSTs to /api/v1/sessions/{id}/messages)
        // The streaming endpoint already persists the user message with dedup logic.
        // Dual persistence caused a race condition where _load_and_merge_history
        // could read stale storage state.
        messageId = `msg-${crypto.randomUUID()}`;
        lastSentMessageIdRef.current = messageId; // Finding 2: Track for async error handling
        dispatch(setPendingMutation(true));
        dispatch(
          addUserMessage({
            id: messageId,
            role: "user",
            content,
            timestamp: Date.now(),
          }),
        );

        // 2. Start streaming response from LLM
        // This calls POST /api/v1/chat/completions/stream
        // Pass model, reasoning options, KB focus mode, execution mode, and tool preference
        // Note: startStream is fire-and-forget (returns void). Stream errors are
        // handled internally by useStreamingChat via state updates (error field).
        // The streaming endpoint handles user message persistence with dedup logic,
        // so no fallback persistence is needed here.
        const history = currentMessagesRef.current.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
        }));

        startStream(effectiveSessionId, content, {
          model: selectedModel,
          reasoningEffort: modelSupportsThinking ? reasoningEffort : undefined,
          enableThinking: modelSupportsThinking ? enableThinking : undefined,
          kbFocus: kbFocusMode,
          executionMode,
          toolPreference, // v7: Native vs builtin tool preference
          history, // RC4: Bounded client history fallback
          messageId, // Finding 1: Pass optimistic messageId for ID-based dedup
        });

        // Note: setPendingMutation(false) is NOT called here.
        // Finding 4 fix: startStream is fire-and-forget, so clearing the flag
        // synchronously would defeat its purpose. Instead, a useEffect below
        // watches isStreaming and clears pendingMutation when streaming ends.

        // 3. Trigger revalidation to sync loader data
        revalidateMessages();
      } catch (error) {
        // Finding 3 fix: If startStream threw synchronously (before the
        // streaming endpoint could persist the message), use sendMessage
        // thunk as a fallback to ensure the message is not lost.
        try {
          await dispatch(sendMessage(content)).unwrap();
        } catch {
          // Both paths failed — mark the optimistic message as failed
          dispatch(
            updateMessage({
              messageId,
              updates: { status: "failed" as const },
            }),
          );
        }
        dispatch(setPendingMutation(false));
        logger.error("Failed to send message", { error });
      }

      // Clear input for next message
      setInputQuery("");
    },
    [
      dispatch,
      navigate,
      revalidateMessages,
      sessionId,
      currentSession?.id,
      startStream,
      kbFocusMode,
      selectedModel,
      reasoningEffort,
      enableThinking,
      modelSupportsThinking,
      executionMode,
      toolPreference, // v7
    ],
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

  // =============================================================================
  // Message Rating & Action Handlers (ADR-0104 UnifiedMessageList)
  // =============================================================================

  // Handle message rating (thumbs up/down)
  const handleRateMessage = useCallback(
    async (messageId: string, rating: "up" | "down" | null) => {
      if (!sessionId || !rating) return;

      // Optimistic update
      setMessageRatings((prev) => ({ ...prev, [messageId]: rating }));

      try {
        await submitRating({
          session_id: sessionId,
          message_id: messageId,
          rating,
        }).unwrap();
        logger.debug("Message rated", { messageId, rating });
      } catch (error) {
        // Revert on error
        setMessageRatings((prev) => ({ ...prev, [messageId]: null }));
        logger.error("Failed to submit rating", error);
      }
    },
    [sessionId, submitRating],
  );

  // Handle rating feedback (text feedback after negative rating)
  const handleRatingFeedback = useCallback(
    async (messageId: string, feedback: string) => {
      if (!sessionId) return;

      try {
        // Re-submit rating with feedback text
        await submitRating({
          session_id: sessionId,
          message_id: messageId,
          rating: messageRatings[messageId] ?? "down",
          feedback,
        }).unwrap();
        logger.debug("Rating feedback submitted", { messageId, feedback });
      } catch (error) {
        logger.error("Failed to submit rating feedback", error);
      }
    },
    [sessionId, submitRating, messageRatings],
  );

  // Handle message edit
  const handleEditMessage = useCallback((messageId: string) => {
    // TODO: Implement message editing when supported
    logger.debug("Edit message requested", { messageId });
  }, []);

  // Handle message deletion
  const handleDeleteMessage = useCallback((messageId: string) => {
    // TODO: Implement message deletion when supported
    logger.debug("Delete message requested", { messageId });
  }, []);

  // Handle message regeneration
  const handleRegenerateMessage = useCallback((messageId: string) => {
    setIsRegenerating(true);
    // TODO: Implement message regeneration when supported
    logger.debug("Regenerate message requested", { messageId });
    setIsRegenerating(false);
  }, []);

  // Handle hallucination report
  const handleReportHallucination = useCallback(
    async (report: {
      messageId: string;
      category: string;
      details: string;
      timestamp: number;
    }) => {
      if (!sessionId) return;

      try {
        await submitHallucinationReport({
          message_id: report.messageId,
          session_id: sessionId,
          category: report.category as
            | "factual_error"
            | "outdated_info"
            | "made_up_source"
            | "other",
          description: report.details,
        }).unwrap();
        logger.debug("Hallucination reported", report);
      } catch (error) {
        logger.error("Failed to submit hallucination report", error);
      }
    },
    [sessionId, submitHallucinationReport],
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
            "bg-error-1 dark:bg-error-a3",
            "border-b border-error-4 dark:border-error-11",
            "text-sm text-error-11 dark:text-error-9",
          )}
        >
          <AlertCircle size={16} className="flex-shrink-0" />
          <div className="flex-1">
            <span className="font-medium">Streaming Error: </span>
            <span>{streamingError}</span>
          </div>
          <Button
            variant="danger"
            className="p-1 hover:bg-error-3 dark:hover:bg-error-a6 rounded"
            data-testid="dismiss-streaming-error"
            onClick={() => setIsStreamingErrorDismissed(true)}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </Button>
        </div>
      )}
      {/* Thinking Content Display (Phase 3.4) */}
      {thinkingContent && isStreaming && (
        <div
          data-testid="thinking-content"
          className={cn(
            "flex flex-col gap-1 px-4 py-2",
            "bg-insight-1 dark:bg-insight-a3",
            "border-b border-insight-4 dark:border-insight-11",
            "text-sm text-insight-11 dark:text-insight-5",
          )}
        >
          <div className="flex items-center gap-2">
            <Brain size={16} className="flex-shrink-0 animate-pulse" />
            <span className="font-medium">Thinking</span>
            {thinkingTokens && (
              <span
                data-testid="thinking-tokens-badge"
                className="px-1.5 py-0.5 bg-insight-2 dark:bg-insight-a6 rounded text-xs"
              >
                {thinkingTokens.toLocaleString()}
              </span>
            )}
            <Button
              variant="primary"
              className="ml-auto p-1 hover:bg-insight-2 dark:hover:bg-insight-a6 rounded"
              data-testid="toggle-thinking-content"
              onClick={() =>
                setIsThinkingContentCollapsed(!isThinkingContentCollapsed)
              }
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
            </Button>
          </div>
          {!isThinkingContentCollapsed && (
            <div className="pl-6 text-xs text-insight-10 dark:text-insight-9 whitespace-pre-wrap max-h-24 overflow-y-auto">
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
            "bg-primary-1 dark:bg-primary-a3",
            "border-b border-primary-4 dark:border-primary-11",
            "text-sm text-primary-11 dark:text-primary-5",
          )}
        >
          <Target size={16} className="flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-medium">Goal: </span>
            <span className="truncate">{goalTracking.primaryGoal}</span>
            {goalTracking.progressPercent !== null && (
              <span className="ml-2 text-primary-10 dark:text-primary-7">
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
            "bg-warning-3 bg-warning-3",
            "border-b border-warning-6 dark:border-warning-11",
            "text-sm text-warning-10 dark:text-warning-6",
          )}
        >
          <AlertTriangle size={16} className="flex-shrink-0" />
          <div className="flex-1">
            <span className="font-medium">Context Usage: </span>
            <span>{contextOptimization.usagePercent?.toFixed(0)}%</span>
            {contextOptimization.recommendedAction && (
              <span className="ml-2 text-warning-9 dark:text-warning-9">
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
            "bg-insight-1 dark:bg-insight-a3",
            "border-b border-insight-4 dark:border-insight-11",
            "text-xs text-insight-11 dark:text-insight-5",
          )}
        >
          <Sparkles size={12} className="flex-shrink-0" />
          <span>
            Detected intent:{" "}
            <span className="font-medium">
              {intentDetection.intent.replace(/_/g, " ")}
            </span>
            {intentDetection.confidence !== null && (
              <span className="ml-1 text-insight-9 dark:text-insight-9">
                ({(intentDetection.confidence * 100).toFixed(0)}%)
              </span>
            )}
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
                ? "bg-grafana-1 dark:bg-grafana-12/20 border-b border-grafana-3 dark:border-grafana-11"
                : "bg-info-1 dark:bg-info-a3 border-b border-info-4 dark:border-info-11",
            )}
          >
            <Lightbulb
              size={16}
              className={cn(
                "flex-shrink-0",
                suggestion.priority === "high"
                  ? "text-grafana-9"
                  : "text-info-9",
              )}
            />
            <div className="flex-1 text-sm text-neutral-11">
              {suggestion.message}
            </div>
            <Button
              variant="secondary"
              className="p-1 hover:bg-neutral-3 rounded"
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              aria-label="Dismiss suggestion"
            >
              <X size={14} className="text-neutral-9" />
            </Button>
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
              "bg-gradient-to-r from-insight-50 to-error-2",
              "dark:from-insight-900/20 dark:to-error-3",
              "border-b border-insight-4 dark:border-insight-11",
            )}
          >
            <Sparkles
              size={20}
              className="flex-shrink-0 text-insight-9 animate-pulse"
            />
            <div className="flex-1 text-sm font-medium text-insight-11 dark:text-insight-5">
              {suggestion.message}
            </div>
            <Button
              variant="secondary"
              className="p-1 hover:bg-insight-4 dark:hover:bg-insight-11 rounded"
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              aria-label="Dismiss suggestion"
            >
              <X size={14} className="text-insight-9" />
            </Button>
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
              "bg-neutral-1",
              "border-b border-neutral-5",
            )}
          >
            <Lightbulb size={12} className="flex-shrink-0 text-neutral-9" />
            <div className="flex-1 text-xs text-neutral-11">
              {suggestion.targetElement && (
                <span className="font-mono text-xs text-neutral-9 mr-2">
                  [{suggestion.targetElement}]
                </span>
              )}
              {suggestion.message}
            </div>
            <Button
              variant="secondary"
              className="p-0.5 hover:bg-neutral-3 rounded"
              data-testid="dismiss-suggestion-button"
              onClick={() => dismissSuggestion(suggestion.id)}
              aria-label="Dismiss suggestion"
            >
              <X size={12} className="text-neutral-9" />
            </Button>
          </div>
        ))}
      {/* Inline Connection Cards (ADR-0102) */}
      {pendingAuthRequirements.map((authReq) => (
        <InlineConnectionCard
          key={authReq.id}
          data-testid="inline-connection-card"
          templateId={authReq.templateId}
          toolName={authReq.toolName}
          message={authReq.message}
          connectionId={authReq.connectionId}
          retryMessageId={authReq.retryMessageId}
          onDismiss={() => handleDismissAuthRequirement(authReq.id)}
        />
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
        // KB Focus mode (controlled - lifted from ConnectedChatInputForm)
        kbFocusValue={kbFocusMode}
        onKBFocusChange={setKbFocusMode}
        // v7: Tool preference for native vs builtin execution
        toolPreference={toolPreference}
        onToolPreferenceChange={setToolPreference}
        // Model selection (Sprint 1)
        showModelSelector={showModelSelector}
        selectedModel={selectedModel}
        availableModels={availableModels}
        onModelChange={onModelChange}
        isModelsLoading={isModelsLoading}
        recentModels={recentModels}
        enableModelSearch={enableModelSearch}
        // Reasoning effort (Sprint 1)
        modelSupportsThinking={modelSupportsThinking}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={onReasoningEffortChange}
        enableThinking={enableThinking}
        onEnableThinkingChange={onEnableThinkingChange}
        // UnifiedMessageList props (ADR-0104)
        showAvatars={showAvatars}
        showTokenUsage={showTokenUsage}
        showAgentTraces={showAgentTraces}
        showRating={showRating}
        enableHallucinationReporting={enableHallucinationReporting}
        enableTraceAI={enableTraceAI}
        modelProvider={modelProvider}
        showCost={showCost}
        userInitials={userInitials}
        userId={userId}
        messageRatings={messageRatings}
        onRateMessage={handleRateMessage}
        onRatingFeedback={handleRatingFeedback}
        isRatingSubmitting={isRatingSubmitting}
        onEditMessage={handleEditMessage}
        onDeleteMessage={handleDeleteMessage}
        onRegenerateMessage={handleRegenerateMessage}
        onReportHallucination={handleReportHallucination}
        isRegenerating={isRegenerating}
        // Inline Plan Card (Issue 7: Execution Plans)
        pendingPlan={currentPlan}
        routingDecision={routingDecision}
        showPlanApproval={showPlanApproval}
        onApprovePlan={handleApprovePlan}
        onRejectPlan={handleRejectPlan}
      />
    </div>
  );
});

// Display name for DevTools
ConnectedConversationPanel.displayName = "ConnectedConversationPanel";
