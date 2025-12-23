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
import { MessageSquare, RefreshCw, ExternalLink, Loader2 } from "lucide-react";
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
        <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <MessageSquare size={48} className="mb-4 opacity-50" />
          <p>No messages yet. Start a conversation!</p>
        </div>
        <div ref={messagesEndRef} data-testid="messages-end" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`group flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div className="relative flex items-start gap-2">
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
              className={`max-w-[70%] px-4 py-3 rounded-lg ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
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
                  <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Sources:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {message.sources.map((source, index) => (
                        <a
                          key={index}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
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
                <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
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
                </div>
              )}

              <p
                className={`text-xs mt-1 ${
                  message.role === "user" ? "text-blue-200" : "text-gray-400"
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
          <div className="max-w-[70%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg text-gray-900 dark:text-gray-100">
            {streamingContent ? (
              <div className="relative prose prose-sm dark:prose-invert max-w-none">
                <MarkdownContent
                  content={streamingContent}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                />
                <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Processing indicator with agent trace toggle */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
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
                      <div className="flex items-center gap-2 p-3 text-gray-400">
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
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
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
                  <div className="flex items-center gap-2 p-3 text-gray-400">
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
