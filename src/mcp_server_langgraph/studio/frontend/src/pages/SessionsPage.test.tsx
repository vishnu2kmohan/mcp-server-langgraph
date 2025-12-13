/**
 * SessionsPage Tests
 *
 * TDD tests for the sessions list page.
 * Tests cover:
 * - Loading state
 * - Empty state
 * - Session list display
 * - Search functionality
 * - Create session
 * - Delete session
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SessionsPage } from './SessionsPage';
import * as sessionStoreModule from '../stores/sessionStore';

// Mock the session store
vi.mock('../stores/sessionStore');

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockUseSessionStore = vi.mocked(sessionStoreModule.useSessionStore);

const renderWithRouter = (component: React.ReactNode) => {
  return render(
    <MemoryRouter>{component}</MemoryRouter>
  );
};

describe('SessionsPage', () => {
  const mockFetchSessions = vi.fn();
  const mockCreateSession = vi.fn();
  const mockDeleteSession = vi.fn();
  const mockLoadSession = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseSessionStore.mockReturnValue({
      sessions: [],
      currentSession: null,
      isLoadingSessions: false,
      isLoadingSession: false,
      isSending: false,
      error: null,
      fetchSessions: mockFetchSessions,
      createSession: mockCreateSession,
      deleteSession: mockDeleteSession,
      loadSession: mockLoadSession,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      clearError: vi.fn(),
    });
  });

  describe('Header', () => {
    it('should display page title', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('Sessions')).toBeInTheDocument();
    });

    it('should display page description', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('Manage your chat sessions and conversation history')).toBeInTheDocument();
    });

    it('should have New Session button', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('New Session')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading sessions', () => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        isLoadingSessions: true,
        sessions: [],
      });

      renderWithRouter(<SessionsPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no sessions', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('No sessions yet')).toBeInTheDocument();
      expect(screen.getByText('Create a new session to get started')).toBeInTheDocument();
    });
  });

  describe('Session List', () => {
    const mockSessions = [
      { id: 'session-1', name: 'Session One', messageCount: 5, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
      { id: 'session-2', name: 'Session Two', messageCount: 10, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    ];

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        sessions: mockSessions,
      });
    });

    it('should display session names', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('Session One')).toBeInTheDocument();
      expect(screen.getByText('Session Two')).toBeInTheDocument();
    });

    it('should display message counts', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByText('5 messages')).toBeInTheDocument();
      expect(screen.getByText('10 messages')).toBeInTheDocument();
    });

    it('should call fetchSessions on mount', () => {
      renderWithRouter(<SessionsPage />);

      expect(mockFetchSessions).toHaveBeenCalled();
    });
  });

  describe('Search', () => {
    const mockSessions = [
      { id: 'session-1', name: 'Alpha Session', messageCount: 5, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
      { id: 'session-2', name: 'Beta Session', messageCount: 10, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    ];

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        sessions: mockSessions,
      });
    });

    it('should have search input', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByPlaceholderText('Search sessions...')).toBeInTheDocument();
    });

    it('should filter sessions by search query', () => {
      renderWithRouter(<SessionsPage />);

      const searchInput = screen.getByPlaceholderText('Search sessions...');
      fireEvent.change(searchInput, { target: { value: 'Alpha' } });

      expect(screen.getByText('Alpha Session')).toBeInTheDocument();
      expect(screen.queryByText('Beta Session')).not.toBeInTheDocument();
    });

    it('should show no results message when search has no matches', () => {
      renderWithRouter(<SessionsPage />);

      const searchInput = screen.getByPlaceholderText('Search sessions...');
      fireEvent.change(searchInput, { target: { value: 'xyz' } });

      expect(screen.getByText(/No sessions found matching/)).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('should have sort dropdown', () => {
      renderWithRouter(<SessionsPage />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
      expect(screen.getByText('Most Recent')).toBeInTheDocument();
    });
  });

  describe('Create Session', () => {
    it('should call createSession when New Session is clicked', async () => {
      mockCreateSession.mockResolvedValue('new-session-id');

      renderWithRouter(<SessionsPage />);

      fireEvent.click(screen.getByText('New Session'));

      await waitFor(() => {
        expect(mockCreateSession).toHaveBeenCalled();
      });
    });

    it('should navigate to chat after creating session', async () => {
      mockCreateSession.mockResolvedValue('new-session-id');

      renderWithRouter(<SessionsPage />);

      fireEvent.click(screen.getByText('New Session'));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/studio/chat');
      });
    });
  });

  describe('Open Session', () => {
    const mockSessions = [
      { id: 'session-1', name: 'Test Session', messageCount: 5, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    ];

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        sessions: mockSessions,
      });
    });

    it('should load session when clicked', async () => {
      renderWithRouter(<SessionsPage />);

      fireEvent.click(screen.getByText('Test Session'));

      await waitFor(() => {
        expect(mockLoadSession).toHaveBeenCalledWith('session-1');
      });
    });

    it('should navigate to chat after loading session', async () => {
      renderWithRouter(<SessionsPage />);

      fireEvent.click(screen.getByText('Test Session'));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/studio/chat');
      });
    });
  });

  describe('Delete Session', () => {
    const mockSessions = [
      { id: 'session-1', name: 'Test Session', messageCount: 5, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    ];

    beforeEach(() => {
      mockUseSessionStore.mockReturnValue({
        ...mockUseSessionStore(),
        sessions: mockSessions,
      });
      // Mock window.confirm
      vi.spyOn(window, 'confirm').mockReturnValue(true);
    });

    it('should call deleteSession when delete button is clicked', async () => {
      renderWithRouter(<SessionsPage />);

      // Find delete button by title
      const deleteButton = screen.getByTitle('Delete session');
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(mockDeleteSession).toHaveBeenCalledWith('session-1');
      });
    });
  });
});
