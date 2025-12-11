import React, { useCallback, useState, useEffect, useRef, Component, ErrorInfo, ReactNode } from 'react';
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
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Download, Save, Code2, FileJson, Loader2, AlertCircle, AlertTriangle, CheckCircle2, Undo2, Redo2, Sun, Moon, Trash2, Settings } from 'lucide-react';
import { useDarkMode } from './hooks/useDarkMode';
import { useWorkflowValidation } from './hooks/useWorkflowValidation';
import { useUndoRedo } from './hooks/useUndoRedo';
import { NodeConfigModal } from './components/NodeConfigModal';
import Editor from '@monaco-editor/react';
import axios from 'axios';
import { Toaster, toast } from 'sonner';

// ==============================================================================
// Error Boundary Component
// ==============================================================================

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md p-8 bg-white rounded-lg shadow-lg text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h2>
            <p className="text-gray-600 mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

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

function AppContent() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string>('');
  const [showCodePanel, setShowCodePanel] = useState(false);
  const [workflowName, setWorkflowName] = useState('my_agent');
  // Description setter is kept for future editing capability
  const [workflowDescription, _setWorkflowDescription] = useState('My custom agent workflow');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    nodeId: string;
  } | null>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  // Selected nodes for deletion
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);

  // ==============================================================================
  // Dark Mode
  // ==============================================================================

  const { isDarkMode, toggle: toggleDarkMode } = useDarkMode();

  // ==============================================================================
  // Workflow Validation
  // ==============================================================================

  const validation = useWorkflowValidation(nodes, edges);

  // ==============================================================================
  // Undo/Redo System
  // ==============================================================================

  const { undo, redo, canUndo, canRedo, takeSnapshot } = useUndoRedo(
    nodes,
    edges,
    setNodes,
    setEdges
  );

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
      setSelectedNodeIds([node.id]);
      setIsConfigModalOpen(true);
      setContextMenu(null); // Close context menu on node click
    },
    []
  );

  // Handle node selection change (for multi-select and deletion)
  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: Node[]; edges: Edge[] }) => {
      setSelectedNodeIds(selectedNodes.map((n) => n.id));
    },
    []
  );

  // Handle node right-click for context menu
  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        nodeId: node.id,
      });
      setSelectedNode(node as WorkflowNode);
    },
    []
  );

  // Delete selected nodes (excluding protected Start node)
  const deleteSelectedNodes = useCallback(() => {
    const nodesToDelete = selectedNodeIds.filter((id) => id !== 'start');
    const protectedNodeAttempted = selectedNodeIds.includes('start');

    if (protectedNodeAttempted && nodesToDelete.length === 0) {
      toast.error('Cannot delete the Start node');
      return;
    }

    if (nodesToDelete.length > 0) {
      takeSnapshot();
      setNodes((nds) => nds.filter((n) => !nodesToDelete.includes(n.id)));
      // Also remove edges connected to deleted nodes
      setEdges((eds) =>
        eds.filter(
          (e) => !nodesToDelete.includes(e.source) && !nodesToDelete.includes(e.target)
        )
      );
      toast.success(
        `Deleted ${nodesToDelete.length} node${nodesToDelete.length > 1 ? 's' : ''}`
      );

      if (protectedNodeAttempted) {
        toast.info('Start node was preserved (required)');
      }
    }

    setContextMenu(null);
  }, [selectedNodeIds, setNodes, setEdges, takeSnapshot]);

  // Delete specific node by ID
  const deleteNode = useCallback(
    (nodeId: string) => {
      if (nodeId === 'start') {
        toast.error('Cannot delete the Start node');
        return;
      }

      takeSnapshot();
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );
      toast.success('Node deleted');
      setContextMenu(null);
    },
    [setNodes, setEdges, takeSnapshot]
  );

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        contextMenuRef.current &&
        !contextMenuRef.current.contains(event.target as globalThis.Node)
      ) {
        setContextMenu(null);
      }
    };

    if (contextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [contextMenu]);

  // Handle node configuration save
  const handleNodeConfigSave = useCallback(
    (updatedNode: WorkflowNode) => {
      takeSnapshot();
      setNodes((nds) =>
        nds.map((n) => (n.id === updatedNode.id ? updatedNode : n))
      );
      setIsConfigModalOpen(false);
    },
    [setNodes, takeSnapshot]
  );

  const addNewNode = useCallback(
    (nodeType: string) => {
      // Take snapshot before making changes for undo support
      takeSnapshot();

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
    [setNodes, takeSnapshot]
  );

  // ==============================================================================
  // Code Generation
  // ==============================================================================

  const generateCode = async () => {
    if (isGenerating) return;
    setIsGenerating(true);

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
      toast.success('Code generated successfully!');
    } catch (error) {
      console.error('Code generation failed:', error);
      toast.error('Code generation failed. See console for details.');
    } finally {
      setIsGenerating(false);
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
    if (isSaving) return;
    setIsSaving(true);

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

      toast.success(`Workflow saved to src/agents/${workflowName}.py`);
    } catch (error) {
      console.error('Save failed:', error);
      toast.error('Save failed. See console for details.');
    } finally {
      setIsSaving(false);
    }
  };

  // ==============================================================================
  // Keyboard Shortcuts
  // ==============================================================================

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle shortcuts when typing in inputs
      const target = e.target as HTMLElement;
      const isInputField =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Ctrl+S or Cmd+S for save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveToFile();
      }
      // Ctrl+G or Cmd+G for generate code
      if ((e.ctrlKey || e.metaKey) && e.key === 'g') {
        e.preventDefault();
        generateCode();
      }
      // Ctrl+Z or Cmd+Z for undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) undo();
      }
      // Ctrl+Y or Cmd+Shift+Z for redo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        if (canRedo) redo();
      }
      // Delete or Backspace to delete selected nodes (only when not in input fields)
      if (!isInputField && (e.key === 'Delete' || e.key === 'Backspace')) {
        e.preventDefault();
        if (selectedNodeIds.length > 0) {
          deleteSelectedNodes();
        }
      }
      // Escape to close context menu
      if (e.key === 'Escape') {
        setContextMenu(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [nodes, edges, workflowName, workflowDescription, isGenerating, isSaving, canUndo, canRedo, undo, redo, selectedNodeIds, deleteSelectedNodes]);

  // ==============================================================================
  // Render
  // ==============================================================================

  return (
    <div className={`h-screen flex flex-col ${isDarkMode ? 'dark bg-gray-900' : 'bg-gray-50'}`}>
      <Toaster position="top-right" richColors closeButton />
      {/* Header */}
      <header className={`px-6 py-4 border-b ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Visual Workflow Builder
            </h1>
            <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              MCP Server with LangGraph - Build agents visually, export to code
            </p>
          </div>

          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              className={`px-3 py-2 border rounded-md ${isDarkMode ? 'bg-gray-800 border-gray-600 text-white' : ''}`}
              placeholder="Workflow name"
            />
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg transition-colors ${
                isDarkMode
                  ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar - Node Palette */}
        <aside className={`w-64 p-4 border-r ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          {/* Undo/Redo Toolbar */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={undo}
              disabled={!canUndo}
              title="Undo (Ctrl+Z)"
              className={`flex-1 px-3 py-2 bg-gray-100 rounded-lg flex items-center justify-center gap-1 ${
                !canUndo ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-200'
              }`}
            >
              <Undo2 size={16} />
              <span className="text-sm">Undo</span>
            </button>
            <button
              onClick={redo}
              disabled={!canRedo}
              title="Redo (Ctrl+Y)"
              className={`flex-1 px-3 py-2 bg-gray-100 rounded-lg flex items-center justify-center gap-1 ${
                !canRedo ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-200'
              }`}
            >
              <Redo2 size={16} />
              <span className="text-sm">Redo</span>
            </button>
          </div>

          <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Node Types</h2>

          <div className="space-y-2">
            {nodeTypes.map((nodeType) => (
              <button
                key={nodeType.type}
                onClick={() => addNewNode(nodeType.type)}
                className={`w-full px-4 py-3 text-left rounded-lg transition-colors border ${
                  isDarkMode
                    ? 'bg-gray-700 hover:bg-gray-600 border-gray-600 text-white'
                    : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{nodeType.icon}</span>
                  <div>
                    <div className="font-medium">{nodeType.label}</div>
                    <div className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{nodeType.description}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-8 space-y-2">
            <button
              onClick={generateCode}
              disabled={isGenerating}
              title="Export Code (Ctrl+G)"
              className={`w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Code2 size={16} />
                  Export Code
                </>
              )}
            </button>

            <button
              onClick={saveToFile}
              disabled={isSaving}
              title="Save to File (Ctrl+S)"
              className={`w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isSaving ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save size={16} />
                  Save to File
                </>
              )}
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
            onNodeContextMenu={onNodeContextMenu}
            onSelectionChange={onSelectionChange}
            onPaneClick={() => setContextMenu(null)}
            deleteKeyCode={null}
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

            {/* Validation Panel */}
            <Panel position="bottom-right" className="bg-white p-4 rounded-lg shadow-lg max-w-xs" data-testid="validation-panel">
              <div className="text-sm">
                <div className="font-semibold mb-2 flex items-center gap-2">
                  {validation.isValid && validation.warnings.length === 0 ? (
                    <>
                      <CheckCircle2 size={16} className="text-green-600" />
                      <span className="text-green-600">Workflow Valid</span>
                    </>
                  ) : validation.errors.length > 0 ? (
                    <>
                      <AlertCircle size={16} className="text-red-600" />
                      <span className="text-red-600">Validation Errors</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={16} className="text-yellow-600" />
                      <span className="text-yellow-600">Warnings</span>
                    </>
                  )}
                </div>

                {/* Errors */}
                {validation.errors.length > 0 && (
                  <div className="mt-2">
                    {validation.errors.map((error, idx) => (
                      <div key={idx} className="text-red-600 text-xs flex items-start gap-1 mt-1">
                        <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
                        <span>{error.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Warnings */}
                {validation.warnings.length > 0 && (
                  <div className="mt-2">
                    {validation.warnings.map((warning, idx) => (
                      <div key={idx} className="text-yellow-600 text-xs flex items-start gap-1 mt-1">
                        <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
                        <span>{warning.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Valid state */}
                {validation.isValid && validation.warnings.length === 0 && (
                  <div className="text-green-600 text-xs mt-1">
                    All nodes connected and configured correctly.
                  </div>
                )}
              </div>
            </Panel>
          </ReactFlow>

          {/* Context Menu */}
          {contextMenu && (
            <div
              ref={contextMenuRef}
              data-testid="context-menu"
              className={`absolute z-50 min-w-[160px] rounded-lg shadow-lg border ${
                isDarkMode
                  ? 'bg-gray-800 border-gray-600'
                  : 'bg-white border-gray-200'
              }`}
              style={{
                left: contextMenu.x,
                top: contextMenu.y,
              }}
              role="menu"
            >
              <button
                onClick={() => {
                  if (selectedNode) {
                    setIsConfigModalOpen(true);
                  }
                  setContextMenu(null);
                }}
                role="menuitem"
                className={`w-full px-4 py-2 text-left flex items-center gap-2 rounded-t-lg ${
                  isDarkMode
                    ? 'text-white hover:bg-gray-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Settings size={16} />
                Configure Node
              </button>
              <button
                onClick={() => deleteNode(contextMenu.nodeId)}
                role="menuitem"
                disabled={contextMenu.nodeId === 'start'}
                className={`w-full px-4 py-2 text-left flex items-center gap-2 rounded-b-lg ${
                  contextMenu.nodeId === 'start'
                    ? 'text-gray-400 cursor-not-allowed'
                    : isDarkMode
                    ? 'text-red-400 hover:bg-gray-700'
                    : 'text-red-600 hover:bg-gray-100'
                }`}
              >
                <Trash2 size={16} />
                Delete Node
                {contextMenu.nodeId === 'start' && (
                  <span className="text-xs ml-auto">(protected)</span>
                )}
              </button>
            </div>
          )}
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
      <footer className={`px-6 py-3 text-sm border-t ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-200 text-gray-600'}`}>
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

      {/* Node Configuration Modal */}
      <NodeConfigModal
        isOpen={isConfigModalOpen}
        node={selectedNode}
        onSave={handleNodeConfigSave}
        onClose={() => setIsConfigModalOpen(false)}
      />
    </div>
  );
}

// ==============================================================================
// Main App Component with Error Boundary
// ==============================================================================

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
