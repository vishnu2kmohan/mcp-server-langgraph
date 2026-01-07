/**
 * MessageBubble - Phase 2
 *
 * Individual chat message bubble with user/assistant styling,
 * code block support, and action buttons.
 */
import { useState, useCallback, useMemo, memo } from "react";
import { User, Bot, Copy, Check } from "lucide-react";
import type { ChatMessage } from "../types";
import { cn } from "../utils/cn";

// Re-export ChatMessage for backwards compatibility
export type { ChatMessage };

export interface MessageBubbleProps {
  message: ChatMessage;
  showTimestamp?: boolean;
  isTyping?: boolean;
  onCopy?: (message: ChatMessage) => void;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function parseCodeBlocks(
  content: string | null | undefined,
): Array<{ type: "text" | "code"; content: string; language?: string }> {
  // Handle null/undefined content gracefully
  if (!content) {
    return [{ type: "text", content: "" }];
  }

  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  const parts: Array<{
    type: "text" | "code";
    content: string;
    language?: string;
  }> = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: "text",
        content: content.slice(lastIndex, match.index),
      });
    }
    const codeContent = match[2];
    if (codeContent !== undefined) {
      parts.push({
        type: "code",
        content: codeContent,
        language: match[1] || "plaintext",
      });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", content: content.slice(lastIndex) });
  }

  return parts.length > 0 ? parts : [{ type: "text", content }];
}

// =============================================================================
// Code Block Component
// =============================================================================

function CodeBlock({
  content,
  language,
}: {
  content: string;
  language?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [content]);

  return (
    <div data-testid="code-block" className="relative my-2">
      <div className="flex items-center justify-between px-3 py-1 bg-gray-700 dark:bg-gray-900 rounded-t-lg text-xs text-gray-400">
        <span>{language}</span>
        <button
          data-testid="copy-code-button"
          type="button"
          onClick={handleCopy}
          className="p-1 hover:bg-gray-600 rounded transition-colors"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
      <pre className="p-3 bg-gray-800 dark:bg-gray-950 rounded-b-lg overflow-x-auto text-sm text-gray-100">
        <code>{content}</code>
      </pre>
    </div>
  );
}

// =============================================================================
// Typing Indicator
// =============================================================================

function TypingIndicator() {
  return (
    <div data-testid="typing-indicator" className="flex gap-1 py-2">
      <div
        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
        style={{ animationDelay: "0ms" }}
      />
      <div
        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
        style={{ animationDelay: "150ms" }}
      />
      <div
        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

function MessageBubbleImpl({
  message,
  showTimestamp = false,
  isTyping = false,
  onCopy,
  className,
}: MessageBubbleProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [copied, setCopied] = useState(false);

  const isUser = message.role === "user";
  const parsedContent = useMemo(
    () => parseCodeBlocks(message.content),
    [message.content],
  );
  const hasCodeBlock = parsedContent.some((part) => part.type === "code");

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
    } catch {
      // Clipboard API may not be available in all environments
    }
    setCopied(true);
    onCopy?.(message);
    setTimeout(() => setCopied(false), 2000);
  }, [message, onCopy]);

  return (
    <div
      data-testid="message-container"
      className={cn(
        "flex gap-3 px-4 py-2",
        isUser ? "justify-end" : "justify-start",
        className,
      )}
    >
      {/* Avatar */}
      {!isUser && (
        <div
          data-testid="ai-avatar"
          className={cn(
            "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
            "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400",
          )}
        >
          <Bot size={16} />
        </div>
      )}

      {/* Message bubble */}
      <article
        data-testid="message-bubble"
        role="article"
        aria-label={`${message.role} message`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          "message-bubble relative max-w-[80%] rounded-2xl px-4 py-2",
          isUser && "user bg-primary-500 text-white",
          !isUser &&
            "assistant bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100",
        )}
      >
        {isTyping ? (
          <TypingIndicator />
        ) : (
          <>
            {/* Content */}
            <div className="text-sm leading-relaxed">
              {parsedContent.map((part, index) =>
                part.type === "code" ? (
                  <CodeBlock
                    key={index}
                    content={part.content}
                    language={part.language}
                  />
                ) : (
                  <span key={index}>{part.content}</span>
                ),
              )}
            </div>

            {/* Timestamp */}
            {showTimestamp && (
              <div
                data-testid="message-timestamp"
                className={cn(
                  "text-xs mt-1",
                  isUser ? "text-primary-200" : "text-gray-400",
                )}
              >
                {formatTime(message.timestamp)}
              </div>
            )}

            {/* Copy button on hover */}
            {isHovered && !hasCodeBlock && (
              <button
                data-testid="copy-message-button"
                type="button"
                onClick={handleCopy}
                className={cn(
                  "absolute -top-2 -right-2 p-1.5 rounded-full",
                  "bg-white dark:bg-gray-700 shadow-md",
                  "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
                  "transition-all",
                )}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
              </button>
            )}
          </>
        )}
      </article>

      {/* User avatar */}
      {isUser && (
        <div
          data-testid="user-avatar"
          className={cn(
            "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
            "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400",
          )}
        >
          <User size={16} />
        </div>
      )}
    </div>
  );
}

export const MessageBubble = memo(MessageBubbleImpl);
MessageBubble.displayName = "MessageBubble";
