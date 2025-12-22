/**
 * useChatAutoScroll Hook
 *
 * Encapsulates auto-scroll logic for chat message lists.
 * Automatically scrolls to the bottom when new messages arrive
 * or streaming content updates.
 *
 * Extracted from ChatMessages.tsx for reusability.
 *
 * @example
 * ```tsx
 * const { messagesEndRef } = useChatAutoScroll(messages, streamingContent);
 *
 * return (
 *   <div>
 *     {messages.map(...)}
 *     <div ref={messagesEndRef} />
 *   </div>
 * );
 * ```
 */

import { useRef, useEffect } from "react";

/**
 * Return type for the useChatAutoScroll hook
 */
export interface UseChatAutoScrollReturn {
  /** Ref to attach to the element at the end of the message list */
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

/**
 * Hook for auto-scrolling chat message lists
 *
 * @param messages - Array of messages (any type with at least an id)
 * @param streamingContent - Optional streaming content that triggers scroll
 * @returns Object with messagesEndRef to attach to scroll target
 */
export function useChatAutoScroll<T>(
  messages: T[],
  streamingContent?: string
): UseChatAutoScrollReturn {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages or streaming content change
  useEffect(() => {
    // Guard against scrollIntoView not being available (e.g., in jsdom tests)
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  return { messagesEndRef };
}

export default useChatAutoScroll;
