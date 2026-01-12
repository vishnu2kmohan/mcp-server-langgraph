/**
 * ChatMessages Component
 *
 * Displays the message list with streaming response support.
 * Handles empty state, message rendering, and auto-scroll.
 *
 * Features:
 * - Rich markdown rendering with react-markdown
 * - GitHub Flavored Markdown (tables, strikethrough, task lists)
 * - Native emoji support
 * - Syntax highlighting for code blocks
 * - Source citations for AI responses
 *
 * Extracted from ChatPage for improved modularity.
 */

import { useState, lazy, Suspense } from "react";
import { useChatAutoScroll } from "../../hooks/useChatAutoScroll";
import { RefreshCw, ExternalLink, Loader2, Bot, User } from "lucide-react";
import { AIEmptyState } from "../EmptyState/AIEmptyState";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { MessageActions } from "./MessageActions";
import { MarkdownContent } from "./MarkdownContent";
// Lazy load AgentExecutionTracePanel to reduce initial bundle size and prevent OOM in tests
const AgentExecutionTracePanel = lazy(() =>
  import("./AgentExecutionTracePanel").then((m) => ({
    default: m.AgentExecutionTracePanel,
  })),
);
import { AgentTraceToggleButton } from "./AgentTraceToggleButton";
import {
  HallucinationIndicator,
  type HallucinationReport,
} from "./HallucinationIndicator";
import { LLMThinkingTrace } from "./LLMThinkingTrace";
import {
  AIFollowUpSuggestions,
  type FollowUpSuggestion,
} from "./AIFollowUpSuggestions";
import { ResponseRating, type RatingValue } from "./ResponseRating";
import { TokenUsageDisplay, type ModelProvider } from "./TokenUsageDisplay";
// Import consolidated chat types
import type {
  Source,
  Message,
  LangGraphNodeType,
  LangGraphNodeStatus,
  LangGraphNode,
  LangGraphEdge,
  AgentExecutionTrace,
  AgentTrace,
  ThinkingTrace,
} from "../../types/chat";

// Re-export types for backwards compatibility
export type {
  Source,
  Message,
  LangGraphNodeType,
  LangGraphNodeStatus,
  LangGraphNode,
  LangGraphEdge,
  AgentExecutionTrace,
  AgentTrace,
  ThinkingTrace,
};

// Re-export FollowUpSuggestion type for consumers
export type { FollowUpSuggestion };

// Re-export rating and token usage types
export type { RatingValue, ModelProvider };

export interface ChatMessagesProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  isSending?: boolean;
  /** Agent execution trace (steps, tokens, raw output). Distinct from LLM thinking. */
  agentExecutionTrace?: AgentExecutionTrace;
  /** Callback when user reports a hallucination */
  onReportHallucination?: (report: HallucinationReport) => void;
  /** Enable interactive artifact rendering (mermaid, charts, SVG, etc.). Default: true */
  enableInteractiveArtifacts?: boolean;
  /** Callback when user wants to edit a message (user messages only) */
  onEditMessage?: (messageId: string) => void;
  /** Callback when user wants to regenerate a response (assistant messages only) */
  onRegenerateMessage?: (messageId: string) => void;
  /** Callback when user wants to delete a message */
  onDeleteMessage?: (messageId: string) => void;
  /** Whether a message is being regenerated */
  isRegenerating?: boolean;
  // LLM native thinking trace props (for extended thinking models like Claude Opus 4.5, Gemini 2.5)
  /** LLM native thinking/reasoning content */
  llmThinkingContent?: string;
  /** Number of thinking tokens used */
  llmThinkingTokens?: number;
  /** Whether thinking trace is expanded */
  isThinkingExpanded?: boolean;
  /** Callback to toggle thinking trace expansion */
  onToggleThinking?: () => void;
  /** LLM model name for display */
  llmModelName?: string;
  /** Whether the current model supports extended thinking */
  isThinkingModel?: boolean;
  // AI Follow-Up Suggestions props
  /** Follow-up suggestions to display after the last assistant message */
  suggestions?: FollowUpSuggestion[];
  /** Callback when a suggestion is selected */
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;
  /** Callback when feedback is provided on a suggestion (thumbs up/down) */
  onSuggestionFeedback?: (
    suggestion: FollowUpSuggestion,
    feedback: "positive" | "negative",
  ) => void;
  /** Whether suggestions are loading */
  suggestionsLoading?: boolean;
  // Response Rating props
  /** Map of message IDs to their rating values */
  messageRatings?: Record<string, RatingValue>;
  /** Callback when user rates a message */
  onRateMessage?: (messageId: string, rating: RatingValue) => void;
  /** Callback when user submits feedback for a negative rating */
  onRatingFeedback?: (messageId: string, feedback: string) => void;
  /** Whether a rating is currently being submitted */
  isRatingSubmitting?: boolean;
  // Token Usage Display props
  /** Whether to show token usage for messages */
  showTokenUsage?: boolean;
  /** Model provider for cost calculation */
  modelProvider?: ModelProvider;
  /** Whether to show cost estimation in token usage */
  showCost?: boolean;
  // Avatar props (show_chat_avatars feature)
  /** Whether to show avatars for messages. Default: false */
  showAvatars?: boolean;
  /** User initials for avatar display (e.g., "JD" for John Doe) */
  userInitials?: string;
}

// Note: MarkdownContent and loading fallbacks moved to MarkdownContent.tsx

export function ChatMessages({
  messages,
  isStreaming = false,
  streamingContent = "",
  isSending = false,
  agentExecutionTrace,
  onReportHallucination,
  enableInteractiveArtifacts = true,
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  isRegenerating = false,
  // LLM native thinking trace props
  llmThinkingContent = "",
  llmThinkingTokens,
  isThinkingExpanded = false,
  onToggleThinking,
  llmModelName,
  isThinkingModel = false,
  // AI Follow-Up Suggestions props
  suggestions = [],
  onSuggestionSelect,
  onSuggestionFeedback,
  suggestionsLoading = false,
  // Response Rating props
  messageRatings = {},
  onRateMessage,
  onRatingFeedback,
  isRatingSubmitting = false,
  // Token Usage Display props
  showTokenUsage = false,
  modelProvider = "openai",
  showCost = false,
  // Avatar props (show_chat_avatars feature)
  showAvatars = false,
  userInitials,
}: ChatMessagesProps) {
  // Use extracted auto-scroll hook
  const { messagesEndRef } = useChatAutoScroll(messages, streamingContent);
  const [showAgentExecutionTrace, setShowAgentExecutionTrace] = useState(false);

  // Determine if we should show the LLM thinking trace
  const showLLMThinkingTrace =
    llmThinkingContent && llmThinkingContent.trim().length > 0;

  if (messages.length === 0 && !isStreaming && !isSending) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        {/* Empty state - AI-enhanced (Sprint 3 Migration) */}
        <AIEmptyState context="messages" emptyType="empty" variant="inline" />
        <div ref={messagesEndRef} data-testid="messages-end" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`group flex animate-message-in motion-reduce:animate-none ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div className="relative flex items-start gap-2">
            {/* Assistant Avatar - shown when showAvatars is true */}
            {showAvatars && message.role !== "user" && (
              <div
                data-testid="assistant-avatar"
                className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-neutral-500 to-neutral-600"
              >
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            {/* Message Actions - appears on hover (before message for assistant, after for user) */}
            {message.role !== "user" &&
              (onEditMessage || onRegenerateMessage || onDeleteMessage) && (
                <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
                  <MessageActions
                    messageId={message.id}
                    content={message.content}
                    role={message.role}
                    onEdit={onEditMessage}
                    onRegenerate={onRegenerateMessage}
                    onDelete={onDeleteMessage}
                    isRegenerating={isRegenerating}
                  />
                </div>
              )}
            <div
              className={`max-w-[70%] px-4 py-3 rounded-2xl ${
                message.role === "user"
                  ? "bg-chat-user-bubble dark:bg-chat-user-bubble-dark text-white rounded-br-md"
                  : "bg-chat-ai-bubble dark:bg-chat-ai-bubble-dark border border-neutral-200 dark:border-neutral-700/50 dark:border-neutral-700/50 text-neutral-900 dark:text-neutral-100 rounded-bl-md"
              }`}
            >
              {/* Rich markdown rendering for all messages */}
              <div
                className={`prose prose-sm dark:prose-invert max-w-none ${
                  message.role === "user" ? "prose-invert" : ""
                }`}
              >
                <MarkdownContent
                  content={message.content}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                />
              </div>
              {/* Source Citations - only for assistant messages with sources */}
              {message.role === "assistant" &&
                message.sources &&
                message.sources.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-neutral-200 dark:border-neutral-700 dark:border-neutral-600">
                    <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                      Sources:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {message.sources.map((source, index) => (
                        <a
                          key={index}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
                        >
                          <ExternalLink size={10} />
                          {source.title}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              {/* AI-specific indicators for assistant messages */}
              {message.role === "assistant" && (
                <div className="mt-2 pt-2 border-t border-neutral-100 dark:border-neutral-700 flex items-center gap-3 flex-wrap">
                  {/* Confidence indicator */}
                  {message.confidence !== undefined && (
                    <ConfidenceIndicator score={message.confidence} />
                  )}

                  {/* Hallucination report button */}
                  {onReportHallucination && (
                    <HallucinationIndicator
                      messageId={message.id}
                      onReport={onReportHallucination}
                      isReported={message.isReported}
                    />
                  )}

                  {/* Token Usage Display */}
                  {showTokenUsage && message.usage && (
                    <TokenUsageDisplay
                      promptTokens={message.usage.promptTokens ?? 0}
                      completionTokens={message.usage.completionTokens ?? 0}
                      modelProvider={modelProvider}
                      showCost={showCost}
                      compact
                    />
                  )}

                  {/* Response Rating */}
                  {onRateMessage && (
                    <ResponseRating
                      messageId={message.id}
                      onRate={onRateMessage}
                      currentRating={messageRatings[message.id]}
                      showFeedbackInput
                      onFeedback={onRatingFeedback}
                      isSubmitting={isRatingSubmitting}
                      showThankYou
                      compact
                    />
                  )}
                </div>
              )}

              <p
                className={`text-xs mt-1 ${
                  message.role === "user"
                    ? "text-primary-200"
                    : "text-neutral-400 dark:text-neutral-400"
                }`}
              >
                {new Date(message.timestamp).toLocaleTimeString()}
              </p>
            </div>
            {/* Message Actions for user messages - appears on hover (after message) */}
            {message.role === "user" &&
              (onEditMessage || onRegenerateMessage || onDeleteMessage) && (
                <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
                  <MessageActions
                    messageId={message.id}
                    content={message.content}
                    role={message.role}
                    onEdit={onEditMessage}
                    onRegenerate={onRegenerateMessage}
                    onDelete={onDeleteMessage}
                    isRegenerating={isRegenerating}
                  />
                </div>
              )}
            {/* User Avatar - shown when showAvatars is true */}
            {showAvatars && message.role === "user" && (
              <div
                data-testid="user-avatar"
                className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-chat-accent to-indigo-600"
              >
                {userInitials ? (
                  <span className="text-white text-xs font-medium">
                    {userInitials}
                  </span>
                ) : (
                  <User className="w-4 h-4 text-white" />
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* LLM Native Thinking Trace - displayed during streaming when thinking content is present */}
      {showLLMThinkingTrace && onToggleThinking && (
        <div className="flex justify-start">
          <div className="max-w-[70%]">
            <LLMThinkingTrace
              thinkingContent={llmThinkingContent}
              isExpanded={isThinkingExpanded}
              onToggle={onToggleThinking}
              thinkingTokens={llmThinkingTokens}
              modelName={llmModelName}
              isThinkingModel={isThinkingModel}
              isStreaming={isStreaming}
            />
          </div>
        </div>
      )}

      {/* Streaming response with markdown rendering */}
      {isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-[70%] bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-4 py-3 rounded-lg text-neutral-900 dark:text-neutral-100">
            {streamingContent ? (
              <div className="relative prose prose-sm dark:prose-invert max-w-none">
                <MarkdownContent
                  content={streamingContent}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                  isStreaming={true}
                />
                <span className="inline-block w-2 h-4 ml-1 bg-primary-500 animate-pulse align-middle" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Processing indicator with agent trace toggle */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Processing...</span>
                  </div>
                  {/* Agent trace toggle button */}
                  <AgentTraceToggleButton
                    isExpanded={showAgentExecutionTrace}
                    onToggle={() =>
                      setShowAgentExecutionTrace(!showAgentExecutionTrace)
                    }
                  />
                </div>

                {/* Agent execution trace panel */}
                {showAgentExecutionTrace && (
                  <Suspense
                    fallback={
                      <div className="flex items-center gap-2 p-3 text-neutral-400 dark:text-neutral-400">
                        <Loader2 size={14} className="animate-spin" />
                        <span className="text-xs">Loading trace panel...</span>
                      </div>
                    }
                  >
                    <AgentExecutionTracePanel trace={agentExecutionTrace} />
                  </Suspense>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Legacy sending indicator (fallback) */}
      {isSending && !isStreaming && (
        <div className="flex justify-start">
          <div className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-4 py-3 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                <RefreshCw size={16} className="animate-spin" />
                <span>Processing...</span>
              </div>
              {/* Agent trace toggle button */}
              <AgentTraceToggleButton
                isExpanded={showAgentExecutionTrace}
                onToggle={() =>
                  setShowAgentExecutionTrace(!showAgentExecutionTrace)
                }
              />
            </div>
            {/* Agent execution trace panel (shows empty state when no trace) */}
            {showAgentExecutionTrace && (
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 p-3 text-neutral-400 dark:text-neutral-400">
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-xs">Loading trace panel...</span>
                  </div>
                }
              >
                <AgentExecutionTracePanel trace={undefined} />
              </Suspense>
            )}
          </div>
        </div>
      )}

      {/* AI Follow-Up Suggestions - show after all messages when not streaming */}
      {!isStreaming && !isSending && onSuggestionSelect && (
        <div className="flex justify-start">
          <div className="max-w-[70%]">
            <AIFollowUpSuggestions
              suggestions={suggestions}
              onSelect={onSuggestionSelect}
              onFeedback={onSuggestionFeedback}
              isLoading={suggestionsLoading}
              compact={true}
            />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} data-testid="messages-end" />
    </div>
  );
}
