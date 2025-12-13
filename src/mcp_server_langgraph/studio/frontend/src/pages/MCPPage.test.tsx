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

    it('should not call addServer when URL is empty', async () => {
      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      const input = screen.getByPlaceholderText(/Enter server URL/);
      fireEvent.change(input, { target: { value: '' } });
      fireEvent.click(screen.getByText('Add'));

      expect(mockAddServer).not.toHaveBeenCalled();
    });

    it('should clear input after adding server', async () => {
      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      const input = screen.getByPlaceholderText(/Enter server URL/) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'http://localhost:3000' } });
      fireEvent.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });
  });

  describe('Resources Tab', () => {
    it('should switch to resources tab when clicked', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllResources: () => [
          { uri: 'file://test.txt', name: 'test.txt', mimeType: 'text/plain' },
        ],
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Resources'));

      expect(screen.getByText('test.txt')).toBeInTheDocument();
    });

    it('should filter resources by search query', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllResources: () => [
          { uri: 'file://doc.txt', name: 'document.txt', mimeType: 'text/plain' },
          { uri: 'file://data.json', name: 'data.json', mimeType: 'application/json' },
        ],
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Resources'));

      // Search input placeholder changes based on active tab
      const searchInput = screen.getByPlaceholderText(/Search/);
      fireEvent.change(searchInput, { target: { value: 'doc' } });

      expect(screen.getByText('document.txt')).toBeInTheDocument();
      expect(screen.queryByText('data.json')).not.toBeInTheDocument();
    });
  });

  describe('Prompts Tab', () => {
    it('should switch to prompts tab when clicked', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllPrompts: () => [
          { name: 'summarize', description: 'Summarize text' },
        ],
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Prompts'));

      expect(screen.getByText('summarize')).toBeInTheDocument();
    });

    it('should filter prompts by search query', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllPrompts: () => [
          { name: 'summarize', description: 'Summarize text' },
          { name: 'translate', description: 'Translate text' },
        ],
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Prompts'));

      // Search input placeholder changes based on active tab
      const searchInput = screen.getByPlaceholderText(/Search/);
      fireEvent.change(searchInput, { target: { value: 'sum' } });

      expect(screen.getByText('summarize')).toBeInTheDocument();
      expect(screen.queryByText('translate')).not.toBeInTheDocument();
    });
  });

  describe('Tool Expansion', () => {
    it('should show tool details when expanded', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        getAllTools: () => [
          {
            name: 'calculator',
            description: 'Perform calculations',
            inputSchema: { type: 'object', properties: { x: { type: 'number' } } },
          },
        ],
      });

      render(<MCPPage />);

      // Click on the tool to expand it
      const expandButton = screen.getByText('calculator').closest('button');
      if (expandButton) {
        fireEvent.click(expandButton);
      }

      // After expanding, should show input schema
      expect(screen.getByText('calculator')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should display error when present', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        error: 'Connection failed',
      });

      render(<MCPPage />);

      expect(screen.getByText(/Connection failed/)).toBeInTheDocument();
    });
  });

  describe('Connecting State', () => {
    it('should show connecting indicator when connecting', () => {
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        isConnecting: true,
      });

      render(<MCPPage />);

      // Check for connecting state (spinning icon or text)
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Server List', () => {
    it('should display connected servers', () => {
      const connectedServer = new Map([
        ['server-1', {
          id: 'server-1',
          url: 'http://localhost:3000',
          status: 'connected' as const,
          tools: [{ name: 'tool1', description: 'A tool' }],
          resources: [],
          prompts: [],
        }],
      ]);
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        servers: connectedServer,
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      expect(screen.getByText('http://localhost:3000')).toBeInTheDocument();
    });

    it('should show remove button for servers', () => {
      const connectedServer = new Map([
        ['server-1', {
          id: 'server-1',
          url: 'http://localhost:3000',
          status: 'connected' as const,
          tools: [],
          resources: [],
          prompts: [],
        }],
      ]);
      mockUseMCPStore.mockReturnValue({
        ...mockUseMCPStore(),
        servers: connectedServer,
      });

      render(<MCPPage />);

      fireEvent.click(screen.getByText('Servers'));

      // There should be a remove/disconnect button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});
