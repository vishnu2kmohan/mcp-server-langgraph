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
 *
 * This replaces the basic conversation/ChatInput.tsx and provides
 * a consistent, feature-rich chat experience throughout the app.
 */
import { useCallback, useMemo } from "react";
import {
  ChatInputForm,
  type SlashCommand,
} from "../components/Chat/ChatInputForm";
import { useFileUpload } from "../hooks/useFileUpload";
import { useVoiceInput } from "../hooks/useVoiceInput";

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
}: ConnectedChatInputFormProps) {
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
    />
  );
}

export default ConnectedChatInputForm;
