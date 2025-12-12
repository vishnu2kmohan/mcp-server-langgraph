/**
 * SessionExportButtons Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionExportButtons } from './SessionExportButtons';

describe('SessionExportButtons', () => {
  const mockSessions = [
    { id: 'session-1', title: 'Test Session 1', messages: [] },
    { id: 'session-2', title: 'Test Session 2', messages: [] },
  ];

  const mockOnImport = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_render_export_button', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} />);

    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
  });

  it('should_render_import_button', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} />);

    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
  });

  it('should_disable_export_when_no_sessions', () => {
    render(<SessionExportButtons sessions={[]} onImport={mockOnImport} />);

    const exportButton = screen.getByRole('button', { name: /export/i });
    expect(exportButton).toBeDisabled();
  });

  it('should_enable_export_when_sessions_exist', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} />);

    const exportButton = screen.getByRole('button', { name: /export/i });
    expect(exportButton).not.toBeDisabled();
  });

  it('should_show_session_count', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} />);

    expect(screen.getByText('2 sessions')).toBeInTheDocument();
  });

  it('should_be_accessible', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} />);

    const exportButton = screen.getByRole('button', { name: /export/i });
    const importButton = screen.getByRole('button', { name: /import/i });

    expect(exportButton).toBeInTheDocument();
    expect(importButton).toBeInTheDocument();
  });

  it('should_render_compact_variant', () => {
    render(<SessionExportButtons sessions={mockSessions} onImport={mockOnImport} variant="compact" />);

    // Compact variant should still have buttons
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument();
  });
});
