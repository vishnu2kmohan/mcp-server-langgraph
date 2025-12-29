/**
 * useSession Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useSession } from './useSession';

const mockPlaygroundAPI = {
  listSessions: vi.fn(),
  getSession: vi.fn(),
  createSession: vi.fn(),
  deleteSession: vi.fn(),
};

vi.mock('../api/playground', () => ({
  getPlaygroundAPI: () => mockPlaygroundAPI,
}));

describe('useSession', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPlaygroundAPI.listSessions.mockResolvedValue([]);
  });

  it('should_start_with_empty_sessions', () => {
    const { result } = renderHook(() => useSession());
    expect(result.current.sessions).toEqual([]);
    expect(result.current.activeSession).toBeNull();
  });

  it('should_load_sessions_on_mount', async () => {
    const sessions = [
      { id: 'session-1', name: 'Session 1', createdAt: '2025-01-01', updatedAt: '2025-01-01', messageCount: 5 },
    ];
    mockPlaygroundAPI.listSessions.mockResolvedValue(sessions);

    const { result } = renderHook(() => useSession({ autoLoad: true }));

    await waitFor(() => {
      expect(result.current.sessions).toEqual(sessions);
    });
  });

  it('should_create_new_session', async () => {
    const newSession = {
      id: 'session-new',
      name: 'New Session',
      config: { modelProvider: 'anthropic', modelName: 'claude-3', temperature: 0.7, maxTokens: 4000 },
      messages: [],
      createdAt: '2025-01-01',
      updatedAt: '2025-01-01',
    };
    mockPlaygroundAPI.createSession.mockResolvedValue(newSession);
    mockPlaygroundAPI.listSessions.mockResolvedValue([]);

    const { result } = renderHook(() => useSession());

    await act(async () => {
      await result.current.createSession('New Session');
    });

    expect(mockPlaygroundAPI.createSession).toHaveBeenCalledWith({ name: 'New Session', config: undefined });
  });

  it('should_select_session', async () => {
    const session = {
      id: 'session-1',
      name: 'Session 1',
      config: { modelProvider: 'anthropic', modelName: 'claude-3', temperature: 0.7, maxTokens: 4000 },
      messages: [],
      createdAt: '2025-01-01',
      updatedAt: '2025-01-01',
    };
    mockPlaygroundAPI.getSession.mockResolvedValue(session);

    const { result } = renderHook(() => useSession());

    await act(async () => {
      await result.current.selectSession('session-1');
    });

    expect(result.current.activeSession).toEqual(session);
  });

  it('should_delete_session', async () => {
    mockPlaygroundAPI.deleteSession.mockResolvedValue(undefined);
    mockPlaygroundAPI.listSessions.mockResolvedValue([]);

    const { result } = renderHook(() => useSession());

    await act(async () => {
      await result.current.deleteSession('session-1');
    });

    expect(mockPlaygroundAPI.deleteSession).toHaveBeenCalledWith('session-1');
  });

  it('should_handle_loading_state', async () => {
    mockPlaygroundAPI.listSessions.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve([]), 100))
    );

    const { result } = renderHook(() => useSession({ autoLoad: true }));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should_handle_error_state', async () => {
    mockPlaygroundAPI.listSessions.mockRejectedValue(new Error('Failed to load'));

    const { result } = renderHook(() => useSession({ autoLoad: true }));

    await waitFor(() => {
      expect(result.current.error).toBeDefined();
    });
  });
});
