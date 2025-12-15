/**
 * NodePalette Component
 *
 * Sidebar component with node types, undo/redo controls, and action buttons.
 */

import { Code2, Save, FileJson, Loader2, Undo2, Redo2 } from "lucide-react";

export type NodeType = "tool" | "llm" | "conditional" | "approval" | "custom";

const nodeTypes: Array<{
  type: NodeType;
  label: string;
  icon: string;
  description: string;
}> = [
  { type: "tool", label: "Tool", icon: "🔧", description: "Execute a tool" },
  { type: "llm", label: "LLM", icon: "🧠", description: "Call language model" },
  {
    type: "conditional",
    label: "Conditional",
    icon: "🔀",
    description: "Conditional routing",
  },
  {
    type: "approval",
    label: "Approval",
    icon: "✋",
    description: "Human approval",
  },
  {
    type: "custom",
    label: "Custom",
    icon: "⚙️",
    description: "Custom function",
  },
];

export interface NodePaletteProps {
  onAddNode: (type: NodeType) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onGenerateCode: () => void;
  onSaveToFile: () => void;
  onExportJSON: () => void;
  isGenerating: boolean;
  isSaving: boolean;
  isDarkMode: boolean;
}

export function NodePalette({
  onAddNode,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onGenerateCode,
  onSaveToFile,
  onExportJSON,
  isGenerating,
  isSaving,
  isDarkMode,
}: NodePaletteProps) {
  return (
    <aside
      className={`w-64 p-4 border-r ${
        isDarkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"
      }`}
    >
      {/* Undo/Redo Toolbar */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
          className={`flex-1 px-3 py-2 bg-gray-100 rounded-lg flex items-center justify-center gap-1 ${
            !canUndo ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-200"
          }`}
        >
          <Undo2 size={16} />
          <span className="text-sm">Undo</span>
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Y)"
          className={`flex-1 px-3 py-2 bg-gray-100 rounded-lg flex items-center justify-center gap-1 ${
            !canRedo ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-200"
          }`}
        >
          <Redo2 size={16} />
          <span className="text-sm">Redo</span>
        </button>
      </div>

      <h2
        className={`text-lg font-semibold mb-4 ${
          isDarkMode ? "text-white" : "text-gray-900"
        }`}
      >
        Node Types
      </h2>

      <div className="space-y-2">
        {nodeTypes.map((nodeType) => (
          <button
            key={nodeType.type}
            onClick={() => onAddNode(nodeType.type)}
            className={`w-full px-4 py-3 text-left rounded-lg transition-colors border ${
              isDarkMode
                ? "bg-gray-700 hover:bg-gray-600 border-gray-600 text-white"
                : "bg-gray-50 hover:bg-gray-100 border-gray-200"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-2xl">{nodeType.icon}</span>
              <div>
                <div className="font-medium">{nodeType.label}</div>
                <div
                  className={`text-xs ${
                    isDarkMode ? "text-gray-400" : "text-gray-500"
                  }`}
                >
                  {nodeType.description}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-8 space-y-2">
        <button
          onClick={onGenerateCode}
          disabled={isGenerating}
          title="Export Code (Ctrl+G)"
          className={`w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 ${
            isGenerating ? "opacity-50 cursor-not-allowed" : ""
          }`}
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
          onClick={onSaveToFile}
          disabled={isSaving}
          title="Save to File (Ctrl+S)"
          className={`w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 ${
            isSaving ? "opacity-50 cursor-not-allowed" : ""
          }`}
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
          onClick={onExportJSON}
          className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center justify-center gap-2"
        >
          <FileJson size={16} />
          Export JSON
        </button>
      </div>
    </aside>
  );
}
