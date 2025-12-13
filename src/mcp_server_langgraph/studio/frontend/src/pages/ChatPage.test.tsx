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
import * as streamingChatModule from '../hooks/useStreamingChat';

// Mock the session store
vi.mock('../stores/sessionStore');

// Mock the streaming chat hook
vi.mock('../hooks/useStreamingChat');

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const mockUseSessionStore = vi.mocked(sessionStoreModule.useSessionStore);
const mockUseStreamingChat = vi.mocked(streamingChatModule.useStreamingChat);

describe('ChatPage', () => {
  const mockSendMessage = vi.fn();
  const mockAddMessage = vi.fn();
  const mockClearMessages = vi.fn();
  const mockClearError = vi.fn();
  const mockStartStream = vi.fn();
  const mockStopStream = vi.fn();
  const mockClearContent = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default streaming chat mock
    mockUseStreamingChat.mockReturnValue({
      isStreaming: false,
      streamingContent: '',
      error: null,
      startStream: mockStartStream,
      stopStream: mockStopStream,
      clearContent: mockClearContent,
    });

    // Default session store mock
    mockUseSessionStore.mockReturnValue({
      currentSession: null,
      sessions: [],
      isLoadingSession: false,
      isLoadingSessions: false,
      isSending: false,
      error: null,
      sendMessage: mockSendMessage,
      addMessage: mockAddMessage,
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
        currentSession: mockSession,
        sessions: [],
        isLoadingSession: false,
        isLoadingSessions: false,
        isSending: false,
        error: null,
        sendMessage: mockSendMessage,
        addMessage: mockAddMessage,
        clearMessages: mockClearMessages,
        clearError: mockClearError,
        fetchSessions: vi.fn(),
        createSession: vi.fn(),
        loadSession: vi.fn(),
        deleteSession: vi.fn(),
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

    it('should add user message and start stream when form is submitted', async () => {
      render(<ChatPage />);

      const input = screen.getByPlaceholderText('Type your message...');
      fireEvent.change(input, { target: { value: 'Hello' } });

      const form = input.closest('form')!;
      fireEvent.submit(form);

      await waitFor(() => {
        // Should add user message immediately
        expect(mockAddMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            role: 'user',
            content: 'Hello',
          })
        );
        // Should start streaming
        expect(mockStartStream).toHaveBeenCalledWith('session-1', 'Hello');
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

    it('should show thinking indicator when sending (legacy)', () => {
      mockUseSessionStore.mockReturnValue({
        currentSession: mockSession,
        sessions: [],
        isLoadingSession: false,
        isLoadingSessions: false,
        isSending: true,
        error: null,
        sendMessage: mockSendMessage,
        addMessage: mockAddMessage,
        clearMessages: mockClearMessages,
        clearError: mockClearError,
        fetchSessions: vi.fn(),
        createSession: vi.fn(),
        loadSession: vi.fn(),
        deleteSession: vi.fn(),
      });

      render(<ChatPage />);

      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });

    it('should show streaming content when streaming', () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: true,
        streamingContent: 'Hello from AI',
        error: null,
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      mockUseSessionStore.mockReturnValue({
        currentSession: mockSession,
        sessions: [],
        isLoadingSession: false,
        isLoadingSessions: false,
        isSending: false,
        error: null,
        sendMessage: mockSendMessage,
        addMessage: mockAddMessage,
        clearMessages: mockClearMessages,
        clearError: mockClearError,
        fetchSessions: vi.fn(),
        createSession: vi.fn(),
        loadSession: vi.fn(),
        deleteSession: vi.fn(),
      });

      render(<ChatPage />);

      expect(screen.getByText(/Hello from AI/)).toBeInTheDocument();
    });

    it('should disable input when streaming', () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: true,
        streamingContent: '',
        error: null,
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      mockUseSessionStore.mockReturnValue({
        currentSession: mockSession,
        sessions: [],
        isLoadingSession: false,
        isLoadingSessions: false,
        isSending: false,
        error: null,
        sendMessage: mockSendMessage,
        addMessage: mockAddMessage,
        clearMessages: mockClearMessages,
        clearError: mockClearError,
        fetchSessions: vi.fn(),
        createSession: vi.fn(),
        loadSession: vi.fn(),
        deleteSession: vi.fn(),
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

    const getErrorMockState = () => ({
      currentSession: mockSession,
      sessions: [],
      isLoadingSession: false,
      isLoadingSessions: false,
      isSending: false,
      error: 'Something went wrong',
      sendMessage: mockSendMessage,
      addMessage: mockAddMessage,
      clearMessages: mockClearMessages,
      clearError: mockClearError,
      fetchSessions: vi.fn(),
      createSession: vi.fn(),
      loadSession: vi.fn(),
      deleteSession: vi.fn(),
    });

    it('should display error banner when error exists', () => {
      mockUseSessionStore.mockReturnValue(getErrorMockState());

      render(<ChatPage />);

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should show dismiss button for errors', () => {
      mockUseSessionStore.mockReturnValue(getErrorMockState());

      render(<ChatPage />);

      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('should call clearError when dismiss is clicked', () => {
      mockUseSessionStore.mockReturnValue(getErrorMockState());

      render(<ChatPage />);

      fireEvent.click(screen.getByText('Dismiss'));
      expect(mockClearError).toHaveBeenCalled();
    });
  });

  describe('Auto Session Management', () => {
    it('should auto-create session when none exists', async () => {
      const mockCreateSession = vi.fn().mockResolvedValue('new-session-id');
      const mockFetchSessions = vi.fn();

      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: null,
        sessions: [],
        isLoadingSessions: false,
        createSession: mockCreateSession,
        fetchSessions: mockFetchSessions,
      });

      render(<ChatPage />);

      await waitFor(() => {
        expect(mockCreateSession).toHaveBeenCalledWith('New Chat');
      });
    });

    it('should load most recent session when sessions exist but none selected', async () => {
      const mockLoadSession = vi.fn();
      const mockFetchSessions = vi.fn();

      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: null,
        sessions: [
          { id: 'session-1', name: 'Test Session', createdAt: Date.now(), updatedAt: Date.now(), messageCount: 5 }
        ],
        isLoadingSessions: false,
        loadSession: mockLoadSession,
        fetchSessions: mockFetchSessions,
      });

      render(<ChatPage />);

      await waitFor(() => {
        expect(mockLoadSession).toHaveBeenCalledWith('session-1');
      });
    });

    it('should not auto-create when loading', () => {
      const mockCreateSession = vi.fn();
      const mockFetchSessions = vi.fn();

      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: null,
        sessions: [],
        isLoadingSessions: true,
        createSession: mockCreateSession,
        fetchSessions: mockFetchSessions,
      });

      render(<ChatPage />);

      expect(mockCreateSession).not.toHaveBeenCalled();
    });

    it('should not auto-create when session already exists', () => {
      const mockCreateSession = vi.fn();
      const mockFetchSessions = vi.fn();

      const mockSession = {
        id: 'session-1',
        name: 'Test Session',
        createdAt: new Date().toISOString(),
        messages: [],
      };

      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: mockSession,
        sessions: [],
        isLoadingSessions: false,
        createSession: mockCreateSession,
        fetchSessions: mockFetchSessions,
      });

      render(<ChatPage />);

      expect(mockCreateSession).not.toHaveBeenCalled();
    });

    it('should fetch sessions on mount when list is empty', async () => {
      const mockFetchSessions = vi.fn();
      const mockCreateSession = vi.fn().mockResolvedValue('new-session-id');

      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        currentSession: null,
        sessions: [],
        isLoadingSessions: false,
        createSession: mockCreateSession,
        fetchSessions: mockFetchSessions,
      });

      render(<ChatPage />);

      await waitFor(() => {
        expect(mockFetchSessions).toHaveBeenCalled();
      });
    });
  });
});
