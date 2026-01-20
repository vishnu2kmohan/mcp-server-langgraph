/**
 * Tests for ToolDisambiguationDialog component
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA accessibility verified.
 *
 * This component handles tool ambiguity when multiple connections
 * share the same server_name.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolDisambiguationDialog } from './ToolDisambiguationDialog';
import type { AmbiguousConnection } from './ToolDisambiguationDialog';

// Test fixtures
const mockConnections: AmbiguousConnection[] = [
  {
    connectionId: 'conn-1',
    serverName: 'filesystem',
    displayName: 'Local Filesystem',
    description: 'Access to local files',
    status: 'connected',
    owner: 'user@example.com',
  },
  {
    connectionId: 'conn-2',
    serverName: 'filesystem',
    displayName: 'Remote Filesystem',
    description: 'Access to remote storage',
    status: 'connected',
    owner: 'team@example.com',
  },
  {
    connectionId: 'conn-3',
    serverName: 'filesystem',
    displayName: 'Shared Drive',
    description: 'Company shared drive',
    status: 'disconnected',
    owner: 'admin@example.com',
  },
];

const defaultProps = {
  isOpen: true,
  toolReference: '[[tool:filesystem:read_file]]',
  serverName: 'filesystem',
  toolName: 'read_file',
  connections: mockConnections,
  onSelect: vi.fn(),
  onCancel: vi.fn(),
};

describe('ToolDisambiguationDialog', () => {
  describe('rendering', () => {
    it('should render nothing when closed', () => {
      const { container } = render(
        <ToolDisambiguationDialog {...defaultProps} isOpen={false} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render dialog when open', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should display the tool reference in the title', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByText(/Multiple connections found/i)).toBeInTheDocument();
      expect(screen.getByText(/filesystem:read_file/)).toBeInTheDocument();
    });

    it('should display explanation text', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(
        screen.getByText(/Multiple connections provide this tool/i)
      ).toBeInTheDocument();
    });

    it('should display all connection options', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByText('Local Filesystem')).toBeInTheDocument();
      expect(screen.getByText('Remote Filesystem')).toBeInTheDocument();
      expect(screen.getByText('Shared Drive')).toBeInTheDocument();
    });

    it('should display connection descriptions', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByText('Access to local files')).toBeInTheDocument();
      expect(screen.getByText('Access to remote storage')).toBeInTheDocument();
    });

    it('should display connection status', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      // Should show connected status for first two
      const connectedBadges = screen.getAllByText('Connected');
      expect(connectedBadges).toHaveLength(2);

      // Should show disconnected status for third
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('should display owner information', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByText(/user@example.com/)).toBeInTheDocument();
      expect(screen.getByText(/team@example.com/)).toBeInTheDocument();
    });

    it('should visually indicate disconnected connections', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const disconnectedOption = screen.getByText('Shared Drive').closest('[role="radio"]');
      expect(disconnectedOption).toHaveClass('opacity-60');
    });
  });

  describe('selection', () => {
    it('should have first connected option selected by default', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const options = screen.getAllByRole('radio');
      expect(options[0]).toBeChecked();
    });

    it('should allow selecting a different connection', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const remoteOption = screen.getByText('Remote Filesystem').closest('[role="radio"]');
      fireEvent.click(remoteOption!);

      expect(remoteOption).toBeChecked();
    });

    it('should call onSelect with selected connection when confirmed', () => {
      const onSelect = vi.fn();
      render(<ToolDisambiguationDialog {...defaultProps} onSelect={onSelect} />);

      // Select second option
      const remoteOption = screen.getByText('Remote Filesystem').closest('[role="radio"]');
      fireEvent.click(remoteOption!);

      // Click confirm button
      fireEvent.click(screen.getByRole('button', { name: /Use Selected/i }));

      expect(onSelect).toHaveBeenCalledWith(mockConnections[1], false);
    });

    it('should call onCancel when cancel button clicked', () => {
      const onCancel = vi.fn();
      render(<ToolDisambiguationDialog {...defaultProps} onCancel={onCancel} />);

      fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));

      expect(onCancel).toHaveBeenCalled();
    });
  });

  describe('keyboard navigation', () => {
    it('should support arrow key navigation between options', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const radioGroup = screen.getByRole('radiogroup');

      // Arrow down to second option
      fireEvent.keyDown(radioGroup, { key: 'ArrowDown' });
      expect(screen.getAllByRole('radio')[1]).toBeChecked();

      // Arrow up back to first
      fireEvent.keyDown(radioGroup, { key: 'ArrowUp' });
      expect(screen.getAllByRole('radio')[0]).toBeChecked();
    });

    it('should close dialog on Escape', () => {
      const onCancel = vi.fn();
      render(<ToolDisambiguationDialog {...defaultProps} onCancel={onCancel} />);

      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

      expect(onCancel).toHaveBeenCalled();
    });

    it('should confirm selection on Enter when option focused', () => {
      const onSelect = vi.fn();
      render(<ToolDisambiguationDialog {...defaultProps} onSelect={onSelect} />);

      // Press Enter on the confirm button
      fireEvent.click(screen.getByRole('button', { name: /Use Selected/i }));

      expect(onSelect).toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('should have proper dialog role', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have aria-labelledby for dialog title', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');

      const labelId = dialog.getAttribute('aria-labelledby');
      expect(document.getElementById(labelId!)).toBeInTheDocument();
    });

    it('should have aria-describedby for dialog description', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-describedby');
    });

    it('should use radiogroup for connection options', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    });

    it('should have aria-label on radiogroup', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(screen.getByRole('radiogroup')).toHaveAttribute(
        'aria-label',
        'Select connection'
      );
    });

    it('should have radio role on each option', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const radios = screen.getAllByRole('radio');
      expect(radios).toHaveLength(3);
    });

    it('should have proper aria-checked state', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const radios = screen.getAllByRole('radio');
      expect(radios[0]).toHaveAttribute('aria-checked', 'true');
      expect(radios[1]).toHaveAttribute('aria-checked', 'false');
    });

    it('should trap focus within dialog', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });
  });

  describe('edge cases', () => {
    it('should handle single connection gracefully', () => {
      const singleConnection = [mockConnections[0]];
      render(
        <ToolDisambiguationDialog {...defaultProps} connections={singleConnection} />
      );

      expect(screen.getByText('Local Filesystem')).toBeInTheDocument();
    });

    it('should handle all disconnected connections', () => {
      const allDisconnected = mockConnections.map((c) => ({
        ...c,
        status: 'disconnected' as const,
      }));
      render(
        <ToolDisambiguationDialog {...defaultProps} connections={allDisconnected} />
      );

      // Should still allow selection
      const radios = screen.getAllByRole('radio');
      expect(radios[0]).toBeChecked();
    });

    it('should prefer connected connection for default selection', () => {
      // Put disconnected first
      const reordered = [mockConnections[2], mockConnections[0], mockConnections[1]];
      render(
        <ToolDisambiguationDialog {...defaultProps} connections={reordered} />
      );

      // Second option (first connected) should be selected
      const radios = screen.getAllByRole('radio');
      expect(radios[1]).toBeChecked();
    });

    it('should handle empty connections array', () => {
      render(<ToolDisambiguationDialog {...defaultProps} connections={[]} />);

      expect(
        screen.getByText(/No connections available/i)
      ).toBeInTheDocument();
    });

    it('should show warning for disconnected selection', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      // Select disconnected option
      const disconnectedOption = screen
        .getByText('Shared Drive')
        .closest('[role="radio"]');
      fireEvent.click(disconnectedOption!);

      expect(
        screen.getByText(/This connection is currently disconnected/i)
      ).toBeInTheDocument();
    });
  });

  describe('remember selection', () => {
    it('should show "Remember my choice" checkbox', () => {
      render(<ToolDisambiguationDialog {...defaultProps} />);

      expect(
        screen.getByRole('checkbox', { name: /Remember my choice/i })
      ).toBeInTheDocument();
    });

    it('should pass remember preference to onSelect', () => {
      const onSelect = vi.fn();
      render(<ToolDisambiguationDialog {...defaultProps} onSelect={onSelect} />);

      // Check "Remember" checkbox
      const rememberCheckbox = screen.getByRole('checkbox', {
        name: /Remember my choice/i,
      });
      fireEvent.click(rememberCheckbox);

      // Confirm selection
      fireEvent.click(screen.getByRole('button', { name: /Use Selected/i }));

      expect(onSelect).toHaveBeenCalledWith(
        expect.anything(),
        true // remember flag
      );
    });
  });
});
