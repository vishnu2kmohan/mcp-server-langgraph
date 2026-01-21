/**
 * UnifiedMessageList - ADR-0104
 *
 * Consolidated message rendering component that merges functionality from
 * MessageList and ChatMessages. This is the single source of truth for
 * message rendering in the conversation panel.
 *
 * Features:
 * - Message rendering with role-based styling
 * - Loading and streaming states
 * - Empty state handling
 * - Source citations display
 * - LLM thinking traces
 * - Message rating (thumbs up/down)
 * - Agent execution traces
 * - Message actions (edit, delete, regenerate)
 * - Follow-up suggestions
 * - Token usage display
 * - Accessibility (role="log", aria-live)
 *
 * Gated by feature flag: unified_message_list
 */
import { memo, useState, Suspense, lazy } from "react";
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import type { ChatMessage, AgentMetadata } from "../types";
import { MessageBubble } from "./MessageBubble";
import { cn } from "../utils/cn";
import { Button } from "@/components/UI";

// Lazy load heavy components
const LLMThinkingTrace = lazy(() =>
  import("@/components/Chat/LLMThinkingTrace").then((mod) => ({
    default: mod.LLMThinkingTrace,
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
  /** Messages to render */
  messages: ChatMessage[];
  /** Whether messages are loading */
  isLoading?: boolean;
  /** Whether assistant is currently streaming */
  isStreaming?: boolean;
  /** Whether to show empty state when no messages */
  showEmptyState?: boolean;
  /** Whether to show rating controls */
  showRating?: boolean;
  /** Whether to show agent traces */
  showAgentTraces?: boolean;
  /** Whether to show token usage */
  showTokenUsage?: boolean;
  /** Follow-up suggestions */
  followUpSuggestions?: FollowUpSuggestion[];
  /** Message ratings map (messageId -> rating) */
  messageRatings?: Record<string, "up" | "down" | null>;
  /** Callback when user edits a message */
  onEditMessage?: (messageId: string) => void;
  /** Callback when user deletes a message */
  onDeleteMessage?: (messageId: string) => void;
  /** Callback when user regenerates a message */
  onRegenerateMessage?: (messageId: string) => void;
  /** Callback when user rates a message */
  onRateMessage?: (messageId: string, rating: "up" | "down") => void;
  /** Callback when user selects a follow-up suggestion */
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Loading Indicator
// =============================================================================

function LoadingIndicator() {
  return (
    <div
      data-testid="loading-indicator"
      className="flex justify-center py-4"
      role="status"
      aria-label="Loading messages"
    >
      <div className="flex gap-1">
        <div className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce" />
        <div className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce animation-delay-150" />
        <div className="w-2 h-2 bg-neutral-5 rounded-full animate-bounce animation-delay-300" />
      </div>
    </div>
  );
}

// =============================================================================
// Typing Indicator
// =============================================================================

function TypingIndicator() {
  return (
    <div
      data-testid="typing-indicator"
      className="flex items-center gap-2 px-4 py-2"
      role="status"
      aria-label="Assistant is typing"
    >
      <div className="flex gap-1">
        <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none" />
        <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none animation-delay-150" />
        <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none animation-delay-300" />
      </div>
      <span className="text-sm text-neutral-9">Assistant is typing...</span>
    </div>
  );
}

// =============================================================================
// Empty State
// =============================================================================

function EmptyState() {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center py-12 text-center"
    >
      <div className="text-neutral-9 text-sm">
        No messages yet. Start a conversation!
      </div>
    </div>
  );
}

// =============================================================================
// Source Citations
// =============================================================================

interface SourceCitationsProps {
  sources: Array<{ title: string; url: string }>;
}

function SourceCitations({ sources }: SourceCitationsProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-neutral-6">
      <div className="text-xs text-neutral-9 mb-1">Sources:</div>
      <div className="flex flex-wrap gap-2">
        {sources.map((source, index) => (
          <a
            key={`${source.url}-${index}`}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary-9 hover:text-primary-10 hover:underline"
          >
            {source.title}
          </a>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Thinking Trace Wrapper
// =============================================================================

interface ThinkingTraceWrapperProps {
  thinkingContent: string;
  thinkingTokens?: number;
  modelName?: string;
}

function ThinkingTraceWrapper({
  thinkingContent,
  thinkingTokens,
  modelName,
}: ThinkingTraceWrapperProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div data-testid="thinking-trace" className="mb-2">
      <Suspense
        fallback={
          <div className="flex items-center gap-2 text-sm text-neutral-9">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading thinking trace...
          </div>
        }
      >
        <LLMThinkingTrace
          thinkingContent={thinkingContent}
          isExpanded={isExpanded}
          onToggle={() => setIsExpanded(!isExpanded)}
          thinkingTokens={thinkingTokens}
          modelName={modelName}
        />
      </Suspense>
    </div>
  );
}

// =============================================================================
// Rating Controls
// =============================================================================

interface RatingControlsProps {
  messageId: string;
  currentRating?: "up" | "down" | null;
  onRate?: (messageId: string, rating: "up" | "down") => void;
}

function RatingControls({ messageId, currentRating, onRate }: RatingControlsProps) {
  return (
    <div data-testid="rating-controls" className="flex gap-1 mt-2">
      <Button
        variant="secondary"
        className={cn(
          "p-1.5 rounded",
          currentRating === "up" && "bg-success-3 text-success-9",
        )}
        onClick={() => onRate?.(messageId, "up")}
        aria-label="Thumbs up"
        type="button"
      >
        <ThumbsUp className="w-4 h-4" />
      </Button>
      <Button
        variant="secondary"
        className={cn(
          "p-1.5 rounded",
          currentRating === "down" && "bg-danger-3 text-danger-9",
        )}
        onClick={() => onRate?.(messageId, "down")}
        aria-label="Thumbs down"
        type="button"
      >
        <ThumbsDown className="w-4 h-4" />
      </Button>
    </div>
  );
}

// =============================================================================
// Agent Trace Toggle
// =============================================================================

interface AgentTraceToggleProps {
  agentMetadata: AgentMetadata;
}

function AgentTraceToggle({ agentMetadata }: AgentTraceToggleProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const stepCount = agentMetadata.steps?.length ?? 0;

  return (
    <div data-testid="agent-trace-toggle" className="mt-2">
      <Button
        variant="secondary"
        className="flex items-center gap-1 text-xs"
        onClick={() => setIsExpanded(!isExpanded)}
        type="button"
      >
        {isExpanded ? (
          <ChevronUp className="w-3 h-3" />
        ) : (
          <ChevronDown className="w-3 h-3" />
        )}
        {stepCount} agent step{stepCount !== 1 ? "s" : ""}
      </Button>
      {isExpanded && (
        <div className="mt-2 p-2 bg-neutral-2 rounded text-xs">
          {agentMetadata.steps?.map((step, idx) => (
            <div key={idx} className="flex justify-between py-1">
              <span>{step.name}</span>
              <span className="text-neutral-9">{step.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Token Usage Display
// =============================================================================

interface TokenUsageDisplayProps {
  usage: { promptTokens?: number; completionTokens?: number };
}

function TokenUsageDisplay({ usage }: TokenUsageDisplayProps) {
  const total = (usage.promptTokens ?? 0) + (usage.completionTokens ?? 0);
  if (total === 0) return null;

  return (
    <div data-testid="token-usage" className="text-xs text-neutral-8 mt-1">
      {usage.promptTokens ?? 0} + {usage.completionTokens ?? 0} = {total} tokens
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

function FollowUpSuggestions({ suggestions, onSelect }: FollowUpSuggestionsProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div data-testid="follow-up-suggestions" className="flex flex-wrap gap-2 px-4 py-2">
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
// Message Item
// =============================================================================

interface MessageItemProps {
  message: ChatMessage;
  showRating?: boolean;
  showAgentTraces?: boolean;
  showTokenUsage?: boolean;
  currentRating?: "up" | "down" | null;
  onRateMessage?: (messageId: string, rating: "up" | "down") => void;
}

function MessageItem({
  message,
  showRating,
  showAgentTraces,
  showTokenUsage,
  currentRating,
  onRateMessage,
}: MessageItemProps) {
  const isAssistant = message.role === "assistant";
  const hasThinkingContent = isAssistant && !!message.thinkingContent?.trim();
  const hasAgentMetadata = isAssistant && !!message.agentMetadata?.steps?.length;
  const hasUsage = isAssistant && message.usage && (message.usage.promptTokens || message.usage.completionTokens);

  return (
    <div className="mb-2">
      {/* Thinking Trace (before message content) */}
      {hasThinkingContent && (
        <div className="px-4">
          <ThinkingTraceWrapper
            thinkingContent={message.thinkingContent!}
            thinkingTokens={message.thinkingTokens}
            modelName={message.modelName}
          />
        </div>
      )}

      {/* Message Bubble */}
      <MessageBubble message={message} />

      {/* Source Citations */}
      {message.sources && message.sources.length > 0 && (
        <div className="px-4">
          <SourceCitations sources={message.sources} />
        </div>
      )}

      {/* Token Usage */}
      {showTokenUsage && hasUsage && (
        <div className="px-4">
          <TokenUsageDisplay usage={message.usage!} />
        </div>
      )}

      {/* Agent Trace Toggle */}
      {showAgentTraces && hasAgentMetadata && (
        <div className="px-4">
          <AgentTraceToggle agentMetadata={message.agentMetadata!} />
        </div>
      )}

      {/* Rating Controls */}
      {showRating && isAssistant && (
        <div className="px-4">
          <RatingControls
            messageId={message.id}
            currentRating={currentRating}
            onRate={onRateMessage}
          />
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

function UnifiedMessageListImpl({
  messages,
  isLoading = false,
  isStreaming = false,
  showEmptyState = false,
  showRating = false,
  showAgentTraces = false,
  showTokenUsage = false,
  followUpSuggestions,
  messageRatings,
  onEditMessage: _onEditMessage,
  onDeleteMessage: _onDeleteMessage,
  onRegenerateMessage: _onRegenerateMessage,
  onRateMessage,
  onSuggestionSelect,
  className,
}: UnifiedMessageListProps) {
  const hasMessages = messages.length > 0;
  const shouldShowEmptyState = showEmptyState && !hasMessages && !isLoading;

  return (
    <div
      data-testid="unified-message-list"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
      className={cn("flex flex-col", className)}
    >
      {/* Loading State */}
      {isLoading && <LoadingIndicator />}

      {/* Empty State */}
      {shouldShowEmptyState && <EmptyState />}

      {/* Messages */}
      {hasMessages &&
        messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            showRating={showRating}
            showAgentTraces={showAgentTraces}
            showTokenUsage={showTokenUsage}
            currentRating={messageRatings?.[message.id]}
            onRateMessage={onRateMessage}
          />
        ))}

      {/* Typing Indicator (streaming) */}
      {isStreaming && <TypingIndicator />}

      {/* Follow-up Suggestions */}
      {!isStreaming && followUpSuggestions && followUpSuggestions.length > 0 && (
        <FollowUpSuggestions
          suggestions={followUpSuggestions}
          onSelect={onSuggestionSelect}
        />
      )}
    </div>
  );
}

export const UnifiedMessageList = memo(UnifiedMessageListImpl);
UnifiedMessageList.displayName = "UnifiedMessageList";
