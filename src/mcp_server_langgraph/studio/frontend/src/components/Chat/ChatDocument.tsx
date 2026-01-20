/**
 * ChatDocument Component
 *
 * A streamlined chat document component for use within the MainDock.
 * Unlike the full ChatPage, this component:
 * - Does NOT include SessionPanel (handled by app-level LeftSidebar)
 * - Does NOT include ContextPanel (handled by app-level RightSidebar)
 * - Focuses only on messages display and input
 *
 * Features:
 * - Message display with streaming support
 * - Chat input with voice and file upload
 * - Compact mode for docked tabs
 */

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { toast } from "sonner";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  loadSession,
  addMessage,
  deleteMessage,
  clearMessages,
  selectCurrentSession,
  selectIsLoadingSession,
  selectIsSending,
} from "../../store/slices/sessionSlice";
import { selectSubmitOnEnter } from "../../store/slices/uiSlice";
import {
  useStreamingChat,
  type ReasoningEffortLevel,
} from "../../hooks/useStreamingChat";
import { useMCPConnection } from "../../hooks/useMCPConnection";
import { useVoiceInput } from "../../hooks/useVoiceInput";
import { useFileUpload } from "../../hooks/useFileUpload";
import { useFollowUpSuggestions } from "../../hooks/useFollowUpSuggestions";
import { useUrlContentFetch } from "../../hooks/useUrlContentFetch";
import { useSlashCommands } from "../../hooks/useSlashCommands";
import { useInlineSuggestions } from "../../hooks/useInlineSuggestions";
import { useAISuggestionsWebSocket } from "../../hooks/useAISuggestionsWebSocket";
import { useSessionAutoName } from "../../hooks/useSessionAutoName";
import type { SlashCommand } from "./ChatInput";
import {
  ChatMessages,
  type Message,
  type AgentExecutionTrace,
  type RatingValue,
  type ModelProvider,
} from "./ChatMessages";
import type { HallucinationReport } from "./HallucinationIndicator";
import type { FollowUpSuggestion } from "./AIFollowUpSuggestions";
import {
  SessionGoalTracker,
  type GoalSetData,
  type GoalResult,
} from "./SessionGoalTracker";
import { ChatInput } from "./ChatInput";
import { ChatSuggestions, type ChatSuggestion } from "./ChatSuggestions";
import type { MentionOption } from "./RichTextInput";
import {
  StylePresets,
  type StylePreset,
  type PresetName,
} from "./StylePresets";
import { Loader2, MessageSquare } from "lucide-react";
import { recordSignal } from "../../analytics/gsm/SignalsRegistry";
import {
  TOAST_ID_CHAT_ERROR,
  TOAST_ID_URL_FETCH_ERROR,
  TOAST_ID_VOICE_ERROR,
  TOAST_ID_FILE_ERROR,
  TOAST_ID_CONVERSATION_CLEAR,
  TOAST_ID_COPY,
  TOAST_ID_SESSION_REFRESH,
  TOAST_ID_FEEDBACK,
  TOAST_ID_RATING_ERROR,
  TOAST_ID_HALLUCINATION_REPORT,
  TOAST_ID_GOAL,
  TOAST_ID_SESSION_SUGGEST,
} from "../../constants/toastIds";
// SlashCommandMenu and ReasoningEffortSelector handled internally by ChatInputForm
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";
import {
  useSubmitMessageRatingMutation,
  useSubmitHallucinationReportMutation,
} from "../../api";

// =============================================================================
// Thinking Model Detection
// =============================================================================

/**
 * Check if a model supports extended thinking / reasoning effort.
 * Matches the backend logic in chat.py.
 */
function modelSupportsThinking(modelName: string): boolean {
  if (!modelName) return false;

  const modelLower = modelName.toLowerCase();

  // Check pattern-based matching for thinking/reasoning models
  const thinkingPatterns = [
    // Claude 4.5 family (all support extended thinking)
    "claude-opus-4",
    "claude-sonnet-4",
    "claude-haiku-4",
    // Gemini 2.5+ and 3.x family
    "gemini-2.5",
    "gemini-3",
    // GPT-5.1 Thinking model
    "gpt-5.1-thinking",
    // Legacy thinking models
    "o1-",
    "o3-",
    "deepseek-reasoner",
  ];

  return thinkingPatterns.some((pattern) => modelLower.includes(pattern));
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Default suggestions for new conversations.
 * These help users understand what the AI can do.
 */
const DEFAULT_CHAT_SUGGESTIONS: ChatSuggestion[] = [
  { id: "1", text: "Explain a concept", category: "learn", icon: "book" },
  { id: "2", text: "Write some code", category: "code", icon: "code" },
  { id: "3", text: "Help me debug", category: "help", icon: "help" },
  { id: "4", text: "Analyze this data", category: "analyze", icon: "search" },
];

// =============================================================================
// Types
// =============================================================================

/** Model option for the model selector */
export interface ModelOption {
  id: string;
  name: string;
  provider: string;
}

/** Default available models for selection (latest versions only) */
const DEFAULT_AVAILABLE_MODELS: ModelOption[] = [
  // Gemini family (default) - 2.5 stable, 3 preview
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "Google" },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "Google" },
  // NOTE: gemini-3-flash-preview is the default model per .env.test MODEL_NAME
  {
    id: "gemini-3-flash-preview",
    name: "Gemini 3 Flash Preview",
    provider: "Google",
  },
  {
    id: "gemini-3-pro-preview",
    name: "Gemini 3 Pro (Preview)",
    provider: "Google",
  },
  // Claude 4.5 family
  { id: "claude-haiku-4-5", name: "Claude 4.5 Haiku", provider: "Anthropic" },
  { id: "claude-sonnet-4-5", name: "Claude 4.5 Sonnet", provider: "Anthropic" },
  { id: "claude-opus-4-5", name: "Claude 4.5 Opus", provider: "Anthropic" },
  // GPT-5.1 family
  { id: "gpt-5.1-instant", name: "GPT-5.1 Instant", provider: "OpenAI" },
  { id: "gpt-5.1-thinking", name: "GPT-5.1 Thinking", provider: "OpenAI" },
  { id: "gpt-5.1-codex-max", name: "GPT-5.1 Codex Max", provider: "OpenAI" },
];

export interface ChatDocumentProps {
  /** Session ID to display */
  sessionId: string;
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when a follow-up suggestion is selected */
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;
  /** Whether to show the model selector */
  showModelSelector?: boolean;
  /** Available models for selection (defaults to common models) */
  availableModels?: ModelOption[];
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Enable URL content fetching with #<url> syntax */
  enableUrlFetch?: boolean;
  /** Enable slash commands menu for templates */
  enableSlashCommands?: boolean;
  /** Callback when a workflow template is selected */
  onTemplateSelect?: (template: {
    templateId: string;
    name: string;
    category: string;
  }) => void;
  /** Show style presets selector (creative/balanced/precise) */
  showStylePresets?: boolean;
  /** Callback when style preset changes */
  onStylePresetChange?: (preset: StylePreset) => void;
  /** Enable rich text editing mode (markdown formatting, mentions) */
  enableRichTextMode?: boolean;
  /** Mention options for rich text input (@model, @file references) */
  richTextMentionOptions?: MentionOption[];
  /** Maximum character length for rich text input */
  richTextMaxLength?: number;
}

// =============================================================================
// Component
// =============================================================================

export function ChatDocument({
  sessionId,
  compact = false,
  className,
  onSuggestionSelect,
  showModelSelector = false,
  availableModels = DEFAULT_AVAILABLE_MODELS,
  onModelChange,
  enableUrlFetch = false,
  enableSlashCommands = false,
  onTemplateSelect,
  showStylePresets = false,
  onStylePresetChange,
  enableRichTextMode: _enableRichTextMode = true,
  richTextMentionOptions,
  richTextMaxLength,
}: ChatDocumentProps) {
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState<string>(
    availableModels[0]?.id || "",
  );
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [_editingMessageId, setEditingMessageId] = useState<string | null>(
    null,
  );
  // LLM Thinking / Reasoning effort state
  // Note (Sprint 4 audit): enableThinking gates whether reasoningEffort is passed to the LLM.
  // - In RichTextInput mode (default): Always enabled, toggle not rendered (thinking is valuable)
  // - In ChatInputForm mode: Toggle available via onEnableThinkingChange prop
  // DO NOT remove enableThinking state - it's actively used to gate reasoningEffort in startStream calls.
  const [reasoningEffort, setReasoningEffort] =
    useState<ReasoningEffortLevel>("medium");
  const [enableThinking, setEnableThinking] = useState(true);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  // Style preset state
  const [activePreset, setActivePreset] = useState<PresetName>("balanced");
  // Message ratings state (local state + backend persistence via RTK Query)
  const [messageRatings, setMessageRatings] = useState<
    Record<string, RatingValue>
  >({});
  // Hallucination reports state (tracks which messages have been reported)
  const [reportedMessages, setReportedMessages] = useState<Set<string>>(
    new Set(),
  );
  // Session goal tracking state
  const [currentGoal, setCurrentGoal] = useState<string | undefined>(undefined);
  // RTK Query mutation for persisting ratings to backend
  const [submitRating, { isLoading: isRatingSubmitting }] =
    useSubmitMessageRatingMutation();
  // RTK Query mutation for persisting hallucination reports to backend
  const [submitHallucinationReport] = useSubmitHallucinationReportMutation();
  const dispatch = useAppDispatch();

  // Feature flags
  const enableInteractiveArtifacts = useFeatureFlag("interactive_artifacts");
  const enableAiSuggestions = useFeatureFlag("ai_suggestions");
  const enableWebSocketSuggestions = useFeatureFlag("ai_suggestions_websocket");
  const showChatAvatars = useFeatureFlag("show_chat_avatars");
  const enableSessionGoalTracker = useFeatureFlag("session_goal_tracker");
  const enableHallucinationReporting = useFeatureFlag(
    "hallucination_reporting",
  );

  // Track previous sessionId for WebSocket context updates
  const prevSessionIdRef = useRef<string | undefined>(undefined);
  // Track cursor position for WebSocket suggestions
  const cursorPositionRef = useRef<number>(0);

  // Redux selectors
  const currentSession = useAppSelector(selectCurrentSession);
  const isLoadingSession = useAppSelector(selectIsLoadingSession);
  const isSending = useAppSelector(selectIsSending);
  const submitOnEnter = useAppSelector(selectSubmitOnEnter);

  // MCP connection hook
  const { connectionMode: _connectionMode } = useMCPConnection({
    autoConnect: true,
    autoReconnect: true,
    maxReconnectAttempts: 5,
  });

  // Streaming chat hook for real-time responses
  const {
    isStreaming,
    streamingContent,
    startStream,
    stopStream,
    clearContent,
    usage,
    model,
    error: streamingError,
    thinkingContent,
    thinkingTokens,
    // LangGraph visualization data
    langgraphNodes,
    langgraphEdges,
    currentNode,
  } = useStreamingChat();

  // Voice input hook for speech-to-text
  const {
    isListening,
    isSupported: isVoiceSupported,
    transcript,
    error: voiceError,
    startListening,
    stopListening,
    clearTranscript,
  } = useVoiceInput({
    continuous: false,
    interimResults: true,
  });

  // File upload hook for attachments
  const {
    files: uploadFiles,
    isUploading,
    isDragging,
    error: fileError,
    selectFiles,
    removeFile,
    clearFiles: clearUploadFiles,
    dragHandlers,
  } = useFileUpload({
    maxSizeMB: 10,
    maxFiles: 5,
  });

  // URL content fetch hook for #<url> patterns
  // Auto-fetch with debounce for smoother UX while typing
  const {
    detectUrls,
    fetchedContent,
    loadingUrls,
    clearUrl: clearFetchedUrl,
    clearContent: clearFetchedContent,
    getContextString,
  } = useUrlContentFetch({
    autoFetch: enableUrlFetch,
    debounceMs: 500, // Wait 500ms after user stops typing to fetch
  });

  // =============================================================================
  // Error UX: Toast Notifications for Errors
  // =============================================================================

  // Track shown errors to avoid duplicate toasts
  const shownErrorsRef = useRef<Set<string>>(new Set());

  // Show toast when streaming error occurs
  useEffect(() => {
    if (streamingError && !shownErrorsRef.current.has(streamingError)) {
      shownErrorsRef.current.add(streamingError);
      toast.error("Chat Error", {
        id: TOAST_ID_CHAT_ERROR,
        description: streamingError,
        duration: 5000,
      });
    }
  }, [streamingError]);

  // Show toast for URL fetch errors
  useEffect(() => {
    for (const content of fetchedContent) {
      if (content.error && !shownErrorsRef.current.has(`url-${content.url}`)) {
        shownErrorsRef.current.add(`url-${content.url}`);
        toast.error("Failed to fetch URL", {
          id: TOAST_ID_URL_FETCH_ERROR,
          description: `Could not load content from ${content.url}`,
          duration: 4000,
        });
      }
    }
  }, [fetchedContent]);

  // Show toast for voice input errors
  useEffect(() => {
    if (voiceError && !shownErrorsRef.current.has(`voice-${voiceError}`)) {
      shownErrorsRef.current.add(`voice-${voiceError}`);
      toast.error("Voice Input Error", {
        id: TOAST_ID_VOICE_ERROR,
        description: voiceError,
        duration: 4000,
      });
    }
  }, [voiceError]);

  // Show toast for file upload errors
  useEffect(() => {
    if (fileError && !shownErrorsRef.current.has(`file-${fileError}`)) {
      shownErrorsRef.current.add(`file-${fileError}`);
      toast.error("File Upload Error", {
        id: TOAST_ID_FILE_ERROR,
        description: fileError,
        duration: 4000,
      });
    }
  }, [fileError]);

  // Built-in slash command handler
  const handleBuiltInCommand = useCallback(
    (command: SlashCommand) => {
      switch (command.name) {
        case "help":
          // Show help message as a system message
          dispatch(
            addMessage({
              id: `msg-${Date.now()}-help`,
              role: "assistant",
              content: `## Available Commands

- **/help** - Show this help message
- **/clear** - Clear the current conversation
- **/copy** - Copy the last response to clipboard
- **/export** - Export conversation (coming soon)
- **/settings** - Open settings panel (coming soon)
- **/refresh** - Refresh the session

Type \`/\` to see available commands.`,
              timestamp: Date.now(),
            }),
          );
          break;

        case "clear":
          // Clear the conversation
          dispatch(clearMessages());
          toast.success("Conversation cleared", {
            id: TOAST_ID_CONVERSATION_CLEAR,
            duration: 2000,
          });
          break;

        case "copy": {
          // Copy last assistant message to clipboard with error handling
          const sessionMessages = currentSession?.messages || [];
          const lastAssistant = sessionMessages.findLast(
            (m: { role: string; content: string }) => m.role === "assistant",
          );
          if (lastAssistant) {
            navigator.clipboard
              .writeText(lastAssistant.content)
              .then(() => {
                toast.success("Copied to clipboard", {
                  id: TOAST_ID_COPY,
                  duration: 2000,
                });
              })
              .catch((err) => {
                toast.error("Failed to copy", {
                  id: TOAST_ID_COPY,
                  description:
                    err instanceof Error
                      ? err.message
                      : "Clipboard access denied",
                  duration: 4000,
                });
              });
          } else {
            toast.info("Nothing to copy", {
              id: TOAST_ID_COPY,
              description: "No assistant message found",
              duration: 2000,
            });
          }
          break;
        }

        case "refresh":
          // Reload the current session
          if (currentSession) {
            dispatch(loadSession(currentSession.id));
            toast.success("Session refreshed", {
              id: TOAST_ID_SESSION_REFRESH,
              duration: 2000,
            });
          }
          break;

        default:
          // Other commands can be handled as needed
          break;
      }
    },
    [dispatch, currentSession],
  );

  // Slash commands hook for "/" templates
  const { commands: slashCommands, handleSelect: handleSlashCommandSelect } =
    useSlashCommands({
      onTemplateSelect,
      onBuiltInCommand: handleBuiltInCommand,
      skipTemplates: !enableSlashCommands,
    });

  // Messages from current session
  const messages = useMemo(
    () => currentSession?.messages || [],
    [currentSession?.messages],
  );

  // Get last assistant message content for generating follow-up suggestions
  const lastAssistantContent = useMemo(() => {
    const assistantMessages = messages.filter((m) => m.role === "assistant");
    if (assistantMessages.length === 0) return "";
    const lastMessage = assistantMessages[assistantMessages.length - 1];
    return lastMessage?.content ?? "";
  }, [messages]);

  // Follow-up suggestions hook (only active when not streaming/sending)
  const {
    suggestions,
    isLoading: suggestionsLoading,
    trackClick,
    submitFeedback,
  } = useFollowUpSuggestions({
    content: lastAssistantContent,
    enabled: enableAiSuggestions && !isStreaming && !isSending,
    maxSuggestions: 4,
    debounceMs: 300,
    sessionId: currentSession?.id,
  });

  // Inline suggestions hook (VSCode Copilot style ghost text)
  const {
    suggestion: inlineSuggestion,
    isLoading: isSuggestionLoading,
    updateInput: updateInlineSuggestionInput,
    acceptSuggestion: handleAcceptInlineSuggestion,
    dismissSuggestion: handleDismissInlineSuggestion,
  } = useInlineSuggestions({
    enabled: enableAiSuggestions && !isStreaming && !isSending,
    sessionId: currentSession?.id,
    minLength: 5, // Only suggest after 5 characters
    debounceMs: 400, // Debounce to avoid too many API calls
    onAccept: (suggestion) => {
      // Append accepted suggestion to input
      setInput((prev) => prev + suggestion);
    },
  });

  // Update inline suggestions when input changes
  useEffect(() => {
    if (enableAiSuggestions && !isStreaming && !isSending) {
      updateInlineSuggestionInput(input);
    }
  }, [
    input,
    enableAiSuggestions,
    isStreaming,
    isSending,
    updateInlineSuggestionInput,
  ]);

  // =============================================================================
  // WebSocket Inline Suggestions (ai_suggestions_websocket feature flag)
  // Uses WebSocket for lower-latency suggestions with cursor position awareness
  // Falls back to REST-based useInlineSuggestions when WebSocket is disconnected
  // =============================================================================
  const useWebSocketForSuggestions =
    enableWebSocketSuggestions &&
    enableAiSuggestions &&
    !isStreaming &&
    !isSending &&
    !!currentSession?.id;

  const {
    status: wsStatus,
    currentSuggestion: wsSuggestion,
    isPending: wsIsPending,
    requestSuggestion: wsRequestSuggestion,
    acceptSuggestion: wsAcceptSuggestion,
    rejectSuggestion: wsRejectSuggestion,
    updateContext: wsUpdateContext,
    clearSuggestion: wsClearSuggestion,
  } = useAISuggestionsWebSocket({
    enabled: useWebSocketForSuggestions,
    sessionId: currentSession?.id,
    onSuggestion: (suggestion) => {
      // Append accepted suggestion to input when received
      setInput((prev) => prev + suggestion.text);
    },
  });

  // Request WebSocket suggestion when input changes (debounced via hook internally)
  useEffect(() => {
    if (
      useWebSocketForSuggestions &&
      wsStatus === "connected" &&
      input.length > 3
    ) {
      wsRequestSuggestion(input, cursorPositionRef.current);
    }
  }, [input, useWebSocketForSuggestions, wsStatus, wsRequestSuggestion]);

  // Update WebSocket context when session changes
  useEffect(() => {
    if (
      useWebSocketForSuggestions &&
      wsStatus === "connected" &&
      currentSession?.id &&
      currentSession.id !== prevSessionIdRef.current
    ) {
      wsUpdateContext(`Session: ${currentSession.id}`);
      prevSessionIdRef.current = currentSession.id;
    }
  }, [
    currentSession?.id,
    useWebSocketForSuggestions,
    wsStatus,
    wsUpdateContext,
  ]);

  // Determine if WebSocket is active and connected
  const isWebSocketActive =
    useWebSocketForSuggestions && wsStatus === "connected";

  // Resolve which suggestion values to use:
  // Priority: WebSocket (when connected) > REST hook
  const effectiveInlineSuggestion = isWebSocketActive
    ? wsSuggestion?.text || ""
    : inlineSuggestion;

  const effectiveIsSuggestionLoading = isWebSocketActive
    ? wsIsPending
    : isSuggestionLoading;

  // Accept suggestion handler - works with WebSocket or REST
  const handleAcceptSuggestion = useCallback(() => {
    if (isWebSocketActive && wsSuggestion?.suggestionId) {
      wsAcceptSuggestion(wsSuggestion.suggestionId);
    } else {
      handleAcceptInlineSuggestion();
    }
  }, [
    isWebSocketActive,
    wsSuggestion,
    wsAcceptSuggestion,
    handleAcceptInlineSuggestion,
  ]);

  // Dismiss suggestion handler - works with WebSocket or REST
  const handleDismissSuggestion = useCallback(() => {
    if (isWebSocketActive && wsSuggestion?.suggestionId) {
      wsRejectSuggestion(wsSuggestion.suggestionId);
    } else {
      wsClearSuggestion();
    }
    handleDismissInlineSuggestion();
  }, [
    isWebSocketActive,
    wsSuggestion,
    wsRejectSuggestion,
    wsClearSuggestion,
    handleDismissInlineSuggestion,
  ]);

  // Session auto-naming (AI-powered title generation like ChatGPT/Claude)
  // Triggers after first user message for sessions with default names
  const { isGenerating: _isGeneratingTitle } = useSessionAutoName({
    sessionId: currentSession?.id,
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    currentName: currentSession?.name,
    enabled: enableAiSuggestions && !!currentSession,
  });

  // Handle suggestion selection - fill input with suggestion text and track click
  const handleSuggestionSelect = useCallback(
    (suggestion: FollowUpSuggestion) => {
      setInput(suggestion.text);

      // Track the click for analytics (fire-and-forget)
      trackClick(suggestion);

      // Optionally call external handler
      onSuggestionSelect?.(suggestion);
    },
    [onSuggestionSelect, trackClick],
  );

  // Handle suggestion feedback (thumbs up/down)
  const handleSuggestionFeedback = useCallback(
    (suggestion: FollowUpSuggestion, feedback: "positive" | "negative") => {
      // Submit feedback for analytics (fire-and-forget)
      submitFeedback(suggestion, feedback);
    },
    [submitFeedback],
  );

  // Handle model selection change
  const handleModelChange = useCallback(
    (modelId: string) => {
      setSelectedModel(modelId);
      onModelChange?.(modelId);
    },
    [onModelChange],
  );

  // Handle style preset change
  const handleStylePresetChange = useCallback(
    (preset: StylePreset) => {
      setActivePreset(preset.name);
      onStylePresetChange?.(preset);
    },
    [onStylePresetChange],
  );

  // Handle message rating - persists to backend via RTK Query
  const handleRateMessage = useCallback(
    (messageId: string, rating: RatingValue) => {
      // Update local state immediately for responsive UI (optimistic update)
      setMessageRatings((prev) => ({
        ...prev,
        [messageId]: rating,
      }));

      // Persist to backend if we have a valid session
      if (currentSession?.id) {
        // Map frontend RatingValue to backend format
        const backendRating =
          rating === "up" ? "up" : rating === "down" ? "down" : null;

        submitRating({
          session_id: currentSession.id,
          message_id: messageId,
          rating: backendRating,
        })
          .unwrap()
          .catch((error) => {
            // Revert optimistic update on failure
            setMessageRatings((prev) => {
              const updated = { ...prev };
              delete updated[messageId];
              return updated;
            });
            toast.error("Failed to save rating", {
              id: TOAST_ID_RATING_ERROR,
              description:
                error instanceof Error ? error.message : "Please try again",
              duration: 3000,
            });
          });
      }
    },
    [currentSession?.id, submitRating],
  );

  // Handle rating feedback (for negative ratings) - persists to backend
  const handleRatingFeedback = useCallback(
    (messageId: string, feedback: string) => {
      // Get current rating for this message
      const currentRating = messageRatings[messageId];

      // Persist feedback with rating to backend
      if (currentSession?.id && currentRating) {
        submitRating({
          session_id: currentSession.id,
          message_id: messageId,
          rating: currentRating === "up" ? "up" : "down",
          feedback, // Include feedback text
        })
          .unwrap()
          .then(() => {
            toast.success("Thank you for your feedback!", { id: TOAST_ID_FEEDBACK, duration: 2000 });
          })
          .catch(() => {
            toast.error("Failed to save feedback", { id: TOAST_ID_FEEDBACK, duration: 3000 });
          });
      } else {
        // Fallback for local-only feedback
        toast.success("Thank you for your feedback!", { id: TOAST_ID_FEEDBACK, duration: 2000 });
      }
    },
    [currentSession?.id, messageRatings, submitRating],
  );

  // Handle hallucination report - tracks reported messages and persists to backend
  // Categories are now aligned between frontend and backend (no mapping needed)
  const handleReportHallucination = useCallback(
    (report: HallucinationReport) => {
      // Mark message as reported (optimistic update)
      setReportedMessages((prev) => new Set([...prev, report.messageId]));

      // Record analytics signals for HEART metrics
      recordSignal("ai_hallucination_reported", 1, {
        sessionId: currentSession?.id,
        messageId: report.messageId,
      });
      recordSignal("ai_hallucination_category", report.category, {
        sessionId: currentSession?.id,
        messageId: report.messageId,
      });

      // Persist to backend
      if (currentSession?.id) {
        submitHallucinationReport({
          message_id: report.messageId,
          session_id: currentSession.id,
          category: report.category, // Direct pass-through (aligned with backend)
          description: report.details,
          severity: "medium", // Default severity
        })
          .unwrap()
          .then(() => {
            toast.success("Thank you for reporting this issue", {
              id: TOAST_ID_HALLUCINATION_REPORT,
              description: "Your feedback helps us improve AI accuracy.",
              duration: 3000,
            });
          })
          .catch((error) => {
            // Revert optimistic update on failure
            setReportedMessages((prev) => {
              const updated = new Set(prev);
              updated.delete(report.messageId);
              return updated;
            });
            console.error("[HallucinationReport] Failed to submit:", error);
            toast.error("Failed to submit report", {
              id: TOAST_ID_HALLUCINATION_REPORT,
              description: "Please try again later.",
              duration: 3000,
            });
          });
      } else {
        // Fallback for no session - local-only feedback
        console.info("[HallucinationReport] No session, local only:", report);
        toast.success("Thank you for reporting this issue", {
          id: TOAST_ID_HALLUCINATION_REPORT,
          description: "Your feedback helps us improve AI accuracy.",
          duration: 3000,
        });
      }
    },
    [currentSession?.id, submitHallucinationReport],
  );

  // Handle session goal set - stores goal for tracking
  const handleGoalSet = useCallback((data: GoalSetData) => {
    setCurrentGoal(data.goal);
    toast.success("Goal set", {
      id: TOAST_ID_GOAL,
      description: data.goal,
      duration: 2000,
    });
    // TODO: Persist goal to backend when API is available
    console.info("[SessionGoal] Set:", data);
  }, []);

  // Handle session goal completion - tracks achievement result
  const handleGoalComplete = useCallback((result: GoalResult) => {
    const achievementText =
      result.achieved === true
        ? "achieved"
        : result.achieved === "partial"
          ? "partially achieved"
          : "not achieved";
    toast.info(`Goal ${achievementText}`, {
      id: TOAST_ID_GOAL,
      description: result.goal,
      duration: 3000,
    });
    // Clear the goal after completion
    setCurrentGoal(undefined);
    // TODO: Persist goal result to backend for analytics
    console.info("[SessionGoal] Complete:", result);
  }, []);

  // Handle session goal clear - removes current goal
  const handleGoalClear = useCallback(() => {
    setCurrentGoal(undefined);
  }, []);

  // Determine model provider from selected model for cost calculation
  const modelProvider: ModelProvider = useMemo(() => {
    const modelLower = (model || selectedModel || "").toLowerCase();
    if (modelLower.includes("claude") || modelLower.includes("anthropic")) {
      return "anthropic";
    }
    if (modelLower.includes("gemini") || modelLower.includes("google")) {
      return "google";
    }
    if (modelLower.includes("azure")) {
      return "azure";
    }
    return "openai"; // default
  }, [model, selectedModel]);

  // Construct agent execution trace from streaming usage data and LangGraph nodes
  const agentExecutionTrace: AgentExecutionTrace | undefined = useMemo(() => {
    // Show trace if streaming, has usage, or has LangGraph nodes
    if (!isStreaming && !usage && langgraphNodes.length === 0) {
      return undefined;
    }
    return {
      tokens: usage
        ? {
            input: usage.promptTokens,
            output: usage.completionTokens,
          }
        : undefined,
      rawOutput: streamingContent || undefined,
      steps: isStreaming
        ? [{ name: "Processing", status: "running" }]
        : usage
          ? [{ name: "Completed", status: "success" }]
          : undefined,
      // LangGraph visualization data
      nodes: langgraphNodes.length > 0 ? langgraphNodes : undefined,
      edges: langgraphEdges.length > 0 ? langgraphEdges : undefined,
      currentNode: currentNode || undefined,
    };
  }, [
    isStreaming,
    usage,
    streamingContent,
    langgraphNodes,
    langgraphEdges,
    currentNode,
  ]);

  // Determine if we're in an active sending/streaming state
  const isProcessing = isSending || isStreaming;

  // Load session when sessionId changes
  useEffect(() => {
    if (sessionId && (!currentSession || currentSession.id !== sessionId)) {
      dispatch(loadSession(sessionId));
    }
  }, [dispatch, sessionId, currentSession]);

  // Guard against processing streaming completion multiple times
  const hasProcessedStreamRef = useRef(false);

  // Reset the stream processing guard when streaming starts
  useEffect(() => {
    if (isStreaming) {
      hasProcessedStreamRef.current = false;
    }
  }, [isStreaming]);

  // When streaming completes, add the response as a message
  // Include thinking content for persistence so it's visible on message reload
  useEffect(() => {
    if (
      !isStreaming &&
      streamingContent &&
      currentSession &&
      !hasProcessedStreamRef.current
    ) {
      hasProcessedStreamRef.current = true;

      const assistantMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        role: "assistant" as const,
        content: streamingContent,
        timestamp: Date.now(),
        // Persist thinking content with the message
        ...(thinkingContent && { thinkingContent }),
        ...(thinkingTokens && { thinkingTokens }),
        ...(model && { modelName: model }),
        // Persist token usage for cost tracking and display
        ...(usage && {
          usage: {
            promptTokens: usage.promptTokens,
            completionTokens: usage.completionTokens,
            totalTokens: usage.promptTokens + usage.completionTokens,
          },
        }),
      };
      dispatch(addMessage(assistantMessage));
      clearContent();
    }
  }, [
    dispatch,
    isStreaming,
    streamingContent,
    currentSession,
    clearContent,
    thinkingContent,
    thinkingTokens,
    model,
    usage,
  ]);

  // Sync voice transcript to input field
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  // Detect URLs in input when URL fetch is enabled
  useEffect(() => {
    if (enableUrlFetch) {
      detectUrls(input);
    }
  }, [input, enableUrlFetch, detectUrls]);

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing || !currentSession) return;

    const content = input.trim();
    setInput("");
    clearTranscript();
    clearUploadFiles();

    // Add user message immediately (optimistic update)
    // Note: User sees original message, but LLM gets URL context appended
    const userMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      role: "user" as const,
      content,
      timestamp: Date.now(),
    };
    dispatch(addMessage(userMessage));

    // Build content for LLM: user message + URL context if available
    const urlContext = enableUrlFetch ? getContextString() : "";
    const contentWithContext = urlContext ? `${content}${urlContext}` : content;

    // Clear fetched URL content after including in message
    if (urlContext) {
      clearFetchedContent();
    }

    // Start streaming response with reasoning effort options
    startStream(currentSession.id, contentWithContext, {
      reasoningEffort: enableThinking ? reasoningEffort : undefined,
    });
  };

  // Handle message edit - sets the input to the message content for re-submission
  const handleEditMessage = useCallback(
    (messageId: string) => {
      const message = messages.find((m) => m.id === messageId);
      if (message && message.role === "user") {
        setEditingMessageId(messageId);
        setInput(message.content);
      }
    },
    [messages],
  );

  // Handle message regeneration - re-sends the last user message to get new response
  const handleRegenerateMessage = useCallback(
    async (messageId: string) => {
      if (!currentSession || isProcessing) return;

      // Find the message to regenerate and the preceding user message
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      // For assistant messages, find the preceding user message
      const message = messages[messageIndex];
      if (!message || message.role !== "assistant") return;

      // Find the user message that prompted this response
      let userMessageIndex = messageIndex - 1;
      while (userMessageIndex >= 0) {
        const msgAtIndex = messages[userMessageIndex];
        if (msgAtIndex?.role === "user") break;
        userMessageIndex--;
      }

      if (userMessageIndex < 0) return;

      const userMessage = messages[userMessageIndex];
      if (!userMessage) return;

      setIsRegenerating(true);
      try {
        // Delete the old assistant response
        dispatch(deleteMessage(messageId));

        // Re-send the user message to get a new response with reasoning effort
        startStream(currentSession.id, userMessage.content, {
          reasoningEffort: enableThinking ? reasoningEffort : undefined,
        });
      } finally {
        setIsRegenerating(false);
      }
    },
    [
      currentSession,
      messages,
      isProcessing,
      dispatch,
      startStream,
      enableThinking,
      reasoningEffort,
    ],
  );

  // Handle message deletion
  const handleDeleteMessage = useCallback(
    (messageId: string) => {
      dispatch(deleteMessage(messageId));
    },
    [dispatch],
  );

  // Loading state
  if (isLoadingSession && !currentSession) {
    return (
      <div
        data-testid="chat-document"
        className={cn(
          "flex items-center justify-center h-full",
          "bg-neutral-1",
          className,
        )}
      >
        <Loader2 className="w-8 h-8 animate-spin text-primary-9" />
      </div>
    );
  }

  // No session state - show suggestions to help users get started
  if (!currentSession) {
    return (
      <div
        data-testid="chat-document"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-neutral-1",
          "text-neutral-10",
          className,
        )}
      >
        <MessageSquare size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No Active Session</h2>
        <p className="text-sm mb-6">
          Select or create a session to start chatting.
        </p>
        <ChatSuggestions
          suggestions={DEFAULT_CHAT_SUGGESTIONS}
          onSelect={(text) => {
            // User clicked a suggestion but no session exists
            // The parent component should handle session creation
            toast.info(`Create a new session to ask: "${text}"`, { id: TOAST_ID_SESSION_SUGGEST });
          }}
          title="Try asking about..."
          compact
        />
      </div>
    );
  }

  return (
    <div
      data-testid="chat-document"
      className={cn(
        "flex flex-col h-full",
        "bg-neutral-1",
        compact && "text-sm",
        className,
      )}
    >
      {/* Session Goal Tracker - helps users track conversation goals */}
      {enableSessionGoalTracker && currentSession && (
        <div className="px-4 py-2 border-b border-neutral-5">
          <SessionGoalTracker
            sessionId={currentSession.id}
            currentGoal={currentGoal}
            onGoalSet={handleGoalSet}
            onGoalComplete={handleGoalComplete}
            onGoalClear={handleGoalClear}
            compact={compact}
          />
        </div>
      )}

      {/* Messages */}
      <ChatMessages
        messages={
          messages.map((m) => ({
            ...m,
            isReported: reportedMessages.has(m.id),
          })) as Message[]
        }
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        isSending={isSending}
        agentExecutionTrace={agentExecutionTrace}
        enableInteractiveArtifacts={enableInteractiveArtifacts}
        onEditMessage={handleEditMessage}
        onRegenerateMessage={handleRegenerateMessage}
        onDeleteMessage={handleDeleteMessage}
        isRegenerating={isRegenerating}
        // LLM Thinking trace props
        llmThinkingContent={thinkingContent}
        llmThinkingTokens={thinkingTokens ?? undefined}
        isThinkingExpanded={isThinkingExpanded}
        onToggleThinking={() => setIsThinkingExpanded((prev) => !prev)}
        llmModelName={model ?? undefined}
        isThinkingModel={modelSupportsThinking(model || "")}
        // AI Follow-Up Suggestions props
        suggestions={enableAiSuggestions ? suggestions : undefined}
        onSuggestionSelect={handleSuggestionSelect}
        onSuggestionFeedback={handleSuggestionFeedback}
        suggestionsLoading={suggestionsLoading}
        // Response Rating props
        messageRatings={messageRatings}
        onRateMessage={handleRateMessage}
        onRatingFeedback={handleRatingFeedback}
        isRatingSubmitting={isRatingSubmitting}
        // Hallucination Reporting props (gated by feature flag)
        onReportHallucination={
          enableHallucinationReporting ? handleReportHallucination : undefined
        }
        // Token Usage Display props
        showTokenUsage={true}
        modelProvider={modelProvider}
        showCost={false}
        // Avatar props (show_chat_avatars feature flag)
        showAvatars={showChatAvatars}
      />

      {/* Style Presets Selector */}
      {showStylePresets && (
        <div className="px-4 py-2 border-t border-neutral-5">
          <StylePresets
            onSelect={handleStylePresetChange}
            activePreset={activePreset}
            compact={compact}
          />
        </div>
      )}

      {/* Input Form - ChatInput pill-style component */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={isProcessing}
        isStreaming={isStreaming}
        onStopStreaming={stopStream}
        isListening={isListening}
        isVoiceSupported={isVoiceSupported}
        voiceError={voiceError ?? undefined}
        onStartListening={startListening}
        onStopListening={stopListening}
        uploadFiles={uploadFiles}
        isUploading={isUploading}
        isDragging={isDragging}
        fileError={fileError ?? undefined}
        onSelectFiles={selectFiles}
        onRemoveFile={removeFile}
        dragHandlers={dragHandlers}
        // Submit behavior
        submitOnEnter={submitOnEnter}
        mentionOptions={richTextMentionOptions}
        maxLength={richTextMaxLength}
        // Reasoning effort / thinking props
        modelSupportsThinking={modelSupportsThinking(model || "")}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={setReasoningEffort}
        enableThinking={enableThinking}
        onEnableThinkingChange={setEnableThinking}
        // Model selector props
        showModelSelector={showModelSelector}
        selectedModel={selectedModel}
        availableModels={availableModels}
        onModelChange={handleModelChange}
        // URL fetch props
        enableUrlFetch={enableUrlFetch}
        urlFetchLoading={loadingUrls}
        fetchedUrls={fetchedContent.map((c) => ({
          url: c.url,
          title: c.title || c.url,
          content: c.content || "",
        }))}
        onRemoveFetchedUrl={clearFetchedUrl}
        // Slash commands props
        slashCommands={
          enableSlashCommands ? (slashCommands as SlashCommand[]) : undefined
        }
        onSlashCommandSelect={
          handleSlashCommandSelect as (cmd: SlashCommand) => void
        }
        // Inline AI suggestions props (VSCode Copilot style)
        // Uses WebSocket when available, falls back to REST
        enableInlineSuggestions={enableAiSuggestions}
        inlineSuggestion={effectiveInlineSuggestion}
        isSuggestionLoading={effectiveIsSuggestionLoading}
        onAcceptSuggestion={handleAcceptSuggestion}
        onDismissSuggestion={handleDismissSuggestion}
        // Cursor position tracking for WebSocket suggestions
        onCursorPositionChange={(pos) => {
          cursorPositionRef.current = pos;
        }}
      />
    </div>
  );
}

export default ChatDocument;
