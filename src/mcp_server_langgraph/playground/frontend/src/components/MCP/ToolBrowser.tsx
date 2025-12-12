/**
 * ToolBrowser Component
 *
 * Displays available MCP tools with search, filtering, and execution capabilities.
 */

import React, { useState, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import { useMCPTools } from '../../hooks/useMCPTools';
import { ToolCard } from './ToolCard';
import { EmptyState } from '../Common';
import type { MCPTool } from '../../api/mcp-types';

function ToolsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
      />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
      />
    </svg>
  );
}

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
          tools.length === 0 ? (
            <EmptyState
              icon={<ToolsIcon className="w-12 h-12" />}
              title="No tools available"
              description="Connect to an MCP server to access powerful tools for your tasks."
              suggestions={[
                "Add an MCP server connection",
                "Check server configuration",
                "Ensure server is running"
              ]}
              variant="compact"
            />
          ) : (
            <EmptyState
              icon={<SearchIcon className="w-10 h-10" />}
              title="No matching tools"
              description={`No tools match "${searchQuery}"`}
              actionLabel="Clear Search"
              onAction={() => setSearchQuery('')}
              variant="compact"
            />
          )
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
