/**
 * useTraceToReactFlow Hook
 *
 * Converts trace spans into React Flow nodes and edges for visualization.
 */

import { useMemo } from 'react';
import type { Node, Edge } from 'reactflow';
import type { TraceSpan } from './useTraceWebSocket';

interface UseTraceToReactFlowOptions {
  spans: TraceSpan[];
  layout?: 'horizontal' | 'vertical';
  nodeWidth?: number;
  nodeHeight?: number;
  nodeSpacing?: number;
}

interface UseTraceToReactFlowReturn {
  nodes: Node[];
  edges: Edge[];
}

export function useTraceToReactFlow(
  options: UseTraceToReactFlowOptions
): UseTraceToReactFlowReturn {
  const {
    spans,
    layout = 'horizontal',
    nodeWidth = 200,
    nodeHeight = 60,
    nodeSpacing = 100,
  } = options;

  const { nodes, edges } = useMemo(() => {
    if (spans.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Build parent-child relationships
    const spanMap = new Map<string, TraceSpan>();
    const childrenMap = new Map<string, string[]>();

    for (const span of spans) {
      spanMap.set(span.spanId, span);

      if (span.parentSpanId) {
        const children = childrenMap.get(span.parentSpanId) || [];
        children.push(span.spanId);
        childrenMap.set(span.parentSpanId, children);
      }
    }

    // Find root spans (no parent)
    const rootSpans = spans.filter((s) => !s.parentSpanId);

    // Calculate positions using BFS
    const positions = new Map<string, { x: number; y: number }>();
    const queue: Array<{ spanId: string; depth: number; siblingIndex: number }> = [];

    // Initialize with root spans
    rootSpans.forEach((span, index) => {
      queue.push({ spanId: span.spanId, depth: 0, siblingIndex: index });
    });

    const maxSiblingAtDepth = new Map<number, number>();

    while (queue.length > 0) {
      const { spanId, depth, siblingIndex } = queue.shift()!;

      // Track max sibling index at each depth
      const currentMax = maxSiblingAtDepth.get(depth) || 0;
      maxSiblingAtDepth.set(depth, Math.max(currentMax, siblingIndex));

      // Calculate position based on layout
      const x =
        layout === 'horizontal'
          ? depth * (nodeWidth + nodeSpacing)
          : siblingIndex * (nodeWidth + nodeSpacing);

      const y =
        layout === 'horizontal'
          ? siblingIndex * (nodeHeight + nodeSpacing)
          : depth * (nodeHeight + nodeSpacing);

      positions.set(spanId, { x, y });

      // Add children to queue
      const children = childrenMap.get(spanId) || [];
      children.forEach((childId, index) => {
        queue.push({
          spanId: childId,
          depth: depth + 1,
          siblingIndex: index,
        });
      });
    }

    // Create React Flow nodes
    const flowNodes: Node[] = spans.map((span) => {
      const position = positions.get(span.spanId) || { x: 0, y: 0 };

      // Determine node status color
      let statusColor = '#6366f1'; // Default indigo
      if (span.status === 'OK') {
        statusColor = '#22c55e'; // Green
      } else if (span.status === 'ERROR') {
        statusColor = '#ef4444'; // Red
      }

      // Calculate duration
      let duration = '';
      if (span.startTime && span.endTime) {
        const start = new Date(span.startTime).getTime();
        const end = new Date(span.endTime).getTime();
        const durationMs = end - start;
        duration = durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(2)}s`;
      }

      return {
        id: span.spanId,
        type: 'traceNode',
        position,
        data: {
          label: span.name,
          status: span.status,
          statusColor,
          duration,
          attributes: span.attributes,
          traceId: span.traceId,
        },
      };
    });

    // Create React Flow edges
    const flowEdges: Edge[] = spans
      .filter((span) => span.parentSpanId)
      .map((span) => ({
        id: `${span.parentSpanId}-${span.spanId}`,
        source: span.parentSpanId!,
        target: span.spanId,
        type: 'smoothstep',
        animated: span.status === 'UNSET' || !span.endTime,
        style: {
          stroke: span.status === 'ERROR' ? '#ef4444' : '#6366f1',
          strokeWidth: 2,
        },
      }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [spans, layout, nodeWidth, nodeHeight, nodeSpacing]);

  return { nodes, edges };
}

export default useTraceToReactFlow;
