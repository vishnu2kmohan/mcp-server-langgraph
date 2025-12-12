/**
 * ServerManager Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ServerManager } from './ServerManager';
import type { MCPServerConnection } from '../../api/mcp-types';

describe('ServerManager', () => {
  const mockServers: MCPServerConnection[] = [
    {
      id: 'server-1',
      url: 'http://localhost:8001',
      status: 'connected',
      capabilities: { tools: true, resources: true, prompts: false },
    },
    {
      id: 'server-2',
      url: 'http://localhost:8002',
      status: 'disconnected',
      capabilities: { tools: true, resources: false, prompts: false },
    },
    {
      id: 'server-3',
      url: 'http://localhost:8003',
      status: 'error',
      error: 'Connection refused',
      capabilities: {},
    },
  ];

  it('should_render_server_list', () => {
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    expect(screen.getByText('server-1')).toBeInTheDocument();
    expect(screen.getByText('server-2')).toBeInTheDocument();
    expect(screen.getByText('server-3')).toBeInTheDocument();
  });

  it('should_show_connected_status', () => {
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    // Use getAllByText since "Connected" appears for connected servers
    const statusElements = screen.getAllByText(/^connected$/i);
    expect(statusElements.length).toBeGreaterThan(0);
  });

  it('should_show_disconnected_status', () => {
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    expect(screen.getByText(/^disconnected$/i)).toBeInTheDocument();
  });

  it('should_show_error_status_with_message', () => {
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText(/connection refused/i)).toBeInTheDocument();
  });

  it('should_show_capability_badges', () => {
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    expect(screen.getAllByText(/tools/i)).toHaveLength(2);
    expect(screen.getByText(/resources/i)).toBeInTheDocument();
  });

  it('should_call_onAddServer_with_url', () => {
    const onAddServer = vi.fn();
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={onAddServer}
        onRemoveServer={() => {}}
      />
    );
    const input = screen.getByPlaceholderText(/server url/i);
    fireEvent.change(input, { target: { value: 'http://localhost:9000' } });
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
    expect(onAddServer).toHaveBeenCalledWith('http://localhost:9000');
  });

  it('should_call_onRemoveServer_when_removed', () => {
    const onRemoveServer = vi.fn();
    render(
      <ServerManager
        servers={mockServers}
        onAddServer={() => {}}
        onRemoveServer={onRemoveServer}
      />
    );
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    fireEvent.click(removeButtons[0]);
    expect(onRemoveServer).toHaveBeenCalledWith('server-1');
  });

  it('should_show_empty_state_when_no_servers', () => {
    render(
      <ServerManager
        servers={[]}
        onAddServer={() => {}}
        onRemoveServer={() => {}}
      />
    );
    expect(screen.getByText(/no servers/i)).toBeInTheDocument();
  });
});
