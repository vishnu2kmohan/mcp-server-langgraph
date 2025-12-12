/**
 * NodePalette Tests
 *
 * Tests for the node palette sidebar component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NodePalette } from './NodePalette';

describe('NodePalette', () => {
  const defaultProps = {
    onAddNode: vi.fn(),
    onUndo: vi.fn(),
    onRedo: vi.fn(),
    canUndo: true,
    canRedo: true,
    onGenerateCode: vi.fn(),
    onSaveToFile: vi.fn(),
    onExportJSON: vi.fn(),
    isGenerating: false,
    isSaving: false,
    isDarkMode: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render the node palette', () => {
      render(<NodePalette {...defaultProps} />);

      expect(screen.getByText('Node Types')).toBeInTheDocument();
    });

    it('should render all node type buttons', () => {
      render(<NodePalette {...defaultProps} />);

      expect(screen.getByText('Tool')).toBeInTheDocument();
      expect(screen.getByText('LLM')).toBeInTheDocument();
      expect(screen.getByText('Conditional')).toBeInTheDocument();
      expect(screen.getByText('Approval')).toBeInTheDocument();
      expect(screen.getByText('Custom')).toBeInTheDocument();
    });

    it('should render undo/redo buttons', () => {
      render(<NodePalette {...defaultProps} />);

      expect(screen.getByText('Undo')).toBeInTheDocument();
      expect(screen.getByText('Redo')).toBeInTheDocument();
    });

    it('should render action buttons', () => {
      render(<NodePalette {...defaultProps} />);

      expect(screen.getByText('Export Code')).toBeInTheDocument();
      expect(screen.getByText('Save to File')).toBeInTheDocument();
      expect(screen.getByText('Export JSON')).toBeInTheDocument();
    });
  });

  describe('Node Type Selection', () => {
    it('should call onAddNode with "tool" when Tool button is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Tool'));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith('tool');
    });

    it('should call onAddNode with "llm" when LLM button is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('LLM'));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith('llm');
    });

    it('should call onAddNode with "conditional" when Conditional button is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Conditional'));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith('conditional');
    });
  });

  describe('Undo/Redo', () => {
    it('should call onUndo when undo button is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Undo'));
      expect(defaultProps.onUndo).toHaveBeenCalled();
    });

    it('should call onRedo when redo button is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Redo'));
      expect(defaultProps.onRedo).toHaveBeenCalled();
    });

    it('should disable undo button when canUndo is false', () => {
      render(<NodePalette {...defaultProps} canUndo={false} />);

      const undoButton = screen.getByText('Undo').closest('button');
      expect(undoButton).toBeDisabled();
    });

    it('should disable redo button when canRedo is false', () => {
      render(<NodePalette {...defaultProps} canRedo={false} />);

      const redoButton = screen.getByText('Redo').closest('button');
      expect(redoButton).toBeDisabled();
    });
  });

  describe('Action Buttons', () => {
    it('should call onGenerateCode when Export Code is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Export Code'));
      expect(defaultProps.onGenerateCode).toHaveBeenCalled();
    });

    it('should call onSaveToFile when Save to File is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Save to File'));
      expect(defaultProps.onSaveToFile).toHaveBeenCalled();
    });

    it('should call onExportJSON when Export JSON is clicked', () => {
      render(<NodePalette {...defaultProps} />);

      fireEvent.click(screen.getByText('Export JSON'));
      expect(defaultProps.onExportJSON).toHaveBeenCalled();
    });

    it('should show loading state when generating code', () => {
      render(<NodePalette {...defaultProps} isGenerating={true} />);

      expect(screen.getByText('Generating...')).toBeInTheDocument();
    });

    it('should show loading state when saving', () => {
      render(<NodePalette {...defaultProps} isSaving={true} />);

      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    it('should disable Export Code button when generating', () => {
      render(<NodePalette {...defaultProps} isGenerating={true} />);

      const button = screen.getByText('Generating...').closest('button');
      expect(button).toBeDisabled();
    });
  });
});
