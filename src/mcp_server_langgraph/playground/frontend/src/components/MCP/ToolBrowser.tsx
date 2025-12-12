/**
 * ToolBrowser Component
 *
 * Displays available MCP tools with search, filtering, and execution capabilities.
 */

import React, { useState, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import { useMCPTools } from '../../hooks/useMCPTools';
import { ToolCard } from './ToolCard';
import type { MCPTool } from '../../api/mcp-types';

export interface ToolBrowserProps {
  className?: string;
  onToolSelect?: (tool: MCPTool) => void;
}

export function ToolBrowser({ className, onToolSelect }: ToolBrowserProps): React.ReactElement {
  const { tools } = useMCPTools();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);

  // Filter tools by search query
  const filteredTools = useMemo(() => {
    if (!searchQuery.trim()) return tools;

    const query = searchQuery.toLowerCase();
    return tools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(query) ||
        tool.description.toLowerCase().includes(query)
    );
  }, [tools, searchQuery]);

  const handleToolClick = useCallback(
    (tool: MCPTool) => {
      setSelectedTool(tool);
      onToolSelect?.(tool);
    },
    [onToolSelect]
  );

  const handleClose = useCallback(() => {
    setSelectedTool(null);
  }, []);

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header with search */}
      <div className="p-3 border-b border-gray-200 dark:border-dark-border">
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider mb-2">
          Tools ({tools.length})
        </h3>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search tools..."
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text placeholder-gray-400 dark:placeholder-dark-textMuted focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Tool list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {filteredTools.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-dark-textMuted">
            {tools.length === 0 ? (
              <p>No tools available. Connect to an MCP server.</p>
            ) : (
              <p>No tools match your search.</p>
            )}
          </div>
        ) : (
          filteredTools.map((tool) => (
            <ToolCard
              key={tool.name}
              tool={tool}
              isSelected={selectedTool?.name === tool.name}
              onClick={() => handleToolClick(tool)}
            />
          ))
        )}
      </div>

      {/* Selected tool detail panel */}
      {selectedTool && (
        <ToolDetailPanel tool={selectedTool} onClose={handleClose} />
      )}
    </div>
  );
}

interface ToolDetailPanelProps {
  tool: MCPTool;
  onClose: () => void;
}

function ToolDetailPanel({ tool, onClose }: ToolDetailPanelProps): React.ReactElement {
  const { callTool } = useMCPTools();
  const [result, setResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = useCallback(
    async (args: Record<string, unknown>) => {
      setIsLoading(true);
      setError(null);
      setResult(null);

      try {
        const toolResult = await callTool(tool.name, args);
        const content = toolResult.content
          .map((c) => (c.type === 'text' ? c.text : JSON.stringify(c)))
          .join('\n');
        setResult(content);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Tool execution failed');
      } finally {
        setIsLoading(false);
      }
    },
    [callTool, tool.name]
  );

  const hasParameters = Object.keys(tool.inputSchema.properties || {}).length > 0;

  return (
    <div className="border-t border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-surface">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-dark-border">
        <h4 className="font-medium text-gray-900 dark:text-dark-text">{tool.name}</h4>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-dark-text"
          aria-label="Close tool details"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-3 max-h-64 overflow-y-auto">
        <p className="text-sm text-gray-600 dark:text-dark-textSecondary mb-3">
          {tool.description}
        </p>

        {hasParameters ? (
          <div className="space-y-3">
            <div className="bg-white dark:bg-dark-bg p-3 rounded-lg border border-gray-200 dark:border-dark-border">
              <SchemaFormCompact
                schema={tool.inputSchema}
                onSubmit={handleExecute}
                isLoading={isLoading}
              />
            </div>
          </div>
        ) : (
          <button
            onClick={() => handleExecute({})}
            disabled={isLoading}
            className="w-full px-4 py-2 rounded-lg font-medium bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {isLoading ? 'Executing...' : 'Execute'}
          </button>
        )}

        {/* Results */}
        {error && (
          <div className="mt-3 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
            <p className="text-sm text-error-700 dark:text-error-400">{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-3 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
            <pre className="text-sm text-success-700 dark:text-success-400 whitespace-pre-wrap overflow-x-auto">
              {result}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

// Compact version of SchemaForm for tool execution
import type { JSONSchema } from '../../api/mcp-types';

interface SchemaFormCompactProps {
  schema: JSONSchema;
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading?: boolean;
}

function SchemaFormCompact({ schema, onSubmit, isLoading }: SchemaFormCompactProps): React.ReactElement {
  const [formData, setFormData] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    const properties = schema.properties || {};
    Object.entries(properties).forEach(([key, prop]) => {
      const p = prop as JSONSchema;
      if (p.default !== undefined) initial[key] = p.default;
      else if (p.type === 'boolean') initial[key] = false;
      else if (p.type === 'number' || p.type === 'integer') initial[key] = '';
      else initial[key] = '';
    });
    return initial;
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Filter out empty string values
    const cleanedData: Record<string, unknown> = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value !== '') cleanedData[key] = value;
    });
    onSubmit(cleanedData);
  };

  const properties = schema.properties || {};
  const required = schema.required || [];

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {Object.entries(properties).map(([key, prop]) => {
        const property = prop as JSONSchema;
        const isRequired = required.includes(key);

        return (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-600 dark:text-dark-textSecondary mb-1">
              {key}
              {isRequired && <span className="text-error-500 ml-1">*</span>}
            </label>

            {property.type === 'boolean' ? (
              <input
                type="checkbox"
                checked={Boolean(formData[key])}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.checked })}
                className="h-4 w-4"
              />
            ) : property.type === 'number' || property.type === 'integer' ? (
              <input
                type="number"
                value={formData[key] as number | string}
                onChange={(e) =>
                  setFormData({ ...formData, [key]: e.target.value === '' ? '' : Number(e.target.value) })
                }
                required={isRequired}
                className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text"
              />
            ) : (
              <input
                type="text"
                value={formData[key] as string}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
                required={isRequired}
                className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text"
              />
            )}
          </div>
        );
      })}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full px-3 py-1.5 text-sm rounded font-medium bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {isLoading ? 'Executing...' : 'Execute Tool'}
      </button>
    </form>
  );
}
