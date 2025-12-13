/**
 * WorkflowsPage Tests
 *
 * TDD tests for the workflow builder page.
 * Tests cover:
 * - Loading state
 * - Toolbar functionality
 * - Node management
 * - Save workflow
 * - Undo/Redo
 * - Export functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { WorkflowsPage } from './WorkflowsPage';
import * as workflowStoreModule from '../stores/workflowStore';

// Mock the workflow store
vi.mock('../stores/workflowStore');

// Mock fetch for code generation
global.fetch = vi.fn();

const mockUseWorkflowStore = vi.mocked(workflowStoreModule.useWorkflowStore);

describe('WorkflowsPage', () => {
  const mockCreateWorkflow = vi.fn();
  const mockSaveWorkflow = vi.fn();
  const mockUndo = vi.fn();
  const mockRedo = vi.fn();
  const mockAddNode = vi.fn();
  const mockValidate = vi.fn(() => ({ isValid: true, errors: [] }));

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseWorkflowStore.mockReturnValue({
      metadata: null,
      nodes: [],
      edges: [],
      isDirty: false,
      isSaving: false,
      isLoading: false,
      validation: { isValid: true, errors: [] },
      undoStack: [],
      redoStack: [],
      createWorkflow: mockCreateWorkflow,
      saveWorkflow: mockSaveWorkflow,
      undo: mockUndo,
      redo: mockRedo,
      addNode: mockAddNode,
      validate: mockValidate,
      loadWorkflow: vi.fn(),
      deleteNode: vi.fn(),
      updateNode: vi.fn(),
      addEdge: vi.fn(),
      removeEdge: vi.fn(),
      setNodes: vi.fn(),
      setEdges: vi.fn(),
      clearWorkflow: vi.fn(),
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        isLoading: true,
      });

      render(<WorkflowsPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Toolbar', () => {
    it('should display workflow name', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        metadata: { id: 'wf-1', name: 'My Workflow', description: '' },
      });

      render(<WorkflowsPage />);

      expect(screen.getByText('My Workflow')).toBeInTheDocument();
    });

    it('should display "New Workflow" when no metadata', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('New Workflow')).toBeInTheDocument();
    });

    it('should show dirty indicator when changes exist', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        metadata: { id: 'wf-1', name: 'My Workflow', description: '' },
        isDirty: true,
      });

      render(<WorkflowsPage />);

      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('should show error count when validation fails', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        validation: { isValid: false, errors: [{ nodeId: 'n1', message: 'Error 1' }, { nodeId: 'n2', message: 'Error 2' }] },
      });

      render(<WorkflowsPage />);

      expect(screen.getByText('2 errors')).toBeInTheDocument();
    });
  });

  describe('Undo/Redo', () => {
    it('should disable undo button when no undo history', () => {
      render(<WorkflowsPage />);

      const undoButton = screen.getByTitle('Undo');
      expect(undoButton).toBeDisabled();
    });

    it('should enable undo button when undo history exists', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        undoStack: [{ nodes: [], edges: [] }],
      });

      render(<WorkflowsPage />);

      const undoButton = screen.getByTitle('Undo');
      expect(undoButton).not.toBeDisabled();
    });

    it('should call undo when undo button is clicked', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        undoStack: [{ nodes: [], edges: [] }],
      });

      render(<WorkflowsPage />);

      fireEvent.click(screen.getByTitle('Undo'));
      expect(mockUndo).toHaveBeenCalled();
    });

    it('should disable redo button when no redo history', () => {
      render(<WorkflowsPage />);

      const redoButton = screen.getByTitle('Redo');
      expect(redoButton).toBeDisabled();
    });

    it('should call redo when redo button is clicked', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        redoStack: [{ nodes: [], edges: [] }],
      });

      render(<WorkflowsPage />);

      fireEvent.click(screen.getByTitle('Redo'));
      expect(mockRedo).toHaveBeenCalled();
    });
  });

  describe('Save Workflow', () => {
    it('should have save button', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    it('should disable save button when not dirty', () => {
      render(<WorkflowsPage />);

      const saveButton = screen.getByText('Save');
      expect(saveButton.closest('button')).toBeDisabled();
    });

    it('should enable save button when dirty', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        isDirty: true,
      });

      render(<WorkflowsPage />);

      const saveButton = screen.getByText('Save');
      expect(saveButton.closest('button')).not.toBeDisabled();
    });

    it('should call saveWorkflow when save is clicked', async () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        metadata: { id: 'wf-1', name: 'My Workflow', description: '' },
        isDirty: true,
      });

      render(<WorkflowsPage />);

      fireEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockSaveWorkflow).toHaveBeenCalled();
      });
    });

    it('should create workflow if none exists before saving', async () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        metadata: null,
        isDirty: true,
      });

      render(<WorkflowsPage />);

      fireEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockCreateWorkflow).toHaveBeenCalledWith('New Workflow', 'Created in visual builder');
      });
    });
  });

  describe('Node Palette', () => {
    it('should show Add Nodes section', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('Add Nodes')).toBeInTheDocument();
    });

    it('should have buttons for each node type', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('Tool Node')).toBeInTheDocument();
      expect(screen.getByText('Llm Node')).toBeInTheDocument();
      expect(screen.getByText('Conditional Node')).toBeInTheDocument();
      expect(screen.getByText('Approval Node')).toBeInTheDocument();
      expect(screen.getByText('Custom Node')).toBeInTheDocument();
    });

    it('should call addNode when node type button is clicked', () => {
      render(<WorkflowsPage />);

      fireEvent.click(screen.getByText('Tool Node'));

      expect(mockAddNode).toHaveBeenCalledWith('tool', expect.any(Object));
    });
  });

  describe('Canvas Area', () => {
    it('should show empty state when no nodes', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText(/No nodes yet/)).toBeInTheDocument();
      expect(screen.getByText('Add First Node')).toBeInTheDocument();
    });

    it('should show node and edge counts when nodes exist', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        nodes: [
          { id: 'n1', type: 'tool', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
          { id: 'n2', type: 'llm', position: { x: 100, y: 0 }, data: { label: 'Node 2' } },
        ],
        edges: [{ id: 'e1', source: 'n1', target: 'n2' }],
      });

      render(<WorkflowsPage />);

      expect(screen.getByText('2 nodes, 1 edges')).toBeInTheDocument();
    });

    it('should show nodes list in sidebar when nodes exist', () => {
      mockUseWorkflowStore.mockReturnValue({
        ...mockUseWorkflowStore(),
        nodes: [
          { id: 'n1', type: 'tool', position: { x: 0, y: 0 }, data: { label: 'My Tool Node' } },
        ],
      });

      render(<WorkflowsPage />);

      expect(screen.getByText('Nodes (1)')).toBeInTheDocument();
      expect(screen.getByText('My Tool Node')).toBeInTheDocument();
    });
  });

  describe('Export', () => {
    it('should have Generate Code button', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('Generate Code')).toBeInTheDocument();
    });

    it('should have Export JSON button', () => {
      render(<WorkflowsPage />);

      expect(screen.getByText('Export JSON')).toBeInTheDocument();
    });
  });
});
