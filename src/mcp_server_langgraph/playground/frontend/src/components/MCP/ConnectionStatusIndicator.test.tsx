/**
 * ConnectionStatusIndicator Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatusIndicator } from './ConnectionStatusIndicator';

// Mock the MCPHost context
vi.mock('../../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(),
}));

import { useMCPHost } from '../../contexts/MCPHostContext';

const mockUseMCPHost = useMCPHost as ReturnType<typeof vi.fn>;

describe('ConnectionStatusIndicator', () => {
  it('should_show_disconnected_when_no_servers', () => {
    mockUseMCPHost.mockReturnValue({
      servers: new Map(),
      primaryServerId: null,
    });

    render(<ConnectionStatusIndicator />);

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('should_show_connecting_when_server_is_connecting', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connecting' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('should_show_connected_when_server_is_connected', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connected' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('should_show_error_when_server_has_error', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'error', error: 'Connection failed' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('should_show_connected_count_with_multiple_servers', () => {
    const servers = new Map([
      ['server1', { id: 'server1', url: '/mcp1', status: 'connected' }],
      ['server2', { id: 'server2', url: '/mcp2', status: 'connected' }],
      ['server3', { id: 'server3', url: '/mcp3', status: 'error' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'server1',
    });

    render(<ConnectionStatusIndicator />);

    expect(screen.getByText('2 of 3')).toBeInTheDocument();
  });

  it('should_show_pulsing_indicator_when_connecting', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connecting' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('animate-pulse');
  });

  it('should_show_green_indicator_when_connected', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connected' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('bg-success-500');
  });

  it('should_show_red_indicator_when_error', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'error' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('bg-error-500');
  });

  it('should_show_gray_indicator_when_disconnected', () => {
    mockUseMCPHost.mockReturnValue({
      servers: new Map(),
      primaryServerId: null,
    });

    render(<ConnectionStatusIndicator />);

    const indicator = screen.getByTestId('status-indicator');
    expect(indicator).toHaveClass('bg-gray-400');
  });

  it('should_be_compact_when_variant_is_compact', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connected' }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator variant="compact" />);

    // Compact mode should not show the status text
    expect(screen.queryByText('Connected')).not.toBeInTheDocument();
    expect(screen.getByTestId('status-indicator')).toBeInTheDocument();
  });

  it('should_show_tooltip_with_server_info', () => {
    const servers = new Map([
      ['default', { id: 'default', url: '/mcp', status: 'connected', serverInfo: { name: 'Test Server' } }],
    ]);

    mockUseMCPHost.mockReturnValue({
      servers,
      primaryServerId: 'default',
    });

    render(<ConnectionStatusIndicator />);

    const container = screen.getByLabelText('MCP Connection Status');
    expect(container).toBeInTheDocument();
  });
});
