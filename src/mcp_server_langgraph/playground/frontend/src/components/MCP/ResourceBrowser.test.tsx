/**
 * ResourceBrowser Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ResourceBrowser } from './ResourceBrowser';

// Mock useMCPResources hook
vi.mock('../../hooks/useMCPResources', () => ({
  useMCPResources: () => ({
    resources: [
      {
        uri: 'file:///docs/readme.md',
        name: 'README',
        description: 'Project documentation',
        mimeType: 'text/markdown',
      },
      {
        uri: 'file:///config/settings.json',
        name: 'Settings',
        description: 'Application settings',
        mimeType: 'application/json',
      },
    ],
    readResource: vi.fn().mockResolvedValue({
      contents: [{ text: 'Sample content' }],
    }),
    isLoading: false,
  }),
}));

describe('ResourceBrowser', () => {
  it('should_render_resource_count', () => {
    render(<ResourceBrowser />);
    expect(screen.getByText(/Resources \(2\)/)).toBeInTheDocument();
  });

  it('should_render_all_resources', () => {
    render(<ResourceBrowser />);
    expect(screen.getByText('README')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should_render_search_input', () => {
    render(<ResourceBrowser />);
    expect(screen.getByPlaceholderText('Search resources...')).toBeInTheDocument();
  });

  it('should_filter_resources_by_search_query', () => {
    render(<ResourceBrowser />);

    const searchInput = screen.getByPlaceholderText('Search resources...');
    fireEvent.change(searchInput, { target: { value: 'readme' } });

    expect(screen.getByText('README')).toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('should_show_no_match_message_when_search_has_no_results', () => {
    render(<ResourceBrowser />);

    const searchInput = screen.getByPlaceholderText('Search resources...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No matching resources')).toBeInTheDocument();
    expect(screen.getByText(/No resources match "nonexistent"/)).toBeInTheDocument();
  });

  it('should_call_onResourceSelect_when_resource_clicked', () => {
    const onResourceSelect = vi.fn();
    render(<ResourceBrowser onResourceSelect={onResourceSelect} />);

    fireEvent.click(screen.getByText('README'));
    expect(onResourceSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'README' })
    );
  });

  it('should_display_resource_uri', () => {
    render(<ResourceBrowser />);
    expect(screen.getByText('file:///docs/readme.md')).toBeInTheDocument();
  });

  it('should_display_resource_mimeType', () => {
    render(<ResourceBrowser />);
    expect(screen.getByText('text/markdown')).toBeInTheDocument();
  });

  it('should_load_resource_content_when_clicked', async () => {
    render(<ResourceBrowser />);

    fireEvent.click(screen.getByText('README'));

    await waitFor(() => {
      expect(screen.getByText('Sample content')).toBeInTheDocument();
    });
  });

  it('should_show_close_button_when_resource_selected', async () => {
    render(<ResourceBrowser />);

    fireEvent.click(screen.getByText('README'));

    await waitFor(() => {
      expect(screen.getByLabelText('Close resource details')).toBeInTheDocument();
    });
  });
});
