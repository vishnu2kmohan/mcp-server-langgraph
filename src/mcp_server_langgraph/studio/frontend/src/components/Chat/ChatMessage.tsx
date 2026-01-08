/**
 * ChatMessage Component
 *
 * Displays a single chat message with role-based styling.
 * Supports interactive artifact rendering for code blocks.
 */

import { Loader2, ExternalLink, Bot, User } from "lucide-react";
import { parseArtifacts } from "../../utils/artifactParser";
import { ArtifactRenderer } from "../Artifacts/ArtifactRenderer";
import { AIFollowUpSuggestions } from "./AIFollowUpSuggestions";
import type { FollowUpSuggestion } from "./AIFollowUpSuggestions";
import { ResponseRating, type RatingValue } from "./ResponseRating";
import { TokenUsageDisplay, type ModelProvider } from "./TokenUsageDisplay";
import type { SourceCitation } from "../../types/api";

// Re-export for consumers
export type { SourceCitation };

export interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  showTimestamp?: boolean;
  isLoading?: boolean;
  renderMarkdown?: boolean;
  /** Enable interactive artifact rendering for code blocks */
  renderArtifacts?: boolean;
  /** Source citations for AI responses (only displayed for assistant messages) */
  sources?: SourceCitation[];
  /** AI-generated follow-up suggestions (only displayed for assistant messages) */
  suggestions?: FollowUpSuggestion[];
  /** Callback when a suggestion is selected */
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;
  /** Whether suggestions are loading */
  suggestionsLoading?: boolean;
  /** Message ID for rating functionality */
  messageId?: string;
  /** Current rating value for this message */
  rating?: RatingValue;
  /** Callback when user rates the message */
  onRate?: (messageId: string, rating: RatingValue) => void;
  /** Callback when user submits feedback for negative rating */
  onFeedback?: (messageId: string, feedback: string) => void;
  /** Whether rating is being submitted */
  isRatingSubmitting?: boolean;
  /** Token usage for this message (only for assistant messages) */
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
  };
  /** Model provider for cost calculation */
  modelProvider?: ModelProvider;
  /** Show cost estimation in token usage display */
  showCost?: boolean;
  /** Show avatar icon next to message (Sprint 3.1 - gated, default: false) */
  showAvatar?: boolean;
  /** User initials for avatar (e.g., "JD" for "John Doe") */
  userInitials?: string;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  showTimestamp = true,
  isLoading = false,
  renderMarkdown = false,
  renderArtifacts = false,
  sources,
  suggestions,
  onSuggestionSelect,
  suggestionsLoading = false,
  messageId,
  rating,
  onRate,
  onFeedback,
  isRatingSubmitting = false,
  tokenUsage,
  modelProvider = "openai",
  showCost = false,
  showAvatar = true,
  userInitials,
}: ChatMessageProps) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";

  const roleLabel = isUser ? "You" : isAssistant ? "Assistant" : "System";

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div
          data-testid="loading-indicator"
          className="flex items-center gap-2"
        >
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-gray-500 dark:text-gray-400">Thinking...</span>
        </div>
      );
    }

    // Interactive artifact rendering - parses code blocks into renderable artifacts
    if (renderArtifacts) {
      const segments = parseArtifacts(content);
      return (
        <div className="space-y-3">
          {segments.map((segment, index) => {
            if (segment.type === "text") {
              // Render text segments with optional markdown
              if (renderMarkdown) {
                const rendered = segment.content
                  .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                  .replace(/\*(.*?)\*/g, "<em>$1</em>");
                return (
                  <div
                    key={index}
                    dangerouslySetInnerHTML={{ __html: rendered }}
                    className="prose prose-sm max-w-none"
                  />
                );
              }
              return (
                <p key={index} className="whitespace-pre-wrap">
                  {segment.content}
                </p>
              );
            } else if (segment.type === "artifact" && segment.artifact) {
              // Render artifact using ArtifactRenderer
              return (
                <ArtifactRenderer
                  key={segment.artifact.id || index}
                  artifact={segment.artifact}
                  className="my-2"
                />
              );
            }
            return null;
          })}
        </div>
      );
    }

    if (renderMarkdown) {
      // Simple markdown rendering for bold text
      const rendered = content
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>");
      return (
        <div
          dangerouslySetInnerHTML={{ __html: rendered }}
          className="prose prose-sm max-w-none"
        />
      );
    }

    return <p className="whitespace-pre-wrap">{content}</p>;
  };

  return (
    <div
      data-role={role}
      className={`flex gap-3 mb-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar - gated behind showAvatar prop (Sprint 3.1) */}
      {showAvatar && (
        <div
          data-testid={isUser ? "user-avatar" : "assistant-avatar"}
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser
              ? "bg-gradient-to-br from-chat-accent to-indigo-600"
              : "bg-gradient-to-br from-gray-500 to-gray-600"
          }`}
        >
          {isUser ? (
            userInitials ? (
              <span className="text-white text-xs font-medium">
                {userInitials}
              </span>
            ) : (
              <User className="w-4 h-4 text-white" />
            )
          ) : (
            <Bot className="w-4 h-4 text-white" />
          )}
        </div>
      )}

      {/* Message bubble - updated styling (Sprint 3.2) */}
      <div
        data-testid="message-bubble"
        className={`flex-1 p-4 rounded-2xl ${
          isUser
            ? "bg-chat-user-bubble dark:bg-chat-user-bubble-dark text-white rounded-br-md ml-8"
            : "bg-chat-ai-bubble dark:bg-chat-ai-bubble-dark text-gray-900 dark:text-gray-100 rounded-bl-md mr-8"
        }`}
      >
        <div className="flex items-center justify-between mb-1">
          <span
            className={`text-sm font-medium ${
              isUser ? "text-white/90" : "text-gray-700 dark:text-gray-300"
            }`}
          >
            {roleLabel}
          </span>
          {showTimestamp && (
            <span
              data-testid="timestamp"
              className={`text-xs ${
                isUser ? "text-white/70" : "text-gray-500 dark:text-gray-400"
              }`}
            >
              {formatTime(timestamp)}
            </span>
          )}
        </div>
        <div
          className={isUser ? "text-white" : "text-gray-900 dark:text-gray-100"}
        >
          {renderContent()}
        </div>

        {/* AI Source Citations - only for assistant messages with sources */}
        {isAssistant && sources && sources.length > 0 && (
          <div
            data-testid="sources-section"
            className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50 dark:border-gray-600/50"
          >
            <div className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
              <ExternalLink
                data-testid="sources-icon"
                size={12}
                className="text-gray-400 dark:text-gray-400"
              />
              <span>Sources:</span>
            </div>
            <ul className="space-y-1">
              {sources.map((source, index) => (
                <li key={index}>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-600 dark:text-primary-400 hover:underline inline-flex items-center gap-1"
                  >
                    {source.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Token Usage Display - only for assistant messages with usage data */}
        {isAssistant && !isLoading && tokenUsage && (
          <div className="mt-2 flex items-center">
            <TokenUsageDisplay
              promptTokens={tokenUsage.promptTokens}
              completionTokens={tokenUsage.completionTokens}
              modelProvider={modelProvider}
              showCost={showCost}
              compact
            />
          </div>
        )}

        {/* Response Rating - only for assistant messages when not loading */}
        {isAssistant && !isLoading && messageId && onRate && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50 dark:border-gray-600/50 flex items-center justify-between">
            <ResponseRating
              messageId={messageId}
              onRate={onRate}
              currentRating={rating}
              showFeedbackInput
              onFeedback={onFeedback}
              isSubmitting={isRatingSubmitting}
              showThankYou
              compact
            />
          </div>
        )}

        {/* AI Follow-Up Suggestions - only for assistant messages when not loading */}
        {isAssistant && !isLoading && onSuggestionSelect && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50 dark:border-gray-600/50">
            <AIFollowUpSuggestions
              suggestions={suggestions || []}
              onSelect={onSuggestionSelect}
              isLoading={suggestionsLoading}
            />
          </div>
        )}
      </div>
    </div>
  );
}
