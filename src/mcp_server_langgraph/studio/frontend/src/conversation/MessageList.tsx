/**
 * MessageList - Phase 2
 *
 * Virtualized message list component with auto-scroll,
 * loading states, and message grouping.
 */
import { useRef, useEffect, useMemo } from "react";
import { ChevronDown } from "lucide-react";
import { MessageBubble, type ChatMessage } from "./MessageBubble";
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
  onScrollToBottom,
  className,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Group messages if enabled
  const messageGroups = useMemo(
    () => (groupMessages ? groupMessagesByRole(messages) : null),
    [messages, groupMessages],
  );

  // Auto-scroll to bottom when new messages arrive (unless user scrolled up)
  useEffect(() => {
    if (!isScrolledUp && endRef.current?.scrollIntoView) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isScrolledUp]);

  const handleScrollToBottom = () => {
    if (endRef.current?.scrollIntoView) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
    onScrollToBottom?.();
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
              {group.messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </div>
          ))
        : messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

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
