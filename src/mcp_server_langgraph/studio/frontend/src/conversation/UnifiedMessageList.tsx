/**
 * UnifiedMessageList - ADR-0104 (Enhanced v3)
 *
 * Consolidated message rendering component with per-message traces.
 * Built following UX best practices and STYLE.md compliance.
 *
 * Features:
 * - CVA variants for message styling
 * - Auto-scroll with rAF fallback
 * - Streaming message handling with cursor
 * - Per-message agent execution traces with OTEL correlation
 * - ResponseRating with correct API
 * - TokenUsageDisplay (compact)
 * - ConfidenceIndicator
 * - HallucinationIndicator for reporting
 * - LLM thinking trace display
 * - Optional avatars for users and assistants
 * - STYLE.md compliance with motion-reduce
 *
 * Gated by feature flag: unified_message_list
 */
import {
  memo,
  useState,
  useRef,
  useEffect,
  useMemo,
  Suspense,
  lazy,
} from "react";
import { Bot, User, ChevronDown, Loader2 } from "lucide-react";

// CVA variants extracted for react-refresh compatibility
import {
  messageRowVariants,
  messageBubbleVariants,
} from "./UnifiedMessageList.variants";

// Types
import type { ChatMessage, ModelProvider } from "../types/session";

// Components
import { MarkdownContent } from "@/components/Chat/MarkdownContent";
import { SourceCitations } from "@/components/Chat/SourceCitations";
import { MessageActions } from "@/components/Chat/MessageActions";
import { ConfidenceIndicator } from "@/components/Chat/ConfidenceIndicator";
import {
  HallucinationIndicator,
  type HallucinationReport,
} from "@/components/Chat/HallucinationIndicator";
import { ResponseRating, type RatingValue } from "@/components/Chat/ResponseRating";
import { TokenUsageDisplay } from "@/components/Chat/TokenUsageDisplay";
import { AgentTraceToggleButton } from "@/components/Chat/AgentTraceToggleButton";
import { AIEmptyState } from "@/components/EmptyState/AIEmptyState";
import { Button } from "@/components/UI";
import { cn } from "../utils/cn";

// Lazy load heavy components
const LLMThinkingTrace = lazy(() =>
  import("@/components/Chat/LLMThinkingTrace").then((mod) => ({
    default: mod.LLMThinkingTrace,
  })),
);

const AgentExecutionTracePanel = lazy(() =>
  import("@/components/Chat/AgentExecutionTracePanel").then((m) => ({
    default: m.AgentExecutionTracePanel,
  })),
);

// =============================================================================
// Types
// =============================================================================

export interface FollowUpSuggestion {
  id: string;
  text: string;
  category: string;
}

export interface UnifiedMessageListProps {
  // Core
  messages: ChatMessage[];
  isLoading?: boolean;
  isStreaming?: boolean;
  showEmptyState?: boolean;
  className?: string;

  // Auto-scroll
  isScrolledUp?: boolean;
  onScrollToBottom?: () => void;

  // Features
  showAvatars?: boolean;
  showTokenUsage?: boolean;
  showAgentTraces?: boolean;
  showRating?: boolean;
  enableInteractiveArtifacts?: boolean;
  enableHallucinationReporting?: boolean;
  enableTraceAI?: boolean;

  // Ratings (correct ResponseRating API)
  messageRatings?: Record<string, RatingValue>;
  onRateMessage?: (messageId: string, rating: RatingValue) => void;
  onRatingFeedback?: (messageId: string, feedback: string) => void;
  isRatingSubmitting?: boolean;

  // Token usage
  modelProvider?: ModelProvider;
  showCost?: boolean;

  // Actions
  onEditMessage?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  onRegenerateMessage?: (messageId: string) => void;
  onReportHallucination?: (report: HallucinationReport) => void;
  isRegenerating?: boolean;

  // Follow-up suggestions
  followUpSuggestions?: FollowUpSuggestion[];
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;

  // Session context
  sessionId?: string;
  userId?: string;
  userInitials?: string;
}

// =============================================================================
// MessageRow Component
// =============================================================================

interface MessageRowProps {
  message: ChatMessage;
  isLastMessage: boolean;
  showAvatars: boolean;
  showTokenUsage: boolean;
  showAgentTraces: boolean;
  showRating: boolean;
  enableInteractiveArtifacts: boolean;
  enableHallucinationReporting: boolean;
  enableTraceAI: boolean;
  messageRatings?: Record<string, RatingValue>;
  onRateMessage?: (messageId: string, rating: RatingValue) => void;
  onRatingFeedback?: (messageId: string, feedback: string) => void;
  isRatingSubmitting: boolean;
  modelProvider: ModelProvider;
  showCost: boolean;
  onEditMessage?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  onRegenerateMessage?: (messageId: string) => void;
  onReportHallucination?: (report: HallucinationReport) => void;
  isRegenerating: boolean;
  sessionId?: string;
  userId?: string;
  userInitials?: string;
}

function MessageRow({
  message,
  showAvatars,
  showTokenUsage,
  showAgentTraces,
  showRating,
  enableInteractiveArtifacts,
  enableHallucinationReporting,
  enableTraceAI,
  messageRatings,
  onRateMessage,
  onRatingFeedback,
  isRatingSubmitting,
  modelProvider,
  showCost,
  onEditMessage,
  onDeleteMessage,
  onRegenerateMessage,
  onReportHallucination,
  isRegenerating,
  userInitials,
}: MessageRowProps) {
  const [showTrace, setShowTrace] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);

  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant" || message.role === "system";
  const isMessageStreaming = message.isStreaming === true;
  const executionTrace = message.agentMetadata?.executionTrace;

  // Check if message has a trace to show
  const hasTrace =
    executionTrace &&
    ((executionTrace.steps && executionTrace.steps.length > 0) ||
      (executionTrace.nodes && executionTrace.nodes.length > 0) ||
      executionTrace.rawOutput);

  return (
    <div
      data-testid={`message-${message.id}`}
      className={messageRowVariants({ role: message.role })}
    >
      {/* Avatar (assistant, before bubble) */}
      {showAvatars && isAssistant && (
        <div
          data-testid="assistant-avatar"
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-insight-2 text-insight-10"
        >
          <Bot size={16} />
        </div>
      )}

      {/* MessageActions (assistant, before bubble) */}
      {isAssistant && (onRegenerateMessage || onDeleteMessage) && (
        <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
          <MessageActions
            messageId={message.id}
            content={message.content}
            role={message.role}
            onRegenerate={onRegenerateMessage}
            onDelete={onDeleteMessage}
            isRegenerating={isRegenerating}
          />
        </div>
      )}

      {/* Message column */}
      <div className="flex flex-col">
        {/* Bubble */}
        <article
          className={messageBubbleVariants({ role: message.role })}
          role="article"
          aria-label={`${message.role} message`}
        >
          {/* LLM Thinking Trace (inside bubble for context) */}
          {isAssistant && message.thinkingContent && (
            <div className="mb-3">
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 text-sm text-neutral-9">
                    <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" />
                    Loading thinking trace...
                  </div>
                }
              >
                <LLMThinkingTrace
                  thinkingContent={message.thinkingContent}
                  isExpanded={isThinkingExpanded}
                  onToggle={() => setIsThinkingExpanded(!isThinkingExpanded)}
                  thinkingTokens={message.thinkingTokens}
                  modelName={message.modelName}
                />
              </Suspense>
            </div>
          )}

          {/* Content with Markdown */}
          <div
            className={cn(
              "prose prose-sm dark:prose-invert max-w-none",
              isUser && "prose-invert",
            )}
          >
            {/* Processing indicator during empty streaming */}
            {isMessageStreaming && !message.content ? (
              <div className="flex items-center gap-2 text-neutral-10">
                <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" />
                <span className="text-sm">Processing...</span>
              </div>
            ) : (
              <>
                <MarkdownContent
                  content={message.content}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                  isStreaming={isMessageStreaming}
                />

                {/* Streaming cursor */}
                {isMessageStreaming && (
                  <span
                    role="status"
                    className="inline-block w-2 h-4 bg-primary-9 animate-pulse motion-reduce:animate-none ml-0.5"
                    aria-label="Generating response"
                  />
                )}
              </>
            )}
          </div>

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <SourceCitations sources={message.sources} />
          )}
        </article>

        {/* Indicator row (after bubble, assistant only) */}
        {isAssistant && !isMessageStreaming && (
          <div className="flex items-center gap-2 px-1 mt-1 flex-wrap">
            {/* Confidence */}
            {message.agentMetadata?.confidence !== undefined && (
              <ConfidenceIndicator
                score={message.agentMetadata.confidence}
                compact
              />
            )}

            {/* Token Usage */}
            {showTokenUsage && message.usage && (
              <TokenUsageDisplay
                promptTokens={message.usage.promptTokens ?? 0}
                completionTokens={message.usage.completionTokens ?? 0}
                modelProvider={modelProvider}
                showCost={showCost}
                compact
              />
            )}

            {/* Hallucination */}
            {enableHallucinationReporting && onReportHallucination && (
              <HallucinationIndicator
                messageId={message.id}
                onReport={onReportHallucination}
                isReported={message.isReported}
              />
            )}
          </div>
        )}

        {/* Response Rating (after indicator row, assistant only) */}
        {showRating && isAssistant && !isMessageStreaming && onRateMessage && (
          <div className="px-1 mt-1">
            <ResponseRating
              messageId={message.id}
              onRate={onRateMessage}
              currentRating={messageRatings?.[message.id]}
              showFeedbackInput
              onFeedback={onRatingFeedback}
              isSubmitting={isRatingSubmitting}
              showThankYou
              compact
            />
          </div>
        )}

        {/* Per-message Agent Trace (after rating, assistant only) */}
        {showAgentTraces && isAssistant && hasTrace && (
          <div className="px-1 mt-2">
            <AgentTraceToggleButton
              isExpanded={showTrace}
              onToggle={() => setShowTrace(!showTrace)}
            />

            {showTrace && (
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 py-2 text-sm text-neutral-9">
                    <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" />
                    Loading trace...
                  </div>
                }
              >
                <AgentExecutionTracePanel
                  trace={executionTrace}
                  enableAI={enableTraceAI && !!executionTrace?.traceId}
                  className="mt-2"
                />
              </Suspense>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "text-xs mt-1 px-1",
            isUser ? "text-primary-4" : "text-neutral-9",
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>

      {/* MessageActions (user, after bubble) */}
      {isUser && (onEditMessage || onDeleteMessage) && (
        <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
          <MessageActions
            messageId={message.id}
            content={message.content}
            role={message.role}
            onEdit={onEditMessage}
            onDelete={onDeleteMessage}
            isRegenerating={isRegenerating}
          />
        </div>
      )}

      {/* Avatar (user, after bubble) */}
      {showAvatars && isUser && (
        <div
          data-testid="user-avatar"
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-primary-3 text-primary-10"
        >
          {userInitials ? (
            <span className="text-xs font-medium">{userInitials}</span>
          ) : (
            <User size={16} />
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Follow-up Suggestions
// =============================================================================

interface FollowUpSuggestionsProps {
  suggestions: FollowUpSuggestion[];
  onSelect?: (suggestion: FollowUpSuggestion) => void;
}

function FollowUpSuggestionsComponent({
  suggestions,
  onSelect,
}: FollowUpSuggestionsProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div
      data-testid="follow-up-suggestions"
      className="flex flex-wrap gap-2 px-4 py-2"
    >
      {suggestions.map((suggestion) => (
        <Button
          key={suggestion.id}
          variant="secondary"
          className="text-sm px-3 py-1.5 rounded-full"
          onClick={() => onSelect?.(suggestion)}
          type="button"
        >
          {suggestion.text}
        </Button>
      ))}
    </div>
  );
}

// =============================================================================
// UnifiedMessageList Component
// =============================================================================

function UnifiedMessageListImpl({
  messages,
  isLoading = false,
  isStreaming = false,
  showEmptyState = true,
  className,
  // Auto-scroll
  isScrolledUp = false,
  onScrollToBottom,
  // Features
  showAvatars = false,
  showTokenUsage = false,
  showAgentTraces = false,
  showRating = false,
  enableInteractiveArtifacts = true,
  enableHallucinationReporting = false,
  enableTraceAI = false,
  // Ratings
  messageRatings,
  onRateMessage,
  onRatingFeedback,
  isRatingSubmitting = false,
  // Token usage
  modelProvider = "openai",
  showCost = false,
  // Actions
  onEditMessage,
  onDeleteMessage,
  onRegenerateMessage,
  onReportHallucination,
  isRegenerating = false,
  // Follow-up suggestions
  followUpSuggestions,
  onSuggestionSelect,
  // Session context
  sessionId,
  userId,
  userInitials,
}: UnifiedMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollRafRef = useRef<number | null>(null);

  // Key off streaming content length (critical for streaming updates)
  const lastMessage = messages[messages.length - 1];
  const streamingContentKey = useMemo(() => {
    if (isStreaming && lastMessage?.isStreaming) {
      return lastMessage.content?.length ?? 0;
    }
    return 0;
  }, [isStreaming, lastMessage?.isStreaming, lastMessage?.content?.length]);

  // Auto-scroll effect with rAF fallback
  useEffect(() => {
    if (isScrolledUp) return;
    if (!endRef.current?.scrollIntoView) return;

    const behavior: ScrollBehavior = isStreaming ? "auto" : "smooth";

    // Cancel any pending scroll
    if (scrollRafRef.current !== null) {
      if (typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(scrollRafRef.current);
      } else {
        // Fallback for environments without cancelAnimationFrame
        clearTimeout(scrollRafRef.current as unknown as number);
      }
    }

    // Schedule scroll with rAF (or setTimeout fallback)
    if (typeof requestAnimationFrame === "function") {
      scrollRafRef.current = requestAnimationFrame(() => {
        endRef.current?.scrollIntoView({ behavior, block: "end" });
        scrollRafRef.current = null;
      });
    } else {
      // Fallback for SSR/test environments
      scrollRafRef.current = setTimeout(() => {
        endRef.current?.scrollIntoView({ behavior, block: "end" });
        scrollRafRef.current = null;
      }, 0) as unknown as number;
    }

    return () => {
      if (scrollRafRef.current !== null) {
        if (typeof cancelAnimationFrame === "function") {
          cancelAnimationFrame(scrollRafRef.current);
        } else {
          clearTimeout(scrollRafRef.current as unknown as number);
        }
      }
    };
  }, [messages.length, streamingContentKey, isScrolledUp, isStreaming]);

  const hasMessages = messages.length > 0;
  const shouldShowEmptyState =
    showEmptyState && !hasMessages && !isLoading && !isStreaming;

  // Empty state
  if (shouldShowEmptyState) {
    return (
      <div
        data-testid="unified-message-list"
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
        className={cn("flex-1 overflow-y-auto p-6", className)}
      >
        <AIEmptyState context="messages" emptyType="empty" variant="inline" />
        <div ref={endRef} data-testid="messages-end" />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="unified-message-list"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
      className={cn("flex-1 overflow-y-auto p-6 space-y-4 relative", className)}
    >
      {/* Messages */}
      {messages.map((message, index) => (
        <MessageRow
          key={message.id}
          message={message}
          isLastMessage={index === messages.length - 1}
          showAvatars={showAvatars}
          showTokenUsage={showTokenUsage}
          showAgentTraces={showAgentTraces}
          showRating={showRating}
          enableInteractiveArtifacts={enableInteractiveArtifacts}
          enableHallucinationReporting={enableHallucinationReporting}
          enableTraceAI={enableTraceAI}
          messageRatings={messageRatings}
          onRateMessage={onRateMessage}
          onRatingFeedback={onRatingFeedback}
          isRatingSubmitting={isRatingSubmitting}
          modelProvider={modelProvider}
          showCost={showCost}
          onEditMessage={onEditMessage}
          onDeleteMessage={onDeleteMessage}
          onRegenerateMessage={onRegenerateMessage}
          onReportHallucination={onReportHallucination}
          isRegenerating={isRegenerating}
          sessionId={sessionId}
          userId={userId}
          userInitials={userInitials}
        />
      ))}

      {/* Loading indicator */}
      {isLoading && !isStreaming && (
        <div className="flex justify-start">
          <div className="bg-neutral-2 border border-neutral-6 px-4 py-3 rounded-2xl rounded-bl-md">
            <div className="flex items-center gap-2 text-neutral-10">
              <div className="flex gap-1">
                <div
                  className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce motion-reduce:animate-none"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce motion-reduce:animate-none"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce motion-reduce:animate-none"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
              <span className="text-sm">Processing...</span>
            </div>
          </div>
        </div>
      )}

      {/* Typing Indicator (streaming without content yet) */}
      {isStreaming &&
        !messages.some((m) => m.isStreaming && m.content) && (
          <div
            data-testid="typing-indicator"
            className="flex items-center gap-2 px-4 py-2"
            role="status"
            aria-label="Assistant is typing"
          >
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none" />
              <div
                className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none"
                style={{ animationDelay: "150ms" }}
              />
              <div
                className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none"
                style={{ animationDelay: "300ms" }}
              />
            </div>
            <span className="text-sm text-neutral-9">
              Assistant is typing...
            </span>
          </div>
        )}

      {/* Follow-up Suggestions */}
      {!isStreaming &&
        !isLoading &&
        followUpSuggestions &&
        followUpSuggestions.length > 0 && (
          <FollowUpSuggestionsComponent
            suggestions={followUpSuggestions}
            onSelect={onSuggestionSelect}
          />
        )}

      {/* Scroll anchor */}
      <div ref={endRef} data-testid="messages-end" />

      {/* Scroll-to-bottom button */}
      {isScrolledUp && onScrollToBottom && (
        <Button
          variant="secondary"
          onClick={onScrollToBottom}
          className="absolute bottom-4 right-4 p-2 rounded-full shadow-md"
          aria-label="Scroll to bottom"
        >
          <ChevronDown size={20} className="text-neutral-11" />
        </Button>
      )}
    </div>
  );
}

export const UnifiedMessageList = memo(UnifiedMessageListImpl);
UnifiedMessageList.displayName = "UnifiedMessageList";

// Re-export types for backwards compatibility
export type { RatingValue };
