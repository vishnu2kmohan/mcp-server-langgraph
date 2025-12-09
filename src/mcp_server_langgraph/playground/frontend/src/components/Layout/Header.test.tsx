/**
 * Header Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from './Header';

// Mock useDarkMode hook
const mockToggle = vi.fn();
vi.mock('../../hooks/useDarkMode', () => ({
  useDarkMode: vi.fn(() => ({
    isDark: false,
    toggle: mockToggle,
  })),
}));

// Mock useMCPHost
vi.mock('../../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    servers: new Map([['primary', { status: 'connected' }]]),
    pendingElicitations: [],
  })),
}));

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_render_title', () => {
    render(<Header />);
    expect(screen.getByText('Interactive Playground')).toBeInTheDocument();
  });

  it('should_render_dark_mode_toggle', () => {
    render(<Header />);
    const button = screen.getByRole('button', { name: /toggle dark mode/i });
    expect(button).toBeInTheDocument();
  });

  it('should_toggle_dark_mode_on_click', () => {
    render(<Header />);
    const button = screen.getByRole('button', { name: /toggle dark mode/i });
    fireEvent.click(button);
    expect(mockToggle).toHaveBeenCalled();
  });

  it('should_show_connection_status', () => {
    render(<Header />);
    expect(screen.getByText(/connected/i)).toBeInTheDocument();
  });

  it('should_be_accessible_with_landmark', () => {
    render(<Header />);
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });
});
