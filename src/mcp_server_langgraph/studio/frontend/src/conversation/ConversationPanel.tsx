/**
 * ConversationPanel - Phase 2
 *
 * Orchestrator component that combines MessageList, ChatInput,
 * FollowUpSuggestions, and SlashCommandMenu into a cohesive chat experience.
 *
 * Features:
 * - Message display with auto-scroll
 * - Rich input with slash command support
 * - AI-generated follow-up suggestions
 * - Session header with actions
 * - Telemetry callbacks for analytics
 */
import { useState, useCallback } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { MessageList } from "./MessageList";
import { ConnectedChatInputForm } from "./ConnectedChatInputForm";
import {
  type SlashCommand,
  type ModelOption,
} from "../components/Chat/ChatInput";
import type { ReasoningEffortLevel } from "../components/Chat/ReasoningEffortSelector";
import { FollowUpSuggestions, type Suggestion } from "./FollowUpSuggestions";
import { GenerateWorkflowButton } from "./GenerateWorkflowButton";
import type { ChatMessage } from "./MessageBubble";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface ConversationPanelProps {
  /** Messages to display */
  messages: ChatMessage[];
  /** Callback when user sends a message */
  onSendMessage: (message: string) => void;
  /** AI-generated follow-up suggestions */
  suggestions?: Suggestion[];
  /** Slash commands available */
  slashCommands?: SlashCommand[];
  /** Callback when slash command selected */
  onSlashCommand?: (command: SlashCommand) => void;
  /** Session ID for workflow generation */
  sessionId?: string;
  /** Session title for header */
  sessionTitle?: string;
  /** Callback for renaming session */
  onRename?: () => void;
  /** Callback for deleting session */
  onDelete?: () => void;
  /** Loading state */
  isLoading?: boolean;
  /** Streaming state (AI is typing) */
  isStreaming?: boolean;
  /** User has scrolled up from bottom */
  isScrolledUp?: boolean;
  /** Callback when scroll-to-bottom clicked */
  onScrollToBottom?: () => void;
  /** Auto-focus input on mount */
  autoFocus?: boolean;
  /** Telemetry: called when message sent */
  onMessageSent?: (data: { messageLength: number; timestamp: number }) => void;
  /** Telemetry: called when suggestion used */
  onSuggestionUsed?: (data: {
    suggestionId: string;
    suggestionType: string;
  }) => void;
  /** Called when input value changes (for AI intent detection) */
  onInputChange?: (value: string) => void;
  /** Additional class name */
  className?: string;
  // Inline AI Suggestions props (Sprint 6 - VSCode Copilot style)
  /** Enable inline ghost text suggestions */
  enableInlineSuggestions?: boolean;
  /** Use the useInlineSuggestions hook internally (auto-fetch suggestions) */
  useInlineSuggestionsHook?: boolean;
  /** Current inline suggestion text (ghost text after cursor) - used when useInlineSuggestionsHook is false */
  inlineSuggestion?: string;
  /** Whether suggestion is being fetched - used when useInlineSuggestionsHook is false */
  isSuggestionLoading?: boolean;
  /** Callback when user accepts suggestion (Tab key) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape key) */
  onDismissSuggestion?: () => void;
  // KB Focus props (for controlled mode - lifting state to parent)
  /** Controlled KB focus mode value */
  kbFocusValue?: "all" | "kb_only" | "web_only" | "none";
  /** Callback when KB focus mode changes */
  onKBFocusChange?: (mode: "all" | "kb_only" | "web_only" | "none") => void;

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
}

// =============================================================================
// Session Header
// =============================================================================

interface SessionHeaderProps {
  title: string;
  sessionId?: string;
  onRename?: () => void;
  onDelete?: () => void;
}

function SessionHeader({
  title,
  sessionId,
  onRename,
  onDelete,
}: SessionHeaderProps) {
  return (
    <div
      data-testid="session-header"
      className={cn(
        "flex items-center justify-between px-4 py-2",
        "border-b border-neutral-5",
      )}
    >
      <h2 className="text-sm font-medium text-neutral-12 truncate">
        {title}
      </h2>
      <div className="flex items-center gap-1">
        {/* Generate Workflow from Chat button */}
        {sessionId && <GenerateWorkflowButton sessionId={sessionId} />}
        {onRename && (
          <Button
            variant="ghost"
            size="icon"
            data-testid="session-rename-button"
            type="button"
            onClick={onRename}
            className="text-neutral-10"
            aria-label="Rename session"
          >
            <Pencil size={14} />
          </Button>
        )}
        {onDelete && (
          <Button
            variant="ghost"
            size="icon"
            data-testid="session-delete-button"
            type="button"
            onClick={onDelete}
            className="text-neutral-10 hover:bg-error-3 dark:hover:bg-error-a4 hover:text-error-10 dark:hover:text-error-7"
            aria-label="Delete session"
          >
            <Trash2 size={14} />
          </Button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function ConversationPanel({
  messages,
  onSendMessage,
  suggestions = [],
  slashCommands = [],
  onSlashCommand,
  sessionId,
  sessionTitle,
  onRename,
  onDelete,
  isLoading = false,
  isStreaming = false,
  isScrolledUp = false,
  onScrollToBottom,
  autoFocus = false,
  onMessageSent,
  onSuggestionUsed,
  onInputChange,
  className,
  // Inline AI suggestions
  enableInlineSuggestions = false,
  useInlineSuggestionsHook = false,
  inlineSuggestion = "",
  isSuggestionLoading = false,
  onAcceptSuggestion,
  onDismissSuggestion,
  // KB Focus props (controlled mode)
  kbFocusValue,
  onKBFocusChange,
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
}: ConversationPanelProps) {
  const [inputValue, setInputValue] = useState("");

  // Handle sending a message
  const handleSendMessage = useCallback(
    (message: string) => {
      onSendMessage(message);
      setInputValue("");

      // Telemetry callback
      onMessageSent?.({
        messageLength: message.length,
        timestamp: Date.now(),
      });
    },
    [onSendMessage, onMessageSent],
  );

  // Handle input value changes
  const handleInputChange = useCallback(
    (newValue: string) => {
      setInputValue(newValue);
      onInputChange?.(newValue);
    },
    [onInputChange],
  );

  // Handle slash command selection (ChatInputForm handles its own menu)
  const handleSelectSlashCommand = useCallback(
    (command: SlashCommand) => {
      setInputValue("");
      onSlashCommand?.(command);
    },
    [onSlashCommand],
  );

  // Handle suggestion selection
  const handleSelectSuggestion = useCallback(
    (suggestion: Suggestion) => {
      handleSendMessage(suggestion.text);

      // Telemetry callback
      onSuggestionUsed?.({
        suggestionId: suggestion.id,
        suggestionType: suggestion.type,
      });
    },
    [handleSendMessage, onSuggestionUsed],
  );

  // Show suggestions only when not loading and has suggestions
  const showSuggestions = !isLoading && suggestions.length > 0;

  return (
    <div
      data-testid="conversation-panel"
      className={cn(
        "flex flex-col h-full bg-neutral-1",
        className,
      )}
    >
      {/* Session Header */}
      {sessionTitle && (
        <SessionHeader
          title={sessionTitle}
          sessionId={sessionId}
          onRename={onRename}
          onDelete={onDelete}
        />
      )}

      {/* Message List */}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        isStreaming={isStreaming}
        isScrolledUp={isScrolledUp}
        onScrollToBottom={onScrollToBottom}
        className="flex-1"
      />

      {/* Follow-up Suggestions */}
      {showSuggestions && (
        <FollowUpSuggestions
          suggestions={suggestions}
          onSelect={handleSelectSuggestion}
          className="px-4 py-2 border-t border-neutral-5"
        />
      )}

      {/* Chat Input with File Upload, Voice, and Slash Command Menu */}
      <div className="p-4 border-t border-neutral-5">
        <ConnectedChatInputForm
          value={inputValue}
          onChange={handleInputChange}
          onSubmit={handleSendMessage}
          isProcessing={isLoading}
          isStreaming={isStreaming}
          slashCommands={slashCommands}
          onSlashCommand={handleSelectSlashCommand}
          autoFocus={autoFocus}
          // Inline AI suggestions
          enableInlineSuggestions={enableInlineSuggestions}
          useInlineSuggestionsHook={useInlineSuggestionsHook}
          sessionId={sessionId}
          inlineSuggestion={inlineSuggestion}
          isSuggestionLoading={isSuggestionLoading}
          onAcceptSuggestion={onAcceptSuggestion}
          onDismissSuggestion={onDismissSuggestion}
          // KB Focus mode (controlled by parent)
          kbFocusValue={kbFocusValue}
          onKBFocusChange={onKBFocusChange}
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
        />
      </div>
    </div>
  );
}
