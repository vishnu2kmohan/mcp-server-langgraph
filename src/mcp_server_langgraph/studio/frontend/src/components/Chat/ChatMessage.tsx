/**
 * ChatMessage Component
 *
 * Displays a single chat message with role-based styling.
 * Supports interactive artifact rendering for code blocks.
 *
 * Design System Compliance:
 * - Uses CVA for role-based variants (user/assistant/system)
 * - Uses Motion.dev for message entrance animations
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */

import { Loader2, ExternalLink, Bot, User } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { listItemVariants } from "@/design-system/micro-interactions";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Message container variants based on role
 */
// eslint-disable-next-line react-refresh/only-export-components
export const messageContainerVariants = cva("flex gap-3 mb-2", {
  variants: {
    role: {
      user: "flex-row-reverse",
      assistant: "flex-row",
      system: "flex-row",
    },
  },
  defaultVariants: {
    role: "assistant",
  },
});

/**
 * Avatar variants based on role
 */
// eslint-disable-next-line react-refresh/only-export-components
export const messageAvatarVariants = cva(
  "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
  {
    variants: {
      role: {
        user: "bg-gradient-to-br from-chat-accent to-primary-10",
        assistant: "bg-gradient-to-br from-neutral-10 to-neutral-11",
        system: "bg-gradient-to-br from-warning-8 to-warning-10",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  },
);

/**
 * Message bubble variants based on role
 */
// eslint-disable-next-line react-refresh/only-export-components
export const messageBubbleVariants = cva("flex-1 p-4 rounded-2xl", {
  variants: {
    role: {
      user: "bg-chat-user-bubble dark:bg-chat-user-bubble-dark text-neutral-12 rounded-br-md ml-8",
      assistant:
        "bg-chat-ai-bubble dark:bg-chat-ai-bubble-dark text-neutral-12 rounded-bl-md mr-8",
      system:
        "bg-warning-3 dark:bg-warning-3 text-warning-11 rounded-bl-md mr-8 border border-warning-6",
    },
  },
  defaultVariants: {
    role: "assistant",
  },
});

/**
 * Role label variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const roleLabelVariants = cva("text-sm font-medium", {
  variants: {
    role: {
      user: "text-neutral-12",
      assistant: "text-neutral-11",
      system: "text-warning-11",
    },
  },
  defaultVariants: {
    role: "assistant",
  },
});

/**
 * Timestamp variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const timestampVariants = cva("text-xs", {
  variants: {
    role: {
      user: "text-neutral-a8",
      assistant: "text-neutral-10",
      system: "text-warning-9",
    },
  },
  defaultVariants: {
    role: "assistant",
  },
});
import { parseArtifacts } from "../../utils/artifactParser";
import { ArtifactRenderer } from "../Artifacts/ArtifactRenderer";
import { ArtifactInteractionWrapper } from "../../canvas/ArtifactInteractionWrapper";
import { AIFollowUpSuggestions } from "./AIFollowUpSuggestions";
import type { FollowUpSuggestion } from "./AIFollowUpSuggestions";
import { ResponseRating, type RatingValue } from "./ResponseRating";
import { SelectedToolsDisplay } from "./SelectedToolsDisplay";
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
  /** Semantically selected tools for this message (ADR-0099) */
  selectedTools?: string[];
  /** Selection scores for each tool (0-1 scale) from semantic search */
  selectionScores?: Record<string, number>;
  /** Total number of tools available for selection (for context) */
  totalAvailableTools?: number | null;
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
  selectedTools,
  selectionScores,
  totalAvailableTools,
}: ChatMessageProps) {
  const prefersReducedMotion = useReducedMotion();
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
          <span className="text-neutral-10">
            Thinking...
          </span>
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
              // Render artifact with interaction wrapper for on-demand canvas launch
              return (
                <ArtifactInteractionWrapper
                  key={segment.artifact.id || index}
                  artifact={segment.artifact}
                  className="my-2"
                >
                  <ArtifactRenderer artifact={segment.artifact} />
                </ArtifactInteractionWrapper>
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
    <motion.div
      data-role={role}
      className={messageContainerVariants({ role })}
      variants={prefersReducedMotion ? undefined : listItemVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Avatar - gated behind showAvatar prop (Sprint 3.1) */}
      {showAvatar && (
        <div
          data-testid={isUser ? "user-avatar" : "assistant-avatar"}
          className={messageAvatarVariants({ role })}
        >
          {isUser ? (
            userInitials ? (
              <span className="text-neutral-12 text-xs font-medium">
                {userInitials}
              </span>
            ) : (
              <User className="w-4 h-4 text-neutral-12" />
            )
          ) : (
            <Bot className="w-4 h-4 text-neutral-12" />
          )}
        </div>
      )}

      {/* Message bubble - updated styling (Sprint 3.2) */}
      <div
        data-testid="message-bubble"
        className={messageBubbleVariants({ role })}
      >
        <div className="flex items-center justify-between mb-1">
          <span className={roleLabelVariants({ role })}>
            {roleLabel}
          </span>
          {showTimestamp && (
            <span
              data-testid="timestamp"
              className={timestampVariants({ role })}
            >
              {formatTime(timestamp)}
            </span>
          )}
        </div>
        <div className="text-neutral-12">
          {renderContent()}
        </div>

        {/* Selected Tools Display - only for assistant messages (ADR-0099) */}
        {isAssistant &&
          !isLoading &&
          selectedTools &&
          selectedTools.length > 0 && (
            <div
              data-testid="selected-tools-display"
              className="mt-2 pt-2 border-t border-neutral-a6/30"
            >
              <SelectedToolsDisplay
                selectedTools={selectedTools}
                selectionScores={selectionScores || {}}
                totalAvailableTools={totalAvailableTools}
                compact
              />
            </div>
          )}

        {/* AI Source Citations - only for assistant messages with sources */}
        {isAssistant && sources && sources.length > 0 && (
          <div
            data-testid="sources-section"
            className="mt-3 pt-3 border-t border-neutral-a6/50"
          >
            <div className="flex items-center gap-1 text-xs font-medium text-neutral-10 mb-2">
              <ExternalLink
                data-testid="sources-icon"
                size={12}
                className="text-neutral-9"
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
                    className="text-sm text-primary-10 dark:text-primary-11 hover:underline inline-flex items-center gap-1"
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
          <div className="mt-3 pt-3 border-t border-neutral-a6/50 flex items-center justify-between">
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
          <div className="mt-3 pt-3 border-t border-neutral-a6/50">
            <AIFollowUpSuggestions
              suggestions={suggestions || []}
              onSelect={onSuggestionSelect}
              isLoading={suggestionsLoading}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}
