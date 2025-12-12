/**
 * Tests for SettingsModal Component
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsModal } from './SettingsModal';

describe('SettingsModal Component', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
  };

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders when isOpen is true', () => {
      render(<SettingsModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(<SettingsModal {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('renders Settings header', () => {
      render(<SettingsModal {...defaultProps} />);
      // There are two headings: "Settings" and "Privacy Settings"
      const headings = screen.getAllByRole('heading', { name: /settings/i });
      expect(headings.length).toBeGreaterThanOrEqual(1);
      expect(headings[0]).toHaveTextContent('Settings');
    });

    it('renders Privacy Settings section', () => {
      render(<SettingsModal {...defaultProps} />);
      expect(screen.getByText(/privacy settings/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('calls onClose when close button is clicked', () => {
      const onClose = vi.fn();
      render(<SettingsModal {...defaultProps} onClose={onClose} />);

      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when overlay is clicked', () => {
      const onClose = vi.fn();
      render(<SettingsModal {...defaultProps} onClose={onClose} />);

      const overlay = screen.getByTestId('settings-overlay');
      fireEvent.click(overlay);

      expect(onClose).toHaveBeenCalled();
    });

    it('does not close when modal content is clicked', () => {
      const onClose = vi.fn();
      render(<SettingsModal {...defaultProps} onClose={onClose} />);

      const dialog = screen.getByRole('dialog');
      fireEvent.click(dialog);

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has proper role for dialog', () => {
      render(<SettingsModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-modal attribute', () => {
      render(<SettingsModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-labelledby for the header', () => {
      render(<SettingsModal {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
    });
  });
});
