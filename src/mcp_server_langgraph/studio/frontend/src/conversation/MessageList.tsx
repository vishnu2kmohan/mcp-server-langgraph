/**
 * MessageList - Phase 2
 *
 * Virtualized message list component with auto-scroll,
 * loading states, and message grouping.
 */
import { useRef, useEffect, useMemo } from "react";
import { ChevronDown, Bot, AlertTriangle } from "lucide-react";
import { MessageBubble, type ChatMessage } from "./MessageBubble";
import { MarkdownContent } from "../components/Chat/MarkdownContent";
import { SourceCitations } from "../components/Chat/SourceCitations";
import { ErrorBoundary } from "../components/ErrorBoundary/ErrorBoundary";
import { cn } from "../utils/cn";
import { dedupeByDomain, sortByRelevance } from "./sourceUtils";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  isStreaming?: boolean;
  isScrolledUp?: boolean;
  groupMessages?: boolean;
  /** Enable rich content rendering for assistant messages (Markdown, diagrams, charts) */
  enableRichContent?: boolean;
  /** Group source citations by type (web vs knowledge base) */
  groupSourcesByType?: boolean;
  onScrollToBottom?: () => void;
  className?: string;
}

interface MessageGroup {
  role: ChatMessage["role"];
  messages: ChatMessage[];
}

// =============================================================================
// Utility
// =============================================================================

function groupMessagesByRole(messages: ChatMessage[]): MessageGroup[] {
  const groups: MessageGroup[] = [];
  let currentGroup: MessageGroup | null = null;

  for (const message of messages) {
    if (!currentGroup || currentGroup.role !== message.role) {
      currentGroup = { role: message.role, messages: [message] };
      groups.push(currentGroup);
    } else {
      currentGroup.messages.push(message);
    }
  }

  return groups;
}

// =============================================================================
// Component
// =============================================================================

export function MessageList({
  messages,
  isLoading = false,
  isStreaming = false,
  isScrolledUp = false,
  groupMessages = false,
  enableRichContent = true,
  groupSourcesByType = true,
  onScrollToBottom,
  className,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollRafRef = useRef<number | null>(null);

  const lastMessage = messages[messages.length - 1];
  const streamingContentKey =
    isStreaming &&
    (lastMessage?.isStreaming || lastMessage?.id === "streaming-message")
      ? lastMessage.content.length
      : 0;

  // Group messages if enabled
  const messageGroups = useMemo(
    () => (groupMessages ? groupMessagesByRole(messages) : null),
    [messages, groupMessages],
  );

  // Auto-scroll to bottom when new messages arrive (unless user scrolled up).
  // During streaming, keep the bottom pinned without continuously animating.
  useEffect(() => {
    if (isScrolledUp) return;
    if (typeof endRef.current?.scrollIntoView !== "function") return;

    const behavior: ScrollBehavior = isStreaming ? "auto" : "smooth";

    if (scrollRafRef.current !== null) {
      if (typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(scrollRafRef.current);
      } else {
        window.clearTimeout(scrollRafRef.current);
      }
    }

    const schedule =
      typeof requestAnimationFrame === "function"
        ? (cb: () => void) => requestAnimationFrame(() => cb())
        : (cb: () => void) => window.setTimeout(cb, 0);

    scrollRafRef.current = schedule(() => {
      endRef.current?.scrollIntoView({ behavior, block: "end" });
      scrollRafRef.current = null;
    });

    return () => {
      if (scrollRafRef.current !== null) {
        if (typeof cancelAnimationFrame === "function") {
          cancelAnimationFrame(scrollRafRef.current);
        } else {
          window.clearTimeout(scrollRafRef.current);
        }
        scrollRafRef.current = null;
      }
    };
  }, [
    messages.length,
    lastMessage?.id,
    streamingContentKey,
    isStreaming,
    isScrolledUp,
  ]);

  const handleScrollToBottom = () => {
    if (endRef.current?.scrollIntoView) {
      endRef.current.scrollIntoView({
        behavior: isStreaming ? "auto" : "smooth",
        block: "end",
      });
    }
    onScrollToBottom?.();
  };

  // Render a single message - uses MarkdownContent for assistant messages when enabled
  const renderMessage = (message: ChatMessage) => {
    // For assistant messages with rich content enabled, use MarkdownContent
    if (message.role === "assistant" && enableRichContent) {
      const isStreamingMessage =
        isStreaming &&
        (message.isStreaming || message.id === "streaming-message");

      // Deduplicate sources by domain, then sort by relevance for cleaner display
      const displaySources = message.sources
        ? sortByRelevance(dedupeByDomain(message.sources))
        : [];

      return (
        <div
          key={message.id}
          className="flex gap-3 px-4 py-2"
          data-testid="rich-message"
        >
          <div
            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-insight-2 dark:bg-insight-a4 text-insight-10 dark:text-insight-9"
            data-testid="ai-avatar"
          >
            <Bot size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm leading-relaxed max-w-none prose prose-sm dark:prose-invert prose-p:my-1 prose-headings:my-2">
              <ErrorBoundary
                name="MarkdownContent"
                fallback={
                  <div
                    className="flex items-center gap-2 px-3 py-2 text-sm text-warning-10 dark:text-warning-6 bg-warning-3 bg-warning-3 rounded border border-warning-6 dark:border-warning-11"
                    role="alert"
                    data-testid="message-render-error"
                  >
                    <AlertTriangle size={16} className="flex-shrink-0" />
                    <span>Failed to render message content</span>
                  </div>
                }
              >
                {isStreamingMessage ? (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                ) : (
                  <MarkdownContent
                    content={message.content}
                    enableInteractiveArtifacts
                  />
                )}
              </ErrorBoundary>
            </div>

            {/* Source Citations */}
            <SourceCitations
              sources={displaySources}
              groupByType={groupSourcesByType}
            />
          </div>
        </div>
      );
    }

    // For user messages or when rich content is disabled, use MessageBubble
    return <MessageBubble key={message.id} message={message} />;
  };

  return (
    <div
      data-testid="message-list"
      ref={containerRef}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
      className={cn("relative flex flex-col flex-1 overflow-y-auto p-4", className)}
    >
      {/* Empty state */}
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center flex-1 text-neutral-10">
          <p>No messages yet. Start a conversation!</p>
        </div>
      )}
      {/* Grouped messages */}
      {groupMessages && messageGroups
        ? messageGroups.map((group, groupIndex) => (
            <div
              key={`group-${groupIndex}`}
              data-testid="message-group"
              className="mb-2"
            >
              {group.messages.map((message) => renderMessage(message))}
            </div>
          ))
        : messages.map((message) => renderMessage(message))}
      {/* Loading indicator */}
      {isLoading && (
        <div
          data-testid="loading-indicator"
          className="flex items-center justify-center py-4"
        >
          <div className="w-6 h-6 border-2 border-primary-9 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      {/* Streaming indicator */}
      {isStreaming && (
        <div
          data-testid="streaming-indicator"
          className="flex items-center gap-2 py-2 px-4 text-neutral-10"
        >
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-neutral-4 rounded-full animate-pulse animation-delay-0" />
            <div className="w-2 h-2 bg-neutral-4 rounded-full animate-pulse animation-delay-150" />
            <div className="w-2 h-2 bg-neutral-4 rounded-full animate-pulse animation-delay-300" />
          </div>
          <span className="text-sm">AI is typing...</span>
        </div>
      )}
      {/* Scroll anchor */}
      <div ref={endRef} />
      {/* Scroll to bottom button - uses sticky positioning to stay above DevTools */}
      {isScrolledUp && (
        <Button
          variant="ghost"
          size="icon"
          data-testid="scroll-to-bottom-button"
          type="button"
          onClick={handleScrollToBottom}
          className={cn(
            "sticky bottom-4 self-end mr-4 rounded-full",
            "bg-neutral-1 shadow-lg",
            "z-10",
          )}
          aria-label="Scroll to bottom"
        >
          <ChevronDown size={20} />
        </Button>
      )}
    </div>
  );
}
