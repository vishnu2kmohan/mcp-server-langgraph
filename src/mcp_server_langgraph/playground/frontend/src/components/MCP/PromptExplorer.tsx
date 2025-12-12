/**
 * PromptExplorer Component
 *
 * Displays available MCP prompts with argument forms and execution.
 */

import React, { useState, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import { useMCPPrompts } from '../../hooks/useMCPPrompts';
import { EmptyState } from '../Common';
import type { MCPPrompt, MCPPromptArgument } from '../../api/mcp-types';

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

export interface PromptExplorerProps {
  className?: string;
  onPromptSelect?: (prompt: MCPPrompt) => void;
  onPromptResult?: (result: string) => void;
}

function PromptIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
      />
    </svg>
  );
}

export function PromptExplorer({ className, onPromptSelect, onPromptResult }: PromptExplorerProps): React.ReactElement {
  const { prompts, getPrompt } = useMCPPrompts();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPrompt, setSelectedPrompt] = useState<MCPPrompt | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter prompts by search query
  const filteredPrompts = useMemo(() => {
    if (!searchQuery.trim()) return prompts;

    const query = searchQuery.toLowerCase();
    return prompts.filter(
      (prompt) =>
        prompt.name.toLowerCase().includes(query) ||
        (prompt.description?.toLowerCase().includes(query))
    );
  }, [prompts, searchQuery]);

  const handlePromptClick = useCallback(
    (prompt: MCPPrompt) => {
      setSelectedPrompt(prompt);
      setResult(null);
      setError(null);
      onPromptSelect?.(prompt);
    },
    [onPromptSelect]
  );

  const handleExecute = useCallback(
    async (args: Record<string, string>) => {
      if (!selectedPrompt) return;

      setIsLoading(true);
      setError(null);
      setResult(null);

      try {
        const promptResult = await getPrompt(selectedPrompt.name, args);
        const content = promptResult.messages
          .map((m) => {
            const role = m.role === 'user' ? 'User' : 'Assistant';
            const text = m.content.type === 'text' ? m.content.text : '[Non-text content]';
            return `${role}: ${text}`;
          })
          .join('\n\n');
        setResult(content);
        onPromptResult?.(content);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to get prompt');
      } finally {
        setIsLoading(false);
      }
    },
    [selectedPrompt, getPrompt, onPromptResult]
  );

  const handleClose = useCallback(() => {
    setSelectedPrompt(null);
    setResult(null);
    setError(null);
  }, []);

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header with search */}
      <div className="p-3 border-b border-gray-200 dark:border-dark-border">
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider mb-2">
          Prompts ({prompts.length})
        </h3>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search prompts..."
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text placeholder-gray-400 dark:placeholder-dark-textMuted focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Prompt list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {filteredPrompts.length === 0 ? (
          prompts.length === 0 ? (
            <EmptyState
              icon={<PromptIcon className="w-12 h-12" />}
              title="No prompts available"
              description="Connect to an MCP server to access pre-built prompt templates."
              suggestions={[
                "Add an MCP server connection",
                "Check server prompt configuration",
                "Explore server capabilities"
              ]}
              variant="compact"
            />
          ) : (
            <EmptyState
              icon={<SearchIcon className="w-10 h-10" />}
              title="No matching prompts"
              description={`No prompts match "${searchQuery}"`}
              actionLabel="Clear Search"
              onAction={() => setSearchQuery('')}
              variant="compact"
            />
          )
        ) : (
          filteredPrompts.map((prompt) => (
            <PromptCard
              key={prompt.name}
              prompt={prompt}
              isSelected={selectedPrompt?.name === prompt.name}
              onClick={() => handlePromptClick(prompt)}
            />
          ))
        )}
      </div>

      {/* Prompt detail panel */}
      {selectedPrompt && (
        <div className="border-t border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-surface">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-dark-border">
            <h4 className="font-medium text-gray-900 dark:text-dark-text">{selectedPrompt.name}</h4>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-dark-text"
              aria-label="Close prompt details"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-3 max-h-64 overflow-y-auto">
            {selectedPrompt.description && (
              <p className="text-sm text-gray-600 dark:text-dark-textSecondary mb-3">
                {selectedPrompt.description}
              </p>
            )}

            {/* Argument form */}
            <PromptArgumentForm
              arguments={selectedPrompt.arguments || []}
              onSubmit={handleExecute}
              isLoading={isLoading}
            />

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
      )}
    </div>
  );
}

interface PromptCardProps {
  prompt: MCPPrompt;
  isSelected?: boolean;
  onClick?: () => void;
}

function PromptCard({ prompt, isSelected = false, onClick }: PromptCardProps): React.ReactElement {
  const argCount = prompt.arguments?.length || 0;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left p-3 rounded-lg border transition-colors',
        isSelected
          ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-500'
          : 'bg-white dark:bg-dark-surface border-gray-200 dark:border-dark-border hover:bg-gray-50 dark:hover:bg-dark-hover'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
            isSelected
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-dark-textSecondary'
          )}
        >
          <PromptIcon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <h4
            className={clsx(
              'font-medium truncate',
              isSelected
                ? 'text-primary-700 dark:text-primary-400'
                : 'text-gray-900 dark:text-dark-text'
            )}
          >
            {prompt.name}
          </h4>
          {prompt.description && (
            <p className="text-sm text-gray-500 dark:text-dark-textMuted line-clamp-2">
              {prompt.description}
            </p>
          )}
          {argCount > 0 && (
            <div className="mt-1 text-xs text-gray-400 dark:text-dark-textMuted">
              {argCount} argument{argCount !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

interface PromptArgumentFormProps {
  arguments: MCPPromptArgument[];
  onSubmit: (args: Record<string, string>) => void;
  isLoading?: boolean;
}

function PromptArgumentForm({ arguments: promptArgs, onSubmit, isLoading }: PromptArgumentFormProps): React.ReactElement {
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    promptArgs.forEach((arg) => {
      initial[arg.name] = '';
    });
    return initial;
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Filter out empty values for optional arguments
    const cleanedData: Record<string, string> = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value.trim()) cleanedData[key] = value;
    });
    onSubmit(cleanedData);
  };

  if (promptArgs.length === 0) {
    return (
      <button
        onClick={() => onSubmit({})}
        disabled={isLoading}
        className="w-full px-4 py-2 rounded-lg font-medium bg-primary-600 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
      >
        {isLoading ? 'Executing...' : 'Get Prompt'}
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 bg-white dark:bg-dark-bg p-3 rounded-lg border border-gray-200 dark:border-dark-border">
      {promptArgs.map((arg) => (
        <div key={arg.name}>
          <label className="block text-xs font-medium text-gray-600 dark:text-dark-textSecondary mb-1">
            {arg.name}
            {arg.required && <span className="text-error-500 ml-1">*</span>}
          </label>
          <input
            type="text"
            value={formData[arg.name] || ''}
            onChange={(e) => setFormData({ ...formData, [arg.name]: e.target.value })}
            required={arg.required}
            placeholder={arg.description}
            className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-dark-surface border-gray-300 dark:border-dark-border text-gray-900 dark:text-dark-text"
          />
          {arg.description && (
            <p className="text-xs text-gray-400 dark:text-dark-textMuted mt-0.5">
              {arg.description}
            </p>
          )}
        </div>
      ))}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full px-3 py-1.5 text-sm rounded font-medium bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {isLoading ? 'Executing...' : 'Get Prompt'}
      </button>
    </form>
  );
}
