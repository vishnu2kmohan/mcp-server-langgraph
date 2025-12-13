/**
 * ChatPage Tests
 *
 * TDD tests for the chat interface page.
 * Tests cover:
 * - Loading state
 * - No session state
 * - Message display
 * - Message sending
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPage } from './ChatPage';
import * as sessionStoreModule from '../stores/sessionStore';

// Mock the session store
vi.mock('../stores/sessionStore');

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const mockUseSessionStore = vi.mocked(sessionStoreModule.useSessionStore);

describe('ChatPage', () => {
  const mockSendMessage = vi.fn();
  const mockClearMessages = vi.fn();
  const mockClearError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseSessionStore.mockReturnValue({
      currentSession: null,
      sessions: [],
      isLoadingSession: false,
      isLoadingSessions: false,
      isSending: false,
      error: null,
      sendMessage: mockSendMessage,
      clearMessages: mockClearMessages,
      clearError: mockClearError,
      fetchSessions: vi.fn(),
      createSession: vi.fn(),
      loadSession: vi.fn(),
      deleteSession: vi.fn(),
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading session', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        isLoadingSession: true,
      });

      render(<ChatPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('No Session State', () => {
    it('should show no session message when no current session', () => {
      render(<ChatPage />);

      expect(screen.getByText('No Active Session')).toBeInTheDocument();
      expect(screen.getByText('Go to Sessions to create or select a session.')).toBeInTheDocument();
    });
  });

  describe('Session Loaded', () => {
    const mockSession = {
      id: 'session-1',
      name: 'Test Session',
      createdAt: new Date().toISOString(),
      messages: [],
    };

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
      });
    });

    it('should display session name in header', () => {
      render(<ChatPage />);

      expect(screen.getByText('Test Session')).toBeInTheDocument();
    });

    it('should display message count', () => {
      render(<ChatPage />);

      expect(screen.getByText('0 messages')).toBeInTheDocument();
    });

    it('should show empty state when no messages', () => {
      render(<ChatPage />);

      expect(screen.getByText('No messages yet. Start a conversation!')).toBeInTheDocument();
    });

    it('should show Clear button', () => {
      render(<ChatPage />);

      expect(screen.getByText('Clear')).toBeInTheDocument();
    });
  });

  describe('Messages Display', () => {
    const mockSessionWithMessages = {
      id: 'session-1',
      name: 'Test Session',
      createdAt: new Date().toISOString(),
      messages: [
        { id: 'msg-1', role: 'user' as const, content: 'Hello', timestamp: new Date().toISOString() },
        { id: 'msg-2', role: 'assistant' as const, content: 'Hi there!', timestamp: new Date().toISOString() },
      ],
    };

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSessionWithMessages,
      });
    });

    it('should display messages', () => {
      render(<ChatPage />);

      expect(screen.getByText('Hello')).toBeInTheDocument();
      expect(screen.getByText('Hi there!')).toBeInTheDocument();
    });

    it('should display correct message count', () => {
      render(<ChatPage />);

      expect(screen.getByText('2 messages')).toBeInTheDocument();
    });
  });

  describe('Message Sending', () => {
    const mockSession = {
      id: 'session-1',
      name: 'Test Session',
      createdAt: new Date().toISOString(),
      messages: [],
    };

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
      });
    });

    it('should have input field and send button', () => {
      render(<ChatPage />);

      expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });

    it('should disable send button when input is empty', () => {
      render(<ChatPage />);

      const sendButton = screen.getByRole('button', { name: /send/i });
      expect(sendButton).toBeDisabled();
    });

    it('should enable send button when input has text', () => {
      render(<ChatPage />);

      const input = screen.getByPlaceholderText('Type your message...');
      fireEvent.change(input, { target: { value: 'Hello' } });

      const sendButton = screen.getByRole('button', { name: /send/i });
      expect(sendButton).not.toBeDisabled();
    });

    it('should call sendMessage when form is submitted', async () => {
      render(<ChatPage />);

      const input = screen.getByPlaceholderText('Type your message...');
      fireEvent.change(input, { target: { value: 'Hello' } });

      const form = input.closest('form')!;
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith('Hello');
      });
    });

    it('should clear input after sending', async () => {
      render(<ChatPage />);

      const input = screen.getByPlaceholderText('Type your message...');
      fireEvent.change(input, { target: { value: 'Hello' } });

      const form = input.closest('form')!;
      fireEvent.submit(form);

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });
  });

  describe('Sending State', () => {
    const mockSession = {
      id: 'session-1',
      name: 'Test Session',
      createdAt: new Date().toISOString(),
      messages: [],
    };

    it('should show thinking indicator when sending', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        isSending: true,
      });

      render(<ChatPage />);

      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });

    it('should disable input when sending', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        isSending: true,
      });

      render(<ChatPage />);

      const input = screen.getByPlaceholderText('Type your message...');
      expect(input).toBeDisabled();
    });
  });

  describe('Error Handling', () => {
    const mockSession = {
      id: 'session-1',
      name: 'Test Session',
      createdAt: new Date().toISOString(),
      messages: [],
    };

    it('should display error banner when error exists', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        error: 'Something went wrong',
      });

      render(<ChatPage />);

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should show dismiss button for errors', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        error: 'Something went wrong',
      });

      render(<ChatPage />);

      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('should call clearError when dismiss is clicked', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        error: 'Something went wrong',
      });

      render(<ChatPage />);

      fireEvent.click(screen.getByText('Dismiss'));
      expect(mockClearError).toHaveBeenCalled();
    });
  });
});
