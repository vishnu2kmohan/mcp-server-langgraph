/**
 * ChatInputForm Component
 *
 * Rich chat input form with voice input, file uploads, and drag-drop support.
 *
 * Layout Design (inspired by ChatGPT, Claude, OpenWebUI):
 * ┌─────────────────────────────────────────────────────────────┐
 * │                     (Bottom padding zone)                    │
 * │  ┌───────────────────────────────────────────────────────┐  │
 * │  │  [📎]  Textarea (expandable)              [🎤] [Send] │  │
 * │  └───────────────────────────────────────────────────────┘  │
 * │                     (Bottom padding zone)                    │
 * └─────────────────────────────────────────────────────────────┘
 *
 * Features:
 * - Centered max-width container for readability on wide screens
 * - Bottom padding for comfortable spacing from page edge
 * - Multi-line textarea with auto-expand
 * - Consolidated controls grouped around input
 */

import { useRef, useEffect, useCallback, useState, useMemo } from "react";
import {
  Send,
  Mic,
  MicOff,
  // Paperclip (unused),
  X,
  Loader2,
  Square,
  Plus,
  ChevronDown,
  Check,
} from "lucide-react";
import type { UploadFile, DragHandlers } from "../../hooks/useFileUpload";
import {
  ReasoningEffortSelector,
  type ReasoningEffortLevel,
} from "./ReasoningEffortSelector";
import { SlashCommandMenu, type SlashCommand } from "./SlashCommandMenu";
import { RichTextInput, type MentionOption } from "./RichTextInput";

// Re-export SlashCommand for external use
export type { SlashCommand };

/** Model option for model selector dropdown */
export interface ModelOption {
  id: string;
  name: string;
  provider: string;
}

// Re-export for test compatibility
export type { UploadFile };

export interface ChatInputFormProps {
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isProcessing: boolean;
  /** Whether response is currently streaming (for stop button) */
  isStreaming?: boolean;
  /** Callback to stop streaming response */
  onStopStreaming?: () => void;
  isListening: boolean;
  isVoiceSupported: boolean;
  voiceError: string | null;
  onStartListening: () => void;
  onStopListening: () => void;
  uploadFiles: UploadFile[];
  isUploading: boolean;
  isDragging: boolean;
  fileError: string | null;
  onSelectFiles: (files: File[]) => void;
  onRemoveFile: (id: string) => void;
  dragHandlers: DragHandlers;
  // Reasoning effort / thinking model props
  /** Whether the current model supports extended thinking (Claude Opus 4.5, Gemini 2.5, etc.) */
  modelSupportsThinking?: boolean;
  /** Current reasoning effort level */
  reasoningEffort?: ReasoningEffortLevel;
  /** Callback when reasoning effort level changes */
  onReasoningEffortChange?: (level: ReasoningEffortLevel) => void;
  /** Whether thinking is enabled for supported models */
  enableThinking?: boolean;
  /** Callback when thinking enabled state changes */
  onEnableThinkingChange?: (enabled: boolean) => void;
  // Model selection props
  /** Whether to show the model selector dropdown */
  showModelSelector?: boolean;
  /** Currently selected model ID */
  selectedModel?: string;
  /** Available models for selection */
  availableModels?: ModelOption[];
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  // Slash command props
  /** Available slash commands (e.g., /help, /clear, /export) */
  slashCommands?: SlashCommand[];
  /** Callback when a slash command is selected */
  onSlashCommandSelect?: (command: SlashCommand) => void;
  // URL content fetch props (OpenWebUI-style "#URL" integration)
  /** Enable URL content fetching when #https://... detected */
  enableUrlFetch?: boolean;
  /** URLs currently being fetched */
  urlFetchLoading?: string[];
  /** Already fetched URL content */
  fetchedUrls?: Array<{ url: string; title?: string; content: string }>;
  /** Callback to remove a fetched URL */
  onRemoveFetchedUrl?: (url: string) => void;
  // Inline AI Suggestions props (Sprint 6 - VSCode Copilot style)
  /** Enable inline ghost text suggestions */
  enableInlineSuggestions?: boolean;
  /** Current inline suggestion text (ghost text after cursor) */
  inlineSuggestion?: string;
  /** Whether suggestion is being fetched */
  isSuggestionLoading?: boolean;
  /** Callback when user accepts suggestion (Tab key) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape key) */
  onDismissSuggestion?: () => void;
  /** Auto-focus the textarea on mount */
  autoFocus?: boolean;
  // RichText mode props (Sprint 5.2 - Pill + RichTextInput as default)
  /**
   * Enable rich text mode with pill container styling.
   * When true: Renders RichTextInput with formatting toolbar
   * When false: Renders plain textarea (backwards compatible)
   */
  enableRichTextMode?: boolean;
  /**
   * Keyboard submit behavior - PASS THROUGH from uiSlice, never hardcode.
   * - true: Enter = submit, Shift+Enter = newline (ChatGPT style)
   * - false: Ctrl/Cmd+Enter = submit, Enter = newline (legacy)
   */
  submitOnEnter?: boolean;
  /** Mention options for RichTextInput autocomplete */
  mentionOptions?: MentionOption[];
  /** Maximum character length for RichTextInput */
  richTextMaxLength?: number;
}

export function ChatInputForm({
  input,
  onInputChange,
  onSubmit,
  isProcessing,
  isStreaming = false,
  onStopStreaming,
  isListening,
  isVoiceSupported,
  voiceError,
  onStartListening,
  onStopListening,
  uploadFiles,
  isUploading,
  isDragging,
  fileError,
  onSelectFiles,
  onRemoveFile,
  dragHandlers,
  // Reasoning effort props
  modelSupportsThinking = false,
  reasoningEffort = "medium",
  onReasoningEffortChange,
  enableThinking = true,
  onEnableThinkingChange,
  // Model selection props
  showModelSelector = false,
  selectedModel,
  availableModels = [],
  onModelChange,
  // Slash command props
  slashCommands,
  onSlashCommandSelect,
  // URL content fetch props
  enableUrlFetch = false,
  urlFetchLoading = [],
  fetchedUrls = [],
  onRemoveFetchedUrl,
  // Inline AI Suggestions props
  enableInlineSuggestions = false,
  inlineSuggestion = "",
  isSuggestionLoading = false,
  onAcceptSuggestion,
  onDismissSuggestion,
  // Auto-focus
  autoFocus = false,
  // RichText mode props
  enableRichTextMode = false,
  submitOnEnter = true,
  mentionOptions = [],
  richTextMaxLength,
}: ChatInputFormProps) {
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [isVoiceBannerDismissed, setIsVoiceBannerDismissed] = useState(false);
  const [isSlashMenuForceClosed, setIsSlashMenuForceClosed] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus the textarea on mount if autoFocus is true
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Slash command menu logic
  const showSlashMenu = useMemo(() => {
    if (!slashCommands || slashCommands.length === 0) return false;
    if (isSlashMenuForceClosed) return false;
    return input.startsWith("/");
  }, [input, slashCommands, isSlashMenuForceClosed]);

  // Filter for slash command menu
  const slashCommandFilter = useMemo(() => {
    if (!input.startsWith("/")) return "";
    return input.slice(1); // Remove the leading "/"
  }, [input]);

  // Reset force-close when input changes (user starts typing again)
  useEffect(() => {
    if (!input.startsWith("/")) {
      setIsSlashMenuForceClosed(false);
    }
  }, [input]);

  // Handle slash command selection
  const handleSlashCommandSelect = useCallback(
    (command: SlashCommand) => {
      onSlashCommandSelect?.(command);
      setIsSlashMenuForceClosed(true);
    },
    [onSlashCommandSelect],
  );

  // Handle slash menu close (Escape key)
  const handleSlashMenuClose = useCallback(() => {
    setIsSlashMenuForceClosed(true);
  }, []);

  // URL detection for #URL integration
  const detectedUrls = useMemo(() => {
    if (!enableUrlFetch) return [];
    const urlPattern = /(?:^|\s)#(https?:\/\/[^\s]+)/g;
    const matches: Array<{ raw: string; url: string }> = [];
    let match;
    while ((match = urlPattern.exec(input)) !== null) {
      const url = match[1];
      if (url) matches.push({ raw: match[0].trim(), url });
    }
    return matches;
  }, [input, enableUrlFetch]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onSelectFiles(Array.from(e.target.files));
    }
    // Reset value to allow same file selection again
    e.target.value = "";
  };

  // Determine if we should show inline suggestion
  const showInlineSuggestion =
    enableInlineSuggestions &&
    !isProcessing &&
    input.trim().length > 0 &&
    !!inlineSuggestion &&
    inlineSuggestion.length > 0;

  // Handle keyboard shortcuts (Enter to send, Shift+Enter for newline, Tab to accept suggestion)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Tab to accept inline suggestion
      if (e.key === "Tab" && enableInlineSuggestions && inlineSuggestion) {
        e.preventDefault();
        onAcceptSuggestion?.(inlineSuggestion);
        return;
      }

      // Escape to dismiss inline suggestion
      if (e.key === "Escape" && enableInlineSuggestions && inlineSuggestion) {
        e.preventDefault();
        onDismissSuggestion?.();
        return;
      }

      // Submit handling - respects submitOnEnter preference
      if (e.key === "Enter") {
        const shouldSubmit = submitOnEnter
          ? !e.shiftKey // Enter to submit (ChatGPT style)
          : e.ctrlKey || e.metaKey; // Ctrl/Cmd+Enter to submit (legacy)

        if (shouldSubmit) {
          e.preventDefault();
          if (input.trim().length > 0 && !isProcessing) {
            onSubmit();
          }
        }
        // Note: when submitOnEnter=false and no modifier key, Enter creates newline (default behavior)
      }
    },
    [
      input,
      isProcessing,
      onSubmit,
      enableInlineSuggestions,
      inlineSuggestion,
      onAcceptSuggestion,
      onDismissSuggestion,
      submitOnEnter,
    ],
  );

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200); // Max 200px height
      textarea.style.height = `${newHeight}px`;
    }
  }, [input]);

  const canSend = input.trim().length > 0 && !isProcessing;

  // Get current model info
  const currentModel = availableModels.find((m) => m.id === selectedModel);

  // Handle model selection
  const handleModelSelect = (modelId: string) => {
    if (onModelChange) {
      onModelChange(modelId);
    }
    setIsModelDropdownOpen(false);
  };

  return (
    <div
      data-testid="chat-input-container"
      className="w-full px-4 pb-6 pt-4 max-w-4xl mx-auto"
      {...dragHandlers}
    >
      {/* Drop zone overlay */}
      {isDragging && (
        <div
          data-testid="drop-zone-overlay"
          className="absolute inset-0 bg-blue-500/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center z-10"
        >
          <p className="text-blue-600 font-medium">Drop files here</p>
        </div>
      )}

      {/* Attached files preview */}
      {uploadFiles.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {uploadFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 px-3 py-1.5 rounded-full text-sm border border-gray-200 dark:border-gray-700"
            >
              <span className="truncate max-w-[150px]">{file.file.name}</span>
              {file.status === "uploading" && (
                <span className="text-blue-500 text-xs">{file.progress}%</span>
              )}
              {file.status === "error" && (
                <span className="text-red-500 text-xs">{file.error}</span>
              )}
              <button
                type="button"
                onClick={() => onRemoveFile(file.id)}
                aria-label="Remove file"
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Error messages */}
      {voiceError && (
        <p className="text-red-500 text-sm mb-2 px-1">{voiceError}</p>
      )}
      {fileError && (
        <p className="text-red-500 text-sm mb-2 px-1">{fileError}</p>
      )}

      {/* Voice input browser compatibility banner */}
      {!isVoiceSupported && !isVoiceBannerDismissed && (
        <div
          data-testid="voice-not-supported-banner"
          className="flex items-center justify-between gap-3 mb-3 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-sm"
        >
          <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200">
            <Mic className="w-4 h-4 flex-shrink-0" />
            <span>
              Voice input is not supported in this browser. For best experience,
              use Chrome, Edge, or Safari.
            </span>
          </div>
          <button
            type="button"
            onClick={() => setIsVoiceBannerDismissed(true)}
            aria-label="Dismiss"
            className="p-1 text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Recording indicator */}
      {isListening && (
        <div
          data-testid="recording-indicator"
          className="flex items-center gap-2 mb-3 text-red-500 px-1"
        >
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-sm">Listening...</span>
        </div>
      )}

      {/* URL Fetch Indicator - detected URLs */}
      {enableUrlFetch && detectedUrls.length > 0 && (
        <div
          data-testid="url-fetch-indicator"
          className="flex flex-wrap items-center gap-2 mb-3 px-1"
        >
          {detectedUrls.map((detected) => {
            const isLoading = urlFetchLoading.includes(detected.url);
            const fetched = fetchedUrls.find((f) => f.url === detected.url);
            const hostname = new URL(detected.url).hostname;

            if (isLoading) {
              return (
                <span
                  key={detected.url}
                  data-testid="url-fetch-loading"
                  className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full"
                >
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>{hostname}</span>
                </span>
              );
            }

            if (fetched) {
              return (
                <span
                  key={detected.url}
                  data-testid="url-fetched-badge"
                  className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full"
                >
                  <Check className="w-3 h-3" />
                  <span>{fetched.title || hostname}</span>
                  {onRemoveFetchedUrl && (
                    <button
                      type="button"
                      onClick={() => onRemoveFetchedUrl(detected.url)}
                      aria-label={`Remove ${hostname}`}
                      className="ml-1 p-0.5 hover:bg-green-200 dark:hover:bg-green-800 rounded-full transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              );
            }

            // Pending - not yet fetched
            return (
              <span
                key={detected.url}
                className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full"
              >
                <span>{hostname}</span>
              </span>
            );
          })}
        </div>
      )}

      {/* Model Selector */}
      {showModelSelector && (
        <div data-testid="model-selector" className="mb-3 relative">
          <button
            type="button"
            data-testid="model-selector-button"
            disabled={isProcessing}
            onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
            aria-label="Select AI model"
            aria-haspopup="listbox"
            aria-expanded={isModelDropdownOpen}
            aria-controls="model-selector-listbox"
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <span className="font-medium">
              {selectedModel || "Select model"}
            </span>
            {currentModel && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                {currentModel.provider}
              </span>
            )}
            <ChevronDown
              className={`w-4 h-4 transition-transform ${isModelDropdownOpen ? "rotate-180" : ""}`}
              aria-hidden="true"
            />
          </button>

          {/* Dropdown menu */}
          {isModelDropdownOpen && (
            <div
              id="model-selector-listbox"
              role="listbox"
              aria-label="Available AI models"
              className="absolute z-20 mt-1 w-64 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg"
            >
              {availableModels.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  role="option"
                  aria-selected={model.id === selectedModel}
                  data-testid={`model-option-${model.id}`}
                  onClick={() => handleModelSelect(model.id)}
                  className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:bg-blue-50 dark:focus:bg-blue-900/30"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{model.name}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                      {model.provider}
                    </span>
                  </div>
                  {model.id === selectedModel && (
                    <Check
                      className="w-4 h-4 text-green-500"
                      aria-hidden="true"
                    />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main input form */}
      <form
        onSubmit={handleSubmit}
        data-testid="chat-input-form"
        className="relative"
      >
        {/* Slash Command Menu - appears above input when typing "/" */}
        {slashCommands && (
          <SlashCommandMenu
            commands={slashCommands}
            onSelect={handleSlashCommandSelect}
            onClose={handleSlashMenuClose}
            isOpen={showSlashMenu}
            filter={slashCommandFilter}
          />
        )}

        {/* RichText Mode: Pill container with RichTextInput */}
        {enableRichTextMode ? (
          <div
            data-testid="pill-container"
            className="relative flex flex-col bg-white dark:bg-gray-800/95 rounded-2xl shadow-lg ring-1 ring-gray-200/50 dark:ring-gray-700/50 backdrop-blur-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-chat-accent/50 focus-within:shadow-xl"
          >
            {/* RichTextInput area */}
            <div data-testid="rich-text-input" className="px-3 pt-3">
              <RichTextInput
                value={input}
                onChange={onInputChange}
                onSubmit={() => onSubmit()}
                placeholder="Type your message..."
                disabled={isProcessing}
                submitOnEnter={submitOnEnter}
                enableInlineSuggestions={enableInlineSuggestions}
                inlineSuggestion={inlineSuggestion}
                onAcceptSuggestion={onAcceptSuggestion}
                onDismissSuggestion={onDismissSuggestion}
                isSuggestionLoading={isSuggestionLoading}
                mentionOptions={mentionOptions}
                maxLength={richTextMaxLength}
                className="w-full border-0 bg-transparent focus:ring-0"
              />
            </div>

            {/* Controls row - OUTSIDE RichTextInput */}
            <div className="flex items-center justify-between px-3 pb-3 border-t border-gray-100 dark:border-gray-700 pt-2 mt-2">
              {/* Left: File upload, Voice */}
              <div className="flex items-center gap-2">
                {/* Hidden file input */}
                <input
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  className="sr-only"
                  aria-hidden="true"
                  id="chat-file-input-rich"
                />
                <button
                  type="button"
                  disabled={isProcessing || isUploading}
                  aria-label="Attach file"
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  onClick={() =>
                    document.getElementById("chat-file-input-rich")?.click()
                  }
                >
                  <Plus className="w-5 h-5" />
                </button>

                {isVoiceSupported && (
                  <button
                    type="button"
                    onClick={isListening ? onStopListening : onStartListening}
                    disabled={isProcessing}
                    aria-label={
                      isListening ? "Stop voice input" : "Start voice input"
                    }
                    className={`p-2 rounded-lg transition-colors ${
                      isListening
                        ? "text-red-500 bg-red-50 dark:bg-red-900/20"
                        : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    } disabled:opacity-50`}
                  >
                    {isListening ? (
                      <MicOff className="w-5 h-5" />
                    ) : (
                      <Mic className="w-5 h-5" />
                    )}
                  </button>
                )}

                {/* Reasoning Effort Selector in controls row (RichText mode only) */}
                {modelSupportsThinking &&
                  enableThinking &&
                  onReasoningEffortChange && (
                    <ReasoningEffortSelector
                      value={reasoningEffort}
                      onChange={onReasoningEffortChange}
                      disabled={isProcessing}
                      modelSupportsThinking={modelSupportsThinking}
                      compact={true}
                    />
                  )}
              </div>

              {/* Right: Send/Stop button */}
              <div className="flex items-center gap-2">
                {isStreaming && onStopStreaming ? (
                  <button
                    type="button"
                    onClick={onStopStreaming}
                    aria-label="Stop generating"
                    className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                    data-testid="stop-streaming-button"
                  >
                    <Square className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!canSend}
                    aria-label="Send"
                    data-testid="send-button"
                    className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isProcessing ? (
                      <Loader2
                        className="w-5 h-5 animate-spin"
                        data-testid="send-button-loading"
                      />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Legacy Mode: Plain textarea with existing styling */
          <div
            data-testid="input-wrapper"
            className="flex items-end gap-2 p-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all"
          >
            {/* Left controls - Attachment button */}
            <div className="flex items-center gap-1 pb-1">
              {/* Hidden file input */}
              <input
                type="file"
                multiple
                onChange={handleFileChange}
                className="sr-only"
                aria-hidden="true"
                id="chat-file-input"
              />
              <button
                type="button"
                disabled={isProcessing || isUploading}
                aria-label="Attach file"
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                onClick={() =>
                  document.getElementById("chat-file-input")?.click()
                }
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>

            {/* Textarea with inline suggestion overlay - expandable multi-line input */}
            <div className="flex-1 relative">
              {/* Ghost text overlay for inline AI suggestions */}
              {showInlineSuggestion && (
                <div
                  data-testid="inline-suggestion-overlay"
                  className="absolute inset-0 px-2 py-2 pointer-events-none overflow-hidden whitespace-pre-wrap break-words min-h-[40px]"
                  aria-hidden="true"
                >
                  {/* Invisible text to position the ghost text after input */}
                  <span className="invisible">{input}</span>
                  {/* Ghost text suggestion */}
                  <span
                    data-testid="inline-suggestion"
                    className="text-gray-400 dark:text-gray-500"
                  >
                    {inlineSuggestion}
                  </span>
                </div>
              )}

              {/* Loading indicator for suggestion fetch */}
              {enableInlineSuggestions &&
                isSuggestionLoading &&
                input.trim().length > 0 && (
                  <div
                    data-testid="suggestion-loading"
                    className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                  >
                    <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  </div>
                )}

              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => onInputChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                disabled={isProcessing}
                rows={1}
                aria-label="Message input"
                className="w-full px-2 py-2 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset rounded-lg disabled:opacity-50 min-h-[40px] max-h-[200px]"
              />

              {/* Hint text for accepting suggestion */}
              {showInlineSuggestion && (
                <div
                  data-testid="suggestion-hint"
                  className="absolute -bottom-5 left-2 text-xs text-gray-400 dark:text-gray-500"
                >
                  Press Tab to accept
                </div>
              )}
            </div>

            {/* Right controls - Voice & Send */}
            <div className="flex items-center gap-1 pb-1">
              {isVoiceSupported && (
                <button
                  type="button"
                  onClick={isListening ? onStopListening : onStartListening}
                  disabled={isProcessing}
                  aria-label={
                    isListening ? "Stop voice input" : "Start voice input"
                  }
                  className={`p-2 rounded-lg transition-colors ${
                    isListening
                      ? "text-red-500 bg-red-50 dark:bg-red-900/20"
                      : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  } disabled:opacity-50`}
                >
                  {isListening ? (
                    <MicOff className="w-5 h-5" />
                  ) : (
                    <Mic className="w-5 h-5" />
                  )}
                </button>
              )}

              {/* Stop button when streaming, otherwise Send button */}
              {isStreaming && onStopStreaming ? (
                <button
                  type="button"
                  onClick={onStopStreaming}
                  aria-label="Stop generating"
                  className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  data-testid="stop-streaming-button"
                >
                  <Square className="w-5 h-5" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!canSend}
                  aria-label="Send"
                  data-testid="send-button"
                  className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessing ? (
                    <Loader2
                      className="w-5 h-5 animate-spin"
                      data-testid="send-button-loading"
                    />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </form>

      {/* Reasoning Effort Selector and Thinking Toggle - only in Legacy mode */}
      {/* In RichText mode, ReasoningEffortSelector is in the controls row; thinking toggle is hidden (product approved) */}
      {modelSupportsThinking && !enableRichTextMode && (
        <div className="flex items-center justify-between mt-3 px-1">
          {/* Enable Thinking Toggle */}
          {onEnableThinkingChange && (
            <button
              type="button"
              data-testid="enable-thinking-toggle"
              onClick={() => onEnableThinkingChange(!enableThinking)}
              aria-label={
                enableThinking
                  ? "Disable extended thinking"
                  : "Enable extended thinking"
              }
              aria-pressed={enableThinking}
              className={`flex items-center gap-2 text-xs transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500 rounded-lg p-1 ${
                enableThinking
                  ? "text-violet-600 dark:text-violet-400"
                  : "text-gray-400 dark:text-gray-500"
              }`}
            >
              <span
                className={`w-8 h-4 rounded-full transition-colors flex items-center px-0.5 ${
                  enableThinking
                    ? "bg-violet-600 justify-end"
                    : "bg-gray-300 dark:bg-gray-600 justify-start"
                }`}
              >
                <span className="w-3 h-3 bg-white rounded-full shadow" />
              </span>
              <span>Extended Thinking</span>
            </button>
          )}

          {/* Reasoning Effort Selector - only when thinking is enabled */}
          {enableThinking && onReasoningEffortChange && (
            <ReasoningEffortSelector
              value={reasoningEffort}
              onChange={onReasoningEffortChange}
              disabled={isProcessing}
              modelSupportsThinking={modelSupportsThinking}
              compact={true}
            />
          )}
        </div>
      )}

      {/* Hint text */}
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
