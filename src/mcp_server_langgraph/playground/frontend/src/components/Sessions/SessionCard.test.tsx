/**
 * SessionCard Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionCard } from './SessionCard';

describe('SessionCard', () => {
  const mockSession = {
    id: 'session-1',
    name: 'Test Session',
    createdAt: '2025-01-01T10:00:00Z',
    updatedAt: '2025-01-01T12:00:00Z',
    messageCount: 5,
  };

  it('should_render_session_name', () => {
    render(<SessionCard session={mockSession} />);
    expect(screen.getByText('Test Session')).toBeInTheDocument();
  });

  it('should_render_message_count', () => {
    render(<SessionCard session={mockSession} />);
    expect(screen.getByText('5 messages')).toBeInTheDocument();
  });

  it('should_call_onClick_when_clicked', () => {
    const onClick = vi.fn();
    render(<SessionCard session={mockSession} onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledWith('session-1');
  });

  it('should_call_onDelete_when_delete_clicked', () => {
    const onDelete = vi.fn();
    render(<SessionCard session={mockSession} onDelete={onDelete} />);
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteButton);
    expect(onDelete).toHaveBeenCalledWith('session-1');
  });

  it('should_show_selected_state', () => {
    render(<SessionCard session={mockSession} isSelected />);
    const card = screen.getByRole('button');
    expect(card).toHaveClass('border-primary-500');
  });

  it('should_truncate_long_names', () => {
    const longSession = {
      ...mockSession,
      name: 'This is a very long session name that should be truncated',
    };
    render(<SessionCard session={longSession} />);
    const nameElement = screen.getByText(/This is a very long session/);
    expect(nameElement).toHaveClass('truncate');
  });

  it('should_be_accessible_as_button', () => {
    render(<SessionCard session={mockSession} />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });
});
