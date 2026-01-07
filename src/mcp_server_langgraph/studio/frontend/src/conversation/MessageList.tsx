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
import { ErrorBoundary } from "../components/ErrorBoundary/ErrorBoundary";
import { cn } from "../utils/cn";

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

      return (
        <div
          key={message.id}
          className="flex gap-3 px-4 py-2"
          data-testid="rich-message"
        >
          <div
            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
            data-testid="ai-avatar"
          >
            <Bot size={16} />
          </div>
          <div className="text-sm leading-relaxed max-w-none prose prose-sm dark:prose-invert prose-p:my-1 prose-headings:my-2">
            <ErrorBoundary
              name="MarkdownContent"
              fallback={
                <div
                  className="flex items-center gap-2 px-3 py-2 text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 rounded border border-amber-200 dark:border-amber-800"
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
      className={cn("flex flex-col flex-1 overflow-y-auto p-4", className)}
    >
      {/* Empty state */}
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center flex-1 text-gray-500 dark:text-gray-400">
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
          <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Streaming indicator */}
      {isStreaming && (
        <div
          data-testid="streaming-indicator"
          className="flex items-center gap-2 py-2 px-4 text-gray-500 dark:text-gray-400"
        >
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"
              style={{ animationDelay: "150ms" }}
            />
            <div
              className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"
              style={{ animationDelay: "300ms" }}
            />
          </div>
          <span className="text-sm">AI is typing...</span>
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={endRef} />

      {/* Scroll to bottom button */}
      {isScrolledUp && (
        <button
          data-testid="scroll-to-bottom-button"
          type="button"
          onClick={handleScrollToBottom}
          className={cn(
            "fixed bottom-24 right-8 p-2 rounded-full",
            "bg-white dark:bg-gray-800 shadow-lg",
            "text-gray-600 dark:text-gray-300",
            "hover:bg-gray-100 dark:hover:bg-gray-700",
            "transition-all",
          )}
          aria-label="Scroll to bottom"
        >
          <ChevronDown size={20} />
        </button>
      )}
    </div>
  );
}
