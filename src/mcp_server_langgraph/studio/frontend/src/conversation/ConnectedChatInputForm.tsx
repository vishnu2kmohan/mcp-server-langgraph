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
 */
import { useCallback, useMemo, useState, useEffect } from "react";
import {
  ChatInputForm,
  type SlashCommand,
  type ModelOption,
} from "../components/Chat/ChatInputForm";
import type { KBFocusMode } from "../components/Chat/KnowledgeBaseFocus";
import type { ReasoningEffortLevel } from "../components/Chat/ReasoningEffortSelector";
import { useFileUpload } from "../hooks/useFileUpload";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { useKBStatus } from "../hooks/useKBStatus";
import { useUrlContentFetch } from "../hooks/useUrlContentFetch";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useAppSelector } from "../store/hooks";
import { selectSubmitOnEnter } from "../store/slices/uiSlice";

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
  inlineSuggestion = "",
  isSuggestionLoading = false,
  onAcceptSuggestion,
  onDismissSuggestion,
  autoFocus = false,
  kbFocusValue,
  onKBFocusChange,
  // Model selection (Sprint 1)
  showModelSelector = false,
  selectedModel,
  availableModels = [],
  onModelChange,
  // Reasoning effort (Sprint 1)
  modelSupportsThinking = false,
  reasoningEffort = "medium",
  onReasoningEffortChange,
  enableThinking = false,
  onEnableThinkingChange,
  // URL fetch (Sprint 1)
  enableUrlFetch = false,
}: ConnectedChatInputFormProps) {
  // =============================================================================
  // Feature Flags & UI State
  // =============================================================================
  const enableRichTextMode = useFeatureFlag("rich_text_chat_input");
  const enableKBFocus = useFeatureFlag("kb_focus");
  const submitOnEnter = useAppSelector(selectSubmitOnEnter);

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

  // Memoize drag handlers to avoid re-renders
  const memoizedDragHandlers = useMemo(() => dragHandlers, [dragHandlers]);

  return (
    <ChatInputForm
      input={value}
      onInputChange={handleInputChange}
      onSubmit={handleSubmit}
      isProcessing={isProcessing}
      isStreaming={isStreaming}
      onStopStreaming={onStopStreaming}
      // Voice input
      isListening={isListening}
      isVoiceSupported={isVoiceSupported}
      voiceError={voiceError}
      onStartListening={handleStartListening}
      onStopListening={handleStopListening}
      // File upload
      uploadFiles={uploadFiles}
      isUploading={isUploading}
      isDragging={isDragging}
      fileError={fileError}
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
      // RichText mode (feature flag + user preference)
      enableRichTextMode={enableRichTextMode}
      submitOnEnter={submitOnEnter}
      // Knowledge Base Focus (feature flag controlled)
      showKBFocus={enableKBFocus}
      kbFocusValue={kbFocusMode}
      onKBFocusChange={handleKBFocusModeChange}
      kbStatus={kbStatusForUI}
      kbStatusMessage={kbStatusMessage}
      // Model selection (Sprint 1 - Chat Input Gap Fix)
      showModelSelector={showModelSelector}
      selectedModel={selectedModel}
      availableModels={availableModels}
      onModelChange={onModelChange}
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
        title: c.title,
        content: c.content || "",
      }))}
      onRemoveFetchedUrl={clearUrl}
    />
  );
}

export default ConnectedChatInputForm;
