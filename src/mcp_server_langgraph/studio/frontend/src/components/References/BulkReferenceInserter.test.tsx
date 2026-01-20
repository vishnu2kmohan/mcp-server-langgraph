/**
 * Tests for BulkReferenceInserter component
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA accessibility verified.
 *
 * Allows users to search and select multiple references
 * to insert into chat input.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkReferenceInserter } from './BulkReferenceInserter';
import type { ReferenceItem } from './BulkReferenceInserter';

// Test fixtures
const mockTools: ReferenceItem[] = [
  { type: 'tool', id: 'filesystem:read_file', name: 'read_file', qualifier: 'filesystem', description: 'Read a file' },
  { type: 'tool', id: 'filesystem:write_file', name: 'write_file', qualifier: 'filesystem', description: 'Write a file' },
  { type: 'tool', id: 'database:query', name: 'query', qualifier: 'database', description: 'Run SQL query' },
];

const mockSkills: ReferenceItem[] = [
  { type: 'skill', id: 'code-review', name: 'Code Review', description: 'Review code changes' },
  { type: 'skill', id: 'test-generator', name: 'Test Generator', description: 'Generate tests' },
];

const mockArtifacts: ReferenceItem[] = [
  { type: 'artifact', id: 'chart-123', name: 'Sales Chart', description: 'Q4 sales visualization' },
  { type: 'artifact', id: 'doc-456', name: 'Report', description: 'Annual report' },
];

const allItems = [...mockTools, ...mockSkills, ...mockArtifacts];

const defaultProps = {
  isOpen: true,
  items: allItems,
  onInsert: vi.fn(),
  onClose: vi.fn(),
};

describe('BulkReferenceInserter', () => {
  describe('rendering', () => {
    it('should render nothing when closed', () => {
      const { container } = render(
        <BulkReferenceInserter {...defaultProps} isOpen={false} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render dialog when open', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should display title', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByText(/Insert References/i)).toBeInTheDocument();
    });

    it('should display search input', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('searchbox')).toBeInTheDocument();
    });

    it('should display type filter tabs', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('tablist')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /All/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Tools/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Skills/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Artifacts/i })).toBeInTheDocument();
    });

    it('should display all items by default', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByText('read_file')).toBeInTheDocument();
      expect(screen.getByText('Code Review')).toBeInTheDocument();
      expect(screen.getByText('Sales Chart')).toBeInTheDocument();
    });

    it('should show item count', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByText(/7 items/i)).toBeInTheDocument();
    });
  });

  describe('filtering', () => {
    it('should filter by search text', async () => {
      const user = userEvent.setup();
      render(<BulkReferenceInserter {...defaultProps} />);

      const search = screen.getByRole('searchbox');
      await user.type(search, 'file');

      expect(screen.getByText('read_file')).toBeInTheDocument();
      expect(screen.getByText('write_file')).toBeInTheDocument();
      expect(screen.queryByText('query')).not.toBeInTheDocument();
    });

    it('should filter by type tab', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      fireEvent.click(screen.getByRole('tab', { name: /Tools/i }));

      expect(screen.getByText('read_file')).toBeInTheDocument();
      expect(screen.queryByText('Code Review')).not.toBeInTheDocument();
    });

    it('should combine search and type filters', async () => {
      const user = userEvent.setup();
      render(<BulkReferenceInserter {...defaultProps} />);

      fireEvent.click(screen.getByRole('tab', { name: /Tools/i }));
      const search = screen.getByRole('searchbox');
      await user.type(search, 'read');

      expect(screen.getByText('read_file')).toBeInTheDocument();
      expect(screen.queryByText('write_file')).not.toBeInTheDocument();
    });

    it('should show empty state when no matches', async () => {
      const user = userEvent.setup();
      render(<BulkReferenceInserter {...defaultProps} />);

      const search = screen.getByRole('searchbox');
      await user.type(search, 'nonexistent');

      expect(screen.getByText(/No matching references/i)).toBeInTheDocument();
    });

    it('should update count when filtering', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      fireEvent.click(screen.getByRole('tab', { name: /Skills/i }));

      expect(screen.getByText(/2 items/i)).toBeInTheDocument();
    });
  });

  describe('selection', () => {
    it('should allow selecting items via checkbox', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(checkbox);

      expect(checkbox).toBeChecked();
    });

    it('should show selected count', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(checkboxes[1]);

      // Multiple status elements may exist, just verify at least one exists
      expect(screen.getAllByText(/2 selected/i).length).toBeGreaterThan(0);
    });

    it('should allow selecting all visible items', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));

      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((cb) => {
        expect(cb).toBeChecked();
      });
    });

    it('should allow deselecting all items', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      // Select all first
      fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
      // Then clear
      fireEvent.click(screen.getByRole('button', { name: /Clear selection/i }));

      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((cb) => {
        expect(cb).not.toBeChecked();
      });
    });

    it('should preserve selection when filtering', async () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      // Select first item
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      // Filter to skills
      fireEvent.click(screen.getByRole('tab', { name: /Skills/i }));

      // Selection count should still show (multiple status elements may exist)
      expect(screen.getAllByText(/1 selected/i).length).toBeGreaterThan(0);

      // Go back to all
      fireEvent.click(screen.getByRole('tab', { name: /All/i }));

      // First item should still be selected
      expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
    });
  });

  describe('insertion', () => {
    it('should call onInsert with selected references', () => {
      const onInsert = vi.fn();
      render(<BulkReferenceInserter {...defaultProps} onInsert={onInsert} />);

      // Select items
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]); // filesystem:read_file
      fireEvent.click(checkboxes[3]); // code-review (4th in combined list)

      // Insert
      fireEvent.click(screen.getByRole('button', { name: /Insert/i }));

      expect(onInsert).toHaveBeenCalledWith([
        expect.objectContaining({ id: 'filesystem:read_file' }),
        expect.objectContaining({ id: 'code-review' }),
      ]);
    });

    it('should close dialog after insertion', () => {
      const onClose = vi.fn();
      render(<BulkReferenceInserter {...defaultProps} onClose={onClose} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);
      fireEvent.click(screen.getByRole('button', { name: /Insert/i }));

      expect(onClose).toHaveBeenCalled();
    });

    it('should disable insert button when nothing selected', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('button', { name: /Insert/i })).toBeDisabled();
    });

    it('should enable insert button when items are selected', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      expect(screen.getByRole('button', { name: /Insert/i })).not.toBeDisabled();
    });
  });

  describe('keyboard navigation', () => {
    it('should close on Escape', () => {
      const onClose = vi.fn();
      render(<BulkReferenceInserter {...defaultProps} onClose={onClose} />);

      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

      expect(onClose).toHaveBeenCalled();
    });

    it('should focus search on open', async () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      // Focus happens via setTimeout, wait for it
      await waitFor(() => {
        expect(screen.getByRole('searchbox')).toHaveFocus();
      });
    });

    it('should navigate items with arrow keys', async () => {
      const user = userEvent.setup();
      render(<BulkReferenceInserter {...defaultProps} />);

      // Tab to list
      await user.tab();
      await user.tab();

      // Arrow down should highlight next item
      await user.keyboard('{ArrowDown}');

      // First list item should be focused
      const listbox = screen.getByRole('listbox');
      expect(listbox.querySelector('[aria-selected="true"]')).toBeInTheDocument();
    });

    it('should toggle item by clicking row', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      // Click the item row to toggle selection
      const options = screen.getAllByRole('option');
      fireEvent.click(options[0]);

      // Checkbox should be checked
      expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
    });
  });

  describe('accessibility', () => {
    it('should have dialog role', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have aria-modal', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('should have aria-labelledby', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
    });

    it('should have tablist for type filters', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });

    it('should have listbox for items', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('should announce selection changes', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(checkbox);

      // Live region should exist (there may be multiple status elements)
      const statusElements = screen.getAllByRole('status');
      const hasSelectedText = statusElements.some((el) =>
        el.textContent?.includes('1 selected')
      );
      expect(hasSelectedText).toBe(true);
    });
  });

  describe('preview', () => {
    it('should show preview of markdown to be inserted', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]); // filesystem:read_file

      expect(screen.getByText(/\[\[tool:filesystem:read_file\]\]/)).toBeInTheDocument();
    });

    it('should update preview as selection changes', () => {
      render(<BulkReferenceInserter {...defaultProps} />);

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[0]);

      expect(screen.getByText(/\[\[tool:filesystem:read_file\]\]/)).toBeInTheDocument();

      fireEvent.click(checkboxes[3]); // code-review skill

      expect(screen.getByText(/\[\[skill:code-review\]\]/)).toBeInTheDocument();
    });
  });
});
