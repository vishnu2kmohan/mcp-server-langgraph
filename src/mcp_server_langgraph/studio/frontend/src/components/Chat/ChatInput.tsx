/**
 * ChatInput Component
 *
 * Unified chat input component that consolidates ChatInputForm and RichTextInput.
 *
 * Layout (with PreferencesMenu):
 *   [+] [Mode: Default|Plan|Auto|Bypass] [🧠 Model▼] [⚙ Preferences] [🎤] [Send/Stop]
 *
 * Layout (without PreferencesMenu - legacy):
 *   [+] [Mode: Default|Plan|Auto|Bypass] [🧠 Model▼] [Tools▼] [KB▼] [🎤] [Send/Stop]
 *
 * Features:
 * - Execution mode SegmentedControl (Ctrl/Cmd+Shift+M to cycle)
 * - Model settings dropdown (brain icon) with model selector + thinking controls
 * - PreferencesMenu for consolidated settings (thinking, tools, KB focus)
 * - Keyboard shortcuts for formatting (Ctrl+B/I/`) - no toolbar
 * - File attachments with drag-and-drop
 * - Voice input
 * - Inline AI suggestions (ghost text)
 * - WCAG 2.1 AA accessibility
 */

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  KeyboardEvent,
  ChangeEvent,
} from "react";
import { motion, useReducedMotion } from "motion/react";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";
import {
  Send,
  Mic,
  MicOff,
  Square,
  Plus,
  Brain,
  ChevronDown,
  Check,
  Loader2,
  X,
  AlertTriangle,
  Search,
  Link,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import type { UploadFile, DragHandlers } from "../../hooks/useFileUpload";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import { ToolSelector, type ToolOption } from "./ToolSelector";
import type { ToolSelectionMode, ToolPreference } from "@/types/tools";
import { ExecutionModeIndicator } from "./ExecutionModeIndicator";
import { PreferencesMenu } from "./PreferencesMenu";
import type { KBFocusMode } from "./KnowledgeBaseFocus";

import { Button, Textarea, Input } from "@/components/UI";
import {
  SegmentedControl,
  SegmentedControlItem,
} from "@/components/UI/SegmentedControl";
import { ShieldCheck } from "lucide-react";
import { cn } from "../../utils/cn";
import type { ModelOption } from "@/types";
import { formatProviderDisplay } from "@/utils/modelDisplay";

// Re-export ModelOption for backwards compatibility
export type { ModelOption } from "@/types";

export interface MentionOption {
  type: "model" | "file" | "user";
  value: string;
  label?: string;
}

export interface FetchedUrl {
  url: string;
  title: string;
  content: string;
}

export interface SlashCommand {
  name: string;
  description: string;
  icon?: string;
}

export interface ChatInputProps {
  /** Controlled textarea value */
  value: string;
  /** Callback when text changes */
  onChange: (value: string) => void;
  /** Callback when message is submitted */
  onSubmit: () => void;
  /** Disabled state */
  disabled?: boolean;
  /** Whether response is currently streaming (for stop button) */
  isStreaming?: boolean;
  /** Callback to stop streaming response */
  onStopStreaming?: () => void;
  /** Auto-focus textarea on mount */
  autoFocus?: boolean;

  // Model settings props
  /** Whether to show the model settings dropdown */
  showModelSelector?: boolean;
  /** Currently selected model ID */
  selectedModel?: string;
  /** Available models for selection */
  availableModels?: ModelOption[];
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Whether the current model supports extended thinking */
  modelSupportsThinking?: boolean;
  /** Current reasoning effort level */
  reasoningEffort?: ReasoningEffortLevel;
  /** Callback when reasoning effort level changes */
  onReasoningEffortChange?: (level: ReasoningEffortLevel) => void;
  /** Whether models are loading */
  isModelsLoading?: boolean;

  // Tool selection props
  /** Whether to show the tool selector */
  showToolSelector?: boolean;
  /** Currently selected tool names */
  selectedTools?: string[];
  /** Callback when tool selection changes */
  onSelectedToolsChange?: (tools: string[]) => void;
  /** Current tool selection mode */
  toolSelectionMode?: ToolSelectionMode;
  /** Callback when tool selection mode changes */
  onToolSelectionModeChange?: (mode: ToolSelectionMode) => void;
  /** Available tools for manual selection */
  availableTools?: ToolOption[];

  // v7: Tool preference for native vs builtin execution
  /** Current tool preference (auto/native/builtin/mcp) */
  toolPreference?: ToolPreference;
  /** Callback when tool preference changes */
  onToolPreferenceChange?: (preference: ToolPreference) => void;

  // KB Focus props
  /** Whether to show the KB Focus dropdown */
  showKBFocus?: boolean;
  /** Current KB focus value */
  kbFocusValue?: string;
  /** Callback when KB focus changes */
  onKBFocusChange?: (mode: string) => void;

  // Voice input props
  /** Whether voice input is supported */
  isVoiceSupported?: boolean;
  /** Whether currently listening for voice */
  isListening?: boolean;
  /** Callback to start listening */
  onStartListening?: () => void;
  /** Callback to stop listening */
  onStopListening?: () => void;

  // Inline suggestions props
  /** Enable inline ghost text suggestions */
  enableInlineSuggestions?: boolean;
  /** Current inline suggestion text */
  inlineSuggestion?: string;
  /** Callback when user accepts suggestion (Tab key) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape key) */
  onDismissSuggestion?: () => void;

  // File upload props
  /** Uploaded files */
  uploadFiles?: UploadFile[];
  /** Callback to remove a file */
  onRemoveFile?: (id: string) => void;
  /** Callback when files are selected */
  onSelectFiles?: (files: File[]) => void;
  /** Accept multiple files */
  acceptMultipleFiles?: boolean;
  /** Whether dragging files over */
  isDragging?: boolean;
  /** Drag event handlers */
  dragHandlers?: DragHandlers;

  // Slash commands props
  /** Available slash commands */
  slashCommands?: SlashCommand[];
  /** Callback when a slash command is selected */
  onSlashCommandSelect?: (command: SlashCommand) => void;

  // P0: Error states
  /** Voice input error message */
  voiceError?: string;
  /** File upload error message */
  fileError?: string;

  // P0: Loading states
  /** Whether file upload is in progress */
  isUploading?: boolean;
  /** Whether suggestion is loading */
  isSuggestionLoading?: boolean;

  // P0: Submit behavior
  /**
   * Keyboard submit behavior
   * - true: Enter = submit, Shift+Enter = newline (default, ChatGPT style)
   * - false: Ctrl/Cmd+Enter = submit, Enter = newline
   */
  submitOnEnter?: boolean;

  // P0: Cursor position tracking
  /** Callback when cursor position changes (for WebSocket integration) */
  onCursorPositionChange?: (position: number) => void;

  // P1: Thinking toggle
  /** Whether thinking is enabled */
  enableThinking?: boolean;
  /** Callback when thinking toggle is changed */
  onEnableThinkingChange?: (enabled: boolean) => void;

  // P1: URL content fetch
  /** Enable URL content fetching */
  enableUrlFetch?: boolean;
  /** URLs currently being fetched */
  urlFetchLoading?: string[];
  /** Already fetched URLs with content */
  fetchedUrls?: FetchedUrl[];
  /** Callback to remove a fetched URL */
  onRemoveFetchedUrl?: (url: string) => void;

  // P2: Mentions system
  /** Mention options for autocomplete */
  mentionOptions?: MentionOption[];

  // P2: Recent models and search
  /** Recently used model IDs */
  recentModels?: string[];
  /** Enable model search in dropdown */
  enableModelSearch?: boolean;

  // P2: Character count
  /** Maximum character length */
  maxLength?: number;

  // P3: KB status
  /** KB status for indicator */
  kbStatus?: "ready" | "indexing" | "error" | "misconfigured";
  /** KB status message for tooltip */
  kbStatusMessage?: string;

  // P3: Tools loading
  /** Whether tools are loading */
  isToolsLoading?: boolean;

  // Execution mode props (Ctrl/Cmd+Shift+M toggle)
  /** Current execution mode */
  executionMode?: "default" | "plan" | "auto_accept" | "bypass";
  /** Callback to cycle execution mode (Ctrl/Cmd+Shift+M keyboard shortcut) */
  onCycleExecutionMode?: () => void;
  /** Callback when execution mode changes directly via SegmentedControl */
  onExecutionModeChange?: (
    mode: "default" | "plan" | "auto_accept" | "bypass",
  ) => void;
  /** Whether user has bypass permission (OpenFGA bypass_executor on system:global) */
  hasBypassPermission?: boolean;

  // Preferences menu props (consolidated settings)
  /** Whether to show the consolidated preferences menu */
  showPreferencesMenu?: boolean;
  /** Current KB focus mode for PreferencesMenu */
  kbFocusMode?: KBFocusMode;
  /** Callback when KB focus mode changes via PreferencesMenu */
  onKBFocusModeChange?: (mode: KBFocusMode) => void;

  // Executor/Critic model props (Critique Loop)
  /** Whether critique loop is enabled (FF_ENABLE_CRITIQUE_LOOP) */
  critiqueLoopEnabled?: boolean;
  /** Currently selected executor model ID (for critique loop) */
  executorModel?: string | null;
  /** Callback when executor model changes */
  onExecutorModelChange?: (modelId: string | null) => void;
  /** Currently selected critic model ID (for critique loop) */
  criticModel?: string | null;
  /** Callback when critic model changes */
  onCriticModelChange?: (modelId: string | null) => void;

  // Style Presets (behind PreferencesMenu)
  /** Currently active style preset */
  activeStylePreset?: import("./StylePresets").PresetName;
  /** Callback when style preset changes */
  onStylePresetChange?: (preset: import("./StylePresets").StylePreset) => void;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function wrapText(
  text: string,
  selectionStart: number,
  selectionEnd: number,
  prefix: string,
  suffix: string,
): { newText: string; newCursorPos: number } {
  const selectedText = text.slice(selectionStart, selectionEnd);
  const before = text.slice(0, selectionStart);
  const after = text.slice(selectionEnd);

  if (selectedText) {
    const newText = `${before}${prefix}${selectedText}${suffix}${after}`;
    return {
      newText,
      newCursorPos:
        selectionStart + prefix.length + selectedText.length + suffix.length,
    };
  } else {
    const newText = `${before}${prefix}${suffix}${after}`;
    return {
      newText,
      newCursorPos: selectionStart + prefix.length,
    };
  }
}

// ==============================================================================
// Component
// ==============================================================================

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  isStreaming = false,
  onStopStreaming,
  autoFocus = false,

  // Model settings
  showModelSelector = false,
  selectedModel,
  availableModels = [],
  onModelChange,
  modelSupportsThinking = false,
  reasoningEffort = "medium",
  onReasoningEffortChange,
  isModelsLoading = false,

  // Tool selection
  showToolSelector = false,
  selectedTools = [],
  onSelectedToolsChange,
  toolSelectionMode = "auto",
  onToolSelectionModeChange,
  availableTools = [],

  // v7: Tool preference
  toolPreference = "auto",
  onToolPreferenceChange,

  // KB Focus
  showKBFocus = false,
  kbFocusValue,
  onKBFocusChange,

  // Voice
  isVoiceSupported = false,
  isListening = false,
  onStartListening,
  onStopListening,

  // Inline suggestions
  enableInlineSuggestions = false,
  inlineSuggestion,
  onAcceptSuggestion,
  onDismissSuggestion,

  // File upload
  uploadFiles = [],
  onRemoveFile,
  onSelectFiles,
  acceptMultipleFiles = false,
  isDragging = false,
  dragHandlers,

  // Slash commands
  slashCommands = [],
  onSlashCommandSelect,

  // P0: Error states
  voiceError,
  fileError,

  // P0: Loading states
  isUploading = false,
  isSuggestionLoading = false,

  // P0: Submit behavior
  submitOnEnter = true,

  // P0: Cursor position tracking
  onCursorPositionChange,

  // P1: Thinking toggle
  enableThinking,
  onEnableThinkingChange,

  // P1: URL content fetch
  enableUrlFetch = false,
  urlFetchLoading = [],
  fetchedUrls = [],
  onRemoveFetchedUrl,

  // P2: Mentions
  mentionOptions = [],

  // P2: Recent models and search
  recentModels = [],
  enableModelSearch = false,

  // P2: Character count
  maxLength,

  // P3: KB status
  kbStatus,
  kbStatusMessage,

  // P3: Tools loading
  isToolsLoading = false,

  // Execution mode (Ctrl/Cmd+Shift+M toggle)
  executionMode = "default",
  onCycleExecutionMode,
  onExecutionModeChange,
  hasBypassPermission = false,

  // Preferences menu (consolidated settings)
  showPreferencesMenu = false,
  kbFocusMode = "all",
  onKBFocusModeChange,

  // Executor/Critic model props (Critique Loop)
  critiqueLoopEnabled = false,
  executorModel,
  onExecutorModelChange,
  criticModel,
  onCriticModelChange,
  // Style presets
  activeStylePreset,
  onStylePresetChange,
}: ChatInputProps) {
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [modelSearchQuery, setModelSearchQuery] = useState("");
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const [mentionStartPos, setMentionStartPos] = useState(0);
  const [dismissedVoiceError, setDismissedVoiceError] = useState(false);
  const [showKbTooltip, setShowKbTooltip] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Get current model info
  const currentModel = availableModels.find((m) => m.id === selectedModel);

  const canSend = value.trim().length > 0 && !disabled;

  // Filter mentions based on current filter
  const filteredMentions = mentionOptions.filter((option) =>
    option.value.toLowerCase().includes(mentionFilter.toLowerCase()),
  );

  // Filter models based on search query
  const filteredModels = modelSearchQuery
    ? availableModels.filter(
        (m) =>
          m.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
          m.provider.toLowerCase().includes(modelSearchQuery.toLowerCase()),
      )
    : availableModels;

  // Get recent models
  const recentModelItems = recentModels
    .map((id) => availableModels.find((m) => m.id === id))
    .filter(Boolean) as ModelOption[];

  // Character count warning threshold (95% of max)
  const isApproachingMaxLength = maxLength && value.length >= maxLength * 0.95;

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [value]);

  // Close model dropdown on click outside or Escape key
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        modelDropdownRef.current &&
        !modelDropdownRef.current.contains(e.target as Node)
      ) {
        setIsModelDropdownOpen(false);
        setModelSearchQuery("");
      }
    };

    const handleEscape = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsModelDropdownOpen(false);
        setModelSearchQuery("");
      }
    };

    if (isModelDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isModelDropdownOpen]);

  // Auto-focus textarea on mount
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Handle file selection
  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0 && onSelectFiles) {
        onSelectFiles(Array.from(files));
      }
      // Reset the input so the same file can be selected again
      e.target.value = "";
    },
    [onSelectFiles],
  );

  // Check if slash command menu should show
  const showSlashCommandMenu =
    value.startsWith("/") && slashCommands.length > 0;

  // Filter slash commands based on input
  const filteredSlashCommands = slashCommands.filter((cmd) =>
    cmd.name.toLowerCase().includes(value.slice(1).toLowerCase()),
  );

  // Apply formatting wrapper
  const applyFormatting = useCallback(
    (prefix: string, suffix: string) => {
      const textarea = textareaRef.current;
      if (!textarea || disabled) return;

      const { selectionStart, selectionEnd } = textarea;
      const { newText, newCursorPos } = wrapText(
        value,
        selectionStart,
        selectionEnd,
        prefix,
        suffix,
      );

      // Enforce maxLength after formatting
      const finalText = maxLength ? newText.slice(0, maxLength) : newText;
      onChange(finalText);

      requestAnimationFrame(() => {
        textarea.focus();
        const clampedPos = Math.min(newCursorPos, finalText.length);
        textarea.setSelectionRange(clampedPos, clampedPos);
      });
    },
    [value, onChange, disabled, maxLength],
  );

  // Handle text change
  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;

      // Apply maxLength if set — truncate instead of silently discarding
      if (maxLength && newValue.length > maxLength) {
        onChange(newValue.slice(0, maxLength));
        onCursorPositionChange?.(maxLength);
        return;
      }

      onChange(newValue);

      // Track cursor position
      const cursorPos = e.target.selectionStart;
      onCursorPositionChange?.(cursorPos);

      // Check for mention trigger
      const textBeforeCursor = newValue.slice(0, cursorPos);
      const lastAtIndex = textBeforeCursor.lastIndexOf("@");

      if (lastAtIndex !== -1 && mentionOptions.length > 0) {
        const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
        // Only trigger mentions when @ is at start or preceded by whitespace
        // (avoids false positives on email addresses like user@example.com)
        const charBeforeAt =
          lastAtIndex > 0 ? textBeforeCursor[lastAtIndex - 1] : " ";
        const isWordBoundary =
          charBeforeAt === " " || charBeforeAt === "\n" || lastAtIndex === 0;
        if (isWordBoundary && !textAfterAt.includes(" ")) {
          setShowMentions(true);
          setMentionFilter(textAfterAt);
          setMentionStartPos(lastAtIndex);
        } else {
          setShowMentions(false);
        }
      } else {
        setShowMentions(false);
      }
    },
    [onChange, maxLength, mentionOptions.length, onCursorPositionChange],
  );

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Ctrl/Cmd+Shift+M to cycle execution mode (WCAG accessible shortcut)
      if (e.key === "m" && e.shiftKey && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        onCycleExecutionMode?.();
        return;
      }

      // Tab to accept inline suggestion
      if (e.key === "Tab" && enableInlineSuggestions && inlineSuggestion) {
        e.preventDefault();
        onAcceptSuggestion?.(inlineSuggestion);
        return;
      }

      // Escape to dismiss inline suggestion or close mentions
      if (e.key === "Escape") {
        if (showMentions) {
          e.preventDefault();
          setShowMentions(false);
          return;
        }
        if (enableInlineSuggestions && inlineSuggestion) {
          e.preventDefault();
          onDismissSuggestion?.();
          return;
        }
      }

      // Submit behavior based on submitOnEnter preference
      if (e.key === "Enter") {
        if (submitOnEnter) {
          // ChatGPT-style: Enter = submit, Shift+Enter = newline
          if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            if (canSend) {
              onSubmit();
            }
            return;
          }
        } else {
          // Legacy-style: Ctrl/Cmd+Enter = submit, Enter = newline
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (canSend) {
              onSubmit();
            }
            return;
          }
        }
      }

      // Formatting shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case "b":
            e.preventDefault();
            applyFormatting("**", "**");
            break;
          case "i":
            e.preventDefault();
            applyFormatting("*", "*");
            break;
          case "`":
            e.preventDefault();
            applyFormatting("`", "`");
            break;
        }
      }
    },
    [
      canSend,
      onSubmit,
      enableInlineSuggestions,
      inlineSuggestion,
      onAcceptSuggestion,
      onDismissSuggestion,
      applyFormatting,
      submitOnEnter,
      showMentions,
      onCycleExecutionMode,
    ],
  );

  // Handle model selection
  const handleModelSelect = useCallback(
    (modelId: string) => {
      onModelChange?.(modelId);
      setIsModelDropdownOpen(false);
      setModelSearchQuery("");
    },
    [onModelChange],
  );

  // Handle mention selection
  const handleMentionSelect = useCallback(
    (option: MentionOption) => {
      const before = value.slice(0, mentionStartPos);
      // Calculate the end of the mention query (@ + filter text)
      const mentionEndPos = mentionStartPos + 1 + mentionFilter.length;
      const after = value.slice(mentionEndPos);
      const newValue = `${before}@${option.value} ${after}`;

      onChange(newValue);
      setShowMentions(false);
      setMentionFilter("");

      // Focus textarea after selection
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    },
    [value, mentionStartPos, mentionFilter, onChange],
  );

  // Reset dismissed voice error when voiceError changes
  useEffect(() => {
    if (voiceError) {
      setDismissedVoiceError(false);
    }
  }, [voiceError]);

  // Detect mentions from initial/controlled value
  useEffect(() => {
    if (mentionOptions.length > 0 && value) {
      const lastAtIndex = value.lastIndexOf("@");
      if (lastAtIndex !== -1) {
        const textAfterAt = value.slice(lastAtIndex + 1);
        // Only trigger when @ is at word boundary (not inside email addresses)
        const charBeforeAt = lastAtIndex > 0 ? value[lastAtIndex - 1] : " ";
        const atWordBoundary =
          charBeforeAt === " " || charBeforeAt === "\n" || lastAtIndex === 0;
        if (atWordBoundary && !textAfterAt.includes(" ")) {
          setShowMentions(true);
          setMentionFilter(textAfterAt);
          setMentionStartPos(lastAtIndex);
        } else {
          setShowMentions(false);
        }
      } else {
        setShowMentions(false);
      }
    } else {
      setShowMentions(false);
    }
  }, [value, mentionOptions.length]);

  return (
    <div
      data-testid="chat-input-form"
      className="relative bg-neutral-1 rounded-2xl shadow-lg ring-1 ring-neutral-a6 backdrop-blur-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-primary-a6"
      {...dragHandlers}
    >
      {/* Drop zone overlay */}
      {isDragging && (
        <div
          data-testid="drop-zone-overlay"
          className="absolute inset-0 bg-primary-4 border-2 border-dashed border-primary-7 rounded-2xl flex items-center justify-center z-10"
        >
          <p className="text-primary-11 font-medium">Drop files here</p>
        </div>
      )}
      {/* P0: Error states */}
      {voiceError && !dismissedVoiceError && (
        <div className="px-3 pt-3 flex items-center gap-2 text-sm text-error-11 bg-error-3 rounded-t-2xl">
          <AlertTriangle className="w-4 h-4" />
          <span>{voiceError}</span>
          <Button
            variant="secondary"
            className="ml-auto min-h-[44px] min-w-[44px] p-1"
            type="button"
            onClick={() => setDismissedVoiceError(true)}
            aria-label="Dismiss error"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}
      {fileError && (
        <div className="px-3 pt-3 flex items-center gap-2 text-sm text-error-11 bg-error-3 rounded-t-2xl">
          <AlertTriangle className="w-4 h-4" />
          <span>{fileError}</span>
        </div>
      )}
      {/* P0: Upload indicator */}
      {isUploading && (
        <div
          data-testid="upload-indicator"
          className="px-3 pt-3 flex items-center gap-2 text-sm text-neutral-11"
        >
          <Loader2
            className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
          />
          <span>Uploading...</span>
        </div>
      )}
      {/* P1: URL fetch loading */}
      {enableUrlFetch && urlFetchLoading.length > 0 && (
        <div
          data-testid="url-fetch-indicator"
          className="px-3 pt-3 flex items-center gap-2 text-sm text-neutral-11"
        >
          <Loader2
            className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
          />
          <span>Fetching URL content...</span>
        </div>
      )}
      {/* P1: Fetched URL badges */}
      {enableUrlFetch && fetchedUrls.length > 0 && (
        <div className="px-3 pt-3 flex flex-wrap gap-2">
          {fetchedUrls.map((urlData) => (
            <div
              key={urlData.url}
              data-testid="url-fetched-badge"
              className="flex items-center gap-2 bg-primary-3 px-3 py-1.5 rounded-full text-sm border border-primary-6"
            >
              <Link className="w-3.5 h-3.5 text-primary-9" />
              <span className="truncate max-w-[150px]">{urlData.title}</span>
              {onRemoveFetchedUrl && (
                <Button
                  variant="secondary"
                  className="min-h-[44px] min-w-[44px] text-neutral-9 hover:text-error-9 p-0.5"
                  type="button"
                  onClick={() => onRemoveFetchedUrl(urlData.url)}
                  aria-label="Remove fetched URL"
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
      {/* File previews */}
      {uploadFiles.length > 0 && (
        <div className="px-3 pt-3 flex flex-wrap gap-2">
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
              {onRemoveFile && (
                <Button
                  variant="secondary"
                  className="min-h-[44px] min-w-[44px] text-neutral-9 hover:text-error-9 p-0.5"
                  type="button"
                  onClick={() => onRemoveFile(file.id)}
                  aria-label="Remove file"
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
      {/* Textarea area */}
      <div className="relative px-3 pt-3">
        {/* Inline suggestion ghost text - must match textarea padding and font size */}
        {enableInlineSuggestions && value && inlineSuggestion && (
          <div
            className="absolute inset-0 px-0 py-2 pointer-events-none overflow-hidden whitespace-pre-wrap break-words text-sm leading-normal"
            aria-hidden="true"
          >
            <span className="invisible">{value}</span>
            <span data-testid="inline-suggestion" className="text-neutral-9">
              {inlineSuggestion}
            </span>
          </div>
        )}

        <label htmlFor="chat-message-input" className="sr-only">
          Message
        </label>
        <Textarea
          id="chat-message-input"
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onSelect={(e) => {
            const target = e.target as HTMLTextAreaElement;
            onCursorPositionChange?.(target.selectionStart);
          }}
          onClick={() => {
            const textarea = textareaRef.current;
            if (textarea) {
              onCursorPositionChange?.(textarea.selectionStart);
            }
          }}
          placeholder="Type your message..."
          disabled={disabled}
          rows={1}
          className="w-full px-0 py-2 bg-transparent text-neutral-12 placeholder-neutral-9 resize-none border-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-offset-2 min-h-[40px] max-h-[200px]"
        />

        {/* P0: Suggestion loading indicator */}
        {enableInlineSuggestions && isSuggestionLoading && (
          <div
            data-testid="suggestion-loading"
            className="absolute right-3 top-3"
          >
            <Loader2
              className={cn(
                "w-4 h-4 text-neutral-9",
                !prefersReducedMotion && "animate-spin",
              )}
            />
          </div>
        )}

        {/* P2: Mention suggestions */}
        {showMentions && filteredMentions.length > 0 && (
          <div
            data-testid="mention-suggestions"
            role="listbox"
            aria-label="Mention suggestions"
            className="absolute z-dropdown w-48 mt-1 bg-neutral-1 border border-neutral-5 rounded-lg shadow-lg max-h-48 overflow-y-auto"
          >
            {filteredMentions.map((option) => (
              <Button
                variant="secondary"
                className="w-full min-h-[44px] px-3 py-2 text-left hover:bg-neutral-2 text-sm text-neutral-12"
                key={`${option.type}-${option.value}`}
                type="button"
                role="option"
                onClick={() => handleMentionSelect(option)}
              >
                <span className="text-neutral-10 mr-1">@</span>
                {option.label || option.value}
              </Button>
            ))}
          </div>
        )}

        {/* Slash command menu */}
        {showSlashCommandMenu && filteredSlashCommands.length > 0 && (
          <div
            data-testid="slash-command-menu"
            className="absolute z-dropdown left-3 bottom-full mb-2 w-64 bg-neutral-1 border border-neutral-5 rounded-lg shadow-lg py-1"
          >
            {filteredSlashCommands.map((cmd) => (
              <Button
                key={cmd.name}
                type="button"
                variant="ghost"
                className="w-full min-h-[44px] px-3 py-2 text-left text-sm hover:bg-neutral-2 flex items-center gap-2 justify-start"
                onClick={() => onSlashCommandSelect?.(cmd)}
              >
                <span className="font-medium text-neutral-12">/{cmd.name}</span>
                <span className="text-neutral-10">{cmd.description}</span>
              </Button>
            ))}
          </div>
        )}
      </div>
      {/* P2: Character count */}
      {maxLength && (
        <div className="px-3 flex justify-end">
          <span
            className={`text-xs ${isApproachingMaxLength ? "text-warning-11" : "text-neutral-10"}`}
            data-testid={
              isApproachingMaxLength ? "char-count-warning" : undefined
            }
          >
            {value.length} / {maxLength}
          </span>
        </div>
      )}
      {/* Controls row */}
      <div
        data-testid="controls-row"
        className="flex items-center justify-between px-3 pb-3 pt-2"
      >
        {/* Left controls */}
        <div className="flex items-center gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileInputChange}
            multiple={acceptMultipleFiles}
            accept="image/*,application/pdf,text/plain,text/csv,application/json"
          />

          {/* Attachment button */}
          <Button
            variant="secondary"
            className="min-h-[44px] min-w-[44px] p-2 text-neutral-9 hover:text-neutral-11 rounded-full hover:bg-neutral-2"
            type="button"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
            aria-label="Attach file"
          >
            <Plus className="w-5 h-5" />
          </Button>

          {/* Execution mode selector - SegmentedControl for direct selection, fallback to Indicator for cycling */}
          {onExecutionModeChange ? (
            <div
              data-testid="execution-mode-segmented"
              className={cn(disabled && "opacity-50 cursor-not-allowed")}
            >
              <SegmentedControl
                value={executionMode}
                onValueChange={(value) =>
                  onExecutionModeChange(
                    value as "default" | "plan" | "auto_accept" | "bypass",
                  )
                }
                aria-label="Execution mode (Ctrl/Cmd+Shift+M to cycle)"
                size="sm"
                disabled={disabled}
              >
                <SegmentedControlItem value="default" aria-label="Default mode">
                  Default
                </SegmentedControlItem>
                <SegmentedControlItem value="plan" aria-label="Plan mode">
                  Plan
                </SegmentedControlItem>
                <SegmentedControlItem
                  value="auto_accept"
                  aria-label="Auto mode"
                >
                  Auto
                </SegmentedControlItem>
                <SegmentedControlItem
                  value="bypass"
                  disabled={!hasBypassPermission}
                  aria-label="Bypass mode - risk-aware auto-approval (requires permission)"
                >
                  <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                  Bypass
                </SegmentedControlItem>
              </SegmentedControl>
            </div>
          ) : onCycleExecutionMode ? (
            <ExecutionModeIndicator
              mode={executionMode}
              onClick={onCycleExecutionMode}
              disabled={disabled}
              hasBypassPermission={hasBypassPermission}
            />
          ) : null}

          {/* Model settings dropdown - only shown when PreferencesMenu is hidden */}
          {!showPreferencesMenu && showModelSelector && (
            <div ref={modelDropdownRef} className="relative">
              <Button
                data-testid="model-settings-button"
                variant="secondary"
                className="min-h-[44px] flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-neutral-5 bg-neutral-1 hover:bg-neutral-2"
                type="button"
                disabled={disabled}
                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                aria-haspopup="true"
                aria-expanded={isModelDropdownOpen}
                aria-label="Model settings"
              >
                <Brain className="w-4 h-4 text-insight-9" />
                {currentModel && (
                  <>
                    <span className="font-medium">{currentModel.name}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                      {formatProviderDisplay(currentModel)}
                    </span>
                  </>
                )}
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${isModelDropdownOpen ? "rotate-180" : ""}`}
                />
              </Button>

              {/* Model dropdown */}
              {isModelDropdownOpen && (
                <div
                  data-testid="model-settings-dropdown"
                  role="listbox"
                  aria-label="Model settings"
                  className="absolute z-dropdown mt-1 left-0 w-72 py-2 bg-neutral-1 border border-neutral-5 rounded-lg shadow-lg max-h-80 overflow-y-auto"
                >
                  {/* P2: Model search */}
                  {enableModelSearch && (
                    <div className="px-2 pb-2">
                      <div className="relative">
                        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-9" />
                        <Input
                          className="pl-8 pr-2 py-1.5 text-sm bg-neutral-2 focus:ring-primary-7"
                          placeholder="Search models..."
                          value={modelSearchQuery}
                          onChange={(e) => setModelSearchQuery(e.target.value)}
                        />
                      </div>
                    </div>
                  )}

                  {/* P2: Recent models section */}
                  {recentModelItems.length > 0 && !modelSearchQuery && (
                    <div className="px-2 pb-2">
                      <div className="text-xs font-semibold text-neutral-10 uppercase tracking-wider px-2 py-1">
                        Recent
                      </div>
                      {recentModelItems.map((model) => (
                        <Button
                          key={`recent-${model.id}`}
                          variant="secondary"
                          role="option"
                          aria-selected={model.id === selectedModel}
                          className="w-full min-h-[44px] flex items-center justify-between px-2 py-2 text-sm hover:bg-neutral-2 rounded"
                          type="button"
                          onClick={() => handleModelSelect(model.id)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{model.name}</span>
                            <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                              {formatProviderDisplay(model)}
                            </span>
                          </div>
                          {model.id === selectedModel && (
                            <Check className="w-4 h-4 text-success-9" />
                          )}
                        </Button>
                      ))}
                    </div>
                  )}

                  {/* Model list */}
                  <div className="px-2 pb-2">
                    <div className="text-xs font-semibold text-neutral-10 uppercase tracking-wider px-2 py-1">
                      Models
                    </div>
                    {isModelsLoading && (
                      <div
                        data-testid="models-loading"
                        className="flex items-center justify-center py-4"
                      >
                        <Loader2
                          className={cn(
                            "w-5 h-5 text-neutral-9",
                            !prefersReducedMotion && "animate-spin",
                          )}
                        />
                      </div>
                    )}
                    {!isModelsLoading &&
                      filteredModels.map((model) => (
                        <Button
                          key={model.id}
                          variant="secondary"
                          role="option"
                          aria-selected={model.id === selectedModel}
                          className="w-full min-h-[44px] flex items-center justify-between px-2 py-2 text-sm hover:bg-neutral-2 rounded"
                          type="button"
                          onClick={() => handleModelSelect(model.id)}
                        >
                          <div className="flex flex-col items-start gap-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{model.name}</span>
                              <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-10">
                                {formatProviderDisplay(model)}
                              </span>
                              {/* P3: Lifecycle badges */}
                              {model.status === "deprecated" && (
                                <span className="text-xs px-1.5 py-0.5 rounded bg-warning-3 text-warning-11">
                                  Deprecated
                                </span>
                              )}
                              {model.status === "preview" && (
                                <span className="text-xs px-1.5 py-0.5 rounded bg-primary-3 text-primary-11">
                                  Preview
                                </span>
                              )}
                            </div>
                            {/* P3: Sunset date */}
                            {model.status === "deprecated" &&
                              model.sunsetDate && (
                                <span className="text-xs text-warning-10">
                                  Sunset: {model.sunsetDate}
                                </span>
                              )}
                          </div>
                          {model.id === selectedModel && (
                            <Check className="w-4 h-4 text-success-9" />
                          )}
                        </Button>
                      ))}
                  </div>

                  {/* Thinking controls */}
                  {modelSupportsThinking && (
                    <div
                      data-testid="thinking-controls"
                      className="border-t border-neutral-5 px-2 pt-2"
                    >
                      {/* P1: Thinking toggle */}
                      {enableThinking !== undefined &&
                        onEnableThinkingChange && (
                          <div className="px-2 py-2 flex items-center justify-between">
                            <span className="text-sm text-neutral-11">
                              Enable Thinking
                            </span>
                            <Button
                              data-testid="thinking-toggle"
                              type="button"
                              variant="ghost"
                              onClick={() =>
                                onEnableThinkingChange(!enableThinking)
                              }
                              className="min-h-[44px] min-w-[44px] text-neutral-11 hover:text-neutral-12 p-0"
                              aria-label={
                                enableThinking
                                  ? "Disable thinking"
                                  : "Enable thinking"
                              }
                            >
                              {enableThinking ? (
                                <ToggleRight className="w-6 h-6 text-success-9" />
                              ) : (
                                <ToggleLeft className="w-6 h-6" />
                              )}
                            </Button>
                          </div>
                        )}

                      {/* Thinking level buttons */}
                      {onReasoningEffortChange && (
                        <>
                          <div className="text-xs font-semibold text-neutral-10 uppercase tracking-wider px-2 py-1">
                            Thinking Level
                          </div>
                          <div className="flex items-center gap-1 px-2">
                            {(
                              [
                                "low",
                                "medium",
                                "high",
                              ] as ReasoningEffortLevel[]
                            ).map((level) => (
                              <Button
                                key={level}
                                variant={
                                  reasoningEffort === level
                                    ? "primary"
                                    : "secondary"
                                }
                                className={cn(
                                  "flex-1 min-h-[44px] px-3 py-1.5 text-sm rounded capitalize",
                                  reasoningEffort === level
                                    ? "bg-insight-9 text-insight-contrast"
                                    : "bg-neutral-2 text-neutral-11 hover:bg-neutral-3",
                                )}
                                type="button"
                                onClick={() => onReasoningEffortChange(level)}
                                aria-label={`Set thinking level to ${level}`}
                              >
                                {level.charAt(0).toUpperCase() + level.slice(1)}
                              </Button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Preferences menu - consolidated settings (model, thinking, tools, KB focus) */}
          {showPreferencesMenu && (
            <PreferencesMenu
              selectedModel={selectedModel}
              availableModels={availableModels}
              isModelsLoading={isModelsLoading}
              onModelChange={onModelChange}
              thinkingLevel={reasoningEffort}
              onThinkingLevelChange={onReasoningEffortChange}
              toolMode={toolSelectionMode}
              onToolModeChange={onToolSelectionModeChange}
              selectedTools={selectedTools}
              onToolsChange={onSelectedToolsChange}
              availableTools={availableTools}
              kbFocusMode={kbFocusMode}
              onKBFocusChange={onKBFocusModeChange}
              // v7: Tool preference for native vs builtin execution
              toolPreference={toolPreference}
              onToolPreferenceChange={onToolPreferenceChange}
              disabled={disabled}
              compact
              // Executor/Critic model selection (Critique Loop)
              critiqueLoopEnabled={critiqueLoopEnabled}
              executorModel={executorModel}
              onExecutorModelChange={onExecutorModelChange}
              criticModel={criticModel}
              onCriticModelChange={onCriticModelChange}
              // Style presets
              activeStylePreset={activeStylePreset}
              onStylePresetChange={onStylePresetChange}
            />
          )}

          {/* Tool selector - only shown when PreferencesMenu is hidden */}
          {!showPreferencesMenu &&
            showToolSelector &&
            onSelectedToolsChange &&
            onToolSelectionModeChange && (
              <div
                data-testid="tool-selector"
                className="flex items-center gap-1"
              >
                {/* P3: Tools loading indicator */}
                {isToolsLoading && (
                  <div
                    data-testid="tools-loading"
                    className="flex items-center"
                  >
                    <Loader2
                      className={cn(
                        "w-4 h-4 text-neutral-9",
                        !prefersReducedMotion && "animate-spin",
                      )}
                    />
                  </div>
                )}
                <ToolSelector
                  selectedTools={selectedTools}
                  onSelectionChange={onSelectedToolsChange}
                  mode={toolSelectionMode}
                  onModeChange={onToolSelectionModeChange}
                  availableTools={availableTools}
                  disabled={disabled}
                  compact
                />
              </div>
            )}

          {/* KB Focus selector - only shown when PreferencesMenu is hidden */}
          {!showPreferencesMenu && showKBFocus && onKBFocusChange && (
            <div className="flex items-center gap-1">
              <Button
                data-testid="kb-focus-selector"
                variant="secondary"
                className="min-h-[44px] px-3 py-1.5 text-sm rounded-lg border border-neutral-5 bg-neutral-1 hover:bg-neutral-2"
                type="button"
                disabled={disabled}
                aria-label={`Knowledge base focus: ${kbFocusValue || "all"}. Click to cycle through modes.`}
                onClick={() => {
                  // Toggle through modes: all -> kb_only -> web_only -> none -> all
                  const modes = ["all", "kb_only", "web_only", "none"];
                  const currentIndex = modes.indexOf(kbFocusValue || "all");
                  const nextIndex = (currentIndex + 1) % modes.length;
                  onKBFocusChange(modes[nextIndex] ?? "all");
                }}
              >
                KB: {kbFocusValue || "all"}
              </Button>

              {/* P3: KB status indicator */}
              {kbStatus && (
                <div
                  data-testid="kb-status-indicator"
                  className="relative"
                  onMouseEnter={() => setShowKbTooltip(true)}
                  onMouseLeave={() => setShowKbTooltip(false)}
                >
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full",
                      kbStatus === "ready" && "bg-success-9",
                      kbStatus === "indexing" && "bg-warning-9",
                      kbStatus === "indexing" &&
                        !prefersReducedMotion &&
                        "animate-pulse",
                      kbStatus !== "ready" &&
                        kbStatus !== "indexing" &&
                        "bg-error-9",
                    )}
                  />
                  {/* Tooltip */}
                  {showKbTooltip && kbStatusMessage && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs bg-neutral-12 text-neutral-1 rounded whitespace-nowrap z-tooltip">
                      {kbStatusMessage}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Voice input */}
          {isVoiceSupported && onStartListening && onStopListening && (
            <Button
              variant="secondary"
              className="min-h-[44px] min-w-[44px] p-2 rounded-lg"
              type="button"
              onClick={isListening ? onStopListening : onStartListening}
              disabled={disabled}
              aria-label={
                isListening ? "Stop voice input" : "Start voice input"
              }
            >
              {isListening ? (
                <MicOff className="w-5 h-5 text-error-9" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </Button>
          )}
        </div>

        {/* Right controls - Send/Stop */}
        <div className="flex items-center gap-2">
          {isStreaming && onStopStreaming ? (
            <Button
              size="icon"
              variant="danger"
              className="min-h-[44px] min-w-[44px] p-2 bg-error-9 text-error-contrast rounded-lg hover:bg-error-10"
              type="button"
              onClick={onStopStreaming}
              aria-label="Stop generating"
            >
              <Square className="w-5 h-5" />
            </Button>
          ) : (
            <motion.button
              className="min-h-[44px] min-w-[44px] p-2 bg-primary-9 text-primary-contrast rounded-lg hover:bg-primary-10 disabled:opacity-50"
              type="button"
              onClick={onSubmit}
              disabled={!canSend}
              aria-label="Send message"
              variants={prefersReducedMotion ? undefined : motionButtonVariants}
              initial="rest"
              whileHover={canSend ? "hover" : undefined}
              whileTap={canSend ? "pressed" : undefined}
            >
              {disabled ? (
                <Loader2
                  className={cn(
                    "w-5 h-5",
                    !prefersReducedMotion && "animate-spin",
                  )}
                />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </motion.button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatInput;
