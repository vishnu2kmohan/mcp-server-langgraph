/**
 * TraceNode Component
 *
 * Custom React Flow node for displaying trace spans.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';

interface TraceNodeData {
  label: string;
  status: 'OK' | 'ERROR' | 'UNSET';
  statusColor: string;
  duration: string;
  attributes: Record<string, unknown>;
  traceId: string;
}

function TraceNode({ data, selected }: NodeProps<TraceNodeData>) {
  const statusClasses = {
    OK: 'bg-green-100 border-green-500 text-green-800',
    ERROR: 'bg-red-100 border-red-500 text-red-800',
    UNSET: 'bg-indigo-100 border-indigo-500 text-indigo-800',
  };

  return (
    <>
      <Handle type="target" position={Position.Left} className="w-2 h-2" />
      <div
        className={`
          px-4 py-2 rounded-lg border-2 min-w-[180px]
          ${statusClasses[data.status]}
          ${selected ? 'ring-2 ring-offset-2 ring-blue-500' : ''}
          transition-all duration-200 hover:shadow-lg
        `}
      >
        <div className="font-medium text-sm truncate max-w-[160px]" title={data.label}>
          {data.label}
        </div>
        {data.duration && (
          <div className="text-xs opacity-75 mt-1">
            {data.duration}
          </div>
        )}
        {data.status === 'UNSET' && (
          <div className="flex items-center gap-1 mt-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            <span className="text-xs">Running...</span>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="w-2 h-2" />
    </>
  );
}

export default memo(TraceNode);
