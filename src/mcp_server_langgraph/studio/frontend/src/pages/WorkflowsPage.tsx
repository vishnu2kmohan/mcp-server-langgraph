/**
 * WorkflowsPage
 *
 * Visual workflow builder page using React Flow for the canvas.
 * Integrates workflow store for state management.
 */

import { useCallback, useState } from 'react';
import { useWorkflowStore } from '../stores/workflowStore';
import {
  Save,
  Undo,
  Redo,
  Code,
  Download,
  Plus,
  Loader2,
} from 'lucide-react';

export function WorkflowsPage() {
  const [isGeneratingCode, setIsGeneratingCode] = useState(false);

  const {
    metadata,
    nodes,
    edges,
    isDirty,
    isSaving,
    isLoading,
    validation,
    undoStack,
    redoStack,
    createWorkflow,
    saveWorkflow,
    undo,
    redo,
    addNode,
    validate,
  } = useWorkflowStore();

  const canUndo = undoStack.length > 0;
  const canRedo = redoStack.length > 0;

  const handleSave = useCallback(async () => {
    if (!metadata) {
      // Create new workflow if none exists
      createWorkflow('New Workflow', 'Created in visual builder');
    }
    await saveWorkflow();
  }, [metadata, createWorkflow, saveWorkflow]);

  const handleGenerateCode = useCallback(async () => {
    setIsGeneratingCode(true);
    try {
      // Validate first
      const result = validate();
      if (!result.isValid) {
        alert('Please fix validation errors before generating code');
        return;
      }

      const response = await fetch('/api/v1/workflows/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: metadata?.name || 'Workflow',
          nodes,
          edges,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Create blob and download
        const blob = new Blob([data.code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename || 'workflow.py';
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to generate code:', error);
    } finally {
      setIsGeneratingCode(false);
    }
  }, [metadata, nodes, edges, validate]);

  const handleExportJSON = useCallback(() => {
    const data = {
      metadata,
      nodes,
      edges,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${metadata?.name || 'workflow'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [metadata, nodes, edges]);

  const handleAddNode = useCallback(() => {
    addNode('tool', { x: 250, y: 150 });
  }, [addNode]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {metadata?.name || 'New Workflow'}
            {isDirty && <span className="text-yellow-500 ml-1">*</span>}
          </h1>

          {!validation.isValid && (
            <span className="text-xs px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded">
              {validation.errors.length} errors
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={undo}
            disabled={!canUndo}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
            title="Undo"
          >
            <Undo size={18} />
          </button>
          <button
            onClick={redo}
            disabled={!canRedo}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
            title="Redo"
          >
            <Redo size={18} />
          </button>

          <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-2" />

          <button
            onClick={handleGenerateCode}
            disabled={isGeneratingCode}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 rounded hover:bg-purple-200"
          >
            <Code size={16} />
            Generate Code
          </button>

          <button
            onClick={handleExportJSON}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded hover:bg-gray-200"
          >
            <Download size={16} />
            Export JSON
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving || !isDirty}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            Save
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Node Palette */}
        <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-4">
            Add Nodes
          </h2>
          <div className="space-y-2">
            {(['tool', 'llm', 'conditional', 'approval', 'custom'] as const).map((type) => (
              <button
                key={type}
                onClick={() => addNode(type, { x: 250, y: 150 + nodes.length * 100 })}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                <Plus size={16} />
                {type.charAt(0).toUpperCase() + type.slice(1)} Node
              </button>
            ))}
          </div>

          {nodes.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-2">
                Nodes ({nodes.length})
              </h3>
              <ul className="space-y-1 text-sm text-gray-500 dark:text-gray-400">
                {nodes.map((node) => (
                  <li key={node.id} className="truncate">
                    {node.data.label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Canvas Area */}
        <div className="flex-1 flex items-center justify-center bg-gray-100 dark:bg-gray-900">
          {nodes.length === 0 ? (
            <div className="text-center">
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                No nodes yet. Add nodes from the sidebar to get started.
              </p>
              <button
                onClick={handleAddNode}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <Plus size={16} />
                Add First Node
              </button>
            </div>
          ) : (
            <div className="text-center text-gray-500 dark:text-gray-400">
              <p className="text-lg mb-2">Workflow Canvas</p>
              <p className="text-sm">
                {nodes.length} nodes, {edges.length} edges
              </p>
              <p className="text-xs mt-4">
                (React Flow canvas integration pending)
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default WorkflowsPage;
