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
import { useSessionAutoName } from "../../hooks/useSessionAutoName";
import type { SlashCommand } from "./SlashCommandMenu";
import {
  ChatMessages,
  type Message,
  type AgentExecutionTrace,
} from "./ChatMessages";
import type { FollowUpSuggestion } from "./AIFollowUpSuggestions";
import { ChatInputForm } from "./ChatInputForm";
import {
  StylePresets,
  type StylePreset,
  type PresetName,
} from "./StylePresets";
import { Loader2, MessageSquare } from "lucide-react";
import { useFeatureFlag } from "../../contexts/FeatureFlagContext";

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
  { id: "gemini-3-flash", name: "Gemini 3 Flash", provider: "Google" },
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
  const [reasoningEffort, setReasoningEffort] =
    useState<ReasoningEffortLevel>("medium");
  const [enableThinking, setEnableThinking] = useState(true);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  // Style preset state
  const [activePreset, setActivePreset] = useState<PresetName>("balanced");
  const dispatch = useAppDispatch();

  // Feature flags
  const enableInteractiveArtifacts = useFeatureFlag("interactive_artifacts");
  const enableAiSuggestions = useFeatureFlag("ai_suggestions");

  // Redux selectors
  const currentSession = useAppSelector(selectCurrentSession);
  const isLoadingSession = useAppSelector(selectIsLoadingSession);
  const isSending = useAppSelector(selectIsSending);

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
    detectedUrls: _detectedUrls,
    detectUrls,
    fetchUrl: _fetchUrl,
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
                  duration: 2000,
                });
              })
              .catch((err) => {
                toast.error("Failed to copy", {
                  description:
                    err instanceof Error
                      ? err.message
                      : "Clipboard access denied",
                  duration: 4000,
                });
              });
          } else {
            toast.info("Nothing to copy", {
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
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // No session state
  if (!currentSession) {
    return (
      <div
        data-testid="chat-document"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-white dark:bg-gray-900",
          "text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <MessageSquare size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No Active Session</h2>
        <p className="text-sm">Select or create a session to start chatting.</p>
      </div>
    );
  }

  return (
    <div
      data-testid="chat-document"
      className={cn(
        "flex flex-col h-full",
        "bg-white dark:bg-gray-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Messages */}
      <ChatMessages
        messages={messages as Message[]}
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
      />

      {/* Style Presets Selector */}
      {showStylePresets && (
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700">
          <StylePresets
            onSelect={handleStylePresetChange}
            activePreset={activePreset}
            compact={compact}
          />
        </div>
      )}

      {/* Input Form */}
      <ChatInputForm
        input={input}
        onInputChange={setInput}
        onSubmit={handleSubmit}
        isProcessing={isProcessing}
        isStreaming={isStreaming}
        onStopStreaming={stopStream}
        isListening={isListening}
        isVoiceSupported={isVoiceSupported}
        voiceError={voiceError}
        onStartListening={startListening}
        onStopListening={stopListening}
        uploadFiles={uploadFiles}
        isUploading={isUploading}
        isDragging={isDragging}
        fileError={fileError}
        onSelectFiles={selectFiles}
        onRemoveFile={removeFile}
        dragHandlers={dragHandlers}
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
          title: c.title,
          content: c.content || "",
        }))}
        onRemoveFetchedUrl={clearFetchedUrl}
        // Slash commands props
        slashCommands={enableSlashCommands ? slashCommands : undefined}
        onSlashCommandSelect={handleSlashCommandSelect}
        // Inline AI suggestions props (Sprint 6 - VSCode Copilot style)
        enableInlineSuggestions={enableAiSuggestions}
        inlineSuggestion={inlineSuggestion}
        isSuggestionLoading={isSuggestionLoading}
        onAcceptSuggestion={handleAcceptInlineSuggestion}
        onDismissSuggestion={handleDismissInlineSuggestion}
      />
    </div>
  );
}

export default ChatDocument;
