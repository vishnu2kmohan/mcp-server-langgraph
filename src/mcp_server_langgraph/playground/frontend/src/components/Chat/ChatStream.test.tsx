/**
 * ChatStream Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatStream } from './ChatStream';

describe('ChatStream', () => {
  const mockMessages = [
    { id: 'msg-1', role: 'user' as const, content: 'Hello', timestamp: '2025-01-01T10:00:00Z' },
    { id: 'msg-2', role: 'assistant' as const, content: 'Hi there!', timestamp: '2025-01-01T10:01:00Z' },
  ];

  it('should_render_all_messages', () => {
    render(<ChatStream messages={mockMessages} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_messages', () => {
    render(<ChatStream messages={[]} />);
    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });

  it('should_have_aria_live_for_new_messages', () => {
    render(<ChatStream messages={mockMessages} />);
    const region = screen.getByRole('log');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('should_show_stop_button_when_streaming', () => {
    const onStop = vi.fn();
    render(<ChatStream messages={mockMessages} isStreaming onStop={onStop} />);
    expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument();
  });

  it('should_call_onStop_when_stop_clicked', () => {
    const onStop = vi.fn();
    render(<ChatStream messages={mockMessages} isStreaming onStop={onStop} />);
    fireEvent.click(screen.getByRole('button', { name: /stop/i }));
    expect(onStop).toHaveBeenCalled();
  });

  it('should_not_show_stop_button_when_not_streaming', () => {
    render(<ChatStream messages={mockMessages} />);
    expect(screen.queryByRole('button', { name: /stop/i })).not.toBeInTheDocument();
  });

  it('should_show_loading_indicator_when_loading', () => {
    render(<ChatStream messages={[]} isLoading />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
