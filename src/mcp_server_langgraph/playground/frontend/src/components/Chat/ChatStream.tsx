/**
 * ChatStream Component
 *
 * Displays a stream of chat messages with auto-scroll
 * and accessibility features.
 */

import React, { useRef, useEffect } from 'react';
import type { ChatMessage as ChatMessageType } from '../../api/types';
import { ChatMessage } from './ChatMessage';

// Stop icon
function StopIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z"
      />
    </svg>
  );
}

export interface ChatStreamProps {
  messages: ChatMessageType[];
  isStreaming?: boolean;
  isLoading?: boolean;
  onStop?: () => void;
}

export function ChatStream({
  messages,
  isStreaming = false,
  isLoading = false,
  onStop,
}: ChatStreamProps): React.ReactElement {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-gray-500 dark:text-dark-textMuted animate-pulse">
          Loading messages...
        </div>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500 dark:text-dark-textMuted">
          <p className="text-lg">Start a conversation</p>
          <p className="text-sm mt-1">Type a message below to begin</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Message List */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-4"
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Stop Button */}
      {isStreaming && onStop && (
        <div className="flex justify-center p-2 border-t border-gray-200 dark:border-dark-border">
          <button
            onClick={onStop}
            className="btn btn-secondary flex items-center gap-2"
            aria-label="Stop generating"
          >
            <StopIcon className="w-4 h-4" />
            Stop generating
          </button>
        </div>
      )}
    </div>
  );
}
