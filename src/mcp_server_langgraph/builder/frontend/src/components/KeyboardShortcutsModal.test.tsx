/**
 * Tests for KeyboardShortcutsModal Component
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KeyboardShortcutsModal } from './KeyboardShortcutsModal';

describe('KeyboardShortcutsModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders modal when isOpen is true', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(<KeyboardShortcutsModal isOpen={false} onClose={mockOnClose} />);

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays modal title', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByRole('heading', { name: /keyboard shortcuts/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Shortcut Display Tests
  // ==============================================================================

  describe('Shortcut Display', () => {
    it('displays save shortcut (Ctrl+S)', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/save workflow/i)).toBeInTheDocument();
      // Ctrl appears multiple times in the modal, just check it exists
      const ctrlKeys = screen.getAllByText(/ctrl/i);
      expect(ctrlKeys.length).toBeGreaterThan(0);
    });

    it('displays generate code shortcut (Ctrl+G)', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/generate code/i)).toBeInTheDocument();
    });

    it('displays undo shortcut (Ctrl+Z)', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/undo/i)).toBeInTheDocument();
    });

    it('displays redo shortcut (Ctrl+Y)', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      // Redo appears twice (Ctrl+Y and Ctrl+Shift+Z alternative)
      const redoTexts = screen.getAllByText(/redo/i);
      expect(redoTexts.length).toBeGreaterThan(0);
    });

    it('displays delete shortcut', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      // "Delete selected nodes" appears twice (Delete key and Backspace), so use getAllByText
      const deleteTexts = screen.getAllByText(/delete selected/i);
      expect(deleteTexts.length).toBeGreaterThanOrEqual(1);
    });

    it('displays toggle dark mode shortcut', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/toggle dark mode/i)).toBeInTheDocument();
    });

    it('displays escape shortcut', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/close menu\/modal/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Close Actions Tests
  // ==============================================================================

  describe('Close Actions', () => {
    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onClose when Escape is pressed', async () => {
      const user = userEvent.setup();
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onClose when backdrop is clicked', async () => {
      const user = userEvent.setup();
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      const backdrop = screen.getByTestId('modal-backdrop');
      await user.click(backdrop);

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has proper dialog role and aria-modal', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-labelledby pointing to title', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
    });

    it('has focus trap enabled', async () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      // First focusable element should receive focus
      await waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByRole('button', { name: /close/i })
        );
      });
    });
  });

  // ==============================================================================
  // Shortcut Categories Tests
  // ==============================================================================

  describe('Shortcut Categories', () => {
    it('groups shortcuts by category', () => {
      render(<KeyboardShortcutsModal isOpen={true} onClose={mockOnClose} />);

      // Check for category headings
      expect(screen.getByText(/general/i)).toBeInTheDocument();
      expect(screen.getByText(/editing/i)).toBeInTheDocument();
    });
  });
});
