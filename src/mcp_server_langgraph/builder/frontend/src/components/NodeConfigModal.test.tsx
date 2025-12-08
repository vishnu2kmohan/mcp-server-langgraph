/**
 * Tests for Node Configuration Modal
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NodeConfigModal } from './NodeConfigModal';

describe('NodeConfigModal Component', () => {
  const mockNode = {
    id: 'node1',
    type: 'default',
    data: {
      label: 'Test Node',
      nodeType: 'tool' as const,
      config: {
        toolName: 'search_web',
        timeout: 30,
      },
    },
    position: { x: 100, y: 100 },
  };

  const mockOnSave = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders modal when isOpen is true', () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(
        <NodeConfigModal
          isOpen={false}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays node label in header', () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/configure.*test node/i)).toBeInTheDocument();
    });

    it('displays node type badge', () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Find the type badge specifically (has capitalize class)
      const typeBadge = screen.getByText('tool');
      expect(typeBadge).toBeInTheDocument();
      expect(typeBadge).toHaveClass('capitalize');
    });
  });

  // ==============================================================================
  // Form Fields Tests
  // ==============================================================================

  describe('Form Fields', () => {
    it('renders label input with current value', () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const labelInput = screen.getByLabelText(/label/i);
      expect(labelInput).toHaveValue('Test Node');
    });

    it('allows editing the label', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const labelInput = screen.getByLabelText(/label/i);
      await user.clear(labelInput);
      await user.type(labelInput, 'New Label');

      expect(labelInput).toHaveValue('New Label');
    });

    it('renders config fields based on node type', () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Tool nodes should have tool-specific fields
      expect(screen.getByLabelText(/tool.*name/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Save/Cancel Actions
  // ==============================================================================

  describe('Actions', () => {
    it('calls onSave with updated data when save is clicked', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const labelInput = screen.getByLabelText(/label/i);
      await user.clear(labelInput);
      await user.type(labelInput, 'Updated Label');

      const saveButton = screen.getByRole('button', { name: /save/i });
      await user.click(saveButton);

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'node1',
          data: expect.objectContaining({
            label: 'Updated Label',
          }),
        })
      );
    });

    it('calls onClose when cancel is clicked', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onClose when clicking outside modal', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Click the backdrop
      const backdrop = screen.getByTestId('modal-backdrop');
      await user.click(backdrop);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onClose when Escape key is pressed', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Validation Tests
  // ==============================================================================

  describe('Validation', () => {
    it('disables save button when label is empty', async () => {
      const user = userEvent.setup();
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const labelInput = screen.getByLabelText(/label/i);
      await user.clear(labelInput);

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save/i });
        expect(saveButton).toBeDisabled();
      });

      // onSave should not be callable when disabled
      expect(mockOnSave).not.toHaveBeenCalled();
    });

    it('enables save button when label is valid', async () => {
      render(
        <NodeConfigModal
          isOpen={true}
          node={mockNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Initially should be enabled with valid label
      const saveButton = screen.getByRole('button', { name: /save/i });
      expect(saveButton).not.toBeDisabled();
    });
  });

  // ==============================================================================
  // Node Type Specific Tests
  // ==============================================================================

  describe('Node Type Specific Fields', () => {
    it('shows model selection for LLM nodes', () => {
      const llmNode = {
        ...mockNode,
        data: {
          ...mockNode.data,
          nodeType: 'llm' as const,
          config: { model: 'gpt-4', temperature: 0.7 },
        },
      };

      render(
        <NodeConfigModal
          isOpen={true}
          node={llmNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText(/model/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/temperature/i)).toBeInTheDocument();
    });

    it('shows condition expression for conditional nodes', () => {
      const conditionalNode = {
        ...mockNode,
        data: {
          ...mockNode.data,
          nodeType: 'conditional' as const,
          config: { condition: 'state.value > 0' },
        },
      };

      render(
        <NodeConfigModal
          isOpen={true}
          node={conditionalNode}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText(/condition/i)).toBeInTheDocument();
    });
  });
});
