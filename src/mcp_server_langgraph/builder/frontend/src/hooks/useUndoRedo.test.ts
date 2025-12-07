/**
 * Tests for Undo/Redo Hook
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUndoRedo } from './useUndoRedo';
import type { Node, Edge } from 'reactflow';

describe('useUndoRedo Hook', () => {
  const initialNodes: Node[] = [
    { id: 'start', type: 'input', data: { label: 'Start' }, position: { x: 0, y: 0 } },
  ];
  const initialEdges: Edge[] = [];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns undo, redo, canUndo, canRedo, and history functions', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      expect(result.current).toHaveProperty('undo');
      expect(result.current).toHaveProperty('redo');
      expect(result.current).toHaveProperty('canUndo');
      expect(result.current).toHaveProperty('canRedo');
      expect(result.current).toHaveProperty('takeSnapshot');
      expect(typeof result.current.undo).toBe('function');
      expect(typeof result.current.redo).toBe('function');
    });
  });

  // ==============================================================================
  // Initial State Tests
  // ==============================================================================

  describe('Initial State', () => {
    it('starts with canUndo false', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      expect(result.current.canUndo).toBe(false);
    });

    it('starts with canRedo false', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      expect(result.current.canRedo).toBe(false);
    });
  });

  // ==============================================================================
  // Snapshot Tests
  // ==============================================================================

  describe('Taking Snapshots', () => {
    it('enables undo after taking a snapshot', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      act(() => {
        result.current.takeSnapshot();
      });

      expect(result.current.canUndo).toBe(true);
    });

    it('maintains history of multiple snapshots', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      act(() => {
        result.current.takeSnapshot();
        result.current.takeSnapshot();
        result.current.takeSnapshot();
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  // ==============================================================================
  // Undo Tests
  // ==============================================================================

  describe('Undo Operation', () => {
    it('calls setNodes and setEdges with previous state on undo', () => {
      const setNodes = vi.fn();
      const setEdges = vi.fn();

      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, setNodes, setEdges)
      );

      // Take a snapshot first
      act(() => {
        result.current.takeSnapshot();
      });

      // Perform undo
      act(() => {
        result.current.undo();
      });

      expect(setNodes).toHaveBeenCalled();
      expect(setEdges).toHaveBeenCalled();
    });

    it('enables redo after undo', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      act(() => {
        result.current.takeSnapshot();
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.canRedo).toBe(true);
    });

    it('disables undo when history is exhausted', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      act(() => {
        result.current.takeSnapshot();
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.canUndo).toBe(false);
    });
  });

  // ==============================================================================
  // Redo Tests
  // ==============================================================================

  describe('Redo Operation', () => {
    it('calls setNodes and setEdges with next state on redo', () => {
      const setNodes = vi.fn();
      const setEdges = vi.fn();

      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, setNodes, setEdges)
      );

      act(() => {
        result.current.takeSnapshot();
      });

      act(() => {
        result.current.undo();
      });

      act(() => {
        result.current.redo();
      });

      // setNodes/setEdges called twice: once for undo, once for redo
      expect(setNodes).toHaveBeenCalledTimes(2);
      expect(setEdges).toHaveBeenCalledTimes(2);
    });

    it('disables redo after taking new snapshot', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn())
      );

      act(() => {
        result.current.takeSnapshot();
      });

      act(() => {
        result.current.undo();
      });

      expect(result.current.canRedo).toBe(true);

      // Taking a new snapshot should clear redo history
      act(() => {
        result.current.takeSnapshot();
      });

      expect(result.current.canRedo).toBe(false);
    });
  });

  // ==============================================================================
  // History Limit Tests
  // ==============================================================================

  describe('History Limits', () => {
    it('limits history to prevent memory bloat', () => {
      const { result } = renderHook(() =>
        useUndoRedo(initialNodes, initialEdges, vi.fn(), vi.fn(), 5)
      );

      // Take more snapshots than the limit
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.takeSnapshot();
        }
      });

      // Should still be able to undo, but only up to the limit
      let undoCount = 0;
      while (result.current.canUndo) {
        act(() => {
          result.current.undo();
        });
        undoCount++;
        if (undoCount > 10) break; // Safety to prevent infinite loop
      }

      expect(undoCount).toBeLessThanOrEqual(5);
    });
  });
});
