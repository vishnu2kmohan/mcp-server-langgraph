/**
 * HelpPanel Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { HelpPanel, type HelpSection, type HelpArticle } from './HelpPanel';

const mockArticles: HelpArticle[] = [
  {
    id: 'article1',
    title: 'Getting Started',
    content: 'This is how you get started with the application.',
    category: 'basics',
  },
  {
    id: 'article2',
    title: 'Creating Agents',
    content: 'Learn how to create AI agents.',
    category: 'agents',
  },
  {
    id: 'article3',
    title: 'Using Tools',
    content: 'Configure and use tools in your agents.',
    category: 'agents',
  },
];

const mockSections: HelpSection[] = [
  { id: 'basics', title: 'Basics', icon: '📚' },
  { id: 'agents', title: 'Agents', icon: '🤖' },
];

describe('HelpPanel Component', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders when isOpen is true', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByText('Help Center')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(
        <HelpPanel
          isOpen={false}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.queryByText('Help Center')).not.toBeInTheDocument();
    });

    it('renders section tabs', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByRole('tab', { name: /basics/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /agents/i })).toBeInTheDocument();
    });

    it('renders articles for current section', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByText('Getting Started')).toBeInTheDocument();
    });

    it('renders search input', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });

    it('renders close button', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Navigation Tests
  // ==============================================================================

  describe('Navigation', () => {
    it('switches sections when tab clicked', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.click(screen.getByRole('tab', { name: /agents/i }));

      expect(screen.getByText('Creating Agents')).toBeInTheDocument();
      expect(screen.getByText('Using Tools')).toBeInTheDocument();
    });

    it('shows article content when article clicked', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.click(screen.getByText('Getting Started'));

      expect(screen.getByText('This is how you get started with the application.')).toBeInTheDocument();
    });

    it('shows back button in article view', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.click(screen.getByText('Getting Started'));

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    it('returns to list when back clicked', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.click(screen.getByText('Getting Started'));
      fireEvent.click(screen.getByRole('button', { name: /back/i }));

      // Should see the section tabs again (in list view)
      expect(screen.getByRole('tab', { name: /basics/i })).toBeInTheDocument();
    });

    it('calls onClose when close clicked', () => {
      const onClose = vi.fn();
      render(
        <HelpPanel
          isOpen={true}
          onClose={onClose}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /close/i }));

      expect(onClose).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Search Tests
  // ==============================================================================

  describe('Search', () => {
    it('filters articles by search query', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: 'agents' } });

      expect(screen.getByText('Creating Agents')).toBeInTheDocument();
      expect(screen.queryByText('Getting Started')).not.toBeInTheDocument();
    });

    it('shows no results message when no matches', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: 'xyz123' } });

      expect(screen.getByText(/no results/i)).toBeInTheDocument();
    });

    it('searches across all sections', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: 'tools' } });

      expect(screen.getByText('Using Tools')).toBeInTheDocument();
    });

    it('clears search when X clicked', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      fireEvent.change(searchInput, { target: { value: 'agents' } });

      const clearButton = screen.getByRole('button', { name: /clear search/i });
      fireEvent.click(clearButton);

      expect(screen.getByText('Getting Started')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has complementary role', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByRole('complementary')).toBeInTheDocument();
    });

    it('has aria-label', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByRole('complementary')).toHaveAttribute('aria-label', 'Help panel');
    });

    it('tabs have proper tablist role', () => {
      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });

    it('escape key closes panel', () => {
      const onClose = vi.fn();
      render(
        <HelpPanel
          isOpen={true}
          onClose={onClose}
          articles={mockArticles}
          sections={mockSections}
        />
      );

      fireEvent.keyDown(screen.getByRole('complementary'), { key: 'Escape' });

      expect(onClose).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Keyboard Shortcuts Display Tests
  // ==============================================================================

  describe('Keyboard Shortcuts', () => {
    it('shows keyboard shortcuts section when provided', () => {
      const shortcuts = [
        { keys: ['Ctrl', 'S'], description: 'Save' },
        { keys: ['Ctrl', 'Z'], description: 'Undo' },
      ];

      render(
        <HelpPanel
          isOpen={true}
          onClose={vi.fn()}
          articles={mockArticles}
          sections={mockSections}
          keyboardShortcuts={shortcuts}
        />
      );

      // Click on keyboard shortcuts tab if it exists
      const shortcutsTab = screen.getByRole('tab', { name: /keyboard/i });
      fireEvent.click(shortcutsTab);

      // Multiple Ctrl keys exist (Ctrl+S, Ctrl+Z)
      expect(screen.getAllByText('Ctrl').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Save')).toBeInTheDocument();
    });
  });
});
