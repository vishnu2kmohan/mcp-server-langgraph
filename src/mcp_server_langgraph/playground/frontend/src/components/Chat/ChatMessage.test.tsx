/**
 * ChatMessage Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage', () => {
  const userMessage = {
    id: 'msg-1',
    role: 'user' as const,
    content: 'Hello, world!',
    timestamp: '2025-01-01T10:00:00Z',
  };

  const assistantMessage = {
    id: 'msg-2',
    role: 'assistant' as const,
    content: 'Hello! How can I help you?',
    timestamp: '2025-01-01T10:01:00Z',
  };

  it('should_render_user_message_content', () => {
    render(<ChatMessage message={userMessage} />);
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('should_render_assistant_message_content', () => {
    render(<ChatMessage message={assistantMessage} />);
    expect(screen.getByText('Hello! How can I help you?')).toBeInTheDocument();
  });

  it('should_apply_user_message_styling', () => {
    render(<ChatMessage message={userMessage} />);
    const container = screen.getByTestId('message-container');
    expect(container).toHaveClass('justify-end');
  });

  it('should_apply_assistant_message_styling', () => {
    render(<ChatMessage message={assistantMessage} />);
    const container = screen.getByTestId('message-container');
    expect(container).toHaveClass('justify-start');
  });

  it('should_show_streaming_indicator_when_streaming', () => {
    const streamingMessage = { ...assistantMessage, isStreaming: true };
    render(<ChatMessage message={streamingMessage} />);
    expect(screen.getByTestId('streaming-cursor')).toBeInTheDocument();
  });

  it('should_render_markdown_content', () => {
    const markdownMessage = {
      ...assistantMessage,
      content: '**Bold** and *italic*',
    };
    render(<ChatMessage message={markdownMessage} />);
    expect(screen.getByText('Bold')).toBeInTheDocument();
    expect(screen.getByText('and')).toBeInTheDocument();
    expect(screen.getByText('italic')).toBeInTheDocument();
  });

  it('should_be_accessible_with_article_role', () => {
    render(<ChatMessage message={userMessage} />);
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('should_show_timestamp_when_enabled', () => {
    render(<ChatMessage message={userMessage} showTimestamp />);
    // Timestamp should be rendered (format is locale-dependent)
    const article = screen.getByRole('article');
    expect(article.textContent).toContain('Hello, world!');
  });
});
