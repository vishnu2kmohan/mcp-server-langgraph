/**
 * SessionList Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionList } from './SessionList';

describe('SessionList', () => {
  const mockSessions = [
    { id: 'session-1', name: 'Session 1', createdAt: '2025-01-01', updatedAt: '2025-01-01', messageCount: 5 },
    { id: 'session-2', name: 'Session 2', createdAt: '2025-01-02', updatedAt: '2025-01-02', messageCount: 10 },
  ];

  it('should_render_all_sessions', () => {
    render(<SessionList sessions={mockSessions} />);
    expect(screen.getByText('Session 1')).toBeInTheDocument();
    expect(screen.getByText('Session 2')).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_sessions', () => {
    render(<SessionList sessions={[]} />);
    expect(screen.getByText(/no sessions/i)).toBeInTheDocument();
  });

  it('should_call_onSelect_when_session_clicked', () => {
    const onSelect = vi.fn();
    render(<SessionList sessions={mockSessions} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Session 1'));
    expect(onSelect).toHaveBeenCalledWith('session-1');
  });

  it('should_call_onDelete_when_delete_clicked', () => {
    const onDelete = vi.fn();
    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith('session-1');
  });

  it('should_highlight_selected_session', () => {
    render(<SessionList sessions={mockSessions} selectedId="session-1" />);
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toHaveClass('border-primary-500');
  });

  it('should_have_listbox_role_for_accessibility', () => {
    render(<SessionList sessions={mockSessions} />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('should_show_loading_state', () => {
    render(<SessionList sessions={[]} isLoading />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
