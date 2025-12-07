/**
 * Tests for Workflow Validation Hook
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWorkflowValidation } from './useWorkflowValidation';
import type { Node, Edge } from 'reactflow';

// Mock axios for server validation
vi.mock('axios');

describe('useWorkflowValidation Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==============================================================================
  // Validation Result Types
  // ==============================================================================

  describe('Validation Result Structure', () => {
    it('returns validation result with valid, errors, and warnings fields', () => {
      const nodes: Node[] = [{ id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } }];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current).toHaveProperty('isValid');
      expect(result.current).toHaveProperty('errors');
      expect(result.current).toHaveProperty('warnings');
      expect(result.current).toHaveProperty('isValidating');
    });
  });

  // ==============================================================================
  // Node Validation Rules
  // ==============================================================================

  describe('Node Validation', () => {
    it('passes validation with valid start node', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start', nodeType: 'custom' }, position: { x: 0, y: 0 } },
      ];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.isValid).toBe(true);
      expect(result.current.errors).toHaveLength(0);
    });

    it('warns when workflow has only one node', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
      ];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.warnings).toContainEqual(
        expect.objectContaining({
          type: 'single_node',
          message: expect.stringContaining('single node'),
        })
      );
    });

    it('errors when node has no label', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: '' }, position: { x: 0, y: 0 } },
      ];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.errors).toContainEqual(
        expect.objectContaining({
          type: 'missing_label',
          nodeId: 'start',
        })
      );
    });

    it('detects duplicate node IDs', () => {
      const nodes: Node[] = [
        { id: 'node1', type: 'default', data: { label: 'Node 1' }, position: { x: 0, y: 0 } },
        { id: 'node1', type: 'default', data: { label: 'Node 2' }, position: { x: 100, y: 100 } },
      ];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.errors).toContainEqual(
        expect.objectContaining({
          type: 'duplicate_id',
        })
      );
    });
  });

  // ==============================================================================
  // Edge Validation Rules
  // ==============================================================================

  describe('Edge Validation', () => {
    it('detects orphan nodes (nodes with no edges)', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
        { id: 'orphan', type: 'default', data: { label: 'Orphan' }, position: { x: 100, y: 100 } },
      ];
      const edges: Edge[] = [];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      // Multiple unconnected nodes should produce warnings
      expect(result.current.warnings.length).toBeGreaterThan(0);
    });

    it('detects edges pointing to non-existent nodes', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
      ];
      const edges: Edge[] = [
        { id: 'e1', source: 'start', target: 'nonexistent' },
      ];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.errors).toContainEqual(
        expect.objectContaining({
          type: 'invalid_edge',
          edgeId: 'e1',
        })
      );
    });

    it('validates connected workflow', () => {
      const nodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
        { id: 'process', type: 'default', data: { label: 'Process' }, position: { x: 100, y: 100 } },
        { id: 'end', type: 'output', data: { label: 'End' }, position: { x: 200, y: 200 } },
      ];
      const edges: Edge[] = [
        { id: 'e1', source: 'start', target: 'process' },
        { id: 'e2', source: 'process', target: 'end' },
      ];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      expect(result.current.isValid).toBe(true);
      expect(result.current.errors).toHaveLength(0);
    });

    it('detects circular dependencies', () => {
      const nodes: Node[] = [
        { id: 'a', type: 'default', data: { label: 'A' }, position: { x: 0, y: 0 } },
        { id: 'b', type: 'default', data: { label: 'B' }, position: { x: 100, y: 100 } },
        { id: 'c', type: 'default', data: { label: 'C' }, position: { x: 200, y: 200 } },
      ];
      const edges: Edge[] = [
        { id: 'e1', source: 'a', target: 'b' },
        { id: 'e2', source: 'b', target: 'c' },
        { id: 'e3', source: 'c', target: 'a' },
      ];

      const { result } = renderHook(() => useWorkflowValidation(nodes, edges));

      // Circular dependencies may be warnings in graph workflows (valid for state machines)
      expect(result.current.warnings).toContainEqual(
        expect.objectContaining({
          type: 'circular_dependency',
        })
      );
    });
  });

  // ==============================================================================
  // Reactivity
  // ==============================================================================

  describe('Reactivity', () => {
    it('re-validates when nodes change', () => {
      const initialNodes: Node[] = [
        { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
      ];
      const edges: Edge[] = [];

      const { result, rerender } = renderHook(
        ({ nodes, edges }) => useWorkflowValidation(nodes, edges),
        { initialProps: { nodes: initialNodes, edges } }
      );

      // Initial validation with single node
      expect(result.current.warnings.length).toBeGreaterThan(0);

      // Add second node with edge
      const updatedNodes: Node[] = [
        ...initialNodes,
        { id: 'end', type: 'output', data: { label: 'End' }, position: { x: 100, y: 100 } },
      ];
      const updatedEdges: Edge[] = [
        { id: 'e1', source: 'start', target: 'end' },
      ];

      rerender({ nodes: updatedNodes, edges: updatedEdges });

      // Validation should update
      expect(result.current.isValid).toBe(true);
    });
  });
});
