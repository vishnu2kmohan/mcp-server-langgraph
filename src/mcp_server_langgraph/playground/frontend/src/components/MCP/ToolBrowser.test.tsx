/**
 * ToolBrowser Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolBrowser } from './ToolBrowser';

// Mock useMCPTools hook
vi.mock('../../hooks/useMCPTools', () => ({
  useMCPTools: () => ({
    tools: [
      {
        name: 'search_tool',
        description: 'Search for documents',
        inputSchema: { type: 'object', properties: { query: { type: 'string' } } },
      },
      {
        name: 'execute_code',
        description: 'Execute Python code',
        inputSchema: { type: 'object', properties: { code: { type: 'string' } } },
      },
    ],
    callTool: vi.fn(),
    isLoading: false,
  }),
}));

describe('ToolBrowser', () => {
  it('should_render_tool_count', () => {
    render(<ToolBrowser />);
    expect(screen.getByText(/Tools \(2\)/)).toBeInTheDocument();
  });

  it('should_render_all_tools', () => {
    render(<ToolBrowser />);
    expect(screen.getByText('search_tool')).toBeInTheDocument();
    expect(screen.getByText('execute_code')).toBeInTheDocument();
  });

  it('should_render_search_input', () => {
    render(<ToolBrowser />);
    expect(screen.getByPlaceholderText('Search tools...')).toBeInTheDocument();
  });

  it('should_filter_tools_by_search_query', () => {
    render(<ToolBrowser />);

    const searchInput = screen.getByPlaceholderText('Search tools...');
    fireEvent.change(searchInput, { target: { value: 'search' } });

    expect(screen.getByText('search_tool')).toBeInTheDocument();
    expect(screen.queryByText('execute_code')).not.toBeInTheDocument();
  });

  it('should_show_no_match_message_when_search_has_no_results', () => {
    render(<ToolBrowser />);

    const searchInput = screen.getByPlaceholderText('Search tools...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No matching tools')).toBeInTheDocument();
    expect(screen.getByText(/No tools match "nonexistent"/)).toBeInTheDocument();
  });

  it('should_call_onToolSelect_when_tool_clicked', () => {
    const onToolSelect = vi.fn();
    render(<ToolBrowser onToolSelect={onToolSelect} />);

    fireEvent.click(screen.getByText('search_tool'));
    expect(onToolSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'search_tool' })
    );
  });
});
