/**
 * MCPPage Tests
 *
 * TDD tests for the MCP explorer page.
 * Tests cover:
 * - Tab navigation
 * - Tools display
 * - Connection status
 * - Search functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MCPPage } from './MCPPage';
import * as mcpStoreModule from '../stores/mcpStore';

// Mock the MCP store
vi.mock('../stores/mcpStore');

const mockUseMCPStore = vi.mocked(mcpStoreModule.useMCPStore);

describe('MCPPage', () => {
  const mockAddServer = vi.fn();
  const mockRemoveServer = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseMCPStore.mockReturnValue({
      servers: new Map(),
      primaryServerId: null,
      isConnecting: false,
      error: null,
      addServer: mockAddServer,
      removeServer: mockRemoveServer,
      getAllTools: () => [],
      getAllResources: () => [],
      getAllPrompts: () => [],
      refreshTools: vi.fn(),
      refreshResources: vi.fn(),
      refreshPrompts: vi.fn(),
      executeTool: vi.fn(),
      setPrimaryServer: vi.fn(),
    });
  });

  describe('Header', () => {
    it('should display page title', () => {
      render(<MCPPage />);

      expect(screen.getByText('MCP Explorer')).toBeInTheDocument();
    });

    it('should show Disconnected when no servers connected', () => {
      render(<MCPPage />);

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('should show Connected when servers are connected', () => {
      const connectedServer = new Map([
        ['server-1', { id: 'server-1', url: 'http://localhost:3000', status: 'connected' as const, tools: [], resources: [], prompts: [] }],
      ]);
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        servers: connectedServer,
      });

      render(<MCPPage />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });
  });

  describe('Tabs', () => {
    it('should have Tools tab', () => {
      render(<MCPPage />);

      expect(screen.getByText('Tools')).toBeInTheDocument();
    });

    it('should have Resources tab', () => {
      render(<MCPPage />);

      expect(screen.getByText('Resources')).toBeInTheDocument();
    });

    it('should have Prompts tab', () => {
      render(<MCPPage />);

      expect(screen.getByText('Prompts')).toBeInTheDocument();
    });

    it('should have Servers tab', () => {
      render(<MCPPage />);

      expect(screen.getByText('Servers')).toBeInTheDocument();
    });
  });

  describe('Tools Tab', () => {
    it('should display tools when available', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllTools: () => [
          { name: 'calculator', description: 'Perform calculations' },
          { name: 'search', description: 'Search the web' },
        ],
      });

      render(<MCPPage />);

      expect(screen.getByText('calculator')).toBeInTheDocument();
      expect(screen.getByText('Perform calculations')).toBeInTheDocument();
    });

    it('should show empty state when no tools', () => {
      render(<MCPPage />);

      expect(screen.getByText('No tools found')).toBeInTheDocument();
    });
  });

  describe('Search', () => {
    it('should have search input', () => {
      render(<MCPPage />);

      expect(screen.getByPlaceholderText(/Search tools/)).toBeInTheDocument();
    });

    it('should filter tools by search query', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllTools: () => [
          { name: 'calculator', description: 'Math operations' },
          { name: 'weather', description: 'Weather data' },
        ],
      });

      render(<MCPPage />);

      const searchInput = screen.getByPlaceholderText(/Search tools/);
      fireEvent.change(searchInput, { target: { value: 'calc' } });

      expect(screen.getByText('calculator')).toBeInTheDocument();
      expect(screen.queryByText('weather')).not.toBeInTheDocument();
    });
  });

  describe('Servers Tab', () => {
    it('should switch to servers tab when clicked', () => {
      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      // Should see add server UI - placeholder is "Enter server URL..."
      expect(screen.getByPlaceholderText(/Enter server URL/)).toBeInTheDocument();
    });

    it('should call addServer when adding a server', async () => {
      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      const input = screen.getByPlaceholderText(/Enter server URL/);
      fireEvent.change(input, { target: { value: 'http://localhost:3000' } });
      fireEvent.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(mockAddServer).toHaveBeenCalledWith(expect.any(String), 'http://localhost:3000');
      });
    });
  });
});
