/**
 * ChatInterface Component
 *
 * Complete chat interface with message stream and input.
 * Integrates with MCP tools for agent communication.
 */

import React, { useState, useCallback, useRef } from 'react';
import { useMCPTools } from '../../hooks/useMCPTools';
import { useMCPHost } from '../../contexts/MCPHostContext';
import type { ChatMessage } from '../../api/types';
import { ChatStream } from './ChatStream';
import { ChatInput } from './ChatInput';

export interface ChatInterfaceProps {
  sessionId?: string;
  className?: string;
}

export function ChatInterface({
  sessionId,
  className,
}: ChatInterfaceProps): React.ReactElement {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const { agentChat } = useMCPTools();
  const { primaryServerId, servers } = useMCPHost();

  const isConnected = primaryServerId && servers.get(primaryServerId)?.status === 'connected';

  const handleSend = useCallback(
    async (content: string) => {
      // Add user message
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Create assistant message for streaming
      const assistantMessageId = `msg-${Date.now()}-assistant`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Start streaming
      setIsStreaming(true);
      abortControllerRef.current = new AbortController();

      try {
        await agentChat(
          content,
          (chunk) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          },
          sessionId
        );
      } catch (error) {
        // Handle abort or error
        if (error instanceof DOMException && error.name === 'AbortError') {
          // User cancelled - keep partial response
        } else {
          // Error - add error message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content:
                      msg.content || 'Sorry, there was an error processing your request.',
                    isStreaming: false,
                  }
                : msg
            )
          );
        }
      } finally {
        // Mark streaming complete
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
          )
        );
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [agentChat, sessionId]
  );

  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return (
    <main
      className={`flex flex-col h-full bg-white dark:bg-dark-bg ${className || ''}`}
      role="main"
      aria-label="Chat interface"
    >
      <ChatStream
        messages={messages}
        isStreaming={isStreaming}
        onStop={handleStop}
      />
      <ChatInput
        onSend={handleSend}
        disabled={isStreaming || !isConnected}
        placeholder={
          !isConnected
            ? 'Connect to a server to start chatting...'
            : isStreaming
            ? 'Wait for response...'
            : 'Type a message... (Enter to send, Shift+Enter for new line)'
        }
      />
    </main>
  );
}
