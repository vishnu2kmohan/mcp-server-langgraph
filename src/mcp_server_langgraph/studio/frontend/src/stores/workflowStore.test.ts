/**
 * workflowStore Tests
 *
 * TDD tests for workflow state management.
 * Tests cover:
 * - Initial state
 * - Node CRUD operations
 * - Edge CRUD operations
 * - Selection state
 * - Undo/redo functionality
 * - Validation
 * - Workflow persistence
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { createTestWorkflowStore } from './workflowStore';
// Types imported for documentation, actual usage through store methods

// Mock fetch
const mockFetch = vi.fn() as Mock;

describe('workflowStore', () => {
  let store: ReturnType<typeof createTestWorkflowStore>;

  beforeEach(() => {
    // Create fresh store for each test
    store = createTestWorkflowStore();
    // Reset mock and stub globally
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('initial state', () => {
    it('should have null metadata when no workflow loaded', () => {
      expect(store.getState().metadata).toBeNull();
    });

    it('should have empty nodes array', () => {
      expect(store.getState().nodes).toEqual([]);
    });

    it('should have empty edges array', () => {
      expect(store.getState().edges).toEqual([]);
    });

    it('should have empty selection', () => {
      expect(store.getState().selectedNodeIds).toEqual([]);
      expect(store.getState().selectedEdgeIds).toEqual([]);
    });

    it('should have empty undo/redo stacks', () => {
      expect(store.getState().undoStack).toEqual([]);
      expect(store.getState().redoStack).toEqual([]);
    });

    it('should not be dirty initially', () => {
      expect(store.getState().isDirty).toBe(false);
    });
  });

  describe('createWorkflow', () => {
    it('should create a new workflow with metadata', () => {
      // Act
      store.getState().createWorkflow('Test Workflow', 'A test workflow');

      // Assert
      const state = store.getState();
      expect(state.metadata).not.toBeNull();
      expect(state.metadata?.name).toBe('Test Workflow');
      expect(state.metadata?.description).toBe('A test workflow');
      expect(state.metadata?.version).toBe(1);
    });

    it('should reset nodes and edges when creating new workflow', () => {
      // Arrange - add some nodes first
      store.getState().addNode('tool', { x: 100, y: 100 });

      // Act
      store.getState().createWorkflow('New Workflow');

      // Assert
      expect(store.getState().nodes).toEqual([]);
      expect(store.getState().edges).toEqual([]);
    });

    it('should clear undo/redo stacks on new workflow', () => {
      // Arrange
      store.getState().createWorkflow('First');
      store.getState().addNode('tool', { x: 100, y: 100 });
      store.getState().takeSnapshot();

      // Act
      store.getState().createWorkflow('Second');

      // Assert
      expect(store.getState().undoStack).toEqual([]);
      expect(store.getState().redoStack).toEqual([]);
    });
  });

  describe('addNode', () => {
    it('should add a node with correct type and position', () => {
      // Act
      const nodeId = store.getState().addNode('tool', { x: 100, y: 200 });

      // Assert
      const nodes = store.getState().nodes;
      expect(nodes).toHaveLength(1);
      expect(nodes[0].id).toBe(nodeId);
      expect(nodes[0].data.nodeType).toBe('tool');
      expect(nodes[0].position).toEqual({ x: 100, y: 200 });
    });

    it('should add a node with custom label', () => {
      // Act
      store.getState().addNode('llm', { x: 50, y: 50 }, 'My LLM Node');

      // Assert
      expect(store.getState().nodes[0].data.label).toBe('My LLM Node');
    });

    it('should use default label based on type if not provided', () => {
      // Act
      store.getState().addNode('conditional', { x: 0, y: 0 });

      // Assert
      expect(store.getState().nodes[0].data.label).toBe('Conditional');
    });

    it('should mark workflow as dirty after adding node', () => {
      // Act
      store.getState().addNode('approval', { x: 0, y: 0 });

      // Assert
      expect(store.getState().isDirty).toBe(true);
    });

    it('should generate unique node IDs', () => {
      // Act
      const id1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const id2 = store.getState().addNode('tool', { x: 100, y: 0 });
      const id3 = store.getState().addNode('tool', { x: 200, y: 0 });

      // Assert
      expect(new Set([id1, id2, id3]).size).toBe(3);
    });
  });

  describe('updateNode', () => {
    it('should update node data', () => {
      // Arrange
      const nodeId = store.getState().addNode('tool', { x: 0, y: 0 });

      // Act
      store.getState().updateNode(nodeId, { label: 'Updated Label' });

      // Assert
      expect(store.getState().nodes[0].data.label).toBe('Updated Label');
    });

    it('should update node config', () => {
      // Arrange
      const nodeId = store.getState().addNode('llm', { x: 0, y: 0 });

      // Act
      store.getState().updateNode(nodeId, {
        config: { model: 'gpt-4', temperature: 0.7 },
      });

      // Assert
      expect(store.getState().nodes[0].data.config).toEqual({
        model: 'gpt-4',
        temperature: 0.7,
      });
    });

    it('should not affect other nodes when updating one', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 }, 'Node 1');
      const node2 = store.getState().addNode('tool', { x: 100, y: 0 }, 'Node 2');

      // Act
      store.getState().updateNode(node1, { label: 'Updated Node 1' });

      // Assert
      const nodes = store.getState().nodes;
      expect(nodes.find((n) => n.id === node1)?.data.label).toBe('Updated Node 1');
      expect(nodes.find((n) => n.id === node2)?.data.label).toBe('Node 2');
    });
  });

  describe('deleteNode', () => {
    it('should remove the specified node', () => {
      // Arrange
      const nodeId = store.getState().addNode('tool', { x: 0, y: 0 });

      // Act
      store.getState().deleteNode(nodeId);

      // Assert
      expect(store.getState().nodes).toHaveLength(0);
    });

    it('should remove connected edges when deleting a node', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });
      store.getState().addEdge(node1, node2);

      // Act
      store.getState().deleteNode(node1);

      // Assert
      expect(store.getState().edges).toHaveLength(0);
    });

    it('should remove node from selection when deleted', () => {
      // Arrange
      const nodeId = store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().setSelectedNodes([nodeId]);

      // Act
      store.getState().deleteNode(nodeId);

      // Assert
      expect(store.getState().selectedNodeIds).not.toContain(nodeId);
    });
  });

  describe('deleteNodes', () => {
    it('should delete multiple nodes at once', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 100, y: 0 });
      const node3 = store.getState().addNode('custom', { x: 200, y: 0 });

      // Act
      store.getState().deleteNodes([node1, node2]);

      // Assert
      expect(store.getState().nodes).toHaveLength(1);
      expect(store.getState().nodes[0].id).toBe(node3);
    });
  });

  describe('addEdge', () => {
    it('should add an edge between two nodes', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });

      // Act
      const edgeId = store.getState().addEdge(node1, node2);

      // Assert
      expect(edgeId).not.toBeNull();
      const edges = store.getState().edges;
      expect(edges).toHaveLength(1);
      expect(edges[0].source).toBe(node1);
      expect(edges[0].target).toBe(node2);
    });

    it('should not add duplicate edges', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });

      // Act
      store.getState().addEdge(node1, node2);
      const secondEdgeId = store.getState().addEdge(node1, node2);

      // Assert
      expect(secondEdgeId).toBeNull();
      expect(store.getState().edges).toHaveLength(1);
    });

    it('should not add self-loop edges', () => {
      // Arrange
      const nodeId = store.getState().addNode('tool', { x: 0, y: 0 });

      // Act
      const edgeId = store.getState().addEdge(nodeId, nodeId);

      // Assert
      expect(edgeId).toBeNull();
      expect(store.getState().edges).toHaveLength(0);
    });
  });

  describe('deleteEdge', () => {
    it('should remove the specified edge', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });
      const edgeId = store.getState().addEdge(node1, node2)!;

      // Act
      store.getState().deleteEdge(edgeId);

      // Assert
      expect(store.getState().edges).toHaveLength(0);
    });
  });

  describe('selection', () => {
    it('should set selected nodes', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 100, y: 0 });

      // Act
      store.getState().setSelectedNodes([node1, node2]);

      // Assert
      expect(store.getState().selectedNodeIds).toEqual([node1, node2]);
    });

    it('should set selected edges', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });
      const edgeId = store.getState().addEdge(node1, node2)!;

      // Act
      store.getState().setSelectedEdges([edgeId]);

      // Assert
      expect(store.getState().selectedEdgeIds).toEqual([edgeId]);
    });

    it('should clear all selection', () => {
      // Arrange
      const node1 = store.getState().addNode('tool', { x: 0, y: 0 });
      const node2 = store.getState().addNode('llm', { x: 200, y: 0 });
      const edgeId = store.getState().addEdge(node1, node2)!;
      store.getState().setSelectedNodes([node1]);
      store.getState().setSelectedEdges([edgeId]);

      // Act
      store.getState().clearSelection();

      // Assert
      expect(store.getState().selectedNodeIds).toEqual([]);
      expect(store.getState().selectedEdgeIds).toEqual([]);
    });
  });

  describe('undo/redo', () => {
    it('should undo adding a node', () => {
      // Arrange
      store.getState().takeSnapshot(); // Initial empty state
      store.getState().addNode('tool', { x: 0, y: 0 });

      // Act
      store.getState().undo();

      // Assert
      expect(store.getState().nodes).toHaveLength(0);
    });

    it('should redo an undone action', () => {
      // Arrange
      store.getState().takeSnapshot();
      store.getState().addNode('tool', { x: 100, y: 100 });
      store.getState().undo();

      // Act
      store.getState().redo();

      // Assert
      expect(store.getState().nodes).toHaveLength(1);
    });

    it('should report canUndo correctly', () => {
      // Initially no undo available
      expect(store.getState().undoStack.length).toBe(0);

      // After taking snapshot, can undo
      store.getState().takeSnapshot();
      expect(store.getState().undoStack.length).toBe(1);
    });

    it('should report canRedo correctly', () => {
      // Initially no redo available
      expect(store.getState().redoStack.length).toBe(0);

      // After undo, can redo
      store.getState().takeSnapshot();
      store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().undo();
      expect(store.getState().redoStack.length).toBe(1);
    });

    it('should clear redo stack when new action is taken after undo', () => {
      // Arrange
      store.getState().takeSnapshot();
      store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().undo();

      // Act - take new action
      store.getState().addNode('llm', { x: 100, y: 100 });

      // Assert - redo should be cleared
      expect(store.getState().redoStack).toEqual([]);
    });
  });

  describe('validate', () => {
    it('should return valid for empty workflow', () => {
      // Act
      const result = store.getState().validate();

      // Assert
      expect(result.isValid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('should detect disconnected nodes as warning', () => {
      // Arrange
      store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().addNode('llm', { x: 200, y: 0 });
      // No edge connecting them

      // Act
      const result = store.getState().validate();

      // Assert
      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it('should detect nodes without labels as error', () => {
      // Arrange
      const nodeId = store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().updateNode(nodeId, { label: '' });

      // Act
      const result = store.getState().validate();

      // Assert
      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.nodeId === nodeId)).toBe(true);
    });
  });

  describe('workflow persistence', () => {
    it('should set isLoading while loading workflow', async () => {
      // Arrange
      let resolveLoad!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveLoad = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    metadata: { id: 'wf-1', name: 'Test', version: 1 },
                    nodes: [],
                    edges: [],
                  }),
              });
          })
      );

      // Act
      const loadPromise = store.getState().loadWorkflow('wf-1');

      // Assert
      expect(store.getState().isLoading).toBe(true);

      // Cleanup
      resolveLoad();
      await loadPromise;
      expect(store.getState().isLoading).toBe(false);
    });

    it('should load workflow from API', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            metadata: {
              id: 'wf-123',
              name: 'Loaded Workflow',
              description: 'A loaded workflow',
              version: 2,
              createdAt: Date.now(),
              updatedAt: Date.now(),
            },
            nodes: [
              {
                id: 'node-1',
                position: { x: 100, y: 100 },
                data: { label: 'Test Node', nodeType: 'tool', config: {} },
              },
            ],
            edges: [],
          }),
      });

      // Act
      await store.getState().loadWorkflow('wf-123');

      // Assert
      const state = store.getState();
      expect(state.metadata?.id).toBe('wf-123');
      expect(state.metadata?.name).toBe('Loaded Workflow');
      expect(state.nodes).toHaveLength(1);
      expect(state.isDirty).toBe(false);
    });

    it('should save workflow to API', async () => {
      // Arrange
      store.getState().createWorkflow('My Workflow', 'Description');
      store.getState().addNode('tool', { x: 100, y: 100 });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'wf-saved',
            version: 1,
          }),
      });

      // Act
      await store.getState().saveWorkflow();

      // Assert
      expect(store.getState().isDirty).toBe(false);
      expect(store.getState().isSaving).toBe(false);
    });

    it('should set error on failed load', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Workflow not found' }),
      });

      // Act
      await store.getState().loadWorkflow('non-existent');

      // Assert
      expect(store.getState().error).toBe('Workflow not found');
      expect(store.getState().isLoading).toBe(false);
    });
  });

  describe('reset', () => {
    it('should reset to initial state', () => {
      // Arrange
      store.getState().createWorkflow('Test');
      store.getState().addNode('tool', { x: 0, y: 0 });
      store.getState().takeSnapshot();

      // Act
      store.getState().reset();

      // Assert
      const state = store.getState();
      expect(state.metadata).toBeNull();
      expect(state.nodes).toEqual([]);
      expect(state.edges).toEqual([]);
      expect(state.undoStack).toEqual([]);
      expect(state.redoStack).toEqual([]);
      expect(state.isDirty).toBe(false);
    });
  });
});
