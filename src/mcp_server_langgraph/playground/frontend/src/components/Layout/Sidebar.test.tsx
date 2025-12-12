/**
 * Sidebar Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from './Sidebar';

// Mock useMCPHost since Sidebar now uses it for ServerManager
vi.mock('../../contexts/MCPHostContext', () => ({
  useMCPHost: () => ({
    servers: new Map(),
    addServer: vi.fn(),
    removeServer: vi.fn(),
  }),
}));

// Mock ServerManager component
vi.mock('../MCP/ServerManager', () => ({
  ServerManager: () => <div data-testid="server-manager">ServerManager</div>,
}));

describe('Sidebar', () => {
  it('should_render_children', () => {
    render(
      <Sidebar>
        <div data-testid="child">Content</div>
      </Sidebar>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('should_have_aside_role', () => {
    render(<Sidebar>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toBeInTheDocument();
  });

  it('should_have_proper_width', () => {
    render(<Sidebar>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toHaveClass('w-80');
  });

  it('should_be_collapsible', () => {
    const onToggle = vi.fn();
    render(
      <Sidebar collapsed={false} onToggle={onToggle}>
        Content
      </Sidebar>
    );

    const toggleButton = screen.getByRole('button', { name: /collapse/i });
    fireEvent.click(toggleButton);
    expect(onToggle).toHaveBeenCalled();
  });

  it('should_render_collapsed_state', () => {
    render(<Sidebar collapsed>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toHaveClass('w-16');
  });

  it('should_render_title_when_provided', () => {
    render(<Sidebar title="My Sidebar">Content</Sidebar>);
    expect(screen.getByText('My Sidebar')).toBeInTheDocument();
  });

  it('should_render_server_manager_section', () => {
    render(<Sidebar>Content</Sidebar>);
    expect(screen.getByText('MCP Servers')).toBeInTheDocument();
    expect(screen.getByTestId('server-manager')).toBeInTheDocument();
  });
});
