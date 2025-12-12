/**
 * ChatInterface Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInterface } from './ChatInterface';

// Mock hooks
const mockAgentChat = vi.fn();
vi.mock('../../hooks/useMCPTools', () => ({
  useMCPTools: vi.fn(() => ({
    agentChat: mockAgentChat,
    tools: [],
  })),
}));

vi.mock('../../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    primaryServerId: 'primary',
    servers: new Map([['primary', { status: 'connected' }]]),
  })),
}));

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAgentChat.mockResolvedValue(undefined);
  });

  it('should_render_input_and_message_area', () => {
    render(<ChatInterface />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    // Empty state doesn't have log role, but main does
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('should_show_empty_state_initially', () => {
    render(<ChatInterface />);
    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });

  it('should_add_user_message_when_sent', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('should_call_agentChat_when_message_sent', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Test message');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockAgentChat).toHaveBeenCalled();
    });
  });

  it('should_disable_input_when_streaming', async () => {
    mockAgentChat.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    const user = userEvent.setup();
    render(<ChatInterface />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    // Input should be disabled while streaming
    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeDisabled();
    });
  });

  it('should_have_main_landmark_role', () => {
    render(<ChatInterface />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('should_show_stop_button_when_streaming', async () => {
    mockAgentChat.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    const user = userEvent.setup();
    render(<ChatInterface />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument();
    });
  });
});
