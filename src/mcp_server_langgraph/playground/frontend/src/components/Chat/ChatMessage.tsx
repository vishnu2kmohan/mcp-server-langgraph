/**
 * ChatMessage Component
 *
 * Displays a single chat message with role-based styling
 * and markdown rendering support.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import clsx from 'clsx';
import type { ChatMessage as ChatMessageType } from '../../api/types';
import { AgentInfoBadge } from './AgentInfoBadge';

function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export interface ChatMessageProps {
  message: ChatMessageType;
  showTimestamp?: boolean;
}

export function ChatMessage({
  message,
  showTimestamp = false,
}: ChatMessageProps): React.ReactElement {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx('flex w-full', isUser ? 'justify-end' : 'justify-start')}
      data-testid="message-container"
    >
      <article
        className={clsx(
          'max-w-[80%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-primary-500 text-white rounded-br-md'
            : 'bg-gray-100 dark:bg-dark-surface text-gray-900 dark:text-dark-text rounded-bl-md'
        )}
        role="article"
        aria-label={`${message.role} message`}
      >
        {/* Message Content */}
        <div className={clsx('prose prose-sm max-w-none', isUser && 'prose-invert')}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Streaming Cursor */}
        {message.isStreaming && (
          <span
            className="inline-block w-2 h-5 bg-current animate-pulse ml-1"
            data-testid="streaming-cursor"
            aria-hidden="true"
          />
        )}

        {/* Timestamp */}
        {showTimestamp && (
          <div
            className={clsx(
              'text-xs mt-1',
              isUser ? 'text-white/70' : 'text-gray-500 dark:text-dark-textMuted'
            )}
          >
            {formatTime(message.timestamp)}
          </div>
        )}

        {/* P4: Agent Transparency - Show metadata for assistant messages */}
        {!isUser && message.agentMetadata && (
          <AgentInfoBadge metadata={message.agentMetadata} />
        )}
      </article>
    </div>
  );
}
