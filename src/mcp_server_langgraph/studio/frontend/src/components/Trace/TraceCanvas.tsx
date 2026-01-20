/**
 * TraceCanvas Component
 *
 * React Flow canvas for visualizing trace spans in real-time.
 * Connects to the MCP WebSocket for live updates.
 */

import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import TraceNode from "./TraceNode";
import { useTraceWebSocket } from "../../hooks/useTraceWebSocket";
import { useTraceToReactFlow } from "../../hooks/useTraceToReactFlow";

import { Button } from "@/components/UI";

interface TraceCanvasProps {
  sessionId?: string;
  autoConnect?: boolean;
  className?: string;
}

// Define custom node types
const nodeTypes: NodeTypes = {
  traceNode: TraceNode,
};

export function TraceCanvas({
  sessionId,
  autoConnect = false,
  className = "",
}: TraceCanvasProps) {
  const { spans, events, isConnected, connect, disconnect, clearTraces } =
    useTraceWebSocket({ sessionId, autoConnect });

  const { nodes: flowNodes, edges: flowEdges } = useTraceToReactFlow({
    spans,
    layout: "horizontal",
  });

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Update nodes and edges when spans change
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const handleConnect = useCallback(() => {
    connect();
  }, [connect]);

  const handleDisconnect = useCallback(() => {
    disconnect();
  }, [disconnect]);

  const handleClear = useCallback(() => {
    clearTraces();
    setNodes([]);
    setEdges([]);
  }, [clearTraces, setNodes, setEdges]);

  return (
    <div className={`w-full h-full ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--neutral-4)" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(node) => node.data?.statusColor || "var(--primary-9)"}
          maskColor="var(--neutral-a4)"
        />

        {/* Control Panel */}
        <Panel
          position="top-right"
          className="bg-neutral-1 rounded-lg shadow-lg p-3"
        >
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <span
                className={`h-3 w-3 rounded-full ${
                  isConnected ? "bg-success-9" : "bg-neutral-4"
                }`}
              />
              <span className="text-sm text-neutral-11">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>

            {/* Span Count */}
            <div className="text-sm text-neutral-10">
              {spans.length} spans | {events.length} events
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              {!isConnected ? (
                <Button
                  variant="primary"
                  size="sm"
                  className="px-3 py-1 text-sm text-neutral-12 rounded hover:bg-primary-10"
                  onClick={handleConnect}
                >
                  Connect
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  size="sm"
                  className="px-3 py-1 text-sm bg-neutral-5 text-neutral-12 rounded hover:bg-neutral-4"
                  onClick={handleDisconnect}
                >
                  Disconnect
                </Button>
              )}
              <Button
                variant="danger"
                size="sm"
                className="px-3 py-1 text-sm bg-error-3 text-error-11 rounded hover:bg-error-4"
                onClick={handleClear}
              >
                Clear
              </Button>
            </div>
          </div>
        </Panel>

        {/* Empty State */}
        {spans.length === 0 && (
          <Panel position="top-center" className="mt-20">
            <div className="bg-neutral-1 rounded-lg shadow-lg p-6 text-center max-w-md">
              <div className="text-4xl mb-4">{isConnected ? "..." : "..."}</div>
              <h3 className="text-lg font-medium text-neutral-12 mb-2">
                {isConnected ? "Waiting for traces..." : "Not connected"}
              </h3>
              <p className="text-neutral-10 text-sm">
                {isConnected
                  ? "Trace spans will appear here as they are received from the MCP server."
                  : "Click Connect to start receiving real-time trace data."}
              </p>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}

export default TraceCanvas;
