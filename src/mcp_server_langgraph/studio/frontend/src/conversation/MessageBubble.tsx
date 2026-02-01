/**
 * MessageBubble - Phase 2
 *
 * Individual chat message bubble with user/assistant styling,
 * code block support, and action buttons.
 *
 * Design System Compliance:
 * - Uses CVA for role-based variants (user/assistant)
 * - Uses Motion.dev for message entrance animation
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import { useState, useCallback, useMemo, memo, lazy, Suspense } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { User, Bot, Copy, Check, Loader2 } from "lucide-react";
import type { ChatMessage } from "../types";
import { cn } from "../utils/cn";
import { listItemVariants } from "@/design-system/micro-interactions";

import { Button } from "@/components/UI";

// Lazy load LLMThinkingTrace for code-splitting
const LLMThinkingTrace = lazy(() =>
  import("@/components/Chat/LLMThinkingTrace").then((mod) => ({
    default: mod.LLMThinkingTrace,
  })),
);

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Message container variants based on role
 */
// eslint-disable-next-line react-refresh/only-export-components
export const messageContainerVariants = cva("flex gap-3 px-4 py-2", {
  variants: {
    role: {
      user: "justify-end",
      assistant: "justify-start",
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
export const avatarVariants = cva(
  "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
  {
    variants: {
      role: {
        user: "bg-primary-3 bg-primary-4 text-primary-10 dark:text-primary-7",
        assistant:
          "bg-insight-2 dark:bg-insight-a4 text-insight-10 dark:text-insight-9",
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
export const bubbleVariants = cva(
  "message-bubble relative max-w-[80%] rounded-2xl px-4 py-2",
  {
    variants: {
      role: {
        user: "user bg-primary-9 text-neutral-12",
        assistant: "assistant bg-neutral-2 text-neutral-12",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  },
);

/**
 * Timestamp variants based on role
 */
// eslint-disable-next-line react-refresh/only-export-components
export const timestampVariants = cva("text-xs mt-1", {
  variants: {
    role: {
      user: "text-primary-4",
      assistant: "text-neutral-9",
    },
  },
  defaultVariants: {
    role: "assistant",
  },
});

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
      <div className="flex items-center justify-between px-3 py-1 bg-neutral-4 rounded-t-lg text-xs text-neutral-9">
        <span>{language}</span>
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-5 rounded"
          data-testid="copy-code-button"
          type="button"
          onClick={handleCopy}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </Button>
      </div>
      <pre className="p-3 bg-neutral-3 rounded-b-lg overflow-x-auto text-sm text-neutral-9">
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
      <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none animation-delay-0" />
      <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none animation-delay-150" />
      <div className="w-2 h-2 bg-neutral-4 rounded-full animate-bounce motion-reduce:animate-none animation-delay-300" />
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
  const prefersReducedMotion = useReducedMotion();
  const [isHovered, setIsHovered] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);

  const isUser = message.role === "user";
  const role = isUser ? "user" : "assistant";
  const hasThinkingContent = !isUser && !!message.thinkingContent?.trim();
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
    <motion.div
      data-testid="message-container"
      className={cn(messageContainerVariants({ role }), className)}
      variants={prefersReducedMotion ? undefined : listItemVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Avatar */}
      {!isUser && (
        <div
          data-testid="ai-avatar"
          className={avatarVariants({ role: "assistant" })}
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
        className={bubbleVariants({ role })}
      >
        {isTyping ? (
          <TypingIndicator />
        ) : (
          <>
            {/* Thinking Trace (collapsed by default for historical messages) */}
            {hasThinkingContent && (
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 text-sm text-neutral-9 mb-2">
                    <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" />
                    Loading thinking trace...
                  </div>
                }
              >
                <LLMThinkingTrace
                  thinkingContent={message.thinkingContent!}
                  isExpanded={isThinkingExpanded}
                  onToggle={() => setIsThinkingExpanded((prev) => !prev)}
                  thinkingTokens={message.thinkingTokens}
                  modelName={message.modelName}
                  className="mb-2"
                />
              </Suspense>
            )}

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
                className={timestampVariants({ role })}
              >
                {formatTime(message.timestamp)}
              </div>
            )}

            {/* Copy button on hover */}
            {isHovered && !hasCodeBlock && (
              <Button
                variant="primary"
                data-testid="copy-message-button"
                type="button"
                onClick={handleCopy}
                className={cn(
                  "absolute -top-2 -right-2 p-1.5 rounded-full",
                  "bg-neutral-1 shadow-md",
                  "text-neutral-10 hover:text-neutral-11",
                  "transition-all",
                )}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
              </Button>
            )}
          </>
        )}
      </article>
      {/* User avatar */}
      {isUser && (
        <div
          data-testid="user-avatar"
          className={avatarVariants({ role: "user" })}
        >
          <User size={16} />
        </div>
      )}
    </motion.div>
  );
}

export const MessageBubble = memo(MessageBubbleImpl);
MessageBubble.displayName = "MessageBubble";
