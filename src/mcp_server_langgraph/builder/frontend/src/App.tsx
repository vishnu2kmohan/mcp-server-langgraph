import React, { useCallback, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Download, Play, Save, Code2, FileJson } from 'lucide-react';
import Editor from '@monaco-editor/react';
import axios from 'axios';

// ==============================================================================
// Types
// ==============================================================================

interface WorkflowNode extends Node {
  data: {
    label: string;
    nodeType: 'tool' | 'llm' | 'conditional' | 'approval' | 'custom';
    config: Record<string, any>;
  };
}

// ==============================================================================
// Initial Nodes and Edges
// ==============================================================================

const initialNodes: WorkflowNode[] = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'Start', nodeType: 'custom', config: {} },
    position: { x: 250, y: 50 },
  },
];

const initialEdges: Edge[] = [];

// ==============================================================================
// Node Types Configuration
// ==============================================================================

const nodeTypeColors = {
  tool: '#3b82f6',      // Blue
  llm: '#8b5cf6',       // Purple
  conditional: '#f59e0b', // Orange
  approval: '#ef4444',  // Red
  custom: '#6b7280',    // Gray
};

const nodeTypes = [
  { type: 'tool', label: 'Tool', icon: '🔧', description: 'Execute a tool' },
  { type: 'llm', label: 'LLM', icon: '🧠', description: 'Call language model' },
  { type: 'conditional', label: 'Conditional', icon: '🔀', description: 'Conditional routing' },
  { type: 'approval', label: 'Approval', icon: '✋', description: 'Human approval' },
  { type: 'custom', label: 'Custom', icon: '⚙️', description: 'Custom function' },
];

// ==============================================================================
// Main App Component
// ==============================================================================

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [generatedCode, setGeneratedCode] = useState<string>('');
  const [showCodePanel, setShowCodePanel] = useState(false);
  const [workflowName, setWorkflowName] = useState('my_agent');
  const [workflowDescription, setWorkflowDescription] = useState('My custom agent workflow');

  // ==============================================================================
  // Node and Edge Handlers
  // ==============================================================================

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNode(node as WorkflowNode);
    },
    []
  );

  const addNewNode = useCallback(
    (nodeType: string) => {
      const id = `node_${Date.now()}`;
      const newNode: WorkflowNode = {
        id,
        type: 'default',
        data: {
          label: `${nodeType} Node`,
          nodeType: nodeType as any,
          config: {},
        },
        position: {
          x: Math.random() * 400 + 100,
          y: Math.random() * 400 + 100,
        },
        style: {
          background: nodeTypeColors[nodeType as keyof typeof nodeTypeColors],
          color: 'white',
          border: '2px solid #fff',
          borderRadius: '8px',
          padding: '10px',
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes]
  );

  // ==============================================================================
  // Code Generation
  // ==============================================================================

  const generateCode = async () => {
    try {
      // Build workflow definition
      const workflow = {
        name: workflowName,
        description: workflowDescription,
        nodes: nodes.map((node) => ({
          id: node.id,
          type: node.data.nodeType,
          label: node.data.label,
          config: node.data.config,
          position: node.position,
        })),
        edges: edges.map((edge) => ({
          from: edge.source,
          to: edge.target,
          label: edge.label || '',
        })),
        entry_point: nodes[0]?.id || 'start',
        state_schema: {
          query: 'str',
          result: 'str',
          metadata: 'Dict[str, Any]',
        },
      };

      // Call backend API
      const response = await axios.post('http://localhost:8001/api/builder/generate', {
        workflow,
      });

      setGeneratedCode(response.data.code);
      setShowCodePanel(true);
    } catch (error) {
      console.error('Code generation failed:', error);
      alert('Code generation failed. See console for details.');
    }
  };

  const downloadCode = () => {
    const blob = new Blob([generatedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName}.py`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const saveToFile = async () => {
    try {
      const workflow = {
        name: workflowName,
        description: workflowDescription,
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.data.nodeType,
          label: n.data.label,
          config: n.data.config,
        })),
        edges: edges.map((e) => ({
          from: e.source,
          to: e.target,
        })),
        entry_point: nodes[0]?.id || 'start',
        state_schema: {},
      };

      await axios.post('http://localhost:8001/api/builder/save', {
        workflow,
        output_path: `src/agents/${workflowName}.py`,
      });

      alert(`Workflow saved to src/agents/${workflowName}.py`);
    } catch (error) {
      console.error('Save failed:', error);
      alert('Save failed. See console for details.');
    }
  };

  // ==============================================================================
  // Render
  // ==============================================================================

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Visual Workflow Builder
            </h1>
            <p className="text-sm text-gray-500">
              MCP Server with LangGraph - Build agents visually, export to code
            </p>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              className="px-3 py-2 border rounded-md"
              placeholder="Workflow name"
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar - Node Palette */}
        <aside className="w-64 bg-white border-r border-gray-200 p-4">
          <h2 className="text-lg font-semibold mb-4">Node Types</h2>

          <div className="space-y-2">
            {nodeTypes.map((nodeType) => (
              <button
                key={nodeType.type}
                onClick={() => addNewNode(nodeType.type)}
                className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
              >
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{nodeType.icon}</span>
                  <div>
                    <div className="font-medium">{nodeType.label}</div>
                    <div className="text-xs text-gray-500">{nodeType.description}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-8 space-y-2">
            <button
              onClick={generateCode}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2"
            >
              <Code2 size={16} />
              Export Code
            </button>

            <button
              onClick={saveToFile}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2"
            >
              <Save size={16} />
              Save to File
            </button>

            <button
              onClick={() => {
                const json = JSON.stringify({ name: workflowName, nodes, edges }, null, 2);
                const blob = new Blob([json], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${workflowName}.json`;
                a.click();
              }}
              className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center justify-center gap-2"
            >
              <FileJson size={16} />
              Export JSON
            </button>
          </div>
        </aside>

        {/* Main Canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />

            <Panel position="top-right" className="bg-white p-4 rounded-lg shadow-lg">
              <div className="text-sm">
                <div className="font-semibold mb-2">Workflow Stats</div>
                <div>Nodes: {nodes.length}</div>
                <div>Edges: {edges.length}</div>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Code Panel */}
        {showCodePanel && (
          <aside className="w-1/2 bg-white border-l border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Generated Python Code</h2>
              <div className="flex gap-2">
                <button
                  onClick={downloadCode}
                  className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
                >
                  <Download size={14} />
                  Download
                </button>
                <button
                  onClick={() => setShowCodePanel(false)}
                  className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="flex-1">
              <Editor
                height="100%"
                defaultLanguage="python"
                value={generatedCode}
                theme="vs-dark"
                options={{
                  readOnly: false,
                  minimap: { enabled: true },
                  fontSize: 14,
                }}
              />
            </div>

            <div className="p-4 bg-green-50 border-t border-green-200">
              <div className="text-sm text-green-800">
                <span className="font-semibold">✨ Unique Feature:</span> Code export
                (OpenAI AgentKit doesn't have this!)
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-6 py-3 text-sm text-gray-600">
        <div className="flex justify-between items-center">
          <div>
            MCP Server with LangGraph Visual Builder - Drag nodes, connect edges, export
            production code
          </div>
          <div className="flex gap-4">
            <a href="/docs" className="hover:text-gray-900">
              Documentation
            </a>
            <a href="https://github.com/vishnu2kmohan/mcp-server-langgraph" className="hover:text-gray-900">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
