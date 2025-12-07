/**
 * Workflow Validation Hook
 *
 * Provides real-time validation for workflow nodes and edges.
 * Validates:
 * - Node labels and IDs
 * - Edge connections
 * - Graph connectivity
 * - Circular dependencies (as warnings for state machines)
 */

import { useMemo } from 'react';
import type { Node, Edge } from 'reactflow';

// ==============================================================================
// Types
// ==============================================================================

export interface ValidationError {
  type: 'missing_label' | 'duplicate_id' | 'invalid_edge' | 'disconnected_graph';
  message: string;
  nodeId?: string;
  edgeId?: string;
}

export interface ValidationWarning {
  type: 'single_node' | 'orphan_node' | 'circular_dependency' | 'unconnected_nodes';
  message: string;
  nodeIds?: string[];
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  isValidating: boolean;
}

// ==============================================================================
// Validation Functions
// ==============================================================================

function findCircularDependencies(nodes: Node[], edges: Edge[]): string[][] {
  const graph = new Map<string, string[]>();
  const nodeIds = new Set(nodes.map(n => n.id));

  // Build adjacency list
  for (const node of nodes) {
    graph.set(node.id, []);
  }
  for (const edge of edges) {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
      graph.get(edge.source)?.push(edge.target);
    }
  }

  const cycles: string[][] = [];
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const path: string[] = [];

  function dfs(node: string): void {
    visited.add(node);
    recursionStack.add(node);
    path.push(node);

    for (const neighbor of graph.get(node) || []) {
      if (!visited.has(neighbor)) {
        dfs(neighbor);
      } else if (recursionStack.has(neighbor)) {
        // Found cycle
        const cycleStart = path.indexOf(neighbor);
        cycles.push(path.slice(cycleStart));
      }
    }

    path.pop();
    recursionStack.delete(node);
  }

  for (const node of nodeIds) {
    if (!visited.has(node)) {
      dfs(node);
    }
  }

  return cycles;
}

function findOrphanNodes(nodes: Node[], edges: Edge[]): string[] {
  if (nodes.length <= 1) return [];

  const connectedNodes = new Set<string>();
  for (const edge of edges) {
    connectedNodes.add(edge.source);
    connectedNodes.add(edge.target);
  }

  return nodes
    .map(n => n.id)
    .filter(id => !connectedNodes.has(id));
}

// ==============================================================================
// Hook Implementation
// ==============================================================================

export function useWorkflowValidation(nodes: Node[], edges: Edge[]): ValidationResult {
  return useMemo(() => {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // ========================================================================
    // Node Validation
    // ========================================================================

    // Check for empty labels
    for (const node of nodes) {
      const label = node.data?.label;
      if (!label || (typeof label === 'string' && label.trim() === '')) {
        errors.push({
          type: 'missing_label',
          message: `Node "${node.id}" has no label`,
          nodeId: node.id,
        });
      }
    }

    // Check for duplicate IDs
    const nodeIds = nodes.map(n => n.id);
    const idCounts = nodeIds.reduce((acc, id) => {
      acc[id] = (acc[id] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    for (const [id, count] of Object.entries(idCounts)) {
      if (count > 1) {
        errors.push({
          type: 'duplicate_id',
          message: `Duplicate node ID: ${id}`,
          nodeId: id,
        });
      }
    }

    // ========================================================================
    // Edge Validation
    // ========================================================================

    const validNodeIds = new Set(nodeIds);

    for (const edge of edges) {
      if (!validNodeIds.has(edge.source) || !validNodeIds.has(edge.target)) {
        errors.push({
          type: 'invalid_edge',
          message: `Edge "${edge.id}" references non-existent node`,
          edgeId: edge.id,
        });
      }
    }

    // ========================================================================
    // Connectivity Warnings
    // ========================================================================

    // Warn if only one node
    if (nodes.length === 1) {
      warnings.push({
        type: 'single_node',
        message: 'Workflow has only a single node. Consider adding more nodes.',
      });
    }

    // Find orphan nodes (nodes with no connections)
    const orphanNodes = findOrphanNodes(nodes, edges);
    if (orphanNodes.length > 0) {
      warnings.push({
        type: 'unconnected_nodes',
        message: `Nodes not connected to workflow: ${orphanNodes.join(', ')}`,
        nodeIds: orphanNodes,
      });
    }

    // ========================================================================
    // Circular Dependency Detection
    // ========================================================================

    const cycles = findCircularDependencies(nodes, edges);
    if (cycles.length > 0) {
      warnings.push({
        type: 'circular_dependency',
        message: `Circular dependencies detected: ${cycles.map(c => c.join(' -> ')).join('; ')}`,
        nodeIds: [...new Set(cycles.flat())],
      });
    }

    // ========================================================================
    // Result
    // ========================================================================

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      isValidating: false, // Synchronous validation, always complete
    };
  }, [nodes, edges]);
}

export default useWorkflowValidation;
