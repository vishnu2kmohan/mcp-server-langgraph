/**
 * useSession Hook
 *
 * Manages playground session state using the REST API.
 */

import { useState, useCallback, useEffect } from 'react';
import { getPlaygroundAPI } from '../api/playground';
import type { SessionSummary, SessionDetails, SessionConfig } from '../api/types';

export interface UseSessionOptions {
  autoLoad?: boolean;
}

export interface UseSessionResult {
  // State
  sessions: SessionSummary[];
  activeSession: SessionDetails | null;
  isLoading: boolean;
  error: Error | null;

  // Actions
  loadSessions: () => Promise<void>;
  createSession: (name: string, config?: Partial<SessionConfig>) => Promise<SessionDetails>;
  selectSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  clearActiveSession: () => void;
}

export function useSession(options: UseSessionOptions = {}): UseSessionResult {
  const { autoLoad = false } = options;

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<SessionDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const api = getPlaygroundAPI();

  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.listSessions();
      setSessions(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load sessions'));
    } finally {
      setIsLoading(false);
    }
  }, [api]);

  const createSession = useCallback(
    async (name: string, config?: Partial<SessionConfig>): Promise<SessionDetails> => {
      setIsLoading(true);
      setError(null);
      try {
        const session = await api.createSession({ name, config });
        await loadSessions();
        setActiveSession(session);
        return session;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to create session');
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [api, loadSessions]
  );

  const selectSession = useCallback(
    async (sessionId: string): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const session = await api.getSession(sessionId);
        setActiveSession(session);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load session'));
      } finally {
        setIsLoading(false);
      }
    },
    [api]
  );

  const deleteSession = useCallback(
    async (sessionId: string): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        await api.deleteSession(sessionId);
        if (activeSession?.id === sessionId) {
          setActiveSession(null);
        }
        await loadSessions();
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to delete session'));
      } finally {
        setIsLoading(false);
      }
    },
    [api, activeSession, loadSessions]
  );

  const clearActiveSession = useCallback(() => {
    setActiveSession(null);
  }, []);

  // Auto-load sessions on mount
  useEffect(() => {
    if (autoLoad) {
      loadSessions();
    }
  }, [autoLoad, loadSessions]);

  return {
    sessions,
    activeSession,
    isLoading,
    error,
    loadSessions,
    createSession,
    selectSession,
    deleteSession,
    clearActiveSession,
  };
}
