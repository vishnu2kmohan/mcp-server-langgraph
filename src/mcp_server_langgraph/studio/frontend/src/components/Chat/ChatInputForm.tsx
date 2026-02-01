/**
 * ChatInputForm Component
 *
 * @deprecated Use ChatInput component instead for new development.
 * ChatInput provides a consolidated interface with:
 * - Model settings dropdown (brain icon) with model selector + thinking controls
 * - Single bottom controls row: [+] [🧠 Model▼] [Tools▼] [KB▼] [🎤] [Send/Stop]
 * - Keyboard shortcuts for formatting (no toolbar)
 * - Cleaner, more maintainable codebase
 *
 * This component is kept for backwards compatibility with ConnectedChatInputForm.
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
import {
  KnowledgeBaseFocus,
  type KBFocusMode,
  type KBStatus,
} from "./KnowledgeBaseFocus";
import { ToolSelector, type ToolOption } from "./ToolSelector";
import type { ToolSelectionMode } from "@/types/tools";

import { Button, Input, Textarea } from "@/components/UI";
import { MODEL_LIFECYCLE_BADGE_STYLES } from "../../utils/colors";
import type { ModelStatus } from "@/types";

// Re-export SlashCommand for external use
export type { SlashCommand };

// Re-export ModelStatus from centralized types for backwards compatibility
export type { ModelStatus } from "@/types";

/** Model option for model selector dropdown */
export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  /** Whether this model supports extended thinking (Claude Opus 4.5, Gemini 2.5, etc.) */
  supportsThinking?: boolean;
  /** Whether this model supports vision/image input */
  supportsVision?: boolean;
  /** Whether this model supports tool/function calling */
  supportsTools?: boolean;
  /** Model lifecycle status (current, preview, legacy, deprecated) */
  status?: ModelStatus;
  /** Sunset date for deprecated models (ISO 8601 format: YYYY-MM-DD) */
  sunsetDate?: string;
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
  /** Whether models are currently loading from API */
  isModelsLoading?: boolean;
  /** Recently used model IDs (most recent first) - displayed in a separate section at top of dropdown */
  recentModels?: string[];
  /** Whether to show search input in model dropdown */
  enableModelSearch?: boolean;
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
  // Knowledge Base Focus props (Perplexity-style Focus mode)
  /** Whether to show the KB Focus dropdown */
  showKBFocus?: boolean;
  /** Current KB focus mode (all, kb_only, web_only, none) */
  kbFocusValue?: KBFocusMode;
  /** Callback when KB focus mode changes */
  onKBFocusChange?: (mode: KBFocusMode) => void;
  /** KB status for indicator (ready, misconfigured, unavailable) */
  kbStatus?: KBStatus;
  /** KB status message for tooltip (e.g., config guidance) */
  kbStatusMessage?: string;
  /** Whether to render KB Focus in compact mode (icon only) */
  kbFocusCompact?: boolean;
  // Tool Selection props (Manual Tool Selection)
  /** Whether to show the tool selector */
  showToolSelector?: boolean;
  /** Currently selected tool names (for manual mode) */
  selectedTools?: string[];
  /** Callback when tool selection changes */
  onSelectedToolsChange?: (tools: string[]) => void;
  /** Current tool selection mode (auto/manual/none) */
  toolSelectionMode?: ToolSelectionMode;
  /** Callback when tool selection mode changes */
  onToolSelectionModeChange?: (mode: ToolSelectionMode) => void;
  /** Available tools for manual selection */
  availableTools?: ToolOption[];
  /** Whether tools are currently loading */
  isToolsLoading?: boolean;
  /** Whether to render tool selector in compact mode */
  toolSelectorCompact?: boolean;
  // Cursor position tracking (for WebSocket suggestions)
  /** Callback when cursor position changes in the input */
  onCursorPositionChange?: (position: number) => void;
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
  isModelsLoading = false,
  recentModels = [],
  enableModelSearch = false,
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
  // KB Focus props
  showKBFocus = false,
  kbFocusValue = "all",
  onKBFocusChange,
  kbStatus,
  kbStatusMessage,
  kbFocusCompact = false,
  // Tool Selection props
  showToolSelector = false,
  selectedTools = [],
  onSelectedToolsChange,
  toolSelectionMode = "auto",
  onToolSelectionModeChange,
  availableTools = [],
  isToolsLoading = false,
  toolSelectorCompact = false,
  // Cursor position tracking
  onCursorPositionChange,
}: ChatInputFormProps) {
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [focusedModelIndex, setFocusedModelIndex] = useState(-1);
  const [isVoiceBannerDismissed, setIsVoiceBannerDismissed] = useState(false);
  const [isSlashMenuForceClosed, setIsSlashMenuForceClosed] = useState(false);
  const [modelSearchQuery, setModelSearchQuery] = useState("");
  const [isDeprecationWarningDismissed, setIsDeprecationWarningDismissed] =
    useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelButtonRef = useRef<HTMLButtonElement>(null);
  const modelSearchInputRef = useRef<HTMLInputElement>(null);

  // Reset focused index and search query when dropdown closes
  // When opening, start with no focus (-1) - arrow keys will focus first/last
  useEffect(() => {
    if (!isModelDropdownOpen) {
      setFocusedModelIndex(-1);
      setModelSearchQuery("");
    } else if (enableModelSearch) {
      // Auto-focus search input when dropdown opens
      // Use setTimeout to ensure DOM is rendered
      setTimeout(() => {
        modelSearchInputRef.current?.focus();
      }, 0);
    }
  }, [isModelDropdownOpen, enableModelSearch]);

  // Reset deprecation warning dismissed state when selected model changes
  useEffect(() => {
    setIsDeprecationWarningDismissed(false);
  }, [selectedModel]);

  // Handle model dropdown keyboard navigation
  const handleModelDropdownKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>) => {
      if (!showModelSelector) return;

      switch (e.key) {
        case "Enter":
        case " ":
          e.preventDefault();
          if (!isModelDropdownOpen) {
            // Open dropdown
            setIsModelDropdownOpen(true);
          } else if (
            focusedModelIndex >= 0 &&
            focusedModelIndex < availableModels.length
          ) {
            // Select focused model
            const selectedModelOption = availableModels[focusedModelIndex];
            if (selectedModelOption) {
              onModelChange?.(selectedModelOption.id);
              setIsModelDropdownOpen(false);
            }
          }
          break;
        case "Escape":
          e.preventDefault();
          setIsModelDropdownOpen(false);
          break;
        case "ArrowDown":
          e.preventDefault();
          if (!isModelDropdownOpen) {
            setIsModelDropdownOpen(true);
          } else {
            // Navigate down with wrap-around
            // If no focus yet (-1), start at first option (0)
            setFocusedModelIndex((prev) => {
              if (prev === -1) return 0;
              return prev >= availableModels.length - 1 ? 0 : prev + 1;
            });
          }
          break;
        case "ArrowUp":
          e.preventDefault();
          if (!isModelDropdownOpen) {
            setIsModelDropdownOpen(true);
          } else {
            // Navigate up with wrap-around
            // If no focus yet (-1), start at last option
            setFocusedModelIndex((prev) => {
              if (prev === -1) return availableModels.length - 1;
              return prev <= 0 ? availableModels.length - 1 : prev - 1;
            });
          }
          break;
        case "Home":
          e.preventDefault();
          if (isModelDropdownOpen) {
            setFocusedModelIndex(0);
          }
          break;
        case "End":
          e.preventDefault();
          if (isModelDropdownOpen) {
            setFocusedModelIndex(availableModels.length - 1);
          }
          break;
      }
    },
    [
      showModelSelector,
      isModelDropdownOpen,
      focusedModelIndex,
      availableModels,
      onModelChange,
    ],
  );

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

  // Get validated recent models (filter invalid IDs and limit to 3)
  const validatedRecentModels = useMemo(() => {
    return recentModels
      .map((id) => availableModels.find((m) => m.id === id))
      .filter((model): model is ModelOption => model !== undefined)
      .slice(0, 3);
  }, [recentModels, availableModels]);

  // Status priority for sorting: current > preview > legacy > deprecated
  // Models without status are treated as "current" (backward compatibility)
  const statusPriority: Record<string, number> = useMemo(
    () => ({
      current: 0,
      preview: 1,
      legacy: 2,
      deprecated: 3,
    }),
    [],
  );

  // Sort models by status priority, then alphabetically by name
  const sortModelsByStatus = useCallback(
    (models: ModelOption[]): ModelOption[] => {
      return [...models].sort((a, b) => {
        // Get status priority (undefined status treated as current)
        const priorityA = statusPriority[a.status ?? "current"] ?? 0;
        const priorityB = statusPriority[b.status ?? "current"] ?? 0;

        // Sort by status priority first
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }

        // Within same status, sort alphabetically by name
        return a.name.localeCompare(b.name);
      });
    },
    [statusPriority],
  );

  // Filter models based on search query and sort by status
  const filteredModels = useMemo(() => {
    let models = availableModels;

    if (modelSearchQuery.trim()) {
      const query = modelSearchQuery.toLowerCase().trim();
      models = availableModels.filter(
        (model) =>
          model.name.toLowerCase().includes(query) ||
          model.provider.toLowerCase().includes(query) ||
          model.id.toLowerCase().includes(query),
      );
    }

    // Always sort by status priority
    return sortModelsByStatus(models);
  }, [availableModels, modelSearchQuery, sortModelsByStatus]);

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
          className="absolute inset-0 bg-primary-4 border-2 border-dashed border-primary-7 rounded-lg flex items-center justify-center z-10"
        >
          <p className="text-primary-11 font-medium">Drop files here</p>
        </div>
      )}
      {/* Attached files preview */}
      {uploadFiles.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {uploadFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 bg-neutral-2 px-3 py-1.5 rounded-full text-sm border border-neutral-5"
            >
              <span className="truncate max-w-[150px]">{file.file.name}</span>
              {file.status === "uploading" && (
                <span className="text-primary-9 text-xs">{file.progress}%</span>
              )}
              {file.status === "error" && (
                <span className="text-error-9 text-xs">{file.error}</span>
              )}
              <Button
                variant="danger"
                className="text-neutral-9 hover:text-error-9"
                type="button"
                onClick={() => onRemoveFile(file.id)}
                aria-label="Remove file"
              >
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}
      {/* Error messages */}
      {voiceError && (
        <p className="text-error-11 text-sm mb-2 px-1">{voiceError}</p>
      )}
      {fileError && (
        <p className="text-error-11 text-sm mb-2 px-1">{fileError}</p>
      )}
      {/* Voice input browser compatibility banner */}
      {!isVoiceSupported && !isVoiceBannerDismissed && (
        <div
          data-testid="voice-not-supported-banner"
          className="flex items-center justify-between gap-3 mb-3 px-3 py-2 bg-warning-3 border border-warning-6 rounded-lg text-sm"
        >
          <div className="flex items-center gap-2 text-warning-11">
            <Mic className="w-4 h-4 flex-shrink-0" />
            <span>
              Voice input is not supported in this browser. For best experience,
              use Chrome, Edge, or Safari.
            </span>
          </div>
          <Button
            variant="secondary"
            className="p-1 text-warning-9 hover:text-warning-11"
            type="button"
            onClick={() => setIsVoiceBannerDismissed(true)}
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}
      {/* Recording indicator */}
      {isListening && (
        <div
          data-testid="recording-indicator"
          className="flex items-center gap-2 mb-3 text-error-9 px-1"
        >
          <span className="w-2 h-2 bg-error-9 rounded-full animate-pulse" />
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
                  className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-primary-3 text-primary-11 rounded-full"
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
                  className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-success-3 text-success-11 rounded-full"
                >
                  <Check className="w-3 h-3" />
                  <span>{fetched.title || hostname}</span>
                  {onRemoveFetchedUrl && (
                    <Button
                      variant="success"
                      className="ml-1 p-0.5 hover:bg-success-4 rounded-full"
                      type="button"
                      onClick={() => onRemoveFetchedUrl(detected.url)}
                      aria-label={`Remove ${hostname}`}
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  )}
                </span>
              );
            }

            // Pending - not yet fetched
            return (
              <span
                key={detected.url}
                className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-neutral-2 text-neutral-11 rounded-full"
              >
                <span>{hostname}</span>
              </span>
            );
          })}
        </div>
      )}
      {/* Model Deprecation Warning Banner */}
      {showModelSelector &&
        currentModel?.status === "deprecated" &&
        !isDeprecationWarningDismissed && (
          <div
            data-testid="deprecation-warning-banner"
            role="alert"
            className="flex items-center justify-between gap-3 mb-3 px-3 py-2 bg-warning-3 border border-warning-6 rounded-lg text-sm text-warning-11"
          >
            <div className="flex items-center gap-2">
              <span className="font-medium">{currentModel.name}</span>
              <span>is deprecated and will be retired on</span>
              <span className="font-medium">
                {currentModel.sunsetDate
                  ? new Date(currentModel.sunsetDate).toLocaleDateString(
                      "en-US",
                      { month: "long", day: "numeric", year: "numeric" },
                    )
                  : "an unspecified date"}
              </span>
            </div>
            <Button
              variant="secondary"
              className="p-1 text-warning-9 hover:text-warning-11"
              type="button"
              onClick={() => setIsDeprecationWarningDismissed(true)}
              aria-label="Dismiss deprecation warning"
              data-testid="deprecation-warning-dismiss"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}
      {/* Model Selector */}
      {showModelSelector && (
        <div data-testid="model-selector" className="mb-3 relative">
          <Button
            variant="secondary"
            className="flex px-3 py-1.5 text-sm rounded-lg border border-neutral-5 bg-neutral-1 hover:bg-neutral-1 focus:ring-primary-7"
            ref={modelButtonRef}
            type="button"
            data-testid="model-selector-button"
            disabled={isProcessing || isModelsLoading}
            onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
            onKeyDown={handleModelDropdownKeyDown}
            aria-label="Select AI model"
            aria-haspopup="listbox"
            aria-expanded={isModelDropdownOpen}
            aria-controls="model-selector-listbox"
            aria-busy={isModelsLoading}
            aria-activedescendant={
              isModelDropdownOpen && focusedModelIndex >= 0
                ? `model-option-${availableModels[focusedModelIndex]?.id}`
                : undefined
            }
          >
            {isModelsLoading ? (
              <>
                <span
                  data-testid="model-selector-loading"
                  className="w-4 h-4 border-2 border-neutral-5 border-t-primary-9 rounded-full animate-spin"
                  aria-hidden="true"
                />
                <span className="font-medium text-neutral-10">
                  Loading models...
                </span>
              </>
            ) : (
              <>
                <span className="font-medium">
                  {selectedModel || "Select model"}
                </span>
                {currentModel && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                    {currentModel.provider}
                  </span>
                )}
                {/* Capability badge for selected model (show thinking indicator) */}
                {currentModel?.supportsThinking && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-insight-3 text-insight-11">
                    Thinking
                  </span>
                )}
                {/* Status badge for selected model (preview, legacy, deprecated) */}
                {currentModel?.status === "preview" && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-info-3 text-info-11">
                    Preview
                  </span>
                )}
                {currentModel?.status === "legacy" && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-warning-3 text-warning-11">
                    Legacy
                  </span>
                )}
                {currentModel?.status === "deprecated" && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-error-3 text-error-11">
                    Deprecated
                  </span>
                )}
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${isModelDropdownOpen ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              </>
            )}
          </Button>

          {/* Dropdown menu */}
          {isModelDropdownOpen && (
            <div
              id="model-selector-listbox"
              role="listbox"
              aria-label="Available AI models"
              className="absolute z-10 mt-1 w-64 py-1 bg-neutral-1 border border-neutral-5 rounded-lg shadow-lg max-h-80 overflow-y-auto"
            >
              {/* Search Input */}
              {enableModelSearch && (
                <div className="px-2 pb-2 pt-1">
                  <Input
                    className="px-3 py-1.5 text-sm bg-neutral-1 focus:ring-primary-7 placeholder-neutral-9"
                    ref={modelSearchInputRef}
                    data-testid="model-search-input"
                    placeholder="Search models..."
                    value={modelSearchQuery}
                    onChange={(e) => setModelSearchQuery(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => {
                      // Prevent dropdown from closing on Enter
                      if (e.key === "Enter") {
                        e.preventDefault();
                        e.stopPropagation();
                      }
                    }}
                  />
                </div>
              )}

              {/* Recent Models Section (hidden when searching) */}
              {validatedRecentModels.length > 0 && !modelSearchQuery && (
                <div data-testid="recent-models-section">
                  <div className="px-3 py-1.5 text-xs font-semibold text-neutral-10 uppercase tracking-wider">
                    Recent
                  </div>
                  {validatedRecentModels.map((model) => (
                    <Button
                      variant="ghost"
                      className="w-full flex justify-between px-3 py-2 text-sm hover:bg-neutral-2 focus:bg-primary-3"
                      key={`recent-${model.id}`}
                      type="button"
                      role="option"
                      aria-selected={model.id === selectedModel}
                      data-testid={`recent-model-option-${model.id}`}
                      onClick={() => handleModelSelect(model.id)}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{model.name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                          {model.provider}
                        </span>
                      </div>
                      {model.id === selectedModel && (
                        <Check
                          className="w-4 h-4 text-success-9"
                          aria-hidden="true"
                        />
                      )}
                    </Button>
                  ))}
                  {/* Divider between recent and all models */}
                  <div className="border-t border-neutral-5 my-1" />
                </div>
              )}

              {/* All Models Section Header (only shown when recent models exist and not searching) */}
              {validatedRecentModels.length > 0 && !modelSearchQuery && (
                <div className="px-3 py-1.5 text-xs font-semibold text-neutral-10 uppercase tracking-wider">
                  All Models
                </div>
              )}

              {/* No Models Found Message */}
              {filteredModels.length === 0 && modelSearchQuery && (
                <div className="px-3 py-4 text-sm text-neutral-10 text-center">
                  No models found
                </div>
              )}

              {/* All Models List (filtered when searching) */}
              {filteredModels.map((model, index) => (
                <Button
                  variant="ghost"
                  className="w-full flex flex-col px-3 py-2 text-sm hover:bg-neutral-2 focus:bg-primary-3"
                  key={model.id}
                  id={`model-option-${model.id}`}
                  type="button"
                  role="option"
                  aria-selected={model.id === selectedModel}
                  data-testid={`model-option-${model.id}`}
                  onClick={() => handleModelSelect(model.id)}
                  onMouseEnter={() => setFocusedModelIndex(index)}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                        {model.provider}
                      </span>
                    </div>
                    {model.id === selectedModel && (
                      <Check
                        className="w-4 h-4 text-success-9"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  {/* Capability badges row */}
                  {(model.supportsThinking ||
                    model.supportsVision ||
                    model.supportsTools) && (
                    <div className="flex items-center gap-1.5">
                      {model.supportsThinking && (
                        <span
                          data-testid={`capability-badge-thinking-${model.id}`}
                          className="text-xs px-1.5 py-0.5 rounded bg-insight-3 text-insight-11"
                        >
                          Thinking
                        </span>
                      )}
                      {model.supportsVision && (
                        <span
                          data-testid={`capability-badge-vision-${model.id}`}
                          className="text-xs px-1.5 py-0.5 rounded bg-primary-3 text-primary-11"
                        >
                          Vision
                        </span>
                      )}
                      {model.supportsTools && (
                        <span
                          data-testid={`capability-badge-tools-${model.id}`}
                          className="text-xs px-1.5 py-0.5 rounded bg-success-3 text-success-11"
                        >
                          Tools
                        </span>
                      )}
                    </div>
                  )}
                  {/* Status badge (preview, legacy, deprecated - not shown for current) */}
                  {model.status === "preview" && (
                    <span
                      data-testid={`status-badge-preview-${model.id}`}
                      className={`text-xs px-1.5 py-0.5 rounded ${MODEL_LIFECYCLE_BADGE_STYLES.preview}`}
                    >
                      Preview
                    </span>
                  )}
                  {model.status === "legacy" && (
                    <span
                      data-testid={`status-badge-legacy-${model.id}`}
                      className={`text-xs px-1.5 py-0.5 rounded ${MODEL_LIFECYCLE_BADGE_STYLES.legacy}`}
                    >
                      Legacy
                    </span>
                  )}
                  {model.status === "deprecated" && (
                    <div className="flex items-center gap-1.5">
                      <span
                        data-testid={`status-badge-deprecated-${model.id}`}
                        className={`text-xs px-1.5 py-0.5 rounded ${MODEL_LIFECYCLE_BADGE_STYLES.deprecated}`}
                      >
                        Deprecated
                      </span>
                      {model.sunsetDate && (
                        <span className="text-xs text-neutral-10">
                          Sunset{" "}
                          {new Date(model.sunsetDate).toLocaleDateString(
                            "en-US",
                            { month: "short", year: "numeric" },
                          )}
                        </span>
                      )}
                    </div>
                  )}
                </Button>
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
            className="relative flex flex-col bg-neutral-1 rounded-2xl shadow-lg ring-1 ring-neutral-a6 backdrop-blur-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-chat-accent/50 focus-within:shadow-xl"
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
                onCursorPositionChange={onCursorPositionChange}
                className="w-full border-0 bg-transparent focus:ring-0"
              />
            </div>

            {/* Controls row - OUTSIDE RichTextInput */}
            <div className="flex items-center justify-between px-3 pb-3 border-t border-neutral-5 pt-2 mt-2">
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
                <Button
                  variant="secondary"
                  className="p-2 text-neutral-9 hover:text-neutral-11 rounded-lg hover:bg-neutral-2"
                  type="button"
                  disabled={isProcessing || isUploading}
                  aria-label="Attach file"
                  onClick={() =>
                    document.getElementById("chat-file-input-rich")?.click()
                  }
                >
                  <Plus className="w-5 h-5" />
                </Button>

                {isVoiceSupported && (
                  <Button
                    variant="primary"
                    className="p-2 rounded-lg"
                    type="button"
                    onClick={isListening ? onStopListening : onStartListening}
                    disabled={isProcessing}
                    aria-label={
                      isListening ? "Stop voice input" : "Start voice input"
                    }
                  >
                    {isListening ? (
                      <MicOff className="w-5 h-5" />
                    ) : (
                      <Mic className="w-5 h-5" />
                    )}
                  </Button>
                )}

                {/* Knowledge Base Focus selector (Perplexity-style) */}
                {showKBFocus && onKBFocusChange && (
                  <KnowledgeBaseFocus
                    value={kbFocusValue}
                    onChange={onKBFocusChange}
                    disabled={isProcessing}
                    kbStatus={kbStatus}
                    kbStatusMessage={kbStatusMessage}
                    compact={kbFocusCompact}
                  />
                )}

                {/* Tool Selector (Manual Tool Selection) */}
                {showToolSelector &&
                  onSelectedToolsChange &&
                  onToolSelectionModeChange && (
                    <ToolSelector
                      selectedTools={selectedTools}
                      onSelectionChange={onSelectedToolsChange}
                      mode={toolSelectionMode}
                      onModeChange={onToolSelectionModeChange}
                      availableTools={availableTools}
                      isLoading={isToolsLoading}
                      disabled={isProcessing}
                      compact={toolSelectorCompact}
                    />
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
                  <Button
                    size="icon"
                    variant="danger"
                    className="p-2 bg-error-9 text-neutral-12 rounded-lg hover:bg-error-10"
                    type="button"
                    onClick={onStopStreaming}
                    aria-label="Stop generating"
                    data-testid="stop-streaming-button"
                  >
                    <Square className="w-5 h-5" />
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    className="p-2 bg-primary-9 text-neutral-12 rounded-lg hover:bg-primary-10"
                    type="submit"
                    disabled={!canSend}
                    aria-label="Send"
                    data-testid="send-button"
                  >
                    {isProcessing ? (
                      <Loader2
                        className="w-5 h-5 animate-spin"
                        data-testid="send-button-loading"
                      />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </Button>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Legacy Mode: Plain textarea with existing styling */
          <div
            data-testid="input-wrapper"
            className="flex items-end gap-2 p-2 bg-neutral-1 border border-neutral-5 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-primary-7 focus-within:border-transparent transition-all"
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
              <Button
                variant="secondary"
                className="p-2 text-neutral-9 hover:text-neutral-11 rounded-lg hover:bg-neutral-2"
                type="button"
                disabled={isProcessing || isUploading}
                aria-label="Attach file"
                onClick={() =>
                  document.getElementById("chat-file-input")?.click()
                }
              >
                <Plus className="w-5 h-5" />
              </Button>
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
                    className="text-neutral-9"
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
                    <Loader2 className="w-4 h-4 animate-spin text-neutral-9" />
                  </div>
                )}

              <Textarea
                size="sm"
                className="px-2 py-2 bg-transparent text-neutral-12 placeholder-neutral-9 resize-none focus:ring-primary-7 focus:ring-inset disabled:opacity-50 min-h-[40px] max-h-[200px]"
                ref={textareaRef}
                value={input}
                onChange={(e) => onInputChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onSelect={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  onCursorPositionChange?.(target.selectionStart);
                }}
                placeholder="Type your message..."
                disabled={isProcessing}
                rows={1}
                aria-label="Message input"
              />

              {/* Hint text for accepting suggestion */}
              {showInlineSuggestion && (
                <div
                  data-testid="suggestion-hint"
                  className="absolute -bottom-5 left-2 text-xs text-neutral-9"
                >
                  Press Tab to accept
                </div>
              )}
            </div>
            {/* Right controls - Voice & Send */}
            <div className="flex items-center gap-1 pb-1">
              {isVoiceSupported && (
                <Button
                  variant="primary"
                  className="p-2 rounded-lg"
                  type="button"
                  onClick={isListening ? onStopListening : onStartListening}
                  disabled={isProcessing}
                  aria-label={
                    isListening ? "Stop voice input" : "Start voice input"
                  }
                >
                  {isListening ? (
                    <MicOff className="w-5 h-5" />
                  ) : (
                    <Mic className="w-5 h-5" />
                  )}
                </Button>
              )}

              {/* Stop button when streaming, otherwise Send button */}
              {isStreaming && onStopStreaming ? (
                <Button
                  size="icon"
                  variant="danger"
                  className="p-2 bg-error-9 text-neutral-12 rounded-lg hover:bg-error-10"
                  type="button"
                  onClick={onStopStreaming}
                  aria-label="Stop generating"
                  data-testid="stop-streaming-button"
                >
                  <Square className="w-5 h-5" />
                </Button>
              ) : (
                <Button
                  variant="primary"
                  className="p-2 bg-primary-9 text-neutral-12 rounded-lg hover:bg-primary-10"
                  type="submit"
                  disabled={!canSend}
                  aria-label="Send"
                  data-testid="send-button"
                >
                  {isProcessing ? (
                    <Loader2
                      className="w-5 h-5 animate-spin"
                      data-testid="send-button-loading"
                    />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </Button>
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
            <Button
              variant="ghost"
              size="sm"
              className="flex text-xs focus:ring-insight-9 rounded-lg p-1"
              type="button"
              data-testid="enable-thinking-toggle"
              onClick={() => onEnableThinkingChange(!enableThinking)}
              aria-label={
                enableThinking
                  ? "Disable extended thinking"
                  : "Enable extended thinking"
              }
              aria-pressed={enableThinking}
            >
              <span
                className={`w-8 h-4 rounded-full transition-colors flex items-center px-0.5 ${
                  enableThinking
                    ? "bg-insight-10 justify-end"
                    : "bg-neutral-3 justify-start"
                }`}
              >
                <span className="w-3 h-3 bg-neutral-1 rounded-full shadow" />
              </span>
              <span>Extended Thinking</span>
            </Button>
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
      <p className="text-xs text-neutral-9 text-center mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
