/**
 * SessionList Component
 *
 * Displays a list of session cards with selection support.
 */

import React from 'react';
import type { SessionSummary } from '../../api/types';
import { SessionCard } from './SessionCard';

export interface SessionListProps {
  sessions: SessionSummary[];
  selectedId?: string;
  isLoading?: boolean;
  onSelect?: (sessionId: string) => void;
  onDelete?: (sessionId: string) => void;
}

export function SessionList({
  sessions,
  selectedId,
  isLoading = false,
  onSelect,
  onDelete,
}: SessionListProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <div className="animate-pulse">Loading sessions...</div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <p>No sessions yet</p>
        <p className="text-sm mt-1">Create a new session to get started</p>
      </div>
    );
  }

  return (
    <div
      className="p-2 space-y-2"
      role="listbox"
      aria-label="Sessions"
    >
      {sessions.map((session) => (
        <SessionCard
          key={session.id}
          session={session}
          isSelected={session.id === selectedId}
          onClick={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
