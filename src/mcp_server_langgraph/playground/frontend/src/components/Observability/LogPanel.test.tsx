/**
 * LogPanel Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LogPanel } from './LogPanel';
import type { LogEntry } from '../../api/types';

describe('LogPanel', () => {
  const mockLogs: LogEntry[] = [
    { id: 'log-1', timestamp: '2025-01-01T10:00:00Z', level: 'info', message: 'Info message', logger: 'test' },
    { id: 'log-2', timestamp: '2025-01-01T10:01:00Z', level: 'error', message: 'Error message', logger: 'test' },
    { id: 'log-3', timestamp: '2025-01-01T10:02:00Z', level: 'warning', message: 'Warning message', logger: 'test' },
  ];

  it('should_render_all_logs', () => {
    render(<LogPanel logs={mockLogs} />);
    expect(screen.getByText('Info message')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByText('Warning message')).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_logs', () => {
    render(<LogPanel logs={[]} />);
    expect(screen.getByText(/no logs/i)).toBeInTheDocument();
  });

  it('should_show_log_level_badge', () => {
    render(<LogPanel logs={mockLogs} />);
    expect(screen.getByText('INFO')).toBeInTheDocument();
    expect(screen.getByText('ERROR')).toBeInTheDocument();
  });

  it('should_apply_level_specific_styling', () => {
    render(<LogPanel logs={mockLogs} />);
    const errorBadge = screen.getByText('ERROR');
    expect(errorBadge).toHaveClass('badge-error');
  });
});
