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
import { type SlashCommand } from "../components/Chat/ChatInputForm";
import { FollowUpSuggestions, type Suggestion } from "./FollowUpSuggestions";
import { GenerateWorkflowButton } from "./GenerateWorkflowButton";
import type { ChatMessage } from "./MessageBubble";
import { cn } from "../utils/cn";

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
  /** Current inline suggestion text (ghost text after cursor) */
  inlineSuggestion?: string;
  /** Whether suggestion is being fetched */
  isSuggestionLoading?: boolean;
  /** Callback when user accepts suggestion (Tab key) */
  onAcceptSuggestion?: (suggestion: string) => void;
  /** Callback when user dismisses suggestion (Escape key) */
  onDismissSuggestion?: () => void;
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
        "border-b border-gray-200 dark:border-gray-700",
      )}
    >
      <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
        {title}
      </h2>
      <div className="flex items-center gap-1">
        {/* Generate Workflow from Chat button */}
        {sessionId && <GenerateWorkflowButton sessionId={sessionId} />}
        {onRename && (
          <button
            data-testid="session-rename-button"
            type="button"
            onClick={onRename}
            className={cn(
              "p-1.5 rounded-md",
              "text-gray-500 dark:text-gray-400",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
              "transition-colors",
            )}
            aria-label="Rename session"
          >
            <Pencil size={14} />
          </button>
        )}
        {onDelete && (
          <button
            data-testid="session-delete-button"
            type="button"
            onClick={onDelete}
            className={cn(
              "p-1.5 rounded-md",
              "text-gray-500 dark:text-gray-400",
              "hover:bg-red-100 dark:hover:bg-red-900/30",
              "hover:text-red-600 dark:hover:text-red-400",
              "transition-colors",
            )}
            aria-label="Delete session"
          >
            <Trash2 size={14} />
          </button>
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
  autoFocus: _autoFocus = false,
  onMessageSent,
  onSuggestionUsed,
  onInputChange,
  className,
  // Inline AI suggestions
  enableInlineSuggestions = false,
  inlineSuggestion = "",
  isSuggestionLoading = false,
  onAcceptSuggestion,
  onDismissSuggestion,
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
        "flex flex-col h-full bg-white dark:bg-gray-900",
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
          className="px-4 py-2 border-t border-gray-200 dark:border-gray-700"
        />
      )}

      {/* Chat Input with File Upload, Voice, and Slash Command Menu */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <ConnectedChatInputForm
          value={inputValue}
          onChange={handleInputChange}
          onSubmit={handleSendMessage}
          isProcessing={isLoading}
          isStreaming={isStreaming}
          slashCommands={slashCommands}
          onSlashCommand={handleSelectSlashCommand}
          // Inline AI suggestions
          enableInlineSuggestions={enableInlineSuggestions}
          inlineSuggestion={inlineSuggestion}
          isSuggestionLoading={isSuggestionLoading}
          onAcceptSuggestion={onAcceptSuggestion}
          onDismissSuggestion={onDismissSuggestion}
        />
      </div>
    </div>
  );
}
