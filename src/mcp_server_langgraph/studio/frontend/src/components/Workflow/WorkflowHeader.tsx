/**
 * WorkflowHeader Component
 *
 * Header component for the visual workflow builder with title, name input,
 * and action buttons (dark mode, settings, help).
 */

import { Sun, Moon, Settings, HelpCircle } from 'lucide-react';

export interface WorkflowHeaderProps {
  workflowName: string;
  onNameChange: (name: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
}

export function WorkflowHeader({
  workflowName,
  onNameChange,
  isDarkMode,
  onToggleDarkMode,
  onOpenSettings,
  onOpenHelp,
}: WorkflowHeaderProps) {
  return (
    <header
      className={`px-6 py-4 border-b ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <h1
            className={`text-2xl font-bold ${
              isDarkMode ? 'text-white' : 'text-gray-900'
            }`}
          >
            Visual Workflow Builder
          </h1>
          <p
            className={`text-sm ${
              isDarkMode ? 'text-gray-400' : 'text-gray-500'
            }`}
          >
            MCP Server with LangGraph - Build agents visually, export to code
          </p>
        </div>

        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => onNameChange(e.target.value)}
            className={`px-3 py-2 border rounded-md ${
              isDarkMode ? 'bg-gray-800 border-gray-600 text-white' : ''
            }`}
            placeholder="Workflow name"
          />
          <button
            onClick={onToggleDarkMode}
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
          <button
            onClick={onOpenSettings}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title="Settings"
            aria-label="Settings"
          >
            <Settings size={20} />
          </button>
          <button
            onClick={onOpenHelp}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title="Help"
            aria-label="Help"
          >
            <HelpCircle size={20} />
          </button>
        </div>
      </div>
    </header>
  );
}
